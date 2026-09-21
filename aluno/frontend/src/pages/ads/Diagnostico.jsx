import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CadeiaDoErro from "../../components/ads/CadeiaDoErro";
import ComoFunciona from "../../components/ads/ComoFunciona";
import CtaFinal from "../../components/ads/CtaFinal";
import DemoAnaliseDoErro from "../../components/ads/DemoAnaliseDoErro";

/**
 * `/ads/diagnostico` — ângulo CURIOSIDADE.
 *
 * A pergunta do herói é uma que a pessoa não sabe responder, e é isso que faz
 * o anúncio funcionar: ela não está sendo convencida de nada, está sendo
 * confrontada com uma lacuna que já existia. A página inteira é a
 * demonstração de que o Sapiens responde aquela pergunta — não uma lista do
 * que ele faz.
 *
 * A demo roda em laço e é a coisa mais importante da primeira dobra: em cinco
 * segundos ela mostra uma questão ser marcada errada, ser ANALISADA, e virar
 * uma habilidade com um próximo passo. Quem não ler uma linha de texto desta
 * página entendeu o produto.
 */
export default function AdsDiagnostico() {
  return (
    <AdsLandingLayout variante="diagnostico" ctaLabel="Fazer diagnóstico grátis">
      <Hero
        olho="Diagnóstico gratuito"
        titulo="Você sabe por que está errando no ENEM?"
        subtexto="O Sapiens analisa seus erros e identifica o que está por trás deles."
        cta="Fazer diagnóstico grátis"
        notaDoCta={<NotaDeEntrada />}
      >
        <DemoAnaliseDoErro />
      </Hero>

      <div className="space-y-16 md:space-y-20">
        <CadeiaDoErro />
        <ComoFunciona />
        <CtaFinal cta="Fazer diagnóstico grátis" nota={<NotaDeEntrada />} />
      </div>
    </AdsLandingLayout>
  );
}

/**
 * A linha sob o botão.
 *
 * A primeira parte é a promessa; a segunda é o que vem antes dela na prática.
 * O Sapiens **não tem diagnóstico sem conta** — responder questão grava
 * evento no perfil do aluno, e não existe perfil anônimo. Esconder isso
 * compraria o clique e perderia a pessoa na tela seguinte, que é o pior lugar
 * possível para perdê-la: depois de a mídia já ter sido paga.
 */
function NotaDeEntrada() {
  return (
    <>
      {/* `tracking` curto e 10px: a 390px a versão anterior quebrava em duas
          linhas e a nota inteira media 63px. */}
      <span className="font-mono-alt text-[10px] uppercase tracking-[0.06em] text-white/55">
        10 questões • grátis • resultado personalizado
      </span>
      <br />
      <span className="text-[11px]">Criar conta leva menos de um minuto e não pede cartão.</span>
    </>
  );
}
