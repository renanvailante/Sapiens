// Camada de APRESENTAÇÃO das 56 missões: rótulo curto + família de sigilo.
//
// A frase original da habilidade (`nome`, vinda de `/treino/mapa`) nunca é
// mostrada ao aluno — ela continua sendo o dado interno, usado só como
// insumo de backend (por exemplo no prompt de aprofundamento da Mentis).
// O que a tela mostra é o rótulo daqui.
//
// Os rótulos foram escolhidos a partir do conteúdo real de cada habilidade e
// agrupados em famílias: quando duas missões tratam do mesmo assunto em
// níveis diferentes, elas compartilham a família e se distinguem pelo
// algarismo — é isso que deixa a coleção legível como progressão, e não como
// 56 nomes soltos.
//
// `familia` escolhe o sigilo (ver glifos.js); `variante` marca quantos
// pontos o sigilo carrega, então nenhuma das 56 missões tem ícone idêntico
// a outra.
export const MISSOES = {
  "HAB-01": { rotulo: "Ordem I", familia: "ordem", variante: 1 },
  "HAB-02": { rotulo: "Razão I", familia: "razao", variante: 1 },
  "HAB-03": { rotulo: "Proporção I", familia: "proporcao", variante: 1 },
  "HAB-04": { rotulo: "Proporção II", familia: "proporcao", variante: 2 },
  "HAB-05": { rotulo: "Percentual I", familia: "percentual", variante: 1 },
  "HAB-06": { rotulo: "Estimativa I", familia: "estimativa", variante: 1 },
  "HAB-07": { rotulo: "Aferição I", familia: "afericao", variante: 1 },
  "HAB-08": { rotulo: "Unidades I", familia: "unidade", variante: 1 },
  "HAB-09": { rotulo: "Unidades II", familia: "unidade", variante: 2 },
  "HAB-10": { rotulo: "Geometria I", familia: "geometria", variante: 1 },
  "HAB-11": { rotulo: "Geometria II", familia: "geometria", variante: 2 },
  "HAB-12": { rotulo: "Área I", familia: "area", variante: 1 },
  "HAB-13": { rotulo: "Volume I", familia: "volume", variante: 1 },
  "HAB-14": { rotulo: "Estruturas I", familia: "estrutura", variante: 1 },
  "HAB-15": { rotulo: "Estruturas II", familia: "estrutura", variante: 2 },
  "HAB-16": { rotulo: "Estruturas III", familia: "estrutura", variante: 3 },
  "HAB-17": { rotulo: "Taxa I", familia: "taxa", variante: 1 },
  "HAB-18": { rotulo: "Variação I", familia: "variacao", variante: 1 },
  "HAB-19": { rotulo: "Gráficos I", familia: "grafico", variante: 1 },
  "HAB-20": { rotulo: "Conservação I", familia: "conservacao", variante: 1 },
  "HAB-21": { rotulo: "Conservação II", familia: "conservacao", variante: 2 },
  "HAB-22": { rotulo: "Calor I", familia: "calor", variante: 1 },
  "HAB-23": { rotulo: "Probabilidade I", familia: "probabilidade", variante: 1 },
  "HAB-24": { rotulo: "Eventos I", familia: "eventos", variante: 1 },
  "HAB-25": { rotulo: "Média I", familia: "media", variante: 1 },
  "HAB-26": { rotulo: "Mediana I", familia: "mediana", variante: 1 },
  "HAB-27": { rotulo: "Moda I", familia: "moda", variante: 1 },
  "HAB-28": { rotulo: "Amplitude I", familia: "amplitude", variante: 1 },
  "HAB-29": { rotulo: "Dispersão I", familia: "dispersao", variante: 1 },
  "HAB-30": { rotulo: "Probabilidade II", familia: "probabilidade", variante: 2 },
  "HAB-31": { rotulo: "Probabilidade III", familia: "probabilidade", variante: 3 },
  "HAB-32": { rotulo: "Causa I", familia: "causa", variante: 1 },
  "HAB-33": { rotulo: "Correlação I", familia: "correlacao", variante: 1 },
  "HAB-34": { rotulo: "Causa II", familia: "causa", variante: 2 },
  "HAB-35": { rotulo: "Causa III", familia: "causa", variante: 3 },
  "HAB-36": { rotulo: "Argumento I", familia: "argumento", variante: 1 },
  "HAB-37": { rotulo: "Falácia I", familia: "falacia", variante: 1 },
  "HAB-38": { rotulo: "Equação I", familia: "equacao", variante: 1 },
  "HAB-39": { rotulo: "Gráficos II", familia: "grafico", variante: 2 },
  "HAB-40": { rotulo: "Notação I", familia: "notacao", variante: 1 },
  "HAB-41": { rotulo: "Notação II", familia: "notacao", variante: 2 },
  "HAB-42": { rotulo: "Dados I", familia: "dados", variante: 1 },
  "HAB-43": { rotulo: "Tabelas I", familia: "tabela", variante: 1 },
  "HAB-44": { rotulo: "Gráficos III", familia: "grafico", variante: 3 },
  "HAB-45": { rotulo: "Inferência I", familia: "inferencia", variante: 1 },
  "HAB-46": { rotulo: "Escala I", familia: "escala", variante: 1 },
  "HAB-47": { rotulo: "Síntese I", familia: "sintese", variante: 1 },
  "HAB-48": { rotulo: "Síntese II", familia: "sintese", variante: 2 },
  "HAB-49": { rotulo: "Hipótese I", familia: "hipotese", variante: 1 },
  "HAB-50": { rotulo: "Variáveis I", familia: "variavel", variante: 1 },
  "HAB-51": { rotulo: "Variáveis II", familia: "variavel", variante: 2 },
  "HAB-52": { rotulo: "Equilíbrio I", familia: "equilibrio", variante: 1 },
  "HAB-53": { rotulo: "Cadeias I", familia: "cadeia", variante: 1 },
  "HAB-54": { rotulo: "Ciclos I", familia: "ciclo", variante: 1 },
  "HAB-55": { rotulo: "Classificação I", familia: "classificacao", variante: 1 },
  "HAB-56": { rotulo: "Classificação II", familia: "classificacao", variante: 2 },
};

const PADRAO = { rotulo: "Missão", familia: "dados", variante: 1 };

/** Rótulo e sigilo de uma missão. Nunca devolve a frase original. */
export function missaoDe(habId) {
  return MISSOES[habId] ?? PADRAO;
}
