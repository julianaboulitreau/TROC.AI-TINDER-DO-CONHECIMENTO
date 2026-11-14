"""API HTTP local para conectar a interface web ao repositório SQLite."""
import json
import secrets
import sqlite3
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import banco

SESSOES = {}
COOKIE_SESSAO = "trocai_sessao"


def preparar_banco(caminho=banco.DB_PADRAO):
    conn = banco.conectar(caminho)
    try:
        tabelas = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "usuarios" not in tabelas:
            banco.criar_banco(conn)
        for perfil in banco.PERFIS_DEMO:
            existente = conn.execute(
                "SELECT 1 FROM usuarios WHERE id = ? OR email = ?",
                (perfil["id"], perfil["email"]),
            ).fetchone()
            if existente is None:
                banco.criar_usuario(conn, **perfil)
    finally:
        conn.close()


class APIHandler(BaseHTTPRequestHandler):
    def _responder(self, status, dados, cookie=None):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_json(self):
        tamanho = int(self.headers.get("Content-Length", "0"))
        if tamanho < 0 or tamanho > 1_000_000:
            raise ValueError("A requisição excede o tamanho permitido.")
        return json.loads(self.rfile.read(tamanho) or b"{}")

    def _usuario_id(self):
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookies.get(COOKIE_SESSAO)
        return SESSOES.get(morsel.value) if morsel else None

    def _exigir_usuario(self):
        usuario_id = self._usuario_id()
        if usuario_id is None:
            self._responder(401, {"erro": "Faça login para continuar."})
        return usuario_id

    def do_GET(self):
        url = urlparse(self.path)
        conn = banco.conectar()
        try:
            if url.path == "/api/sessao":
                usuario_id = self._usuario_id()
                perfil = banco.obter_perfil(conn, usuario_id) if usuario_id else None
                return self._responder(200, {"usuario": perfil})

            if url.path == "/api/opcoes":
                habilidades = banco.listar_habilidades(conn)
                return self._responder(200, {"habilidades": habilidades})

            if url.path == "/api/conhecimentos":
                params = parse_qs(url.query)
                consulta = params.get("q", [""])[0].strip().casefold()
                tipo = params.get("tipo", [""])[0].strip().casefold()
                usuario_id = self._usuario_id()
                perfis = banco.buscar_perfis(
                    conn, excluir_usuario_id=usuario_id)
                if usuario_id is not None:
                    interagidos = {
                        r["para_usuario_id"] for r in conn.execute(
                            "SELECT para_usuario_id FROM interacoes WHERE de_usuario_id = ?",
                            (usuario_id,),
                        )
                    }
                    perfis = [p for p in perfis if p["id"] not in interagidos]
                if tipo not in ("", "oferta", "demanda"):
                    return self._responder(400, {"erro": "Tipo de busca inválido."})
                filtrados = []
                for perfil in perfis:
                    if tipo == "oferta":
                        habilidades = perfil["skills_out"]
                    elif tipo == "demanda":
                        habilidades = perfil["skills_in"]
                    else:
                        habilidades = perfil["skills_out"] + perfil["skills_in"]
                    textos = [
                        perfil["nome"], perfil["bio"] or "", perfil["curso"] or "",
                        perfil["cidade"] or "", perfil["zona"] or "",
                        *habilidades,
                    ]
                    if consulta and not any(consulta in texto.casefold() for texto in textos):
                        continue
                    filtrados.append({
                        **perfil,
                        "habilidades_encontradas": habilidades,
                        "tipo_busca": "Demanda" if tipo == "demanda" else "Oferta",
                    })
                return self._responder(200, filtrados)

            if url.path == "/api/match":
                usuario_id = self._exigir_usuario()
                if usuario_id is None:
                    return
                matches = []
                for match in banco.listar_matches(conn, usuario_id):
                    perfil = banco.obter_perfil(conn, match["outro_usuario_id"])
                    matches.append({**match, "perfil": perfil})
                return self._responder(200, matches)

            return self._responder(404, {"erro": "Rota não encontrada."})
        except banco.RegraDeNegocioError as erro:
            self._responder(400, {"erro": str(erro)})
        except sqlite3.Error:
            self._responder(500, {"erro": "Não foi possível consultar o banco de dados."})
        finally:
            conn.close()

    def do_POST(self):
        url = urlparse(self.path)
        try:
            dados = self._ler_json()
            if not isinstance(dados, dict):
                raise ValueError("O corpo da requisição deve ser um objeto JSON.")
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as erro:
            return self._responder(400, {"erro": str(erro) or "JSON inválido."})

        conn = banco.conectar()
        try:
            if url.path == "/api/login":
                email = str(dados.get("email", "")).strip()
                senha = str(dados.get("senha", ""))
                usuario_id = banco.autenticar(conn, email, senha)
                if usuario_id is None:
                    return self._responder(401, {"erro": "E-mail ou senha incorretos."})
                token = secrets.token_urlsafe(32)
                SESSOES[token] = usuario_id
                cookie = f"{COOKIE_SESSAO}={token}; HttpOnly; SameSite=Lax; Path=/"
                return self._responder(
                    200, {"usuario": banco.obter_perfil(conn, usuario_id)}, cookie)

            if url.path == "/api/logout":
                cookies = SimpleCookie(self.headers.get("Cookie", ""))
                morsel = cookies.get(COOKIE_SESSAO)
                if morsel:
                    SESSOES.pop(morsel.value, None)
                return self._responder(
                    200, {"mensagem": "Sessão encerrada."},
                    f"{COOKIE_SESSAO}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")

            if url.path == "/api/usuarios":
                skills_out = dados.get("skills_out", [])
                skills_in = dados.get("skills_in", [])
                if not isinstance(skills_out, list) or not isinstance(skills_in, list):
                    return self._responder(400, {"erro": "As habilidades devem ser enviadas como listas."})
                if not all(isinstance(item, str) for item in skills_out + skills_in):
                    return self._responder(400, {"erro": "Cada habilidade deve ser um texto."})
                uid = banco.criar_usuario(
                    conn,
                    nome=str(dados.get("nome", "")).strip(),
                    email=str(dados.get("email", "")).strip(),
                    senha=str(dados.get("senha", "")),
                    curso=dados.get("curso") or None,
                    instituicao=dados.get("instituicao") or None,
                    cidade=dados.get("cidade") or None,
                    zona=dados.get("zona") or None,
                    skills_out=skills_out,
                    skills_in=skills_in,
                )
                token = secrets.token_urlsafe(32)
                SESSOES[token] = uid
                cookie = f"{COOKIE_SESSAO}={token}; HttpOnly; SameSite=Lax; Path=/"
                return self._responder(
                    201, {"usuario": banco.obter_perfil(conn, uid)}, cookie)

            if url.path == "/api/interacoes":
                usuario_id = self._exigir_usuario()
                if usuario_id is None:
                    return
                try:
                    alvo_id = int(dados.get("para_usuario_id"))
                except (TypeError, ValueError):
                    return self._responder(400, {"erro": "Perfil de destino inválido."})
                resultado = banco.registrar_interacao(
                    conn, usuario_id, alvo_id, str(dados.get("acao", "")))
                return self._responder(201, resultado)

            return self._responder(404, {"erro": "Rota não encontrada."})
        except banco.RegraDeNegocioError as erro:
            self._responder(400, {"erro": str(erro)})
        except sqlite3.IntegrityError as erro:
            mensagem = str(erro)
            if "usuarios.email" in mensagem:
                self._responder(409, {"erro": "Este e-mail já está cadastrado."})
            else:
                self._responder(400, {"erro": "Os dados enviados não são válidos."})
        except sqlite3.Error:
            self._responder(500, {"erro": "Não foi possível atualizar o banco de dados."})
        finally:
            conn.close()

    def log_message(self, formato, *args):
        print(f"{self.address_string()} - {formato % args}")


if __name__ == "__main__":
    preparar_banco()
    servidor = ThreadingHTTPServer(("127.0.0.1", 3001), APIHandler)
    print("API Troc.ai disponível em http://127.0.0.1:3001")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()
