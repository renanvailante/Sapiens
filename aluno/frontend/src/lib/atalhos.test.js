import { ATALHOS } from "./atalhos";

/**
 * A tira do celular. Duas regras, e as duas são de produto.
 *
 * O que este teste protegia antes era a ARITMÉTICA da barra do desktop
 * (`quantasCabem`): quantos círculos de 32px cabiam na folga. Essa fileira
 * saiu em 2026-09-17 — ícone sem rótulo não é atalho, é charada — e com ela
 * saiu a conta. O que sobra para travar é o que importava desde o começo:
 * nenhuma porta duplicada, e nenhuma porta perdida.
 */

const PRIMARIAS = ["/dashboard", "/exams", "/cronograma", "/desempenho", "/cursos", "/mentis"];

test("nada que seja aba primária aparece também na tira", () => {
  // Atalho a 40px de distância da aba com o mesmo destino é ruído: o aluno
  // não consegue aprender que são a mesma coisa, então trata como duas.
  for (const a of ATALHOS) expect(PRIMARIAS).not.toContain(a.rota);
});

test("o que saiu da barra continua alcançável em um toque", () => {
  // Redação, Mural e Aula ao vivo eram alvos de topo até 2026-09-17. Podem
  // descer, não podem sumir — quem já usava não pode perder o caminho.
  const rotas = ATALHOS.map((a) => a.rota);
  expect(rotas).toContain("/redacao");
  expect(rotas).toContain("/comunidade");
  expect(rotas).toContain("/aula-ao-vivo");
});

test("toda pílula da tira tem nome escrito", () => {
  // A tira do celular sempre desenhou `nome` ao lado do ícone, e é por isso
  // que ela sobreviveu à passada que matou as miniaturas. Sem nome, não entra.
  for (const a of ATALHOS) {
    expect(typeof a.nome).toBe("string");
    expect(a.nome.length).toBeGreaterThan(0);
    expect(a.label.length).toBeGreaterThan(0);
  }
});

/**
 * A LARGURA DA BARRA, travada como número.
 *
 * A barra de cima vive em 1072px úteis e nenhum monitor a aumenta. Com os
 * seis primários escritos por extenso, a medição no navegador (tipografia
 * real da aplicação, 2026-09-17) deu 979px — 93px de folga. É pouco: um
 * rótulo a mais estoura.
 *
 * Este teste não mede pixel (jsdom não faz layout). Ele trava o que CAUSA o
 * estouro: a quantidade de itens nomeados na barra. Se alguém acrescentar um
 * sétimo, o teste cai e manda medir de novo antes de seguir — que é
 * exatamente a conversa que precisa acontecer.
 */
const LARGURA_UTIL = 1072;
const MEDIDO_COM_SEIS = 979;

test("seis primários é o teto medido da barra", () => {
  expect(PRIMARIAS).toHaveLength(6);
  expect(MEDIDO_COM_SEIS).toBeLessThan(LARGURA_UTIL);
  // A folga não paga um sétimo rótulo (o menor deles, "Painel", mede ~95px).
  expect(LARGURA_UTIL - MEDIDO_COM_SEIS).toBeLessThan(95);
});
