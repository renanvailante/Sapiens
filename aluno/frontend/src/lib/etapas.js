/**
 * A ESTAÇÃO EM ETAPAS — uma tela de cada vez, com "Continuar" entre elas.
 *
 * A estação chega do servidor como uma lista de blocos e antes era desenhada
 * inteira numa página que se rolava. Funciona, e é exatamente o formato que
 * faz alguém abrir uma aula, ver quarenta telas de rolagem e fechar. O que
 * muda aqui não é o conteúdo: é o RITMO.
 *
 *     explicação  →  exemplos resolvidos  →  5 exercícios  →  5 exercícios
 *
 * Cada trecho cabe numa tela, termina num botão e dá a sensação de terminar
 * alguma coisa — o empréstimo é declarado (Duolingo), e a razão pela qual
 * funciona é velha: uma tarefa com fim visível é uma tarefa que se começa.
 *
 * **Isto é paginação, não pedagogia.** Por isso mora no cliente: o servidor
 * não tem opinião sobre quantos exercícios cabem numa tela, e o contrato de
 * conteúdo continua sendo uma lista de blocos. Um curso novo, com outra
 * mistura de blocos, é dividido pelas mesmas regras sem ninguém reescrever
 * nada.
 *
 * Lógica pura, sem React, testada em `etapas.test.js`.
 */

/** Quantos exercícios por tela. Cinco é o maior número que ainda cabe numa
 *  tela de celular sem rolagem longa, e o menor que ainda parece um treino
 *  em vez de uma pergunta solta. */
export const EXERCICIOS_POR_ETAPA = 5;

const EXERCICIO = new Set(["exercicio", "desafio"]);

/**
 * Divide os blocos da estação em etapas.
 *
 * As regras, em ordem:
 *
 * 1. tudo que vem ANTES do primeiro exemplo e não é exercício → *explicação*;
 * 2. os exemplos resolvidos, mais o que vier depois deles e ainda não for
 *    exercício (estratégias, erros comuns, vídeo) → *exemplos*. Lê como uma
 *    aula: o modelo resolvido, e então o que generalizar dele;
 * 3. os exercícios, em blocos de cinco, na ordem do conteúdo — que é a ordem
 *    do fácil ao difícil garantida pelo validador do servidor.
 *
 * Etapa vazia não é criada. Uma estação só de exercícios (revisão) vira
 * só etapas de exercício, sem tela de explicação vazia no começo.
 */
export function dividirEmEtapas(blocos = []) {
  const lista = Array.isArray(blocos) ? blocos : [];
  const exercicios = lista.filter((b) => EXERCICIO.has(b.tipo));
  const estudo = lista.filter((b) => !EXERCICIO.has(b.tipo));

  const primeiroExemplo = estudo.findIndex((b) => b.tipo === "exemplo");
  const corte = primeiroExemplo === -1 ? estudo.length : primeiroExemplo;

  const etapas = [];
  const explicacao = estudo.slice(0, corte);
  if (explicacao.length) {
    etapas.push({ tipo: "explicacao", rotulo: "Entender", blocos: explicacao });
  }
  const exemplos = estudo.slice(corte);
  if (exemplos.length) {
    etapas.push({ tipo: "exemplos", rotulo: "Ver resolvido", blocos: exemplos });
  }
  for (let i = 0; i < exercicios.length; i += EXERCICIOS_POR_ETAPA) {
    const parte = exercicios.slice(i, i + EXERCICIOS_POR_ETAPA);
    etapas.push({
      tipo: "exercicios",
      rotulo: exercicios.length > EXERCICIOS_POR_ETAPA
        ? `Praticar ${Math.floor(i / EXERCICIOS_POR_ETAPA) + 1}`
        : "Praticar",
      blocos: parte,
    });
  }

  return etapas.map((e, i) => ({ ...e, indice: i, total: etapas.length }));
}

/**
 * A etapa de exercícios só libera o "Continuar" depois de TODAS respondidas —
 * certas ou erradas.
 *
 * Exigir acerto transformaria a etapa num muro (é para isso que existe a
 * escada de devolutiva, que termina entregando a resolução). Não exigir nada
 * transformaria o botão num "pular", e aí a divisão em etapas não teria
 * servido para nada.
 */
export function etapaCumprida(etapa, respostas = {}) {
  if (!etapa) return false;
  if (etapa.tipo !== "exercicios") return true;
  return etapa.blocos.every((b) => (respostas[b.bloco_id]?.tentativas || 0) > 0);
}

/** Por onde retomar: a primeira etapa ainda não cumprida.
 *
 *  Quem volta a uma estação começada não quer reler a explicação — quer
 *  cair onde parou. Etapas de leitura contam como cumpridas quando já foram
 *  vistas, e é o que permite a retomada acertar o alvo. */
export function etapaParaRetomar(etapas, respostas = {}, vistos = []) {
  const jaVistos = new Set(vistos);
  for (const etapa of etapas) {
    if (etapa.tipo === "exercicios") {
      if (!etapaCumprida(etapa, respostas)) return etapa.indice;
    } else if (!etapa.blocos.every((b) => jaVistos.has(b.bloco_id))) {
      return etapa.indice;
    }
  }
  return Math.max(0, etapas.length - 1);
}

/**
 * O PROGRESSO DE CADA ETAPA, num formato que a tela só precisa desenhar.
 *
 * Existe porque o progresso da estação estava espalhado: um contador de
 * acertos no cabeçalho, uma régua de segmentos no topo e um conjunto de
 * `if`s dentro da página decidindo o que estava cumprido. Três lugares, três
 * regras parecidas — e "parecidas" é como duas partes da tela passam a
 * discordar sobre a mesma etapa.
 *
 * A mudança de regra que vem junto: **uma etapa de leitura conta como
 * cumprida quando foi LIDA**, e não quando o aluno passou dela. `vistos` já é
 * gravado no servidor a cada bloco que entra na tela, então o estado
 * sobrevive a um recarregamento — antes, quem voltava à estação via as telas
 * de explicação apagadas de novo, como se nunca tivesse lido nada.
 *
 * `feitos/total` é o par que a tela mostra: respostas dadas, em exercício; e
 * blocos lidos, em leitura. Nenhum dos dois é acerto — acerto tem contador
 * próprio, vem do servidor e é o que conclui a estação.
 */
export function progressoDasEtapas(etapas = [], respostas = {}, vistos = []) {
  const jaVistos = new Set(vistos);
  return (etapas || []).map((etapa, i) => {
    const blocos = etapa.blocos || [];
    const exercicios = etapa.tipo === "exercicios";
    const feitos = blocos.filter((b) => (
      exercicios ? (respostas[b.bloco_id]?.tentativas || 0) > 0 : jaVistos.has(b.bloco_id)
    )).length;
    const acertos = exercicios
      ? blocos.filter((b) => respostas[b.bloco_id]?.acertou).length
      : 0;
    return {
      indice: etapa.indice ?? i,
      tipo: etapa.tipo,
      rotulo: etapa.rotulo,
      total: blocos.length,
      feitos,
      acertos,
      // Leitura cumprida = lida inteira. Exercício cumprido = respondido
      // inteiro, certo ou errado (a régua do `etapaCumprida`, que é a mesma
      // que libera o "Continuar").
      cumprida: exercicios ? etapaCumprida(etapa, respostas) : feitos >= blocos.length,
    };
  });
}

/** Os índices das etapas cumpridas — o que a régua de passos pinta. */
export function etapasCumpridas(etapas = [], respostas = {}, vistos = []) {
  return new Set(
    progressoDasEtapas(etapas, respostas, vistos)
      .filter((e) => e.cumprida)
      .map((e) => e.indice),
  );
}
