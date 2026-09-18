import {
  MARGEM,
  dentroDeCampo,
  lembravelMaisProximo,
  montarPayload,
  normalizar,
  posicionarBotao,
  resumir,
  rotaAceitaCaptura,
  textoSuficiente,
} from "./lembretes";

/** Uma janela de celular e uma de desktop, para não repetir o objeto. */
const CELULAR = { vw: 375, vh: 812, largura: 230, altura: 40, toque: true };
const DESKTOP = { vw: 1440, vh: 900, largura: 230, altura: 40, toque: false };

const rect = (left, top, width = 200, height = 20) => ({
  left, top, width, height, right: left + width, bottom: top + height,
});

describe("onde o botão aparece", () => {
  test("no mouse, nasce ACIMA do trecho — o cursor está embaixo dele", () => {
    const { y } = posicionarBotao(rect(400, 300), DESKTOP);
    expect(y).toBeLessThan(300);
  });

  test("no toque, nasce ABAIXO — o balão nativo do iOS/Android fica em cima", () => {
    const { y } = posicionarBotao(rect(40, 300), CELULAR);
    expect(y).toBeGreaterThan(320);
  });

  test("trecho no topo da tela empurra o botão para baixo dele", () => {
    const { y } = posicionarBotao(rect(400, 4), DESKTOP);
    expect(y).toBeGreaterThanOrEqual(MARGEM);
  });

  test("nunca sai da tela, nem quando o trecho começa na margem", () => {
    const esquerda = posicionarBotao(rect(0, 400, 10), CELULAR);
    const direita = posicionarBotao(rect(370, 400, 5), CELULAR);
    expect(esquerda.x).toBeGreaterThanOrEqual(MARGEM);
    expect(direita.x + CELULAR.largura).toBeLessThanOrEqual(CELULAR.vw - MARGEM);
  });

  test("sai da zona morta do ícone da Mentis no canto inferior direito", () => {
    // Um trecho no rodapé à direita colocaria o botão exatamente debaixo do
    // mascote — o defeito que a auditoria de celular de 12/09 encontrou em
    // cinco telas. Ele anda para a esquerda, nunca para cima.
    const semDesvio = rect(1200, 830, 200, 20);
    const { x, y } = posicionarBotao(semDesvio, { ...DESKTOP, toque: true });
    const invade = x + DESKTOP.largura > DESKTOP.vw - 96 && y + DESKTOP.altura > DESKTOP.vh - 96;
    expect(invade).toBe(false);
  });
});

describe("o que conta como o mesmo trecho", () => {
  test("espaço, quebra de linha e caixa não mudam a identidade", () => {
    // O espelho de `lembretes_routes.normalizar`: o navegador quase nunca
    // devolve a mesma seleção byte a byte duas vezes.
    expect(normalizar("  A   Entalpia\né isto. ")).toBe("a entalpia é isto.");
  });

  test("seleção curta demais não vira botão", () => {
    expect(textoSuficiente("  a ")).toBe(false);
    expect(textoSuficiente("  ")).toBe(false);
    expect(textoSuficiente("mol")).toBe(true);
  });
});

describe("onde o botão NÃO aparece", () => {
  test("nas telas públicas e nas que já são a Mentis", () => {
    expect(rotaAceitaCaptura("/")).toBe(false);
    expect(rotaAceitaCaptura("/login")).toBe(false);
    expect(rotaAceitaCaptura("/mentis")).toBe(false);
    expect(rotaAceitaCaptura("/bem-vindo")).toBe(false);
    expect(rotaAceitaCaptura("/feed")).toBe(false);
  });

  test("mas aparece em toda tela de estudo", () => {
    expect(rotaAceitaCaptura("/dashboard")).toBe(true);
    expect(rotaAceitaCaptura("/revisoes")).toBe(true);
    expect(rotaAceitaCaptura("/cursos/quimica/estacao/3")).toBe(true);
    expect(rotaAceitaCaptura("/redacao")).toBe(true);
  });

  test("dentro de um campo, selecionar é EDITAR, não marcar", () => {
    // O aluno que seleciona o que acabou de escrever na redação para apagar
    // não pode ver um botão de 10 Sparks sobre a própria frase.
    const area = document.createElement("textarea");
    const div = document.createElement("div");
    div.appendChild(document.createElement("span"));
    expect(dentroDeCampo(area)).toBe(true);
    expect(dentroDeCampo(div.firstChild)).toBe(false);
  });

  test("selecionar o texto DO botão não reabre o botão", () => {
    const ui = document.createElement("div");
    ui.dataset.lembrarUi = "1";
    const dentro = document.createElement("span");
    ui.appendChild(dentro);
    expect(dentroDeCampo(dentro)).toBe(true);
  });
});

describe("objetos marcados com data-lembrar", () => {
  test("o gesto sobe até o ancestral marcado", () => {
    const card = document.createElement("div");
    card.dataset.lembrar = "Gráfico da variação de entalpia";
    card.dataset.lembrarRef = "curso:termo:estacao-2";
    const filho = document.createElement("img");
    card.appendChild(filho);

    const achado = lembravelMaisProximo(filho);
    expect(achado.texto).toBe("Gráfico da variação de entalpia");
    expect(achado.ref).toBe("curso:termo:estacao-2");
    expect(achado.elemento).toBe(card);
  });

  test("fora de um objeto marcado, não há nada a capturar", () => {
    expect(lembravelMaisProximo(document.createElement("p"))).toBeNull();
  });
});

describe("o que vai para o servidor", () => {
  test("a rota perde query e hash — senão o mesmo trecho seria cobrado duas vezes", () => {
    // `rota` entra no hash do `_id` no servidor. Se `?pagina=2` fosse junto,
    // voltar à mesma tela por outro caminho criaria uma linha nova paga.
    const p = montarPayload({
      texto: "  um trecho  ",
      pathname: "/cursos/quimica/estacao/3?volta=1#bloco-4",
      titulo: "Química",
      contexto: "Estudando termoquímica.",
    });
    expect(p.rota).toBe("/cursos/quimica/estacao/3");
    expect(p.texto).toBe("um trecho");
    expect(p.tipo).toBe("texto");
  });

  test("o preview cabe numa linha e usa reticências de verdade", () => {
    expect(resumir("a".repeat(200), 10)).toBe(`${"a".repeat(9)}…`);
    expect(resumir("  duas   linhas\nviram uma  ")).toBe("duas linhas viram uma");
  });
});
