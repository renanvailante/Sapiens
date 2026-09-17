import { Link } from "react-router-dom";
import {
  Medal, Radio, ArrowRight, Target, Route, Brain, MessageCircleMore, Users, Clock,
} from "lucide-react";
import Nav from "../components/Nav";
import MentorUSP from "../components/MentorUSP";
import ListaDeEsperaMentoria from "../components/ListaDeEsperaMentoria";
import ContagemEnem from "../components/ContagemEnem";
import { useDeclararContextoMentis } from "../lib/mentisContexto";

/**
 * `/mentoria` — a lista de espera da mentoria com o 1º colocado de Medicina
 * da USP.
 *
 * Substituiu `/aulas` ("aula particular com alunos de Medicina da USP") em
 * 2026-09-15. Três coisas mudaram, e a página inteira é consequência delas:
 *
 * 1. **Não são vários professores: é UMA pessoa**, e é a pessoa que ficou em
 *    primeiro lugar no vestibular mais disputado do país. Por isso o rosto
 *    dela abre a página, em tamanho grande — é o maior ativo do produto, e
 *    esconder o ativo atrás de um formulário seria jogá-lo fora.
 * 2. **Não se agenda: entra-se numa fila.** Uma pessoa não atende todo mundo,
 *    e prometer horário seria mentir. A tela promete posição e contato.
 * 3. **A escassez é real e por isso pode ser dita.** Não é contador falso de
 *    "restam 3 vagas": é uma agenda de uma pessoa só.
 */

const O_QUE_E = [
  {
    icone: Route,
    titulo: "A rotina que deu certo, aplicada à sua",
    texto: "Não é conselho genérico de vídeo. É a sua semana, olhada por quem montou uma que funcionou até o fim.",
  },
  {
    icone: Target,
    titulo: "O que cortar — e o que você está estudando à toa",
    texto: "A parte mais cara do vestibular é o tempo gasto no lugar errado. É a primeira coisa que a mentoria ataca.",
  },
  {
    icone: Brain,
    titulo: "Seu erro lido por quem já errou igual",
    texto: "O Sapiens mostra o padrão do seu erro. A mentoria traduz esse padrão em o que fazer na segunda de manhã.",
  },
  {
    icone: MessageCircleMore,
    titulo: "Conversa de verdade, não aula gravada",
    texto: "Um a um, pelo WhatsApp e em chamada. Você pergunta o que não perguntaria numa sala com 200 pessoas.",
  },
];

export default function Mentoria() {
  useDeclararContextoMentis(
    "Na página da mentoria, vendo a lista de espera da mentoria com o 1º colocado de Medicina da USP.",
  );

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-6 py-8 md:px-10 md:py-10">
        <div className="mb-6">
          <ContagemEnem comCta={false} testid="mentoria-contagem-enem" />
        </div>

        {/* --------------------------------------------------------------
            O ROSTO. Primeira coisa da página, em tamanho grande.
            -------------------------------------------------------------- */}
        <section
          className="mapa-vitrine relative overflow-hidden rounded-3xl p-6 md:p-10"
          data-testid="mentoria-hero"
        >
          <div className="relative grid gap-8 md:grid-cols-[auto_1fr] md:items-center">
            <div className="flex justify-center md:justify-start">
              <MentorUSP tamanho="g" testid="mentoria-foto" />
            </div>

            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-amber-300/40 bg-amber-400/10 px-3 py-1.5 font-mono-alt text-[10px] font-bold uppercase tracking-[0.2em] text-amber-200">
                <Medal className="h-3 w-3" /> Primeiro lugar · Medicina USP
              </span>

              <h1 className="mt-5 font-display text-4xl font-extrabold leading-[1.02] tracking-tighter text-white md:text-5xl">
                Mentoria com quem passou em{" "}
                <span className="text-[#7FD8FF]">1º lugar em Medicina na USP</span>.
              </h1>

              <p className="mt-4 max-w-2xl leading-relaxed text-white/65">
                Não é um professor contratado para dar aula. É a pessoa que ficou em primeiro
                lugar no vestibular mais disputado do Brasil, sentando com você para olhar a
                sua rotina, o seu erro e o seu plano — um a um.
              </p>

              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/45">
                Uma pessoa não atende todo mundo. Por isso aqui não tem agenda aberta: tem
                <strong className="font-semibold text-white/70"> lista de espera</strong>, e a
                ordem da conversa é a ordem de chegada.
              </p>

              <div className="mt-6 flex flex-wrap items-center gap-3">
                <a
                  href="#lista"
                  className="pill btn-calor inline-flex items-center gap-2 rounded-full px-7 py-4 text-sm"
                  data-testid="mentoria-cta-topo"
                >
                  <Users className="h-4 w-4" /> Entrar na lista de espera
                </a>
                <span className="inline-flex items-center gap-1.5 text-xs text-white/40">
                  <Clock className="h-3.5 w-3.5" /> de graça, e sem compromisso
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* --------------------------------------------------------------
            O QUE É A MENTORIA
            -------------------------------------------------------------- */}
        <section className="mt-10" data-testid="mentoria-o-que-e">
          <h2 className="font-display text-2xl font-extrabold tracking-tighter text-white md:text-3xl">
            O que acontece numa mentoria
          </h2>
          <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
            {O_QUE_E.map((x) => (
              <div key={x.titulo} className="macio border border-white/10 bg-white/[0.035] p-4">
                <div className="flex items-start gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-[#7FD8FF]">
                    <x.icone className="h-4 w-4" strokeWidth={1.8} />
                  </span>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-white">{x.titulo}</div>
                    <div className="mt-1 text-xs leading-relaxed text-white/45">{x.texto}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* --------------------------------------------------------------
            A LISTA
            -------------------------------------------------------------- */}
        <section id="lista" className="mt-10 scroll-mt-24" data-testid="mentoria-lista">
          <div className="macio border border-[#4FD9FF]/25 bg-[#4FD9FF]/[0.05] p-6 md:p-8">
            <div className="mb-6 flex items-center gap-4">
              <MentorUSP tamanho="p" comSelo={false} testid="mentoria-foto-form" />
              <div className="min-w-0">
                <h2 className="font-display text-2xl font-extrabold tracking-tighter text-white">
                  Entrar na lista de espera
                </h2>
                <p className="text-sm text-white/50">
                  A gente chama pelo WhatsApp, na ordem de chegada.
                </p>
              </div>
            </div>
            <ListaDeEsperaMentoria />
          </div>
        </section>

        {/* --------------------------------------------------------------
            A PONTE PARA A LIVE — a mesma pessoa, toda quinta
            -------------------------------------------------------------- */}
        <Link
          to="/aula-ao-vivo"
          className="lift mt-8 flex flex-wrap items-center gap-4 rounded-2xl border border-rose-400/25 bg-gradient-to-r from-rose-500/[0.12] via-amber-400/[0.07] to-transparent p-5 hover:border-rose-400/50"
          data-testid="mentoria-para-live"
        >
          <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-rose-400/30 bg-rose-500/15 text-rose-200">
            <Radio className="h-5 w-5" strokeWidth={1.8} />
            <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
            </span>
          </span>
          <div className="min-w-0 flex-1">
            <div className="font-display text-base font-bold tracking-tight text-white">
              Não quer esperar? Ele dá aula ao vivo toda quinta.
            </div>
            <div className="text-xs text-white/45">
              Mesma pessoa, 60 minutos, com perguntas abertas no fim — por 200 Sparks.
            </div>
          </div>
          <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
        </Link>
      </div>
    </div>
  );
}
