// Transforma a resposta de `GET /treino/mapa` numa descrição de cena pura
// (sem React/Three). `treino_grafo_v0_2.py` (backend) continua sendo a única
// fonte de `x`, `y`, `estado`, `bioma_id` e `relation` — aqui só se decide
// ONDE, em que ilha e em que altitude cada coisa fica, 100% no cliente.
//
// A composição é um ARQUIPÉLAGO: o vetor do nó em relação à âncora do seu
// bioma é espalhado (`ESPALHAMENTO`) enquanto as próprias âncoras são
// afastadas uma da outra (`SEPARACAO_ILHAS`). O resultado são 6 massas de
// terra distintas, com abismo entre elas — e o vazio passa a fazer parte do
// desenho, em vez de tudo se aglomerar no centro.
import { hash01 } from "./noise";
import { BIOMA_ARCHETYPES, PESO_ESTADO } from "./biomaArchetypes";

export const SOURCE_W = 1000;
export const SOURCE_H = 640;
export const SCALE = 0.072;

/** Afastamento entre as ilhas (aplicado às âncoras de bioma). */
export const SEPARACAO_ILHAS = 22;
/** Espalhamento dos nós DENTRO da própria ilha. */
export const ESPALHAMENTO = 21;

/** Altura de um pavimento. */
export const NIVEL = 5.5;
/** Espessura da laje que forma o piso de um quarteirão. */
export const LAJE = 0.5;

// Espelha `_ANCORA_BIOMA` de treino_grafo_v0_2.py (backend) — camada de
// produto, não ontologia. Se o backend rebalancear as âncoras, este mapa
// client-side precisa ser atualizado junto.
const ANCORA_BIOMA_SRC = {
  perceber: [170, 480],
  relacionar: [430, 560],
  representar: [700, 470],
  investigar: [880, 300],
  integrar: [700, 130],
  decidir: [380, 110],
};

export const BIOMA_IDS = Object.keys(ANCORA_BIOMA_SRC);

export const ESTADO_LABEL = {
  unknown: "Não descoberto",
  discovered: "Percebido",
  available: "Disponível",
  in_progress: "Em progresso",
  mastered: "Dominado",
};

/** Centro da ilha de um bioma, no plano XZ do mundo. */
export const ANCORA_MUNDO = Object.fromEntries(
  BIOMA_IDS.map((id) => {
    const [sx, sy] = ANCORA_BIOMA_SRC[id];
    return [
      id,
      {
        x: (sx - SOURCE_W / 2) * SCALE * SEPARACAO_ILHAS,
        z: (sy - SOURCE_H / 2) * SCALE * SEPARACAO_ILHAS,
      },
    ];
  }),
);

/** Cota do terreno da ilha — cada bioma tem a sua altitude. É o que cria
 * desnível de verdade entre regiões e obriga as rotas a subirem. */
export function alturaIlha(biomaId) {
  return BIOMA_ARCHETYPES[biomaId].nivelBase * NIVEL;
}

/** Posição de um nó: âncora da ilha + deslocamento local espalhado. */
export function posicaoDoNo(srcX, srcY, biomaId) {
  const [ax, ay] = ANCORA_BIOMA_SRC[biomaId];
  const centro = ANCORA_MUNDO[biomaId];
  return {
    x: centro.x + (srcX - ax) * SCALE * ESPALHAMENTO,
    z: centro.z + (srcY - ay) * SCALE * ESPALHAMENTO,
  };
}

/** Pavimento local do nó dentro da própria ilha (0..variação). */
export function nivelDoNo(habId, biomaId) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  return Math.floor(hash01(`${habId}:nivel`) * (arq.nivelVariacao + 1));
}

/** Cota do piso de um quarteirão: terreno da ilha + pavimento local. */
export function alturaDoNo(habId, biomaId) {
  return alturaIlha(biomaId) + nivelDoNo(habId, biomaId) * NIVEL + LAJE;
}

/** Resposta de `GET /treino/mapa` + `nodeIndex` -> descrição da cena.
 * `nos` traz TODOS os nós (inclusive `unknown`, que viram massa bruta na
 * ilha); `arestas` só as visíveis, com a mesma regra de sempre. */
export function construirCena(mapaData, nodeIndex) {
  const nos = [];
  for (const bioma of mapaData.biomas) {
    for (const n of bioma.nodes) {
      const { x, z } = posicaoDoNo(n.x, n.y, bioma.bioma_id);
      nos.push({
        hab_id: n.hab_id,
        nome: n.nome,
        estado: n.estado,
        respondidas: n.respondidas,
        biomaId: bioma.bioma_id,
        nivel: nivelDoNo(n.hab_id, bioma.bioma_id),
        position: [x, alturaDoNo(n.hab_id, bioma.bioma_id), z],
      });
    }
  }

  const porId = {};
  for (const n of nos) porId[n.hab_id] = n;
  const nosVisiveis = nos.filter((n) => n.estado !== "unknown");

  const arestas = [];
  for (const a of mapaData.arestas) {
    const s = porId[a.source];
    const t = porId[a.target];
    if (!s || !t || s.estado === "unknown" || t.estado === "unknown") continue;
    arestas.push({
      id: `${a.source}-${a.target}`,
      relation: a.relation,
      source: a.source,
      target: a.target,
      sourceMastered: s.estado === "mastered",
      biomaId: s.biomaId,
      biomaAlvo: t.biomaId,
      from: s.position,
      to: t.position,
      peso: Math.min(PESO_ESTADO[s.estado], PESO_ESTADO[t.estado]),
    });
  }

  // Extensão do mundo, para enquadrar câmera e névoa sem números mágicos.
  let raio = 1;
  for (const n of nos) raio = Math.max(raio, Math.hypot(n.position[0], n.position[2]));
  const limites = { raio: raio + 150 };

  return { nos, nosVisiveis, arestas, limites };
}
