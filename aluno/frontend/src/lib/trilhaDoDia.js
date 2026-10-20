import { diaLocal } from "./atividade";
import { ROTAS } from "./rotas";
import { rotuloDaLinha } from "./rotulosDoMotor";

/**
 * A TRILHA DO DIA — o caminho do Duolingo, feito do dia deste aluno.
 *
 * Pedido do dono em 2026-10-09: *"quero que o aluno saiba exatamente o que
 * fazer sempre (…) nunca ele pode ficar pensando 'e agora? onde tenho que
 * ir?'"*, com o Duolingo como referência total.
 *
 * O que o Duolingo faz e o Hoje antigo não fazia: a tela inicial é UM
 * caminho, e só um ponto dele está aceso. O Hoje anterior respondia "e agora?"
 * com um passo e três botões ao lado dele, e mais abaixo com as missões, os
 * eventos, o mentor e dez portas — quinze alvos clicáveis na primeira
 * rolagem, cada um certo sozinho, e o aluno sem saber qual era O próximo.
 *
 * ---------------------------------------------------------------------------
 * DE ONDE VEM CADA NÓ (zero requisição nova)
 * ---------------------------------------------------------------------------
 *
 * Tudo sai do que o Hoje já carregava:
 *
 *   1. **Revisão vencida** — a única coisa com prazo (`/revisao/fila`). Leva
 *      DIRETO às questões que voltaram, não à lista da Agenda.
 *   2. **Os blocos de hoje** do cronograma — o que o aluno mesmo marcou.
 *   3. **As três missões do dia** (`/engajamento/me`) — o servidor conta o
 *      progresso de cada uma, e é por isso que a trilha anda sozinha: o nó
 *      fica dourado quando o CONTADOR do servidor chega no alvo, nunca porque
 *      a tela achou que sim. As de prática levam ao padrão de erro do motor
 *      (o mesmo destino do Próximo Passo antigo) ou direto a questões da área.
 *   4. **O troféu** — o dia completo. Depois dele, uma lição extra: o aluno
 *      nunca fica sem um próximo passo.
 *
 * A missão de revisão e a de cronograma se FUNDEM ao nó da coisa em si (a
 * revisão vencida, o primeiro bloco de hoje): duas peças para a mesma ação
 * leriam como duas coisas a fazer.
 *
 * ---------------------------------------------------------------------------
 * O NÓ ACESO
 * ---------------------------------------------------------------------------
 *
 * Um só, sempre: o primeiro prêmio pronto para resgatar (é instantâneo e é do
 * aluno) e, sem prêmio, o primeiro nó pendente. Os pendentes depois dele
 * continuam tocáveis — as missões não dependem umas das outras —, mas não
 * acendem. Uma luz por tela é a regra 1 do sistema visual.
 *
 * A linha ética de sempre: o prêmio mostrado num nó é o que o servidor
 * anuncia na própria missão (`sparks`, `xp`), e nada aqui comemora o que o
 * servidor não contou.
 */

// As missões que contam resposta de questão em qualquer tela — a mesma
// lista de `praticaDirigida.destinoDaMissao`.
const MISSOES_DE_PRATICA = new Set(["responder5", "responder15", "acertar8"]);

const TETO_BLOCOS = 3;

/** O destino de prática quando o motor ainda não aponta um padrão: questões
 *  da área, abertas direto no motor de prova. A lista de cadernos é uma
 *  escolha — e uma escolha é exatamente o que um nó da trilha não pede. */
export function rotaDePratica(area = "Matemática") {
  return `${ROTAS.PROVAS}?area=${encodeURIComponent(area)}`;
}

function estadoDe({ missao = null, pendente = false, espera = false }) {
  if (missao?.concluida && !missao.resgatada) return "resgatar";
  if (pendente) return "pendente";
  if (missao && !missao.concluida) return espera ? "espera" : "pendente";
  return "feito";
}

function premioDe(missao) {
  if (!missao) return null;
  return { sparks: missao.sparks || 0, xp: missao.xp || 0, missaoId: missao.id, resgatada: Boolean(missao.resgatada) };
}

function progressoDe(missao) {
  if (!missao || !(missao.alvo > 0)) return null;
  return { feito: Math.min(missao.progresso || 0, missao.alvo), alvo: missao.alvo };
}

function noDaRevisao(revisoes, missao) {
  const vencidas = revisoes?.resumo?.questoes || 0;
  if (!vencidas && !missao) return null;
  const itens = revisoes?.itens || [];
  const ids = itens.flatMap((i) => (i?.praticar || []).map((p) => p?.item_id)).filter(Boolean);
  const primeira = itens.find((i) => i?.processo_id);
  return {
    chave: "revisao",
    tipo: "revisao",
    icone: "revisao",
    titulo: vencidas
      ? vencidas === 1 ? "1 questão voltou" : `${vencidas} questões voltaram`
      : missao?.titulo || "Revisão da fila",
    detalhe: vencidas
      ? primeira ? `Revisão de «${rotuloDaLinha(primeira)}»` : "Revisão espaçada"
      : "Nada venceu hoje — a fila abre quando uma questão voltar.",
    estado: estadoDe({ missao, pendente: vencidas > 0, espera: !vencidas }),
    progresso: progressoDe(missao),
    premio: premioDe(missao),
    acao: { tipo: "rota", rota: ids.length ? `${ROTAS.PROVAS}?item_ids=${encodeURIComponent(ids.join(","))}` : `${ROTAS.AGENDA}#revisoes` },
    cta: "Revisar agora",
    fala: vencidas
      ? `${vencidas === 1 ? "Uma questão que você errou voltou" : `${vencidas} questões que você errou voltaram`} hoje. Revisar no dia certo é o que faz a memória durar — começamos por elas?`
      : "A sua fila de revisão está em dia. Quando uma questão voltar, ela aparece aqui.",
    voz: vencidas ? (vencidas === 1 ? "revisao-uma" : "revisao-varias") : "revisao-em-dia",
  };
}

function nosDosBlocos(cronograma, missao, hoje) {
  const dia = cronograma?.dias?.find((d) => d.data === hoje);
  const blocos = [...(dia?.blocos || [])]
    .sort((a, b) => String(a.inicio || "").localeCompare(String(b.inicio || "")))
    .slice(0, TETO_BLOCOS);
  return blocos.map((b, i) => ({
    chave: `bloco-${b.id}`,
    tipo: "bloco",
    icone: "agenda",
    titulo: b.titulo || "Bloco do seu cronograma",
    detalhe: b.inicio && b.fim ? `Hoje, ${b.inicio}–${b.fim}` : "No seu cronograma de hoje",
    // A missão de cronograma ("conclua 1 bloco") mora no PRIMEIRO bloco: é
    // ele que a cumpre, e o prêmio aparece onde o trabalho acontece.
    estado: i === 0 ? estadoDe({ missao, pendente: !b.concluido }) : b.concluido ? "feito" : "pendente",
    progresso: null,
    premio: i === 0 ? premioDe(missao) : null,
    acao: { tipo: "rota", rota: b.rota || ROTAS.AGENDA },
    cta: "Começar",
    fala: `Você mesmo marcou ${b.inicio ? `${b.inicio} ` : ""}para «${b.titulo || "este bloco"}». Cumprir o que você planejou vale mais do que qualquer sugestão minha.`,
    voz: "bloco",
  }));
}

function noDaMissao(m, { passo, area }) {
  const base = {
    chave: `missao-${m.id}`,
    tipo: "missao",
    titulo: m.titulo,
    estado: estadoDe({ missao: m }),
    progresso: progressoDe(m),
    premio: premioDe(m),
  };
  const faltam = Math.max(0, (m.alvo || 0) - (m.progresso || 0));

  if (MISSOES_DE_PRATICA.has(m.id)) {
    const dirigida = passo?.dirigida || null;
    return {
      ...base,
      icone: "pratica",
      detalhe: dirigida ? `No seu ponto de atenção: «${passo.titulo}»` : `Questões de ${area}, direto no ENEM`,
      acao: dirigida
        ? { tipo: "dirigida", processoId: dirigida.processoId, escolha: dirigida.escolha, rota: passo.rota }
        : { tipo: "rota", rota: rotaDePratica(area) },
      cta: "Começar",
      fala: dirigida
        ? `Separei questões novas sobre «${passo.titulo}», onde os seus erros mais se repetem.`
        : `Vamos de questões de ${area}: cada resposta me mostra onde você tropeça.`,
      voz: dirigida ? "pratica-dirigida" : "pratica",
    };
  }
  if (m.id === "treino") {
    return {
      ...base,
      icone: "treino",
      detalhe: "Missões curtas no mapa de treino",
      acao: { tipo: "rota", rota: ROTAS.TREINO },
      cta: "Treinar",
      fala: `Hora do mapa de treino: questões curtas, uma habilidade por vez.${faltam ? ` Faltam ${faltam}.` : ""}`,
      voz: "treino",
    };
  }
  if (m.id === "comunidade") {
    return {
      ...base,
      icone: "comunidade",
      detalhe: "Responda uma dúvida no mural",
      acao: { tipo: "rota", rota: ROTAS.COMUNIDADE },
      cta: "Ajudar",
      fala: "Um colega travou numa dúvida. Explicar para alguém é um dos jeitos mais fortes de fixar o conteúdo em você.",
      voz: "comunidade",
    };
  }
  if (m.id === "cronograma") {
    return {
      ...base,
      icone: "agenda",
      detalhe: "Marque um bloco da sua semana como feito",
      acao: { tipo: "rota", rota: ROTAS.AGENDA },
      cta: "Ver a semana",
      fala: "Abra a sua semana e cumpra um bloco do cronograma — é o plano que você montou.",
      voz: "cronograma",
    };
  }
  return {
    ...base,
    icone: "estrela",
    detalhe: m.cta || "",
    acao: { tipo: "rota", rota: m.rota || ROTAS.ESTUDAR },
    cta: m.cta || "Começar",
    fala: `Próxima missão: ${m.titulo}.`,
    voz: "missao",
  };
}

function noExtra(passo, area) {
  const dirigida = passo?.dirigida || null;
  return {
    chave: "extra",
    tipo: "extra",
    icone: "estrela",
    titulo: dirigida ? `Lição extra: «${passo.titulo}»` : "Lição extra",
    detalhe: dirigida ? "Mais questões no seu ponto de atenção" : `Mais questões de ${area}`,
    estado: "pendente",
    progresso: null,
    premio: null,
    acao: dirigida
      ? { tipo: "dirigida", processoId: dirigida.processoId, escolha: dirigida.escolha, rota: passo.rota }
      : { tipo: "rota", rota: passo?.rota && passo.chave !== "praticar" && passo.chave !== "continuar" ? passo.rota : rotaDePratica(area) },
    cta: "Continuar",
    fala: "Você fechou o dia. Se ainda tiver energia, uma lição extra deixa o seu mapa mais nítido — sem pressão.",
    voz: "extra",
  };
}

/**
 * Monta a trilha. Pura: recebe o que o Hoje carregou, devolve os nós.
 *
 * @param {object} p
 * @param {object} [p.revisoes]     `/revisao/fila`
 * @param {object} [p.cronograma]   `/cronograma`
 * @param {object} [p.engajamento]  `/engajamento/me`
 * @param {object} [p.passo]        `ProximoPasso.escolherPasso(...)`
 * @param {string} [p.area]         área para a prática genérica
 * @param {string} [p.hoje]         dia local (AAAA-MM-DD)
 * @param {object} [p.anterior]     `lerTrilhaVista()` — a trilha como estava na
 *                                  última visita DE HOJE (ver a revisão abaixo)
 * @returns {{ nos: object[], atual: object|null, feitos: number, total: number, completo: boolean }}
 */
export function montarTrilhaDoDia({ revisoes = null, cronograma = null, engajamento = null, passo = null, area = "Matemática", hoje = diaLocal(), anterior = null } = {}) {
  const missoes = engajamento?.missoes || [];
  const mRevisao = missoes.find((m) => m.id === "revisao") || null;
  const mBloco = missoes.find((m) => m.id === "cronograma") || null;

  const nos = [];
  const vencidas = revisoes?.resumo?.questoes || 0;
  // Sem nada vencido, a missão de revisão vira nó próprio no lugar dela
  // entre as missões (e não lá no topo, onde prometeria uma revisão que a
  // fila não tem).
  const revisao = noDaRevisao(revisoes, vencidas ? mRevisao : null);
  if (revisao && vencidas) nos.push(revisao);

  // A revisão que o aluno FEZ hoje. A fila só mostra o que está vencido, então
  // revisar esvazia a fila e o nó sumiria da trilha justo no momento em que
  // devia ficar dourado. Se ele estava na trilha numa visita anterior de hoje
  // e a fila agora está vazia, foi revisado — a fila não esvazia sozinha.
  const revisouHoje = !vencidas && anterior?.dia === hoje && (anterior.presentes || []).includes("revisao");
  if (revisouHoje) {
    nos.push({
      chave: "revisao",
      tipo: "revisao",
      icone: "revisao",
      titulo: "Revisão do dia",
      detalhe: "As questões que voltaram hoje estão revisadas.",
      estado: mRevisao?.concluida && !mRevisao.resgatada ? "resgatar" : "feito",
      progresso: null,
      premio: premioDe(mRevisao),
      acao: { tipo: "rota", rota: `${ROTAS.AGENDA}#revisoes` },
      cta: "Ver as revisões",
      fala: "A sua revisão de hoje está feita — a memória agradece.",
      voz: "revisao-feita",
    });
  }

  const blocos = nosDosBlocos(cronograma, mBloco, hoje);
  nos.push(...blocos);

  missoes.forEach((m) => {
    if (m.id === "revisao" && (vencidas || revisouHoje)) return; // fundida acima
    if (m.id === "cronograma" && blocos.length) return; // fundida no 1º bloco
    if (m.id === "revisao") {
      const r = noDaRevisao(null, m);
      if (r) nos.push(r);
      return;
    }
    nos.push(noDaMissao(m, { passo, area }));
  });

  // Sem engajamento (rede falhou) e sem prazo nenhum: o passo do motor vira o
  // único nó. A trilha nunca nasce vazia — vazia, ela seria a pergunta
  // "e agora?" de volta na cara do aluno.
  if (!nos.length && passo) {
    nos.push({
      ...noExtra(passo, area),
      chave: "passo",
      titulo: passo.titulo,
      detalhe: passo.olho,
      cta: passo.cta || "Começar",
      fala: passo.porque,
      voz: "passo",
      acao: passo.dirigida
        ? { tipo: "dirigida", processoId: passo.dirigida.processoId, escolha: passo.dirigida.escolha, rota: passo.rota }
        : { tipo: "rota", rota: passo.chave === "praticar" || passo.chave === "continuar" ? rotaDePratica(area) : passo.rota },
    });
  }

  const contaveis = nos.filter((n) => n.estado !== "espera");
  const feitos = contaveis.filter((n) => n.estado === "feito").length;
  const completo = contaveis.length > 0 && contaveis.every((n) => n.estado === "feito");

  nos.push({
    chave: "trofeu",
    tipo: "trofeu",
    icone: "trofeu",
    titulo: completo ? "Dia completo!" : "Dia completo",
    detalhe: completo ? "Você fez tudo o que tinha para hoje" : "Feche os passos acima",
    estado: completo ? "feito" : "bloqueado",
    progresso: null,
    premio: null,
    acao: null,
    cta: null,
    fala: null,
    voz: null,
  });
  if (completo) nos.push(noExtra(passo, area));

  const atual = nos.find((n) => n.estado === "resgatar") || nos.find((n) => n.estado === "pendente") || null;
  return {
    nos: nos.map((n) => ({ ...n, atual: atual ? n.chave === atual.chave : false })),
    atual,
    feitos,
    total: contaveis.length,
    completo,
  };
}

// ---------------------------------------------------------------------------
// O que a Mentis diz
// ---------------------------------------------------------------------------

const VOZ_DA_SAUDACAO = { "Bom dia": "bom-dia", "Boa tarde": "boa-tarde", "Boa noite": "boa-noite" };

export function saudacao(hora = new Date().getHours()) {
  if (hora < 5) return "Boa noite";
  if (hora < 12) return "Bom dia";
  if (hora < 18) return "Boa tarde";
  return "Boa noite";
}

/**
 * A fala do topo da trilha: saudação, a ofensiva (só com número de verdade) e
 * o nó aceso. Sem emoji e sem euforia — ela é mentora, não animadora de
 * auditório; quem comemora é a tela, quando há o que comemorar.
 */
export function falaDaMentis({ trilha, nome, ofensiva = null, voltouDe = null, hora } = {}) {
  const primeiro = (nome || "").split(" ")[0];
  const oi = `${saudacao(hora)}${primeiro ? `, ${primeiro}` : ""}!`;
  const atual = trilha?.atual;
  const partes = [];
  // O que ela DIZ em voz alta: as mesmas ideias, em frases gravadas uma vez
  // (`falasGravadas.json`). O que muda de aluno para aluno — nome, número,
  // título — fica no balão, escrito; a voz não custa nada por isso.
  const voz = [voltouDe ? "mandou-bem" : VOZ_DA_SAUDACAO[saudacao(hora)]];

  if (voltouDe) partes.push(`Mais um passo feito: «${voltouDe}».`);
  if (ofensiva?.dias > 0 && !ofensiva.estudou_hoje) {
    partes.push(`Sua ofensiva de ${ofensiva.dias} ${ofensiva.dias === 1 ? "dia" : "dias"} espera por hoje.`);
    voz.push("ofensiva-espera");
  } else if (ofensiva?.estudou_hoje && ofensiva?.dias > 0 && !voltouDe && !trilha?.completo) {
    partes.push(`Dia ${ofensiva.dias} da ofensiva garantido.`);
    voz.push("ofensiva-garantida");
  }

  if (!atual) {
    partes.push("Por hoje está tudo feito. Descanse — amanhã a trilha recomeça.");
    voz.push("dia-feito");
  } else if (atual.estado === "resgatar") {
    const p = atual.premio;
    partes.push(`Você cumpriu «${atual.titulo}». Toque no baú para pegar ${p?.sparks || 0} Sparks${p?.xp ? ` e ${p.xp} XP` : ""}.`);
    voz.push("resgatar");
  } else {
    partes.push(atual.fala);
    if (atual.voz) voz.push(atual.voz);
  }

  return { titulo: voltouDe ? "Mandou bem!" : oi, texto: partes.join(" "), voz };
}

// ---------------------------------------------------------------------------
// O que mudou desde a última vez que o aluno viu a trilha
// ---------------------------------------------------------------------------

const chaveVista = (uid) => `sapiens:trilha-vista:${uid || "anon"}`;

/** Os nós que ficaram prontos (ou com prêmio) desde a última visita DE HOJE.
 *  Na primeira visita do dia não há o que comparar — e anunciar tudo como
 *  novidade seria comemorar o que não aconteceu agora. */
export function novidadesDaTrilha(nos, anterior, hoje = diaLocal()) {
  if (!anterior || anterior.dia !== hoje) return [];
  const antes = new Set(anterior.feitos || []);
  return (nos || [])
    .filter((n) => (n.estado === "feito" || n.estado === "resgatar") && n.tipo !== "trofeu" && !antes.has(n.chave))
    .map((n) => n.chave);
}

export function lerTrilhaVista(uid) {
  try {
    return JSON.parse(localStorage.getItem(chaveVista(uid)) || "null");
  } catch {
    return null;
  }
}

export function gravarTrilhaVista(uid, nos, hoje = diaLocal()) {
  const feitos = (nos || []).filter((n) => n.estado === "feito" || n.estado === "resgatar").map((n) => n.chave);
  const presentes = (nos || []).map((n) => n.chave);
  try {
    localStorage.setItem(chaveVista(uid), JSON.stringify({ dia: hoje, feitos, presentes }));
  } catch {
    /* sem storage: a trilha só não comemora a volta — nada quebra */
  }
}

// ---------------------------------------------------------------------------
// O passo aceso, para quem não está no Hoje
// ---------------------------------------------------------------------------
//
// A Mentis flutua em toda tela e precisa saber "qual é o próximo passo" sem
// pagar as quinze leituras do Hoje em cada navegação. O Hoje publica o nó aceso
// aqui (do aparelho, do dia) e quem quiser lê. Vale só no dia em que foi
// gravado: o passo de ontem não é o próximo passo de ninguém.

const CHAVE_PASSO = "sapiens:passo-atual";
export const EVENTO_PASSO = "sapiens:passo-atual";

export function publicarPassoAtual(no, hoje = diaLocal()) {
  const valor = no
    ? { dia: hoje, chave: no.chave, titulo: no.titulo, detalhe: no.detalhe, cta: no.cta, acao: no.acao, estado: no.estado, icone: no.icone }
    : { dia: hoje, completo: true };
  try {
    localStorage.setItem(CHAVE_PASSO, JSON.stringify(valor));
  } catch {
    /* sem storage: a Mentis manda para o Hoje, que sempre sabe */
  }
  try {
    window.dispatchEvent(new Event(EVENTO_PASSO));
  } catch {
    /* fora do navegador */
  }
}

export function lerPassoAtual(hoje = diaLocal()) {
  try {
    const v = JSON.parse(localStorage.getItem(CHAVE_PASSO) || "null");
    return v && v.dia === hoje ? v : null;
  } catch {
    return null;
  }
}
