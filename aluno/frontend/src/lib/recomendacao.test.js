import { recomendar, emAndamento, naoComecados, porArea } from "./recomendacao";

/**
 * A recomendação é uma REGRA, e regra se testa. O que está protegido aqui não
 * é a frase: é a promessa de que o produto não afirma o que os dados não
 * dizem, e de que ele sugere uma coisa só.
 */

const curso = (id, extra = {}) => ({
  curso_id: id,
  titulo: id,
  area: "matematica",
  tenho_acesso: true,
  tem_conteudo: true,
  ...extra,
});

const progresso = (percentual, estacoes = 10) => ({
  comecou: percentual > 0,
  percentual,
  estacoes,
  concluidas: Math.round((percentual / 100) * estacoes),
});

describe("recomendar", () => {
  it("manda voltar para o curso mais avançado que está parado", () => {
    const r = recomendar([
      curso("a", { progresso: progresso(20) }),
      curso("b", { progresso: progresso(80) }),
    ]);
    expect(r.curso.curso_id).toBe("b");
    expect(r.acao).toBe("Continuar");
    expect(r.motivo).toContain("2 estações");
  });

  it("concorda com o singular quando falta uma estação só", () => {
    const r = recomendar([curso("a", { progresso: progresso(90) })]);
    expect(r.motivo).toBe("Falta uma estação para você terminar este curso.");
  });

  it("quando nada foi começado, sugere pelo peso no ENEM", () => {
    const r = recomendar([
      curso("linguagem", { area: "linguagens", progresso: progresso(0) }),
      curso("mat", { area: "matematica", progresso: progresso(0) }),
    ]);
    expect(r.curso.curso_id).toBe("mat");
    expect(r.acao).toBe("Começar");
  });

  it("não recomenda curso sem conteúdo publicado", () => {
    expect(recomendar([curso("a", { tem_conteudo: false })])).toBeNull();
  });

  it("não inventa recomendação quando não há o que sugerir", () => {
    expect(recomendar([])).toBeNull();
  });

  it("curso terminado sai da lista de continuar", () => {
    expect(emAndamento([curso("a", { progresso: progresso(100) })])).toEqual([]);
  });

  it("curso sem acesso não entra em 'não começados'", () => {
    expect(naoComecados([curso("a", { tenho_acesso: false })])).toEqual([]);
  });
});

describe("porArea", () => {
  it("sem áreas, devolve o catálogo inteiro num grupo só", () => {
    // Front novo contra servidor velho: sem esta saída, a aba de Cursos
    // ficaria sem curso nenhum durante a janela entre os dois deploys.
    const grupos = porArea(undefined, [curso("a"), curso("b")]);
    expect(grupos).toHaveLength(1);
    expect(grupos[0].itens).toHaveLength(2);
  });

  it("sem curso nenhum, não inventa grupo", () => {
    expect(porArea([], [])).toEqual([]);
  });

  it("agrupa na ordem do servidor e descarta área vazia", () => {
    const grupos = porArea(
      [
        { area_id: "matematica", titulo: "Matemática", cursos: ["mat"] },
        { area_id: "vazia", titulo: "Vazia", cursos: [] },
      ],
      [curso("mat")],
    );
    expect(grupos).toHaveLength(1);
    expect(grupos[0].itens[0].curso_id).toBe("mat");
  });
});
