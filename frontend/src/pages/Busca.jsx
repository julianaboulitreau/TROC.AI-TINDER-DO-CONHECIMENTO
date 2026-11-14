import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buscar, conectarPerfil } from "../api.js";

export default function Busca({ usuario }) {
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState("");
  const [perfis, setPerfis] = useState(null);
  const [erro, setErro] = useState("");
  const [feedback, setFeedback] = useState("");
  const [conectando, setConectando] = useState(null);

  const pesquisar = async (e) => {
    e?.preventDefault();
    setErro("");
    try {
      setPerfis(await buscar(q, tipo));
    } catch (err) {
      setErro(err.message);
    }
  };

  useEffect(() => {
    pesquisar();
  }, [usuario?.id]);

  const conectar = async (perfil) => {
    setConectando(perfil.id);
    setFeedback("");
    setErro("");
    try {
      const resultado = await conectarPerfil(perfil.id);
      setFeedback(resultado.match
        ? `Deu match com ${perfil.nome}!`
        : `Interesse enviado para ${perfil.nome}. Se a pessoa também se conectar, vocês terão um match.`);
      setPerfis((atuais) => atuais?.filter((item) => item.id !== perfil.id) ?? []);
    } catch (err) {
      setErro(err.message);
    } finally {
      setConectando(null);
    }
  };

  return (
    <>
      <h1>Buscar pessoas</h1>
      <p className="sub">Encontre quem ensina o que você quer aprender.</p>
      <form className="busca" onSubmit={pesquisar}>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por habilidade, nome ou cidade"
        />
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Ofertas e demandas</option>
          <option value="oferta">O que as pessoas ensinam</option>
          <option value="demanda">O que as pessoas querem aprender</option>
        </select>
        <button type="submit">Buscar</button>
      </form>

      {erro && <div className="alerta erro" role="alert">{erro}</div>}
      {feedback && <div className="alerta ok" role="status">{feedback}</div>}
      {perfis && perfis.length === 0 && (
        <div className="vazio">Nenhum perfil ativo corresponde à busca.</div>
      )}
      <div className="grade">
        {perfis?.map((perfil) => {
          const ensina = perfil.skills_out;
          const querAprender = perfil.skills_in;
          return (
            <article className="cartao perfil" key={perfil.id}>
              <span className="selo oferta">{perfil.cidade || "Comunidade online"}</span>
              <h2>{perfil.nome}</h2>
              {(perfil.curso || perfil.instituicao) && (
                <p className="detalhe">{[perfil.curso, perfil.instituicao].filter(Boolean).join(" · ")}</p>
              )}
              {perfil.bio && <p>{perfil.bio}</p>}
              <h3>Ensina</h3>
              <p>{ensina.join(", ")}</p>
              <h3>Quer aprender</h3>
              <p>{querAprender.join(", ")}</p>
              {usuario ? (
                <button
                  type="button"
                  disabled={conectando === perfil.id}
                  onClick={() => conectar(perfil)}
                >
                  {conectando === perfil.id ? "Enviando..." : "♡ Conectar"}
                </button>
              ) : (
                <Link to="/login">Entre para se conectar</Link>
              )}
            </article>
          );
        })}
      </div>
    </>
  );
}
