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
 * A visualização de uma landing. Padrão `PageView` do Meta — o evento que
 * toda campanha usa como denominador.
 *
 * `chave` é o que torna a visualização única (a variante da landing). Chamar
 * duas vezes com a mesma chave não dispara duas vezes.
 */
export function visualizacao(chave) {
  if (jaVistas.has(chave)) return;
  jaVistas.add(chave);
  carregar();
  disparar("PageView");
}

/**
 * Um evento de conversão da landing. Hoje só um: o clique no CTA.
 *
 * Nome customizado (`trackCustom`) e não um padrão do Meta de propósito —
 * `Lead` significa cadastro concluído, e usá-lo para um clique inflaria a
 * conversão do anúncio com gente que só tocou no botão. O cadastro em si
 * acontece em `/login`, fora destas páginas, e quando houver evento para ele
 * é aqui que ele entra.
 */
export function evento(nome, dados = {}) {
  disparar(nome, dados, true);
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
