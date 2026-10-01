/**
 * A próxima missão do desfecho: lacuna conhecida antes de território novo,
 * nunca a missão que acabou, nunca um ponto que o mapa ainda esconde.
 */
import { proximaMissaoNoMapa } from "./trilha";

const no = (hab_id, over = {}) => ({ hab_id, acesso: "acessivel", estado: "available", respondidas: 0, acertos: 0, ...over });

describe("proximaMissaoNoMapa", () => {
  const arestas = [{ source: "A", target: "B" }, { source: "C", target: "A" }];

  test("lacuna conhecida vem antes de território novo, do pior acerto para o melhor", () => {
    const biomas = [{ nodes: [
      no("A", { respondidas: 5, acertos: 2, estado: "in_progress" }),
      no("B"),
      no("D", { respondidas: 10, acertos: 7, estado: "in_progress" }),
      no("E", { respondidas: 4, acertos: 1, estado: "in_progress" }),
    ] }];
    expect(proximaMissaoNoMapa(biomas, arestas, "A").hab_id).toBe("E");
  });

  test("sem lacuna, prefere o vizinho que a missão acabou de abrir", () => {
    const biomas = [{ nodes: [no("A", { respondidas: 5, acertos: 5, estado: "mastered" }), no("Z"), no("C")] }];
    expect(proximaMissaoNoMapa(biomas, arestas, "A").hab_id).toBe("C");
  });

  test("nunca repete a missão atual nem oferece ponto oculto ou dominado", () => {
    const biomas = [{ nodes: [
      no("A", { respondidas: 5, acertos: 1, estado: "in_progress" }),
      no("B", { acesso: "entrevisto", estado: "discovered" }),
      no("C", { respondidas: 6, acertos: 6, estado: "mastered", estadoBackend: "mastered" }),
    ] }];
    expect(proximaMissaoNoMapa(biomas, arestas, "A")).toBeNull();
  });

  test("mapa vazio ou ausente não quebra", () => {
    expect(proximaMissaoNoMapa(null, null, "A")).toBeNull();
    expect(proximaMissaoNoMapa([], [], "A")).toBeNull();
  });
});

describe("proximaMissaoNoMapa com o padrão de erro das provas", () => {
  test("a missão ligada ao padrão vence a lacuna interna do mapa", () => {
    const biomas = [{ nodes: [
      { hab_id: "A", acesso: "acessivel", estado: "in_progress", respondidas: 5, acertos: 1 },
      { hab_id: "B", acesso: "acessivel", estado: "available", respondidas: 0, acertos: 0 },
    ] }];
    expect(proximaMissaoNoMapa(biomas, [], "Z", new Set(["B"])).hab_id).toBe("B");
  });

  test("ligada mas oculta ou dominada não conta", () => {
    const biomas = [{ nodes: [
      { hab_id: "A", acesso: "acessivel", estado: "in_progress", respondidas: 5, acertos: 1 },
      { hab_id: "B", acesso: "oculto", estado: "unknown" },
      { hab_id: "C", acesso: "acessivel", estado: "mastered", estadoBackend: "mastered", respondidas: 6, acertos: 6 },
    ] }];
    expect(proximaMissaoNoMapa(biomas, [], "Z", new Set(["B", "C"])).hab_id).toBe("A");
  });
});
