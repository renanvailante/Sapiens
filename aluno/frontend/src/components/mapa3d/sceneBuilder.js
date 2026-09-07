// Transforma a resposta de `GET /treino/mapa` numa descrição de cena 3D pura
// (sem import de React/Three) — coordenadas de mundo, elevação, visibilidade
// e tier de cada nó/aresta, posição dos balões. `treino_grafo_v0_2.py`
// (backend) continua sendo a única fonte de `x`, `y`, `estado`, `bioma_id` e
// `relation`; este módulo só decora isso com uma terceira dimensão e
// topografia, 100% no cliente (decisão do plano: zero mudança de backend).
import { seededNoise2D, hash01 } from "./noise";
import { BIOMA_ARCHETYPES, PESO_ESTADO } from "./biomaArchetypes";
import { BALOES_CURADOS } from "./balloonContent";

export const SOURCE_W = 1000;
export const SOURCE_H = 640;
export const SCALE = 0.075;

export const WORLD_WIDTH = SOURCE_W * SCALE * 1.2;
export const WORLD_DEPTH = SOURCE_H * SCALE * 1.2;

// Raio de influência de um bioma, em unidades de mundo — calibrado pela
// distância típica entre âncoras vizinhas (~18-24 unidades após o SCALE
// acima), pra cada arquétipo se expressar dentro do próprio "território"
// sem vazar demais para o vizinho.
const REGIAO_RAIO = 15;

// Espelha `_ANCORA_BIOMA` de treino_grafo_v0_2.py (backend) — camada de
// produto, não ontologia. Copiado aqui porque o mundo 3D é montado
// inteiramente no cliente; se o backend um dia rebalancear essas âncoras,
// este mapa client-side precisa ser atualizado junto.
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
 * mundo 3D. `y` do backend vira **Z**; **Y** fica só para elevação — nunca
 * confundir os dois eixos. */
export function toWorld(x, y) {
  return { x: (x - SOURCE_W / 2) * SCALE, z: (y - SOURCE_H / 2) * SCALE };
}

const ANCORA_MUNDO = Object.fromEntries(
  Object.entries(ANCORA_BIOMA_SRC).map(([id, [x, y]]) => [id, toWorld(x, y)]),
);

function smoothstep(t) {
  const c = Math.min(1, Math.max(0, t));
  return c * c * (3 - 2 * c);
}

function formaElevacao(kind, params, distNorm, wx, wz, noise2D) {
  const falloff = Math.max(0, 1 - distNorm);
  switch (kind) {
    case "flat-reflective":
      return params.amplitude * falloff * 0.3;
    case "terraced":
    case "quantized": {
      const bruto = params.amplitude * falloff;
      return Math.round(bruto / params.step) * params.step;
    }
    case "spires": {
      const n = noise2D(wx * 0.12, wz * 0.12);
      return params.amplitude * falloff * Math.max(0, n) * 1.6;
    }
    case "basin":
      return params.amplitude * falloff; // amplitude negativa => bacia
    case "summit":
      return params.amplitude * Math.min(falloff * 1.3, 1); // topo achatado
    default:
      return params.amplitude * falloff;
  }
}

/** Distância (não normalizada) de um ponto do mundo até cada âncora de
 * bioma, ordenada da mais próxima para a mais distante. */
function distanciasOrdenadas(worldX, worldZ) {
  return BIOMA_IDS.map((id) => {
    const a = ANCORA_MUNDO[id];
    return { id, d: Math.hypot(worldX - a.x, worldZ - a.z) };
  }).sort((a, b) => a.d - b.d);
}

/** Peso dos 2 biomas mais próximos de um ponto do mundo (smoothstep, soma 1)
 * — a MESMA função usada pra blendar elevação e cor do terreno, pra fronteira
 * entre biomas ser uma transição, nunca um corte duro (Voronoi). */
export function pesosBioma(worldX, worldZ) {
  const [n1, n2] = distanciasOrdenadas(worldX, worldZ);
  const somaD = n1.d + n2.d;
  let w1 = somaD > 0 ? 1 - n1.d / somaD : 1;
  w1 = smoothstep(w1);
  return { id1: n1.id, id2: n2.id, d1: n1.d, d2: n2.d, w1, w2: 1 - w1 };
}

/** Bioma dominante (âncora mais próxima) de um ponto do mundo. */
export function dominantBiomaAt(worldX, worldZ) {
  return distanciasOrdenadas(worldX, worldZ)[0].id;
}

/** Altura do terreno num ponto arbitrário do mundo: blend suave (smoothstep)
 * dos 2 biomas mais próximos, cada um com sua própria "forma" de elevação +
 * ruído de detalhe seedado por bioma. Determinístico: mesma entrada, mesma
 * saída, sempre — todo aluno vê o mesmo relevo. */
export function elevationAt(worldX, worldZ) {
  const { id1, id2, d1, d2, w1, w2 } = pesosBioma(worldX, worldZ);
  const n1 = { id: id1, d: d1 };
  const n2 = { id: id2, d: d2 };

  const arc1 = BIOMA_ARCHETYPES[n1.id].elevation;
  const arc2 = BIOMA_ARCHETYPES[n2.id].elevation;
  const noise1 = seededNoise2D(`terreno:${n1.id}`);
  const noise2 = seededNoise2D(`terreno:${n2.id}`);

  const h1 = formaElevacao(arc1.kind, arc1, n1.d / REGIAO_RAIO, worldX, worldZ, noise1);
  const h2 = formaElevacao(arc2.kind, arc2, n2.d / REGIAO_RAIO, worldX, worldZ, noise2);
  const base = h1 * w1 + h2 * w2;

  const detalhe =
    noise1(worldX * arc1.detailFreq, worldZ * arc1.detailFreq) * arc1.detailAmplitude * w1 +
    noise2(worldX * arc2.detailFreq, worldZ * arc2.detailFreq) * arc2.detailAmplitude * w2;

  return base + detalhe;
}

/** Resposta de `GET /treino/mapa` + `nodeIndex` (já montado pela página,
 * `hab_id -> {...,bioma}`) -> descrição de cena 3D: nós visíveis (nunca
 * `unknown`, fog-of-war), arestas visíveis, âncoras de bioma. */
export function construirCena(mapaData, nodeIndex) {
  const nos = [];
  for (const bioma of mapaData.biomas) {
    for (const n of bioma.nodes) {
      if (n.estado === "unknown") continue;
      const { x, z } = toWorld(n.x, n.y);
      const y = elevationAt(x, z);
      nos.push({
        hab_id: n.hab_id,
        nome: n.nome,
        estado: n.estado,
        respondidas: n.respondidas,
        biomaId: bioma.bioma_id,
        position: [x, y, z],
      });
    }
  }

  const arestas = [];
  for (const a of mapaData.arestas) {
    const s = nodeIndex[a.source];
    const t = nodeIndex[a.target];
    if (!s || !t || s.estado === "unknown" || t.estado === "unknown") continue;
    const ps = toWorld(s.x, s.y);
    const pt = toWorld(t.x, t.y);
    arestas.push({
      id: `${a.source}-${a.target}`,
      relation: a.relation,
      source: a.source,
      target: a.target,
      sourceMastered: s.estado === "mastered",
      from: [ps.x, elevationAt(ps.x, ps.z), ps.z],
      to: [pt.x, elevationAt(pt.x, pt.z), pt.z],
      peso: Math.min(PESO_ESTADO[s.estado], PESO_ESTADO[t.estado]),
    });
  }

  const biomaAnchors = BIOMA_IDS.map((id) => {
    const bioma = mapaData.biomas.find((b) => b.bioma_id === id);
    const { x, z } = ANCORA_MUNDO[id];
    return { biomaId: id, nome: bioma?.nome ?? id, position: [x, elevationAt(x, z) + 2.2, z] };
  });

  return { nos, arestas, biomaAnchors };
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

/** Balões: 1 âncora por bioma (a partir de `bioma.ideia`, já escrita no tom
 * certo) + até 12 frases curadas gerais, posicionadas por uma sequência de
 * Halton sobre os limites do mundo — determinístico, bem distribuído, sem
 * precisar guardar estado. Rejeita candidatos perto demais de um nó ou de
 * outro balão já colocado. */
export function construirBaloes(mapaData, nos) {
  const baloes = [];
  const ocupados = nos.map((n) => n.position);

  for (const bioma of mapaData.biomas) {
    const { x, z } = ANCORA_MUNDO[bioma.bioma_id];
    const angulo = hash01(`${bioma.bioma_id}:ideia`) * Math.PI * 2;
    const px = x + Math.cos(angulo) * 4.5;
    const pz = z + Math.sin(angulo) * 4.5;
    const py = elevationAt(px, pz) + 1.7;
    baloes.push({ id: `ideia-${bioma.bioma_id}`, texto: bioma.ideia, position: [px, py, pz], largura: 3.6, altura: 0.9 });
    ocupados.push([px, py, pz]);
  }

  const alvo = Math.min(BALOES_CURADOS.length, 12);
  let colocados = 0;
  let tentativa = 1;
  while (colocados < alvo && tentativa < 500) {
    const hx = halton(tentativa, 2) * WORLD_WIDTH - WORLD_WIDTH / 2;
    const hz = halton(tentativa, 3) * WORLD_DEPTH - WORLD_DEPTH / 2;
    tentativa += 1;
    const pertoDemais = ocupados.some(([ox, , oz]) => Math.hypot(hx - ox, hz - oz) < 6);
    if (pertoDemais) continue;
    const texto = BALOES_CURADOS[colocados];
    const py = elevationAt(hx, hz) + 1.4;
    baloes.push({ id: `curado-${colocados}`, texto, position: [hx, py, hz], largura: 2.9, altura: 0.85 });
    ocupados.push([hx, py, hz]);
    colocados += 1;
  }

  return baloes;
}
