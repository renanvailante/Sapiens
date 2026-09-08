// Transforma a resposta de `GET /treino/mapa` numa descrição de cena pura
// (sem React/Three). `treino_grafo_v0_2.py` (backend) continua sendo a única
// fonte de `x`, `y`, `estado`, `bioma_id` e `relation` — aqui só se decide
// ONDE, em que ilha e em que altitude cada coisa fica, 100% no cliente.
//
// A composição é um CONTINENTE ÚNICO: as âncoras dos seis biomas ficam perto
// o bastante para que suas pegadas se encostem, e o terreno é gerado como uma
// massa só (ver `gerarContinente`). Os biomas continuam distintos por cor e
// cota, mas são lobos do mesmo corpo de terra — não ilhas com abismo no meio.
// O vazio ficou para fora, onde ele desenha a silhueta da costa e hospeda as
// ilhotas satélites.
import { hash01 } from "./noise";
import { BIOMA_ARCHETYPES, PESO_ESTADO } from "./biomaArchetypes";

export const SOURCE_W = 1000;
export const SOURCE_H = 640;
export const SCALE = 0.072;

/** Afastamento entre as regiões (aplicado às âncoras de bioma). Baixo de
 * propósito: acima disto as pegadas se soltam e voltam a virar arquipélago. */
export const SEPARACAO_ILHAS = 26;
/** Espalhamento dos nós DENTRO da própria região. */
export const ESPALHAMENTO = 30;
/** O continente é mais comprido que fundo — é o que dá a leitura de terra
 * larga da referência, em vez de um disco. Aplicado só ao eixo X. */
export const ALONGAMENTO_X = 1.55;

/** Altura de um pavimento. */
export const NIVEL = 9;
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
        x: (sx - SOURCE_W / 2) * SCALE * SEPARACAO_ILHAS * ALONGAMENTO_X,
        z: (sy - SOURCE_H / 2) * SCALE * SEPARACAO_ILHAS,
      },
    ];
  }),
);

// Perfil do continente ao longo do comprimento: planície baixa no meio,
// maciço de rocha subindo nas duas pontas. É a silhueta da referência — terra
// plana no centro, penhasco gigante de cada lado.
//
// Mora AQUI, e não no gerador de arquitetura, porque a cota do NÓ e a cota do
// TERRENO precisam sair da mesma conta. Se divergirem, os nós das pontas
// aparecem enterrados dentro da rocha.
const XS_ANCORAS = BIOMA_IDS.map((id) => ANCORA_MUNDO[id].x);
export const CENTRO_X = (Math.min(...XS_ANCORAS) + Math.max(...XS_ANCORAS)) / 2;
export const MEIA_LARGURA = (Math.max(...XS_ANCORAS) - Math.min(...XS_ANCORAS)) / 2 + 420;
/** Quanto o maciço das pontas sobe acima da planície. */
export const ALTURA_MACICO = 430;
/** Onde, ao longo do comprimento, a planície começa a virar rocha. */
const INICIO_MACICO = 0.32;

const suave = (a, b, x) => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** 0 na planície central, 1 no alto dos maciços das pontas. */
export function fatorMacico(x) {
  return suave(INICIO_MACICO, 1, Math.abs((x - CENTRO_X) / MEIA_LARGURA));
}

/** Cota que o perfil continental acrescenta num ponto. */
export function relevoContinental(x) {
  return fatorMacico(x) * ALTURA_MACICO;
}

/** Cota do terreno da região — cada bioma tem a sua altitude. É o que cria
 * desnível de verdade entre regiões e obriga as rotas a subirem. */
export function alturaIlha(biomaId) {
  return BIOMA_ARCHETYPES[biomaId].nivelBase * NIVEL;
}

/** Posição de um nó: âncora da ilha + deslocamento local espalhado. */
export function posicaoDoNo(srcX, srcY, biomaId) {
  const [ax, ay] = ANCORA_BIOMA_SRC[biomaId];
  const centro = ANCORA_MUNDO[biomaId];
  return {
    x: centro.x + (srcX - ax) * SCALE * ESPALHAMENTO * ALONGAMENTO_X,
    z: centro.z + (srcY - ay) * SCALE * ESPALHAMENTO,
  };
}

/** Pavimento local do nó dentro da própria ilha (0..variação). */
export function nivelDoNo(habId, biomaId) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  return Math.floor(hash01(`${habId}:nivel`) * (arq.nivelVariacao + 1));
}

/** Cota do piso de um quarteirão: terreno da ilha + pavimento local. */
export function alturaDoNo(habId, biomaId, x = CENTRO_X) {
  return alturaIlha(biomaId) + relevoContinental(x) + nivelDoNo(habId, biomaId) * NIVEL + LAJE;
}

/** Resposta de `GET /treino/mapa` + `nodeIndex` -> descrição da cena.
 * `nos` traz TODOS os nós (inclusive `unknown`, que viram massa bruta na
 * ilha); `arestas` só as visíveis, com a mesma regra de sempre. */
const conhecido = (n) => (n.acesso ? n.acesso === "acessivel" : n.estado !== "unknown");

export function construirCena(mapaData, nodeIndex) {
  const nos = [];
  for (const bioma of mapaData.biomas) {
    for (const n of bioma.nodes) {
      const { x, z } = posicaoDoNo(n.x, n.y, bioma.bioma_id);
      nos.push({
        hab_id: n.hab_id,
        // `rotulo` é o que a tela mostra; a frase original (`nome`) fica só
        // como dado interno e nunca é renderizada.
        rotulo: n.rotulo,
        interativo: n.interativo !== false,
        estado: n.estado,
        respondidas: n.respondidas,
        biomaId: bioma.bioma_id,
        nivel: nivelDoNo(n.hab_id, bioma.bioma_id),
        position: [x, alturaDoNo(n.hab_id, bioma.bioma_id, x), z],
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
    // Uma rota só existe entre pontas CONHECIDAS. Vislumbre e oculto não
    // ancoram linha nenhuma: uma ligação saindo para o escuro entregaria a
    // existência de algo que o aluno ainda não alcançou.
    if (!s || !t || !conhecido(s) || !conhecido(t)) continue;
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
  const limites = { raio: raio + 420 };

  // Todas as 56 dominadas? É o que destrava o santuário central.
  const completo = nos.length > 0 && nos.every((n) => (n.estadoBackend ?? n.estado) === "mastered");

  return { nos, nosVisiveis, arestas, limites, completo };
}
