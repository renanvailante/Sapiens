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

// O Hoje não pede mais aberta para a conta nova (ver o item 2 do cabeçalho de
// `ExplorarOSapiens.jsx`); o prop continua funcionando para quem o passar.
test("abertoInicial abre a seção quando quem monta pede", () => {
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
 * A hierarquia do Hoje, travada.
 *
 * A ordem das dobras foi reescrita cinco vezes, e cada passada desfez a
 * anterior sem saber que ela era uma decisão. Desde 2026-10-09 o Hoje é a
 * TRILHA DO DIA (Duolingo como referência total, pedido do dono), e a ordem
 * responde a uma pergunta por dobra:
 *
 *   1. Guia ......... a Mentis diz o próximo passo, com UM botão
 *   2. Trilha ....... o caminho de hoje, com um nó aceso (as missões são nós)
 *   3. Plus ......... o desafio dos 5 dias, visível desde a conta nova
 *   4. Mudou ........ os eventos, não os resumos das outras abas
 *   5. Ritmo ........ o detalhe do placar: ofensiva, nível, liga, ENEM
 *   6. Mentor ....... quem me ensina
 *   7. Explorar ..... o que mais existe aqui         (fechado por padrão)
 *
 * Se você vier mexer nisto, mexa porque tem evidência de que uma dessas
 * dobras está no lugar errado — não porque a ordem pareceu estranha.
 */
test("a ordem das dobras do Hoje é a decisão, não o acaso", () => {
  const DOBRAS = ["guia", "trilha", "plus", "mudou", "ritmo", "mentor", "explorar"];
  // Quem diz o que fazer e onde fazer vêm antes de tudo, colados.
  expect(DOBRAS.indexOf("guia")).toBe(0);
  expect(DOBRAS.indexOf("trilha")).toBe(1);
  // Explorar vem DEPOIS de tudo que é ação e medida.
  expect(DOBRAS.indexOf("explorar")).toBe(DOBRAS.length - 1);
  // O desafio do Plus é o dono pedindo "desde o início": logo depois da trilha.
  expect(DOBRAS.indexOf("plus")).toBe(DOBRAS.indexOf("trilha") + 1);
});
