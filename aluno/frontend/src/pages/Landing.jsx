import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, Brain, Network, ChevronRight, Radio, Video, Clock, Medal, Users, Quote, Check, X, BookOpen, ShieldCheck } from "lucide-react";
import { useAuth } from "../lib/auth";
import Logo from "../components/Logo";
import BrandMark from "../components/BrandMark";
import Mentis from "../components/Mentis";
import MentorUSP from "../components/MentorUSP";
import VideoDoMentor from "../components/VideoDoMentor";
import { MENTOR } from "../lib/mentor";
import ContagemEnem from "../components/ContagemEnem";
import { OPERADOR } from "../lib/operador";
import { PROBLEMA, DOR_INTERNA, EMBASAMENTO, PLANO, APOSTAS, DEPOIMENTOS, FAQ } from "../lib/historia";

/**
 * A landing — a única tela que fala com quem ainda não é aluno.
 *
 * **Reescrita em 2026-09-17 na estrutura de Donald Miller** (*Building a
 * StoryBrand*), que passa a ser a espinha de toda a marca. A ordem das seções
 * NÃO é gosto de diagramação, é a história:
 *
 *   herói → problema → guia → plano → convite → fracasso evitado → sucesso
 *
 * O que isso trocou na prática: a landing antiga abria descrevendo o produto
 * ("padrões, não notas", "perfil cognitivo", "mapa de aprendizagem") — três
 * elogios ao Sapiens antes de uma única frase sobre a vida de quem lê. Quem
 * chega por um link de WhatsApp tem cinco segundos e não está procurando um
 * produto: está com medo de não passar. Agora o produto só aparece depois de
 * o problema estar dito, e aparece como PLANO, não como lista de recursos.
 *
 * Regra permanente desta tela: **o herói é o aluno, o Sapiens é o guia**. Se
 * uma seção nova elogiar a plataforma sem dizer o que muda para quem lê, ela
 * está no lugar errado. A copy mora em `lib/historia.js`.
 *
 * O degradê animado sobre "conhecimento" continua: ele é a promessa da marca.
 * Ver a nota longa do `.shimmer` no `index.css` — a rampa foi corrigida para
 * não comer a barriga das letras em corpo de display.
 */

const CYCLE = ["Resolver", "Observar", "Estimar estado cognitivo", "Identificar lacunas", "Adaptar", "Evoluir"];

const VALOR = [
  { icon: Brain, title: "Padrões, não notas", body: "Descobrimos por que você erra — leitura apressada, excesso de confiança, duas variáveis simultâneas." },
  { icon: Sparkles, title: "Perfil cognitivo", body: "Um retrato vivo da sua mente: precisão, velocidade, abstração e tolerância à complexidade." },
  { icon: Network, title: "Mapa de aprendizagem", body: "Não estude o sintoma. Estude a causa-raiz — o grafo revela o que precisa ser destravado." },
];

/** O convite à ação. Um só verbo, repetido em toda a página: quem muda o
 *  texto do botão a cada seção ensina que são coisas diferentes. */
function BotaoPrincipal({ user, nav, testid, children }) {
  return (
    <button
      onClick={() => nav(user ? "/dashboard" : "/login?novo=1")}
      className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-7 py-4 text-base font-bold"
      data-testid={testid}
    >
      {user ? "Ir para o painel" : children || "Começar agora"} <ArrowRight className="h-4 w-4" />
    </button>
  );
}

export default function Landing() {
  const nav = useNavigate();
  const { user } = useAuth();

  return (
    <div className="topo-seguro min-h-screen">
      {/* Barra do topo */}
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 pt-6 md:px-10">
        <Logo tamanho="m" testid="landing-brand" />
        <div className="flex items-center gap-3">
          {user ? (
            <Link to="/dashboard" className="pill btn-sapiens rounded-full px-5 py-2.5 text-sm font-bold" data-testid="landing-go-dashboard">
              Ir para o painel
            </Link>
          ) : (
            <Link to="/login" className="pill btn-vidro rounded-full px-5 py-2.5 text-sm font-semibold" data-testid="landing-login">
              Entrar
            </Link>
          )}
        </div>
      </div>

      {/* ---------------- 1. O HERÓI E O QUE ELE QUER ----------------
          Uma promessa, uma frase de como, um convite. Nada mais acima da
          dobra: cada elemento a mais aqui custa um leitor. */}
      <div className="mx-auto max-w-3xl px-5 pb-14 pt-16 text-center md:px-10 md:pt-24">
        <div className="reveal mb-8 flex justify-center">
          <BrandMark className="h-24 w-24 md:h-32 md:w-32" halo />
        </div>
        <div className="reveal reveal-delay-1 secao-olho">Para quem vai prestar vestibular</div>
        <h1
          className="reveal reveal-delay-2 mt-5 font-display text-[clamp(2.4rem,1.2rem+5.2vw,4.5rem)] font-extrabold leading-[1.02] tracking-[-0.045em] text-white"
          data-testid="landing-hero-title"
        >
          Transforme seus erros em <span className="shimmer">conhecimento</span>.
        </h1>
        <p className="reveal reveal-delay-3 mx-auto mt-6 max-w-xl text-lg leading-relaxed text-white/65" data-testid="landing-hero-subtitle">
          Você não erra por falta de estudo. Erra por um padrão que ninguém nunca
          te mostrou. O Sapiens encontra esse padrão — e te conecta com o seu
          melhor futuro.
        </p>
        <div className="reveal reveal-delay-4 mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <BotaoPrincipal user={user} nav={nav} testid="landing-analyze-cta" />
          {/* CTA transicional: para quem ainda não vai dar o e-mail. Sem ele,
              quem não clica no primeiro botão simplesmente sai. */}
          <a href="#plano" className="pill btn-vidro inline-flex items-center gap-2 rounded-full px-6 py-4 text-sm font-semibold" data-testid="landing-cta-transicional">
            Ver como funciona
          </a>
        </div>
        <p className="reveal reveal-delay-4 mt-4 text-xs text-white/40">
          Grátis para começar · leva 10 minutos · funciona no celular
        </p>
      </div>

      {/* O relógio do ENEM, público: quem ainda não entrou está correndo
          contra a mesma data de quem já está aqui dentro. */}
      <div className="mx-auto max-w-4xl px-5 pb-16 md:px-10">
        <ContagemEnem comCta={false} testid="landing-contagem-enem" />
      </div>

      {/* ---------------- 2. O PROBLEMA ----------------
          O vilão tem nome (estudar no escuro) porque história sem vilão não
          tem tensão — e sem tensão ninguém lê a seção seguinte. */}
      <div className="mx-auto max-w-5xl px-5 pb-6 md:px-10" data-testid="landing-problema">
        <div className="mx-auto max-w-2xl text-center">
          <div className="secao-olho">O que está travando você</div>
          <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-white md:text-4xl">
            O problema nunca foi preguiça. Foi estudar no escuro.
          </h2>
        </div>
        <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-3">
          {PROBLEMA.map((p, i) => (
            <div key={p.titulo} className="superficie p-7" data-testid={`landing-problema-${i}`}>
              <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-rose-400/25 bg-rose-500/10 text-rose-200">
                <X className="h-4 w-4" strokeWidth={2.2} />
              </span>
              <div className="mt-4 font-display text-lg font-bold tracking-tight text-white">{p.titulo}</div>
              <div className="mt-2 text-sm leading-relaxed text-white/55">{p.corpo}</div>
            </div>
          ))}
        </div>
        <p className="mx-auto mt-10 max-w-2xl text-center font-display text-xl leading-snug tracking-tight text-white/85 md:text-2xl" data-testid="landing-dor">
          {DOR_INTERNA}
        </p>
      </div>

      {/* ---------------- 3. O GUIA (parte 1: a Mentis) ----------------
          Empatia PRIMEIRO, autoridade depois — nesta ordem. Autoridade sem
          empatia lê como vendedor; empatia sem autoridade lê como colega. */}
      <div className="mx-auto max-w-4xl px-5 pb-16 pt-14 md:px-10">
        <div className="superficie relative overflow-hidden p-7 md:p-10" data-testid="landing-guia">
          <div className="grid gap-8 md:grid-cols-[auto_1fr] md:items-start">
            <div className="flex justify-center">
              <Mentis className="h-28 w-28 md:h-32 md:w-32" estado="analise" />
            </div>
            <div className="min-w-0">
              <div className="secao-olho">Conheça a Mentis</div>
              <h2 className="mt-2 font-display text-2xl font-extrabold leading-tight tracking-tighter text-white md:text-4xl">
                Ela já viu esse erro antes. E sabe o que fazer com ele.
              </h2>
              <p className="mt-4 leading-relaxed text-white/65">
                A Mentis é a inteligência do Sapiens — e ela não te dá aula: ela
                te lê. Cada questão que você responde diz a ela alguma coisa sobre
                como você pensa, e é disso que sai o seu plano. Você não precisa
                descobrir sozinho o que estudar. Esse trabalho é dela.
              </p>
              {/* Autoridade: o que dá respaldo NÃO é adjetivo, é referência. */}
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="secao-olho flex items-center gap-1.5 text-[#7FD8FF]/85">
                  <BookOpen className="h-3 w-3" /> Nada aqui é achismo
                </div>
                <ul className="mt-3 space-y-2">
                  {EMBASAMENTO.map((e) => (
                    <li key={e.fonte} className="flex gap-2 text-sm leading-relaxed text-white/55">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#7FD8FF]" strokeWidth={2.2} />
                      <span><strong className="font-semibold text-white/80">{e.fonte}</strong> — {e.uso}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ---------------- 3. O GUIA (parte 2: a pessoa) ----------------
          Uma IA sozinha não constrói confiança: quem assina o método tem rosto,
          nome e uma credencial que se pode conferir. */}
      <div className="mx-auto max-w-4xl px-5 pb-16 md:px-10">
        <div className="mapa-vitrine relative overflow-hidden rounded-[30px] p-7 md:p-10" data-testid="landing-live">
          <div className="relative grid gap-8 md:grid-cols-[1fr_auto] md:items-center">
            <div className="min-w-0">
              <span className="inline-flex items-center gap-2 rounded-full border border-rose-400/40 bg-rose-500/15 px-3 py-1.5 font-mono-alt text-[10px] font-bold uppercase tracking-[0.2em] text-rose-200">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-400" />
                </span>
                Ao vivo · toda quinta-feira
              </span>
              <h2 className="mt-5 font-display text-3xl font-extrabold leading-[1.03] tracking-tighter text-white md:text-5xl">
                {/* Sem `.shimmer` aqui, ao contrário do que o herói usava: o
                    gradiente animado sobre `background-clip: text` come a
                    barriga do "P" em tamanho de display e a palavra lê "USF"
                    (medido no navegador em 2026-09-15). */}
                Toda quinta você estuda com o{" "}
                <span className="text-[#7FD8FF]">{MENTOR.nome}</span>, {MENTOR.titulo}.
              </h2>
              <p className="mt-4 max-w-2xl leading-relaxed text-white/65">
                Ao vivo, 60 min, uma vez por semana. {MENTOR.nome} resolve questão na
                sua frente, conta a rotina que o levou ao primeiro lugar no vestibular mais
                disputado do país e responde as suas perguntas no fim. Não é gravação, não é
                resumo em PDF — e cada edição acontece uma vez só.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => nav(user ? "/aula-ao-vivo" : "/login")}
                  className="pill btn-calor inline-flex items-center gap-2 rounded-full px-7 py-4 text-base font-bold"
                  data-testid="landing-live-cta"
                >
                  <Radio className="h-4 w-4" /> Quero entrar na próxima quinta
                </button>
                <span className="inline-flex items-center gap-1.5 text-xs text-white/45">
                  <Clock className="h-3.5 w-3.5" /> 20h, horário de Brasília · 60 min
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs text-white/45">
                  <Video className="h-3.5 w-3.5" /> ao vivo no Google Meet
                </span>
              </div>

              {/* O box MENOR é a medalha, e o grande é o rosto. Duas fotos da
                  mesma pessoa a 20cm uma da outra competem entre si; a
                  medalha diz a mesma coisa em outro registro. */}
              <div className="mt-7 flex flex-col items-stretch gap-4 border-t border-white/10 pt-6 sm:flex-row sm:items-center">
                <div className="flex min-w-0 flex-1 items-center gap-4">
                  <MentorUSP tamanho="p" variante="medalha" comSelo={false} testid="landing-mentor-mini" />
                  <div className="min-w-0 flex-1">
                    <div className="secao-olho flex items-center gap-1.5 text-amber-200/85">
                      <Medal className="h-3 w-3" /> A mesma pessoa, um a um
                    </div>
                    <div className="mt-1 text-sm text-white/60">
                      A mentoria com {MENTOR.nome} tem lista de espera — uma pessoa,
                      poucas vagas.
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => nav(user ? "/mentoria" : "/login")}
                  className="pill btn-vidro inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold sm:w-auto"
                  data-testid="landing-mentoria-cta"
                >
                  <Users className="h-4 w-4" /> Entrar na lista
                </button>
              </div>
            </div>

            {/* O rosto grande. É o maior ativo do produto e a landing é onde
                mora quem ainda não conhece ninguém aqui. */}
            <div className="order-first flex justify-center md:order-none">
              <MentorUSP tamanho="g" testid="landing-mentor" />
            </div>
          </div>
        </div>
      </div>

      {/* ---------------- QUEM É O VITOR ----------------
          O rosto já aparece acima, mas rosto não conta história. Quem chega
          por um link de WhatsApp não tem como verificar uma credencial grande
          dita por um site; um vídeo em que a pessoa fala é a coisa mais
          próxima de verificação que a landing consegue oferecer.

          Fachada, não iframe: o player só carrega no clique. Ver
          `components/VideoDoMentor`. */}
      <div className="mx-auto max-w-3xl px-5 pb-20 md:px-10">
        <div className="mb-4 text-center">
          <div className="secao-olho">Quem dá as aulas</div>
          <h2 className="mt-2 font-display text-2xl font-extrabold tracking-tighter text-white md:text-3xl">
            {MENTOR.nome} não é um professor contratado.
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-white/55">
            É a pessoa que passou em <strong className="font-semibold text-white/80">1º lugar
            em Medicina na USP</strong> — e é ela que grava os cursos, dá a aula ao vivo de
            quinta e atende a mentoria. Veja com as palavras dele.
          </p>
        </div>
        <VideoDoMentor testid="landing-video-mentor" />
      </div>

      {/* ---------------- 4. O PLANO ----------------
          Três passos. O plano existe para tirar o risco da cabeça de quem lê:
          "eu não vou saber usar" morre aqui, não no suporte. */}
      <div id="plano" className="mx-auto max-w-5xl scroll-mt-8 px-5 pb-8 md:px-10" data-testid="landing-plano">
        <div className="mx-auto max-w-2xl text-center">
          <div className="secao-olho">O plano</div>
          <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-white md:text-4xl">
            Três passos. O primeiro leva dez minutos.
          </h2>
        </div>
        <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-3">
          {PLANO.map((p, i) => (
            <div key={p.passo} className="superficie lift relative p-7" data-testid={`landing-plano-${i}`}>
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#4FD9FF]/25 bg-[#4FD9FF]/10 font-display text-lg font-extrabold text-[#7FD8FF]">
                {p.passo}
              </span>
              <div className="mt-4 font-display text-lg font-bold tracking-tight text-white">{p.titulo}</div>
              <div className="mt-2 text-sm leading-relaxed text-white/55">{p.corpo}</div>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-center gap-3">
          <BotaoPrincipal user={user} nav={nav} testid="landing-plano-cta">Fazer o meu diagnóstico</BotaoPrincipal>
          <span className="inline-flex items-center gap-1.5 text-xs text-white/40">
            <ShieldCheck className="h-3.5 w-3.5" /> Sem cartão. Você pode parar quando quiser.
          </span>
        </div>
      </div>

      {/* ---------------- O ciclo cognitivo ----------------
          O detalhe técnico vem DEPOIS do plano, e de propósito: é a resposta
          para quem quer saber como, não a abertura para quem quer saber se
          resolve. */}
      <div className="mx-auto max-w-4xl px-5 pb-20 pt-10 text-center md:px-10">
        <p className="font-display text-xl tracking-tight text-white/90 md:text-2xl" data-testid="landing-tagline">
          O Sapiens aprende como você aprende.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-1.5 gap-y-3" data-testid="landing-cycle">
          {CYCLE.map((step, i) => (
            <div key={step} className="flex items-center gap-1.5">
              <span className="chip font-mono-alt text-xs">{step}</span>
              {i < CYCLE.length - 1 && <ChevronRight className="h-4 w-4 shrink-0 text-white/25" />}
            </div>
          ))}
        </div>
      </div>

      {/* ---------------- 6 e 7. FRACASSO EVITADO E SUCESSO ----------------
          Os dois lados juntos e nesta ordem — o que se perde, depois o que se
          ganha, porque a história tem de terminar no sucesso. A coluna do
          fracasso é curta e a do sucesso é longa: proporção é ética aqui. */}
      <div className="mx-auto max-w-5xl px-5 pb-24 md:px-10" data-testid="landing-apostas">
        <div className="mx-auto max-w-2xl text-center">
          <div className="secao-olho">O que está em jogo</div>
          <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-white md:text-4xl">
            Um ano decide os próximos trinta.
          </h2>
          <p className="mt-3 text-white/55">
            Não é sobre uma prova. É sobre quem você vai ser depois dela.
          </p>
        </div>
        <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-2">
          <div className="superficie p-7 md:order-last" data-testid="landing-sucesso">
            <div className="secao-olho flex items-center gap-1.5 text-[#7FD8FF]/85">
              <Sparkles className="h-3 w-3" /> {APOSTAS.sucesso.titulo}
            </div>
            <ul className="mt-4 space-y-3">
              {APOSTAS.sucesso.itens.map((t) => (
                <li key={t} className="flex gap-2 leading-relaxed text-white/75">
                  <Check className="mt-1 h-4 w-4 shrink-0 text-[#7FD8FF]" strokeWidth={2.2} />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-[26px] border border-white/10 bg-white/[0.02] p-7" data-testid="landing-fracasso">
            <div className="secao-olho flex items-center gap-1.5 text-white/40">
              <X className="h-3 w-3" /> {APOSTAS.fracasso.titulo}
            </div>
            <ul className="mt-4 space-y-3">
              {APOSTAS.fracasso.itens.map((t) => (
                <li key={t} className="flex gap-2 text-sm leading-relaxed text-white/45">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-white/30" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
            <p className="mt-5 text-sm leading-relaxed text-white/55">
              Nenhuma das duas listas depende de sorte. Dependem do que você faz
              a partir de hoje — e de ter, enfim, um método.
            </p>
          </div>
        </div>
      </div>

      {/* ---------------- PROVA SOCIAL ----------------
          Depoimentos reais reescritos em forma geral e SEM identificação, a
          pedido de quem tem as mensagens originais. Ver a nota em
          `lib/historia.js`: sem nome, sem foto, sem faculdade específica —
          parafrasear já é limite, atribuir seria inventar. */}
      <div className="mx-auto max-w-5xl px-5 pb-24 md:px-10" data-testid="landing-depoimentos">
        <div className="mx-auto max-w-2xl text-center">
          <div className="secao-olho">Quem já passou por aqui</div>
          <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-white md:text-4xl">
            Alunos do Sapiens já estão na universidade pública. Inclusive em Medicina.
          </h2>
        </div>
        <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {DEPOIMENTOS.map((d, i) => (
            <figure key={i} className="superficie p-7" data-testid={`landing-depoimento-${i}`}>
              <Quote className="h-5 w-5 text-[#7FD8FF]/60" />
              <blockquote className="mt-3 leading-relaxed text-white/80">"{d.texto}"</blockquote>
              <figcaption className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-white/35">
                {d.assina}
              </figcaption>
            </figure>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-white/30">
          Depoimentos de alunos, publicados sem identificação a pedido deles.
        </p>
      </div>

      {/* ---------------- O QUE VOCÊ RECEBE ---------------- */}
      <div className="mx-auto max-w-5xl px-5 pb-24 md:px-10">
        <div className="mx-auto mb-10 max-w-2xl text-center">
          <div className="secao-olho">Por dentro</div>
          <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-white md:text-4xl">
            O que a Mentis devolve para você
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {VALOR.map((c, i) => (
            <div key={c.title} className="superficie lift p-7" data-testid={`landing-feature-${i}`}>
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#4FD9FF]/25 bg-[#4FD9FF]/10 text-[#7FD8FF]">
                <c.icon className="h-5 w-5" strokeWidth={1.7} />
              </span>
              <div className="mt-4 font-display text-lg font-bold tracking-tight text-white">{c.title}</div>
              <div className="mt-2 text-sm leading-relaxed text-white/55">{c.body}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ---------------- PERGUNTAS ----------------
          Objeção respondida é conversão, e é também o bloco que o Google lê
          como FAQPage. O JSON-LD equivalente está no `public/index.html` e
          precisa dizer EXATAMENTE o mesmo texto. */}
      <div className="mx-auto max-w-3xl px-5 pb-24 md:px-10" data-testid="landing-faq">
        <div className="mb-8 text-center">
          <div className="secao-olho">Perguntas frequentes</div>
          <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-white md:text-4xl">
            O que todo mundo pergunta antes de começar
          </h2>
        </div>
        <div className="space-y-3">
          {FAQ.map((f, i) => (
            <details key={f.p} className="superficie group p-6" data-testid={`landing-faq-${i}`}>
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-display text-base font-bold tracking-tight text-white">
                {f.p}
                <ChevronRight className="h-4 w-4 shrink-0 text-white/35 transition-transform group-open:rotate-90" />
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-white/60">{f.r}</p>
            </details>
          ))}
        </div>
      </div>

      {/* ---------------- 5. O CONVITE, DE NOVO ----------------
          Quem chegou até aqui leu a história inteira. O último bloco não
          explica mais nada: só chama. */}
      <div className="mx-auto max-w-3xl px-5 pb-28 text-center md:px-10">
        <div className="superficie px-7 py-12 md:px-12">
          <BrandMark className="mx-auto h-14 w-14" halo />
          <h2 className="mt-6 font-display text-3xl font-extrabold leading-tight tracking-tighter text-white md:text-4xl">
            O seu próximo erro pode ser o último daquele tipo.
          </h2>
          <p className="mx-auto mt-4 max-w-md leading-relaxed text-white/60">
            Comece hoje pelo diagnóstico. Em dez minutos você sai daqui sabendo
            o que estudar amanhã de manhã — e por quê.
          </p>
          <div className="mt-8 flex justify-center">
            <BotaoPrincipal user={user} nav={nav} testid="landing-cta-final">Começar agora</BotaoPrincipal>
          </div>
        </div>
      </div>

      {/* Rodapé legal — exigido para publicar: identificação de quem opera o
          serviço, documentos e um canal de contato (CDC art. 31, LGPD art. 9). */}
      <footer className="border-t border-white/10">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-5 py-10 text-sm md:flex-row md:px-10">
          <div className="flex items-center gap-3 text-white/40">
            <BrandMark className="h-5 w-5" />
            © {new Date().getFullYear()} {OPERADOR.razaoSocial || OPERADOR.nomeFantasia}
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-white/50">
            <Link to="/termos" className="transition-colors hover:text-white">Termos de Uso</Link>
            <Link to="/privacidade" className="transition-colors hover:text-white">Privacidade</Link>
            <a href={`mailto:${OPERADOR.emailContato}`} className="transition-colors hover:text-white">Contato</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
