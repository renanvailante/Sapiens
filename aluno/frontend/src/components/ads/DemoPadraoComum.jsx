import { X } from "lucide-react";
import Demo, { Achado, FaixaDeAnalise, LinhaRevelada } from "./Demo";
import { useRoteiro } from "./movimento";

/**
 * DEMO DE `/ads/mesmo-erro` — três erros que parecem diferentes e não são.
 *
 * Seis estados, em laço:
 *
 *   0. três questões de matérias diferentes, todas erradas
 *   1. "parecem três problemas diferentes"     ← a leitura que a pessoa já tem
 *   2. três linhas descem e CONVERGEM num ponto
 *   3. 1 padrão em comum
 *   4. Interpretação
 *   5. Habilidade para treinar
 *
 * O passo 2 é a página inteira. A dor do ângulo ("estudo e continuo errando")
 * é feita de erros que a pessoa arquiva como azar separado; o produto existe
 * porque eles não são separados. Mostrar isso com três cartões parados ao
 * lado de um texto explicando a convergência seria pedir que ela acredite na
 * frase. O desenho tem de fazer a convergência ACONTECER.
 *
 * ---------------------------------------------------------------------------
 * AS LINHAS SÃO SVG COM `stroke-dashoffset`, E NÃO UMA BIBLIOTECA
 * ---------------------------------------------------------------------------
 *
 * Três curvas desenhando-se é o caso de escola do truque de dash: o traço
 * inteiro vira um "tracejado" do próprio comprimento, e animar o deslocamento
 * faz a linha nascer da origem até o destino. É uma transição de CSS sobre uma
 * propriedade que o compositor anima sozinho — sem JavaScript por quadro, sem
 * `framer-motion` (que está no pacote e pesaria mais do que este arquivo
 * inteiro), e com o `prefers-reduced-motion` resolvido de graça porque o
 * roteiro já entrega o último passo pronto.
 *
 * As matérias são propositalmente distantes (linguagens, biologia, química):
 * é o que torna a convergência surpreendente. Se as três fossem de
 * matemática, "tem um padrão em comum" seria óbvio e não provaria nada.
 *
 * Nenhum nome da ontologia aparece aqui — o padrão é dito na língua do
 * vestibulando, igual o produto já faz com ele.
 */

const QUESTOES = [
  { materia: "Linguagens", resumo: "Texto sobre mobilidade urbana" },
  { materia: "Biologia", resumo: "Gráfico de população de uma espécie" },
  { materia: "Química", resumo: "Tabela de solubilidade" },
];

const DURACOES = [1100, 1200, 1100, 1200, 1100, 1400];

const NARRACAO = [
  "Três questões erradas, de três matérias diferentes.",
  "À primeira vista, parecem três problemas diferentes.",
  "As três se conectam.",
  "Um padrão em comum entre os três erros.",
  "O padrão é de interpretação.",
  "Habilidade para treinar: ler informação apresentada em gráfico e tabela.",
];

export default function DemoPadraoComum() {
  const [alvo, passo, { reiniciar, visivel }] = useRoteiro(DURACOES);

  return (
    <div ref={alvo}>
      <Demo
        olho="Demonstração"
        passo={passo}
        passos={DURACOES.length}
        aoRever={reiniciar}
        narracao={NARRACAO[passo]}
        testid="ads-demo-padrao"
      >
        {/* As três questões. Empilhadas, e não lado a lado: a 320px três
            cartões numa linha viram três colunas de texto espremido — o
            defeito de `flex-wrap` documentado em `ux/mobile.md`. */}
        <ul className="space-y-2" data-testid="ads-demo-questoes">
          {QUESTOES.map((q, i) => (
            <li
              key={q.materia}
              className={`ads-erro-cartao ads-revela ${visivel ? "ads-revela-on" : ""}`}
              style={{ transitionDelay: `${i * 90}ms` }}
              data-testid={`ads-demo-questao-${i}`}
            >
              <span className="ads-erro-marca" aria-hidden="true">
                <X className="h-3 w-3" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[13px] font-bold leading-tight text-white/85">
                  {q.materia}
                </span>
                <span className="block truncate text-[11px] leading-tight text-white/40">
                  {q.resumo}
                </span>
              </span>
              <span className="font-mono-alt text-[10px] font-bold uppercase tracking-[0.14em] text-rose-300/80">
                errou
              </span>
            </li>
          ))}
        </ul>

        {/* A legenda que morre no passo 2: ela existe para ser DESMENTIDA
            pelas linhas, então precisa ter sido lida antes delas. */}
        <div className="mt-2 h-4">
          <LinhaRevelada visivel={passo === 1}>
            <p className="text-center text-[11px] italic text-white/35">
              parecem três problemas diferentes
            </p>
          </LinhaRevelada>
        </div>

        <Funil ativo={passo >= 2} />

        <FaixaDeAnalise
          testid="ads-demo-padrao-saida"
          aguardando={passo < 3 ? "Procurando o que se repete…" : null}
        >
          <LinhaRevelada visivel={passo >= 3}>
            <div className="ads-no-padrao" data-testid="ads-demo-no">
              <span className="font-mono-alt text-[10px] font-semibold uppercase tracking-[0.2em] text-[#7FD8FF]/80">
                1 padrão em comum
              </span>
            </div>
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 4}>
            <Achado rotulo="O que se repete" valor="Interpretação" />
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 5}>
            <Achado
              rotulo="Habilidade para treinar"
              valor="Ler informação apresentada em gráfico e tabela"
              tom="acao"
            />
          </LinhaRevelada>
        </FaixaDeAnalise>
      </Demo>
    </div>
  );
}

/**
 * As três curvas que descem dos cartões e se juntam num ponto só.
 *
 * `viewBox` com `preserveAspectRatio="none"` porque o desenho é puro
 * relacional — três origens espalhadas no topo, um destino no centro de
 * baixo. Esticar horizontalmente é exatamente o comportamento desejado quando
 * a caixa muda de largura, e evita ter de recalcular pontos em JavaScript a
 * cada `resize`.
 */
function Funil({ ativo }) {
  const curvas = [
    "M 10 0 C 10 22, 50 20, 50 42",
    "M 50 0 L 50 42",
    "M 90 0 C 90 22, 50 20, 50 42",
  ];

  return (
    <svg
      viewBox="0 0 100 44"
      preserveAspectRatio="none"
      className="my-1 h-11 w-full"
      aria-hidden="true"
      data-testid="ads-demo-funil"
      data-ativo={ativo ? "1" : "0"}
    >
      {curvas.map((d, i) => (
        <path
          key={d}
          d={d}
          fill="none"
          stroke="#4FD9FF"
          strokeWidth="0.8"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
          // `pathLength="1"` é o que faz o CSS funcionar: ele reescala o
          // comprimento da curva para 1, então `stroke-dasharray: 1` é
          // exatamente UM traço do tamanho da linha inteira, e animar o
          // deslocamento de 1 até 0 faz a linha nascer da origem. Sem isto,
          // "1" seria uma unidade do viewBox e as três curvas apareceriam
          // pontilhadas em vez de se desenhando — e as três têm comprimentos
          // diferentes, então nenhum valor fixo serviria para as três.
          pathLength="1"
          className={`ads-traco ${ativo ? "ads-traco-on" : ""}`}
          style={{ transitionDelay: `${i * 110}ms` }}
        />
      ))}
    </svg>
  );
}
