import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, Brain, Network } from "lucide-react";
import { useAuth } from "../lib/auth";

export default function Landing() {
  const nav = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen grain">
      {/* Top bar */}
      <div className="max-w-6xl mx-auto px-6 md:px-10 pt-6 flex items-center justify-between">
        <div className="font-display text-2xl font-extrabold tracking-tighter" data-testid="landing-brand">
          Sapiens<span className="text-emerald-500">.</span>
        </div>
        <div className="flex items-center gap-3">
          {user ? (
            <Link to="/dashboard" className="pill text-sm font-medium bg-zinc-950 text-white hover:bg-zinc-800 px-4 py-2 rounded-full" data-testid="landing-go-dashboard">
              Ir para o painel
            </Link>
          ) : (
            <Link to="/login" className="pill text-sm font-medium text-zinc-900 hover:text-zinc-600 px-3 py-2" data-testid="landing-login">
              Entrar
            </Link>
          )}
        </div>
      </div>

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 md:px-10 pt-24 md:pt-32 pb-16 text-center">
        <div className="reveal font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-6">
          Inteligência educacional
        </div>
        <h1 className="reveal reveal-delay-1 font-display text-6xl md:text-8xl font-extrabold tracking-tighter leading-[0.95] text-zinc-950" data-testid="landing-hero-title">
          <span className="shimmer">Sapiens</span>
        </h1>
        <p className="reveal reveal-delay-2 mt-8 text-2xl md:text-3xl font-display text-zinc-700 tracking-tight" data-testid="landing-hero-subtitle">
          Descubra por que você erra.
        </p>
        <p className="reveal reveal-delay-3 mt-6 max-w-xl mx-auto text-zinc-500 leading-relaxed">
          Não somos um corretor de provas. Somos o sistema que descobre padrões cognitivos escondidos nos seus erros — e transforma cada prova em um mapa para você evoluir.
        </p>
        <div className="reveal reveal-delay-4 mt-10 flex items-center justify-center gap-3">
          <button
            onClick={() => nav(user ? "/exams" : "/login")}
            className="pill inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 text-white text-base font-medium px-7 py-4 rounded-full"
            data-testid="landing-analyze-cta"
          >
            Analisar uma prova <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Three-column value */}
      <div className="max-w-5xl mx-auto px-6 md:px-10 pb-32 grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { icon: Brain, title: "Padrões, não notas", body: "Descobrimos por que você erra — leitura apressada, excesso de confiança, duas variáveis simultâneas." },
          { icon: Sparkles, title: "Perfil cognitivo", body: "Um retrato vivo da sua mente: precisão, velocidade, abstração e tolerância à complexidade." },
          { icon: Network, title: "Mapa de aprendizagem", body: "Não estude o sintoma. Estude a causa-raiz — o grafo revela o que precisa ser destravado." },
        ].map((c, i) => (
          <div key={i} className="lift bg-white border border-zinc-200 rounded-2xl p-7" data-testid={`landing-feature-${i}`}>
            <c.icon className="w-5 h-5 text-emerald-500" strokeWidth={1.6} />
            <div className="mt-4 font-display font-bold text-lg tracking-tight text-zinc-950">{c.title}</div>
            <div className="mt-2 text-sm text-zinc-500 leading-relaxed">{c.body}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
