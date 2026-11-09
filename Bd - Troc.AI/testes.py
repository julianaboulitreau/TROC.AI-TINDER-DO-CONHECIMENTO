"""Testes automatizados da camada de dados. Execute: python -m unittest -v"""
import sqlite3
import unittest

import banco as db

LUCAS, MARINA, MARIA, BEATRIZ, PEDRO = 1045, 1046, 1047, 1048, 1049


class BancoTestCase(unittest.TestCase):
    def setUp(self):
        db.ITERACOES_SENHA = 1000            # acelera o hash nos testes
        self.conn = db.conectar(":memory:")
        db.criar_banco(self.conn)
        db.popular_demo(self.conn)

    def tearDown(self):
        self.conn.close()

    def match_lucas_marina(self):
        db.registrar_interacao(self.conn, LUCAS, MARINA, "CONECTAR")
        return db.registrar_interacao(self.conn, MARINA, LUCAS, "CONECTAR")["match_id"]

    def sessao_lucas_marina(self):
        mid = self.match_lucas_marina()
        troca = db.definir_troca(self.conn, mid, "Manutenção de Hardware", "UI Design",
                                 "Manutenção do notebook em troca do protótipo no Figma")
        return db.agendar_sessao(self.conn, troca, "2026-12-05 14:00", "presencial", "Lab. Senac")


class TestEstrutura(BancoTestCase):
    def test_tabelas_e_views_existem(self):
        nomes = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        esperado = {"usuarios", "habilidades", "categorias", "usuario_habilidades", "interacoes",
                    "matches", "notificacoes", "mensagens", "trocas", "sessoes", "avaliacoes",
                    "selos", "usuario_selos", "v_usuarios_ativos", "v_cobertura",
                    "v_afinidade_skills", "v_reputacao"}
        self.assertTrue(esperado <= nomes, esperado - nomes)

    def test_pelo_menos_4_perfis_ativos(self):
        total = self.conn.execute("SELECT COUNT(*) FROM v_usuarios_ativos").fetchone()[0]
        self.assertGreaterEqual(total, 4)

    def test_personas_do_documento_com_ids_corretos(self):
        self.assertEqual(db.obter_perfil(self.conn, LUCAS)["nome"], "Lucas Andrade")
        self.assertEqual(db.obter_perfil(self.conn, MARINA)["nome"], "Marina Costa")

    def test_senha_nao_fica_em_texto_puro(self):
        h = self.conn.execute("SELECT senha_hash FROM usuarios WHERE id=?", (LUCAS,)).fetchone()[0]
        self.assertNotIn("senha123", h)
        self.assertEqual(db.autenticar(self.conn, "lucas.andrade@troc.ai", "senha123"), LUCAS)
        self.assertIsNone(db.autenticar(self.conn, "lucas.andrade@troc.ai", "errada"))

    def test_email_duplicado_e_invalido(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.criar_usuario(self.conn, "Outro", "LUCAS.ANDRADE@troc.ai", "abc123")
        with self.assertRaises(sqlite3.IntegrityError):
            db.criar_usuario(self.conn, "Sem Arroba", "emailinvalido", "abc123")


class TestHabilidades(BancoTestCase):
    def test_habilidade_nao_pode_ser_out_e_in(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.definir_habilidades(self.conn, LUCAS, ["Python", "Office", "Git"], ["Python"])

    def test_habilidade_fora_do_catalogo(self):
        with self.assertRaises(db.RegraDeNegocioError):
            db.definir_habilidades(self.conn, LUCAS, ["Culinária Marciana"], [])

    def test_perfil_com_menos_de_3_skills_out_fica_inativo(self):
        novo = db.criar_usuario(self.conn, "Novo Usuário", "novo@troc.ai", "abc123",
                                cidade="São Paulo", skills_out=["Git", "SQL"], skills_in=["Inglês"])
        self.assertFalse(db.perfil_ativo(self.conn, novo))
        with self.assertRaises(db.RegraDeNegocioError):
            db.sugestoes(self.conn, novo)
        # e não aparece nas sugestões dos outros
        ids = [s["id"] for s in db.sugestoes(self.conn, LUCAS)]
        self.assertNotIn(novo, ids)
        # ao completar 3 Skills Out, ativa
        db.definir_habilidades(self.conn, novo, ["Git", "SQL", "Cloud"], ["Inglês"])
        self.assertTrue(db.perfil_ativo(self.conn, novo))


class TestAfinidade(BancoTestCase):
    def test_afinidade_lucas_marina_e_98(self):
        self.assertEqual(db.calcular_afinidade(self.conn, LUCAS, MARINA), 98.0)
        self.assertEqual(db.calcular_afinidade(self.conn, MARINA, LUCAS), 98.0)  # simétrica

    def test_melhor_sugestao_do_lucas_e_marina(self):
        sug = db.sugestoes(self.conn, LUCAS)
        self.assertEqual(sug[0]["id"], MARINA)
        self.assertEqual(sug[0]["indice_afinidade"], 98.0)
        notas = [s["indice_afinidade"] for s in sug]
        self.assertEqual(notas, sorted(notas, reverse=True))

    def test_cenario_beatriz_pedro_power_bi_ingles(self):
        self.assertGreaterEqual(db.calcular_afinidade(self.conn, BEATRIZ, PEDRO), 90)
        self.assertEqual(db.sugestoes(self.conn, BEATRIZ)[0]["id"], PEDRO)

    def test_afinidade_zero_sem_complementaridade(self):
        self.assertLess(db.calcular_afinidade(self.conn, MARINA, PEDRO), 60)

    def test_filtros_de_busca(self):
        por_hab = db.buscar_perfis(self.conn, habilidade="Figma")
        self.assertEqual({p["id"] for p in por_hab}, {MARINA, MARIA})
        por_cat = db.buscar_perfis(self.conn, categoria="Idiomas")
        self.assertEqual({p["id"] for p in por_cat}, {BEATRIZ})
        por_zona = db.buscar_perfis(self.conn, zona="Zona Sul")
        self.assertEqual({p["id"] for p in por_zona}, {MARINA, BEATRIZ})
        quer_ingles = db.buscar_perfis(self.conn, habilidade="Inglês", tipo="IN")
        self.assertEqual({p["id"] for p in quer_ingles}, {MARIA, PEDRO})


class TestMatchENotificacoes(BancoTestCase):
    def test_match_somente_com_aceite_mutuo(self):
        r1 = db.registrar_interacao(self.conn, LUCAS, MARINA, "CONECTAR")
        self.assertFalse(r1["match"])
        self.assertIsNone(db.obter_match_entre(self.conn, LUCAS, MARINA))
        r2 = db.registrar_interacao(self.conn, MARINA, LUCAS, "CONECTAR")
        self.assertTrue(r2["match"])
        self.assertEqual(r2["indice_afinidade"], 98.0)
        self.assertIsNotNone(db.obter_match_entre(self.conn, MARINA, LUCAS))
        self.assertEqual(len(db.listar_matches(self.conn, LUCAS)), 1)

    def test_descartar_nao_gera_match_e_some_do_feed(self):
        db.registrar_interacao(self.conn, LUCAS, MARINA, "DESCARTAR")
        r = db.registrar_interacao(self.conn, MARINA, LUCAS, "CONECTAR")
        self.assertFalse(r["match"])
        self.assertNotIn(MARINA, [s["id"] for s in db.sugestoes(self.conn, LUCAS)])

    def test_interacao_repetida_ou_consigo_mesmo(self):
        db.registrar_interacao(self.conn, LUCAS, MARINA, "CONECTAR")
        with self.assertRaises(sqlite3.IntegrityError):
            db.registrar_interacao(self.conn, LUCAS, MARINA, "CONECTAR")
        with self.assertRaises(sqlite3.IntegrityError):
            db.registrar_interacao(self.conn, LUCAS, LUCAS, "CONECTAR")

    def test_notificacao_de_alta_afinidade_sem_duplicar(self):
        criadas = db.gerar_notificacoes_afinidade(self.conn)
        self.assertGreaterEqual(criadas, 4)
        msgs = [n["mensagem"] for n in db.listar_notificacoes(self.conn, LUCAS)]
        self.assertTrue(any("Marina Costa" in m and "98%" in m for m in msgs))
        self.assertEqual(db.gerar_notificacoes_afinidade(self.conn), 0)   # idempotente

    def test_notificacao_de_match_confirmado(self):
        self.match_lucas_marina()
        for uid in (LUCAS, MARINA):
            tipos = [n["tipo"] for n in db.listar_notificacoes(self.conn, uid)]
            self.assertIn("MATCH_CONFIRMADO", tipos)


class TestChat(BancoTestCase):
    def test_chat_bloqueado_sem_match(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.enviar_mensagem(self.conn, 999, LUCAS, "Oi!")

    def test_chat_liberado_apenas_para_participantes(self):
        mid = self.match_lucas_marina()
        db.enviar_mensagem(self.conn, mid, LUCAS, "Oi! Vi que você quer aprender HTML.")
        db.enviar_mensagem(self.conn, mid, MARINA, "Sim! Posso te ensinar UI/Figma em troca.")
        msgs = db.listar_mensagens(self.conn, mid)
        self.assertEqual([m["remetente_nome"] for m in msgs], ["Lucas Andrade", "Marina Costa"])
        with self.assertRaises(sqlite3.IntegrityError):
            db.enviar_mensagem(self.conn, mid, PEDRO, "Posso entrar?")

    def test_mensagem_vazia_rejeitada(self):
        mid = self.match_lucas_marina()
        with self.assertRaises(sqlite3.IntegrityError):
            db.enviar_mensagem(self.conn, mid, LUCAS, "   ")


class TestTrocaSessaoReputacao(BancoTestCase):
    def test_troca_exige_skill_out_de_cada_lado(self):
        mid = self.match_lucas_marina()
        with self.assertRaises(sqlite3.IntegrityError):       # Lucas não ensina Figma
            db.definir_troca(self.conn, mid, "Figma", "UI Design")

    def test_modalidade_e_data_invalidas(self):
        mid = self.match_lucas_marina()
        troca = db.definir_troca(self.conn, mid, "Python", "Figma")
        with self.assertRaises(sqlite3.IntegrityError):
            db.agendar_sessao(self.conn, troca, "2026-12-05 14:00", "TELEPATIA")
        with self.assertRaises(db.RegraDeNegocioError):
            db.agendar_sessao(self.conn, troca, "05/12/2026", "ONLINE")

    def test_fluxo_completo_ate_selo_e_reputacao(self):
        sessao = self.sessao_lucas_marina()
        # avaliação antes de concluir é bloqueada
        with self.assertRaises(sqlite3.IntegrityError):
            db.avaliar(self.conn, sessao, LUCAS, MARINA, 5, "Ótimo!")
        db.concluir_sessao(self.conn, sessao)
        with self.assertRaises(db.RegraDeNegocioError):        # não conclui duas vezes
            db.concluir_sessao(self.conn, sessao)
        db.avaliar(self.conn, sessao, LUCAS, MARINA, 5, "Protótipo incrível no Figma!")
        db.avaliar(self.conn, sessao, MARINA, LUCAS, 5, "Meu notebook voou!")
        for uid in (LUCAS, MARINA):
            rep = db.reputacao(self.conn, uid)
            self.assertEqual(rep["nota_media"], 5.0)
            self.assertEqual(rep["total_avaliacoes"], 1)
            self.assertEqual(rep["trocas_concluidas"], 1)
            self.assertIn("Primeira Permuta Concluída", db.selos_do_usuario(self.conn, uid))
        self.assertEqual(len(db.depoimentos(self.conn, MARINA)), 1)
        concluida_em = self.conn.execute("SELECT concluida_em FROM sessoes WHERE id=?",
                                         (sessao,)).fetchone()[0]
        self.assertIsNotNone(concluida_em)

    def test_nota_fora_de_1_a_5(self):
        sessao = self.sessao_lucas_marina()
        db.concluir_sessao(self.conn, sessao)
        for nota in (0, 6):
            with self.assertRaises(sqlite3.IntegrityError):
                db.avaliar(self.conn, sessao, LUCAS, MARINA, nota)

    def test_avaliacao_duplicada_e_de_estranho(self):
        sessao = self.sessao_lucas_marina()
        db.concluir_sessao(self.conn, sessao)
        db.avaliar(self.conn, sessao, LUCAS, MARINA, 4)
        with self.assertRaises(sqlite3.IntegrityError):
            db.avaliar(self.conn, sessao, LUCAS, MARINA, 5)
        with self.assertRaises(sqlite3.IntegrityError):
            db.avaliar(self.conn, sessao, PEDRO, MARINA, 5)
        with self.assertRaises(sqlite3.IntegrityError):
            db.avaliar(self.conn, sessao, LUCAS, LUCAS, 5)

    def test_media_com_varias_avaliacoes(self):
        sessao = self.sessao_lucas_marina()
        db.concluir_sessao(self.conn, sessao)
        db.avaliar(self.conn, sessao, LUCAS, MARINA, 5)
        # Segunda sessão, outra avaliação nota 4 para Marina
        mid = db.obter_match_entre(self.conn, LUCAS, MARINA)
        troca2 = db.definir_troca(self.conn, mid, "Python", "Figma")
        s2 = db.agendar_sessao(self.conn, troca2, "2026-12-12 10:00", "ONLINE", "meet.google.com/x")
        db.concluir_sessao(self.conn, s2)
        db.avaliar(self.conn, s2, LUCAS, MARINA, 4)
        self.assertEqual(db.reputacao(self.conn, MARINA)["nota_media"], 4.5)
        self.assertEqual(db.reputacao(self.conn, MARINA)["trocas_concluidas"], 2)


class TestPersistenciaEmArquivo(unittest.TestCase):
    def test_banco_em_arquivo_reabre_com_dados(self):
        import tempfile, os
        db.ITERACOES_SENHA = 1000
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "t.db")
            c = db.recriar_banco(caminho)
            db.popular_demo(c)
            c.close()
            c2 = db.conectar(caminho)
            self.assertEqual(c2.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0], 5)
            self.assertEqual(c2.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            c2.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
