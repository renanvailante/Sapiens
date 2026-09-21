import { montarSugestoes } from "./sugestoes";
import { ROTAS } from "./rotas";

/**
 * As regras do balão de sugestões.
 *
 * O que este teste protege não é a aparência da lista — é a PROMESSA dela. Um
 * painel de sugestões é a peça mais fácil do produto de deixar mentir: basta
 * relaxar uma condição de amostra e ele passa a mandar o aluno "reforçar
 * Química" por causa de três questões, ou a dizer "continue assim!" para quem
 * nunca respondeu nada. Nos dois casos a tela continua bonita, nenhum teste de
 * render quebra, e o aluno aprende em duas semanas que o balão não vale
 * leitura. Depois disso, o aviso que importava também não vale.
 *
 * Por isso as asserções aqui são quase todas NEGATIVAS: o que o balão não
 * pode dizer.
 */

// Segunda-feira, 2026-09-14. Dia fixo porque metade das regras olha o
// calendário, e um teste que roda diferente na sexta é um teste que ninguém
// consegue depurar.
const SEGUNDA = new Date("2026-09-14T10:00:00");
const SEXTA = new Date("2026-09-18T10:00:00");
const QUINTA = new Date("2026-09-17T10:00:00");

const painelVazio = {
  frentes: { linhas: [], tendencia: [] },
  redacao: null,
  constancia: {},
  mentis: { leituras: [] },
};

describe("a aula ao vivo", () => {
  test("aparece de domingo a quinta, porque ainda dá para garantir vaga", () => {
    const s = montarSugestoes(painelVazio, SEGUNDA);
    const aula = s.find((x) => x.id === "aula-ao-vivo");
    expect(aula).toBeTruthy();
    expect(aula.rota).toBe("/aula-ao-vivo");
    expect(aula.porque).toContain("3 dias");
  });

  test("na quinta ela diz que é HOJE e manda entrar na sala", () => {
    const aula = montarSugestoes(painelVazio, QUINTA).find((x) => x.id === "aula-ao-vivo");
    expect(aula.porque).toContain("é hoje");
    expect(aula.cta).toBe("Entrar na sala");
  });

  test("na sexta ela SOME — aula que já passou não é sugestão, é cobrança", () => {
    const s = montarSugestoes(painelVazio, SEXTA);
    expect(s.find((x) => x.id === "aula-ao-vivo")).toBeUndefined();
  });
});

describe("as frentes", () => {
  test("amostra pequena não vira sugestão nenhuma", () => {
    // 3 questões em Química: 33% não é uma medida, é um acaso. Apontá-lo
    // manda o aluno gastar uma semana perseguindo um número que não existe.
    const painel = {
      ...painelVazio,
      frentes: {
        linhas: [{ chave: "quimica", nome: "Química", respondidas: 3, taxa: 33 }],
        tendencia: [],
      },
    };
    const s = montarSugestoes(painel, SEXTA);
    expect(s).toHaveLength(0);
  });

  test("com amostra, a frente mais fraca vira a sugestão e cita o número dela", () => {
    const painel = {
      ...painelVazio,
      frentes: {
        linhas: [
          { chave: "quimica", nome: "Química", respondidas: 40, taxa: 48 },
          { chave: "biologia", nome: "Biologia", respondidas: 40, taxa: 57 },
        ],
        tendencia: [],
      },
    };
    const s = montarSugestoes(painel, SEXTA);
    expect(s[0].titulo).toBe("Retome Química");
    expect(s[0].porque).toContain("48%");
    expect(s[0].porque).toContain("40 questões");
    expect(s[0].rota).toBe("/exams?area=quimica");
  });

  test("frente boa não vira problema inventado", () => {
    const painel = {
      ...painelVazio,
      frentes: {
        linhas: [{ chave: "historia", nome: "História", respondidas: 80, taxa: 78 }],
        tendencia: [],
      },
    };
    expect(montarSugestoes(painel, SEXTA)).toHaveLength(0);
  });

  test("a mesma frente não aparece duas vezes", () => {
    // Matemática caindo E fraca: as duas regras disparam. Dizer "revise
    // Matemática" logo acima de "retome Matemática" é a mesma frase duas
    // vezes, e a segunda faz o aluno duvidar da primeira.
    const painel = {
      ...painelVazio,
      frentes: {
        linhas: [{ chave: "matematica", nome: "Matemática", respondidas: 60, taxa: 44 }],
        tendencia: [{ chave: "matematica", nome: "Matemática", delta: -12 }],
      },
    };
    const s = montarSugestoes(painel, SEXTA);
    const sobreMatematica = s.filter((x) => x.id.includes("matematica"));
    expect(sobreMatematica).toHaveLength(1);
  });
});

describe("a redação", () => {
  test("quem nunca escreveu recebe o convite", () => {
    const painel = { ...painelVazio, redacao: { corrigidas: 0, serie: [] } };
    const s = montarSugestoes(painel, SEXTA);
    expect(s[0].id).toBe("redacao-primeira");
    expect(s[0].rota).toBe(ROTAS.REDACAO);
  });

  test("quem escreveu esta semana NÃO é cobrado", () => {
    const painel = {
      ...painelVazio,
      redacao: { corrigidas: 3, serie: [{ data: "2026-09-16", nota: 820 }] },
    };
    expect(montarSugestoes(painel, SEXTA)).toHaveLength(0);
  });

  test("quem parou há três semanas é lembrado, com o número de dias", () => {
    const painel = {
      ...painelVazio,
      redacao: { corrigidas: 3, serie: [{ data: "2026-08-28", nota: 820 }] },
    };
    const s = montarSugestoes(painel, SEXTA);
    expect(s[0].id).toBe("redacao-parada");
    expect(s[0].porque).toContain("21 dias");
  });
});

describe("o reconhecimento", () => {
  test("dois dias seguidos não é conquista, é terça-feira", () => {
    const painel = { ...painelVazio, constancia: { sequencia: 2 } };
    expect(montarSugestoes(painel, SEXTA)).toHaveLength(0);
  });

  test("uma sequência de verdade entra — e entra por ÚLTIMO", () => {
    const painel = {
      ...painelVazio,
      constancia: { sequencia: 9 },
      frentes: {
        linhas: [{ chave: "fisica", nome: "Física", respondidas: 30, taxa: 41 }],
        tendencia: [],
      },
    };
    const s = montarSugestoes(painel, SEXTA);
    expect(s[s.length - 1].id).toBe("conquista-sequencia");
    // Quem abriu o painel abriu para agir: o elogio é o fecho, não a manchete.
    expect(s[0].id).not.toBe("conquista-sequencia");
  });
});

describe("as leituras da Mentis", () => {
  test("só entram as que TÊM ação — uma frase sem destino não é sugestão", () => {
    const painel = {
      ...painelVazio,
      mentis: {
        leituras: [
          { id: "a", titulo: "Sem ação", texto: "…", acao: null },
          { id: "b", titulo: "Com ação", texto: "…", acao: { tipo: "mentis", rotulo: "Perguntar" } },
          { id: "c", titulo: "Vai para algum lugar", texto: "…", acao: { tipo: "ir", rotulo: "Ver", href: "/treino" } },
        ],
      },
    };
    const s = montarSugestoes(painel, SEXTA);
    expect(s).toHaveLength(1);
    expect(s[0].rota).toBe("/treino");
  });
});

describe("o balão inteiro", () => {
  test("aluno sem dado nenhum não recebe sugestão genérica", () => {
    // A asserção mais importante do arquivo. É trivial fazer um balão que
    // sempre tem o que dizer; o que custa é ele calar quando não sabe nada.
    expect(montarSugestoes(painelVazio, SEXTA)).toEqual([]);
    expect(montarSugestoes(null, SEXTA)).toEqual([]);
  });

  test("nunca passa de quatro itens", () => {
    const painel = {
      frentes: {
        linhas: [
          { chave: "quimica", nome: "Química", respondidas: 40, taxa: 40 },
          { chave: "fisica", nome: "Física", respondidas: 40, taxa: 45 },
        ],
        tendencia: [{ chave: "fisica", nome: "Física", delta: -14 }],
      },
      redacao: { corrigidas: 1, serie: [{ data: "2026-07-01" }] },
      constancia: { sequencia: 12 },
      mentis: {
        leituras: [
          { id: "m1", titulo: "t", texto: "x", acao: { tipo: "ir", rotulo: "Ver", href: "/a" } },
          { id: "m2", titulo: "t", texto: "x", acao: { tipo: "ir", rotulo: "Ver", href: "/b" } },
        ],
      },
    };
    expect(montarSugestoes(painel, SEGUNDA).length).toBeLessThanOrEqual(4);
  });

  test("toda sugestão é clicável e leva a algum lugar", () => {
    const painel = {
      ...painelVazio,
      constancia: { sequencia: 5 },
      frentes: {
        linhas: [{ chave: "fisica", nome: "Física", respondidas: 30, taxa: 41 }],
        tendencia: [],
      },
    };
    for (const s of montarSugestoes(painel, SEGUNDA)) {
      expect(typeof s.rota).toBe("string");
      expect(s.rota.startsWith("/")).toBe(true);
      expect(s.cta.length).toBeGreaterThan(0);
      expect(s.titulo.length).toBeGreaterThan(0);
    }
  });
});
