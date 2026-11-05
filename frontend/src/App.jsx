import { NavLink, Route, Routes } from "react-router-dom";
import Busca from "./pages/Busca.jsx";
import Cadastro from "./pages/Cadastro.jsx";
import Match from "./pages/Match.jsx";

export default function App() {
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
        </nav>
      </header>
      <main className="conteudo">
        <Routes>
          <Route path="/" element={<Busca />} />
          <Route path="/cadastro" element={<Cadastro />} />
          <Route path="/match" element={<Match />} />
        </Routes>
      </main>
    </>
  );
}
