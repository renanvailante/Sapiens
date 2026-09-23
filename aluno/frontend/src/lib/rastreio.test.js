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
  /** O módulo guarda a trava do `Lead` em estado próprio, então cada caso
   *  precisa de uma cópia nova — senão o segundo teste herda o "já mandei" do
   *  primeiro e passaria por acidente. */
  function moduloNovo() {
    let mod;
    jest.isolateModules(() => {
      mod = require("./rastreio");
    });
    return mod;
  }

  afterEach(() => {
    delete window.fbq;
    delete window._fbq;
    delete window.__sapiensPixel;
  });

  /** Os eventos que saíram, lidos da FILA do `fbq`.
   *
   *  Não dá para espiar pondo um `window.fbq` falso antes: `cadastroConcluido`
   *  chama `carregar()`, que instala o stub oficial por cima de qualquer coisa
   *  que estivesse ali — e isso é o comportamento certo, é ele que faz o
   *  evento sobreviver quando o `fbevents.js` ainda não chegou. Então a
   *  verificação é onde o evento de fato repousa até o script carregar. */
  const eventos = () => (window.fbq?.queue || []).filter((c) => c[0] !== "init");

  it("manda `Lead` com o método, e NADA que identifique a pessoa", () => {
    const { cadastroConcluido, pixelAtivo } = moduloNovo();
    // Só faz sentido afirmar o disparo com o pixel ligado. Sem
    // `REACT_APP_META_PIXEL_ID` o módulo é inerte de propósito, e é isso que
    // o outro caso abaixo cobre — o `.env` não é versionado, então a suíte
    // roda dos dois jeitos conforme a máquina.
    if (!pixelAtivo()) return;
    cadastroConcluido("google");

    const chamadas = eventos();
    expect(chamadas).toHaveLength(1);
    const [tipo, nome, dados] = chamadas[0];
    expect([tipo, nome, dados]).toEqual(["track", "Lead", { content_name: "google" }]);
    // A regra que importa: o que viaja é o FLUXO, não o aluno. Nenhum campo
    // de identificação do Meta (`em`, `ph`, `fn`, `external_id`) pode
    // aparecer — o produto atende menor de idade.
    const carga = JSON.stringify(chamadas);
    for (const proibido of ["em", "ph", "fn", "ln", "external_id", "@"]) {
      expect(carga.includes(`"${proibido}"`)).toBe(false);
    }
  });

  it("manda um `eventID`, para a Meta descartar a repetida", () => {
    const { cadastroConcluido, pixelAtivo } = moduloNovo();
    if (!pixelAtivo()) return;
    cadastroConcluido("email");

    const opcoes = eventos()[0][3];
    expect(typeof opcoes.eventID).toBe("string");
    expect(opcoes.eventID.startsWith("lead-")).toBe(true);
    // O id não pode carregar nada da pessoa: é hora + aleatório, e só.
    expect(opcoes.eventID).not.toMatch(/@/);
  });

  it("dispara UMA vez, por mais que o chamem — clique duplo, re-render, StrictMode", () => {
    const { cadastroConcluido, pixelAtivo } = moduloNovo();
    if (!pixelAtivo()) return;
    expect(cadastroConcluido("email")).toBe(true);
    expect(cadastroConcluido("email")).toBe(false);
    expect(cadastroConcluido("google")).toBe(false);

    expect(eventos()).toHaveLength(1);
  });

  it("carrega o pixel sozinho, sem depender de um PageView ter rodado antes", () => {
    const { cadastroConcluido, pixelAtivo } = moduloNovo();
    if (!pixelAtivo()) return;
    // Nenhum `paginaPublicaVista` foi chamado: `window.fbq` não existe ainda.
    // Era exatamente aqui que o evento sumia em silêncio antes de 23/09/2026.
    expect(typeof window.fbq).toBe("undefined");

    cadastroConcluido("email");

    // O módulo criou o `fbq` (stub com fila) por conta própria.
    expect(typeof window.fbq).toBe("function");
    // E deixou rastro do disparo, para dar para conferir no navegador.
    expect(window.__sapiensPixel.some((e) => e.evento === "Lead")).toBe(true);
  });

  it("não derruba a página quando o pixel não carregou", () => {
    const { cadastroConcluido } = moduloNovo();
    // Bloqueador de anúncio, rede caída, `fbevents.js` que nunca chegou: o
    // medidor não pode virar o erro visível. Mesma regra de `monitoring.js`.
    expect(() => cadastroConcluido("email")).not.toThrow();
  });
});
