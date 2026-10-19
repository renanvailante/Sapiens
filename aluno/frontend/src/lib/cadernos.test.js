import {
  chaveDaArea, identidadeDaArea, corDoCaderno, nomeDoCaderno, diaDoCaderno,
  rotuloDoCaderno, estadoDoCaderno, agruparPorEdicao, AREAS_DO_ENEM,
} from "./cadernos";

const bloco = (over = {}) => ({
  banca: "ENEM", ano: 2023, prova: "AZUL", numero_min: 136, numero_max: 180,
  count: 45, disciplinas: ["Matemática"], ...over,
});

describe("área do caderno", () => {
  test("casa por pista, com e sem acento, nos nomes que o servidor manda", () => {
    expect(chaveDaArea("Matemática")).toBe("matematica");
    expect(chaveDaArea("Linguagens e Códigos")).toBe("linguagens");
    expect(chaveDaArea("Linguagens, Codigos e suas Tecnologias")).toBe("linguagens");
    expect(chaveDaArea("Ciências Humanas")).toBe("humanas");
    expect(chaveDaArea("Ciencias da Natureza")).toBe("natureza");
    expect(chaveDaArea("Redação")).toBeNull();
    expect(chaveDaArea(undefined)).toBeNull();
  });

  test("cada área tem cor própria e área desconhecida não fica sem cor", () => {
    const cores = Object.values(AREAS_DO_ENEM).map((a) => a.de);
    expect(new Set(cores).size).toBe(cores.length);
    expect(identidadeDaArea("Física Quântica").de).toBeTruthy();
  });
});

describe("nome do caderno", () => {
  test("cor só quando a palavra está no dado", () => {
    expect(corDoCaderno("AZUL")).toBe("Azul");
    expect(corDoCaderno("D2 - amarelo")).toBe("Amarelo");
    expect(corDoCaderno("ENEM-CAD01")).toBeNull();
    expect(nomeDoCaderno("AZUL")).toBe("Caderno Azul");
  });

  test("número de caderno sem cor vira 'Caderno N'; o resto, o próprio texto", () => {
    expect(nomeDoCaderno("ENEM-CAD01")).toBe("Caderno 1");
    expect(nomeDoCaderno("D2_CD5")).toBe("Caderno 5");
    expect(nomeDoCaderno("unica")).toBe("Caderno Unica");
    expect(nomeDoCaderno("")).toBe("Caderno");
  });

  test("o dia sai da numeração", () => {
    expect(diaDoCaderno(bloco({ numero_min: 1 }))).toBe(1);
    expect(diaDoCaderno(bloco({ numero_min: 46 }))).toBe(1);
    expect(diaDoCaderno(bloco({ numero_min: 91 }))).toBe(2);
    expect(diaDoCaderno(bloco({ numero_min: 136 }))).toBe(2);
    expect(diaDoCaderno(bloco({ numero_min: 181 }))).toBeNull();
    expect(diaDoCaderno({})).toBeNull();
  });
});

describe("rótulo do cartão", () => {
  test("o título é a ÁREA, e a edição vai para o grupo", () => {
    const r = rotuloDoCaderno(bloco());
    expect(r.titulo).toBe("Matemática");
    expect(r.edicao).toBe("ENEM 2023");
    expect(r.caderno).toBe("Caderno Azul");
    expect(r.faixa).toBe("Questões 136–180");
    expect(r.dia).toBe(2);
    expect(r.sub).toBe("2º dia · nº 136–180");
  });

  test("sem área conhecida, a faixa de questões — nunca vazio", () => {
    expect(rotuloDoCaderno(bloco({ disciplinas: [] })).titulo).toBe("Questões 136–180");
    expect(rotuloDoCaderno(bloco({ disciplinas: ["Filosofia"] })).titulo).toBe("Filosofia");
  });

  test("estado pelo progresso real", () => {
    expect(estadoDoCaderno(0, 45)).toBe("novo");
    expect(estadoDoCaderno(12, 45)).toBe("andamento");
    expect(estadoDoCaderno(45, 45)).toBe("concluido");
    expect(estadoDoCaderno(3, 0)).toBe("novo");
  });
});

describe("agrupar por edição", () => {
  test("um grupo por banca+ano+caderno, na ordem do servidor, blocos pela numeração", () => {
    const grupos = agruparPorEdicao([
      bloco({ numero_min: 136, numero_max: 180 }),
      bloco({ numero_min: 1, numero_max: 45, disciplinas: ["Linguagens"] }),
      bloco({ ano: 2022, prova: "AMARELO", numero_min: 91, numero_max: 135 }),
    ]);
    expect(grupos.map((g) => g.titulo)).toEqual(["ENEM 2023", "ENEM 2022"]);
    expect(grupos[0].caderno).toBe("Caderno Azul");
    expect(grupos[0].itens.map((p) => p.numero_min)).toEqual([1, 136]);
    expect(grupos[1].caderno).toBe("Caderno Amarelo");
  });

  test("lista vazia não quebra", () => {
    expect(agruparPorEdicao()).toEqual([]);
  });
});
