import {
  deveComemorarOfensiva,
  deveComemorarPlus,
  fraseDoDesafio,
  horasRestantes,
  letraDoDia,
  prazoDoPlus,
  BENEFICIOS_DO_PLUS,
} from "./celebracao";

const eng = (o, hoje = "2026-10-08") => ({ hoje, ofensiva: { dias: 3, estudou_hoje: true, ...o } });

describe("a comemoração da ofensiva", () => {
  test("acende no primeiro estudo do dia", () => {
    expect(deveComemorarOfensiva(eng({}), null)).toBe(true);
  });

  test("não repete no mesmo dia", () => {
    expect(deveComemorarOfensiva(eng({}), "2026-10-08")).toBe(false);
  });

  test("volta no dia seguinte", () => {
    expect(deveComemorarOfensiva(eng({}, "2026-10-09"), "2026-10-08")).toBe(true);
  });

  test("não comemora quem ainda não estudou hoje — a chama não acendeu", () => {
    expect(deveComemorarOfensiva(eng({ estudou_hoje: false }), null)).toBe(false);
  });

  test("sem dado do servidor, nada", () => {
    expect(deveComemorarOfensiva(null, null)).toBe(false);
    expect(deveComemorarOfensiva({ ofensiva: { dias: 0, estudou_hoje: true }, hoje: "x" }, null)).toBe(false);
  });
});

describe("o presente do Plus", () => {
  const plus = { ativo: true, concedido_em: "2026-10-08T20:00:00+00:00" };

  test("comemora uma vez por prêmio", () => {
    expect(deveComemorarPlus(plus, null)).toBe(true);
    expect(deveComemorarPlus(plus, plus.concedido_em)).toBe(false);
  });

  test("Plus vencido não é comemorado", () => {
    expect(deveComemorarPlus({ ...plus, ativo: false }, null)).toBe(false);
  });
});

describe("a promessa escrita", () => {
  test("conta nova ouve a regra inteira", () => {
    expect(fraseDoDesafio({ progresso: 0, faltam: 5, meta_dias: 5, presente_dias: 2 })).toBe(
      "Estude 5 dias seguidos e ganhe 2 dias de Sapiens Plus.",
    );
  });

  test("no caminho, conta o que falta", () => {
    expect(fraseDoDesafio({ progresso: 3, faltam: 2, meta_dias: 5, presente_dias: 2 })).toBe(
      "Faltam 2 dias para ganhar 2 dias de Sapiens Plus.",
    );
    expect(fraseDoDesafio({ progresso: 4, faltam: 1, meta_dias: 5, presente_dias: 2 })).toBe(
      "Falta 1 dia para ganhar 2 dias de Sapiens Plus.",
    );
  });

  test("quem já ganhou não ouve a promessa de novo", () => {
    expect(fraseDoDesafio({ conquistado: true, progresso: 5, faltam: 0 })).toBeNull();
  });

  test("o Plus anuncia exatamente os três direitos do backend (sem a live)", () => {
    expect(BENEFICIOS_DO_PLUS.map((b) => b.chave).sort()).toEqual(
      ["comunidade_vip", "cursos_inclusos", "mentis_ilimitada"],
    );
  });
});

describe("o prazo", () => {
  test("escreve o dia e a hora de São Paulo", () => {
    // 2026-10-10T20:00Z = sábado, 17h em Brasília
    expect(prazoDoPlus("2026-10-10T20:00:00+00:00")).toBe("até sábado, 17h");
  });

  test("prazo ilegível não vira texto", () => {
    expect(prazoDoPlus("amanhã")).toBeNull();
    expect(prazoDoPlus(null)).toBeNull();
  });

  test("horas restantes arredondam e somem quando vence", () => {
    const agora = Date.parse("2026-10-08T20:00:00Z");
    expect(horasRestantes("2026-10-10T20:00:00Z", agora)).toBe(48);
    expect(horasRestantes("2026-10-08T19:00:00Z", agora)).toBeNull();
  });

  test("letras da semana", () => {
    expect(letraDoDia("2026-10-08")).toBe("Q"); // quinta
    expect(letraDoDia("2026-10-11")).toBe("D");
  });
});
