import {
  dividirEmEtapas, etapaCumprida, etapaParaRetomar,
  progressoDasEtapas, etapasCumpridas,
} from "./etapas";

const texto = (id) => ({ tipo: "texto", bloco_id: id, markdown: "…" });
const tabela = (id) => ({ tipo: "tabela", bloco_id: id, colunas: ["a", "b"], linhas: [] });
const exemplo = (id) => ({ tipo: "exemplo", bloco_id: id, passos: [] });
const exercicio = (id) => ({ tipo: "exercicio", bloco_id: id, nivel: 1 });
const desafio = (id) => ({ tipo: "desafio", bloco_id: id, nivel: 5 });

/** A estação real de Matemática Básica: conteúdo, exemplos, estratégias,
 *  erros comuns, vídeo, dez exercícios e um desafio. */
const estacaoReal = () => [
  texto("c1"), tabela("c2"), texto("c3"),
  exemplo("ex1"), exemplo("ex2"),
  texto("estrategias"), texto("erros"),
  { tipo: "video", bloco_id: "v1" },
  ...Array.from({ length: 10 }, (_, i) => exercicio(`q${i + 1}`)),
  desafio("d1"),
];

describe("dividirEmEtapas", () => {
  it("divide a estação real em entender → resolvido → praticar × 3", () => {
    const etapas = dividirEmEtapas(estacaoReal());
    expect(etapas.map((e) => e.tipo)).toEqual([
      "explicacao", "exemplos", "exercicios", "exercicios", "exercicios",
    ]);
    expect(etapas[0].blocos.map((b) => b.bloco_id)).toEqual(["c1", "c2", "c3"]);
    // Estratégias, erros comuns e vídeo ficam com os exemplos: é o que se
    // generaliza do modelo resolvido, e não uma tela nova de leitura.
    expect(etapas[1].blocos.map((b) => b.bloco_id))
      .toEqual(["ex1", "ex2", "estrategias", "erros", "v1"]);
    expect(etapas[2].blocos).toHaveLength(5);
    // Onze avaliáveis (dez exercícios + desafio) viram 5 + 5 + 1: o desafio
    // fica sozinho na última tela, que é onde ele pertence.
    expect(etapas[4].blocos.map((b) => b.bloco_id)).toEqual(["d1"]);
  });

  it("o desafio entra na última etapa de prática", () => {
    const etapas = dividirEmEtapas(estacaoReal());
    const ultima = etapas[etapas.length - 1];
    expect(ultima.blocos.map((b) => b.tipo)).toContain("desafio");
  });

  it("não cria etapa vazia", () => {
    const etapas = dividirEmEtapas([exercicio("q1"), exercicio("q2")]);
    expect(etapas).toHaveLength(1);
    expect(etapas[0].tipo).toBe("exercicios");
  });

  it("estação sem exemplo tem explicação e prática", () => {
    const etapas = dividirEmEtapas([texto("c1"), exercicio("q1")]);
    expect(etapas.map((e) => e.tipo)).toEqual(["explicacao", "exercicios"]);
  });

  it("numera as etapas e diz o total", () => {
    const etapas = dividirEmEtapas(estacaoReal());
    expect(etapas.map((e) => e.indice)).toEqual([0, 1, 2, 3, 4]);
    expect(etapas.every((e) => e.total === 5)).toBe(true);
  });

  it("aguenta entrada vazia", () => {
    expect(dividirEmEtapas()).toEqual([]);
    expect(dividirEmEtapas([])).toEqual([]);
  });
});

describe("etapaCumprida", () => {
  const etapa = { tipo: "exercicios", blocos: [exercicio("q1"), exercicio("q2")] };

  it("leitura está sempre cumprida", () => {
    expect(etapaCumprida({ tipo: "explicacao", blocos: [texto("c1")] })).toBe(true);
  });

  it("exige TODAS respondidas", () => {
    expect(etapaCumprida(etapa, { q1: { tentativas: 1 } })).toBe(false);
    expect(etapaCumprida(etapa, { q1: { tentativas: 1 }, q2: { tentativas: 3 } })).toBe(true);
  });

  it("errar conta como responder — o muro é a escada de devolutiva, não o botão", () => {
    const respostas = { q1: { tentativas: 2, acertou: false }, q2: { tentativas: 1, acertou: false } };
    expect(etapaCumprida(etapa, respostas)).toBe(true);
  });
});

describe("etapaParaRetomar", () => {
  const etapas = dividirEmEtapas(estacaoReal());

  it("quem nunca entrou começa do começo", () => {
    expect(etapaParaRetomar(etapas, {}, [])).toBe(0);
  });

  it("quem leu tudo cai na primeira prática", () => {
    const vistos = [...etapas[0].blocos, ...etapas[1].blocos].map((b) => b.bloco_id);
    expect(etapaParaRetomar(etapas, {}, vistos)).toBe(2);
  });

  it("quem respondeu a primeira prática cai na segunda", () => {
    const vistos = [...etapas[0].blocos, ...etapas[1].blocos].map((b) => b.bloco_id);
    const respostas = Object.fromEntries(
      etapas[2].blocos.map((b) => [b.bloco_id, { tentativas: 1 }]),
    );
    expect(etapaParaRetomar(etapas, respostas, vistos)).toBe(3);
  });
});

describe("progressoDasEtapas", () => {
  it("conta resposta em exercício e leitura em texto — e são coisas diferentes", () => {
    const etapas = dividirEmEtapas(estacaoReal());
    const progresso = progressoDasEtapas(
      etapas,
      { q1: { tentativas: 2, acertou: true }, q2: { tentativas: 1 } },
      ["c1", "c2"],
    );

    // Etapa de leitura: dois dos três blocos vistos.
    expect(progresso[0]).toMatchObject({ tipo: "explicacao", feitos: 2, total: 3, cumprida: false });
    // Etapa de exercícios: duas respondidas, uma certa.
    expect(progresso[2]).toMatchObject({ tipo: "exercicios", feitos: 2, acertos: 1, cumprida: false });
  });

  it("a etapa de leitura fica cumprida quando foi LIDA, e não só quando se passa dela", () => {
    const etapas = dividirEmEtapas(estacaoReal());
    const cumpridas = etapasCumpridas(etapas, {}, ["c1", "c2", "c3"]);
    expect(cumpridas.has(0)).toBe(true);
    // Os exemplos ainda não foram vistos.
    expect(cumpridas.has(1)).toBe(false);
  });

  it("a etapa de exercícios fica cumprida com todas respondidas, mesmo errando", () => {
    const etapas = dividirEmEtapas(estacaoReal());
    const respostas = {};
    etapas[2].blocos.forEach((b) => { respostas[b.bloco_id] = { tentativas: 1, acertou: false }; });
    const cumpridas = etapasCumpridas(etapas, respostas, []);
    expect(cumpridas.has(2)).toBe(true);
    expect(progressoDasEtapas(etapas, respostas, [])[2].acertos).toBe(0);
  });

  it("estação intocada não inventa progresso nenhum", () => {
    const etapas = dividirEmEtapas(estacaoReal());
    expect(etapasCumpridas(etapas, {}, []).size).toBe(0);
    expect(progressoDasEtapas(etapas, {}, []).every((e) => e.feitos === 0)).toBe(true);
  });
});
