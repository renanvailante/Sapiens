// Transforma a resposta de `GET /treino/mapa` numa descrição de cena pura
// (sem React/Three): posição de mundo, NÍVEL construído e visibilidade de
// cada nó/conexão. `treino_grafo_v0_2.py` (backend) continua sendo a única
// fonte de `x`, `y`, `estado`, `bioma_id` e `relation` — aqui só se decide
// em que pavimento da cidade cada coisa fica, 100% no cliente.
//
// A altura não é mais relevo de ruído: é NÍVEL. A cidade tem pavimentos de
// altura fixa, e cada habilidade ocupa um deles. Isso é o que faz escada,
// ponte e platô se encaixarem em vez de flutuarem sobre um terreno ondulado.
import { hash01 } from "./noise";
import { BIOMA_ARCHETYPES, PESO_ESTADO } from "./biomaArchetypes";
import { BALOES_CURADOS } from "./balloonContent";

export const SOURCE_W = 1000;
export const SOURCE_H = 640;
export const SCALE = 0.072;

export const WORLD_WIDTH = SOURCE_W * SCALE * 1.18;
export const WORLD_DEPTH = SOURCE_H * SCALE * 1.18;

/** Altura de um pavimento. Tudo que sobe na cidade sobe em múltiplos disto. */
export const NIVEL = 1.7;
/** Espessura da laje que forma o piso de um quarteirão. */
export const LAJE = 0.5;
/** Topo do plinto — o "chão" da cidade, de onde as torres saem. */
export const BASE_TOPO = 0;
export const BASE_ESPESSURA = 3.4;

// Espelha `_ANCORA_BIOMA` de treino_grafo_v0_2.py (backend) — camada de
// produto, não ontologia. Copiado aqui porque o mundo é montado inteiramente
// no cliente; se o backend rebalancear as âncoras, este mapa precisa ser
// atualizado junto.
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

/** Mapeia o canvas virtual 2D do backend (1000×640) para o plano XZ do
 * mundo 3D. `y` do backend vira **Z**; **Y** fica só para altura — nunca
 * confundir os dois eixos. */
export function toWorld(x, y) {
  return { x: (x - SOURCE_W / 2) * SCALE, z: (y - SOURCE_H / 2) * SCALE };
}

export const ANCORA_MUNDO = Object.fromEntries(
  Object.entries(ANCORA_BIOMA_SRC).map(([id, [x, y]]) => [id, toWorld(x, y)]),
);

/** Pavimento de uma habilidade: base do distrito + variação estável por
 * `hab_id`. Determinístico — todo aluno vê a mesma cidade. */
export function nivelDoNo(habId, biomaId) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  return arq.nivelBase + Math.floor(hash01(`${habId}:nivel`) * (arq.nivelVariacao + 1));
}

/** Cota do PISO de um pavimento (topo da laje). */
export function alturaDeNivel(nivel) {
  return BASE_TOPO + nivel * NIVEL + LAJE;
}

/** Bioma do ponto do mundo mais próximo — usado para pintar o plinto por
 * distrito. */
export function biomaMaisProximo(x, z) {
  let melhor = null;
  let dist = Infinity;
  for (const id of BIOMA_IDS) {
    const a = ANCORA_MUNDO[id];
    const d = Math.hypot(a.x - x, a.z - z);
    if (d < dist) {
      dist = d;
      melhor = id;
    }
  }
  return { biomaId: melhor, distancia: dist };
}

/** Resposta de `GET /treino/mapa` + `nodeIndex` (já montado pela página) ->
 * descrição da cena. `nos` traz TODOS os nós (inclusive `unknown`, que viram
 * massa bruta na cidade); `arestas` só as visíveis, com a mesma regra de
 * sempre (as duas pontas != `unknown`). */
export function construirCena(mapaData, nodeIndex) {
  const nos = [];
  for (const bioma of mapaData.biomas) {
    for (const n of bioma.nodes) {
      const { x, z } = toWorld(n.x, n.y);
      const nivel = nivelDoNo(n.hab_id, bioma.bioma_id);
      nos.push({
        hab_id: n.hab_id,
        nome: n.nome,
        estado: n.estado,
        respondidas: n.respondidas,
        biomaId: bioma.bioma_id,
        nivel,
        position: [x, alturaDeNivel(nivel), z],
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
      from: s.position,
      to: t.position,
      peso: Math.min(PESO_ESTADO[s.estado], PESO_ESTADO[t.estado]),
    });
  }

  const biomaAnchors = BIOMA_IDS.map((id) => {
    const bioma = mapaData.biomas.find((b) => b.bioma_id === id);
    const { x, z } = ANCORA_MUNDO[id];
    const arq = BIOMA_ARCHETYPES[id];
    return {
      biomaId: id,
      nome: bioma?.nome ?? id,
      position: [x, alturaDeNivel(arq.nivelBase) + 11.5, z],
    };
  });

  return { nos, nosVisiveis, arestas, biomaAnchors };
}

function halton(index, base) {
  let resultado = 0;
  let f = 1 / base;
  let i = index;
  while (i > 0) {
    resultado += f * (i % base);
    i = Math.floor(i / base);
    f /= base;
  }
  return resultado;
}

/** Balões: 1 por bioma (a `ideia`, já escrita no tom certo) + frases curadas
 * distribuídas por sequência de Halton. Ficam acima do skyline local para
 * não entrar dentro de torre nenhuma. */
export function construirBaloes(mapaData, nos) {
  const baloes = [];
  const ocupados = nos.map((n) => n.position);

  const alturaLocal = (x, z) => {
    let maior = BASE_TOPO;
    for (const n of nos) {
      if (Math.hypot(n.position[0] - x, n.position[2] - z) < 9) {
        maior = Math.max(maior, n.position[1]);
      }
    }
    return maior;
  };

  for (const bioma of mapaData.biomas) {
    const { x, z } = ANCORA_MUNDO[bioma.bioma_id];
    const angulo = hash01(`${bioma.bioma_id}:ideia`) * Math.PI * 2;
    const px = x + Math.cos(angulo) * 6.5;
    const pz = z + Math.sin(angulo) * 6.5;
    baloes.push({
      id: `ideia-${bioma.bioma_id}`,
      texto: bioma.ideia,
      biomaId: bioma.bioma_id,
      position: [px, alturaLocal(px, pz) + 3.4, pz],
      largura: 3.8,
      altura: 0.95,
    });
    ocupados.push([px, 0, pz]);
  }

  const alvo = Math.min(BALOES_CURADOS.length, 10);
  let colocados = 0;
  let tentativa = 1;
  while (colocados < alvo && tentativa < 600) {
    const hx = halton(tentativa, 2) * WORLD_WIDTH - WORLD_WIDTH / 2;
    const hz = halton(tentativa, 3) * WORLD_DEPTH - WORLD_DEPTH / 2;
    tentativa += 1;
    const pertoDemais = ocupados.some(([ox, , oz]) => Math.hypot(hx - ox, hz - oz) < 8);
    if (pertoDemais) continue;
    const { distancia } = biomaMaisProximo(hx, hz);
    if (distancia > 24) continue; // fora da cidade
    baloes.push({
      id: `curado-${colocados}`,
      texto: BALOES_CURADOS[colocados],
      biomaId: biomaMaisProximo(hx, hz).biomaId,
      position: [hx, alturaLocal(hx, hz) + 3, hz],
      largura: 3.1,
      altura: 0.9,
    });
    ocupados.push([hx, 0, hz]);
    colocados += 1;
  }

  return baloes;
}
