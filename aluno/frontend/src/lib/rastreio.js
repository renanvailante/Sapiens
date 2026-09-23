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
 * `REACT_APP_META_PIXEL_ID` é o que LIGA tudo isto. Sem ele o módulo é inerte:
 * zero JavaScript de terceiro, zero requisição, zero cookie. **Ligado desde
 * 22/09/2026**, por decisão do dono, com o pixel `3603769776438017`; até ali o
 * produto não tinha analytics de frontend nenhum. As duas razões pelas quais
 * a chave de liga/desliga existe continuam valendo, e é por isso que ela não
 * virou código fixo:
 *
 * - **Performance.** O `fbevents.js` é script de terceiro num produto cuja
 *   landing de anúncio tem de abrir rápido no 4G. Ele nunca entra no caminho
 *   crítico: só é injetado depois da primeira pintura (ver `carregar`).
 * - **LGPD.** O Sapiens atende menor de idade e tem política de privacidade
 *   publicada. Ligar rastreio de terceiro é decisão do dono, não efeito
 *   colateral de um deploy de frontend — preencher a variável é o ato
 *   explícito que liga, e esvaziá-la desliga tudo num build, sem precisar
 *   caçar chamada nenhuma pelo código. Duas coisas que o texto da política de
 *   privacidade precisa acompanhar, e que este módulo sozinho não resolve:
 *   dizer que há pixel de terceiro e qual é a base legal dele.
 *
 * ---------------------------------------------------------------------------
 * ONDE O PIXEL CARREGA — e a linha que ele não atravessa (2026-09-22)
 * ---------------------------------------------------------------------------
 *
 * Nas três superfícies PÚBLICAS, e em nenhuma outra:
 *
 * | rota        | quem dispara                                    |
 * |-------------|-------------------------------------------------|
 * | `/ads/*`    | `landingView` (`AdsLandingLayout`)              |
 * | `/`         | `PixelDeRota` (montado no `App`)                |
 * | `/login`    | `PixelDeRota`                                   |
 *
 * **Dentro do app do aluno ele não entra.** Depois do cadastro não há mais
 * campanha a medir e há aluno menor de idade estudando: carregar script de
 * terceiro e cookie da Meta numa tela de estudo trocaria privacidade e peso
 * por um dado que ninguém pediu. `ROTAS_PUBLICAS` abaixo é essa fronteira, e
 * ela é uma lista fechada de propósito — uma regra do tipo "tudo que não é
 * protegido" faria a próxima tela pública nascer com pixel sem ninguém decidir.
 *
 * > A fronteira mora AQUI, não no `index.html`. O snippet oficial do Meta,
 * > colado no HTML, carrega em toda página e dispara `PageView` uma vez só —
 * > numa SPA isso é o pior dos dois mundos: pixel na tela de estudo e funil
 * > cego a partir do segundo clique. Por isso ele não está lá.
 */

const PIXEL_ID = process.env.REACT_APP_META_PIXEL_ID;

let carregado = false;
// Um `PageView` por página vista, nunca dois. O `useEffect` do React roda
// duas vezes no StrictMode do desenvolvimento, e uma remontagem da rota
// (troca de variante) não pode virar duas visualizações no relatório.
const jaVistas = new Set();

/** As rotas públicas fora de `/ads/*` onde o pixel pode carregar.
 *
 *  Lista fechada, e comparada por igualdade exata — `/login/qualquer-coisa`
 *  não entra. As landings de anúncio NÃO estão aqui: elas têm emissor próprio
 *  (`landingView`), que além do `PageView` manda a variante. Repetir `/ads`
 *  nesta lista contaria a visita duas vezes. */
const ROTAS_PUBLICAS = new Set(["/", "/login"]);

/** O pixel está configurado? */
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

/**
 * UMA TELA PÚBLICA FOI VISTA. É o que `components/PixelDeRota.jsx` chama a
 * cada mudança de rota.
 *
 * Devolve `true` quando de fato contou, só para o teste ter o que afirmar.
 *
 * A trava por caminho é a mesma de `landingView`, e pela mesma razão: o
 * `useEffect` roda duas vezes no StrictMode do desenvolvimento. Mas aqui ela
 * é por VISITA e não por vida da aba — ir de `/` para `/login` e voltar são
 * duas visualizações honestas, e é justamente esse vaivém que diz se a
 * pessoa hesitou no cadastro. Quem zera é o próprio componente.
 */
export function paginaPublicaVista(caminho) {
  if (!ROTAS_PUBLICAS.has(caminho)) return false;
  carregar();
  disparar("PageView");
  return true;
}

/**
 * CADASTRO CONCLUÍDO — o `Lead` do Meta, e o único evento deste módulo que
 * nasce DENTRO do produto (`pages/Login.jsx`).
 *
 * Padrão do Meta, e não `trackCustom`: `Lead` é o vocabulário que o
 * Gerenciador de Anúncios entende para otimizar campanha por cadastro. O que
 * o doc deste módulo recusava era usá-lo para um CLIQUE — aqui ele significa
 * exatamente o que o Meta diz que significa: a conta existe.
 *
 * `metodo` é `"email"` ou `"google"` — é dado do fluxo, não da pessoa.
 * **Nada que identifique o aluno sai daqui**: nem e-mail, nem nome, nem
 * telefone, nem `user_id`. O Meta aceitaria (`em`, `ph` com hash), e é
 * exatamente por isso que a recusa precisa estar escrita: o produto atende
 * menor de idade, e mandar dado de contato dele para uma rede de anúncios é
 * uma decisão que ninguém deve poder tomar sem querer.
 *
 * Só conta cadastro de verdade. Ver `conta_criada` em `backend/auth.py`: o
 * botão do Google entra e cadastra pela mesma porta, e sem essa flag todo
 * retorno de um aluno antigo viraria uma conversão nova no relatório.
 */
export function cadastroConcluido(metodo) {
  disparar("Lead", { content_name: metodo });
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
