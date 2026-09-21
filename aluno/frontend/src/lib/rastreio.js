/**
 * O RASTREIO DAS LANDINGS DE ANÚNCIO — uma porta só.
 *
 * O produto **não tinha nenhum analytics de frontend** antes disto: nem Meta
 * Pixel, nem Google Analytics, nem tag manager. O que existia (e continua
 * existindo, e é reaproveitado aqui) é o funil próprio no backend —
 * `POST /track/click` → `growth_events` → `campaigns.resumo_comparativo`.
 *
 * Este módulo existe para que a chegada do Pixel não se espalhe pelas telas.
 * A regra é: **nenhum componente chama `fbq`**. Os componentes chamam
 * `evento()`, e é aqui que se decide para onde isso vai. No dia em que entrar
 * Meta CAPI, GA4 ou outro destino, muda este arquivo e mais nenhum — é a mesma
 * disciplina de `lib/monitoring.reportarErro`.
 *
 * ---------------------------------------------------------------------------
 * O PIXEL NÃO CARREGA SEM UM ID CONFIGURADO, E ISSO É DELIBERADO
 * ---------------------------------------------------------------------------
 *
 * `REACT_APP_META_PIXEL_ID` não existe em nenhum `.env` hoje. Sem ele este
 * módulo é inerte: zero JavaScript de terceiro, zero requisição, zero cookie.
 * Duas razões, e as duas pesam:
 *
 * - **Performance.** O `fbevents.js` é script de terceiro num produto cuja
 *   landing de anúncio tem de abrir rápido no 4G. Ele nunca entra no caminho
 *   crítico: só é injetado depois da primeira pintura (ver `carregar`).
 * - **LGPD.** O Sapiens atende menor de idade e tem política de privacidade
 *   publicada. Ligar rastreio de terceiro é decisão do dono com revisão
 *   jurídica, não efeito colateral de um deploy de frontend. Preencher a
 *   variável é o ato explícito que liga.
 *
 * E o pixel só é carregado nas rotas `/ads/*` — nunca dentro do app do aluno.
 * Rastreio de anúncio não tem o que fazer numa tela de estudo, e colocá-lo lá
 * seria trocar privacidade e peso por um dado que ninguém pediu.
 */

const PIXEL_ID = process.env.REACT_APP_META_PIXEL_ID;

let carregado = false;
// Um `PageView` por página vista, nunca dois. O `useEffect` do React roda
// duas vezes no StrictMode do desenvolvimento, e uma remontagem da rota
// (troca de variante) não pode virar duas visualizações no relatório.
const jaVistas = new Set();

/** O pixel está configurado? Falso hoje, e é o estado esperado. */
export function pixelAtivo() {
  return Boolean(PIXEL_ID);
}

/** Injeta o `fbevents.js` uma vez, fora do caminho crítico. */
function carregar() {
  if (carregado || !PIXEL_ID || typeof window === "undefined") return;
  carregado = true;

  // O trecho oficial do Meta, reescrito legível. `fbq` precisa existir e
  // enfileirar ANTES de o script chegar, senão os eventos disparados durante
  // o download se perdem.
  const fbq = function (...args) {
    if (fbq.callMethod) fbq.callMethod(...args);
    else fbq.queue.push(args);
  };
  fbq.queue = [];
  fbq.loaded = true;
  fbq.version = "2.0";
  window.fbq = window._fbq = fbq;

  fbq("init", PIXEL_ID);

  const injetar = () => {
    const s = document.createElement("script");
    s.async = true;
    s.src = "https://connect.facebook.net/en_US/fbevents.js";
    document.head.appendChild(s);
  };

  // Depois da primeira pintura, sempre. `requestIdleCallback` não existe no
  // Safari — o `setTimeout` é o caminho real no iPhone, não o plano B.
  if (typeof window.requestIdleCallback === "function") {
    window.requestIdleCallback(injetar, { timeout: 3000 });
  } else {
    setTimeout(injetar, 1200);
  }
}

/**
 * O VOCABULÁRIO DE EVENTOS DESTAS PÁGINAS. Três, e só três.
 *
 * Nomes customizados (`trackCustom`) e não padrões do Meta, de propósito:
 * `Lead` significa cadastro CONCLUÍDO, e usá-lo para um clique inflaria a
 * conversão do anúncio com gente que só tocou no botão — depois é o
 * algoritmo do Meta que otimiza em cima dessa mentira.
 *
 * | evento                     | quando                                    |
 * |----------------------------|-------------------------------------------|
 * | `landing_view`             | a landing abriu (uma vez por variante)    |
 * | `landing_demo_interaction` | a pessoa TOCOU na demonstração            |
 * | `landing_cta_click`        | clique no CTA, com a posição na página    |
 *
 * **`landing_signup_start` não existe aqui, e a ausência é decisão.** Ele
 * aconteceria em `/login`, que é tela do produto e não landing. Instrumentá-lo
 * exigiria importar este módulo dentro de `Login.jsx` — espalhar analytics
 * pelo app por um sinal que, hoje, é indistinguível de `landing_cta_click`:
 * o CTA navega direto para o cadastro, sem tela intermediária onde alguém
 * possa desistir. Quando houver etapa no meio (ou quando o pixel estiver
 * ligado e a diferença virar mensurável), ele entra AQUI e é chamado de lá.
 *
 * `landing_demo_interaction` só tem emissor em `/ads/10-questoes`: é a única
 * das quatro demos em que existe algo a tocar. Nas outras três a demonstração
 * roda sozinha, e um "interagiu" disparado por scroll mediria rolagem, não
 * interesse.
 */
export function evento(nome, dados = {}) {
  disparar(nome, dados, true);
}

/** A landing abriu. Dispara o `PageView` (o denominador de toda campanha) e
 *  o evento nomeado, uma vez só por variante. */
export function landingView(variante) {
  if (jaVistas.has(variante)) return;
  jaVistas.add(variante);
  carregar();
  disparar("PageView");
  evento("landing_view", { variante });
}

/** A pessoa tocou na demonstração. `escolha` é a alternativa que ela marcou —
 *  é dado do criativo, não da pessoa, e não identifica ninguém. */
export function demoInteragida(variante, escolha) {
  evento("landing_demo_interaction", { variante, escolha });
}

/** Clique no CTA. `posicao` é o que diz se a página converte na primeira
 *  dobra ou só depois da demonstração — sem isso só se sabe o total. */
export function ctaClicado(variante, posicao) {
  evento("landing_cta_click", { variante, posicao });
}

function disparar(nome, dados = {}, custom = false) {
  if (!PIXEL_ID || typeof window === "undefined") return;
  try {
    window.fbq?.(custom ? "trackCustom" : "track", nome, dados);
  } catch {
    // Rastreio nunca derruba a página. Mesma regra de `monitoring.js`: um erro
    // dentro do medidor não pode virar o erro visível.
  }
}
