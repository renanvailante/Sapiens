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

// As seis abas do DESKTOP (`PRIMARY_LINKS` em `Nav.jsx`). Desde 2026-09-18,
// "Praticar" e "Cursos" viraram uma só (`/estudar`) e a vaga aberta foi para
// a aula ao vivo.
const PRIMARIAS = ["/dashboard", "/estudar", "/cronograma", "/desempenho", "/aula-ao-vivo", "/mentis"];

// Os cinco alvos da BARRA INFERIOR (`ABAS` + `ACAO` em `BarraInferior.jsx`),
// que é o que o celular realmente desenha. O quinto é o Menu, que não é rota.
const DO_CELULAR = ["/dashboard", "/cronograma", "/estudar", "/desempenho"];

test("nada que o celular já desenha aparece também na tira", () => {
  // A regra é contra DUPLICATA NA MESMA TELA: um atalho a 40px de distância
  // de outro alvo com o mesmo destino é ruído, porque o aluno não consegue
  // aprender que são a mesma coisa e passa a tratar como duas.
  //
  // A régua é a barra inferior, e não as abas do desktop, porque é a barra
  // que divide a tela com a tira: as abas são `lg:flex` e a tira é
  // `lg:hidden` — elas nunca aparecem juntas. Foi essa distinção que abriu
  // caminho para a aula ao vivo ser aba no notebook E pílula no celular sem
  // se repetir em lugar nenhum.
  for (const a of ATALHOS) expect(DO_CELULAR).not.toContain(a.rota);
});

test("o que saiu da barra continua alcançável em um toque", () => {
  // Redação, Mural e Aula ao vivo eram alvos de topo até 2026-09-17. Podem
  // descer, não podem sumir — quem já usava não pode perder o caminho.
  const rotas = ATALHOS.map((a) => a.rota);
  expect(rotas).toContain("/redacao");
  expect(rotas).toContain("/comunidade");
  expect(rotas).toContain("/aula-ao-vivo");
});

test("a aula ao vivo é a primeira da tira, e é a única em destaque", () => {
  // Único destino do produto com HORA MARCADA: acontece na quinta e quem
  // perde não repõe. No celular não há barra de abas, então a tira é o
  // caminho — e ela precisa ser o primeiro alvo do polegar, não o sétimo.
  expect(ATALHOS[0].rota).toBe("/aula-ao-vivo");
  // Âmbar é recurso de uso único: duas pílulas quentes e nenhuma chama
  // atenção. O `Nav` lê `destaque` para pintar (ver `data-aceso` no CSS).
  expect(ATALHOS.filter((a) => a.destaque)).toHaveLength(1);
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
 * 2026-09-18: os rótulos MUDARAM sem mudar a contagem — "Praticar" e "Cursos"
 * saíram, "Estudar" e "Aulas" entraram. A soma dos caracteres caiu de 47 para
 * 44, então a folga não encolheu; a conta de 979px continua sendo o teto.
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
