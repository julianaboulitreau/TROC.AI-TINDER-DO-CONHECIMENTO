import { useEffect, useState } from "react";
import { buscar } from "../api.js";

// RF-02: dashboard de busca
export default function Busca() {
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState("");
  const [itens, setItens] = useState(null);
  const [erro, setErro] = useState("");

  const pesquisar = (e) => {
    e?.preventDefault();
    buscar(q, tipo).then(setItens).catch((err) => setErro(err.message));
  };

  useEffect(pesquisar, []); // carrega tudo ao abrir a tela

  return (
    <>
      <h1>Dashboard de busca</h1>
      <form className="busca" onSubmit={pesquisar}>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Pesquisar por área ou conhecimento (ex.: Python, Design)"
        />
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Ofertas e demandas</option>
          <option value="Oferta">Ofertas</option>
          <option value="Demanda">Demandas</option>
        </select>
        <button type="submit">Buscar</button>
      </form>

      {erro && <div className="alerta erro">{erro}</div>}
      {itens && itens.length === 0 && <div className="vazio">Nenhuma correspondência foi encontrada.</div>}
      <div className="grade">
        {itens?.map((i) => (
          <article className="cartao" key={i.id}>
            <span className={`selo ${i.tipo.toLowerCase()}`}>{i.tipo}</span>
            <h3>{i.area}</h3>
            <p>{i.descricao}</p>
            <small>{i.nome} · {i.nivel} · {i.disponibilidade}</small>
          </article>
        ))}
      </div>
    </>
  );
}
