import { useEffect, useState } from "react";
import { cadastrar, obterOpcoes } from "../api.js";

const VAZIO = { tipo: "", nome: "", area: "", descricao: "", nivel: "", disponibilidade: "" };

// RF-01: cadastrar oferta ou demanda
export default function Cadastro() {
  const [opcoes, setOpcoes] = useState({ areas: [], niveis: [] });
  const [dados, setDados] = useState(VAZIO);
  const [msg, setMsg] = useState(null); // { tipo: "ok" | "erro", texto }

  useEffect(() => {
    obterOpcoes().then(setOpcoes);
  }, []);

  const mudar = (campo) => (e) => setDados({ ...dados, [campo]: e.target.value });

  const enviar = async (e) => {
    e.preventDefault();
    try {
      const r = await cadastrar(dados); // a validação é feita no servidor
      setMsg({ tipo: "ok", texto: r.mensagem });
      setDados(VAZIO);
      setTimeout(() => setMsg(null), 4000);
    } catch (err) {
      setMsg({ tipo: "erro", texto: err.message });
    }
  };

  return (
    <>
      <h1>Cadastrar oferta ou demanda</h1>
      <p className="sub">Diga o que você sabe ensinar ou o que quer aprender.</p>
      {msg && <div className={`alerta ${msg.tipo}`} role="alert">{msg.texto}</div>}
      <form className="cartao form" onSubmit={enviar} noValidate>
        <label>Tipo de cadastro *
          <div className="opcoes">
            {["Oferta", "Demanda"].map((t) => (
              <label key={t}>
                <input type="radio" name="tipo" value={t} checked={dados.tipo === t} onChange={mudar("tipo")} />
                {t === "Oferta" ? " Oferta (sei ensinar)" : " Demanda (quero aprender)"}
              </label>
            ))}
          </div>
        </label>
        <label>Seu nome *
          <input type="text" value={dados.nome} onChange={mudar("nome")} />
        </label>
        <label>Área de conhecimento *
          <select value={dados.area} onChange={mudar("area")}>
            <option value="">Selecione...</option>
            {opcoes.areas.map((a) => <option key={a}>{a}</option>)}
          </select>
        </label>
        <label>Descrição do conhecimento *
          <textarea rows="3" value={dados.descricao} onChange={mudar("descricao")} />
        </label>
        <label>Nível de conhecimento *
          <select value={dados.nivel} onChange={mudar("nivel")}>
            <option value="">Selecione...</option>
            {opcoes.niveis.map((n) => <option key={n}>{n}</option>)}
          </select>
        </label>
        <label>Disponibilidade *
          <input type="text" placeholder="Ex.: noites e fins de semana" value={dados.disponibilidade} onChange={mudar("disponibilidade")} />
        </label>
        <button type="submit">Cadastrar</button>
      </form>
    </>
  );
}
