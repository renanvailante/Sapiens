import AdsLandingLayout from "../../components/ads/AdsLandingLayout";
import Hero from "../../components/ads/Hero";
import CadeiaDoErro from "../../components/ads/CadeiaDoErro";
import ComoFunciona from "../../components/ads/ComoFunciona";
import CtaFinal from "../../components/ads/CtaFinal";
import DemoRetaFinal from "../../components/ads/DemoRetaFinal";
import { proximaProva, tempoRestante } from "../../lib/enem";

/**
 * `/ads/reta-final` — ângulo URGÊNCIA.
 *
 * A quinta variante, e a única cujo gancho é o CALENDÁRIO em vez do erro. As
 * outras quatro argumentam sobre o mecanismo do produto ("por que você erra");
 * esta argumenta sobre o tempo que sobrou e o que fazer com ele — e mostra a
 * outra metade do Sapiens, `prioridade_enem`, que nenhuma landing usava.
 *
 * ---------------------------------------------------------------------------
 * POR QUE ESTE ÂNGULO NÃO PRECISA AFIRMAR NADA SOBRE QUEM LÊ
 * ---------------------------------------------------------------------------
 *
 * É a vantagem estrutural dele, e vale registrar. "Faltam 45 dias para o
 * ENEM" é um fato do calendário, verdadeiro para todo mundo que vê. "Quando a
 * prova se aproxima, fica a dúvida" atribui a dúvida à SITUAÇÃO, não à
 * pessoa. Nenhuma das duas cruza a política de atributos pessoais do Meta,
 * que é o que derruba anúncio de educação — e nenhuma das duas precisa fingir
 * saber algo de quem acabou de chegar.
 *
 * ---------------------------------------------------------------------------
 * O NÚMERO É SEMPRE MEDIDO
 * ---------------------------------------------------------------------------
 *
 * A manchete lê `lib/enem`, a mesma fonte da contagem que já roda em cinco
 * telas. No criativo em vídeo o número é assado no arquivo e tem prazo de
 * validade; aqui ele nunca fica errado, nem no dia seguinte, nem no mês que
 * vem. Passados os dois domingos, `proximaProva` devolve `null` e a página
 * troca de manchete em vez de mostrar contagem negativa.
 */
export default function AdsRetaFinal() {
  const prova = proximaProva();
  const dias = prova ? tempoRestante(prova.inicio).dias : null;

  return (
    <AdsLandingLayout variante="reta-final" ctaLabel="Descobrir agora">
      <Hero
        olho="Reta final"
        titulo={
          dias === null ? (
            <>O ENEM passou. O próximo <em className="not-italic text-[#9BE8FF]">começa agora</em>.</>
          ) : (
            <>Faltam <span className="text-[#9BE8FF]">{dias}</span> dias para o ENEM.</>
          )
        }
        subtexto="Quando a prova se aproxima, a dúvida deixa de ser se você vai estudar. É o que ainda precisa melhorar."
        cta="Descobrir agora"
        notaDoCta="Grátis. Criar conta leva menos de um minuto e não pede cartão."
      >
        <DemoRetaFinal />
      </Hero>

      <div className="space-y-16 md:space-y-20">
        <CadeiaDoErro
          titulo="O plano não sai do calendário. Sai do que você responde."
          corpo="Dias iguais viram semanas diferentes quando o Sapiens sabe onde a sua próxima hora rende mais."
        />
        <ComoFunciona />
        <CtaFinal
          titulo="Descubra o que ainda dá para melhorar."
          cta="Descobrir agora"
        />
      </div>
    </AdsLandingLayout>
  );
}
