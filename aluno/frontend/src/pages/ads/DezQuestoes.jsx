import { useCallback } from "react";
import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CadeiaDoErro from "../../components/ads/CadeiaDoErro";
import ComoFunciona from "../../components/ads/ComoFunciona";
import CtaFinal from "../../components/ads/CtaFinal";
import DemoQuestao from "../../components/ads/DemoQuestao";
import { demoInteragida } from "../../lib/rastreio";

/**
 * `/ads/10-questoes` — ângulo DESAFIO.
 *
 * A única das quatro em que o visitante RESPONDE alguma coisa. As outras três
 * mostram o produto; esta deixa a pessoa ter tido uma pequena experiência
 * dele — e é o que o anúncio prometeu: se o criativo diz "comece o desafio" e
 * a landing só tem um botão de cadastro, o anúncio mentiu na primeira tela.
 *
 * A questão é local e descartável: nada de API, de Gemini, de Sparks, de
 * Firestore, de resposta gravada. Ver a nota longa em
 * `components/ads/DemoQuestao.jsx` — cada um desses "não" é deliberado.
 *
 * O CTA muda de verbo depois da interação ("Continuar com meu diagnóstico"
 * em vez de "Começar"), porque quem respondeu já começou: convidar a começar
 * de novo apaga o que a pessoa acabou de fazer.
 */
export default function AdsDezQuestoes() {
  const aoInteragir = useCallback((letra) => {
    demoInteragida("10-questoes", letra);
  }, []);

  return (
    <AdsLandingLayout variante="10-questoes" ctaLabel="Continuar com meu diagnóstico">
      <Hero
        olho="Uma rodada de 10"
        titulo="10 questões podem revelar onde você está perdendo pontos."
        subtexto="Resolva algumas questões e veja o que seus erros dizem sobre seu estudo."
        cta="Começar diagnóstico"
        notaDoCta="Grátis. Criar conta leva menos de um minuto e não pede cartão."
      >
        <DemoQuestao aoInteragir={aoInteragir} />
      </Hero>

      <div className="space-y-16 md:space-y-20">
        <CadeiaDoErro
          titulo="Uma rodada fecha com leitura, não com nota."
          corpo="Quantas você acertou, o que mudou desde a rodada anterior e quais padrões apareceram nos seus erros."
        />
        <ComoFunciona />
        <CtaFinal
          titulo="Descubra o que seus erros estão tentando mostrar."
          cta="Continuar com meu diagnóstico"
        />
      </div>
    </AdsLandingLayout>
  );
}
