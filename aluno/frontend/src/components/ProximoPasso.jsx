import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Compass, PlayCircle, RotateCw, CalendarClock, Target, Flame,
} from "lucide-react";
import TrilhaDeMissoes from "./TrilhaDeMissoes";
import { missaoAtual } from "../lib/trilha";
import { diaLocal } from "../lib/atividade";

/**
 * O PRÓXIMO PASSO — a primeira coisa do Painel, e a única que responde a
 * pergunta que o aluno realmente tem quando abre o produto: *e agora?*
 *
 * O Painel de 15/09 abria com a vitrine do Mapa, que é a peça que melhor
 * MOSTRA o que o Sapiens é. O problema é que mostrar o produto e dizer o que
 * fazer não são a mesma coisa: quem abre o app às sete da noite, com uma hora
 * livre, não precisa ser convencido de que o mapa existe — precisa saber onde
 * pisar. Abaixo da vitrine havia dez destinos concorrentes e nenhuma ordem
 * entre eles, e escolher entre dez coisas é o jeito mais confiável de não
 * fazer nenhuma.
 *
 * Então a vitrine continua — a trilha está aqui, à direita, e os números do
 * mapa embaixo — mas quem fala primeiro é a AÇÃO.
 *
 * ---------------------------------------------------------------------------
 * COMO O PASSO É ESCOLHIDO
 * ---------------------------------------------------------------------------
 *
 * Uma escada de prioridade, de cima para baixo, e a primeira que tiver dado
 * real vence. Nenhum degrau inventa nada: todos leem o que o Painel já
 * carregou, então isto custa zero requisição.
 *
 *   1. **Revisão vencida.** É a única coisa do produto com prazo por baixo —
 *      a fila de repetição espaçada marca uma data, e revisar depois dela vale
 *      menos. Prazo ganha de preferência.
 *   2. **O bloco de hoje no cronograma.** O aluno mesmo marcou a hora. Nada
 *      que o Sapiens escolha por ele ganha do que ele escolheu.
 *   3. **A missão atual da trilha.** O nó em que ele está — a MESMA função que
 *      desenha o halo na trilha ao lado (`lib/trilha.js`), para as duas peças
 *      nunca apontarem para lugares diferentes na mesma dobra da tela.
 *   4. **Praticar.** Quem ainda não tem medida nenhuma não tem lacuna
 *      conhecida; o caminho é responder questão até haver o que medir.
 *
 * A OFENSIVA não é um degrau: ela é o MOTIVO, e entra como uma linha de
 * urgência no passo que tiver vencido. "Você está no dia 12 e ainda não
 * estudou hoje" muda o peso de abrir o app; trocar o destino por causa disso
 * mandaria o aluno a um lugar pior só para não perder a sequência.
 */

const TOTAL_HABILIDADES = 56;

export function escolherPasso({ revisoes, cronograma, habilidades }) {
  const vencidas = revisoes?.resumo?.questoes || 0;
  if (vencidas > 0) {
    return {
      chave: "revisao",
      icone: RotateCw,
      olho: "Venceu hoje",
      titulo: vencidas === 1 ? "1 questão voltou para revisão" : `${vencidas} questões voltaram para revisão`,
      porque: "Revisar no dia em que vence é o que faz a memória durar. Depois disso, rende menos.",
      rota: "/revisoes",
      cta: "Revisar agora",
      testid: "passo-revisao",
    };
  }

  const hoje = cronograma?.dias?.find((d) => d.data === diaLocal());
  const bloco = (hoje?.blocos || []).find((b) => !b.concluido);
  if (bloco) {
    return {
      chave: `bloco-${bloco.id}`,
      icone: CalendarClock,
      olho: bloco.inicio && bloco.fim ? `Hoje, ${bloco.inicio}–${bloco.fim}` : "Hoje, no seu cronograma",
      titulo: bloco.titulo,
      porque: bloco.frente_nome
        ? `${bloco.frente_nome} — você mesmo marcou esta hora para isto.`
        : "Você mesmo marcou esta hora para isto.",
      rota: bloco.rota || "/cronograma",
      cta: "Começar",
      testid: "passo-cronograma",
    };
  }

  const missao = missaoAtual(habilidades);
  if (missao) {
    const tocada = missao.respondidas > 0;
    return {
      chave: `hab-${missao.hab_id}`,
      icone: Target,
      olho: tocada ? "Sua missão atual" : "Território novo",
      titulo: missao.nome,
      porque: tocada
        ? `Você acerta ${Math.round(missao.percentual ?? 0)}% aqui. É onde uma hora de estudo rende mais.`
        : "Ainda não há medida sua neste ponto. Algumas questões e o mapa se revela.",
      rota: `/treino?hab=${missao.hab_id}`,
      cta: tocada ? "Abrir a missão" : "Começar a missão",
      testid: "passo-missao",
    };
  }

  return {
    chave: "praticar",
    icone: PlayCircle,
    olho: "Comece por aqui",
    titulo: "Responda uma prova do ENEM",
    porque: "É a partir das suas respostas que o mapa, as missões e o seu perfil existem.",
    rota: "/exams",
    cta: "Praticar agora",
    testid: "passo-praticar",
  };
}

export default function ProximoPasso({
  habilidades = [],
  revisoes = null,
  cronograma = null,
  totalRespondidas = 0,
  ofensiva = 0,
  estudouHoje = true,
  testid = "proximo-passo",
}) {
  const passo = useMemo(
    () => escolherPasso({ revisoes, cronograma, habilidades }),
    [revisoes, cronograma, habilidades],
  );

  const pontosTocados = habilidades.filter((h) => h.respondidas > 0).length;
  const pontosDominados = habilidades.filter((h) => h.classificacao === "forte").length;
  const Icone = passo.icone;

  // A ofensiva em risco. Aparece só quando há sequência DE VERDADE a perder e
  // o dia ainda não está garantido — a mesma linha ética do painel de
  // engajamento: nunca um aviso construído sobre um número que não existe.
  const emRisco = ofensiva > 0 && !estudouHoje;

  return (
    <section
      className="mapa-vitrine relative overflow-hidden rounded-[26px] p-6 md:p-8"
      data-testid={testid}
      data-tour="dash-mapa"
    >
      <div className="relative grid gap-7 md:grid-cols-[1.4fr_1fr] md:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="secao-olho inline-flex items-center gap-1.5">
              <Icone className="h-3.5 w-3.5" /> {passo.olho}
            </span>
            {emRisco && (
              <span
                className="chip border-amber-300/30 bg-amber-400/12 py-1 text-[11px] text-amber-100"
                data-testid={`${testid}-risco`}
              >
                <Flame className="h-3 w-3 text-amber-300" />
                {ofensiva} {ofensiva === 1 ? "dia" : "dias"} em risco
              </span>
            )}
          </div>

          <h2 className="titulo-heroi mt-2.5" data-testid={`${testid}-titulo`}>
            {passo.titulo}
          </h2>
          <p className="mt-2.5 max-w-lg text-sm leading-relaxed text-white/60">{passo.porque}</p>

          <div className="mt-6 flex flex-wrap items-center gap-2.5">
            <Link
              to={passo.rota}
              className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-sm font-bold"
              data-testid={passo.testid}
            >
              {passo.cta} <ArrowRight className="h-4 w-4" />
            </Link>
            {/* O MAPA. Era um fantasma chamado "O mapa" — dois problemas num
                botão só. Fantasma, perdia para o passo aceso ao lado e o olho
                não parava nele; e "o mapa" não diz a que se refere para quem
                ainda não entrou nele uma vez.
                Agora tem contorno, peso e o nome inteiro da coisa. Continua
                abaixo do passo principal na hierarquia — o passo é a ação de
                hoje —, mas deixa de ser invisível. */}
            <Link
              to="/treino"
              className="pill btn-contorno inline-flex items-center gap-2 rounded-full px-5 py-3.5 text-sm font-bold"
              data-testid="dash-cta-mapa"
            >
              <Compass className="h-4 w-4" /> Mapa de treino
            </Link>
            <Link
              to="/exams"
              className="pill btn-vidro inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm"
              data-testid="dash-cta-provas"
              data-tour="dash-provas"
            >
              <PlayCircle className="h-4 w-4" /> Provas do ENEM
            </Link>
          </div>

          {/* Os números que provam o mapa, sem uma frase para explicá-los.
              Grade de três e não `flex-wrap`: a 390px os três não cabiam numa
              linha só e o terceiro caía sozinho embaixo, com um vão do
              tamanho de dois deles ao lado — o que lia como erro de layout,
              não como continuação. */}
          <div className="mt-7 grid grid-cols-3 gap-3">
            {[
              { n: pontosTocados, de: TOTAL_HABILIDADES, rotulo: "pontos explorados" },
              { n: pontosDominados, rotulo: "dominados" },
              { n: totalRespondidas, rotulo: "questões" },
            ].map((x) => (
              <div key={x.rotulo}>
                <div className="medida-n text-2xl">
                  {x.n}
                  {x.de != null && <span className="text-base text-white/30">/{x.de}</span>}
                </div>
                <div className="medida-rotulo">{x.rotulo}</div>
              </div>
            ))}
          </div>
        </div>

        {/* A trilha. O caminho de entrada no mapa — e a peça que faz o Painel
            PARECER o produto em vez de descrevê-lo. O nó com halo é o mesmo
            que o passo acima anuncia: os dois leem `lib/trilha.js`.

            Ela é um LINK, e essa é a correção principal de 17/09: a peça mais
            parecida com o produto na tela inteira era decoração. O aluno via
            a trilha, entendia que era o mapa, clicava — e não acontecia nada.
            Quem desenha um caminho e não deixa andar nele ensina que a tela
            não responde, e depois disso nem o botão ao lado é tentado.

            `group` + `aria-label`: o alvo é o painel inteiro, no mouse e no
            toque, e quem usa leitor de tela ouve para onde ele vai em vez de
            ouvir a lista de nós soltos. */}
        <Link
          to="/treino"
          aria-label="Abrir o mapa de treino"
          className="group block rounded-[26px] border border-white/25 bg-black/35 p-4 pb-6 transition hover:border-[#7FD8FF]/60 hover:bg-black/50"
          data-testid="dash-trilha-porta"
        >
          <div className="mb-3 text-center font-mono-alt text-[11px] uppercase tracking-[0.25em] text-white/70">
            Seu caminho
          </div>
          <TrilhaDeMissoes habilidades={habilidades} limite={4} testid="dash-trilha" />
          <div className="mt-5 flex items-center justify-center gap-1.5 text-sm font-bold text-[#7FD8FF]">
            Abrir o mapa de treino
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </div>
        </Link>
      </div>
    </section>
  );
}
