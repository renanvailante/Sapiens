import { ATALHOS, MAX_MINIATURAS, quantasCabem } from "./atalhos";

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

test("monitor largo para no teto, e não enche a folga toda", () => {
  // Antes isto devolvia `ATALHOS.length`: num monitor de 1536px o aluno via
  // quatro abas nomeadas ao lado de nove círculos de 32px mudos. A cauda
  // longa mora no Menu, que mostra nome e função de cada ferramenta.
  expect(quantasCabem(4000, 600)).toBe(MAX_MINIATURAS);
  expect(MAX_MINIATURAS).toBeLessThan(ATALHOS.length);
});

test("as três abas rebaixadas encabeçam a prioridade", () => {
  // Redação, Semana e Mural eram abas primárias do desktop até 2026-09-17.
  // Elas descem, mas descem para a frente da fila — senão a convergência das
  // barras vira, na prática, esconder três telas que o aluno já usava.
  expect(ATALHOS.slice(0, 4).map((a) => a.rota)).toContain("/redacao");
  expect(ATALHOS.slice(0, 4).map((a) => a.rota)).toContain("/cronograma");
  expect(ATALHOS.slice(0, 4).map((a) => a.rota)).toContain("/comunidade");
});

test("nada que seja aba primária aparece também como miniatura", () => {
  // Miniatura repetida a 40px da aba com o mesmo destino é ruído, não atalho.
  const primarias = ["/dashboard", "/treino", "/exams", "/mentis"];
  for (const a of ATALHOS) expect(primarias).not.toContain(a.rota);
});

test("largura ainda não medida (0) não vira número negativo", () => {
  expect(quantasCabem(0, 0)).toBe(0);
  expect(quantasCabem(NaN, 0)).toBe(0);
});
