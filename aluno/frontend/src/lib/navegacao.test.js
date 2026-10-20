import { AREAS, AREA_DE_ACAO, MENU, MENU_EQUIPE, temNavegacao } from "./navegacao";
import { ROTAS, LEGADO, normalizar, destinoLegado, ehRotaAtual, ehLegado } from "./rotas";

/**
 * O CONTRATO DA NAVEGAÇÃO.
 *
 * Substitui `atalhos.test.js`, que comparava três listas diferentes de
 * destinos entre si (abas do desktop × barra do celular × tira de atalhos) e
 * existia justamente porque as três podiam divergir. Agora há uma lista só, e
 * o que precisa de trava é outra coisa:
 *
 *   1. as cinco áreas são as mesmas nos dois aparelhos — por construção;
 *   2. o Menu não guarda nada pedagógico;
 *   3. todo endereço antigo continua chegando em algum lugar, com a query
 *      intacta.
 *
 * O item 3 é o que protege dinheiro e deep link: `/exams?area=Matemática` sem
 * a query manda o aluno para um caderno genérico, e nada na tela acusa.
 */

// ---------------------------------------------------------------------------
// As áreas
// ---------------------------------------------------------------------------

/**
 * O TETO DE CINCO ÁREAS.
 *
 * Até 2026-10-19 este teste travava a LARGURA da barra de cima do desktop
 * (1072px úteis, 811px medidos com cinco abas). O trilho lateral aposentou
 * essa conta — as áreas empilham na vertical. O teto continua, pelo motivo
 * que sobrou: a barra do celular tem cinco alvos de polegar, com o do meio
 * elevado, e uma sexta área não cabe nela sem encolher todos os rótulos.
 * Ver `Cerebro/ux/navegacao.md`.
 */
test("cinco áreas — o teto da barra do celular", () => {
  expect(AREAS).toHaveLength(5);
});

test("toda área tem cor de endereço própria", () => {
  // A cor pinta o ícone no trilho e na barra do celular: duas áreas com a
  // mesma cor deixam de ser achadas pelo olho antes da leitura.
  const cores = AREAS.map((a) => a.cor);
  for (const cor of cores) expect(cor).toMatch(/^#[0-9A-F]{6}$/i);
  expect(new Set(cores).size).toBe(cores.length);
});

test("toda área tem nome escrito, pergunta e rota canônica", () => {
  for (const area of AREAS) {
    expect(area.nome).toBeTruthy();
    // A pergunta é o que a aba responde — ela vira o tooltip e o `aria-label`.
    // Sem ela a barra volta a ser uma fileira de substantivos.
    expect(area.pergunta).toMatch(/\?$/);
    expect(Object.values(ROTAS)).toContain(area.rota);
    // Nenhuma área aponta para um endereço antigo.
    expect(ehLegado(area.rota)).toBe(false);
  }
});

test("exatamente uma área é o alvo elevado do celular, e é Estudar", () => {
  expect(AREAS.filter((a) => a.acao)).toHaveLength(1);
  expect(AREA_DE_ACAO.rota).toBe(ROTAS.ESTUDAR);
  // Ele precisa estar no MEIO dos cinco: é onde o polegar chega sem esticar,
  // e a barra o desenha 22px acima das vizinhas.
  expect(AREAS.indexOf(AREA_DE_ACAO)).toBe(2);
});

test("nenhuma área se repete", () => {
  const rotas = AREAS.map((a) => a.rota);
  expect(new Set(rotas).size).toBe(rotas.length);
});

// ---------------------------------------------------------------------------
// O Menu
// ---------------------------------------------------------------------------

/**
 * A regra que define a gaveta, como teste.
 *
 * Enquanto o Menu guardava mural, liga, revisões, questões geradas, perfil e
 * histórico, ele era metade do produto atrás de um botão — e por isso precisava
 * de um alvo fixo na barra do celular. Esvaziá-lo é o que liberou o quinto
 * alvo do polegar para uma área de verdade.
 *
 * Se alguém puser uma ferramenta de estudo aqui de novo, este teste cai.
 */
const ROTAS_PEDAGOGICAS = [
  ROTAS.HOJE, ROTAS.ESTUDAR, ROTAS.PROVAS, ROTAS.CURSOS, ROTAS.REDACAO,
  ROTAS.TREINO, ROTAS.FOLHEAR, ROTAS.AGENDA, ROTAS.PROGRESSO, ROTAS.COMUNIDADE,
];

test("o Menu não guarda nenhuma ferramenta pedagógica", () => {
  const noMenu = MENU.flatMap((g) => g.itens).map((i) => i.rota);
  for (const rota of noMenu) {
    expect(ROTAS_PEDAGOGICAS).not.toContain(rota);
  }
});

test("nada aparece ao mesmo tempo como área e como linha do Menu", () => {
  const areas = new Set(AREAS.map((a) => a.rota));
  for (const item of MENU.flatMap((g) => g.itens)) {
    expect(areas.has(item.rota)).toBe(false);
  }
});

test("as ferramentas de equipe ficam fora da lista do aluno", () => {
  const doAluno = MENU.flatMap((g) => g.itens).map((i) => i.rota);
  for (const item of MENU_EQUIPE) {
    expect(doAluno).not.toContain(item.rota);
  }
});

// ---------------------------------------------------------------------------
// Onde a navegação não entra
// ---------------------------------------------------------------------------

test("a prova em andamento não tem navegação; a lista de cadernos tem", () => {
  // A tela de responder é a única com estado NÃO SALVO dentro: uma barra
  // permanente embaixo de um gabarito pela metade é um convite a perdê-lo.
  expect(temNavegacao("/estudar/provas/enem-2023")).toBe(false);
  // A lista é escolha, não prova — e precisa da barra para o aluno sair.
  expect(temNavegacao(ROTAS.PROVAS)).toBe(true);
});

test("o onboarding e o folhear ficam sem navegação", () => {
  expect(temNavegacao(ROTAS.BEM_VINDO)).toBe(false);
  expect(temNavegacao(ROTAS.FOLHEAR)).toBe(false);
  expect(temNavegacao(ROTAS.COMPLETAR_CADASTRO)).toBe(false);
});

test("as cinco áreas têm navegação", () => {
  for (const area of AREAS) expect(temNavegacao(area.rota)).toBe(true);
});

// ---------------------------------------------------------------------------
// Os endereços antigos
// ---------------------------------------------------------------------------

test("todo endereço antigo chega numa rota que existe", () => {
  const canonicas = new Set(Object.values(ROTAS));
  for (const [antiga, nova] of Object.entries(LEGADO)) {
    const base = nova.split(/[?#]/)[0];
    expect(canonicas.has(base)).toBe(true);
    // E o destino nunca é ele mesmo um endereço antigo: um redirect que aponta
    // para outro redirect é um salto a mais na barra de endereço do aluno, e o
    // primeiro que virar laço trava a aba.
    expect(LEGADO[base]).toBeUndefined();
    expect(antiga).not.toBe(base);
  }
});

test("a query do aluno sobrevive ao redirect", () => {
  // O caso que mais importa: o Hoje, a Agenda e a Mentis abrem as provas COM
  // filtro. Perder a query não quebra a tela — entrega um caderno genérico
  // onde o aluno pediu a questão que errou, e nada acusa.
  expect(destinoLegado({ pathname: "/exams", search: "?area=Matemática" }))
    .toBe("/estudar/provas?area=Matem%C3%A1tica");
  expect(destinoLegado({ pathname: "/treino", search: "?hab=HAB-12" }))
    .toBe("/estudar/treino?hab=HAB-12");
  expect(destinoLegado({ pathname: "/exams", search: "?item_ids=a,b,c" }))
    .toBe("/estudar/provas?item_ids=a%2Cb%2Cc");
});

test("os endereços com parâmetro traduzem o parâmetro", () => {
  expect(normalizar("/exam/enem-2023-d1")).toBe("/estudar/provas/enem-2023-d1");
  expect(normalizar("/cursos/mat-basica")).toBe("/estudar/cursos/mat-basica");
  expect(normalizar("/cursos/mat-basica/estacao/06"))
    .toBe("/estudar/cursos/mat-basica/estacao/06");
  expect(normalizar("/cursos/ebooks/redacao-nota-mil"))
    .toBe("/estudar/ebooks/redacao-nota-mil");
  // O mapa radial de uma análise antiga saiu; o registro que ele ilustrava fica.
  expect(normalizar("/map/abc123")).toBe("/analysis/abc123");
});

test("o que virou seção leva âncora, e não o topo da aba", () => {
  // Cair no topo de uma aba de cinco seções, vindo de um link que prometia
  // "conquistas", é o mesmo que não ter redirecionado.
  expect(destinoLegado({ pathname: "/conquistas" })).toBe("/progresso#conquistas");
  expect(destinoLegado({ pathname: "/liga" })).toBe("/progresso#conquistas");
  expect(destinoLegado({ pathname: "/history" })).toBe("/progresso#historico");
  expect(destinoLegado({ pathname: "/revisoes" })).toBe("/agenda#revisoes");
  // A lixeira virou filtro do histórico: a query do destino é a tradução.
  expect(destinoLegado({ pathname: "/trash" })).toBe("/progresso?apagados=1#historico");
});

test("o hash do aluno vence o do destino", () => {
  // Se ele pediu uma seção explicitamente, é nela que quer cair.
  expect(destinoLegado({ pathname: "/desempenho", hash: "#trajetoria" }))
    .toBe("/progresso#trajetoria");
});

test("uma rota canônica não é tocada por normalizar", () => {
  for (const rota of Object.values(ROTAS)) {
    if (rota.includes(":")) continue;
    expect(normalizar(rota)).toBe(rota);
  }
});

// ---------------------------------------------------------------------------
// A aba acesa
// ---------------------------------------------------------------------------

test("a aba acende nas telas filhas, e Hoje só nela mesma", () => {
  // Tudo volta para o Hoje, então ela casa exato — senão ela acenderia em
  // qualquer rota que comece com o mesmo prefixo.
  expect(ehRotaAtual(ROTAS.HOJE, ROTAS.HOJE)).toBe(true);
  expect(ehRotaAtual("/hoje/qualquer", ROTAS.HOJE)).toBe(false);

  // Estudar fica aceso durante a prova, o curso e a redação.
  expect(ehRotaAtual("/estudar/provas/enem-2023", ROTAS.ESTUDAR)).toBe(true);
  expect(ehRotaAtual("/estudar/redacao", ROTAS.ESTUDAR)).toBe(true);
  expect(ehRotaAtual("/estudar/cursos/mat/estacao/1", ROTAS.ESTUDAR)).toBe(true);

  // Comunidade fica acesa enquanto a dúvida está aberta.
  expect(ehRotaAtual("/comunidade/abc", ROTAS.COMUNIDADE)).toBe(true);

  // E uma área não acende na outra.
  expect(ehRotaAtual("/agenda", ROTAS.ESTUDAR)).toBe(false);
  expect(ehRotaAtual("/progresso", ROTAS.AGENDA)).toBe(false);
});
