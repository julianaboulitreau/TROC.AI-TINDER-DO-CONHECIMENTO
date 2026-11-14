async function pedir(url, opcoes = {}) {
  const resposta = await fetch(url, {
    ...opcoes,
    credentials: "same-origin",
    headers: {
      ...(opcoes.body ? { "Content-Type": "application/json" } : {}),
      ...opcoes.headers,
    },
  });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.erro || "Erro na requisição");
  return dados;
}

export const obterSessao = () => pedir("/api/sessao");
export const obterOpcoes = () => pedir("/api/opcoes");
export const buscar = (q, tipo) =>
  pedir(`/api/conhecimentos?q=${encodeURIComponent(q)}&tipo=${encodeURIComponent(tipo)}`);
export const cadastrar = (dados) =>
  pedir("/api/usuarios", { method: "POST", body: JSON.stringify(dados) });
export const entrar = (dados) =>
  pedir("/api/login", { method: "POST", body: JSON.stringify(dados) });
export const sair = () => pedir("/api/logout", { method: "POST", body: "{}" });
export const obterMatches = () => pedir("/api/match");
export const conectarPerfil = (para_usuario_id) =>
  pedir("/api/interacoes", {
    method: "POST",
    body: JSON.stringify({ para_usuario_id, acao: "CONECTAR" }),
  });

export function notificarMudancaSessao() {
  window.dispatchEvent(new Event("trocai-sessao-alterada"));
}
