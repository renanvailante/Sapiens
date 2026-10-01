/**
 * A MICROVITÓRIA do "O que mudou" — a única linha do Hoje que responde
 * "estou evoluindo?". Três promessas travadas aqui:
 *
 *  · só marco de ACERTO vira vitória (revisão acertada, acerto em contexto
 *    novo); erro recorrente e revisão falha nunca aparecem como conquista;
 *  · depois de três dias ela deixa de ser notícia;
 *  · o teto de quatro linhas não a corta quando há muitas pendências.
 */
jest.mock("lucide-react", () => new Proxy({}, { get: () => () => null }), { virtual: true });
jest.mock("react-router-dom", () => ({ Link: ({ children }) => children }), { virtual: true });

// eslint-disable-next-line import/first
import { eventosDoDia, microvitoria } from "./OQueMudou";

const haDias = (n) => new Date(Date.now() - n * 86400000).toISOString();

const trajetoria = (marcos, nome = "Interpretar a relação entre grandezas") => ({
  habilidades: [{ processo_id: "P-10", processo_nome: nome, marcos }],
});

describe("microvitoria", () => {
  test("sem trajetória, sem vitória", () => {
    expect(microvitoria(null)).toBeNull();
    expect(microvitoria({ habilidades: [] })).toBeNull();
  });

  test("marco de erro nunca vira vitória", () => {
    const t = trajetoria([
      { tipo: "raiz", quando: haDias(0) },
      { tipo: "reteste_falho", quando: haDias(0) },
      { tipo: "intervencao", quando: haDias(0) },
    ]);
    expect(microvitoria(t)).toBeNull();
  });

  test("pega o acerto mais recente entre todas as habilidades", () => {
    const t = {
      habilidades: [
        { processo_nome: "A", marcos: [{ tipo: "reteste_ok", quando: haDias(2) }] },
        { processo_nome: "B", marcos: [{ tipo: "transferencia", quando: haDias(1) }] },
      ],
    };
    const v = microvitoria(t);
    expect(v.tipo).toBe("transferencia");
    expect(v.processo_nome).toBe("B");
  });

  test("velha demais deixa de ser notícia", () => {
    expect(microvitoria(trajetoria([{ tipo: "reteste_ok", quando: haDias(5) }]))).toBeNull();
  });
});

describe("eventosDoDia com a vitória", () => {
  test("revisão acertada aparece com o nome do ponto e leva à trajetória", () => {
    const eventos = eventosDoDia({ trajetoria: trajetoria([{ tipo: "reteste_ok", quando: haDias(0) }]) });
    const v = eventos.find((e) => e.chave === "vitoria");
    expect(v.titulo).toBe("A revisão de «Interpretar a relação entre grandezas» saiu certa");
    expect(v.rota).toBe("/progresso#trajetoria");
  });

  test("o teto de quatro não corta a vitória quando há muitas pendências", () => {
    const hoje = new Date();
    const dia = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
    const eventos = eventosDoDia({
      revisoes: { resumo: { questoes: 2 } },
      redacoes: [{ avaliacao: { nota_total: 720, corrigida_em: haDias(0) } }],
      cronograma: {
        dias: [{
          data: dia,
          blocos: [
            { id: "b1", titulo: "Funções", concluido: false },
            { id: "b2", titulo: "Curso", tipo: "curso", concluido: false },
          ],
        }],
      },
      engajamento: { ofensiva: { dias: 5, estudou_hoje: false } },
      trajetoria: trajetoria([{ tipo: "transferencia", quando: haDias(1) }]),
    });
    expect(eventos).toHaveLength(4);
    expect(eventos.map((e) => e.chave)).toContain("vitoria");
  });
});

describe("a conquista", () => {
  test("usa o nome que o catálogo de fato tem (label), nunca 'undefined'", () => {
    const eventos = eventosDoDia({ conquistas: [{ id: "10q", label: "10 questões", desbloqueada: true }] });
    const c = eventos.find((e) => e.chave === "conquista");
    expect(c.titulo).toBe('Você desbloqueou "10 questões"');
    expect(c.titulo).not.toMatch(/undefined/);
  });
});

