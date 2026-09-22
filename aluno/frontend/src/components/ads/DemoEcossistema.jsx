import Demo, { Achado, FaixaDeAnalise, LinhaRevelada } from "./Demo";
import { useRoteiro } from "./movimento";

/**
 * DEMO DE `/ads/sem-mensalidade` — um número pesado vira muitas coisas.
 *
 * O sexto ângulo, e o primeiro cujo argumento é CUSTO. Seis estados:
 *
 *   0. R$ 6.000, sozinho, ocupando a tela
 *   1. ele encolhe para um canto
 *   2-3. as peças do produto entram, preenchendo o vazio que ele deixou
 *   4. o que é de graça
 *   5. o que não é — e como se paga
 *
 * A virada visual é **um número grande sozinho → muitas coisas concretas**.
 * A alternativa óbvia seria uma comparação de barras, que é fraca por dois
 * motivos: barra contra barra convida a comparar valores (e o Sapiens não
 * tem um valor a comparar, tem outro modelo), e barra é a forma mais
 * genérica possível de dizer "somos mais baratos".
 *
 * ---------------------------------------------------------------------------
 * O PASSO 5 É A PEÇA MAIS IMPORTANTE, E É O QUE QUASE TODO ANÚNCIO OMITE
 * ---------------------------------------------------------------------------
 *
 * O Sapiens é **freemium, não gratuito**: responder questão, ler o
 * diagnóstico e montar o cronograma não custam nada; curso, e-book, redação
 * corrigida e a Mentis custam Sparks (ver `produto/economia-de-sparks.md` —
 * e nunca cite um preço daqui sem conferir a constante no backend).
 *
 * Dizer isso na própria peça não é cautela jurídica, é conversão: quem chega
 * de um anúncio que promete tudo de graça e bate num paywall na terceira tela
 * não volta, e ainda reclama. Quem chega sabendo que o diagnóstico é de graça
 * e o resto se paga por uso, chega com a expectativa certa.
 *
 * Por isso o último passo não é o CTA — é a linha que diz o que é o quê.
 */

/** O que o produto de fato oferece. Nenhum item aqui é aspiracional: todos
 *  são telas que existem hoje. `livre` marca o que não custa Spark nenhum —
 *  conferido contra a tabela de `economia-de-sparks.md`. */
const PECAS = [
  { nome: "Provas do ENEM", livre: true },
  { nome: "Diagnóstico dos erros", livre: true },
  { nome: "Cronograma da semana", livre: true },
  { nome: "Mapa de treino", livre: true },
  { nome: "Cursos", livre: false },
  { nome: "E-books", livre: false },
  { nome: "Redação corrigida", livre: false },
  { nome: "Mentoria e aula ao vivo", livre: false },
];

const DURACOES = [1500, 1200, 1300, 1300, 1500, 1800];

const NARRACAO = [
  "Existem plataformas de preparação que custam seis mil reais.",
  "Seis mil reais, em algumas delas.",
  "O Sapiens oferece provas do ENEM, diagnóstico dos erros, cronograma e mapa de treino.",
  "E também cursos, e-books, correção de redação, mentoria e aula ao vivo.",
  "O diagnóstico é de graça.",
  "Não há mensalidade: o resto você paga só se usar.",
];

export default function DemoEcossistema() {
  const [alvo, passo, { reiniciar }] = useRoteiro(DURACOES);

  // As peças entram em duas ondas: as gratuitas primeiro. A ordem não é
  // estética — é o argumento. Quem vê a lista começando pelo que não custa
  // nada lê "isto aqui eu já posso usar", e não "isto aqui é a vitrine".
  const ondaDe = (i) => (i < 4 ? 2 : 3);

  return (
    <div ref={alvo}>
      <Demo
        olho="Demonstração"
        passo={passo}
        passos={DURACOES.length}
        aoRever={reiniciar}
        narracao={NARRACAO[passo]}
        testid="ads-demo-ecossistema"
      >
        {/* O número pesado. `data-foco` encolhe quando as peças entram —
            mesma técnica das outras demos: troca de protagonista por escala,
            nunca por troca de elemento, senão o bloco pisca e muda de
            altura. A altura é reservada para o estado maior. */}
        <div className="ads-eco-topo">
          <div className="ads-eco-preco" data-foco={passo === 0 ? "1" : "0"}>
            <div className="medida-n ads-eco-valor" data-testid="ads-eco-valor">R$ 6.000</div>
            <div className="medida-rotulo">em algumas plataformas</div>
          </div>
        </div>

        {/* As peças. Todas existem no DOM desde o primeiro quadro, e o que
            muda é a opacidade: criar elemento no meio da sequência faria o
            cartão crescer e empurrar a página sob o dedo de quem lê. */}
        <ul className="ads-eco-pecas" data-testid="ads-eco-pecas">
          {PECAS.map((p, i) => (
            <li
              key={p.nome}
              className={`chip ads-eco-peca ${passo >= ondaDe(i) ? "ads-eco-peca-on" : ""} ${p.livre ? "ads-eco-peca-livre" : ""}`}
              style={{ transitionDelay: `${(i % 4) * 70}ms` }}
            >
              {p.nome}
            </li>
          ))}
        </ul>

        <FaixaDeAnalise
          testid="ads-eco-saida"
          altura="min-h-[104px]"
          aguardando={passo < 4 ? "Comparando o que você recebe…" : null}
        >
          <LinhaRevelada visivel={passo >= 4}>
            <Achado rotulo="De graça" valor="Questões, diagnóstico e cronograma" tom="acao" />
          </LinhaRevelada>

          <LinhaRevelada visivel={passo >= 5}>
            <Achado rotulo="Sem mensalidade" valor="O resto, você paga só se usar" />
          </LinhaRevelada>
        </FaixaDeAnalise>
      </Demo>
    </div>
  );
}
