import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cadastrar, notificarMudancaSessao, obterOpcoes } from "../api.js";

const VAZIO = {
  nome: "",
  email: "",
  senha: "",
  cidade: "",
  zona: "",
  skills_out: [],
  skills_in: [],
};

export default function Cadastro() {
  const [opcoes, setOpcoes] = useState([]);
  const [dados, setDados] = useState(VAZIO);
  const [erroOpcoes, setErroOpcoes] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [salvando, setSalvando] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    obterOpcoes()
      .then((r) => setOpcoes(r.habilidades))
      .catch((err) => setErroOpcoes(err.message));
  }, []);

  const mudar = (campo) => (e) => setDados({ ...dados, [campo]: e.target.value });

  const alternarHabilidade = (campo, nome) => {
    const outroCampo = campo === "skills_out" ? "skills_in" : "skills_out";
    if (dados[outroCampo].includes(nome)) return;
    const habilidades = dados[campo].includes(nome)
      ? dados[campo].filter((item) => item !== nome)
      : [...dados[campo], nome];
    setDados({ ...dados, [campo]: habilidades });
  };

  const enviar = async (e) => {
    e.preventDefault();
    setMensagem("");
    if (dados.skills_out.length < 3 || dados.skills_in.length < 1) {
      setMensagem("Selecione ao menos 3 habilidades para ensinar e 1 para aprender.");
      return;
    }
    setSalvando(true);
    try {
      const resultado = await cadastrar(dados);
      setMensagem(`Bem-vindo(a), ${resultado.usuario.nome}!`);
      notificarMudancaSessao();
      navigate("/");
    } catch (err) {
      setMensagem(err.message);
    } finally {
      setSalvando(false);
    }
  };

  const seletorHabilidades = (campo, titulo, minimo) => (
    <fieldset className="habilidades">
      <legend>{titulo} ({dados[campo].length}/{minimo} mínimo)</legend>
      <div className="lista-habilidades">
        {opcoes.map((habilidade) => {
          const selecionado = dados[campo].includes(habilidade.nome);
          const selecionadoNoOutro = dados[
            campo === "skills_out" ? "skills_in" : "skills_out"
          ].includes(habilidade.nome);
          return (
            <label key={`${campo}-${habilidade.id}`}>
              <input
                type="checkbox"
                checked={selecionado}
                disabled={selecionadoNoOutro}
                onChange={() => alternarHabilidade(campo, habilidade.nome)}
              />
              {habilidade.nome} <small>({habilidade.categoria})</small>
            </label>
          );
        })}
      </div>
    </fieldset>
  );

  return (
    <>
      <h1>Criar perfil</h1>
      <p className="sub">Conte o que pode ensinar e o que deseja aprender.</p>
      {mensagem && <div className="alerta erro" role="alert">{mensagem}</div>}
      {erroOpcoes && <div className="alerta erro" role="alert">{erroOpcoes}</div>}
      <form className="cartao form" onSubmit={enviar}>
        <label>Seu nome *
          <input type="text" autoComplete="name" value={dados.nome} onChange={mudar("nome")} required />
        </label>
        <label>E-mail *
          <input type="email" autoComplete="email" value={dados.email} onChange={mudar("email")} required />
        </label>
        <label>Senha * (mínimo 6 caracteres)
          <input type="password" autoComplete="new-password" value={dados.senha} onChange={mudar("senha")} minLength="6" required />
        </label>
        <label>Cidade
          <input type="text" value={dados.cidade} onChange={mudar("cidade")} />
        </label>
        <label>Zona ou região
          <input type="text" value={dados.zona} onChange={mudar("zona")} />
        </label>
        {seletorHabilidades("skills_out", "O que você pode ensinar", 3)}
        {seletorHabilidades("skills_in", "O que quer aprender", 1)}
        <button type="submit" disabled={
          salvando || Boolean(erroOpcoes) || opcoes.length === 0 ||
          dados.skills_out.length < 3 || dados.skills_in.length < 1
        }>
          {salvando ? "Criando perfil..." : "Criar perfil"}
        </button>
      </form>
    </>
  );
}
