import { ATALHOS, quantasCabem } from "./atalhos";

/**
 * A regra que este teste protege: a barra NUNCA estoura. A medição de
 * 2026-09-17 mostrou uma conta admin+promoter usando 1119px dos 1152
 * disponíveis — 33px de folga, que não paga nem uma miniatura.
 */
test("barra cheia (admin + promoter) não ganha miniatura nenhuma", () => {
  expect(quantasCabem(1152, 1119)).toBe(0);
});

test("aluno comum em 1152px ganha algumas, sem passar do que existe", () => {
  const n = quantasCabem(1152, 900);
  expect(n).toBeGreaterThan(0);
  expect(900 + 32 + n * 40).toBeLessThanOrEqual(1152);
});

test("monitor largo não desenha mais miniaturas do que a lista tem", () => {
  expect(quantasCabem(4000, 600)).toBe(ATALHOS.length);
});

test("largura ainda não medida (0) não vira número negativo", () => {
  expect(quantasCabem(0, 0)).toBe(0);
  expect(quantasCabem(NaN, 0)).toBe(0);
});
