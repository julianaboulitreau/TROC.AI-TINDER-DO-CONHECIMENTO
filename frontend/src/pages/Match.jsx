import { useEffect, useState } from "react";
import { obterMatches } from "../api.js";

// RF-03: tela "Deu Match"
export default function Match() {
  const [matches, setMatches] = useState(null);

  useEffect(() => {
    obterMatches().then(setMatches);
  }, []);

  return (
    <>
      <h1>Deu Match!</h1>
      {matches && matches.length === 0 && (
        <div className="vazio">Ainda não há combinações disponíveis. Cadastre ofertas e demandas para encontrar um match.</div>
      )}
      {matches?.map((m) => (
        <section className="cartao match" key={m.a + m.b}>
          <div className="afinidade">{m.afinidade}%<small>afinidade</small></div>
          <h2>{m.a} ⇄ {m.b}</h2>
          <p className={m.mutuo ? "mutuo" : "parcial"}>
            {m.mutuo ? "Match mútuo: os dois lados podem ensinar e aprender." : "Match parcial: apenas um lado é atendido."}
          </p>
          <ul>
            {m.aEnsina.map((x) => <li key={"a" + x}><strong>{m.a}</strong> oferece <em>{x}</em> e {m.b} deseja aprender.</li>)}
            {m.bEnsina.map((x) => <li key={"b" + x}><strong>{m.b}</strong> oferece <em>{x}</em> e {m.a} deseja aprender.</li>)}
          </ul>
        </section>
      ))}
    </>
  );
}
