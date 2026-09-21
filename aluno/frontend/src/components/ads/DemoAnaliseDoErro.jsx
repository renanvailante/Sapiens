import Alternativas from "../questao/Alternativas";
import Demo, { Achado, FaixaDeAnalise, LinhaRevelada } from "./Demo";
import { useRoteiro } from "./movimento";

/**
 * DEMO DE `/ads/diagnostico` — uma questão sendo LIDA pelo Sapiens.
 *
 * Seis estados, em laço:
 *
 *   0. a questão, alternativas livres
 *   1. uma alternativa é marcada
 *   2. "Analisando seu erro…"        ← o beat que separa resposta de veredito
 *   3. Erro identificado  → interpretação da informação
 *   4. Habilidade         → inferência a partir do texto
 *   5. Próximo passo      → treinar questões focadas nessa habilidade
 *
 * O passo 2 é o argumento inteiro da página. Um produto comum vai de "marcou
 * C" para "errado" em um quadro; o Sapiens põe uma etapa no meio, e é essa
 * etapa que a landing precisa deixar a pessoa VER acontecendo. Sem ela, a
 * demo mostra um corretor de gabarito.
 *
 * ---------------------------------------------------------------------------
 * A QUESTÃO É DESENHADA PELO PRODUTO DE VERDADE
 * ---------------------------------------------------------------------------
 *
 * `components/questao/Alternativas` é a MESMA peça das provas do ENEM, do
 * mapa de treino e dos blocos de curso — mesmo verde, mesmo vermelho, mesmo
 * pé sólido, mesma letra que vira ícone quando a resposta chega. O estado da
 * alternativa é dado (`data-estado`) e quem pinta é o CSS, então basta mudar
 * `selecionada`/`resultado` conforme o passo e o produto se desenha sozinho.
 *
 * > **`.leitura-clara` em volta é obrigatório.** `.alternativa` tem papel
 * > branco próprio e o texto dentro usa `text-zinc-*`, que a camada de
 * > tradução do `index.css` CLAREIA fora desse envelope. Sem ele: texto claro
 * > sobre papel branco. Ver `ux/sistema-visual.md`.
 *
 * O enunciado é escrito para a landing, não é item do acervo, e a moldura
 * `Demo` carrega o selo que diz isso.
 */

/* Cada alternativa cabe em UMA linha a 390px, e o limite é MEDIDO, não
   estimado: `.alternativa` gasta 32px de respiro, 30px de letra e 12px de
   vão, e o cartão está dentro de três contêineres com respiro próprio — a
   390px sobram ~212px de texto, ou seja ~26 caracteres. Escrever 35 e supor
   que cabe foi o erro da primeira versão.
 *
 * Por que isso importa mais do que parece: com duas linhas por alternativa o
 * cartão media 481px e empurrava a faixa de análise 164px abaixo da dobra.
 * Quem não rolasse via um quiz — e o quiz é justamente o produto que o
 * Sapiens NÃO é. */
const ALTERNATIVAS = [
  { letra: "A", texto: "O hábito de ler caiu." },
  { letra: "B", texto: "Mudou o que é ler." },
  { letra: "C", texto: "Texto curto não é leitura." },
  { letra: "D", texto: "Dois tempos comparados." },
];

const MARCADA = "C";
const CORRETA = "B";

/** Quanto cada passo dura. "Analisando" respira; os achados ficam de pé para
 *  serem lidos; o último segura antes de o laço recomeçar (`pausaDoLaco`). */
const DURACOES = [1100, 900, 1300, 1200, 1200, 1400];

const NARRACAO = [
  "Uma questão de interpretação de texto, com quatro alternativas.",
  "A alternativa C é marcada.",
  "O Sapiens está analisando o erro.",
  "Erro identificado: interpretação da informação.",
  "Habilidade relacionada: inferência a partir do texto.",
  "Próximo passo: treinar questões focadas nessa habilidade.",
];

export default function DemoAnaliseDoErro() {
  const [alvo, passo, { reiniciar }] = useRoteiro(DURACOES);

  // A partir do passo 2 a resposta já "chegou": o `resultado` faz C ficar
  // vermelha e B verde, exatamente como numa prova de verdade.
  const respondida = passo >= 2;

  return (
    <div ref={alvo}>
      <Demo
        olho="Demonstração"
        passo={passo}
        passos={DURACOES.length}
        aoRever={reiniciar}
        narracao={NARRACAO[passo]}
        testid="ads-demo-analise"
      >
        <article className="leitura-clara rounded-2xl p-4">
          <p className="text-[14px] leading-relaxed text-zinc-800">
            “Ler deixou de ser um gesto e virou um ambiente.” O texto quer dizer que:
          </p>

          <div className="mt-3">
            <Alternativas
              alternativas={ALTERNATIVAS}
              selecionada={passo >= 1 ? MARCADA : null}
              resultado={respondida ? { correta: CORRETA } : null}
              desabilitado
              teclado={false}
              testidPrefixo="ads-demo-alt"
            />
          </div>
        </article>

        <FaixaDeAnalise
          testid="ads-demo-analise-saida"
          aguardando={passo < 2 ? "Aguardando a resposta…" : null}
        >
          <LinhaRevelada visivel={passo === 2}>
            <div className="flex items-center gap-2.5" data-testid="ads-demo-analisando">
              <span className="ads-pulso" aria-hidden="true" />
              <span className="text-[13px] font-semibold text-white/70">Analisando seu erro…</span>
            </div>
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 3}>
            <Achado rotulo="Erro identificado" valor="Interpretação da informação" tom="erro" />
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 4}>
            <Achado rotulo="Habilidade relacionada" valor="Inferência a partir do texto" />
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 5}>
            <Achado rotulo="Próximo passo" valor="Treinar questões focadas nessa habilidade" tom="acao" />
          </LinhaRevelada>
        </FaixaDeAnalise>
      </Demo>
    </div>
  );
}
