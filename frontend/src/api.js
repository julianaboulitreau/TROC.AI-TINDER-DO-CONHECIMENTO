// Chamadas à API do backend (o Vite encaminha /api para http://localhost:3001).
async function pedir(url, opcoes) {
  const r = await fetch(url, opcoes);
  const dados = await r.json();
  if (!r.ok) throw new Error(dados.erro || "Erro na requisição");
  return dados;
}

export const obterOpcoes = () => pedir("/api/opcoes");
export const buscar = (q, tipo) =>
  pedir(`/api/conhecimentos?q=${encodeURIComponent(q)}&tipo=${encodeURIComponent(tipo)}`);
export const cadastrar = (dados) =>
  pedir("/api/conhecimentos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
export const obterMatches = () => pedir("/api/match");
