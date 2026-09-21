import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CTA from "../../components/ads/CTA";
import QuestionProgress from "../../components/ads/QuestionProgress";

/**
 * `/ads/10-questoes` — ângulo DESAFIO.
 *
 * Esta é a página mais curta das quatro, e isso é o desenho, não pressa: o
 * argumento dela é **baixa fricção**, e uma página longa desmente o próprio
 * argumento. Quem chega por este criativo já aceitou a proposta no anúncio;
 * o trabalho da landing é não colocar nada entre ela e o botão.
 *
 * O "10" é o número real do produto — `RODADA_TAMANHO = 10`, a rodada que
 * fecha com devolutiva (acertos, evolução e padrões de erro, sem IA e sem
 * custo). Ver a nota em `components/ads/QuestionProgress.jsx`.
 */
export default function AdsDezQuestoes() {
  return (
    <AdsLandingLayout variante="10-questoes" ctaLabel="Começar desafio">
      <Hero
        olho="Uma rodada"
        titulo="10 questões. Descubra onde você realmente está perdendo pontos."
        subtexto="Faça um diagnóstico rápido e veja quais habilidades precisam de mais atenção."
        cta="Começar desafio"
        notaDoCta="Gratuito. Criar conta leva menos de um minuto e não pede cartão."
      >
        <QuestionProgress />
      </Hero>

      <section className="mx-auto max-w-xl text-center">
        <h2 className="titulo-tela">No fim da rodada, a leitura.</h2>
        <p className="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-white/60">
          Quantas você acertou, o que mudou em relação à rodada anterior e quais
          padrões apareceram nos seus erros. Seu resultado mostra onde concentrar
          seus estudos.
        </p>
        <CTA posicao="fim" className="mt-8">Começar desafio</CTA>
      </section>
    </AdsLandingLayout>
  );
}
