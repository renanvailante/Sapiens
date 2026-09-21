import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CTA from "../../components/ads/CTA";
import FeatureFlow from "../../components/ads/FeatureFlow";
import ErrorAnalysisPreview from "../../components/ads/ErrorAnalysisPreview";

/**
 * `/ads/mesmo-erro` — ângulo DOR / REPETIÇÃO.
 *
 * O herói nomeia uma experiência que a pessoa reconhece sem precisar acreditar
 * em nada: estudar, fazer questão e continuar errando as mesmas coisas. É o
 * vilão da marca ("estudar no escuro") dito na linguagem de quem está dentro
 * dele, e não na de quem vende a saída.
 *
 * A esteira ERRO → ANÁLISE → HABILIDADE → PRÓXIMO ESTUDO é o argumento
 * inteiro: a repetição não se quebra fazendo mais questões, se quebra
 * mudando o que se estuda depois delas.
 */
const PASSOS = [
  { rotulo: "Erro", corpo: "Você marca a alternativa errada numa questão." },
  { rotulo: "Análise", corpo: "O Sapiens compara esse erro com os anteriores e procura o que se repete." },
  { rotulo: "Habilidade", corpo: "O padrão aponta uma habilidade específica, não uma matéria inteira." },
  { rotulo: "Próximo estudo", corpo: "Ela entra no que você vai estudar em seguida." },
];

export default function AdsMesmoErro() {
  return (
    <AdsLandingLayout variante="mesmo-erro" ctaLabel="Descobrir meus padrões de erro">
      <Hero
        olho="Para quem já estuda e não sai do lugar"
        titulo="Você estuda, faz questões… e continua errando as mesmas coisas?"
        subtexto="O Sapiens analisa seus erros para identificar o que está por trás deles e orientar o que estudar depois."
        cta="Descobrir meus padrões de erro"
        notaDoCta="Gratuito para começar. Criar conta leva menos de um minuto."
      >
        <ErrorAnalysisPreview titulo="Um erro, lido por dentro" />
      </Hero>

      <div className="mx-auto max-w-3xl">
        <FeatureFlow
          passos={PASSOS}
          nota="Acertar ou errar uma questão é só o começo. O importante é entender o motivo."
        />
      </div>

      <section className="mx-auto mt-12 max-w-xl text-center">
        <h2 className="titulo-tela">Errar de novo não é falta de esforço.</h2>
        <p className="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-white/60">
          É sinal de que a causa continua intacta. Enquanto ela não aparece, a
          próxima lista de exercícios repete o mesmo caminho.
        </p>
        <CTA posicao="fim" className="mt-8">Descobrir meus padrões de erro</CTA>
      </section>
    </AdsLandingLayout>
  );
}
