/**
 * Janela de atribuição de influencer/campanha — 30 dias.
 *
 * Por que existe: o cadastro só grava `influenciado_por` se o campo de
 * cupom estiver preenchido NA HORA de criar a conta (ver
 * `influencers.resolver_e_registrar_atribuicao`). Alguém que clica no link
 * de um influencer, fecha a aba e volta dias depois para se cadastrar sem
 * `?convite=` na URL perderia a atribuição sem isto — é o "clique → cadastro
 * dentro de uma janela" que o programa de afiliados pede.
 *
 * `localStorage`, por viewer, best-effort: se o navegador bloquear (aba
 * anônima, storage desligado), o cupom simplesmente não sobrevive entre
 * sessões — comportamento degradado, nunca erro.
 */
const CHAVE = "sapiens_atribuicao";
const JANELA_DIAS = 30;

export function salvarAtribuicao(codigo, bonus) {
  if (!codigo) return;
  try {
    localStorage.setItem(CHAVE, JSON.stringify({
      codigo,
      bonus: bonus || null,
      expira_em: Date.now() + JANELA_DIAS * 86400000,
    }));
  } catch { /* storage bloqueado — degradação silenciosa */ }
}

export function lerAtribuicao() {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return null;
    const dado = JSON.parse(bruto);
    if (!dado?.codigo || !dado?.expira_em || dado.expira_em < Date.now()) return null;
    return dado;
  } catch {
    return null;
  }
}
