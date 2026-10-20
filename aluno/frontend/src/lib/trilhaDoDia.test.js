/**
 * A trilha do dia decide o que o aluno vê como "o próximo passo" — a peça
 * mais importante do Hoje. Estes testes travam as regras que fazem dela um
 * caminho de verdade, e não mais uma lista de sugestões:
 *
 *   · sempre existe UM nó aceso (nunca zero com coisa pendente, nunca dois);
 *   · o prêmio pronto ganha de qualquer pendência (é instantâneo e é do aluno);
 *   · feito é o que o SERVIDOR contou — nenhuma regra aqui inventa conclusão;
 *   · a trilha nunca nasce vazia;
 *   · e a revisão feita hoje continua na trilha, dourada, em vez de sumir.
 */
import {
  montarTrilhaDoDia, falaDaMentis, novidadesDaTrilha, rotaDePratica, saudacao,
} from "./trilhaDoDia";
import { dicaPara, marcarDicaVista } from "./dicasDaMentis";
import { escolherVoz, textoFalavel } from "./vozDaMentis";

const HOJE = "2026-10-09";

const missao = (id, extra = {}) => ({
  id, titulo: `Missão ${id}`, alvo: 5, progresso: 0, concluida: false, sparks: 5, xp: 20,
  rota: "/x", cta: "Ir", resgatada: false, ...extra,
});

const engajamento = (missoes, ofensiva = { dias: 3, estudou_hoje: false }) => ({ missoes, ofensiva });

const passoDirigido = {
  chave: "padrao-P-10", titulo: "Proporção", rota: "/estudar/provas", cta: "Praticar este ponto",
  dirigida: { processoId: "P-10", escolha: { tipo: "causa" } },
};

const chaves = (t) => t.nos.map((n) => n.chave);
const acesos = (t) => t.nos.filter((n) => n.atual);

test("as três missões viram três nós, e o troféu fecha o caminho", () => {
  const t = montarTrilhaDoDia({
    engajamento: engajamento([missao("responder5"), missao("treino"), missao("comunidade")]),
    hoje: HOJE,
  });
  expect(chaves(t)).toEqual(["missao-responder5", "missao-treino", "missao-comunidade", "trofeu"]);
  expect(acesos(t).map((n) => n.chave)).toEqual(["missao-responder5"]);
  expect(t.total).toBe(3);
  expect(t.feitos).toBe(0);
  expect(t.completo).toBe(false);
});

test("revisão vencida vem primeiro, leva direto às questões e funde a missão de revisão", () => {
  const t = montarTrilhaDoDia({
    revisoes: { resumo: { questoes: 2 }, itens: [{ processo_id: "P-1", praticar: [{ item_id: "A" }, { item_id: "B" }] }] },
    engajamento: engajamento([missao("responder5"), missao("revisao", { alvo: 1 })]),
    hoje: HOJE,
  });
  expect(chaves(t)).toEqual(["revisao", "missao-responder5", "trofeu"]);
  const rev = t.nos[0];
  expect(rev.atual).toBe(true);
  expect(rev.acao.rota).toBe("/estudar/provas?item_ids=A%2CB");
  // O prêmio da missão de revisão aparece NO nó da revisão.
  expect(rev.premio.missaoId).toBe("revisao");
});

test("os blocos de hoje entram na ordem do horário; a missão de cronograma mora no primeiro", () => {
  const t = montarTrilhaDoDia({
    cronograma: { dias: [{ data: HOJE, blocos: [
      { id: "b2", titulo: "Tarde", inicio: "15:00", fim: "15:40", concluido: false },
      { id: "b1", titulo: "Manhã", inicio: "08:00", fim: "08:40", concluido: true },
    ] }] },
    engajamento: engajamento([missao("cronograma", { alvo: 1, progresso: 1, concluida: true, resgatada: true })]),
    hoje: HOJE,
  });
  expect(chaves(t)).toEqual(["bloco-b1", "bloco-b2", "trofeu"]);
  expect(t.nos[0].estado).toBe("feito");
  expect(t.nos[1].atual).toBe(true);
});

test("o baú pronto acende antes de qualquer pendência", () => {
  const t = montarTrilhaDoDia({
    engajamento: engajamento([
      missao("responder5"),
      missao("treino", { progresso: 10, alvo: 10, concluida: true }),
    ]),
    hoje: HOJE,
  });
  const atual = acesos(t);
  expect(atual).toHaveLength(1);
  expect(atual[0].chave).toBe("missao-treino");
  expect(atual[0].estado).toBe("resgatar");
});

test("feito é só o que o servidor contou: progresso parcial continua pendente", () => {
  const t = montarTrilhaDoDia({
    engajamento: engajamento([missao("responder5", { progresso: 4 })]),
    hoje: HOJE,
  });
  expect(t.nos[0].estado).toBe("pendente");
  expect(t.nos[0].progresso).toEqual({ feito: 4, alvo: 5 });
});

test("prática com padrão de erro leva à prática dirigida; sem padrão, direto às questões da área", () => {
  const com = montarTrilhaDoDia({ engajamento: engajamento([missao("acertar8")]), passo: passoDirigido, hoje: HOJE });
  expect(com.nos[0].acao).toMatchObject({ tipo: "dirigida", processoId: "P-10" });

  const sem = montarTrilhaDoDia({ engajamento: engajamento([missao("acertar8")]), area: "Ciências da Natureza", hoje: HOJE });
  expect(sem.nos[0].acao).toEqual({ tipo: "rota", rota: rotaDePratica("Ciências da Natureza") });
  // Nunca a LISTA de cadernos: um nó da trilha não pede escolha.
  expect(sem.nos[0].acao.rota).toContain("?area=");
});

test("dia completo: troféu dourado e uma lição extra — o aluno nunca fica sem próximo passo", () => {
  const t = montarTrilhaDoDia({
    engajamento: engajamento([missao("responder5", { progresso: 5, concluida: true, resgatada: true })]),
    passo: passoDirigido,
    hoje: HOJE,
  });
  expect(t.completo).toBe(true);
  expect(chaves(t)).toEqual(["missao-responder5", "trofeu", "extra"]);
  expect(t.nos.find((n) => n.chave === "trofeu").estado).toBe("feito");
  expect(acesos(t).map((n) => n.chave)).toEqual(["extra"]);
});

test("sem engajamento (rede falhou), o passo do motor vira o único nó — a trilha nunca nasce vazia", () => {
  const t = montarTrilhaDoDia({ passo: { ...passoDirigido, olho: "O padrão", porque: "Porque sim." }, hoje: HOJE });
  expect(chaves(t)).toEqual(["passo", "trofeu"]);
  expect(t.atual.chave).toBe("passo");
});

test("a missão de revisão sem nada vencido não acende — a fila não tem o que revisar", () => {
  const t = montarTrilhaDoDia({
    revisoes: { resumo: { questoes: 0 }, itens: [] },
    engajamento: engajamento([missao("revisao", { alvo: 1 }), missao("responder5")]),
    hoje: HOJE,
  });
  const rev = t.nos.find((n) => n.chave === "revisao");
  expect(rev.estado).toBe("espera");
  expect(rev.atual).toBe(false);
  expect(t.atual.chave).toBe("missao-responder5");
  // "Espera" não conta no "N de M": seria cobrar o que não dá para fazer.
  expect(t.total).toBe(1);
});

test("a revisão feita hoje continua na trilha como feita, em vez de sumir com a fila", () => {
  const anterior = { dia: HOJE, feitos: [], presentes: ["revisao", "missao-responder5", "trofeu"] };
  const t = montarTrilhaDoDia({
    revisoes: { resumo: { questoes: 0 }, itens: [] },
    engajamento: engajamento([missao("responder5")]),
    anterior,
    hoje: HOJE,
  });
  expect(t.nos[0]).toMatchObject({ chave: "revisao", estado: "feito" });
  // De ONTEM não vale: a fila de hoje vazia não diz nada sobre revisar hoje.
  const ontem = montarTrilhaDoDia({
    revisoes: { resumo: { questoes: 0 }, itens: [] },
    engajamento: engajamento([missao("responder5")]),
    anterior: { ...anterior, dia: "2026-10-08" },
    hoje: HOJE,
  });
  expect(chaves(ontem)).not.toContain("revisao");
});

test("novidades: só o que ficou pronto desde a última visita DE HOJE", () => {
  const t = montarTrilhaDoDia({
    engajamento: engajamento([missao("responder5", { progresso: 5, concluida: true }), missao("treino")]),
    hoje: HOJE,
  });
  // Primeira visita do dia: nada é anunciado como novo.
  expect(novidadesDaTrilha(t.nos, null, HOJE)).toEqual([]);
  expect(novidadesDaTrilha(t.nos, { dia: "2026-10-08", feitos: [] }, HOJE)).toEqual([]);
  // Visita anterior hoje sem nada pronto: a missão concluída é a novidade.
  expect(novidadesDaTrilha(t.nos, { dia: HOJE, feitos: [] }, HOJE)).toEqual(["missao-responder5"]);
  // Já vista pronta: não comemora de novo.
  expect(novidadesDaTrilha(t.nos, { dia: HOJE, feitos: ["missao-responder5"] }, HOJE)).toEqual([]);
});

test("a fala da Mentis: saudação pelo horário, ofensiva só com número real, e o nó aceso", () => {
  const t = montarTrilhaDoDia({ engajamento: engajamento([missao("treino")]), hoje: HOJE });
  const f = falaDaMentis({ trilha: t, nome: "Ana Maria", ofensiva: { dias: 3, estudou_hoje: false }, hora: 9 });
  expect(f.titulo).toBe("Bom dia, Ana!");
  expect(f.texto).toContain("ofensiva de 3 dias");
  expect(f.texto).toContain(t.atual.fala);

  const semOfensiva = falaDaMentis({ trilha: t, nome: "Ana", ofensiva: { dias: 0, estudou_hoje: false }, hora: 20 });
  expect(semOfensiva.titulo).toBe("Boa noite, Ana!");
  expect(semOfensiva.texto).not.toContain("ofensiva");

  const volta = falaDaMentis({ trilha: t, nome: "Ana", voltouDe: "Revisão do dia", hora: 15 });
  expect(volta.titulo).toBe("Mandou bem!");
  expect(volta.texto).toContain("«Revisão do dia»");
});

test("a voz diz a mesma coisa em frases gravadas: saudação, ofensiva e o nó aceso", () => {
  const t = montarTrilhaDoDia({
    revisoes: { resumo: { questoes: 2 }, itens: [] },
    engajamento: engajamento([missao("revisao")]),
    hoje: HOJE,
  });
  expect(falaDaMentis({ trilha: t, nome: "Ana", ofensiva: { dias: 3, estudou_hoje: false }, hora: 9 }).voz)
    .toEqual(["bom-dia", "ofensiva-espera", "revisao-varias"]);
  expect(falaDaMentis({ trilha: t, nome: "Ana", voltouDe: "Bloco", hora: 15 }).voz)
    .toEqual(["mandou-bem", "revisao-varias"]);
  expect(falaDaMentis({ trilha: { atual: null }, hora: 20 }).voz).toEqual(["boa-noite", "dia-feito"]);
});

test("a fala nunca tem emoji — ela é mentora, não animadora", () => {
  const t = montarTrilhaDoDia({
    revisoes: { resumo: { questoes: 1 }, itens: [] },
    cronograma: { dias: [{ data: HOJE, blocos: [{ id: "b", titulo: "Bloco", inicio: "10:00", fim: "11:00" }] }] },
    engajamento: engajamento([missao("responder5"), missao("treino"), missao("comunidade"), missao("cronograma")]),
    passo: passoDirigido,
    hoje: HOJE,
  });
  const emoji = /\p{Extended_Pictographic}/u;
  t.nos.forEach((n) => {
    expect(emoji.test(n.fala || "")).toBe(false);
    expect(emoji.test(n.titulo || "")).toBe(false);
  });
});

test("saudacao cobre o dia inteiro", () => {
  expect(saudacao(3)).toBe("Boa noite");
  expect(saudacao(7)).toBe("Bom dia");
  expect(saudacao(13)).toBe("Boa tarde");
  expect(saudacao(22)).toBe("Boa noite");
});

describe("dicas da Mentis", () => {
  beforeEach(() => {
    try { localStorage.clear(); } catch { /* sem storage */ }
  });

  test("uma vez por área, e nunca por cima de questão", () => {
    expect(dicaPara("/agenda")).toMatchObject({ rota: "/agenda" });
    expect(dicaPara("/agenda/")).toMatchObject({ rota: "/agenda" });
    marcarDicaVista("/agenda");
    expect(dicaPara("/agenda")).toBeNull();
    expect(dicaPara("/estudar/provas", "?item_ids=A,B")).toBeNull();
    expect(dicaPara("/estudar/provas", "?area=Matem%C3%A1tica")).toBeNull();
    expect(dicaPara("/estudar/provas")).toMatchObject({ rota: "/estudar/provas" });
  });

  test("o Hoje não tem dica: lá a Mentis já está falando no conteúdo", () => {
    expect(dicaPara("/hoje")).toBeNull();
  });
});

describe("a voz da Mentis", () => {
  test("prefere pt-BR natural e feminina; aceita qualquer português; sem português, nenhuma", () => {
    const vozes = [
      { name: "Daniel", lang: "en-GB" },
      { name: "Joana", lang: "pt-PT" },
      { name: "Google português do Brasil", lang: "pt-BR" },
      { name: "Microsoft Francisca Online (Natural)", lang: "pt-BR" },
    ];
    expect(escolherVoz(vozes).name).toContain("Francisca");
    expect(escolherVoz([{ name: "Joana", lang: "pt-PT" }]).name).toBe("Joana");
    expect(escolherVoz([{ name: "Daniel", lang: "en-GB" }])).toBeNull();
    expect(escolherVoz(undefined)).toBeNull();
  });

  test("não pronuncia as aspas angulares", () => {
    expect(textoFalavel("Revisão de «Proporção»  agora")).toBe("Revisão de Proporção agora");
  });
});
