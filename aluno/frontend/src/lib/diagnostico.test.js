import { ROTA_DO_DIAGNOSTICO, destinoDepoisDeEntrar, etapasDoPlano, saidaDoDiagnostico } from "./diagnostico";

describe("o caminho do primeiro acesso", () => {
  it("conta nova vai direto à primeira questão do diagnóstico", () => {
    expect(destinoDepoisDeEntrar({ contaCriada: true })).toBe(ROTA_DO_DIAGNOSTICO);
    expect(ROTA_DO_DIAGNOSTICO).toBe("/estudar/provas?diagnostico=1");
  });

  it("aluno que volta pelo Google não refaz o diagnóstico", () => {
    expect(destinoDepoisDeEntrar({ contaCriada: false })).toBe("/hoje");
    expect(destinoDepoisDeEntrar()).toBe("/hoje");
  });

  it("o fim do diagnóstico leva ao plano enquanto ele não existe", () => {
    expect(saidaDoDiagnostico({ planoFeito: false })).toEqual({ rota: "/bem-vindo", rotulo: "Montar o meu plano" });
    expect(saidaDoDiagnostico({ planoFeito: true }).rota).toBe("/hoje");
  });
});

describe("as etapas do plano (/bem-vindo)", () => {
  it("quem já respondeu e tem número vai direto às três perguntas e ao desafio", () => {
    expect(etapasDoPlano({})).toEqual(["objetivo", "meta", "dificuldades", "desafio"]);
  });

  it("sem nenhuma resposta, o diagnóstico vem antes do plano", () => {
    expect(etapasDoPlano({ semRespostas: true })[0]).toBe("diagnostico");
  });

  it("sem WhatsApp, o número é pedido depois das perguntas e antes do desafio", () => {
    const etapas = etapasDoPlano({ semWhatsapp: true });
    expect(etapas.indexOf("whatsapp")).toBe(etapas.length - 2);
  });

  it("o desafio do Plus é sempre o último, e o vídeo não volta", () => {
    for (const e of [etapasDoPlano({}), etapasDoPlano({ semRespostas: true, semWhatsapp: true })]) {
      expect(e[e.length - 1]).toBe("desafio");
      expect(e).not.toContain("video");
    }
  });
});
