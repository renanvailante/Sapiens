import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CadeiaDoErro from "../../components/ads/CadeiaDoErro";
import ComoFunciona from "../../components/ads/ComoFunciona";
import CtaFinal from "../../components/ads/CtaFinal";
import DemoEcossistema from "../../components/ads/DemoEcossistema";

/**
 * `/ads/sem-mensalidade` — ângulo CUSTO.
 *
 * O sexto, e o único que argumenta sobre dinheiro. Os outros cinco falam do
 * mecanismo (por que você erra) ou do tempo (quantos dias faltam).
 *
 * ---------------------------------------------------------------------------
 * A REGRA QUE ESTA PÁGINA NÃO PODE QUEBRAR
 * ---------------------------------------------------------------------------
 *
 * **O Sapiens é freemium, não gratuito.** Responder questão, ler o
 * diagnóstico e montar o cronograma não custam nada; curso, e-book, redação
 * corrigida e a Mentis custam Sparks. Um aluno novo começa com 100, que não
 * pagam nem um curso.
 *
 * Por isso a página inteira diz "o diagnóstico é de graça" e "sem
 * mensalidade", nunca "é gratuito". A diferença não é jurídica, é de
 * conversão: quem chega de um anúncio que promete tudo de graça e bate num
 * paywall na terceira tela não volta — e o paywall aparece depois de a mídia
 * já ter sido paga, que é o pior lugar possível para perder alguém.
 *
 * > **Nenhum preço do Sapiens é escrito aqui à mão.** A página fala de modelo
 * > ("sem mensalidade", "paga só se usar"), nunca de valor. Preço do produto
 * > mora no backend e é citado só depois de conferir a constante — ver
 * > `produto/economia-de-sparks.md`.
 *
 * O R$ 6.000 é uma afirmação sobre o preço de TERCEIROS, feita pelo dono com
 * fonte própria, e por decisão dele a fonte não aparece na página. Se o Meta
 * questionar o anúncio, é essa fonte que precisa existir.
 */
export default function AdsSemMensalidade() {
  return (
    <AdsLandingLayout variante="sem-mensalidade" ctaLabel="Fazer meu diagnóstico">
      <Hero
        olho="Sem mensalidade"
        titulo={<>Preparação completa para o ENEM, <em className="not-italic text-[#9BE8FF]">sem mensalidade</em>.</>}
        subtexto="Existem plataformas que custam até R$ 6.000. No Sapiens você paga só pelo que usar — e o diagnóstico é de graça."
        cta="Fazer meu diagnóstico"
        notaDoCta="Questões, diagnóstico e cronograma: de graça. Conta em 1 minuto, sem cartão."
      >
        <DemoEcossistema />
      </Hero>

      <div className="space-y-16 md:space-y-20">
        <CadeiaDoErro
          titulo="Preço alto não é o que faz alguém estudar melhor."
          corpo="O que muda o estudo é saber o que fazer depois de errar. É nisso que o Sapiens gasta o esforço dele."
        />
        <ComoFunciona />
        <CtaFinal
          titulo="Comece pelo diagnóstico. Ele é de graça."
          cta="Fazer meu diagnóstico"
        />
      </div>
    </AdsLandingLayout>
  );
}
