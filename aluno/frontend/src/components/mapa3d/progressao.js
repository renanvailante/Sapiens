// Camada de PROGRESSÃO — decide o que o aluno vê, sobre os dados que o
// backend já manda. Nada aqui altera ontologia, id, API ou conteúdo: é
// apresentação.
//
// O backend continua fazendo o que sempre fez (`estado` por distância no
// grafo, nunca cadeado). Esta camada aperta a abertura: em vez de revelar
// tudo o que está a até 3 arestas de distância, o mundo começa com ~30% das
// missões acessíveis e vai se abrindo à medida que as vizinhas são
// praticadas.
//
// Três leituras:
//   acessivel   dá para entrar; aparece acesa no mapa e completa na lista
//   entrevisto  vizinha de uma acessível: aparece como silhueta, sem nome e
//               sem clique — é o que mantém o mundo misterioso
//   oculto      nem existe ainda; no mapa continua sendo natureza bruta
//
// A regra de abertura é a mesma que a paisagem já contava: praticar uma
// missão acende as vizinhas dela no grafo.
import { missaoDe } from "./missoes";

/** Fração das missões acessíveis no começo. */
export const FRACAO_INICIAL = 0.3;

const ENGAJADA = new Set(["in_progress", "mastered"]);

function vizinhanca(arestas) {
  const mapa = {};
  for (const a of arestas) {
    (mapa[a.source] ??= new Set()).add(a.target);
    (mapa[a.target] ??= new Set()).add(a.source);
  }
  return mapa;
}

/** Sementes: as primeiras missões de cada bioma, na ordem canônica, entre as
 * que o backend já revela. Determinístico — todo aluno começa pelo mesmo
 * conjunto, e ele soma ~30% das 56. */
function sementes(biomas) {
  const escolhidas = new Set();
  for (const bioma of biomas) {
    // A cota sai do tamanho REAL do bioma (não do que o backend já revelou),
    // senão uma região ainda fechada contribui com quase nada e a abertura
    // total cai bem abaixo dos 30% pretendidos.
    const quantas = Math.max(1, Math.round(bioma.nodes.length * FRACAO_INICIAL));
    const reveladas = bioma.nodes.filter((n) => n.estado !== "unknown");
    for (const n of reveladas.slice(0, quantas)) escolhidas.add(n.hab_id);
  }
  return escolhidas;
}

/** Devolve os biomas com o `estado` já traduzido para o que a tela deve
 * mostrar, mais os campos de apresentação (`rotulo`, `familia`, `variante`,
 * `interativo`, `acesso`). O `nome` original é preservado no objeto porque
 * segue sendo insumo de backend — mas nenhuma tela o exibe. */
export function aplicarProgressao(biomas, arestas) {
  const vizinhos = vizinhanca(arestas);
  const porId = {};
  for (const bioma of biomas) for (const n of bioma.nodes) porId[n.hab_id] = n;

  const semente = sementes(biomas);
  const engajadas = new Set(
    Object.values(porId).filter((n) => ENGAJADA.has(n.estado)).map((n) => n.hab_id),
  );

  const acessiveis = new Set();
  for (const n of Object.values(porId)) {
    if (n.estado === "unknown") continue;
    const temVizinhoEngajado = [...(vizinhos[n.hab_id] ?? [])].some((v) => engajadas.has(v));
    if (engajadas.has(n.hab_id) || semente.has(n.hab_id) || temVizinhoEngajado) {
      acessiveis.add(n.hab_id);
    }
  }

  const entrevistos = new Set();
  for (const n of Object.values(porId)) {
    if (n.estado === "unknown" || acessiveis.has(n.hab_id)) continue;
    if ([...(vizinhos[n.hab_id] ?? [])].some((v) => acessiveis.has(v))) entrevistos.add(n.hab_id);
  }

  const traduzir = (n) => {
    const missao = missaoDe(n.hab_id);
    if (acessiveis.has(n.hab_id)) {
      return {
        ...n,
        ...missao,
        acesso: "acessivel",
        interativo: true,
        // Quem já praticou mantém o próprio estado; o resto entra como
        // disponível, que é o tier aceso do mapa.
        estado: ENGAJADA.has(n.estado) ? n.estado : "available",
      };
    }
    if (entrevistos.has(n.hab_id)) {
      return { ...n, ...missao, acesso: "entrevisto", interativo: false, estado: "discovered" };
    }
    return { ...n, ...missao, acesso: "oculto", interativo: false, estado: "unknown" };
  };

  return biomas.map((bioma) => ({ ...bioma, nodes: bioma.nodes.map(traduzir) }));
}

/** Missões que destravam uma dada missão entrevista — usado pela lista para
 * dizer o que falta praticar, sem revelar nada que ainda esteja no escuro. */
export function destravadaPor(habId, biomas, arestas) {
  const porId = {};
  for (const bioma of biomas) for (const n of bioma.nodes) porId[n.hab_id] = n;
  const saida = [];
  for (const a of arestas) {
    const outro = a.source === habId ? a.target : a.target === habId ? a.source : null;
    if (!outro) continue;
    const no = porId[outro];
    if (no?.acesso === "acessivel") saida.push(no);
  }
  return saida;
}
