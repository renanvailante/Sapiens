/**
 * A LINGUAGEM DE CONTINUIDADE, travada em teste.
 *
 * As duas peças desta camada existem para obedecer a uma regra de produto que
 * é fácil de escrever e fácil de desfazer sem perceber: a pista de "tem mais
 * conteúdo" aparece quando há mais conteúdo, e SÓ quando há. Um enfeite
 * permanente no pé da tela seria mais simples de implementar, passaria em
 * qualquer revisão visual rápida e mentiria para o aluno em toda página curta
 * e em toda última dobra — que é justamente onde ele mais precisa acreditar no
 * que a interface diz.
 *
 * Por isso a matemática das duas saiu de dentro do `useEffect`: uma regra que
 * só pode ser conferida abrindo um navegador não é conferida.
 */
// O `react-router-dom` 7 é ESM e o jest do CRA não o resolve — mesmo mock
// virtual das outras suítes desta pasta. O que se testa aqui é matemática
// pura; o roteador entra só porque o componente que a hospeda lê a rota atual.
jest.mock("react-router-dom", () => ({ useLocation: () => ({ pathname: "/" }) }), {
  virtual: true,
});

import { forcaDaPista } from "./ContinuidadeDaPagina";
import { ondeContinua } from "./TiraRolavel";

describe("o véu do pé da página", () => {
  test("página que cabe na janela não acende pista nenhuma", () => {
    expect(forcaDaPista(700, 800, 0)).toBe(0);
    expect(forcaDaPista(800, 800, 0)).toBe(0);
  });

  test("muito conteúdo abaixo: pista no máximo", () => {
    expect(forcaDaPista(8000, 800, 0)).toBe(1);
    expect(forcaDaPista(8000, 800, 3000)).toBe(1);
  });

  test("a pista se apaga sozinha na chegada, e chega a zero no fim", () => {
    const alturaTotal = 2000;
    const janela = 800;
    const fim = alturaTotal - janela;

    const a164 = forcaDaPista(alturaTotal, janela, fim - 164);
    const a100 = forcaDaPista(alturaTotal, janela, fim - 100);
    const a40 = forcaDaPista(alturaTotal, janela, fim - 40);
    const noFim = forcaDaPista(alturaTotal, janela, fim);

    expect(a164).toBe(1);
    expect(a100).toBeCloseTo(0.54, 2);
    expect(a40).toBeCloseTo(0.11, 2);
    expect(noFim).toBe(0);

    // Monotônica: rolar para baixo nunca AUMENTA a pista. Sem isto, um ajuste
    // na janela de apagamento pode criar um degrau em que a sombra volta a
    // crescer perto do fim.
    expect(a164).toBeGreaterThanOrEqual(a100);
    expect(a100).toBeGreaterThanOrEqual(a40);
    expect(a40).toBeGreaterThanOrEqual(noFim);
  });

  test("um resto de poucos pixels é arredondamento, não conteúdo", () => {
    // Barra de endereço do iOS encolhendo, zoom, subpixel: 20px de sobra não
    // são uma seção escondida, e acender a sombra por causa deles faria a
    // pista aparecer no fim de páginas que acabaram.
    expect(forcaDaPista(820, 800, 0)).toBe(0);
  });

  test("nunca passa do intervalo 0–1, nem com rolagem além do fim", () => {
    // O iOS deixa rolar além do fim (borracha): a conta fica negativa.
    expect(forcaDaPista(2000, 800, 1400)).toBe(0);
    expect(forcaDaPista(2000, 800, -120)).toBe(1);
  });
});

describe("a fileira rolável", () => {
  test("fileira que cabe na tela não recebe máscara de lado nenhum", () => {
    expect(ondeContinua(0, 300, 300)).toEqual({ inicio: false, fim: false });
  });

  test("no começo, corta só à direita", () => {
    expect(ondeContinua(0, 900, 375)).toEqual({ inicio: false, fim: true });
  });

  test("no meio, corta dos dois lados", () => {
    expect(ondeContinua(200, 900, 375)).toEqual({ inicio: true, fim: true });
  });

  test("no fim, a máscara da direita SAI — ali ela seria mentira", () => {
    expect(ondeContinua(525, 900, 375)).toEqual({ inicio: true, fim: false });
  });

  test("a folga cobre o scrollLeft fracionário", () => {
    // Sem a folga de 2px, um `scrollLeft` de 524.6 num máximo de 525 deixaria
    // a máscara da direita acesa para sempre no fim da fileira.
    expect(ondeContinua(524.6, 900, 375).fim).toBe(false);
    // E um resto de 1px no começo não é "o aluno já rolou".
    expect(ondeContinua(1, 900, 375).inicio).toBe(false);
  });
});
