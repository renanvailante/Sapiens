/**
 * A PALETA DOS GRÁFICOS — escolhida por medição, não por gosto.
 *
 * Cor de gráfico não é decoração: ela é o canal que diz QUAL série é qual.
 * Por isso as oito cores abaixo não foram escolhidas olhando na tela — foram
 * validadas contra a superfície escura do produto (`.card-sapiens`, que com o
 * vidro sobre o abismo fica em torno de `#14203a`) em cinco checagens:
 *
 *   · faixa de luminosidade para fundo escuro (OKLCH L entre 0.48 e 0.67);
 *   · piso de croma (abaixo de 0.10 a cor lê como cinza e para de identificar);
 *   · separação sob daltonismo (protanopia/deuteranopia, ΔE ≥ 8 em OKLab×100)
 *     entre CORES VIZINHAS na ordem — é a ordem que garante a segurança, então
 *     ela nunca muda e as cores nunca são recicladas;
 *   · piso de separação para visão normal (ΔE ≥ 15);
 *   · contraste de no mínimo 3:1 contra a superfície.
 *
 * O ciano da marca puro (`--bio-ciano`, #4FD9FF) **não** passa na faixa de
 * luminosidade sobre fundo escuro: ele é claro demais e, ao lado de outra
 * série, some. Ele continua sendo a cor da interface (títulos, brilhos, a
 * própria Mentis); dentro do gráfico entra o mesmo ciano um passo mais fundo.
 *
 * Se alguém precisar de uma nona série: não invente a nona cor. Agrupe o
 * excedente em "Outras" ou quebre em gráficos pequenos lado a lado — uma cor
 * gerada por conta própria é indistinguível de uma que já está na tela.
 */

/** A superfície contra a qual tudo acima foi medido. Também é o que preenche
 *  as folgas de 2px entre marcas vizinhas: quem separa é o fundo, nunca uma
 *  borda desenhada em volta. */
export const SUPERFICIE = "#14203a";

/** Ordem fixa. Nunca reordene para "ficar bonito": a ordem É a checagem. */
export const SERIES = [
  "#1f9fc4", // 1 · ciano (a cor da casa, um passo mais fundo)
  "#d95926", // 2 · laranja
  "#199e70", // 3 · verde-água
  "#c98500", // 4 · âmbar
  "#d55181", // 5 · magenta
  "#008300", // 6 · verde
  "#9085e9", // 7 · violeta
  "#e66767", // 8 · vermelho
];

/** Cor da série `i`, sem nunca dar a volta na lista. */
export const serie = (i) => SERIES[i] || SERIES[SERIES.length - 1];

/**
 * Rampa ORDINAL de uma cor só (azul), clara = mais. Serve o calendário de
 * constância e qualquer escala em que a ordem é o significado (faixas de
 * tempo, por exemplo). Cada degrau tem diferença de luminosidade suficiente
 * para ser visto, e o degrau mais fraco ainda se separa do fundo.
 */
export const RAMPA = ["#1c5cab", "#2a78d6", "#5598e7", "#9ec5f4"];
/** O degrau zero não é uma cor da rampa: é a ausência de dado. */
export const VAZIO = "rgba(255,255,255,0.055)";

/** O meio do par divergente: cinza, nunca uma terceira cor. Um tom colorido
 *  no zero faria "não mudou nada" parecer um resultado. */
const GRADE_MEIO = "rgba(175, 196, 224, 0.35)";

/**
 * Par DIVERGENTE — azul e vermelho, com o zero como meio neutro. Serve o
 * único gráfico da tela que encoda POLARIDADE (subiu/caiu), e por isso não
 * usa as cores de série: ali a cor não diz "qual matéria", diz "para que
 * lado". Validado como par sobre a mesma superfície (ΔE 19,2 sob protanopia).
 */
export const DIVERGENTE = { positivo: "#3987e5", negativo: "#e66767", meio: GRADE_MEIO };

/** Estados. Reservados: nunca viram "a série 9". Sempre acompanhados de
 *  ícone ou texto — cor sozinha não pode carregar significado. */
export const ESTADO = {
  bom: "#0ca30c",
  atencao: "#fab219",
  serio: "#ec835a",
  critico: "#d03b3b",
};

/** Tinta. Texto NUNCA veste a cor da série: quem identifica é a marca
 *  colorida ao lado, não a letra. */
export const TINTA = {
  forte: "#E8F2FF",
  media: "#AFC4E0",
  fraca: "#8CA2C0",
  apagada: "#6D82A2",
};

/** Grade e eixos: fio de 1px, sólido, um passo acima do fundo. Tracejado lê
 *  como "projeção" e some atrás do dado. */
export const GRADE = "rgba(150, 200, 255, 0.14)";

/** Estilo do balão de valor do recharts, no vidro da casa. */
export const BALAO = {
  background: "rgba(10, 21, 38, 0.96)",
  border: `1px solid ${GRADE}`,
  borderRadius: 14,
  boxShadow: "0 18px 44px -26px rgba(0,0,0,0.9)",
  color: TINTA.forte,
  fontSize: 12,
  padding: "10px 12px",
};

/** Eixo padrão — repetido em oito gráficos, então mora aqui. */
export const EIXO = {
  stroke: GRADE,
  tick: { fill: TINTA.fraca, fontSize: 11 },
  tickLine: false,
  axisLine: false,
};

/** `63.5` -> `"64%"`; `null` -> `"—"`. Percentual quebrado em gráfico é ruído:
 *  a casa decimal existe no dado, não na leitura. */
export const pct = (v) => (v == null ? "—" : `${Math.round(v)}%`);

/** Plural sem gambiarra de template no meio do JSX. */
export const questoes = (n) => `${n} ${n === 1 ? "questão" : "questões"}`;
