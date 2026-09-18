/**
 * AS SUGESTÕES DO PAINEL — o que este aluno deveria fazer a seguir.
 *
 * A REGRA QUE GOVERNA O ARQUIVO INTEIRO: nenhuma sugestão genérica. Se a
 * frase que sai daqui puder ser dita para qualquer aluno do Sapiens, ela não
 * deveria ter sido dita. "Continue estudando!" é decoração com aparência de
 * ajuda, e o custo dela não é zero: um painel que enche de avisos vazios
 * ensina o aluno a ignorar o painel, e aí o aviso que importava também
 * desaparece. Cada regra abaixo cita um NÚMERO do próprio aluno.
 *
 * NENHUMA CHAMADA NOVA. Tudo o que está aqui sai do payload que
 * `/perfil/painel` já devolve numa requisição só — as frentes com taxa e
 * tendência, a constância, as forças, a redação e as leituras da Mentis. Isso
 * não é elegância: em 2026-09-04 o app inteiro caiu por estouro de cota do
 * Firestore, e a disciplina que saiu de lá é que nada pode ler O(eventos) por
 * requisição. Um painel de sugestões que fizesse quatro chamadas para montar
 * um balão seria a forma mais cara possível de dizer o que já estava na mão.
 *
 * A ORDEM É PRIORIDADE PEDAGÓGICA, e não novidade:
 *
 *   1. o que tem PRAZO          — a aula de quinta, que não se repõe
 *   2. o que a memória vai perder — o que ele estudou e não revisou
 *   3. onde ele está errando     — a frente mais fraca com amostra suficiente
 *   4. o que ele abandonou       — a redação, a ofensiva quebrada
 *   5. o que a Mentis leu        — as leituras acionáveis do próprio painel
 *   6. o que ele conquistou      — o reconhecimento vem por último de propósito
 *
 * O reconhecimento por último não é desprezo pelo aluno: é que um elogio no
 * topo de uma lista de ações empurra as ações para baixo, e quem abriu o
 * painel abriu para agir. O elogio é o fecho, não a manchete.
 */

/** O dia da semana em que a aula ao vivo acontece (0 = domingo). */
const QUINTA = 4;

/** Abaixo disto, a taxa de uma frente é ruído estatístico e não vira
 *  sugestão: mandar o aluno "reforçar Química" por causa de 3 questões é
 *  mandá-lo perseguir um número que não existe. */
const AMOSTRA_MINIMA_PARA_APONTAR = 12;

/** Uma frente só é "fraca" abaixo disto. Acima, ela está dentro do esperado e
 *  apontá-la seria inventar um problema para ter o que dizer. */
const TAXA_FRACA = 60;

/** Dias sem escrever redação a partir dos quais vale lembrar. Menos que isso
 *  é a semana normal de quem também estuda outras cinco matérias. */
const DIAS_SEM_REDACAO = 14;

function diaDaSemana(hoje) {
  return hoje.getDay();
}

/**
 * A aula ao vivo. Aparece de domingo a quinta e some na sexta e no sábado:
 * uma aula que já passou não é uma sugestão, é um lembrete de que ele
 * perdeu — e o produto não ganha nada com isso.
 */
function sugestaoDaAula(hoje) {
  const dia = diaDaSemana(hoje);
  if (dia > QUINTA) return null;

  const faltam = QUINTA - dia;
  const quando =
    faltam === 0 ? "é hoje" : faltam === 1 ? "é amanhã" : `em ${faltam} dias`;

  return {
    id: "aula-ao-vivo",
    icone: "radio",
    olho: faltam === 0 ? "Hoje" : "Toda quinta",
    titulo: "Garanta sua vaga na aula com Vitor Lara",
    porque: `A aula ${quando}. São 60 minutos ao vivo com o 1º colocado de Medicina da USP — e ela não fica gravada para quem faltou.`,
    rota: "/aula-ao-vivo",
    cta: faltam === 0 ? "Entrar na sala" : "Garantir a vaga",
    tom: "quente",
  };
}

/**
 * O QUE ELE ESTUDOU E NÃO VOLTOU A VER. A tendência por frente diz o que
 * caiu; uma frente que ele já trabalhou (amostra suficiente) e que está
 * DESCENDO é o caso clássico de conteúdo que a memória está soltando.
 */
function sugestaoDeRevisao(frentes) {
  const caindo = (frentes || [])
    .filter(
      (f) =>
        f.respondidas >= AMOSTRA_MINIMA_PARA_APONTAR &&
        typeof f.delta === "number" &&
        f.delta <= -5,
    )
    .sort((a, b) => a.delta - b.delta)[0];

  if (!caindo) return null;

  return {
    id: `revisar-${caindo.chave}`,
    icone: "rotate",
    olho: "Escorregando",
    titulo: `Revise ${caindo.nome} antes de seguir`,
    porque: `Seu acerto em ${caindo.nome} caiu ${Math.abs(Math.round(caindo.delta))} pontos nas últimas semanas. Conteúdo que já foi seu e está voltando atrás é o mais barato de recuperar.`,
    rota: `/exams?area=${encodeURIComponent(caindo.chave)}`,
    cta: "Revisar agora",
  };
}

/**
 * ONDE ELE ERRA MAIS. A frente com a pior taxa entre as que têm amostra. É a
 * sugestão de maior retorno por hora estudada e a razão de o painel existir.
 */
function sugestaoDeDificuldade(frentes) {
  const fraca = (frentes || [])
    .filter(
      (f) =>
        f.respondidas >= AMOSTRA_MINIMA_PARA_APONTAR &&
        typeof f.taxa === "number" &&
        f.taxa < TAXA_FRACA,
    )
    .sort((a, b) => a.taxa - b.taxa)[0];

  if (!fraca) return null;

  return {
    id: `dificuldade-${fraca.chave}`,
    icone: "alvo",
    olho: "Onde rende mais",
    titulo: `Retome ${fraca.nome}`,
    porque: `Você acerta ${Math.round(fraca.taxa)}% em ${fraca.nome}, com ${fraca.respondidas} questões respondidas. É o ponto em que uma hora de estudo muda mais a sua nota.`,
    rota: `/exams?area=${encodeURIComponent(fraca.chave)}`,
    cta: "Praticar esta frente",
  };
}

/**
 * A REDAÇÃO. Ela vale um quinto da nota do ENEM e é a primeira coisa que o
 * aluno para de fazer, porque é a única que dá trabalho sem devolver um
 * "certo" na hora.
 */
function sugestaoDeRedacao(redacao, hoje) {
  if (!redacao) return null;

  // Os nomes são os do payload, conferidos em `backend/perfil_painel._redacao`:
  // `corrigidas` (quantas já foram avaliadas) e `serie` (as últimas doze, cada
  // uma com `data`). Não existe `ultima_em` — e inventar um campo aqui não
  // quebraria o build: viraria `undefined`, e a regra simplesmente nunca
  // dispararia. É o bug silencioso que `PortaisDaJornada.test.js` documenta.
  const ultimaEntrada = (redacao.serie || [])[(redacao.serie || []).length - 1];
  const ultima = ultimaEntrada?.data ? new Date(ultimaEntrada.data) : null;

  if (!ultima || Number.isNaN(ultima.getTime())) {
    if (redacao.corrigidas) return null;
    return {
      id: "redacao-primeira",
      icone: "caneta",
      olho: "Um quinto da nota",
      titulo: "Escreva a sua primeira redação",
      porque:
        "A redação vale 1000 pontos sozinha e é a única parte do ENEM em que dá para ganhar nota com método em poucas semanas. O Sapiens corrige por competência.",
      rota: "/redacao",
      cta: "Começar a escrever",
    };
  }

  const dias = Math.floor((hoje - ultima) / 86400000);
  if (dias < DIAS_SEM_REDACAO) return null;

  return {
    id: "redacao-parada",
    icone: "caneta",
    olho: `${dias} dias`,
    titulo: "Faz tempo que você não escreve",
    porque: `Sua última redação foi há ${dias} dias. Escrever uma a cada duas semanas é o que mantém repertório e estrutura na mão no dia da prova.`,
    rota: "/redacao",
    cta: "Escrever agora",
  };
}

/**
 * AS LEITURAS DA MENTIS. O backend já devolve as frases dela sobre os
 * gráficos deste aluno, e algumas vêm com ação (`acao.tipo === "ir"`). Elas
 * entram aqui sem reescrita: quem sabe o que a Mentis quis dizer é a Mentis.
 */
function sugestoesDaMentis(leituras) {
  return (leituras || [])
    .filter((l) => l?.acao?.tipo === "ir" && l.acao.href)
    .slice(0, 2)
    .map((l) => ({
      id: `mentis-${l.id}`,
      icone: "mentis",
      olho: "A Mentis notou",
      titulo: l.titulo,
      porque: l.texto,
      rota: l.acao.href,
      cta: l.acao.rotulo || "Ver",
    }));
}

/**
 * O QUE ELE CONQUISTOU. Última da fila, e só quando há número — uma ofensiva
 * de um dia não é uma conquista, é terça-feira.
 */
function sugestaoDeConquista(constancia) {
  // `sequencia`, e não `ofensiva`: o nome do campo é o do payload.
  const sequencia = constancia?.sequencia || 0;
  if (sequencia < 3) return null;

  return {
    id: "conquista-sequencia",
    icone: "chama",
    olho: "Sua sequência",
    titulo: `${sequencia} dias seguidos estudando`,
    porque:
      "Constância é o que separa quem melhora de quem só estuda muito em alguns dias. Veja onde isso te colocou na liga.",
    rota: "/conquistas",
    cta: "Ver conquistas",
    tom: "conquista",
  };
}

/**
 * Monta a lista final.
 *
 * `limite` existe porque um balão com nove itens é uma segunda página, não um
 * balão: o aluno rola, perde o contexto do gráfico que estava olhando e não
 * age em nenhum. Quatro cabe na altura de uma dobra e ainda deixa o painel
 * atrás dele respirando.
 */
export function montarSugestoes(painel, hoje = new Date(), limite = 4) {
  if (!painel) return [];

  const frentes = painel.frentes?.linhas || [];
  const tendencia = painel.frentes?.tendencia || [];

  // A tendência vem numa lista separada da taxa; juntar as duas aqui evita
  // que cada regra tenha de fazer o mesmo casamento.
  const porChave = {};
  for (const f of frentes) porChave[f.chave] = { ...f };
  for (const t of tendencia) {
    if (porChave[t.chave]) porChave[t.chave].delta = t.delta;
  }
  const comTendencia = Object.values(porChave);

  const candidatas = [
    sugestaoDaAula(hoje),
    sugestaoDeRevisao(comTendencia),
    sugestaoDeDificuldade(comTendencia),
    sugestaoDeRedacao(painel.redacao, hoje),
    ...sugestoesDaMentis(painel.mentis?.leituras),
    sugestaoDeConquista(painel.constancia),
  ].filter(Boolean);

  // Nunca duas sugestões sobre a MESMA frente: "revise Matemática" logo acima
  // de "retome Matemática" são a mesma frase dita duas vezes, e a segunda faz
  // o aluno duvidar da primeira.
  const vistas = new Set();
  const finais = [];
  for (const s of candidatas) {
    const assunto = s.id.split("-").slice(1).join("-");
    if (assunto && vistas.has(assunto)) continue;
    if (assunto) vistas.add(assunto);
    finais.push(s);
    if (finais.length >= limite) break;
  }
  return finais;
}
