// Configuração visual client-side dos 6 biomas — camada de PRODUTO, igual a
// `treino_grafo_v0_2.py::BIOMAS` no espírito (nunca a ontologia). Existe só
// aqui porque o mundo 3D é construído inteiramente no cliente: zero mudança
// de backend.
//
// As cores permanecem dentro da família ciano→violeta do sistema de design
// (index.css: --bio-ciano/--bio-azul/--bio-violeta) — nunca verde/vermelho/
// âmbar, reservados a certo/errado/aviso. A identidade de cada bioma vem da
// TOPOGRAFIA (elevation.kind) e da geometria do nó, não de uma cor fora da
// família.
export const BIOMA_ARCHETYPES = {
  perceber: {
    // "Observar antes de interpretar" — chão raso, quase espelhado.
    tint: { base: "#4FD9FF", deep: "#0f2a3d", emissive: "#4FD9FF" },
    elevation: { kind: "flat-reflective", amplitude: 0.6, detailFreq: 0.07, detailAmplitude: 0.18 },
    nodeGeometry: "disc-ring",
    ground: { roughness: 0.2, metalness: 0.4 },
  },
  relacionar: {
    // "Uma coisa muda em função da outra" — vale em terraços.
    tint: { base: "#3FBFEA", deep: "#123350", emissive: "#3FBFEA" },
    elevation: { kind: "terraced", amplitude: 2.4, step: 0.55, detailFreq: 0.05, detailAmplitude: 0.2 },
    nodeGeometry: "stepped-block",
    ground: { roughness: 0.55, metalness: 0.12 },
  },
  representar: {
    // "Ideia → estrutura manipulável" — platô cristalino, altura quantizada.
    tint: { base: "#4A85E3", deep: "#16254c", emissive: "#4A85E3" },
    elevation: { kind: "quantized", amplitude: 2.6, step: 0.5, detailFreq: 0.03, detailAmplitude: 0.05 },
    nodeGeometry: "crystal-prism",
    ground: { roughness: 0.3, metalness: 0.3 },
  },
  investigar: {
    // "Testar uma explicação" — cluster de torres/observatórios.
    tint: { base: "#6E82E8", deep: "#1c1a48", emissive: "#6E82E8" },
    elevation: { kind: "spires", amplitude: 3.6, detailFreq: 0.1, detailAmplitude: 0.7 },
    nodeGeometry: "obelisk",
    ground: { roughness: 0.6, metalness: 0.1 },
  },
  integrar: {
    // "O sistema inteiro" — bacia de convergência (amplitude negativa: é o
    // ponto mais baixo, então pontes de outros biomas descem até ele sem
    // nenhuma lógica extra de caminho).
    tint: { base: "#8B7BFF", deep: "#1f1640", emissive: "#8B7BFF" },
    elevation: { kind: "basin", amplitude: -2.1, detailFreq: 0.05, detailAmplitude: 0.2 },
    nodeGeometry: "hub-node",
    ground: { roughness: 0.35, metalness: 0.22 },
  },
  decidir: {
    // "Julgar, classificar, escolher" — platô-cume, elevado e plano no topo.
    tint: { base: "#A489FF", deep: "#251a44", emissive: "#A489FF" },
    elevation: { kind: "summit", amplitude: 3.1, detailFreq: 0.04, detailAmplitude: 0.1 },
    nodeGeometry: "tribunal-block",
    ground: { roughness: 0.4, metalness: 0.32 },
  },
};

// Tiers visuais por `estado` — substitui `estiloEstado()` do SVG 2D.
// `unknown` não tem entrada: nunca vira estrutura (fog-of-war), igual hoje.
export const ESTADO_TIER = {
  mastered: { scale: 1.15, emissiveIntensity: 1.1, opacity: 1, label: true, pulse: false },
  in_progress: { scale: 1.0, emissiveIntensity: 0.65, opacity: 1, label: true, pulse: false },
  available: { scale: 0.85, emissiveIntensity: 0.3, opacity: 0.92, label: true, pulse: true },
  discovered: { scale: 0.6, emissiveIntensity: 0.0, opacity: 0.5, label: false, pulse: false },
};

// Mesma escala de peso do SVG 2D (`pesoEstado` em TreinoHabilidades.jsx).
export const PESO_ESTADO = { mastered: 1, in_progress: 0.8, available: 0.5, discovered: 0.22 };
