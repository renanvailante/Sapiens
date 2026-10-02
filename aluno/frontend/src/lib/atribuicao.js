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

// Só o código é guardado. A janela já carregou junto um `bonus` vindo da URL,
// que a tela exibia como promessa — e que qualquer pessoa editava na barra de
// endereço antes de o valor ser gravado aqui por 30 dias. O valor do bônus
// mora no catálogo do backend e é lido no cadastro; nunca daqui.
export function salvarAtribuicao(codigo) {
  if (!codigo) return;
  try {
    localStorage.setItem(CHAVE, JSON.stringify({
      codigo,
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

/**
 * Em que modo o `/login` abre. Só um pedido EXPLÍCITO de cadastro abre em
 * "Criar conta": o convite que veio na URL (alguém clicou no link de um
 * amigo agora) ou o `?novo=1` do "Começar agora".
 *
 * A atribuição GUARDADA (`lerAtribuicao`, até 30 dias) não decide o modo — ela
 * é a memória de um clique antigo num anúncio, e quem a carrega é muitas
 * vezes alguém que já tem conta e só voltou para entrar. Até 2026-10-02 ela
 * decidia: o botão "Entrar" abria em "Criar conta" com o cupom ADS-RETA
 * preenchido, para o próprio dono do produto. O cupom continua preenchido —
 * para quem trocar para "Criar conta" —, só não sequestra mais a tela.
 */
export function modoInicialDoLogin({ novo = false, conviteDaUrl = "" } = {}) {
  return novo || Boolean(conviteDaUrl) ? "signup" : "login";
}
