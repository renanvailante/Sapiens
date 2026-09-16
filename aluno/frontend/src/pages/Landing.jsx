import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, Brain, Network, ChevronRight, Radio, Video, Clock, Medal, Users } from "lucide-react";
import { useAuth } from "../lib/auth";
import BrandMark from "../components/BrandMark";
import MentorUSP from "../components/MentorUSP";
import { OPERADOR } from "../lib/operador";

const CYCLE = ["Resolver", "Observar", "Estimar estado cognitivo", "Identificar lacunas", "Adaptar", "Evoluir"];

export default function Landing() {
  const nav = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen grain">
      {/* Top bar */}
      <div className="max-w-6xl mx-auto px-6 md:px-10 pt-6 flex items-center justify-between">
        <div className="flex items-center gap-2 font-display text-2xl font-extrabold tracking-tighter text-white" data-testid="landing-brand">
          <BrandMark className="w-6 h-6" />
          Sapiens
        </div>
        <div className="flex items-center gap-3">
          {user ? (
            <Link to="/dashboard" className="pill btn-sapiens text-sm font-medium px-4 py-2 rounded-full" data-testid="landing-go-dashboard">
              Ir para o painel
            </Link>
          ) : (
            <Link to="/login" className="pill text-sm font-medium text-white/80 hover:text-white px-3 py-2" data-testid="landing-login">
              Entrar
            </Link>
          )}
        </div>
      </div>

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 md:px-10 pt-24 md:pt-32 pb-16 text-center">
        <div className="reveal font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-6">
          Inteligência educacional
        </div>
        <h1 className="reveal reveal-delay-1 font-display text-6xl md:text-8xl font-extrabold tracking-tighter leading-[0.95]" data-testid="landing-hero-title">
          <span className="shimmer">Sapiens</span>
        </h1>
        <p className="reveal reveal-delay-2 mt-8 text-2xl md:text-3xl font-display text-white/90 tracking-tight" data-testid="landing-hero-subtitle">
          Descubra por que você erra.
        </p>
        <p className="reveal reveal-delay-3 mt-6 max-w-xl mx-auto text-white/60 leading-relaxed">
          Não somos um corretor de provas. Somos o sistema que descobre padrões cognitivos escondidos nos seus erros — e transforma cada prova em um mapa para você evoluir.
        </p>
        <div className="reveal reveal-delay-4 mt-10 flex items-center justify-center gap-3">
          <button
            onClick={() => nav(user ? "/exams" : "/login")}
            className="pill btn-sapiens inline-flex items-center gap-2 text-base font-medium px-7 py-4 rounded-full"
            data-testid="landing-analyze-cta"
          >
            Analisar uma prova <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* A AULA AO VIVO DE QUINTA — a primeira coisa depois do herói.
          É o único compromisso com hora marcada que o produto tem, o
          argumento mais forte que ele oferece a quem ainda não entrou, e a
          landing é onde mora quem ainda não entrou. */}
      <div className="max-w-4xl mx-auto px-6 md:px-10 pb-16">
        <div className="mapa-vitrine relative overflow-hidden rounded-3xl p-7 md:p-10" data-testid="landing-live">
          <div className="relative grid gap-8 md:grid-cols-[1fr_auto] md:items-center">
            <div className="min-w-0">
            <span className="inline-flex items-center gap-2 rounded-full border border-rose-400/40 bg-rose-500/15 px-3 py-1.5 font-mono-alt text-[10px] font-bold uppercase tracking-[0.2em] text-rose-200">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-400" />
              </span>
              Ao vivo · toda quinta-feira
            </span>
            <h2 className="mt-5 font-display text-3xl md:text-5xl font-extrabold tracking-tighter leading-[1.03] text-white">
              {/* Sem `.shimmer` aqui, ao contrário do "Sapiens" do herói: o
                  gradiente animado sobre `background-clip: text` come a
                  barriga do "P" em tamanho de display e a palavra lê "USF"
                  (medido no navegador em 2026-09-15). */}
              Toda quinta você estuda com o{" "}
              <span className="text-[#7FD8FF]">1º colocado de Medicina da USP</span>.
            </h2>
            <p className="mt-4 max-w-2xl text-white/65 leading-relaxed">
              Ao vivo, 90 minutos, uma vez por semana. Ele resolve questão na sua frente,
              conta a rotina que o levou ao primeiro lugar no vestibular mais disputado do
              país e responde as suas perguntas no fim. Não é gravação, não é resumo em PDF.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                onClick={() => nav(user ? "/cursos" : "/login")}
                className="pill btn-calor inline-flex items-center gap-2 text-base font-medium px-7 py-4 rounded-full"
                data-testid="landing-live-cta"
              >
                <Radio className="w-4 h-4" /> Quero entrar na próxima quinta
              </button>
              <span className="inline-flex items-center gap-1.5 text-xs text-white/45">
                <Clock className="w-3.5 h-3.5" /> 20h, horário de Brasília
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs text-white/45">
                <Video className="w-3.5 h-3.5" /> ao vivo no Google Meet
              </span>
            </div>

            <div className="mt-7 flex flex-wrap items-center gap-4 border-t border-white/10 pt-6">
              <MentorUSP tamanho="p" comSelo={false} testid="landing-mentor-mini" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 font-mono-alt text-[10px] uppercase tracking-[0.2em] text-amber-200">
                  <Medal className="w-3 h-3" /> A mesma pessoa, um a um
                </div>
                <div className="mt-0.5 text-sm text-white/60">
                  A mentoria individual tem lista de espera — uma pessoa, poucas vagas.
                </div>
              </div>
              <button
                onClick={() => nav(user ? "/mentoria" : "/login")}
                className="pill btn-vidro inline-flex shrink-0 items-center gap-2 rounded-full px-5 py-3 text-sm"
                data-testid="landing-mentoria-cta"
              >
                <Users className="w-4 h-4" /> Entrar na lista
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

      {/* O ciclo cognitivo */}
      <div className="max-w-4xl mx-auto px-6 md:px-10 pb-24 text-center">
        <p className="font-display text-xl md:text-2xl text-white/90 tracking-tight" data-testid="landing-tagline">
          O Sapiens aprende como você aprende.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-1.5 gap-y-4" data-testid="landing-cycle">
          {CYCLE.map((step, i) => (
            <div key={step} className="flex items-center gap-1.5">
              <span className="font-mono-alt text-xs md:text-sm text-white/70 bg-white/5 border border-white/10 rounded-full px-4 py-2">
                {step}
              </span>
              {i < CYCLE.length - 1 && <ChevronRight className="w-4 h-4 text-white/25 shrink-0" />}
            </div>
          ))}
        </div>
      </div>

      {/* Three-column value */}
      <div className="max-w-5xl mx-auto px-6 md:px-10 pb-32 grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { icon: Brain, title: "Padrões, não notas", body: "Descobrimos por que você erra — leitura apressada, excesso de confiança, duas variáveis simultâneas." },
          { icon: Sparkles, title: "Perfil cognitivo", body: "Um retrato vivo da sua mente: precisão, velocidade, abstração e tolerância à complexidade." },
          { icon: Network, title: "Mapa de aprendizagem", body: "Não estude o sintoma. Estude a causa-raiz — o grafo revela o que precisa ser destravado." },
        ].map((c, i) => (
          <div key={i} className="lift card-sapiens rounded-2xl p-7" data-testid={`landing-feature-${i}`}>
            <c.icon className="w-5 h-5 text-sapiens-accent" strokeWidth={1.6} />
            <div className="mt-4 font-display font-bold text-lg tracking-tight text-zinc-950">{c.title}</div>
            <div className="mt-2 text-sm text-zinc-500 leading-relaxed">{c.body}</div>
          </div>
        ))}
      </div>

      {/* Rodapé legal — exigido para publicar: identificação de quem opera o
          serviço, documentos e um canal de contato (CDC art. 31, LGPD art. 9). */}
      <footer className="border-t border-white/10">
        <div className="max-w-5xl mx-auto px-6 md:px-10 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm">
          <div className="text-white/40">
            © {new Date().getFullYear()} {OPERADOR.razaoSocial || OPERADOR.nomeFantasia}
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-white/50">
            <Link to="/termos" className="hover:text-white transition-colors">Termos de Uso</Link>
            <Link to="/privacidade" className="hover:text-white transition-colors">Privacidade</Link>
            <a href={`mailto:${OPERADOR.emailContato}`} className="hover:text-white transition-colors">Contato</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
