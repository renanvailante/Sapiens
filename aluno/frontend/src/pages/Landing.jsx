import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, Brain, Network, ChevronRight } from "lucide-react";
import { useAuth } from "../lib/auth";
import BrandMark from "../components/BrandMark";

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
    </div>
  );
}
