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
import { eventosDoDia, microvitoria, conquistasDoDia } from "./OQueMudou";

const haDias = (n) => new Date(Date.now() - n * 86400000).toISOString();

const trajetoria = (marcos, nome = "Interpretar a relação entre grandezas") => ({
  habilidades: [{ processo_id: "PROC-QUANT-02", processo_nome: nome, marcos }],
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
        { processo_id: "PROC-QUANT-01", processo_nome: "A", marcos: [{ tipo: "reteste_ok", quando: haDias(2) }] },
        { processo_id: "PROC-TEXT-02", processo_nome: "B", marcos: [{ tipo: "transferencia", quando: haDias(1) }] },
      ],
    };
    const v = microvitoria(t);
    expect(v.tipo).toBe("transferencia");
    // Rótulo de produto do processo, não o nome que veio na linha.
    expect(v.processo_nome).toBe("Ler nas entrelinhas");
  });

  test("velha demais deixa de ser notícia", () => {
    expect(microvitoria(trajetoria([{ tipo: "reteste_ok", quando: haDias(5) }]))).toBeNull();
  });
});

describe("eventosDoDia com a vitória", () => {
  test("revisão acertada aparece com o nome do ponto e leva à trajetória", () => {
    const eventos = eventosDoDia({ trajetoria: trajetoria([{ tipo: "reteste_ok", quando: haDias(0) }]) });
    const v = eventos.find((e) => e.chave === "vitoria");
    expect(v.titulo).toBe("A revisão de «Proporção» saiu certa");
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


describe("conquistasDoDia — conquista é notícia só no dia em que aparece", () => {
  const c = (id, desbloqueada = true) => ({ id, label: id, desbloqueada });

  test("primeira visita não anuncia nada (não há como saber o que é novo)", () => {
    const { doDia, vistas } = conquistasDoDia([c("10q"), c("100q")], null, "2026-10-01");
    expect(doDia).toEqual([]);
    expect(vistas).toEqual({ "10q": "antes", "100q": "antes" });
  });

  test("a recém-desbloqueada vale no dia em que apareceu, e some no seguinte", () => {
    const vistas = { "10q": "antes" };
    const hoje = conquistasDoDia([c("10q"), c("100q")], vistas, "2026-10-01");
    expect(hoje.doDia.map((x) => x.id)).toEqual(["100q"]);
    const reabriu = conquistasDoDia([c("10q"), c("100q")], hoje.vistas, "2026-10-01");
    expect(reabriu.doDia.map((x) => x.id)).toEqual(["100q"]);
    const amanha = conquistasDoDia([c("10q"), c("100q")], hoje.vistas, "2026-10-02");
    expect(amanha.doDia).toEqual([]);
  });

  test("bloqueada nunca entra", () => {
    expect(conquistasDoDia([c("10q", false)], {}, "2026-10-01").doDia).toEqual([]);
  });
});

describe("trechos guardados que voltaram (revisão programada)", () => {
  test("aparece com a contagem e de onde veio o primeiro", () => {
    const eventos = eventosDoDia({ lembretes: { vencidos: 2, primeiro_vencido: { titulo: "Termoquímica · Estação 2" } } });
    const l = eventos.find((e) => e.chave === "lembretes");
    expect(l.titulo).toBe("2 trechos que você guardou voltaram hoje");
    expect(l.detalhe).toContain("«Termoquímica · Estação 2»");
    expect(l.rota).toBe("/agenda#lembretes");
  });

  test("sem trecho vencido, sem linha", () => {
    expect(eventosDoDia({ lembretes: { vencidos: 0 } }).find((e) => e.chave === "lembretes")).toBeUndefined();
    expect(eventosDoDia({ lembretes: null }).find((e) => e.chave === "lembretes")).toBeUndefined();
  });
});
