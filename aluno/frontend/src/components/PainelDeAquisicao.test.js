/**
 * O painel que responde "qual anúncio trouxe este aluno".
 *
 * Renderização em string, sem testing-library (não está no projeto) — o mesmo
 * caminho de `PortaisDaJornada.test.js`. É a única verificação possível: a
 * tela é de admin e não abre sem sessão, então um campo lido com o nome
 * errado só apareceria como coluna zerada, em produção, depois de a verba
 * ter sido gasta. Foi exatamente o defeito que este arquivo pegou na
 * primeira versão (uma coluna "Compraram" lendo `total_gasto_cents`, campo
 * que `/admin/users` não devolve).
 */
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import PainelDeAquisicao from "./PainelDeAquisicao";

const render = (users) => renderToStaticMarkup(createElement(PainelDeAquisicao, { users }));

/** Como `/admin/users` devolve um aluno: o documento cru do Mongo (com os
 *  `utm_*` que `auth._registrar_origem` carimbou) mais o enriquecimento do
 *  Firestore feito em `admin_routes.py`. */
const aluno = (extra = {}) => ({
  user_id: "u1",
  name: "Aluno",
  email: "a@b.c",
  sparks_balance: 100,
  questoes_respondidas: 0,
  dias_ativos: 0,
  ...extra,
});

test("sem ninguém de campanha, diz isso em vez de uma tabela vazia", () => {
  const html = render([aluno(), aluno({ user_id: "u2" })]);
  expect(html).toContain("Nenhuma conta com marca de campanha");
});

test("agrupa por ângulo e conta cadastros", () => {
  const html = render([
    aluno({ user_id: "u1", utm_source: "meta", utm_campaign: "ads", utm_content: "curiosidade" }),
    aluno({ user_id: "u2", utm_source: "meta", utm_campaign: "ads", utm_content: "curiosidade" }),
    aluno({ user_id: "u3", utm_source: "meta", utm_campaign: "ads", utm_content: "desafio" }),
  ]);
  expect(html).toContain("curiosidade");
  expect(html).toContain("desafio");
  expect(html).toContain("3 de campanha");
});

test("separa quem respondeu de quem só se cadastrou", () => {
  // A distinção que importa numa campanha: pagar por cadastro que nunca
  // responde uma questão é pagar por nada.
  const html = render([
    aluno({ user_id: "u1", utm_content: "desafio", questoes_respondidas: 12, dias_ativos: 3 }),
    aluno({ user_id: "u2", utm_content: "desafio", questoes_respondidas: 0 }),
  ]);
  expect(html).toContain("desafio");
  expect(html).toMatch(/>2</); // cadastros
  expect(html).toMatch(/>1</); // responderam
  expect(html).toContain(">12<"); // questões somadas
});

test("orgânico não entra na conta de campanha", () => {
  const html = render([
    aluno({ user_id: "u1", utm_source: "meta", utm_content: "erro" }),
    aluno({ user_id: "u2" }),
    aluno({ user_id: "u3" }),
  ]);
  expect(html).toContain("1 de campanha · 2 orgânicos");
});

test("conta com origem mas sem `utm_content` não some num balde genérico", () => {
  // Uma campanha mal etiquetada tem de APARECER, e com o que ela tem —
  // esconder atrás de "desconhecido" é perder a única pista de que a URL do
  // anúncio foi montada errada.
  const html = render([aluno({ utm_source: "meta", utm_campaign: "teste-sem-content" })]);
  expect(html).toContain("teste-sem-content");
});

test("não inventa coluna de compra — o payload não traz esse dado", () => {
  const html = render([aluno({ utm_content: "erro" })]);
  expect(html).not.toContain("Compraram");
  expect(html).toContain("/admin/transacoes");
});
