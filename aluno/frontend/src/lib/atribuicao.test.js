/**
 * O modo em que o login abre. A atribuição guardada de um anúncio antigo não
 * pode fazer o "Entrar" abrir em "Criar conta" — foi o que aconteceu com o
 * próprio dono do produto, com o cupom ADS-RETA preenchido sozinho.
 */
import { modoInicialDoLogin } from "./atribuicao";

describe("modoInicialDoLogin", () => {
  test("sem pedido explícito, abre em Entrar — mesmo com campanha guardada", () => {
    expect(modoInicialDoLogin({})).toBe("login");
    expect(modoInicialDoLogin({ novo: false, conviteDaUrl: "" })).toBe("login");
  });

  test("convite na URL (link de amigo) abre em Criar conta", () => {
    expect(modoInicialDoLogin({ conviteDaUrl: "RENAN4K7Q" })).toBe("signup");
  });

  test("o Começar agora (?novo=1) abre em Criar conta", () => {
    expect(modoInicialDoLogin({ novo: true })).toBe("signup");
  });
});
