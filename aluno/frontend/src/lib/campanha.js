/**
 * A ORIGEM DO TRÁFEGO — capturar, preservar, repassar.
 *
 * As landings de anúncio (`/ads/*`) recebem gente que o Sapiens nunca viu, e
 * a única coisa que diz de onde essa pessoa veio é a query da URL. Se ela se
 * perder no primeiro clique, o anúncio que trouxe o cadastro deixa de ser
 * conhecível — e sem isso não existe comparação entre criativos.
 *
 * Quatro coisas moram aqui, e só quatro:
 *
 * 1. `lerOrigem` — o que a URL trouxe.
 * 2. `salvarOrigem` / `origemSalva` — a janela de 30 dias no `localStorage`.
 * 3. `destinoComOrigem` — a URL do CTA, com a origem colada nela.
 * 4. `origemParaEnvio` — o objeto que `Login.jsx` manda no cadastro.
 *
 * ---------------------------------------------------------------------------
 * POR QUE A QUERY INTEIRA VIAJA, E NÃO SÓ AS CHAVES QUE O PRODUTO LÊ HOJE
 * ---------------------------------------------------------------------------
 *
 * Hoje o cadastro lê exatamente um parâmetro (`convite`, ver `lib/atribuicao`)
 * e o rastreio de clique lê `campanha_id`. Os `utm_*` e o `fbclid` não são
 * lidos por ninguém ainda. Uma lista branca com só o que é lido hoje parece
 * mais limpa e é pior: no dia em que o backend passar a gravar a origem no
 * cadastro, o parâmetro já teria sido descartado três telas antes, e o
 * conserto seria refazer isto em vez de ler um campo que já chegou.
 *
 * Então a regra é: **a query de origem viaja inteira até o cadastro**. O que
 * ninguém lê não custa nada; o que foi jogado fora custa uma campanha.
 *
 * ---------------------------------------------------------------------------
 * A JANELA DE 30 DIAS É EMPRESTADA, NÃO INVENTADA
 * ---------------------------------------------------------------------------
 *
 * `lib/atribuicao.js` já resolve "clicou hoje, cadastrou daqui a duas semanas"
 * para o programa de afiliados, com `localStorage`, 30 dias e degradação
 * silenciosa. Este módulo usa a MESMA janela e a MESMA disciplina, em chave
 * própria: aba anônima ou storage bloqueado = sem memória, nunca erro. E,
 * igual lá, isto **nunca é fonte de verdade** — quem decide é o que está na
 * URL no momento do POST.
 */
import { ROTAS } from "./rotas";

const CHAVE = "sapiens_origem";
const JANELA_DIAS = 30;

/**
 * Os parâmetros de origem que a janela guarda.
 *
 * `convite` NÃO está aqui de propósito: ele já tem dono (`lib/atribuicao.js`,
 * com a mesma janela de 30 dias) e duas cópias do mesmo código em dois
 * `localStorage` diferentes divergiriam no dia em que uma delas expirasse
 * antes da outra. Ele continua viajando na URL — ver `destinoComOrigem` —,
 * só não é guardado duas vezes.
 */
export const PARAMS_DE_ORIGEM = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
  // O id da campanha do catálogo do admin (`campaigns.criar` gera
  // `camp_<hex>`). É o ÚNICO parâmetro que o backend sabe pendurar num
  // funil hoje, via `POST /track/click`.
  "campanha_id",
  // O clique do Meta. Não é lido por nada ainda; é o que uma integração de
  // CAPI precisaria para não contar o mesmo cadastro duas vezes.
  "fbclid",
];

/** O que a URL trouxe, só as chaves conhecidas e só as que vieram. */
export function lerOrigem(search) {
  const params = new URLSearchParams(search || "");
  const origem = {};
  for (const chave of PARAMS_DE_ORIGEM) {
    const valor = (params.get(chave) || "").trim();
    if (valor) origem[chave] = valor.slice(0, 200);
  }
  return origem;
}

/** Guarda por 30 dias. Sem origem nenhuma, não apaga o que já havia: chegar
 *  pela mesma landing sem UTM (um link colado no WhatsApp, por exemplo) não
 *  pode apagar a campanha que trouxe a pessoa da primeira vez. */
export function salvarOrigem(origem) {
  if (!origem || Object.keys(origem).length === 0) return;
  try {
    localStorage.setItem(CHAVE, JSON.stringify({
      ...origem,
      expira_em: Date.now() + JANELA_DIAS * 86400000,
    }));
  } catch { /* storage bloqueado — degradação silenciosa */ }
}

export function origemSalva() {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return null;
    const { expira_em, ...origem } = JSON.parse(bruto) || {};
    if (!expira_em || expira_em < Date.now()) return null;
    return Object.keys(origem).length ? origem : null;
  } catch {
    return null;
  }
}

/**
 * O endereço para onde o CTA leva, carregando a origem.
 *
 * A query DA URL vence a guardada: se a pessoa está chegando por um anúncio
 * agora, é esse anúncio que trouxe este cadastro, não o de duas semanas atrás.
 * A guardada só preenche o que falta.
 *
 * `novo=1` é escrito por último porque é a porta que `Login.jsx` lê para abrir
 * em "Criar conta" em vez de "Entrar" — quem clicou num anúncio está
 * chegando, e pedir a senha de uma conta que não existe é perder a pessoa na
 * tela seguinte.
 */
export function destinoComOrigem(search, { rota = ROTAS.LOGIN, salva = null } = {}) {
  const params = new URLSearchParams(search || "");
  for (const [chave, valor] of Object.entries(salva || {})) {
    if (!params.get(chave)) params.set(chave, valor);
  }
  params.set("novo", "1");
  const query = params.toString();
  return `${rota}${query ? `?${query}` : ""}`;
}

/**
 * A origem a mandar no `/auth/signup` (ou `/auth/google`): mesma regra de
 * precedência de `destinoComOrigem` — a URL vence, o que estava guardado
 * preenche o resto —, mas devolve o objeto pronto para o payload em vez de
 * montar uma URL. É o elo que fechava a ponta descrita no header deste
 * arquivo: até aqui a origem chegava na URL do `/login` e parava.
 */
export function origemParaEnvio(search) {
  return { ...(origemSalva() || {}), ...lerOrigem(search) };
}
