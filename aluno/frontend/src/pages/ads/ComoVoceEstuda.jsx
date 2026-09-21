import { ArrowRight } from "lucide-react";
import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CTA from "../../components/ads/CTA";
import ErrorAnalysisPreview from "../../components/ads/ErrorAnalysisPreview";

/**
 * `/ads/como-voce-estuda` — ângulo DIFERENCIAÇÃO.
 *
 * A mais conceitual das quatro. O argumento não é "o Sapiens é melhor", é que
 * a conta que todo mundo faz depois de um simulado ("errei 4") para no lugar
 * onde o estudo deveria começar. A comparação existe para mostrar que os dois
 * lados olham o MESMO simulado — o que muda é até onde a leitura vai.
 *
 * ---------------------------------------------------------------------------
 * A COMPARAÇÃO NÃO CITA NINGUÉM, E OS NÚMEROS SÃO DO EXEMPLO
 * ---------------------------------------------------------------------------
 *
 * "Método tradicional" é o hábito, não um concorrente: comparar-se a um
 * cursinho nomeado seria afirmar coisas sobre o produto de outra pessoa que
 * esta página não tem como sustentar. E "4 erros → 3 padrões" é a aritmética
 * do exemplo desenhado ao lado, não uma estatística de uso — nenhum número
 * desta página descreve alunos reais.
 *
 * O bloco da comparação mora neste arquivo e não em `components/ads/` porque
 * uma peça usada por uma página só é composição, não sistema; promovê-la a
 * componente compartilhado convidaria as outras três a repetir o mesmo
 * argumento, que é exatamente o que quatro variantes não devem fazer.
 */
const CADEIA = ["4 erros", "3 padrões", "habilidades específicas", "próxima ação de estudo"];

export default function AdsComoVoceEstuda() {
  return (
    <AdsLandingLayout variante="como-voce-estuda" ctaLabel="Ver meu diagnóstico">
      <Hero
        olho="Depois do simulado"
        titulo="Você sabe quanto acertou. Mas sabe por que errou?"
        subtexto="O Sapiens transforma seus erros em um mapa do que você precisa estudar."
        cta="Ver meu diagnóstico"
        notaDoCta="Gratuito para começar. Criar conta leva menos de um minuto."
      >
        <Comparacao />
      </Hero>

      <div className="mx-auto max-w-2xl">
        <ErrorAnalysisPreview titulo="Como um erro vira estudo" />
      </div>

      <section className="mx-auto mt-12 max-w-xl text-center">
        <h2 className="titulo-tela">A correção termina onde o estudo deveria começar.</h2>
        <p className="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-white/60">
          Contar acertos fecha o simulado. Ler os erros abre a próxima semana.
        </p>
        <CTA posicao="fim" className="mt-8">Ver meu diagnóstico</CTA>
      </section>
    </AdsLandingLayout>
  );
}

/**
 * Os dois olhares sobre o mesmo simulado.
 *
 * O lado "tradicional" é deliberadamente pobre de desenho — uma linha, um
 * número, e o vazio embaixo. O contraste não é de cor nem de moldura: é de
 * quanta informação cabe em cada leitura. Um card cheio ao lado de outro card
 * cheio mediria estilo; um card com uma frase ao lado de uma cadeia de quatro
 * elos mede o que a página está afirmando.
 */
function Comparacao() {
  return (
    <div className="grid gap-3" data-testid="ads-comparacao">
      <div className="superficie rounded-3xl p-5">
        <div className="secao-olho text-white/40">Método tradicional</div>
        <p className="mt-3 text-[17px] font-bold text-white/70">“Errei 4 questões.”</p>
        <p className="mt-2 text-[13px] leading-relaxed text-white/35">E o estudo de amanhã continua o mesmo.</p>
      </div>

      <div className="card-sapiens rounded-3xl p-5">
        <div className="secao-olho">Com o Sapiens</div>
        {/* A cadeia quebra em duas linhas no celular sem virar uma palavra por
            linha: `flex-wrap` com itens `shrink-0` é seguro aqui porque nenhum
            elo é `flex-1` — ver a armadilha do texto espremido em
            `ux/mobile.md`. */}
        <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-2">
          {CADEIA.map((elo, i) => (
            <span key={elo} className="flex shrink-0 items-center gap-2">
              <span className="chip">{elo}</span>
              {i < CADEIA.length - 1 && (
                <ArrowRight className="h-3.5 w-3.5 text-[#7FD8FF]/50" aria-hidden="true" />
              )}
            </span>
          ))}
        </div>
        <p className="mt-4 text-[13px] leading-relaxed text-white/50">
          Os números acima são do exemplo mostrado nesta página.
        </p>
      </div>
    </div>
  );
}
