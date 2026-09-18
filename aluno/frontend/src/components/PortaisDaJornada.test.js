/**
 * O teste que impede o Painel de abrir quebrado.
 *
 * As portas leem campos de QUATRO payloads diferentes (fila de revisão,
 * cronograma, engajamento, redações) e um nome de campo errado não derruba o
 * build — devolve `undefined`, vira "0" na tela e ninguém percebe. Já
 * aconteceu aqui: a fila foi lida como `resumo.vencidas`, que não existe (o
 * campo é `resumo.questoes`), e a porta de revisões diria "nada vence hoje"
 * com a fila cheia.
 *
 * Renderização em string, sem testing-library (não está no projeto): o que
 * precisa ser garantido é que o componente monta e que os números medidos
 * chegam ao texto.
 */
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import PortaisDaJornada from "./PortaisDaJornada";

// O `react-router-dom` 7 é ESM e o jest do CRA não o resolve. O que este
// teste precisa do roteador é só um `<a>` e um `useNavigate` que não faz
// nada — trocar a biblioteca inteira por isso é mais barato e mais estável
// do que reconfigurar o transform para um pacote que a aplicação já exercita
// de verdade em produção.
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...resto }) =>
    require("react").createElement("a", { href: to, ...resto }, children),
  useNavigate: () => () => {},
}), { virtual: true });

const render = (props) => renderToStaticMarkup(createElement(PortaisDaJornada, props));

test("monta sem dado nenhum — aluno recém-criado", () => {
  const html = render({});
  expect(html).toContain("Por onde começar hoje");
  expect(html).toContain("Mapa de treino");
  expect(html).toContain("Falar com a Mentis");
});

test("mostra a fila de revisão de hoje pelo campo real do payload", () => {
  const html = render({ revisoes: { resumo: { questoes: 7 } } });
  expect(html).toContain("7 vencem hoje");
});

test("conta territórios tocados, blocos da semana, medalhas e a última nota", () => {
  const html = render({
    habilidades: [{ respondidas: 3 }, { respondidas: 0 }, { respondidas: 1 }],
    cronograma: { total_concluidos: 4, total_blocos: 9 },
    conquistas: [{ desbloqueada: true }, { desbloqueada: false }],
    redacoes: [{ avaliacao: { nota_total: 860 } }],
    totalRespondidas: 128,
  });
  expect(html).toContain("Você pisou em 2");
  expect(html).toContain("4/9 feitos");
  expect(html).toContain("1/2");
  expect(html).toContain("última: 860");
  expect(html).toContain("128 respondidas");
});

test("a ofensiva medida vira o título da seção", () => {
  expect(render({ engajamento: { ofensiva: { dias: 5 } } })).toContain("5 dias seguidos");
  expect(render({ engajamento: { ofensiva: { dias: 0 } } })).toContain("Dez portas");
});

// O modo compacto é o que a seção "Explorar" usa. Duas coisas não podem
// mudar aí: as dez portas continuam inteiras (a descoberta não foi podada,
// só realocada) e o cabeçalho grande sai, porque quem anuncia a seção é a
// seção — repetir o título ali seria o mesmo texto duas vezes na mesma dobra.
test("compacto: as dez portas inteiras, sem o cabeçalho da vitrine", () => {
  const html = render({ compacto: true });
  expect(html).not.toContain("Por onde começar hoje");
  expect(html).not.toContain("Dez portas. Cada uma");
  expect(html).toContain("Mapa de treino");
  expect(html).toContain("Falar com a Mentis");
  // o sorteio desce para o rodapé da grade, mas não some
  expect(html).toContain("Surpreenda-me");
});
