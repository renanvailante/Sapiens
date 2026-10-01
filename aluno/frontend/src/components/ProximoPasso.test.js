/**
 * A ESCADA DO PRÓXIMO PASSO.
 *
 * `escolherPasso` é pura e exportada de propósito: ela decide a ÚNICA ação
 * que o Painel oferece, e a escolha errada manda o aluno para o lugar errado
 * sem nada na tela acusando. Foi exatamente o que aconteceu — ver o teste
 * "conta nova cai em praticar" abaixo, que trava o defeito de 2026-09-21.
 */
// `lucide-react` e o `react-router-dom` 7 são ESM e o jest do CRA não os
// resolve. `escolherPasso` é pura e não toca em nenhum dos dois — o mock
// existe só para o módulo carregar. É o mesmo caminho que
// `PortaisDaJornada.test.js` já usa, e é mais barato que reconfigurar o
// transform para pacotes que a aplicação exercita de verdade em produção.
jest.mock("lucide-react", () => new Proxy({}, {
  get: () => () => null,
}), { virtual: true });
jest.mock("react-router-dom", () => ({
  Link: ({ children }) => children,
  useNavigate: () => () => {},
}), { virtual: true });

// eslint-disable-next-line import/first
import { escolherPasso } from "./ProximoPasso";

/** Como `/treino/habilidades` responde para quem NUNCA respondeu nada: as 56
 *  vêm sempre, zeradas e classificadas como "sem_dados". */
const catalogoIntocado = (n = 56) =>
  Array.from({ length: n }, (_, i) => ({
    hab_id: `HAB-${String(i + 1).padStart(2, "0")}`,
    nome: `Habilidade ${i + 1}`,
    respondidas: 0,
    acertos: 0,
    percentual: null,
    classificacao: "sem_dados",
  }));

const vazio = { revisoes: null, cronograma: null, habilidades: [] };

describe("escolherPasso", () => {
  test("conta nova cai em PRATICAR, não numa missão sorteada do catálogo", () => {
    // O defeito: as 56 intocadas passavam no filtro `classificacao !== "forte"`
    // de `missaoAtual`, que então devolvia HAB-01 e nunca `null`. O aluno
    // recém-cadastrado — inclusive o que veio de anúncio pago prometendo "10
    // questões" — abria o Painel em "Território novo · Habilidade 1" com
    // destino ao mapa 3D, em vez da prova.
    const passo = escolherPasso({ ...vazio, habilidades: catalogoIntocado() });
    expect(passo.chave).toBe("praticar");
    expect(passo.rota).toBe("/estudar/provas");
  });

  test("uma única habilidade tocada já devolve a trilha", () => {
    const habilidades = catalogoIntocado();
    habilidades[7] = { ...habilidades[7], respondidas: 4, acertos: 1, percentual: 25, classificacao: "fraca" };
    const passo = escolherPasso({ ...vazio, habilidades });
    expect(passo.chave).toBe("hab-HAB-08");
    expect(passo.rota).toBe("/treino?hab=HAB-08");
  });

  test("sem habilidade nenhuma na resposta, também cai em praticar", () => {
    expect(escolherPasso(vazio).chave).toBe("praticar");
    expect(escolherPasso({ ...vazio, habilidades: undefined }).chave).toBe("praticar");
  });

  test("revisão vencida ganha de tudo — prazo vence preferência", () => {
    const passo = escolherPasso({
      ...vazio,
      revisoes: { resumo: { questoes: 3 } },
      habilidades: catalogoIntocado(),
    });
    expect(passo.chave).toBe("revisao");
  });

  test("o que o aluno marcou na agenda ganha do que o Sapiens escolheria", () => {
    const hoje = new Date();
    const dia = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
    const passo = escolherPasso({
      ...vazio,
      cronograma: { dias: [{ data: dia, blocos: [{ id: "b1", titulo: "Funções", concluido: false, rota: "/estudar/treino" }] }] },
      habilidades: catalogoIntocado(),
    });
    expect(passo.chave).toBe("bloco-b1");
  });

  // ---------------------------------------------------------------------
  // O POR QUÊ (2026-09-28). A fila do motor já chegava ao Painel e não
  // mudava a ação; agora ela entra na escada.
  // ---------------------------------------------------------------------

  const causa = {
    origem: "error_trace",
    processo_id: "P-10",
    processo_nome: "Interpretar a relação entre grandezas",
    sem_intervencao_catalogada: false,
    provisorio: true,
    ocorrencias_raiz: 4,
    erro_dominante: { nome: "Inverter a direção da proporção", sem_catalogo: false },
  };
  const desempenho = {
    origem: "desempenho",
    processo_id: "P-12",
    processo_nome: "Comparar frações",
    percentual_acerto: 40,
    respondidas: 10,
  };

  test("quem só fez provas NÃO recebe 'Seu primeiro passo' — o produto se lembra dele", () => {
    // O defeito: a trilha só lê o treino (`treino_agregado`); quem tinha 200
    // questões de prova e nunca abriu o mapa caía no degrau da conta nova.
    const passo = escolherPasso({ ...vazio, habilidades: catalogoIntocado(), totalRespondidas: 200 });
    expect(passo.chave).toBe("continuar");
    expect(passo.olho).not.toMatch(/primeiro/i);
    expect(passo.porque).toContain("200 respostas");
  });

  test("o padrão de erro com causa vence a trilha e abre prática dirigida", () => {
    const habilidades = catalogoIntocado();
    habilidades[7] = { ...habilidades[7], respondidas: 4, acertos: 1, percentual: 25, classificacao: "fraco" };
    const passo = escolherPasso({ ...vazio, habilidades, padroes: [causa], totalRespondidas: 40 });
    expect(passo.chave).toBe("padrao-P-10");
    expect(passo.titulo).toBe("Interpretar a relação entre grandezas");
    expect(passo.porque).toContain("«Inverter a direção da proporção»");
    expect(passo.dirigida.processoId).toBe("P-10");
    expect(passo.provisorio).toBe(true);
  });

  test("revisão e cronograma continuam acima do padrão", () => {
    const comRevisao = escolherPasso({ ...vazio, revisoes: { resumo: { questoes: 2 } }, padroes: [causa] });
    expect(comRevisao.chave).toBe("revisao");
  });

  test("a revisão diz DE QUE é a questão que voltou", () => {
    const passo = escolherPasso({
      ...vazio,
      revisoes: { resumo: { questoes: 2 }, itens: [{ processo_nome: "Ler o gráfico", rotulo: "erro recorrente" }] },
    });
    expect(passo.porque).toContain("«Ler o gráfico»");
    expect(passo.porque).toContain("erro recorrente");
  });

  test("desempenho sem traço é evidência mais fraca: fica ABAIXO da trilha", () => {
    const habilidades = catalogoIntocado();
    habilidades[2] = { ...habilidades[2], respondidas: 5, acertos: 1, percentual: 20, classificacao: "fraco" };
    expect(escolherPasso({ ...vazio, habilidades, padroes: [desempenho] }).chave).toBe("hab-HAB-03");
    const semTrilha = escolherPasso({ ...vazio, habilidades: catalogoIntocado(), padroes: [desempenho], totalRespondidas: 30 });
    expect(semTrilha.chave).toBe("padrao-P-12");
    expect(semTrilha.porque).toContain("40%");
    expect(semTrilha.provisorio).toBe(false);
  });

  test("causa sem catálogo nunca mostra o nome do erro", () => {
    const sentinela = {
      ...causa,
      sem_intervencao_catalogada: true,
      erro_dominante: { nome: "erro não catalogado nesta versão", sem_catalogo: true },
    };
    const passo = escolherPasso({ ...vazio, padroes: [sentinela], totalRespondidas: 20 });
    expect(passo.chave).toBe("padrao-P-10");
    expect(passo.porque).not.toMatch(/catalogado/);
    expect(passo.porque).toContain("4 dos seus erros");
  });
});

