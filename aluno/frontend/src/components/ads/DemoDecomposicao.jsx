import Demo, { Achado, FaixaDeAnalise, LinhaRevelada } from "./Demo";
import { useRoteiro } from "./movimento";

/**
 * DEMO DE `/ads/como-voce-estuda` — o número vira estudo.
 *
 * Seis estados, em laço:
 *
 *   0. 72% de acerto                  ← o número com que todo mundo para
 *   1. 28% de erros                   ← o mesmo simulado, virado do avesso
 *   2. os erros se separam em quatro naturezas
 *   3. 3 padrões prioritários
 *   4. habilidades para desenvolver
 *   5. próxima sequência de estudo
 *
 * O argumento da página está na virada do passo 0 para o 1: é o MESMO
 * simulado, e a diferença é para qual metade se olha. Por isso o 72% não
 * some — ele encolhe e continua ali ao lado do 28%, que cresce. Se o número
 * bom desaparecesse, a página estaria dizendo "sua nota não importa", que não
 * é a afirmação e afastaria exatamente quem vai bem e quer ir melhor.
 *
 * ---------------------------------------------------------------------------
 * OS NÚMEROS SÃO DA CENA, NUNCA DE QUEM ESTÁ LENDO
 * ---------------------------------------------------------------------------
 *
 * 72/28 e as quatro naturezas são um exemplo montado. A moldura `Demo` carrega
 * o selo "Demonstração" e a página repete isso em texto sob a peça. Uma
 * landing que anima uma porcentagem sem dizer de quem ela é está, na prática,
 * afirmando saber algo sobre uma pessoa que acabou de chegar de um anúncio —
 * e o produto não inventa resultado nem dentro nem fora dele.
 *
 * As quatro naturezas de erro são ditas em português comum. Os nomes reais da
 * ontologia são a propriedade intelectual do produto e não aparecem para o
 * aluno em nenhuma superfície, muito menos numa página pública.
 */

const NATUREZAS = [
  { nome: "Interpretação", peso: 42 },
  { nome: "Estratégia", peso: 28 },
  { nome: "Conhecimento", peso: 18 },
  { nome: "Atenção", peso: 12 },
];

const DURACOES = [1300, 1200, 1400, 1200, 1100, 1400];

const NARRACAO = [
  "Um simulado de exemplo, com 72 por cento de acerto.",
  "Os mesmos resultados, olhados pelos 28 por cento de erro.",
  "Os erros se separam em quatro naturezas: interpretação, estratégia, conhecimento e atenção.",
  "Três padrões prioritários.",
  "Habilidades para desenvolver.",
  "Próxima sequência de estudo.",
];

export default function DemoDecomposicao() {
  const [alvo, passo, { reiniciar }] = useRoteiro(DURACOES);

  const virou = passo >= 1;

  return (
    <div ref={alvo}>
      <Demo
        olho="Demonstração"
        passo={passo}
        passos={DURACOES.length}
        aoRever={reiniciar}
        narracao={NARRACAO[passo]}
        testid="ads-demo-decomposicao"
      >
        {/* Os dois números, lado a lado. Quem manda no tamanho é `data-foco`:
            a troca de protagonista é uma transição de escala e cor, não uma
            troca de elemento — trocar faria o bloco piscar e mudar de altura. */}
        <div className="flex items-end justify-center gap-6" data-testid="ads-demo-numeros">
          <Numero valor="72%" rotulo="de acerto" foco={!virou} tom="neutro" />
          <Numero valor="28%" rotulo="de erros" foco={virou} tom="sinal" />
        </div>

        <p className="mt-2 text-center text-[11px] text-white/30">
          simulado de exemplo — não são seus resultados
        </p>

        {/* As quatro naturezas. As barras crescem do zero quando o passo 2
            chega; a altura do bloco já está reservada desde o começo. */}
        <div className="mt-4 min-h-[112px]">
          <LinhaRevelada visivel={passo >= 2}>
            <ul className="space-y-2" data-testid="ads-demo-naturezas">
              {NATUREZAS.map((n, i) => (
                <li key={n.nome} className="flex items-center gap-3">
                  <span className="w-[86px] shrink-0 text-[11px] font-semibold text-white/60">
                    {n.nome}
                  </span>
                  <span className="ads-barra">
                    <span
                      className="ads-barra-preenche"
                      style={{
                        width: passo >= 2 ? `${n.peso}%` : "0%",
                        transitionDelay: `${i * 110}ms`,
                      }}
                    />
                  </span>
                </li>
              ))}
            </ul>
          </LinhaRevelada>
        </div>

        <FaixaDeAnalise
          testid="ads-demo-decomposicao-saida"
          aguardando={passo < 3 ? "Agrupando os erros…" : null}
        >
          <LinhaRevelada visivel={passo >= 3}>
            <Achado rotulo="Padrões prioritários" valor="3 padrões, e não 28 erros soltos" />
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 4}>
            <Achado
              rotulo="Habilidades para desenvolver"
              valor="As que aparecem nos três padrões, em ordem de peso"
            />
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 5}>
            <Achado rotulo="Próxima sequência de estudo" valor="O que fazer na próxima semana" tom="acao" />
          </LinhaRevelada>
        </FaixaDeAnalise>
      </Demo>
    </div>
  );
}

/** Um número grande com rótulo pequeno. `.medida-n` é a primitiva do produto
 *  (tabular de propósito: um número que troca de largura faz a linha dançar). */
function Numero({ valor, rotulo, foco, tom }) {
  return (
    <div className="ads-numero text-center" data-foco={foco ? "1" : "0"} data-tom={tom}>
      <div className="medida-n ads-numero-valor">{valor}</div>
      <div className="medida-rotulo">{rotulo}</div>
    </div>
  );
}
