import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { entrar, notificarMudancaSessao } from "../api.js";

export default function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const navigate = useNavigate();

  const enviar = async (e) => {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      await entrar({ email, senha });
      notificarMudancaSessao();
      navigate("/");
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <h1>Entrar</h1>
      <p className="sub">Acesse seu perfil para conectar com outras pessoas.</p>
      {erro && <div className="alerta erro" role="alert">{erro}</div>}
      <form className="cartao form formulario-curto" onSubmit={enviar}>
        <label>E-mail
          <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>Senha
          <input type="password" autoComplete="current-password" value={senha} onChange={(e) => setSenha(e.target.value)} required />
        </label>
        <button type="submit" disabled={enviando}>
          {enviando ? "Entrando..." : "Entrar"}
        </button>
      </form>
      <p>Ainda não tem perfil? <Link to="/cadastro">Cadastre-se</Link>.</p>
    </>
  );
}
