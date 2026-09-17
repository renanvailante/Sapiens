import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, Brain, Network, ChevronRight, Radio, Video, Clock, Medal, Users } from "lucide-react";
import { useAuth } from "../lib/auth";
import Logo from "../components/Logo";
import BrandMark from "../components/BrandMark";
import MentorUSP from "../components/MentorUSP";
import VideoDoMentor from "../components/VideoDoMentor";
import { MENTOR } from "../lib/mentor";
import ContagemEnem from "../components/ContagemEnem";
import { OPERADOR } from "../lib/operador";

/**
 * A landing — a única tela que fala com quem ainda não é aluno.
 *
 * O herói mudou em 2026-09-16: a palavra "Sapiens" em corpo 8xl deixou de ser
 * o primeiro plano e deu lugar à MARCA, grande e com halo, acima da frase que
 * o produto realmente vende — um nome em corpo gigante não diz o que o produto
 * faz, e quem chega aqui por um link de WhatsApp tem cinco segundos.
 *
 * **O degradê animado voltou em 2026-09-17**, agora sobre "conhecimento" — a
 * palavra que a frase existe para entregar. Ele tinha sido banido porque
 * comia a barriga das letras em corpo de display (foi o que fez "USP" ler
 * "USF" no título da live): a rampa antiga ia até um azul escuro, e em corpo
 * grande uma parada de degradê cobre uma letra inteira, então a letra sumia.
 * O `.shimmer` do `index.css` foi corrigido junto — o piso subiu para o mesmo
 * #7FD8FF das outras palavras de destaque e o branco virou uma faixa estreita
 * que passa por cima. Ver a nota longa lá.
 */

const CYCLE = ["Resolver", "Observar", "Estimar estado cognitivo", "Identificar lacunas", "Adaptar", "Evoluir"];

const VALOR = [
  { icon: Brain, title: "Padrões, não notas", body: "Descobrimos por que você erra — leitura apressada, excesso de confiança, duas variáveis simultâneas." },
  { icon: Sparkles, title: "Perfil cognitivo", body: "Um retrato vivo da sua mente: precisão, velocidade, abstração e tolerância à complexidade." },
  { icon: Network, title: "Mapa de aprendizagem", body: "Não estude o sintoma. Estude a causa-raiz — o grafo revela o que precisa ser destravado." },
];

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

      {/* ---------------- Herói ---------------- */}
      <div className="mx-auto max-w-3xl px-5 pb-16 pt-20 text-center md:px-10 md:pt-28">
        <div className="reveal mb-8 flex justify-center">
          <BrandMark className="h-24 w-24 md:h-32 md:w-32" halo />
        </div>
        <div className="reveal reveal-delay-1 secao-olho">Inteligência educacional</div>
        <h1
          className="reveal reveal-delay-2 mt-5 font-display text-[clamp(2.4rem,1.2rem+5.2vw,4.5rem)] font-extrabold leading-[1.02] tracking-[-0.045em] text-white"
          data-testid="landing-hero-title"
        >
          Transforme seus erros em <span className="shimmer">conhecimento</span>.
        </h1>
        <p className="reveal reveal-delay-3 mx-auto mt-6 max-w-xl leading-relaxed text-white/60" data-testid="landing-hero-subtitle">
          O Sapiens descobre padrões cognitivos escondidos nos seus erros e te conecta com
          sua melhor versão.
        </p>
        {/* "Começar agora" leva ao CADASTRO, e não à lista de provas: quem
            chega aqui sem conta não tem prova nenhuma para analisar, e o botão
            antigo ("Analisar uma prova") prometia uma ação que terminava numa
            tela de login sem explicação. `?novo=1` abre a aba "Criar conta"
            já selecionada — ver `pages/Login.jsx`. */}
        <div className="reveal reveal-delay-4 mt-10 flex items-center justify-center gap-3">
          <button
            onClick={() => nav(user ? "/dashboard" : "/login?novo=1")}
            className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-7 py-4 text-base font-bold"
            data-testid="landing-analyze-cta"
          >
            {user ? "Ir para o painel" : "Começar agora"} <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* O relógio do ENEM, público: quem ainda não entrou está correndo
          contra a mesma data de quem já está aqui dentro. */}
      <div className="mx-auto max-w-4xl px-5 pb-10 md:px-10">
        <ContagemEnem comCta={false} testid="landing-contagem-enem" />
      </div>

      {/* ---------------- A AULA AO VIVO DE QUINTA ----------------
          A primeira coisa depois do herói. É o único compromisso com hora
          marcada que o produto tem, o argumento mais forte que ele oferece a
          quem ainda não entrou, e a landing é onde mora quem ainda não entrou. */}
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
                resumo em PDF.
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
              <div className="mt-7 flex flex-wrap items-center gap-4 border-t border-white/10 pt-6">
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
                <button
                  onClick={() => nav(user ? "/mentoria" : "/login")}
                  className="pill btn-vidro inline-flex shrink-0 items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold"
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
            quinta e atende a mentoria. Veja com as suas palavras dele.
          </p>
        </div>
        <VideoDoMentor testid="landing-video-mentor" />
      </div>

      {/* ---------------- O ciclo cognitivo ---------------- */}
      <div className="mx-auto max-w-4xl px-5 pb-24 text-center md:px-10">
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

      {/* ---------------- Três colunas de valor ---------------- */}
      <div className="mx-auto grid max-w-5xl grid-cols-1 gap-5 px-5 pb-32 md:grid-cols-3 md:px-10">
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
