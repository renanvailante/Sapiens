// Sigilos das missões — desenho geométrico de traço fino, na mesma família
// visual do resto do produto (linha de 1px acesa, nada de ilustração).
//
// Cada glifo é uma lista de primitivas numa caixa de 24×24, escritas numa
// notação curta para caber em uma linha cada:
//   "l x1 y1 x2 y2"        linha
//   "c cx cy r"            círculo (contorno)
//   "d cx cy r"            disco (preenchido)
//   "r x y w h"            retângulo
//   "p <path d>"           caminho livre
//
// A ideia é a mesma dos sigilos: a forma diz do que a missão trata antes de
// qualquer texto — dado, gráfico, proporção, ciclo, argumento.
export const GLIFOS = {
  ordem: ["l 5 19 5 14", "l 12 19 12 10", "l 19 19 19 5", "l 3 21 21 21"],
  razao: ["l 4 12 20 12", "d 9 7 1.6", "d 15 17 1.6"],
  proporcao: ["p M4 19 L10 19 L10 13 Z", "p M13 19 L21 19 L21 8 Z"],
  percentual: ["c 8 8 3", "c 16 16 3", "l 5 19 19 5"],
  estimativa: ["p M3 14 q4 -6 8 0 t8 0", "d 6 8 1.3", "d 18 18 1.3"],
  afericao: ["c 12 12 7.5", "l 7 12 17 12", "d 12 8.5 1.4"],
  unidade: ["r 3 9 18 6", "l 8 9 8 12", "l 12 9 12 13", "l 16 9 16 12"],
  geometria: ["p M5 19 L12 5 L19 19 Z", "l 8 19 8 16", "l 8 16 11 16"],
  area: ["r 5 5 14 14", "l 5 19 19 5", "l 11 19 19 11"],
  volume: ["p M12 3 L20 8 L20 17 L12 22 L4 17 L4 8 Z", "l 12 12 12 22", "l 12 12 20 8", "l 12 12 4 8"],
  estrutura: ["p M12 3 L20 8 L20 17 L12 22 L4 17 L4 8 Z", "c 12 12 3"],
  taxa: ["l 4 4 4 20", "l 4 20 20 20", "p M6 17 L18 7", "l 14 7 18 7", "l 18 7 18 11"],
  variacao: ["p M3 9 q4 -5 8 0 t8 0", "p M3 17 q4 -5 8 0 t8 0"],
  grafico: ["l 3 20 21 20", "l 7 20 7 13", "l 12 20 12 7", "l 17 20 17 16"],
  conservacao: ["c 12 12 8", "l 8 10 16 10", "l 8 14 16 14"],
  calor: ["p M8 20 q3 -4 0 -7 t0 -6", "p M14 20 q3 -4 0 -7 t0 -6", "l 4 20 20 20"],
  probabilidade: ["r 4 4 16 16", "d 8 8 1.5", "d 12 12 1.5", "d 16 16 1.5"],
  eventos: ["c 9 12 5.5", "c 15 12 5.5"],
  media: ["l 3 12 21 12", "l 7 17 7 12", "l 12 6 12 12", "l 17 15 17 12"],
  mediana: ["l 5 19 5 12", "l 9 19 9 8", "l 12 19 12 4", "l 15 19 15 9", "l 19 19 19 14", "d 12 2 1.4"],
  moda: ["l 5 19 5 14", "l 9 19 9 9", "l 13 19 13 9", "l 17 19 17 15", "l 8 6 14 6"],
  amplitude: ["l 4 12 20 12", "l 4 8 4 16", "l 20 8 20 16", "d 12 12 1.3"],
  dispersao: ["l 3 12 21 12", "d 6 8 1.3", "d 10 16 1.3", "d 14 7 1.3", "d 18 15 1.3"],
  causa: ["r 3 9 6 6", "l 10 12 17 12", "l 14 9 17 12", "l 14 15 17 12", "c 19.5 12 2"],
  correlacao: ["l 4 19 20 6", "d 7 16 1.3", "d 11 13 1.3", "d 16 9 1.3", "l 14 17 20 11", "l 14 11 20 17"],
  argumento: ["l 5 6 19 6", "l 5 10 19 10", "l 3 14 21 14", "l 9 19 15 19"],
  falacia: ["c 12 12 8", "l 6 18 18 6"],
  equacao: ["l 4 7 10 17", "l 10 7 4 17", "l 13 10 21 10", "l 13 15 21 15"],
  notacao: ["l 4 19 10 5", "l 10 5 16 19", "l 6.5 14 13.5 14", "d 19 17 1.6"],
  dados: ["r 5 3 14 18", "l 8 8 16 8", "l 8 12 16 12", "l 8 16 13 16"],
  tabela: ["r 3 5 18 14", "l 3 10 21 10", "l 3 15 21 15", "l 10 5 10 19"],
  inferencia: ["c 5 12 2", "l 8 12 10 12", "l 12 12 14 12", "l 16 12 17 12", "c 20 12 2", "l 17.5 9.5 20 12"],
  escala: ["l 4 4 4 20", "l 4 20 20 20", "l 4 8 7 8", "l 4 12 7 12", "l 4 16 7 16", "p M8 17 L19 8"],
  sintese: ["p M3 6 Q13 12 21 12", "p M3 18 Q13 12 21 12", "d 21 12 1.6"],
  hipotese: ["l 8 3 16 3", "p M9.5 3 L9.5 10 L5 20 L19 20 L14.5 10 L14.5 3", "l 7 15 17 15"],
  variavel: ["l 4 20 20 20", "l 4 20 4 4", "c 10 14 2.4", "c 16 9 2.4", "l 12 13 14 10"],
  equilibrio: ["l 12 4 12 9", "l 4 9 20 9", "l 4 9 4 12", "l 20 9 20 12", "p M2 12 a4 4 0 0 0 8 0", "p M14 12 a4 4 0 0 0 8 0"],
  cadeia: ["c 5.5 12 2.6", "c 12 12 2.6", "c 18.5 12 2.6", "l 8.2 12 9.4 12", "l 14.6 12 15.9 12"],
  ciclo: ["p M19 12 a7 7 0 1 1 -3 -5.7", "l 16 3 16 6.5", "l 16 6.5 19.5 6.5"],
  classificacao: ["r 3 4 7 6", "r 14 4 7 6", "r 8 14 8 6", "l 6.5 10 12 14", "l 17.5 10 12 14"],
};

/** Converte a notação curta em elementos SVG. */
export function primitivasDe(familia) {
  return (GLIFOS[familia] ?? GLIFOS.dados).map((linha) => {
    const [tipo, ...n] = linha.split(" ");
    if (tipo === "p") return { tipo, d: linha.slice(2) };
    return { tipo, n: n.map(Number) };
  });
}
