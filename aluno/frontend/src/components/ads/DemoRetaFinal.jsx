import { proximaProva, tempoRestante } from "../../lib/enem";
import Demo, { Achado, FaixaDeAnalise, LinhaRevelada } from "./Demo";
import { useRoteiro } from "./movimento";

/**
 * DEMO DE `/ads/reta-final` — os dias que sobraram viram um plano.
 *
 * As outras quatro demos mostram o Sapiens lendo um ERRO. Esta mostra a outra
 * metade do produto, que nenhuma landing tinha usado: `prioridade_enem`, a
 * resposta única a "o que estudar agora". O ângulo é TEMPO, e o público está
 * a menos de dois meses da prova.
 *
 * Seis estados, em laço:
 *
 *   0. o número de dias, grande e sozinho
 *   1. ele encolhe; a data da prova aparece como destino
 *   2. o número se ESTILHAÇA em um quadradinho por dia, espalhados
 *   3. eles ficam ali, parados e IDÊNTICOS — nada diz qual importa
 *   4. eles se encaixam numa grade de semana; alguns crescem e acendem
 *   5. "nem toda hora de estudo rende o mesmo"
 *
 * ---------------------------------------------------------------------------
 * A TESE VISUAL, EM UMA FRASE
 * ---------------------------------------------------------------------------
 *
 * **No caos todos os quadrados são iguais; na ordem, alguns valem mais.**
 *
 * É literalmente o que `prioridade_enem` faz — `peso × lacuna × confiança`
 * decide onde a próxima hora rende mais ponto — dito sem fórmula, sem número
 * inventado e sem uma palavra de explicação. O passo 3 existe só para o passo
 * 4 ter o que desmentir: sem ver os quadrados indistinguíveis primeiro, a
 * organização depois não significa nada.
 *
 * ---------------------------------------------------------------------------
 * O NÚMERO É MEDIDO, NUNCA ESCRITO
 * ---------------------------------------------------------------------------
 *
 * Os dias vêm de `lib/enem.proximaProva`/`tempoRestante` — a MESMA fonte da
 * contagem que já roda em cinco telas do produto. Uma landing de urgência com
 * número digitado à mão seria a única peça do Sapiens capaz de mentir sozinha
 * no dia seguinte.
 *
 * E quando os dois domingos passam, `proximaProva` devolve `null`: a demo
 * inteira some da página em vez de mostrar contagem negativa ou reciclar o
 * ano seguinte sem alguém ter revisado o calendário.
 */

/** Um quadradinho por dia restante, com teto. Acima de ~50 a grade vira
 *  confete e o olho para de contar — o que importa é ler "são muitos e são
 *  todos iguais", não auditar a quantidade. */
const TETO_DE_QUADRADOS = 49;

const DURACOES = [1500, 1300, 1400, 1500, 1600, 1800];

/**
 * O deslocamento de cada quadrado no estado espalhado.
 *
 * Determinístico por índice, e não `Math.random()`: o mesmo quadrado tem de
 * cair no mesmo lugar a cada volta do laço. Com aleatório, cada repetição
 * redesenha o caos de um jeito diferente e a peça lê como ruído animado em
 * vez de um estado que existe e depois se resolve.
 */
function desvio(i) {
  const h = Math.sin(i * 127.1) * 43758.5453;
  const a = h - Math.floor(h);
  const g = Math.sin(i * 311.7) * 24634.6345;
  const b = g - Math.floor(g);
  return {
    x: (a - 0.5) * 54,
    y: (b - 0.5) * 30,
    giro: (a - 0.5) * 38,
  };
}

/** Quais quadrados "valem mais" no estado organizado.
 *
 *  Posições fixas e espalhadas pelas sete colunas — não é medida de ninguém,
 *  é a forma de dizer "alguns pesam mais" sem inventar percentual nenhum.
 *
 *  A primeira escolha caía numa diagonal (3, 9, 10, 16, 22…) e, com sete
 *  colunas, desenhava uma escada. Escada lê como ornamento: o olho vê um
 *  padrão geométrico e para de procurar significado. Espalhados, os mesmos
 *  dez quadrados leem como seleção. */
const DESTACADOS = new Set([1, 5, 10, 14, 20, 23, 32, 36, 40, 45]);

export default function DemoRetaFinal() {
  const [alvo, passo, { reiniciar, visivel }] = useRoteiro(DURACOES);

  const prova = proximaProva();
  // Sem prova à frente, a peça inteira sai do ar. Ver a nota do topo.
  if (!prova) return null;

  const dias = tempoRestante(prova.inicio).dias;
  const quantos = Math.min(dias, TETO_DE_QUADRADOS);
  const dataProva = new Date(prova.inicio).toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "long",
  });

  const espalhado = passo >= 2 && passo <= 3;
  const organizado = passo >= 4;

  return (
    <div ref={alvo}>
      <Demo
        olho="Reta final"
        passo={passo}
        passos={DURACOES.length}
        aoRever={reiniciar}
        narracao={NARRACAO(dias, dataProva)[passo]}
        testid="ads-demo-reta"
      >
        {/* O número e o destino. `data-foco` encolhe o número quando a data
            entra — mesma técnica da demo de decomposição: quem troca de
            protagonista é a escala, não o elemento, senão o bloco pisca e
            muda de altura. */}
        <div className="flex items-end justify-between gap-4" data-testid="ads-reta-topo">
          <div className="ads-reta-numero" data-foco={passo === 0 ? "1" : "0"}>
            <div className="medida-n ads-reta-valor" data-testid="ads-reta-dias">{dias}</div>
            <div className="medida-rotulo">dias para o ENEM</div>
          </div>

          <LinhaRevelada visivel={passo >= 1} className="text-right">
            <div className="font-mono-alt text-[10px] font-semibold uppercase tracking-[0.2em] text-white/40">
              A prova
            </div>
            <div className="mt-0.5 text-[15px] font-bold text-[#9BE8FF]">{dataProva}</div>
          </LinhaRevelada>
        </div>

        {/* A grade. Ela existe desde o primeiro quadro com a altura final: o
            que muda é o `transform` de cada quadrado, que o compositor anima
            sozinho e que não toca no layout. Revelar criando elementos faria
            o cartão crescer no meio da sequência. */}
        <div className="ads-reta-grade" data-testid="ads-reta-grade" aria-hidden="true">
          {Array.from({ length: quantos }, (_, i) => {
            const d = desvio(i);
            const forte = organizado && DESTACADOS.has(i);
            const estilo = espalhado
              ? { transform: `translate(${d.x}px, ${d.y}px) rotate(${d.giro}deg)` }
              : { transform: "translate(0,0) rotate(0deg)" };
            return (
              <span
                key={i}
                className={`ads-reta-dia ${visivel ? "ads-reta-dia-on" : ""} ${forte ? "ads-reta-dia-forte" : ""}`}
                style={{ ...estilo, transitionDelay: `${(i % 7) * 26}ms` }}
              />
            );
          })}
        </div>

        <FaixaDeAnalise
          testid="ads-reta-saida"
          altura="min-h-[104px]"
          aguardando={passo < 4 ? "Todos os dias parecem iguais…" : null}
        >
          <LinhaRevelada visivel={passo >= 4}>
            <Achado rotulo="Os mesmos dias, organizados" valor="Uma semana de estudo por vez" />
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 5}>
            <Achado
              rotulo="O que o Sapiens decide"
              valor="Nem toda hora de estudo rende o mesmo"
              tom="acao"
            />
          </LinhaRevelada>
        </FaixaDeAnalise>
      </Demo>
    </div>
  );
}

/** A narração para leitor de tela. Recebe o número medido — o texto não pode
 *  ter o número escrito, pela mesma razão que a tela não tem. */
const NARRACAO = (dias, data) => [
  `Faltam ${dias} dias para o ENEM.`,
  `A prova é em ${data}.`,
  `Os dias se separam, um a um.`,
  `Soltos, todos parecem iguais.`,
  `Organizados, viram uma semana de estudo.`,
  `Nem toda hora de estudo rende o mesmo.`,
];
