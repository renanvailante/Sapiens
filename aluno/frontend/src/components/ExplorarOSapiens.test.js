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
