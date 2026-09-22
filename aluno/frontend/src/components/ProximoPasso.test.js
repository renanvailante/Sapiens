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
});
