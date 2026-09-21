import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CadeiaDoErro from "../../components/ads/CadeiaDoErro";
import ComoFunciona from "../../components/ads/ComoFunciona";
import CtaFinal from "../../components/ads/CtaFinal";
import DemoDecomposicao from "../../components/ads/DemoDecomposicao";

/**
 * `/ads/como-voce-estuda` — ângulo DIFERENCIAÇÃO.
 *
 * A mais conceitual das quatro. O argumento não é "o Sapiens é melhor": é que
 * a conta que todo mundo faz depois de um simulado ("acertei 72%") para
 * exatamente no lugar onde o estudo deveria começar.
 *
 * A demo faz o número virar do avesso — 72% de acerto vira 28% de erro, o
 * erro vira quatro naturezas, as naturezas viram padrões, os padrões viram
 * habilidades, e as habilidades viram a próxima semana. É o MESMO simulado
 * o tempo todo; o que muda é para qual metade se olha.
 *
 * Nenhum número desta página descreve quem está lendo — ver a nota em
 * `components/ads/DemoDecomposicao.jsx`.
 */
export default function AdsComoVoceEstuda() {
  return (
    <AdsLandingLayout variante="como-voce-estuda" ctaLabel="Descobrir meu perfil">
      <Hero
        olho="Depois do simulado"
        titulo="Você sabe quanto acerta. Mas sabe por que erra?"
        subtexto="O Sapiens transforma seus erros em um mapa do que você precisa estudar."
        cta="Descobrir meu perfil"
        notaDoCta="Grátis para começar. Criar conta leva menos de um minuto."
      >
        <DemoDecomposicao />
      </Hero>

      <div className="space-y-16 md:space-y-20">
        <CadeiaDoErro
          titulo="A correção termina onde o estudo deveria começar."
          corpo="Contar acertos fecha o simulado. Ler os erros abre a próxima semana."
        />
        <ComoFunciona />
        <CtaFinal
          titulo="Descubra o que seus erros estão tentando mostrar."
          cta="Descobrir meu perfil"
        />
      </div>
    </AdsLandingLayout>
  );
}
