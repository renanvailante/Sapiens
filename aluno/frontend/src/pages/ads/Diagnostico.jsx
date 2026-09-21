import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CTA from "../../components/ads/CTA";
import DiagnosticPreview from "../../components/ads/DiagnosticPreview";
import ErrorAnalysisPreview from "../../components/ads/ErrorAnalysisPreview";

/**
 * `/ads/diagnostico` — ângulo CURIOSIDADE.
 *
 * A pergunta do herói ("você sabe POR QUE está errando?") é uma pergunta que a
 * pessoa não sabe responder, e é isso que faz o anúncio funcionar: ela não
 * está sendo convencida de nada, está sendo confrontada com uma lacuna que
 * já existia. A página inteira é a demonstração de que o Sapiens responde
 * aquela pergunta — não uma lista do que ele faz.
 *
 * Composição: herói com a questão de exemplo ao lado → a leitura do erro em
 * três degraus → o convite de novo. Nada mais. Não há seção sobre a
 * plataforma, sobre o mentor, sobre preço: quem chega aqui não está
 * comparando produtos, está com uma pergunta na cabeça.
 */
export default function AdsDiagnostico() {
  return (
    <AdsLandingLayout variante="diagnostico" ctaLabel="Fazer diagnóstico gratuito">
      <Hero
        olho="Diagnóstico gratuito"
        titulo="Você sabe por que está errando no ENEM?"
        subtexto="Faça um diagnóstico gratuito e descubra quais habilidades estão por trás dos seus erros."
        cta="Fazer diagnóstico gratuito"
        notaDoCta={<NotaDeEntrada />}
      >
        <DiagnosticPreview />
      </Hero>

      <div className="mx-auto max-w-2xl">
        <ErrorAnalysisPreview />
      </div>

      <section className="mx-auto mt-12 max-w-xl text-center">
        <h2 className="titulo-tela">A nota diz onde você está. O erro diz por quê.</h2>
        <p className="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-white/60">
          O Sapiens olha cada resposta sua e monta a partir dela o que estudar
          em seguida — a habilidade, não a questão.
        </p>
        <CTA posicao="fim" className="mt-8" nota={<NotaDeEntrada />}>
          Fazer diagnóstico gratuito
        </CTA>
      </section>
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
 * possível para perdê-la: depois de pagar a mídia.
 */
function NotaDeEntrada() {
  return (
    <>
      <span className="font-mono-alt text-[11px] uppercase tracking-[0.14em] text-white/55">
        10 questões • gratuito • resultado personalizado
      </span>
      <br />
      <span className="mt-1 inline-block">Criar conta leva menos de um minuto e não pede cartão.</span>
    </>
  );
}
