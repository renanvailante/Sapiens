/**
 * Quando o pedido de aviso no celular aparece. As duas regras são do dono do
 * produto: nunca antes de o aluno ter feito alguma coisa, e uma vez só — a
 * recusa no navegador é quase irreversível, então perguntar na hora errada
 * custa o canal inteiro.
 */
jest.mock("./api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
// eslint-disable-next-line import/first
import { devePerguntar, situacaoDoPush } from "./push";

describe("situacaoDoPush", () => {
  test("iPhone fora da tela de início precisa instalar antes de qualquer coisa", () => {
    expect(situacaoDoPush({ suporte: false, plataforma: "ios", instalado: false, permissao: "default" })).toBe("precisa_instalar");
  });

  test("permissão negada vira bloqueado, concedida vira permitido", () => {
    expect(situacaoDoPush({ suporte: true, plataforma: "android", instalado: false, permissao: "denied" })).toBe("bloqueado");
    expect(situacaoDoPush({ suporte: true, plataforma: "android", instalado: false, permissao: "granted" })).toBe("permitido");
  });

  test("navegador sem a API não oferece nada", () => {
    expect(situacaoDoPush({ suporte: false, plataforma: "desktop", instalado: false, permissao: "default" })).toBe("indisponivel");
  });
});

describe("devePerguntar", () => {
  const base = { situacao: "pode_pedir", jaPerguntado: false, inscrito: false, respondeuNaSerie: true };

  test("pergunta no fim de uma série com resposta, num aparelho que pode receber", () => {
    expect(devePerguntar(base)).toBe(true);
  });

  test("nunca antes de o aluno responder alguma coisa", () => {
    expect(devePerguntar({ ...base, respondeuNaSerie: false })).toBe(false);
  });

  test("uma vez só, e nunca para quem já está inscrito", () => {
    expect(devePerguntar({ ...base, jaPerguntado: true })).toBe(false);
    expect(devePerguntar({ ...base, inscrito: true })).toBe(false);
  });

  test("bloqueado ou sem suporte não vê um botão que não faz nada", () => {
    expect(devePerguntar({ ...base, situacao: "bloqueado" })).toBe(false);
    expect(devePerguntar({ ...base, situacao: "indisponivel" })).toBe(false);
  });
});
