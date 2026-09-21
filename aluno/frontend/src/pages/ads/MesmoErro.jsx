import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CadeiaDoErro from "../../components/ads/CadeiaDoErro";
import ComoFunciona from "../../components/ads/ComoFunciona";
import CtaFinal from "../../components/ads/CtaFinal";
import DemoPadraoComum from "../../components/ads/DemoPadraoComum";

/**
 * `/ads/mesmo-erro` — ângulo DOR / REPETIÇÃO.
 *
 * O herói nomeia uma experiência que a pessoa reconhece sem precisar
 * acreditar em nada: estudar, fazer questão e continuar errando as mesmas
 * coisas. É o vilão da marca ("estudar no escuro") dito na linguagem de quem
 * está dentro dele, e não na de quem vende a saída.
 *
 * É a mais forte visualmente das quatro, e a força está num movimento só: as
 * três linhas convergindo. A dor deste ângulo é feita de erros que a pessoa
 * arquiva como azar separado; o produto existe porque eles não são separados.
 * Explicar isso em texto seria pedir que ela acredite na frase — o desenho
 * faz a convergência acontecer na frente dela.
 */
export default function AdsMesmoErro() {
  return (
    <AdsLandingLayout variante="mesmo-erro" ctaLabel="Descobrir meus padrões">
      <Hero
        olho="Para quem já estuda e não sai do lugar"
        titulo="Você continua errando a mesma coisa?"
        subtexto="Talvez o problema não seja falta de estudo. Pode ser o padrão por trás dos seus erros."
        cta="Descobrir meus padrões"
        notaDoCta="Grátis para começar. Criar conta leva menos de um minuto."
      >
        <DemoPadraoComum />
      </Hero>

      <div className="space-y-16 md:space-y-20">
        <CadeiaDoErro
          titulo="Errar de novo não é falta de esforço."
          corpo="É sinal de que a causa continua intacta. Enquanto ela não aparece, a próxima lista de exercícios repete o mesmo caminho."
        />
        <ComoFunciona />
        <CtaFinal
          titulo="Descubra o que seus erros estão tentando mostrar."
          cta="Descobrir meus padrões"
        />
      </div>
    </AdsLandingLayout>
  );
}
