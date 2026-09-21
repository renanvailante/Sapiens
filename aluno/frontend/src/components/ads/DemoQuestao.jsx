import { useCallback, useEffect, useRef, useState } from "react";
import Alternativas from "../questao/Alternativas";
import Demo, { Achado, FaixaDeAnalise, LinhaRevelada } from "./Demo";
import { semMovimento } from "./movimento";

/**
 * DEMO DE `/ads/10-questoes` — a única em que o visitante TOCA.
 *
 * As outras três rodam sozinhas: elas mostram. Esta responde. É a diferença
 * entre assistir a uma demonstração e ter tido uma, e é o que o ângulo
 * "desafio" promete no anúncio — se a página pede para começar um desafio e
 * não deixa a pessoa fazer nada, o anúncio mentiu na primeira tela.
 *
 * ---------------------------------------------------------------------------
 * ISTO NÃO É UMA QUESTÃO DO PRODUTO, E NÃO PODE VIRAR UMA
 * ---------------------------------------------------------------------------
 *
 * Tudo aqui é local, e cada "não" abaixo é deliberado:
 *
 * - **não chama API** — nenhuma rota, nem pública nem autenticada;
 * - **não grava resposta** — nada em `students/{uid}/behavior`; não existe
 *   `uid`, e inventar perfil anônimo para uma landing seria construir a
 *   arquitetura paralela que não deve existir;
 * - **não chama Gemini** e **não consome Sparks** — não há o que cobrar de
 *   quem não tem conta, e uma landing que gasta orçamento de IA por visitante
 *   de anúncio é um custo que cresce com a verba de mídia;
 * - **não lê o Firestore** — um visitante de anúncio custa zero leitura.
 *
 * O que a pessoa responde aqui morre no navegador dela. O diagnóstico de
 * verdade é o que está do outro lado do CTA.
 *
 * ---------------------------------------------------------------------------
 * O QUE ELA GANHA POR TER TOCADO
 * ---------------------------------------------------------------------------
 *
 * Nada de "certo!" ou "errado!" — esse é justamente o produto que o Sapiens
 * não é. O retorno é uma leitura curta do que aquela escolha indica, igual à
 * devolutiva determinística que a rodada de dez questões dá dentro do
 * produto. Por isso a análise existe nos DOIS casos: quem acerta também
 * recebe uma leitura, porque acertar por eliminação e acertar por
 * compreensão não são a mesma coisa, e é isso que a página está afirmando.
 */

/* Curtas o bastante para caberem em uma ou duas linhas a 390px. Aqui a
   pessoa precisa LER e ESCOLHER, então o limite é mais frouxo do que na demo
   automática do `/ads/diagnostico` — mas quatro alternativas de três linhas
   empurravam a análise para muito longe da dobra, e a análise é o que
   recompensa quem tocou. */
const ALTERNATIVAS = [
  { letra: "A", texto: "Cresceu de forma constante." },
  { letra: "B", texto: "O maior salto foi no último intervalo." },
  { letra: "C", texto: "A população dobrou no período." },
  { letra: "D", texto: "Houve queda em algum intervalo." },
];

const CORRETA = "B";

/** A leitura de cada escolha. Não é gabarito comentado: é o que o erro (ou o
 *  acerto) INDICA — a única coisa que esta página está prometendo. */
const LEITURA = {
  A: { erro: "Leitura global do gráfico", habilidade: "Comparar intervalos, não só o começo e o fim" },
  B: { erro: null, habilidade: "Comparar variação entre intervalos" },
  C: { erro: "Estimativa sem conferir a escala", habilidade: "Ler valores no eixo antes de concluir" },
  D: { erro: "Leitura de tendência", habilidade: "Distinguir queda de crescimento mais lento" },
};

export default function DemoQuestao({ aoInteragir }) {
  const [escolhida, setEscolhida] = useState(null);
  const [fase, setFase] = useState(0); // 0 aguardando · 1 registrada · 2 leitura · 3 fecho
  const relogios = useRef([]);

  const limpar = useCallback(() => {
    relogios.current.forEach(clearTimeout);
    relogios.current = [];
  }, []);

  useEffect(() => limpar, [limpar]);

  const responder = useCallback((letra) => {
    if (escolhida) return;
    setEscolhida(letra);
    setFase(1);
    aoInteragir?.(letra);

    // Quem pediu menos movimento recebe a leitura inteira de uma vez: a
    // encenação em três tempos É o movimento, e uma versão mais lenta dela
    // não atende o pedido.
    if (semMovimento()) {
      setFase(3);
      return;
    }
    limpar();
    relogios.current.push(setTimeout(() => setFase(2), 700));
    relogios.current.push(setTimeout(() => setFase(3), 1600));
  }, [escolhida, aoInteragir, limpar]);

  const refazer = useCallback(() => {
    limpar();
    setEscolhida(null);
    setFase(0);
  }, [limpar]);

  const leitura = escolhida ? LEITURA[escolhida] : null;
  const acertou = escolhida === CORRETA;

  return (
    <Demo
      // O selo é o MESMO das outras três. "Demonstração · você responde"
      // quebrava em duas linhas a 390px e deslocava o trilho de passos — e o
      // convite a tocar já mora dentro do painel ("Toque numa alternativa…"),
      // onde ele é lido no momento em que serve.
      olho="Demonstração"
      passo={fase}
      passos={4}
      aoRever={escolhida ? refazer : null}
      narracao={
        fase === 0
          ? "Questão 1 de 10. Escolha uma alternativa."
          : fase >= 3
          ? `Resposta registrada. ${leitura?.habilidade || ""}`
          : "Resposta registrada."
      }
      testid="ads-demo-questao"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="font-mono-alt text-[11px] font-bold text-white/70">
          Questão 1 <span className="text-white/30">de 10</span>
        </span>
        <div className="flex flex-1 justify-end gap-1" aria-hidden="true">
          {Array.from({ length: 10 }, (_, i) => (
            <span
              key={i}
              className={`h-1.5 w-full max-w-[14px] rounded-full transition-colors duration-300 ${
                i === 0 && escolhida ? "bg-[#4FD9FF]" : "bg-white/12"
              }`}
            />
          ))}
        </div>
      </div>

      <article className="leitura-clara rounded-2xl p-4">
        <p className="text-[14px] leading-relaxed text-zinc-800">
          O gráfico abaixo mostra a população de uma espécie em quatro medições.
          Qual afirmação ele sustenta?
        </p>

        <GraficoDaDemo />

        <div className="mt-3.5">
          {/* `teclado` fica LIGADO aqui, e é de graça: `Alternativas` já
              responde a A–E em todo o produto. Numa landing isso é o teste de
              teclado da questão resolvido sem escrever nada. */}
          <Alternativas
            alternativas={ALTERNATIVAS}
            selecionada={escolhida}
            resultado={escolhida ? { correta: CORRETA } : null}
            aoEscolher={responder}
            testidPrefixo="ads-q"
          />
        </div>
      </article>

      <FaixaDeAnalise
        testid="ads-demo-questao-saida"
        altura="min-h-[204px]"
        aguardando={fase === 0 ? "Toque numa alternativa para ver o que o Sapiens lê nela." : null}
      >
        <LinhaRevelada visivel={fase >= 1}>
          <div className="flex items-center gap-2.5">
            <span className={fase >= 2 ? "ads-ponto ads-ponto-sinal" : "ads-pulso"} aria-hidden="true" />
            <span className="text-[13px] font-semibold text-white/70">
              {fase >= 2 ? "Resposta registrada." : "Registrando…"}
            </span>
          </div>
        </LinhaRevelada>

        <LinhaRevelada visivel={fase >= 2}>
          <Achado
            rotulo={acertou ? "O que esse acerto indica" : "O que esse erro indica"}
            valor={leitura?.erro || "Comparação correta entre intervalos"}
            tom={acertou ? "sinal" : "erro"}
          />
        </LinhaRevelada>

        <LinhaRevelada visivel={fase >= 3}>
          <Achado rotulo="Habilidade envolvida" valor={leitura?.habilidade} tom="acao" />
        </LinhaRevelada>

        <LinhaRevelada visivel={fase >= 3}>
          <p className="pt-0.5 text-[12px] leading-relaxed text-white/45">
            Seu resultado não é só “certo” ou “errado”. Com 10 questões, o
            diagnóstico identifica os padrões por trás das respostas.
          </p>
        </LinhaRevelada>

      </FaixaDeAnalise>
    </Demo>
  );
}

/**
 * O gráfico do enunciado, em SVG inline.
 *
 * Quatro retângulos e um eixo. O `recharts` que o produto usa nas telas de
 * progresso pesa mais do que esta landing inteira, e carregá-lo para desenhar
 * quatro barras paradas trocaria o ativo mais importante da página — o tempo
 * até a primeira pintura — por nada.
 *
 * As alturas são o dado que sustenta a alternativa correta: o maior salto
 * está no último intervalo, e nenhum intervalo cai.
 */
function GraficoDaDemo() {
  const barras = [
    { rotulo: "1ª", valor: 30 },
    { rotulo: "2ª", valor: 38 },
    { rotulo: "3ª", valor: 44 },
    { rotulo: "4ª", valor: 72 },
  ];
  const max = 78;
  const largura = 38;
  const vao = 18;
  const caixa = 96;

  return (
    <svg
      viewBox={`0 0 ${barras.length * (largura + vao)} ${caixa + 20}`}
      className="mt-3 w-full max-w-[220px]"
      role="img"
      aria-label="Gráfico de barras com quatro medições: 30, 38, 44 e 72. O maior salto está entre a terceira e a quarta."
      data-testid="ads-demo-grafico"
    >
      {barras.map((b, i) => {
        const altura = (b.valor / max) * caixa;
        const x = i * (largura + vao);
        return (
          <g key={b.rotulo}>
            <rect
              x={x}
              y={caixa - altura}
              width={largura}
              height={altura}
              rx="5"
              fill={i === barras.length - 1 ? "#2E7FD6" : "#9DC4EC"}
            />
            <text
              x={x + largura / 2}
              y={caixa + 15}
              textAnchor="middle"
              fontSize="10"
              fill="#52607A"
              fontWeight="600"
            >
              {b.rotulo}
            </text>
          </g>
        );
      })}
      <line
        x1="0"
        y1={caixa + 0.5}
        x2={barras.length * (largura + vao)}
        y2={caixa + 0.5}
        stroke="#C8D6E8"
        strokeWidth="1"
      />
    </svg>
  );
}
