// Identidade visual dos 6 biomas — camada de PRODUTO no cliente, nunca a
// ontologia. Cada bioma é um DISTRITO da mesma cidade: tem paleta própria,
// altura própria e um landmark próprio, mas todos são construídos com o
// mesmo vocabulário (laje, cornija, torre, arcada, escada, ponte, arco).
//
// Paleta: cada distrito tem 3 tons de superfície + 1 luz. Os tons são pedra
// fria dessaturada puxada para o matiz do bioma; a saturação forte fica
// reservada à LUZ (o `brilho`), que é sempre um dos matizes do sistema de
// design (ciano -> azul -> violeta, index.css). Nenhum verde/vermelho/âmbar
// entra como cor de superfície — eles continuam significando
// acerto/erro/aviso no resto do produto.
//
// A leitura de volume (o "Monument Valley") não vem da cor e sim da luz: as
// faces superiores recebem a luz principal, as laterais caem para o `medio`
// e o `escuro`, e a cornija de 30cm sob cada laje devolve uma linha clara
// que separa massa de piso.
export const BIOMA_ARCHETYPES = {
  perceber: {
    // "Observar antes de interpretar" — o distrito baixo, quase plano, de
    // pátios e espelhos d'água. É por onde se entra na cidade.
    paleta: { claro: "#A5DCEF", medio: "#4C7F9E", escuro: "#204765", brilho: "#4FD9FF" },
    nivelBase: 0,
    nivelVariacao: 1,
    landmark: "patio",
    formaNo: "anel",
  },
  relacionar: {
    // "Uma coisa muda em função da outra" — terraços encadeados, ligados por
    // escadarias que sobem em duas direções.
    paleta: { claro: "#9CC9E8", medio: "#446F9C", escuro: "#1C3D63", brilho: "#3FBFEA" },
    nivelBase: 1,
    nivelVariacao: 2,
    landmark: "escadaria",
    formaNo: "ziggurat",
  },
  representar: {
    // "Ideia -> estrutura manipulável" — platôs cristalinos e torres-grade:
    // a estrutura aparente, o desenho técnico virado edifício.
    paleta: { claro: "#A3BCE6", medio: "#4A63A0", escuro: "#213166", brilho: "#4A85E3" },
    nivelBase: 2,
    nivelVariacao: 2,
    landmark: "torre-grade",
    formaNo: "cristal",
  },
  investigar: {
    // "Testar uma explicação" — o distrito alto, de observatórios e antenas,
    // de onde se enxerga o resto da cidade.
    paleta: { claro: "#ADB2EC", medio: "#55589E", escuro: "#292863", brilho: "#6E82E8" },
    nivelBase: 3,
    nivelVariacao: 2,
    landmark: "observatorio",
    formaNo: "obelisco",
  },
  integrar: {
    // "O sistema inteiro" — a bacia: o ponto mais baixo, onde as pontes de
    // todos os outros distritos descem e se encontram num anfiteatro.
    paleta: { claro: "#BBADEE", medio: "#6355A6", escuro: "#2F2569", brilho: "#8B7BFF" },
    nivelBase: 0,
    nivelVariacao: 1,
    landmark: "anfiteatro",
    formaNo: "nucleo",
  },
  decidir: {
    // "Julgar, classificar, escolher" — o cume: pórtico de colunas e um
    // volume suspenso sobre ele.
    paleta: { claro: "#C9B7F2", medio: "#7059AE", escuro: "#3A296E", brilho: "#A489FF" },
    nivelBase: 4,
    nivelVariacao: 1,
    landmark: "portico",
    formaNo: "cubo",
  },
};

// Tiers visuais por `estado` — mesma escada de sempre (substitui o
// `estiloEstado()` do SVG 2D). `unknown` não tem entrada: continua sendo
// fog-of-war, mas agora em vez de sumir vira MASSA BRUTA (bloco escuro sem
// cornija, sem janela, sem objeto) — o quarteirão existe, só não foi
// iluminado ainda.
export const ESTADO_TIER = {
  mastered: { escala: 1.15, emissiva: 1.7, janela: "brilho", rotulo: true, pulsa: false },
  in_progress: { escala: 1.0, emissiva: 1.0, janela: "brilho", rotulo: true, pulsa: false },
  available: { escala: 0.9, emissiva: 0.5, janela: "brilhoFraco", rotulo: true, pulsa: true },
  discovered: { escala: 0.7, emissiva: 0.12, janela: "brilhoFraco", rotulo: false, pulsa: false },
};

// Mesma escala de peso do mapa SVG anterior — decide o quanto uma conexão
// está "acesa" na cidade.
export const PESO_ESTADO = { mastered: 1, in_progress: 0.8, available: 0.5, discovered: 0.22 };
