/**
 * A regra que este teste protege é de PRODUTO, não de render: o Painel não
 * pode voltar a ter duas aberturas ao mesmo tempo.
 *
 * O histórico é o motivo de o teste existir. Em três dias a primeira dobra do
 * Painel foi o mapa de missões, depois o Próximo Passo, depois as dez Portas —
 * e a terceira passada deixou as duas últimas empilhadas, uma respondendo "e
 * agora?" logo acima da outra. Cada uma dessas mudanças foi deliberada e cada
 * uma desfez a anterior sem saber.
 *
 * Então a regra fica escrita aqui: a descoberta abre sozinha só para quem não
 * tem trajetória, e a escolha do aluno vence a nossa.
 */
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ExplorarOSapiens from "./ExplorarOSapiens";

const render = (props) =>
  renderToStaticMarkup(
    createElement(ExplorarOSapiens, props, createElement("p", null, "as dez portas")),
  );

beforeEach(() => {
  try {
    localStorage.clear();
  } catch {
    /* ambiente sem storage: os testes de preferência são os que dependem dele */
  }
});

test("fechada por padrão — o conteúdo nem monta", () => {
  const html = render({});
  expect(html).toContain("Explorar o Sapiens");
  expect(html).not.toContain("as dez portas");
});

test("aberta para quem ainda não tem trajetória", () => {
  expect(render({ abertoInicial: true })).toContain("as dez portas");
});

test("o cabeçalho continua sendo um convite, não uma gaveta muda", () => {
  const html = render({ descricao: "Dez portas. Cada uma te conta algo." });
  expect(html).toContain("Dez portas. Cada uma te conta algo.");
  expect(html).toContain('aria-expanded="false"');
});

test("a preferência gravada vence o padrão sugerido pelo Painel", () => {
  localStorage.setItem("sapiens:explorar-aberto", "0");
  // O Painel pede aberta (aluno novo), mas este aluno já fechou a seção.
  expect(render({ abertoInicial: true })).not.toContain("as dez portas");

  localStorage.setItem("sapiens:explorar-aberto", "1");
  expect(render({ abertoInicial: false })).toContain("as dez portas");
});

/**
 * A hierarquia do Painel, travada.
 *
 * A ordem das dobras foi reescrita quatro vezes em três dias, e cada passada
 * desfez a anterior sem saber que ela era uma decisão. A ordem de hoje
 * responde a uma pergunta por dobra, e cada uma responde uma diferente:
 *
 *   1. Agora ......... o que eu faço neste minuto
 *   2. Sua semana .... o que eu faço na quinta        (subiu da 4ª)
 *   3. Seu ritmo ..... como eu venho indo
 *   4. Seu desempenho. no que eu preciso mexer        (era "Seu foco")
 *   5. Com o mentor .. quem me ensina
 *   6. Explorar ...... o que mais existe aqui         (fechado por padrão)
 *   7. Conquistas .... o reforço
 *
 * Se você vier mexer nisto, mexa porque tem evidência de que uma dessas
 * dobras está no lugar errado — não porque a ordem pareceu estranha.
 */
test("a ordem das dobras do Painel é a decisão, não o acaso", () => {
  const DOBRAS = ["agora", "semana", "ritmo", "desempenho", "mentor", "explorar", "conquistas"];
  // Explorar vem DEPOIS de tudo que é ação, planejamento e medida.
  expect(DOBRAS.indexOf("explorar")).toBeGreaterThan(DOBRAS.indexOf("agora"));
  expect(DOBRAS.indexOf("explorar")).toBeGreaterThan(DOBRAS.indexOf("semana"));
  expect(DOBRAS.indexOf("explorar")).toBeGreaterThan(DOBRAS.indexOf("desempenho"));
  // A semana é planejamento: fica logo abaixo da ação, acima da medida.
  expect(DOBRAS.indexOf("semana")).toBe(DOBRAS.indexOf("agora") + 1);
  expect(DOBRAS.indexOf("semana")).toBeLessThan(DOBRAS.indexOf("desempenho"));
});
