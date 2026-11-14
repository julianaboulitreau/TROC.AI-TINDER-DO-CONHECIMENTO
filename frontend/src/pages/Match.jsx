import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { obterMatches } from "../api.js";

export default function Match({ usuario }) {
  const [matches, setMatches] = useState(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    setErro("");
    if (!usuario) {
      setMatches([]);
      return;
    }
    setMatches(null);
    obterMatches()
      .then(setMatches)
      .catch((err) => setErro(err.message));
  }, [usuario?.id]);

  return (
    <>
      <h1>Deu Match!</h1>
      {!usuario && (
        <div className="vazio">
          <p>Entre para ver suas conexões confirmadas.</p>
          <Link to="/login">Entrar</Link>
        </div>
      )}
      {erro && <div className="alerta erro" role="alert">{erro}</div>}
      {usuario && matches?.length === 0 && (
        <div className="vazio">
          Ainda não há matches. Encontre perfis na <Link to="/">busca</Link> e conecte-se.
        </div>
      )}
      {usuario && matches?.map((match) => (
        <section className="cartao match" key={match.match_id}>
          <div className="afinidade">
            {match.indice_afinidade}%<small>afinidade</small>
          </div>
          <h2>{usuario.nome} ⇄ {match.perfil.nome}</h2>
          <p className="mutuo">Conexão confirmada: vocês demonstraram interesse mútuo.</p>
          <p><strong>{match.perfil.nome} ensina:</strong> {match.perfil.skills_out.join(", ")}</p>
          <p><strong>{match.perfil.nome} quer aprender:</strong> {match.perfil.skills_in.join(", ")}</p>
        </section>
      ))}
    </>
  );
}
