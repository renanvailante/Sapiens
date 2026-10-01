import { ROTAS } from "./rotas";

/**
 * PRÁTICA DIRIGIDA — o erro virando sequência.
 *
 * O motor cognitivo já sabia, para cada aluno, onde os erros começam
 * (`/motor/perfil`) e já montava, para cada ponto, um plano com questões
 * inéditas que exercitam exatamente aquele raciocínio e um objetivo escrito à
 * mão (`/motor/habilidade/:processo`, `intervencoes.montar`). Nenhuma tela
 * chamava esse plano. O aluno errava, lia o veredito e recebia "próxima
 * questão" — a mesma prova, na ordem da prova, como se o erro não tivesse
 * acontecido.
 *
 * Este módulo liga as três pontas que já existiam, sem requisição nova no
 * carregamento de tela nenhuma:
 *
 *   1. `escolherPadrao` — qual ponto o Próximo Passo anuncia (Hoje);
 *   2. `montarPraticaDirigida` — o plano do motor vira um endereço de prática
 *      (`/estudar/provas?item_ids=…`) com o PORQUÊ viajando junto, no `state`
 *      da navegação, para a tela de questões explicar a escolha;
 *   3. `resumoDaSerie` / `pontoRepetido` — o fechamento compara o que saiu
 *      agora com o histórico daquele ponto e aponta o próximo passo.
 *
 * O plano só é buscado no CLIQUE (`abrirPraticaDirigida`). Buscá-lo ao abrir
 * o Hoje seria pagar uma chamada por visita para um botão que a maioria das
 * visitas não aperta.
 *
 * Nada aqui atribui causa a uma resposta individual, e nada afirma que o
 * aluno melhorou por causa da prática: o fechamento DESCREVE (antes X%,
 * agora Y de Z), que é o que o portão de crença desligado permite.
 */

/** Uma série curta: cinco questões do ENEM cabem numa pausa de estudo. */
export const TETO_QUESTOES = 5;

/** Abaixo disto, comparar percentuais é comparar ruído. */
export const MIN_PARA_COMPARAR = 3;

/** Diferença, em pontos percentuais, a partir da qual "subiu"/"caiu" vale. */
const LIMIAR_DIFERENCA = 10;

/**
 * O ponto que o Próximo Passo deve anunciar, lido da fila que o motor já
 * ordenou (`habilidades_prioritarias`). A ordem do motor é respeitada; aqui só
 * se escolhe o TIPO de evidência, do mais forte para o mais fraco:
 *
 *  · `causa`      — o erro de raiz tem nome e intervenção catalogada;
 *  · `traco`      — há traço de raiz, mas a causa ainda não tem nome (a
 *                   evidência é real; o nome do erro não é mostrado);
 *  · `desempenho` — sem traço, só acerto abaixo da média do próprio aluno.
 *
 * `null` quando a fila está vazia — e aí o Próximo Passo segue a escada dele.
 */
export function escolherPadrao(prioritarias = []) {
  const linhas = Array.isArray(prioritarias) ? prioritarias.filter(Boolean) : [];
  const deTraco = linhas.filter((l) => l.origem === "error_trace" && l.processo_id);

  const comCausa = deTraco.find(
    (l) => l.erro_dominante?.nome && !l.erro_dominante?.sem_catalogo && !l.sem_intervencao_catalogada,
  );
  if (comCausa) return { tipo: "causa", linha: comCausa };

  if (deTraco.length) return { tipo: "traco", linha: deTraco[0] };

  const medida = linhas.find(
    (l) => l.origem === "desempenho" && l.processo_id && l.percentual_acerto != null && l.respondidas > 0,
  );
  if (medida) return { tipo: "desempenho", linha: medida };

  return null;
}

/**
 * O plano do motor (`GET /motor/habilidade/:processo`) vira um endereço de
 * prática. `null` quando o acervo não tem mais questão inédita daquele ponto —
 * quem chama decide o que fazer (hoje: cair na prática comum).
 *
 * O enquadramento (objetivo, como praticar, sinal de progresso) só viaja
 * quando o plano saiu de um traço com intervenção catalogada. O texto do caso
 * sem catálogo fala da própria ontologia ("nesta versão da ontologia") e não
 * é para o aluno.
 */
export function montarPraticaDirigida(detalhe, escolha = null) {
  const plano = detalhe?.intervencao || {};
  const itens = plano.praticar?.itens || [];
  const ids = itens.map((i) => i?.item_id).filter(Boolean).slice(0, TETO_QUESTOES);
  if (!ids.length) return null;

  const comEnquadramento = plano.origem === "error_trace" && Boolean(plano.intervencao_id);
  const d = detalhe?.desempenho || {};
  const antes =
    d.respondidas > 0 && d.percentual_acerto != null
      ? { respondidas: d.respondidas, acertos: d.acertos ?? 0, percentual: d.percentual_acerto }
      : null;

  return {
    url: `${ROTAS.PROVAS}?item_ids=${encodeURIComponent(ids.join(","))}`,
    state: {
      dirigida: {
        // Por que ESTE ponto: "causa" | "traco" | "desempenho" | "repetido"
        // (erros da própria série). É o que a tela de questões diz ao aluno.
        tipo: escolha?.tipo || null,
        processoId: detalhe?.processo?.id || escolha?.linha?.processo_id || null,
        foco: detalhe?.processo?.nome || escolha?.linha?.processo_nome || null,
        erro: escolha?.tipo === "causa" ? escolha.linha.erro_dominante?.nome || null : null,
        objetivo: comEnquadramento ? plano.objetivo || null : null,
        comoPraticar: comEnquadramento ? (plano.como_praticar || []).slice(0, 2) : [],
        sinal: comEnquadramento ? plano.sinal_de_progresso || null : null,
        antes,
        // As missões do mapa do Treino que exercitam este mesmo processo — o
        // catálogo liga cada habilidade aos processos dela, e o Treino usa os
        // mesmos ids. É a ponte prova → Treino no fechamento da série.
        habilidades: (detalhe?.processo?.habilidades || []).map((h) => h?.id).filter(Boolean),
        provisorio: Boolean(detalhe?.provisorio),
        total: ids.length,
        restantes: Math.max(0, (plano.praticar?.total_disponivel ?? ids.length) - ids.length),
      },
    },
  };
}

/**
 * Busca o plano e navega. `api` e `navegar` entram por parâmetro para a
 * função ser testável sem rede. Falha de rede ou acervo esgotado nunca deixam
 * o clique sem destino: caem em `reserva` (a prática comum).
 */
export async function abrirPraticaDirigida({ api, navegar, processoId, escolha = null, reserva = ROTAS.PROVAS }) {
  if (processoId) {
    try {
      const { data } = await api.get(`/motor/habilidade/${encodeURIComponent(processoId)}`);
      const pratica = montarPraticaDirigida(data, escolha);
      if (pratica) {
        navegar(pratica.url, { state: pratica.state });
        return true;
      }
    } catch {
      /* segue para a reserva */
    }
  }
  navegar(reserva);
  return false;
}

/**
 * O ponto em que mais erros DESTA série começaram — só quando se repete.
 * Lê a `causa_raiz` que já veio em cada resposta errada (`POST
 * /students/me/answer`); um erro isolado não é padrão, dois no mesmo ponto
 * numa série curta já merecem ser ditos.
 */
export function pontoRepetido(respostas = [], minimo = 2) {
  const conta = {};
  for (const r of respostas || []) {
    const pid = r?.acertou === false ? r?.causa_raiz?.processo_id : null;
    if (pid) conta[pid] = (conta[pid] || 0) + 1;
  }
  let melhor = null;
  for (const [processoId, vezes] of Object.entries(conta)) {
    if (vezes >= minimo && (!melhor || vezes > melhor.vezes)) melhor = { processoId, vezes };
  }
  return melhor;
}

/**
 * O fechamento de uma série: quanto saiu, e — na prática dirigida — como isso
 * se compara com o histórico daquele ponto antes da série.
 *
 * A comparação só existe com amostra dos dois lados (`MIN_PARA_COMPARAR`) e
 * é DESCRITIVA: `sentido` diz se o número desta série ficou acima, abaixo ou
 * no mesmo patamar do histórico, nunca que o aluno "aprendeu".
 */
export function resumoDaSerie(respostas = [], dirigida = null) {
  const lista = respostas || [];
  const total = lista.length;
  const acertos = lista.filter((r) => r?.acertou === true).length;
  const percentual = total ? Math.round((100 * acertos) / total) : null;

  let comparacao = null;
  const antes = dirigida?.antes;
  if (
    antes &&
    antes.percentual != null &&
    antes.respondidas >= MIN_PARA_COMPARAR &&
    total >= MIN_PARA_COMPARAR
  ) {
    const historico = Math.round(antes.percentual);
    const delta = percentual - historico;
    comparacao = {
      antes: historico,
      agora: percentual,
      delta,
      sentido: delta >= LIMIAR_DIFERENCA ? "acima" : delta <= -LIMIAR_DIFERENCA ? "abaixo" : "igual",
    };
  }

  return { total, acertos, percentual, comparacao, repetido: pontoRepetido(lista) };
}

/** A frase do fechamento, a partir do resumo. Sóbria, sem euforia — e honesta
 *  sobre o tamanho da amostra quando o número subiu. */
export function fraseDoFechamento(resumo) {
  const c = resumo?.comparacao;
  if (!c) return null;
  if (c.sentido === "acima") {
    return `Antes desta série você acertava ${c.antes}% neste ponto. Agora foram ${resumo.acertos} de ${resumo.total}. Uma série curta não fecha a questão, mas é o primeiro sinal de que está virando.`;
  }
  if (c.sentido === "abaixo") {
    return `Antes desta série você acertava ${c.antes}% neste ponto, e hoje saiu abaixo disso. Isso também é informação: vale voltar a este ponto antes de abrir outro.`;
  }
  return `Mesmo patamar do seu histórico neste ponto (${c.antes}%). Estabilizar vem antes de subir.`;
}

/** Missões medidas por questão respondida/acertada em QUALQUER lugar. */
const MISSOES_DE_PRATICA = new Set(["responder5", "responder15", "acertar8"]);

/**
 * Para onde a missão leva. As de prática contam resposta em qualquer tela —
 * então, quando o motor já aponta um padrão de erro, elas levam às questões
 * daquele padrão em vez de a um caderno qualquer. A missão, o alvo e o prêmio
 * não mudam (a linha ética de `engajamento.py` continua intacta): muda só o
 * lugar onde as mesmas cinco questões rendem mais.
 */
export function destinoDaMissao(missao, pratica) {
  if (pratica?.processoId && MISSOES_DE_PRATICA.has(missao?.id)) {
    return { tipo: "dirigida", cta: "No seu ponto de atenção" };
  }
  return { tipo: "rota", rota: missao?.rota, cta: missao?.cta };
}
