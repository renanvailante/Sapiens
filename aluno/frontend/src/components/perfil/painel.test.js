/**
 * O teste que impede o painel do perfil de abrir quebrado.
 *
 * Onze gráficos leem trinta e poucos campos de UM payload
 * (`GET /perfil/painel`). Um nome de campo trocado no servidor não derruba o
 * build: vira `undefined`, desenha um gráfico vazio e ninguém percebe — a
 * mesma armadilha que fez nascer o teste das Portas da Jornada.
 *
 * Por isso o dado daqui não é inventado: `__fixtures__/painel.json` é a saída
 * REAL de `perfil_painel.montar` (gerado por
 * `backend/tests/gerar_fixture_do_painel.py` sobre um aluno com cinco meses de
 * histórico). Se o formato do servidor mudar sem o fixture ser regerado, o
 * teste do backend acusa; se mudar COM o fixture regerado e a tela não
 * acompanhar, este aqui acusa.
 *
 * Renderização em string, sem testing-library (não está no projeto). O que
 * precisa ser garantido é que cada cartão monta e que os números medidos
 * chegam ao texto.
 */
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import painel from "./__fixtures__/painel.json";

// `react-router-dom` 7 é ESM e o jest do CRA não o resolve. O que os cartões
// precisam do roteador é um `<a>` e um `useNavigate` inerte.
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...resto }) =>
    require("react").createElement("a", { href: to, ...resto }, children),
  useNavigate: () => () => {},
}), { virtual: true });

const { CurvaDeAcerto, VolumePorSemana, ComecoEAgora } = require("./GraficosEvolucao");
const {
  AcertoPorFrente, OndeRendeMais, DistribuicaoDoEsforco, EvolucaoPorFrente, TendenciaPorFrente,
} = require("./GraficosFrentes");
const {
  QuandoVoceEstuda, AcertoPorPeriodo, SuaSemana, RitmoDeResposta,
  MudarDeResposta, DeOndeVemSuasRespostas,
} = require("./GraficosRitmo");
const { EvolucaoDaRedacao, CompetenciasDaRedacao } = require("./GraficosRedacao");
const Calendario = require("./Calendario").default;
const ResumoDoPainel = require("./ResumoDoPainel").default;

const render = (Componente, props) => renderToStaticMarkup(createElement(Componente, props));

/** Cada cartão com o pedaço do payload que ele recebe na tela — a mesma
 *  ligação que `PerfilCognitivo.jsx` faz. Um campo renomeado no servidor
 *  quebra aqui, que é o ponto. */
const CARTOES = [
  ["curva de acerto", CurvaDeAcerto, { diaria: painel.evolucao.diaria }, "Taxa de acerto ao longo do tempo"],
  ["volume por semana", VolumePorSemana, { semanal: painel.evolucao.semanal }, "Quantas questões por semana"],
  ["começo × agora", ComecoEAgora, { comparativo: painel.evolucao.comparativo }, "Quanto você mudou"],
  ["acerto por frente", AcertoPorFrente, { linhas: painel.frentes.linhas }, "Onde você acerta mais"],
  ["onde rende mais", OndeRendeMais, { linhas: painel.frentes.linhas }, "Peso na prova"],
  ["tendência", TendenciaPorFrente, { tendencia: painel.frentes.tendencia }, "O que subiu e o que caiu"],
  ["divisão do esforço", DistribuicaoDoEsforco, { linhas: painel.frentes.linhas }, "De onde vieram as suas questões"],
  ["evolução por frente", EvolucaoPorFrente, { porFrente: painel.evolucao.por_frente }, "A sua evolução em cada matéria"],
  ["relógio", QuandoVoceEstuda, { porHora: painel.ritmo.por_hora }, "A que horas você estuda"],
  ["período", AcertoPorPeriodo, { blocos: painel.ritmo.blocos }, "Em que período você acerta mais"],
  ["semana", SuaSemana, { porDiaSemana: painel.ritmo.por_dia_semana }, "Em que dias você estuda"],
  ["ritmo de resposta", RitmoDeResposta, { faixas: painel.ritmo.por_faixa_de_tempo }, "rápido ou com calma"],
  ["mudar de resposta", MudarDeResposta, { decisao: painel.habitos.decisao }, "Vale a pena mudar de resposta"],
  ["origem", DeOndeVemSuasRespostas, { origem: painel.habitos.origem }, "Onde você responde questão"],
  ["redação", EvolucaoDaRedacao, { redacao: painel.redacao }, "correção a correção"],
  ["competências", CompetenciasDaRedacao, { redacao: painel.redacao }, "A forma da sua redação"],
  ["calendário", Calendario, { constancia: painel.constancia }, "últimos quatro meses"],
];

describe("cada cartão monta com o payload real do servidor", () => {
  test.each(CARTOES)("%s", (_nome, Componente, props, esperado) => {
    const html = render(Componente, props);
    expect(html).toContain(esperado);
    // "undefined" no HTML é o sintoma de campo renomeado — nunca é texto.
    expect(html).not.toContain("undefined");
    expect(html).not.toContain("NaN");
  });
});

describe("cada cartão sobrevive ao aluno que ainda não tem aquele dado", () => {
  test.each(CARTOES)("%s sem dado", (_nome, Componente) => {
    expect(() => render(Componente, {})).not.toThrow();
  });
});

test("a tira de medidas mostra os números medidos, não os rótulos", () => {
  const html = render(ResumoDoPainel, { resumo: painel.resumo });
  expect(html).toContain(String(painel.resumo.respondidas));
  expect(html).toContain(`${Math.round(painel.resumo.taxa)}%`);
  expect(html).toContain(`melhor sequência: ${painel.resumo.melhor_sequencia}`);
  expect(html).not.toContain("undefined");
});

test("a tira de medidas não inventa variação sem amostra dos dois lados", () => {
  const semPulso = { ...painel.resumo, pulso: { dias: [], delta_taxa: null } };
  const html = render(ResumoDoPainel, { resumo: semPulso });
  expect(html).not.toContain("data-testid=\"perfil-variacao\"");
});

test("frente sem medida não vira barra de zero por cento", () => {
  const linhas = [
    { chave: "matematica", nome: "Matemática", respondidas: 20, acertos: 12, taxa_acerto: 60, estado: "medido", lacuna: 0.4, peso: 1 },
    { chave: "fisica", nome: "Física", respondidas: 0, acertos: 0, taxa_acerto: null, estado: "sem_medida", lacuna: 0.5, peso: 0.7 },
  ];
  const html = render(AcertoPorFrente, { linhas });
  // A frente sem medida some do gráfico e aparece por escrito, com a saída.
  expect(html).toContain("Ainda sem medida: Física");
});

test("a tabela de números existe em todo gráfico que tem dado", () => {
  const html = render(CurvaDeAcerto, { diaria: painel.evolucao.diaria });
  expect(html).toContain("Ver os números");
});

test("o aluno sem redação recebe o convite, não um gráfico vazio", () => {
  const html = render(EvolucaoDaRedacao, { redacao: { corrigidas: 0, serie: [], competencias: [] } });
  expect(html).toContain("Corrigir uma redação");
});

test("a leitura da Mentis sobre um gráfico aparece dentro dele", () => {
  const { ContextoDaMentis } = require("./Grafico");
  const leitura = painel.mentis.leituras.find((l) => l.ancora === "constancia");
  const html = renderToStaticMarkup(
    createElement(
      ContextoDaMentis.Provider,
      { value: { porAncora: { constancia: { ...leitura, indice: 0 } }, ativa: "constancia", aoFocar: () => {} } },
      createElement(Calendario, { constancia: painel.constancia }),
    ),
  );
  expect(html).toContain(leitura.titulo);
  expect(html).toContain("mentis-no-grafico-constancia");
});
