/**
 * "Lembrar-me com a Mentis" — as decisões que a camada de captura precisa
 * tomar, fora do React para poderem ser testadas.
 *
 * Quem usa isto é `components/LembrarComAMentis.jsx`, que é montado UMA vez em
 * `App.js` e vale para o produto inteiro. O motivo de a lógica morar aqui e
 * não lá é o de sempre nesta casa: o que decide se um gesto vira cobrança de
 * 10 Sparks tem de ser verificável sem navegador.
 */

/**
 * "Alguém acabou de guardar (ou tirar) um lembrete."
 *
 * Um evento de janela, e não um contexto de React, pelo mesmo motivo do
 * `EVENTO_SPARKS` da barra: quem captura é uma camada global montada em
 * `App.js`, e quem mostra a fila é uma seção lá no fim da aba de Revisões. Um
 * provedor ligando os dois seria mais encanamento do que problema.
 *
 * Sem isto, marcar um trecho ESTANDO na aba de Revisões não mudava nada na
 * tela: a lista tinha carregado no `mount` e continuava dizendo "você ainda
 * não marcou nada" logo abaixo do toast que dizia que sim.
 */
export const EVENTO_LEMBRETES = "lembretes:mudou";

export function avisarLembretesMudou() {
  window.dispatchEvent(new Event(EVENTO_LEMBRETES));
}

/** Abaixo disto não há o que rever — e o servidor recusa igual
 *  (`lembretes_routes.MIN_TEXTO`). Repetido aqui para o botão nem aparecer:
 *  oferecer um botão que o servidor vai recusar é pior que não oferecer. */
export const MIN_TEXTO = 3;

/** O mesmo teto do servidor (`lembretes_routes.MAX_TEXTO`). O corte acontece
 *  lá; aqui serve só para o preview não crescer sem fim. */
export const MAX_TEXTO = 1200;

/** Campos em que selecionar texto NÃO é marcar conteúdo — é editar.
 *  Um aluno que seleciona o que acabou de escrever na redação para apagar não
 *  pode ver um botão de 10 Sparks aparecendo sobre a própria frase. */
const EDITAVEIS = new Set(["INPUT", "TEXTAREA", "SELECT", "OPTION"]);

/** Onde o botão não entra, porque a tela já é uma conversa com a Mentis (ou
 *  não tem aluno logado). Mesmas exclusões do `MentisWidget`, mais as telas
 *  públicas: marcar um trecho da landing não tem fila para onde ir. */
const ROTAS_SEM_CAPTURA = [
  "/mentis",
  "/bem-vindo",
  "/feed",
  "/login",
  "/cadastro",
  "/esqueci-senha",
  "/redefinir-senha",
  "/completar-cadastro",
];

export function rotaAceitaCaptura(pathname) {
  const rota = pathname || "/";
  if (rota === "/") return false;
  return !ROTAS_SEM_CAPTURA.some((r) => rota === r || rota.startsWith(`${r}/`));
}

/** O texto como ele conta para a IDENTIDADE — o espelho exato de
 *  `lembretes_routes.normalizar`. O cliente usa isto só para saber se ESTE
 *  trecho já está na fila (e então mostrar "já guardado" em vez de um preço);
 *  quem decide de verdade continua sendo o servidor. */
export function normalizar(texto) {
  return (texto || "").replace(/\s+/g, " ").trim().toLocaleLowerCase();
}

export function textoSuficiente(texto) {
  return normalizar(texto).length >= MIN_TEXTO;
}

/** O elemento está dentro de um campo editável (ou de um `contenteditable`)? */
export function dentroDeCampo(no) {
  let atual = no && no.nodeType === 3 ? no.parentElement : no;
  while (atual) {
    if (EDITAVEIS.has(atual.tagName)) return true;
    if (atual.isContentEditable) return true;
    // A própria camada de captura: selecionar o texto DO botão não pode
    // reabrir o botão.
    if (atual.dataset && atual.dataset.lembrarUi === "1") return true;
    atual = atual.parentElement;
  }
  return false;
}

/**
 * Onde desenhar o botão, em coordenadas de viewport (`position: fixed`).
 *
 * Três regras, e todas nasceram de um defeito real do produto:
 *
 * 1. **No toque, por baixo da seleção.** iOS e Android desenham o próprio
 *    balão de "Copiar/Compartilhar" ACIMA do trecho selecionado. Um botão
 *    nosso no mesmo lugar fica atrás dele ou disputa o polegar com ele.
 * 2. **Nunca encostando na borda.** `MARGEM` de cada lado, senão o botão
 *    nasce metade fora da tela quando a seleção começa na margem.
 * 3. **Fora da zona morta do ícone da Mentis** (`fixed bottom-5 right-5`,
 *    56px — ver `project_aluno_mobile_invariantes`). Uma seleção no rodapé à
 *    direita colocaria o botão exatamente debaixo do mascote, que é o defeito
 *    que a auditoria de 12/09 encontrou em cinco telas.
 */
/** O aparelho é de TOQUE?
 *
 *  Decidido pelo ponteiro, e não pelo evento que por acaso disparou. Um
 *  `touchend` prova que houve toque, mas a ausência dele não prova o
 *  contrário: um celular que recebe a seleção por um caminho que termina em
 *  `mouseup` (teclado, menu do sistema, um navegador que sintetiza o evento)
 *  ganharia o botão do lado ERRADO — bem onde iOS e Android desenham o balão
 *  nativo de "Copiar". `pointer: coarse` é a mesma pergunta que o `index.css`
 *  já faz para fechar os hovers em tela de toque. */
export function pontoGrosso() {
  try {
    return window.matchMedia?.("(pointer: coarse)")?.matches === true;
  } catch {
    return false;
  }
}

export const MARGEM = 12;
const FOLGA = 10;
const ZONA_MENTIS = { largura: 96, altura: 96 };

export function posicionarBotao(alvo, janela) {
  const { vw, vh, largura, altura, toque = false } = janela;

  let x = alvo.left + alvo.width / 2 - largura / 2;
  x = Math.min(Math.max(x, MARGEM), Math.max(MARGEM, vw - largura - MARGEM));

  const acima = alvo.top - altura - FOLGA;
  const abaixo = alvo.bottom + FOLGA;
  const cabeAcima = acima >= MARGEM;
  const cabeAbaixo = abaixo + altura <= vh - MARGEM;

  // No toque a preferência se inverte (regra 1); no mouse, acima é melhor
  // porque o cursor está embaixo, sobre o fim da seleção.
  let y;
  if (toque) y = cabeAbaixo ? abaixo : cabeAcima ? acima : abaixo;
  else y = cabeAcima ? acima : cabeAbaixo ? abaixo : acima;
  y = Math.min(Math.max(y, MARGEM), Math.max(MARGEM, vh - altura - MARGEM));

  // Regra 3: se o botão terminaria dentro do quadrado do mascote, ele anda
  // para a esquerda o suficiente para sair dali — nunca para cima, porque
  // subir o afastaria do trecho que ele descreve.
  const invadeMentis =
    x + largura > vw - ZONA_MENTIS.largura && y + altura > vh - ZONA_MENTIS.altura;
  if (invadeMentis) {
    x = Math.max(MARGEM, vw - ZONA_MENTIS.largura - largura - FOLGA);
  }

  return { x: Math.round(x), y: Math.round(y) };
}

/** O retângulo que a seleção ocupa, unindo todos os pedaços dela.
 *
 *  `getBoundingClientRect()` do Range já faria isso, mas devolve um retângulo
 *  de altura zero quando a seleção termina numa quebra de linha — e aí o botão
 *  aparece colado no topo da página, longe do texto. Somar os retângulos dos
 *  pedaços é o que sobrevive à seleção de várias linhas. */
export function retanguloDaSelecao(range) {
  const pedacos = Array.from(range.getClientRects()).filter((r) => r.width > 0 || r.height > 0);
  const base = pedacos.length ? pedacos : [range.getBoundingClientRect()];
  const left = Math.min(...base.map((r) => r.left));
  const right = Math.max(...base.map((r) => r.right));
  const top = Math.min(...base.map((r) => r.top));
  const bottom = Math.max(...base.map((r) => r.bottom));
  return { left, top, right, bottom, width: right - left, height: bottom - top };
}

/** O que vai para o servidor. `rota` entra na identidade do lembrete (é parte
 *  do hash no `_id`), então ela é o `pathname` limpo — sem query nem hash, que
 *  mudam entre visitas à mesma tela e fariam o mesmo trecho ser cobrado duas
 *  vezes. */
export function montarPayload({ texto, pathname, titulo, contexto, tipo = "texto", ref = "" }) {
  return {
    texto: (texto || "").trim().slice(0, MAX_TEXTO),
    rota: (pathname || "").split("?")[0].split("#")[0],
    titulo: (titulo || "").trim().slice(0, 200),
    contexto: (contexto || "").trim().slice(0, 400),
    tipo,
    ref: (ref || "").slice(0, 200),
  };
}

/** O preview do trecho no botão e na fila: uma linha, sem quebra, com
 *  reticências de verdade quando não cabe. */
export function resumir(texto, limite = 90) {
  const limpo = (texto || "").replace(/\s+/g, " ").trim();
  return limpo.length > limite ? `${limpo.slice(0, limite - 1)}…` : limpo;
}

/** Um objeto marcado com `data-lembrar` vira lembrete com o mesmo formato de
 *  uma seleção. O atributo carrega a descrição do objeto porque um `<img>` ou
 *  um card não têm texto que sirva sozinho — quem marca a tela escreve o que
 *  aquele objeto É. */
export function lembravelMaisProximo(elemento) {
  let atual = elemento;
  while (atual && atual.dataset) {
    if (atual.dataset.lembrar) {
      return {
        texto: atual.dataset.lembrar,
        ref: atual.dataset.lembrarRef || "",
        elemento: atual,
      };
    }
    atual = atual.parentElement;
  }
  return null;
}
