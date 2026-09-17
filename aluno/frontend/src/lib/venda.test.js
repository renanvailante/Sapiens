/**
 * A linha ética do argumento de venda.
 *
 * Este é o único módulo do app cuja saída existe para convencer alguém a
 * gastar dinheiro, então o que ele NÃO pode fazer é mais importante do que o
 * que ele faz:
 *
 * * não inventar número — toda frase é multiplicação sobre dado do aluno;
 * * não prometer o conteúdo da aula, que ninguém sabe qual é;
 * * não vender a quem já comprou;
 * * não somar na conta um direito que o aluno já tem.
 *
 * Os testes abaixo são essas quatro regras, uma por vez.
 */
import { argumentoDaLive, argumentosDaLive, economiaDoPacote, pacoteComDireito } from "./venda";

const PRECOS = { live_sparks: 200, curso_sparks: 500, total_cursos: 4 };
const PACOTE_4000 = {
  package_id: "spark_4000",
  sparks_amount: 4000,
  price_cents: 11990,
  direitos: ["cursos_inclusos", "lives_inclusas", "mentis_ilimitada", "comunidade_vip"],
};
// Catálogo HIPOTÉTICO, não o real: desde 2026-09-16 só o pacote de 4.000
// concede `lives_inclusas` (ver `backend/sparks_store.py`). O que estes testes
// fecham é a REGRA — anunciar a porta mais barata de um direito —, que precisa
// continuar valendo no dia em que dois pacotes voltarem a vender o mesmo.
const PACOTE_BARATO_COM_LIVES = {
  package_id: "spark_hipotetico",
  sparks_amount: 1500,
  price_cents: 5490,
  direitos: ["lives_inclusas"],
};

const RAIZ = {
  processo_id: "PC-07",
  processo_nome: "Leitura de gráficos",
  percentual_acerto: 41.6,
  erro_dominante: { id: "ERR-3", nome: "Confundir eixo com escala" },
};

describe("qual argumento ganha", () => {
  it("a causa raiz vence tudo: é o único número que é só daquele aluno", () => {
    const a = argumentoDaLive({
      fracos: [RAIZ],
      focos: [{ titulo: "Matemática", evidencia: "38% de acerto em 60 questões" }],
      quintasRestantes: 1,
      ofensiva: 30,
    });
    expect(a.id).toBe("causa-raiz");
    expect(a.texto).toContain("Confundir eixo com escala");
    expect(a.texto).toContain("42%"); // 41,6 arredondado, o número que ele vê no Painel
  });

  it("sem causa nomeada, cai no ponto fraco medido", () => {
    const a = argumentoDaLive({
      focos: [{ titulo: "Matemática", evidencia: "38% de acerto em 60 questões" }],
      quintasRestantes: 3,
    });
    expect(a.id).toBe("ponto-fraco");
    expect(a.texto).toContain("38% de acerto em 60 questões");
  });

  it("um ponto fraco sem evidência não vira frase", () => {
    // Título sem número atrás é slogan, não argumento.
    const a = argumentoDaLive({ focos: [{ titulo: "Matemática" }], quintasRestantes: 0 });
    expect(a.id).toBe("generico");
  });

  it("o aluno novo recebe o que a aula É, sem personalização inventada", () => {
    const a = argumentoDaLive({});
    expect(a.id).toBe("generico");
    expect(a.texto).toContain("ao vivo");
  });
});

describe("o calendário é aritmética, nunca escassez inventada", () => {
  it("conta as quintas que ainda cabem quando já são poucas", () => {
    const ids = argumentosDaLive({ quintasRestantes: 2 }).map((x) => x.id);
    expect(ids).toContain("quintas-restantes");
    const linha = argumentosDaLive({ quintasRestantes: 2 }).find((x) => x.id === "quintas-restantes");
    expect(linha.texto).toContain("2 quintas");
  });

  it("a última aula é chamada de última, e só quando é", () => {
    const linha = argumentosDaLive({ quintasRestantes: 1 }).find((x) => x.id === "quintas-restantes");
    expect(linha.titulo).toBe("Esta é a última aula antes da prova");
  });

  it("depois da prova (ou muito antes dela) o calendário não é argumento", () => {
    expect(argumentosDaLive({ quintasRestantes: 0 }).map((x) => x.id)).not.toContain("quintas-restantes");
    expect(argumentosDaLive({ quintasRestantes: 30 }).map((x) => x.id)).not.toContain("quintas-restantes");
  });
});

describe("nunca se promete o conteúdo da aula", () => {
  it("nenhuma frase diz que ele VAI ensinar o assunto do aluno", () => {
    const todas = argumentosDaLive({
      fracos: [RAIZ],
      focos: [{ titulo: "Redação · Competência 3", evidencia: "80 de 200 pontos" }],
      quintasRestantes: 2,
      ofensiva: 10,
    });
    for (const a of todas) {
      expect(a.texto).not.toMatch(/vai ensinar|vai explicar|aula sobre/i);
    }
  });
});

describe("a conta do pacote", () => {
  it("multiplica o que dá para conferir de cabeça", () => {
    const e = economiaDoPacote({ pacote: PACOTE_4000, quintasRestantes: 8, precos: PRECOS });
    expect(e.sparksLives).toBe(1600); // 8 × 200
    expect(e.sparksCursos).toBe(2000); // 4 × 500
    expect(e.total).toBe(3600);
    expect(e.partes).toEqual([
      "8 aulas ao vivo × 200 = 1600 Sparks",
      "4 cursos × 500 = 2000 Sparks",
    ]);
  });

  it("um pacote só com as lives não conta curso nenhum na economia", () => {
    const e = economiaDoPacote({ pacote: PACOTE_BARATO_COM_LIVES, quintasRestantes: 8, precos: PRECOS });
    expect(e.sparksCursos).toBe(0);
    expect(e.total).toBe(1600);
    expect(e.incluiCursos).toBe(false);
  });

  it("não cobra de novo pelo direito que o aluno já tem", () => {
    const e = economiaDoPacote({
      pacote: PACOTE_4000,
      quintasRestantes: 8,
      precos: PRECOS,
      direitos: { lives_inclusas: true },
    });
    expect(e.sparksLives).toBe(0);
    expect(e.total).toBe(2000);
  });

  it("quem já tem tudo não recebe oferta nenhuma", () => {
    const e = economiaDoPacote({
      pacote: PACOTE_4000,
      quintasRestantes: 8,
      precos: PRECOS,
      direitos: { lives_inclusas: true, cursos_inclusos: true },
    });
    expect(e).toBeNull();
  });

  it("sem prova pela frente, sobra a conta dos cursos — e nunca um total zerado", () => {
    const e = economiaDoPacote({ pacote: PACOTE_4000, quintasRestantes: 0, precos: PRECOS });
    expect(e.total).toBe(2000);
    expect(economiaDoPacote({ pacote: PACOTE_BARATO_COM_LIVES, quintasRestantes: 0, precos: PRECOS })).toBeNull();
  });

  it("sem catálogo do servidor não se inventa preço", () => {
    expect(economiaDoPacote({ pacote: PACOTE_4000, quintasRestantes: 8 })).toBeNull();
    expect(economiaDoPacote({ precos: PRECOS, quintasRestantes: 8 })).toBeNull();
  });
});

describe("a oferta aponta para a porta mais barata", () => {
  it("um direito vendido por dois pacotes é anunciado pelo mais barato", () => {
    const catalogo = [PACOTE_BARATO_COM_LIVES, PACOTE_4000];
    expect(pacoteComDireito(catalogo, "lives_inclusas").package_id).toBe("spark_hipotetico");
    expect(pacoteComDireito(catalogo, "cursos_inclusos").package_id).toBe("spark_4000");
  });

  it("pacote oculto nunca é anunciado", () => {
    const catalogo = [{ package_id: "teste", oculto: true, direitos: ["lives_inclusas"] }, PACOTE_BARATO_COM_LIVES];
    expect(pacoteComDireito(catalogo, "lives_inclusas").package_id).toBe("spark_hipotetico");
  });
});
