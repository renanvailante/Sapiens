/**
 * A PRÁTICA DIRIGIDA trava três promessas que só se conferem abrindo o
 * navegador — por isso as funções são puras e testadas aqui:
 *
 *  · o Próximo Passo anuncia o ponto certo da fila do motor, e nunca o nome
 *    de um erro que não tem catálogo;
 *  · o plano do motor vira um endereço de prática com o porquê junto, e o
 *    texto do caso "sem catálogo" (que fala da ontologia) nunca viaja;
 *  · o fechamento só compara com amostra dos dois lados, e descreve em vez
 *    de alegar melhora.
 */
import {
  escolherPadrao,
  montarPraticaDirigida,
  abrirPraticaDirigida,
  pontoRepetido,
  resumoDaSerie,
  fraseDoFechamento,
  destinoDaMissao,
  recompensaDaSerie,
  TETO_QUESTOES,
} from "./praticaDirigida";

const linhaCausa = {
  origem: "error_trace",
  processo_id: "PROC-QUANT-02",
  processo_nome: "Inferir e aplicar relacao proporcional entre grandezas",
  sem_intervencao_catalogada: false,
  provisorio: true,
  erro_dominante: { id: "ERR-05", nome: "Confusao de direcao em relacao proporcional", sem_catalogo: false },
  percentual_acerto: 38,
  respondidas: 13,
};
const linhaSentinela = {
  origem: "error_trace",
  processo_id: "P-11",
  processo_nome: "Ler o gráfico",
  sem_intervencao_catalogada: true,
  erro_dominante: { id: "sentinela", nome: "erro não catalogado nesta versão", sem_catalogo: true },
};
const linhaDesempenho = {
  origem: "desempenho",
  processo_id: "P-12",
  processo_nome: "Comparar frações",
  erro_dominante: null,
  percentual_acerto: 40,
  respondidas: 10,
};

const detalhe = (over = {}) => ({
  processo: { id: "PROC-QUANT-02", nome: "Inferir e aplicar relacao proporcional entre grandezas" },
  desempenho: { respondidas: 13, acertos: 5, percentual_acerto: 38.5 },
  provisorio: true,
  intervencao: {
    origem: "error_trace",
    intervencao_id: "INT-03",
    objetivo: "Fixar a direção da relação.",
    como_praticar: ["Passo 1", "Passo 2", "Passo 3"],
    sinal_de_progresso: "Você detecta a resposta absurda.",
    praticar: {
      itens: Array.from({ length: 6 }, (_, i) => ({ item_id: `ITEM-${i + 1}` })),
      total_disponivel: 9,
    },
  },
  ...over,
});

describe("escolherPadrao", () => {
  test("fila vazia ou ausente não inventa ponto", () => {
    expect(escolherPadrao([])).toBeNull();
    expect(escolherPadrao(undefined)).toBeNull();
    expect(escolherPadrao(null)).toBeNull();
  });

  test("causa com catálogo vence sentinela, mesmo vindo depois na fila", () => {
    const e = escolherPadrao([linhaSentinela, linhaCausa]);
    expect(e.tipo).toBe("causa");
    expect(e.linha.processo_id).toBe("PROC-QUANT-02");
  });

  test("só sentinela: o ponto aparece, mas como traço (sem nome de erro)", () => {
    const e = escolherPadrao([linhaSentinela, linhaDesempenho]);
    expect(e.tipo).toBe("traco");
    expect(e.linha.processo_id).toBe("P-11");
  });

  test("sem traço nenhum, cai no desempenho medido", () => {
    expect(escolherPadrao([linhaDesempenho]).tipo).toBe("desempenho");
  });

  test("linha de desempenho sem medida não conta", () => {
    expect(escolherPadrao([{ ...linhaDesempenho, percentual_acerto: null }])).toBeNull();
    expect(escolherPadrao([{ ...linhaDesempenho, respondidas: 0 }])).toBeNull();
  });
});

describe("montarPraticaDirigida", () => {
  test("vira endereço de prática com no máximo TETO_QUESTOES inéditas", () => {
    const p = montarPraticaDirigida(detalhe(), { tipo: "causa", linha: linhaCausa });
    const ids = decodeURIComponent(p.url.split("item_ids=")[1]).split(",");
    expect(p.url.startsWith("/estudar/provas?item_ids=")).toBe(true);
    expect(ids).toHaveLength(TETO_QUESTOES);
    expect(ids[0]).toBe("ITEM-1");
    expect(p.state.dirigida.total).toBe(TETO_QUESTOES);
    expect(p.state.dirigida.restantes).toBe(4);
  });

  test("o porquê viaja junto: foco, erro, objetivo, dois passos e o sinal", () => {
    const d = montarPraticaDirigida(detalhe(), { tipo: "causa", linha: linhaCausa }).state.dirigida;
    // Rótulos de produto: o nome do catálogo não viaja nem no state.
    expect(d.foco).toBe("Proporção");
    expect(d.erro).toBe("Proporção invertida");
    expect(JSON.stringify(d)).not.toMatch(/relacao proporcional|Confusao de direcao/);
    expect(d.objetivo).toBe("Fixar a direção da relação.");
    expect(d.comoPraticar).toEqual(["Passo 1", "Passo 2"]);
    expect(d.sinal).toBe("Você detecta a resposta absurda.");
    expect(d.provisorio).toBe(true);
    expect(d.antes).toEqual({ respondidas: 13, acertos: 5, percentual: 38.5 });
  });

  test("plano sem intervenção catalogada NÃO leva o texto que fala da ontologia", () => {
    const semCatalogo = detalhe({
      intervencao: {
        origem: "error_trace",
        intervencao_id: null,
        objetivo: "Este tipo de erro ainda não tem intervenção catalogada nesta versão da ontologia.",
        como_praticar: ["x"],
        sinal_de_progresso: "y",
        praticar: { itens: [{ item_id: "A" }], total_disponivel: 1 },
      },
    });
    const d = montarPraticaDirigida(semCatalogo, { tipo: "traco", linha: linhaSentinela }).state.dirigida;
    expect(d.objetivo).toBeNull();
    expect(d.comoPraticar).toEqual([]);
    expect(d.sinal).toBeNull();
    expect(d.erro).toBeNull();
    expect(JSON.stringify(d)).not.toMatch(/ontologia/i);
  });

  test("acervo esgotado devolve null (quem chama cai na prática comum)", () => {
    const esgotado = detalhe({ intervencao: { origem: "sem_traco", praticar: { itens: [], total_disponivel: 0 } } });
    expect(montarPraticaDirigida(esgotado)).toBeNull();
    expect(montarPraticaDirigida(null)).toBeNull();
  });

  test("sem histórico no ponto, não há 'antes' para comparar", () => {
    const d = montarPraticaDirigida(detalhe({ desempenho: { respondidas: 0, acertos: 0, percentual_acerto: null } }))
      .state.dirigida;
    expect(d.antes).toBeNull();
  });
});

describe("abrirPraticaDirigida", () => {
  test("navega para a prática com o state quando o plano tem questões", async () => {
    const api = { get: jest.fn().mockResolvedValue({ data: detalhe() }) };
    const navegar = jest.fn();
    const ok = await abrirPraticaDirigida({ api, navegar, processoId: "PROC-QUANT-02", escolha: { tipo: "causa", linha: linhaCausa } });
    expect(ok).toBe(true);
    expect(api.get).toHaveBeenCalledWith("/motor/habilidade/PROC-QUANT-02");
    expect(navegar.mock.calls[0][0]).toMatch(/^\/estudar\/provas\?item_ids=/);
    expect(navegar.mock.calls[0][1].state.dirigida.foco).toBe("Proporção");
  });

  test("falha de rede nunca deixa o clique sem destino", async () => {
    const api = { get: jest.fn().mockRejectedValue(new Error("rede")) };
    const navegar = jest.fn();
    const ok = await abrirPraticaDirigida({ api, navegar, processoId: "P-10" });
    expect(ok).toBe(false);
    expect(navegar).toHaveBeenCalledWith("/estudar/provas");
  });

  test("sem processo, vai direto para a reserva sem chamar o servidor", async () => {
    const api = { get: jest.fn() };
    const navegar = jest.fn();
    await abrirPraticaDirigida({ api, navegar, processoId: null, reserva: "/hoje" });
    expect(api.get).not.toHaveBeenCalled();
    expect(navegar).toHaveBeenCalledWith("/hoje");
  });
});

describe("pontoRepetido", () => {
  test("um erro isolado não é padrão; dois no mesmo ponto são", () => {
    const um = [{ acertou: false, causa_raiz: { processo_id: "P-1" } }];
    expect(pontoRepetido(um)).toBeNull();
    const dois = [...um, { acertou: true }, { acertou: false, causa_raiz: { processo_id: "P-1" } }];
    expect(pontoRepetido(dois)).toEqual({ processoId: "P-1", vezes: 2 });
  });

  test("acerto com causa_raiz (não deveria vir) não conta como erro", () => {
    const r = [
      { acertou: true, causa_raiz: { processo_id: "P-1" } },
      { acertou: true, causa_raiz: { processo_id: "P-1" } },
    ];
    expect(pontoRepetido(r)).toBeNull();
  });
});

describe("resumoDaSerie e fraseDoFechamento", () => {
  const serie = (certas, total) =>
    Array.from({ length: total }, (_, i) => ({ acertou: i < certas }));
  const dirigida = { antes: { respondidas: 13, acertos: 5, percentual: 38.5 } };

  test("conta acertos mesmo sem prática dirigida, e aí não compara", () => {
    const r = resumoDaSerie(serie(3, 5));
    expect(r).toMatchObject({ total: 5, acertos: 3, percentual: 60, comparacao: null });
    expect(fraseDoFechamento(r)).toBeNull();
  });

  test("acima do histórico: descreve e avisa que a série é curta", () => {
    const r = resumoDaSerie(serie(4, 5), dirigida);
    expect(r.comparacao).toMatchObject({ antes: 39, agora: 80, sentido: "acima" });
    const f = fraseDoFechamento(r);
    expect(f).toContain("39%");
    expect(f).toContain("4 de 5");
    expect(f).toMatch(/série curta/);
    expect(f).not.toMatch(/aprendeu|dominou/i);
  });

  test("abaixo e igual também têm frase, sem drama", () => {
    expect(resumoDaSerie(serie(0, 5), dirigida).comparacao.sentido).toBe("abaixo");
    expect(resumoDaSerie(serie(2, 5), dirigida).comparacao.sentido).toBe("igual");
    expect(fraseDoFechamento(resumoDaSerie(serie(2, 5), dirigida))).toMatch(/Mesmo patamar/);
  });

  test("amostra curta de qualquer lado não compara", () => {
    expect(resumoDaSerie(serie(2, 2), dirigida).comparacao).toBeNull();
    expect(resumoDaSerie(serie(4, 5), { antes: { respondidas: 2, acertos: 0, percentual: 0 } }).comparacao).toBeNull();
  });

  test("série vazia (reabriu um conjunto já terminado) não divide por zero", () => {
    expect(resumoDaSerie([], dirigida)).toMatchObject({ total: 0, percentual: null, comparacao: null });
  });
});

describe("destinoDaMissao", () => {
  const pratica = { processoId: "PROC-QUANT-02", escolha: { tipo: "causa" } };

  test("missão de prática vai ao padrão quando o motor aponta um", () => {
    for (const id of ["responder5", "responder15", "acertar8"]) {
      expect(destinoDaMissao({ id, rota: "/estudar/provas", cta: "Praticar" }, pratica).tipo).toBe("dirigida");
    }
  });

  test("sem padrão, ou missão de outro tipo, segue a rota do servidor", () => {
    expect(destinoDaMissao({ id: "responder5", rota: "/estudar/provas", cta: "Praticar" }, null))
      .toEqual({ tipo: "rota", rota: "/estudar/provas", cta: "Praticar" });
    expect(destinoDaMissao({ id: "revisao", rota: "/agenda#revisoes", cta: "Revisar" }, pratica).tipo).toBe("rota");
    expect(destinoDaMissao({ id: "treino", rota: "/estudar/treino", cta: "Treinar" }, pratica).tipo).toBe("rota");
  });
});

describe("recompensaDaSerie — só celebra o que o servidor contou", () => {
  const estado = {
    nivel: { xp_total: 680 },
    ofensiva: { dias: 4, estudou_hoje: true },
    missoes: [
      { id: "responder5", concluida: true, resgatada: false, sparks: 5 },
      { id: "acertar8", concluida: false, resgatada: false },
      { id: "revisao", concluida: true, resgatada: true },
    ],
  };

  test("XP é a diferença real; sequência garantida; só missão pronta e não resgatada", () => {
    const r = recompensaDaSerie(estado, 640, 4);
    expect(r.xp).toBe(40);
    expect(r.diaGarantido).toBe(4);
    expect(r.seguidas).toBe(4);
    expect(r.prontas.map((m) => m.id)).toEqual(["responder5"]);
  });

  test("sem baseline de XP, ou sem estudo hoje, não inventa", () => {
    const r = recompensaDaSerie({ ...estado, ofensiva: { dias: 4, estudou_hoje: false } }, null, 2);
    expect(r.xp).toBe(0);
    expect(r.diaGarantido).toBe(0);
    expect(r.seguidas).toBe(0); // dois seguidos acontecem por acaso
  });

  test("missão resgatada na própria tela some da lista", () => {
    expect(recompensaDaSerie(estado, 640, 0, new Set(["responder5"])).prontas).toEqual([]);
  });

  test("sem estado (rede falhou), nada", () => {
    expect(recompensaDaSerie(null, 640, 5)).toEqual({ xp: 0, diaGarantido: 0, seguidas: 5, prontas: [] });
  });
});
