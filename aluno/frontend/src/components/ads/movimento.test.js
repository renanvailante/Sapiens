/**
 * O ponto de decisão do movimento das demos.
 *
 * `semMovimento()` é o que separa "a sequência roda" de "a peça se entrega
 * pronta". Ele é testado aqui, e não no navegador, por uma razão concreta:
 * **o painel do navegador não emula `prefers-reduced-motion`**, e o
 * `javascript_tool` roda num mundo isolado, então sobrescrever `matchMedia`
 * de fora não é visto pelo React da página. Uma verificação que não pode ser
 * feita no navegador tem de ser feita aqui — é a mesma razão pela qual a
 * matemática da pista de continuidade do produto vive em teste e não em
 * inspeção visual.
 */
import { semMovimento } from "./movimento";

const original = window.matchMedia;

afterEach(() => {
  window.matchMedia = original;
});

function fingirPreferencia(reduzido) {
  window.matchMedia = (consulta) => ({
    matches: consulta.includes("prefers-reduced-motion") ? reduzido : false,
    media: consulta,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
  });
}

test("quem pediu menos movimento ao sistema é detectado", () => {
  fingirPreferencia(true);
  expect(semMovimento()).toBe(true);
});

test("sem a preferência, as demos rodam normalmente", () => {
  fingirPreferencia(false);
  expect(semMovimento()).toBe(false);
});

test("navegador sem `matchMedia` não quebra a landing", () => {
  // Não é hipótese: a landing é a primeira tela que um visitante de anúncio
  // abre, e ela pode chegar num navegador embutido de rede social antigo. Sem
  // esta guarda, `semMovimento` lançaria e derrubaria a demo inteira — numa
  // página cujo único trabalho é demonstrar que o produto funciona.
  delete window.matchMedia;
  expect(() => semMovimento()).not.toThrow();
  expect(semMovimento()).toBe(false);
});

test("a preferência é lida na hora, não memorizada na carga", () => {
  // Alguém pode ligar "reduzir movimento" no sistema com a landing aberta.
  fingirPreferencia(false);
  expect(semMovimento()).toBe(false);
  fingirPreferencia(true);
  expect(semMovimento()).toBe(true);
});
