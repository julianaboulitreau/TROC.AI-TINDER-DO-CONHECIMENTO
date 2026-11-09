"""
Troc.ai (Tinder do Conhecimento) - Camada de dados / repositório.
Responsável: Pessoa 4 (Daphiny) - Back-end (O Banco).

Uso pela API (Pessoa 3):
    from banco import conectar, sugestoes, registrar_interacao, ...
    conn = conectar()
    sugestoes(conn, usuario_id=1045)

Banco: SQLite (arquivo trocai.db), sem instalação extra - só Python 3.8+.
"""
import hashlib
import hmac
import os
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PADRAO = BASE_DIR / "trocai.db"

# Índice de Afinidade final = 90% skills (matriz oferta x demanda) + 10% proximidade
PESO_SKILLS = 0.9
PESO_PROXIMIDADE = 0.1
LIMIAR_NOTIFICACAO = 80.0          # afinidade mínima para disparar alerta
ITERACOES_SENHA = 200_000


class RegraDeNegocioError(Exception):
    """Violação de regra de negócio detectada na camada Python."""


# ----------------------------------------------------------------------
# Conexão e criação do banco
# ----------------------------------------------------------------------
def conectar(caminho=DB_PADRAO):
    conn = sqlite3.connect(str(caminho))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")      # SQLite exige ativar por conexão
    return conn


def criar_banco(conn):
    """Cria tabelas, triggers, views e o catálogo de habilidades/selos."""
    conn.executescript((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript((BASE_DIR / "dados_iniciais.sql").read_text(encoding="utf-8"))
    conn.commit()


def recriar_banco(caminho=DB_PADRAO):
    """Apaga o arquivo e recria tudo do zero (útil em desenvolvimento)."""
    if str(caminho) != ":memory:" and Path(caminho).exists():
        Path(caminho).unlink()
    conn = conectar(caminho)
    criar_banco(conn)
    return conn


# ----------------------------------------------------------------------
# Senha (nunca armazenar em texto puro)
# ----------------------------------------------------------------------
def gerar_hash_senha(senha):
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, ITERACOES_SENHA)
    return f"pbkdf2_sha256${ITERACOES_SENHA}${salt.hex()}${h.hex()}"


def verificar_senha(senha, armazenado):
    try:
        _, iteracoes, salt, esperado = armazenado.split("$")
        h = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"),
                                bytes.fromhex(salt), int(iteracoes))
        return hmac.compare_digest(h.hex(), esperado)
    except (ValueError, AttributeError):
        return False


# ----------------------------------------------------------------------
# Habilidades e usuários (Telas 01 a 06)
# ----------------------------------------------------------------------
def listar_habilidades(conn):
    return [dict(r) for r in conn.execute(
        """SELECT h.id, h.nome, c.nome AS categoria
             FROM habilidades h JOIN categorias c ON c.id = h.categoria_id
            ORDER BY c.nome, h.nome""")]


def _id_habilidade(conn, nome):
    row = conn.execute("SELECT id FROM habilidades WHERE nome = ?", (nome,)).fetchone()
    if row is None:
        raise RegraDeNegocioError(f"Habilidade '{nome}' não existe no catálogo")
    return row["id"]


def _gravar_habilidades(conn, usuario_id, skills_out, skills_in):
    conn.execute("DELETE FROM usuario_habilidades WHERE usuario_id = ?", (usuario_id,))
    for tipo, nomes in (("OUT", skills_out), ("IN", skills_in)):
        for nome in nomes:
            conn.execute(
                "INSERT INTO usuario_habilidades (usuario_id, habilidade_id, tipo) VALUES (?,?,?)",
                (usuario_id, _id_habilidade(conn, nome), tipo))


def criar_usuario(conn, nome, email, senha, *, id=None, curso=None, instituicao=None,
                  bio=None, foto_url=None, cidade=None, zona=None, latitude=None,
                  longitude=None, nivel_tecnologia=None, skills_out=(), skills_in=()):
    if len(senha) < 6:
        raise RegraDeNegocioError("A senha deve ter ao menos 6 caracteres")
    with conn:
        cur = conn.execute(
            """INSERT INTO usuarios (id, nome, email, senha_hash, curso, instituicao, bio,
                                     foto_url, cidade, zona, latitude, longitude, nivel_tecnologia)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (id, nome, email, gerar_hash_senha(senha), curso, instituicao, bio, foto_url,
             cidade, zona, latitude, longitude, nivel_tecnologia))
        uid = cur.lastrowid
        _gravar_habilidades(conn, uid, skills_out, skills_in)
    return uid


def definir_habilidades(conn, usuario_id, skills_out, skills_in):
    """Tela 04 / Tela 06: substitui a matriz de habilidades do usuário."""
    with conn:
        _gravar_habilidades(conn, usuario_id, skills_out, skills_in)


def autenticar(conn, email, senha):
    """Tela 01 (login). Retorna o id do usuário ou None."""
    row = conn.execute("SELECT id, senha_hash FROM usuarios WHERE email = ?", (email,)).fetchone()
    if row and verificar_senha(senha, row["senha_hash"]):
        return row["id"]
    return None


def perfil_ativo(conn, usuario_id):
    """True se tem >= 3 Skills Out e >= 1 Skill In (ativa o algoritmo)."""
    return conn.execute("SELECT 1 FROM v_usuarios_ativos WHERE id = ?",
                        (usuario_id,)).fetchone() is not None


def obter_perfil(conn, usuario_id):
    """Tela 05 / Tela 08: perfil completo com skills e reputação."""
    u = conn.execute(
        """SELECT id, nome, email, curso, instituicao, bio, foto_url, cidade, zona,
                  latitude, longitude, nivel_tecnologia, criado_em
             FROM usuarios WHERE id = ?""", (usuario_id,)).fetchone()
    if u is None:
        return None
    perfil = dict(u)
    for chave, tipo in (("skills_out", "OUT"), ("skills_in", "IN")):
        perfil[chave] = [r["nome"] for r in conn.execute(
            """SELECT h.nome FROM usuario_habilidades uh
                 JOIN habilidades h ON h.id = uh.habilidade_id
                WHERE uh.usuario_id = ? AND uh.tipo = ? ORDER BY h.nome""", (usuario_id, tipo))]
    perfil["perfil_ativo"] = perfil_ativo(conn, usuario_id)
    perfil["reputacao"] = reputacao(conn, usuario_id)
    perfil["selos"] = selos_do_usuario(conn, usuario_id)
    return perfil


# ----------------------------------------------------------------------
# Afinidade, feed e busca com filtros (Telas 07 e 08)
# ----------------------------------------------------------------------
def calcular_proximidade(u1, u2):
    """100 = mesma cidade e zona | 80 = mesma cidade | 50 = cidades diferentes (online)."""
    if u1["cidade"] and u1["cidade"] == u2["cidade"]:
        return 100.0 if u1["zona"] and u1["zona"] == u2["zona"] else 80.0
    return 50.0


def calcular_afinidade(conn, usuario_1, usuario_2):
    """Índice de Afinidade (0-100). Retorna 0 se algum perfil não estiver ativo."""
    a, b = sorted((usuario_1, usuario_2))
    row = conn.execute(
        "SELECT afinidade_skills FROM v_afinidade_skills WHERE usuario_a_id=? AND usuario_b_id=?",
        (a, b)).fetchone()
    if row is None:
        return 0.0
    u1 = conn.execute("SELECT cidade, zona FROM usuarios WHERE id=?", (a,)).fetchone()
    u2 = conn.execute("SELECT cidade, zona FROM usuarios WHERE id=?", (b,)).fetchone()
    prox = calcular_proximidade(u1, u2)
    return round(PESO_SKILLS * row["afinidade_skills"] + PESO_PROXIMIDADE * prox, 1)


def sugestoes(conn, usuario_id, limite=10):
    """Tela 07: perfis recomendados ordenados por afinidade (já descartados/conectados saem)."""
    if not perfil_ativo(conn, usuario_id):
        raise RegraDeNegocioError(
            "Perfil inativo: cadastre ao menos 3 Skills Out e 1 Skill In para usar o match")
    ids = [r["id"] for r in conn.execute(
        """SELECT id FROM v_usuarios_ativos
            WHERE id <> ?
              AND id NOT IN (SELECT para_usuario_id FROM interacoes WHERE de_usuario_id = ?)""",
        (usuario_id, usuario_id))]
    lista = []
    for outro in ids:
        perfil = obter_perfil(conn, outro)
        perfil["indice_afinidade"] = calcular_afinidade(conn, usuario_id, outro)
        lista.append(perfil)
    lista.sort(key=lambda p: p["indice_afinidade"], reverse=True)
    return lista[:limite]


def buscar_perfis(conn, *, habilidade=None, categoria=None, tipo="OUT",
                  cidade=None, zona=None, excluir_usuario_id=None):
    """Busca com filtros (categoria técnica, habilidade, localização)."""
    sql = ["SELECT DISTINCT u.id FROM usuarios u"]
    params = []
    if habilidade or categoria:
        sql.append("""JOIN usuario_habilidades uh ON uh.usuario_id = u.id AND uh.tipo = ?
                      JOIN habilidades h ON h.id = uh.habilidade_id
                      JOIN categorias  c ON c.id = h.categoria_id""")
        params.append(tipo)
    sql.append("WHERE u.id IN (SELECT id FROM v_usuarios_ativos)")
    if habilidade:
        sql.append("AND h.nome = ?"); params.append(habilidade)
    if categoria:
        sql.append("AND c.nome = ?"); params.append(categoria)
    if cidade:
        sql.append("AND u.cidade = ?"); params.append(cidade)
    if zona:
        sql.append("AND u.zona = ?"); params.append(zona)
    if excluir_usuario_id is not None:
        sql.append("AND u.id <> ?"); params.append(excluir_usuario_id)
    sql.append("ORDER BY u.id")
    return [obter_perfil(conn, r["id"]) for r in conn.execute(" ".join(sql), params)]


# ----------------------------------------------------------------------
# Match, notificações (Tela 09)
# ----------------------------------------------------------------------
def registrar_interacao(conn, de_usuario_id, para_usuario_id, acao):
    """✕ Descartar / ♡ Conectar. Match só nasce com aceitação MÚTUA."""
    acao = acao.upper()
    if acao not in ("CONECTAR", "DESCARTAR"):
        raise RegraDeNegocioError("Ação inválida (use CONECTAR ou DESCARTAR)")
    if not (perfil_ativo(conn, de_usuario_id) and perfil_ativo(conn, para_usuario_id)):
        raise RegraDeNegocioError("Os dois perfis precisam estar ativos (mín. 3 Skills Out)")
    with conn:
        conn.execute(
            "INSERT INTO interacoes (de_usuario_id, para_usuario_id, acao) VALUES (?,?,?)",
            (de_usuario_id, para_usuario_id, acao))
        if acao == "DESCARTAR":
            return {"match": False, "match_id": None, "indice_afinidade": None}
        reciproco = conn.execute(
            """SELECT 1 FROM interacoes
                WHERE de_usuario_id = ? AND para_usuario_id = ? AND acao = 'CONECTAR'""",
            (para_usuario_id, de_usuario_id)).fetchone()
        if not reciproco:
            return {"match": False, "match_id": None, "indice_afinidade": None}
        a, b = sorted((de_usuario_id, para_usuario_id))
        afinidade = calcular_afinidade(conn, a, b)
        cur = conn.execute(
            "INSERT INTO matches (usuario_a_id, usuario_b_id, indice_afinidade) VALUES (?,?,?)",
            (a, b, afinidade))
        for quem, outro in ((a, b), (b, a)):
            nome = conn.execute("SELECT nome FROM usuarios WHERE id=?", (outro,)).fetchone()["nome"]
            conn.execute(
                """INSERT OR IGNORE INTO notificacoes (usuario_id, ref_usuario_id, tipo, mensagem)
                   VALUES (?,?, 'MATCH_CONFIRMADO', ?)""",
                (quem, outro, f"É um match! Você e {nome} podem conversar e combinar a troca."))
        return {"match": True, "match_id": cur.lastrowid, "indice_afinidade": afinidade}


def obter_match_entre(conn, usuario_1, usuario_2):
    a, b = sorted((usuario_1, usuario_2))
    row = conn.execute("SELECT id FROM matches WHERE usuario_a_id=? AND usuario_b_id=?",
                       (a, b)).fetchone()
    return row["id"] if row else None


def listar_matches(conn, usuario_id):
    return [dict(r) for r in conn.execute(
        """SELECT m.id AS match_id, m.indice_afinidade, m.criado_em,
                  u.id AS outro_usuario_id, u.nome AS outro_usuario_nome
             FROM matches m
             JOIN usuarios u ON u.id = CASE WHEN m.usuario_a_id = ? THEN m.usuario_b_id
                                            ELSE m.usuario_a_id END
            WHERE ? IN (m.usuario_a_id, m.usuario_b_id)
            ORDER BY m.id DESC""", (usuario_id, usuario_id))]


def gerar_notificacoes_afinidade(conn, limiar=LIMIAR_NOTIFICACAO):
    """Dispara 'MATCH_SUGERIDO' para pares com afinidade >= limiar (sem duplicar)."""
    criadas = 0
    pares = conn.execute("SELECT usuario_a_id, usuario_b_id FROM v_afinidade_skills").fetchall()
    with conn:
        for p in pares:
            a, b = p["usuario_a_id"], p["usuario_b_id"]
            if obter_match_entre(conn, a, b):
                continue
            afinidade = calcular_afinidade(conn, a, b)
            if afinidade < limiar:
                continue
            for quem, outro in ((a, b), (b, a)):
                nome = conn.execute("SELECT nome FROM usuarios WHERE id=?", (outro,)).fetchone()["nome"]
                cur = conn.execute(
                    """INSERT OR IGNORE INTO notificacoes (usuario_id, ref_usuario_id, tipo, mensagem)
                       VALUES (?,?, 'MATCH_SUGERIDO', ?)""",
                    (quem, outro, f"{nome} tem {afinidade:.0f}% de afinidade com você!"))
                criadas += cur.rowcount
    return criadas


def listar_notificacoes(conn, usuario_id, apenas_nao_lidas=False):
    sql = "SELECT * FROM notificacoes WHERE usuario_id = ?"
    if apenas_nao_lidas:
        sql += " AND lida = 0"
    return [dict(r) for r in conn.execute(sql + " ORDER BY id DESC", (usuario_id,))]


def marcar_notificacao_lida(conn, notificacao_id):
    with conn:
        conn.execute("UPDATE notificacoes SET lida = 1 WHERE id = ?", (notificacao_id,))


# ----------------------------------------------------------------------
# Chat e definição da troca (Telas 10 e 11)
# ----------------------------------------------------------------------
def enviar_mensagem(conn, match_id, remetente_id, texto):
    with conn:
        cur = conn.execute(
            "INSERT INTO mensagens (match_id, remetente_id, texto) VALUES (?,?,?)",
            (match_id, remetente_id, texto))
    return cur.lastrowid


def listar_mensagens(conn, match_id):
    return [dict(r) for r in conn.execute(
        """SELECT m.id, m.remetente_id, u.nome AS remetente_nome, m.texto, m.enviada_em
             FROM mensagens m JOIN usuarios u ON u.id = m.remetente_id
            WHERE m.match_id = ? ORDER BY m.id""", (match_id,))]


def definir_troca(conn, match_id, habilidade_usuario_a, habilidade_usuario_b, objetivo=None):
    """A ensina X, B ensina Y. (a/b = ordem por id dentro do match)."""
    with conn:
        cur = conn.execute(
            """INSERT INTO trocas (match_id, habilidade_a_id, habilidade_b_id, objetivo)
               VALUES (?,?,?,?)""",
            (match_id, _id_habilidade(conn, habilidade_usuario_a),
             _id_habilidade(conn, habilidade_usuario_b), objetivo))
    return cur.lastrowid


# ----------------------------------------------------------------------
# Sessões, avaliação e reputação (Telas 12 a 15)
# ----------------------------------------------------------------------
def agendar_sessao(conn, troca_id, data_hora, modalidade, local_ou_link=None):
    try:
        datetime.strptime(data_hora, "%Y-%m-%d %H:%M")
    except ValueError:
        raise RegraDeNegocioError("data_hora deve estar no formato 'AAAA-MM-DD HH:MM'")
    with conn:
        cur = conn.execute(
            """INSERT INTO sessoes (troca_id, data_hora, modalidade, local_ou_link)
               VALUES (?,?,?,?)""", (troca_id, data_hora, modalidade.upper(), local_ou_link))
    return cur.lastrowid


def concluir_sessao(conn, sessao_id):
    """Botão 'Marcar sessão como concluída' (Tela 13)."""
    with conn:
        cur = conn.execute(
            "UPDATE sessoes SET status = 'CONCLUIDA' WHERE id = ? AND status = 'AGENDADA'",
            (sessao_id,))
        if cur.rowcount == 0:
            raise RegraDeNegocioError("Sessão inexistente ou não está agendada")


def avaliar(conn, sessao_id, avaliador_id, avaliado_id, nota, comentario=None):
    """Tela 14: nota de 1 a 5 + comentário."""
    with conn:
        cur = conn.execute(
            """INSERT INTO avaliacoes (sessao_id, avaliador_id, avaliado_id, nota, comentario)
               VALUES (?,?,?,?,?)""", (sessao_id, avaliador_id, avaliado_id, nota, comentario))
    return cur.lastrowid


def reputacao(conn, usuario_id):
    """Tela 15: nota média, nº de avaliações e trocas concluídas."""
    row = conn.execute("SELECT nota_media, total_avaliacoes, trocas_concluidas "
                       "FROM v_reputacao WHERE usuario_id = ?", (usuario_id,)).fetchone()
    return dict(row) if row else None


def depoimentos(conn, usuario_id):
    return [dict(r) for r in conn.execute(
        """SELECT a.nota, a.comentario, u.nome AS autor, a.criada_em
             FROM avaliacoes a JOIN usuarios u ON u.id = a.avaliador_id
            WHERE a.avaliado_id = ? AND a.comentario IS NOT NULL ORDER BY a.id DESC""",
        (usuario_id,))]


def selos_do_usuario(conn, usuario_id):
    return [r["nome"] for r in conn.execute(
        """SELECT s.nome FROM usuario_selos us JOIN selos s ON s.id = us.selo_id
            WHERE us.usuario_id = ?""", (usuario_id,))]


# ----------------------------------------------------------------------
# Dados de demonstração: personas do documento + 3 perfis extras
# ----------------------------------------------------------------------
PERFIS_DEMO = [
    dict(id=1045, nome="Lucas Andrade", email="lucas.andrade@troc.ai", senha="senha123",
         curso="Análise e Desenvolvimento de Sistemas", instituicao="Senac",
         bio="Estagiário de TI, 22 anos. Quero a UI do meu app de finanças para o TCC.",
         cidade="São Paulo", zona="Zona Leste", nivel_tecnologia="Avançado",
         skills_out=["Python", "Manutenção de Hardware", "Office", "Lógica de Programação",
                     "Programação Básica", "HTML/Web"],
         skills_in=["UI Design", "Figma", "Design Gráfico", "Photoshop"]),
    dict(id=1046, nome="Marina Costa", email="marina.costa@troc.ai", senha="senha123",
         curso="Design Gráfico", instituicao="Senac",
         bio="Freelancer, 24 anos. Meu notebook trava e preciso de um site de portfólio.",
         cidade="São Paulo", zona="Zona Sul", nivel_tecnologia="Intermediário",
         skills_out=["Design Gráfico", "UI Design", "Figma", "Photoshop", "Illustrator",
                     "Identidade Visual"],
         skills_in=["Manutenção de Hardware", "Programação Básica", "HTML/Web"]),
    dict(id=1047, nome="Maria Oliveira", email="maria.oliveira@troc.ai", senha="senha123",
         curso="Sistemas de Informação", instituicao="Senac",
         bio="Desenvolvedora interessada em aprender e compartilhar conhecimentos.",
         cidade="São Paulo", zona="Zona Oeste", nivel_tecnologia="Intermediário",
         skills_out=["UX Design", "UI Design", "Figma"],
         skills_in=["Python", "SQL", "Inglês", "Cloud"]),
    dict(id=1048, nome="Beatriz Ferreira", email="beatriz.ferreira@troc.ai", senha="senha123",
         curso="Administração", instituicao="Senac",
         bio="Preciso de Power BI e Excel avançado para concorrer a um estágio.",
         cidade="São Paulo", zona="Zona Sul", nivel_tecnologia="Básico",
         skills_out=["Inglês", "Office", "Design Gráfico"],
         skills_in=["Power BI", "Excel Avançado"]),
    dict(id=1049, nome="Pedro Henrique", email="pedro.henrique@troc.ai", senha="senha123",
         curso="Ciência da Computação", instituicao="Senac",
         bio="Domino Power BI e SQL. Quero praticar inglês e aprender design.",
         cidade="São Paulo", zona="Zona Norte", nivel_tecnologia="Avançado",
         skills_out=["Power BI", "Excel Avançado", "SQL", "Python"],
         skills_in=["Inglês", "Design Gráfico"]),
]


def popular_demo(conn):
    for p in PERFIS_DEMO:
        criar_usuario(conn, **p)


if __name__ == "__main__":
    conn = recriar_banco()
    popular_demo(conn)
    print("Banco criado:", DB_PADRAO)
    print("\nSugestões para Lucas Andrade (#1045):")
    for s in sugestoes(conn, 1045):
        print(f"  {s['indice_afinidade']:5.1f}%  #{s['id']} {s['nome']}")
    print("\nNotificações geradas:", gerar_notificacoes_afinidade(conn))
