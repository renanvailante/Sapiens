import Alternativas from "../questao/Alternativas";

/**
 * A QUESTÃO, DESENHADA PELO PRODUTO DE VERDADE.
 *
 * Este bloco não reimplementa a aparência de uma questão: ele monta
 * `components/questao/Alternativas` — a mesma peça que as provas do ENEM, o
 * mapa de treino e os blocos de curso usam — dentro da mesma superfície
 * `.leitura-clara` em que ela aparece no produto.
 *
 * Isso importa mais numa landing do que dentro do app. Quem chega de anúncio
 * está decidindo se o que a página promete existe; uma captura de tela
 * redesenhada à mão é justamente a coisa que não prova nada. Aqui o que a
 * pessoa vê na landing é, literalmente, o componente que ela vai tocar depois
 * de criar a conta — com o mesmo verde, o mesmo vermelho e o mesmo pé sólido.
 *
 * > **`leitura-clara` é obrigatória em volta.** As alternativas são desenhadas
 * > sobre papel claro (`.alternativa` tem fundo branco próprio), e o texto
 * > dentro delas usa `text-zinc-700`, que a camada de tradução do `index.css`
 * > CLAREIA para superfícies escuras. Sem o envelope, o enunciado fica texto
 * > claro sobre papel branco — o defeito que apagou um curso inteiro em 17/09.
 * > Ver `ux/sistema-visual.md` no Cerebro.
 *
 * ---------------------------------------------------------------------------
 * A QUESTÃO É ILUSTRATIVA, E A PÁGINA DIZ ISSO
 * ---------------------------------------------------------------------------
 *
 * O enunciado abaixo é um exemplo escrito para a landing, não um item do
 * acervo, e o resultado mostrado não é o resultado de ninguém. O aviso não é
 * rodapé jurídico: é a diferença entre demonstrar como o Sapiens lê um erro e
 * dar a impressão de que a página já sabe alguma coisa sobre quem está lendo.
 */

const ALTERNATIVAS = [
  { letra: "A", texto: "A produção caiu entre 2019 e 2020." },
  { letra: "B", texto: "A produção cresceu todos os anos do período." },
  { letra: "C", texto: "O maior crescimento ocorreu entre 2021 e 2022." },
  { letra: "D", texto: "A produção de 2022 foi o dobro da de 2018." },
];

export default function DiagnosticPreview({ respondida = true }) {
  return (
    <div className="grid gap-3" data-testid="ads-previa-questao">
      <article className="card-sapiens leitura-clara rounded-2xl p-5 md:p-6">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-sapiens-accentSoft px-3 py-1 text-[11px] font-semibold text-sapiens-navy">
            Exemplo
          </span>
          <span className="text-[11px] font-medium text-zinc-500">
            Interpretação de gráfico
          </span>
        </div>

        <p className="mt-4 text-[15px] leading-relaxed text-zinc-800">
          O gráfico mostra a produção anual de uma indústria entre 2018 e 2022.
          Com base nele, qual afirmação está correta?
        </p>

        <GraficoIlustrativo />

        <div className="mt-4">
          <Alternativas
            alternativas={ALTERNATIVAS}
            selecionada={respondida ? "D" : null}
            resultado={respondida ? { correta: "C" } : null}
            desabilitado
            teclado={false}
            testidPrefixo="ads-alt"
          />
        </div>
      </article>

      <p className="px-1 text-[11px] leading-relaxed text-white/35" data-testid="ads-aviso-ilustrativo">
        Exemplo ilustrativo de como o Sapiens funciona. Não é uma questão do seu
        diagnóstico nem um resultado seu.
      </p>
    </div>
  );
}

/**
 * O gráfico do enunciado, em SVG inline.
 *
 * Sem imagem e sem biblioteca: são cinco retângulos e dois eixos. O `recharts`
 * que o produto usa nas telas de progresso pesa mais que a landing inteira, e
 * carregá-lo para desenhar cinco barras estáticas trocaria o ativo mais
 * importante desta página — o tempo até a primeira pintura — por nada.
 *
 * As cores vêm dos tokens da marca; as alturas são o dado do próprio
 * enunciado, e é a barra de 2021→2022 que sustenta a alternativa correta.
 */
function GraficoIlustrativo() {
  const barras = [
    { ano: "2018", valor: 38 },
    { ano: "2019", valor: 44 },
    { ano: "2020", valor: 42 },
    { ano: "2021", valor: 50 },
    { ano: "2022", valor: 76 },
  ];
  const max = 80;
  const largura = 40;
  const vao = 16;
  const alturaCaixa = 110;

  return (
    <svg
      viewBox={`0 0 ${barras.length * (largura + vao)} ${alturaCaixa + 22}`}
      className="mt-4 w-full max-w-[280px]"
      role="img"
      aria-label="Gráfico de barras da produção anual entre 2018 e 2022, com o maior salto entre 2021 e 2022."
      data-testid="ads-grafico"
    >
      {barras.map((b, i) => {
        const altura = (b.valor / max) * alturaCaixa;
        const x = i * (largura + vao);
        return (
          <g key={b.ano}>
            <rect
              x={x}
              y={alturaCaixa - altura}
              width={largura}
              height={altura}
              rx="5"
              fill={i === barras.length - 1 ? "#2E7FD6" : "#9DC4EC"}
            />
            <text
              x={x + largura / 2}
              y={alturaCaixa + 16}
              textAnchor="middle"
              fontSize="10"
              fill="#52607A"
              fontWeight="600"
            >
              {b.ano}
            </text>
          </g>
        );
      })}
      <line
        x1="0"
        y1={alturaCaixa + 0.5}
        x2={barras.length * (largura + vao)}
        y2={alturaCaixa + 0.5}
        stroke="#C8D6E8"
        strokeWidth="1"
      />
    </svg>
  );
}
