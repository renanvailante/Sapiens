/**
 * A gramática de responder questão, travada.
 *
 * O produto tinha cinco lugares onde o aluno responde e três desenhos
 * diferentes de "certa": `.alternativa[data-estado]` nas provas e nos cursos,
 * `border-emerald-400 bg-emerald-50` no treino, `border-emerald-400/50
 * bg-emerald-400/10` nas questões geradas. Ninguém fez isso de propósito —
 * cada tela nasceu num dia e copiou o que tinha por perto.
 *
 * Estes testes existem para que a próxima tela que precisar de alternativas
 * não tenha essa escolha: o estado é DADO (`data-estado`), quem pinta é o
 * CSS, e a devolutiva não inventa gabarito que ninguém informou.
 */
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import Alternativas, { letrasCorretas } from "./Alternativas";
import Veredito from "./Veredito";

const ALTS = [
  { letra: "A", texto: "primeira" },
  { letra: "B", texto: "segunda" },
  { letra: "C", texto: "terceira" },
];

const render = (props) => renderToStaticMarkup(createElement(Alternativas, { alternativas: ALTS, ...props }));

test("sem resposta ainda: tudo livre, nada acusa certo ou errado", () => {
  const html = render({});
  expect(html.match(/data-estado="livre"/g)).toHaveLength(3);
  expect(html).not.toContain('data-estado="certa"');
});

test("a escolha antes do envio é 'escolhida', não 'certa'", () => {
  const html = render({ selecionada: "B" });
  expect(html).toContain('data-estado="escolhida"');
  expect(html).not.toContain('data-estado="certa"');
});

test("acerto: a marcada vira certa; erro: a marcada vira errada e a correta acende", () => {
  const acerto = render({ selecionada: "B", resultado: { acertou: true, correta: "B" } });
  expect(acerto.match(/data-estado="certa"/g)).toHaveLength(1);
  expect(acerto).not.toContain('data-estado="errada"');

  const erro = render({ selecionada: "A", resultado: { acertou: false, correta: "C" } });
  expect(erro).toContain('data-estado="errada"');
  expect(erro).toContain('data-estado="certa"');
});

test("os dois formatos de gabarito do backend são o mesmo gabarito", () => {
  // provas mandam `correta` (uma letra); treino manda `gabarito` (lista)
  expect(letrasCorretas({ correta: "B" })).toEqual(["B"]);
  expect(letrasCorretas({ gabarito: ["A", "C"] })).toEqual(["A", "C"]);
  expect(letrasCorretas(null)).toEqual([]);
});

test("gabarito desconhecido não pinta nada de verde", () => {
  // O caso real: reabrir uma questão gerada que o aluno errou. O servidor não
  // devolve o gabarito, e a tela pintava a resposta ERRADA do aluno de verde.
  const html = render({ selecionada: "A", resultado: { acertou: false, gabarito: [] } });
  expect(html).not.toContain('data-estado="certa"');
  expect(html).toContain('data-estado="errada"');
});

test("alternativa sem texto não é clicável", () => {
  const html = render({ alternativas: [{ letra: "A", texto: "" }] });
  expect(html).toContain("disabled");
  expect(html).toContain("está em correção");
});

test("o veredito só comemora o acerto", () => {
  const acerto = renderToStaticMarkup(
    createElement(Veredito, { resultado: { acertou: true, correta: "A" } }),
  );
  expect(acerto).toContain("recompensa");
  expect(acerto).toContain('data-acertou="true"');

  const erro = renderToStaticMarkup(
    createElement(Veredito, { resultado: { acertou: false, correta: "C" } }),
  );
  expect(erro).not.toContain("recompensa");
  expect(erro).toContain("Correta: C");
});

test("o veredito aceita explicação em texto ou em parágrafos", () => {
  const texto = renderToStaticMarkup(
    createElement(Veredito, { resultado: { acertou: true }, explicacao: "porque sim" }),
  );
  expect(texto).toContain("porque sim");

  const lista = renderToStaticMarkup(
    createElement(Veredito, { resultado: { acertou: true, feedback: { mensagens: ["um", "dois"] } } }),
  );
  expect(lista).toContain("um");
  expect(lista).toContain("dois");
});
