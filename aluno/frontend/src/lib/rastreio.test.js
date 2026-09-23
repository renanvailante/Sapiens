import { paginaPublicaVista, cadastroConcluido, pixelAtivo } from "./rastreio";

/**
 * A FRONTEIRA DO PIXEL, travada em teste.
 *
 * Estes casos não medem o Meta — medem a única regra de privacidade que este
 * módulo carrega: **o pixel não entra no app do aluno.** Ela é fácil de
 * quebrar sem perceber, porque quebrar significa apenas acrescentar uma rota
 * a uma lista, e nada na tela muda quando isso acontece.
 *
 * `paginaPublicaVista` devolve se contou, e é por isso que ela devolve algo.
 * O disparo em si depende de `REACT_APP_META_PIXEL_ID`, que não existe no
 * ambiente de teste (nem deve): o que se afirma aqui é a DECISÃO de contar.
 */
describe("paginaPublicaVista", () => {
  it("conta as duas telas públicas", () => {
    expect(paginaPublicaVista("/")).toBe(true);
    expect(paginaPublicaVista("/login")).toBe(true);
  });

  it("não conta nenhuma tela de dentro do produto", () => {
    for (const rota of ["/hoje", "/estudar", "/provas", "/redacao", "/sparks", "/mentis", "/bem-vindo"]) {
      expect(paginaPublicaVista(rota)).toBe(false);
    }
  });

  it("não conta as landings de anúncio — elas têm emissor próprio", () => {
    // `landingView` já dispara o `PageView` COM a variante junto. Se `/ads/*`
    // entrasse na lista pública, toda visita de anúncio valeria duas — e o
    // custo por visita da campanha apareceria pela metade no relatório.
    for (const rota of ["/ads/diagnostico", "/ads/mesmo-erro", "/ads/10-questoes", "/ads/reta-final"]) {
      expect(paginaPublicaVista(rota)).toBe(false);
    }
  });

  it("compara o caminho inteiro, não o começo dele", () => {
    // Uma rota futura pendurada em `/login` (um `/login/ajuda`, por exemplo)
    // não herda o pixel sem alguém decidir que ela o merece.
    expect(paginaPublicaVista("/login/ajuda")).toBe(false);
    expect(paginaPublicaVista("/loginhoje")).toBe(false);
  });
});

describe("cadastroConcluido", () => {
  afterEach(() => {
    delete window.fbq;
  });

  it("manda `Lead` com o método, e NADA que identifique a pessoa", () => {
    // Só faz sentido afirmar o disparo com o pixel ligado. Sem
    // `REACT_APP_META_PIXEL_ID` o módulo é inerte de propósito, e é isso que
    // o outro caso abaixo cobre — o `.env` não é versionado, então a suíte
    // roda dos dois jeitos conforme a máquina.
    if (!pixelAtivo()) return;
    const chamadas = [];
    window.fbq = (...args) => chamadas.push(args);

    cadastroConcluido("google");

    expect(chamadas).toEqual([["track", "Lead", { content_name: "google" }]]);
    // A regra que importa: o que viaja é o FLUXO, não o aluno. Nenhum campo
    // de identificação do Meta (`em`, `ph`, `fn`, `external_id`) pode
    // aparecer — o produto atende menor de idade.
    const carga = JSON.stringify(chamadas);
    for (const proibido of ["em", "ph", "fn", "ln", "external_id", "@"]) {
      expect(carga.includes(`"${proibido}"`)).toBe(false);
    }
  });

  it("não derruba a página quando o pixel não carregou", () => {
    // Bloqueador de anúncio, rede caída, `fbevents.js` que nunca chegou: o
    // medidor não pode virar o erro visível. Mesma regra de `monitoring.js`.
    expect(() => cadastroConcluido("email")).not.toThrow();
  });
});
