import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { obterSessao, sair } from "./api.js";
import Busca from "./pages/Busca.jsx";
import Cadastro from "./pages/Cadastro.jsx";
import Login from "./pages/Login.jsx";
import Match from "./pages/Match.jsx";

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [erroSessao, setErroSessao] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const atualizar = () => {
      obterSessao()
        .then((r) => {
          setUsuario(r.usuario);
          setErroSessao("");
        })
        .catch((err) => setErroSessao(err.message));
    };
    atualizar();
    window.addEventListener("trocai-sessao-alterada", atualizar);
    return () => window.removeEventListener("trocai-sessao-alterada", atualizar);
  }, []);

  const encerrarSessao = async () => {
    try {
      await sair();
      setUsuario(null);
      navigate("/login");
    } catch (err) {
      setErroSessao(err.message);
    }
  };

  return (
    <>
      <header className="topo">
        <NavLink className="marca" to="/">
          Troc<span>.ai</span>
        </NavLink>
        <nav>
          <NavLink to="/" end>Buscar</NavLink>
          <NavLink to="/cadastro">Cadastrar</NavLink>
          <NavLink to="/match">Deu Match</NavLink>
          {usuario ? (
            <button className="botao-nav" type="button" onClick={encerrarSessao}>
              Sair ({usuario.nome})
            </button>
          ) : (
            <NavLink to="/login">Entrar</NavLink>
          )}
        </nav>
      </header>
      <main className="conteudo">
        {erroSessao && <div className="alerta erro" role="alert">{erroSessao}</div>}
        <Routes>
          <Route path="/" element={<Busca usuario={usuario} />} />
          <Route path="/cadastro" element={<Cadastro />} />
          <Route path="/login" element={usuario ? <p>Você já está conectado.</p> : <Login />} />
          <Route path="/match" element={<Match usuario={usuario} />} />
          <Route path="*" element={<p>Página não encontrada. <Link to="/">Voltar à busca</Link>.</p>} />
        </Routes>
      </main>
    </>
  );
}
