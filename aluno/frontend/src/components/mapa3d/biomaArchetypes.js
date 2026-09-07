// Identidade dos 6 distritos — camada de PRODUTO no cliente, nunca a
// ontologia. Cada um é uma ILHA própria do arquipélago, com cor, altitude,
// vegetação e landmark próprios; o vazio entre elas faz parte da composição.
//
// A referência de terreno é brasileira (Cerrado, Mata Atlântica, Caatinga,
// Amazônia, Pantanal, Pampas) e entra pela TOPOGRAFIA e pela vegetação, não
// por realismo: continua tudo em volume geométrico chapado.
//
// Cor: cada ilha tem um neon próprio (a luz) + 3 tons de pedra tingidos por
// ele (as superfícies). O espectro anda do ciano ao magenta passando por
// turquesa, azul, índigo e violeta — frio e elétrico, longe do
// verde/vermelho/âmbar que no resto do app significam acerto, erro e aviso.
export const BIOMA_ARCHETYPES = {
  perceber: {
    // Cerrado — campo aberto, horizonte largo, rocha exposta, vegetação baixa.
    // A ilha de entrada: baixa, ampla, com muito vazio entre as coisas.
    paleta: { claro: "#7FD8F5", medio: "#2E7FA8", escuro: "#0F3449", brilho: "#4FD9FF" },
    nivelBase: 0,
    nivelVariacao: 1,
    landmark: "mirante",
    formaNo: "anel",
    vegetacao: "cerrado",
    raioIlha: 26,
  },
  relacionar: {
    // Mata Atlântica — mata fechada, rios, caminhos que se cruzam.
    paleta: { claro: "#6FE0D2", medio: "#1F8C82", escuro: "#0A3B38", brilho: "#35E0D8" },
    nivelBase: 3,
    nivelVariacao: 2,
    landmark: "passarelas",
    formaNo: "ziggurat",
    vegetacao: "mata",
    raioIlha: 23,
  },
  representar: {
    // Caatinga — geometria árida, pedra, cristal, contraste duro.
    paleta: { claro: "#7FA6F0", medio: "#2F55A8", escuro: "#111F4E", brilho: "#4A85E3" },
    nivelBase: 6,
    nivelVariacao: 2,
    landmark: "cristal",
    formaNo: "cristal",
    vegetacao: "caatinga",
    raioIlha: 22,
  },
  investigar: {
    // Amazônia — floresta profunda com torres/observatórios emergindo dela.
    paleta: { claro: "#9A93F5", medio: "#4A3FB0", escuro: "#181350", brilho: "#7C6BFF" },
    nivelBase: 10,
    nivelVariacao: 2,
    landmark: "observatorio",
    formaNo: "obelisco",
    vegetacao: "amazonia",
    raioIlha: 21,
  },
  integrar: {
    // Pantanal — água, ilhotas, canais, estruturas horizontais conectadas.
    paleta: { claro: "#C293F5", medio: "#6C34B0", escuro: "#260F50", brilho: "#A45BFF" },
    nivelBase: 1,
    nivelVariacao: 1,
    landmark: "delta",
    formaNo: "nucleo",
    vegetacao: "pantanal",
    raioIlha: 27,
  },
  decidir: {
    // Pampas — planalto aberto, quase vazio, com estrutura monumental.
    paleta: { claro: "#F09AE4", medio: "#A82F98", escuro: "#400C3B", brilho: "#E45BD8" },
    nivelBase: 14,
    nivelVariacao: 1,
    landmark: "monumento",
    formaNo: "cubo",
    vegetacao: "pampas",
    raioIlha: 24,
  },
};

// Tiers visuais por `estado`. `unknown` não tem entrada: continua fog-of-war,
// existindo como massa bruta sem detalhe. `discovered` ganha `nevoa`: a
// estrutura está lá, mas encoberta — revela silhueta, não conteúdo.
export const ESTADO_TIER = {
  mastered: { escala: 1.2, emissiva: 1.9, janela: "brilho", rotulo: true, pulsa: false, nevoa: false },
  in_progress: { escala: 1.05, emissiva: 1.1, janela: "brilho", rotulo: true, pulsa: false, nevoa: false },
  available: { escala: 0.95, emissiva: 0.55, janela: "brilhoFraco", rotulo: true, pulsa: true, nevoa: false },
  discovered: { escala: 0.66, emissiva: 0.04, janela: "medio", rotulo: false, pulsa: false, nevoa: false },
};

// Mesma escala de peso de sempre — decide o quanto uma rota está acesa.
export const PESO_ESTADO = { mastered: 1, in_progress: 0.8, available: 0.5, discovered: 0.22 };
