import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight, Sparkles, Network, Compass } from "lucide-react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { useAuth } from "../lib/auth";

export default function Dashboard() {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState([]);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/analyses").then(({ data }) => setAnalyses(data));
  }, []);

  const latest = analyses[0];
  const evolution = [...analyses].reverse().map((a, i) => ({ name: `#${i + 1}`, pct: a.percent }));
  const profileData = latest ? Object.entries(latest.cognitive_profile || {}).map(([k, v]) => ({ trait: k, value: Number(v) })) : [];

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-10">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-10">
          <div>
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-2">Painel</div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="dash-title">
              Olá, {user?.name?.split(" ")[0] || "aluno"}.
            </h1>
            <p className="mt-2 text-zinc-500 max-w-lg">Aqui está o que o Sapiens descobriu sobre você.</p>
          </div>
          <button onClick={() => nav("/exams")} className="pill inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 text-white px-5 py-3 rounded-full text-sm font-medium" data-testid="dash-new-analysis">
            <Sparkles className="w-4 h-4" /> Analisar prova
          </button>
        </div>

        {analyses.length === 0 ? (
          <div className="bg-white border border-zinc-200 rounded-2xl p-10 text-center">
            <div className="font-display text-2xl font-bold tracking-tight text-zinc-950">Sua primeira análise está a um clique.</div>
            <p className="mt-2 text-zinc-500 max-w-md mx-auto">Escolha uma prova do ENEM, envie suas respostas e revelaremos os padrões cognitivos por trás delas.</p>
            <button onClick={() => nav("/exams")} className="pill mt-6 inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 text-white px-6 py-3 rounded-full text-sm font-medium" data-testid="dash-cta-first">
              Começar <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Latest headline */}
            <div className="md:col-span-3 bg-zinc-950 text-white rounded-2xl p-8">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Último diagnóstico · {latest.exam_label}</div>
              <div className="mt-4 font-display text-2xl md:text-3xl tracking-tight leading-tight" data-testid="dash-headline">
                {latest.diagnostic_headline}
              </div>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <Link to={`/analysis/${latest.analysis_id}`} className="pill inline-flex items-center gap-2 bg-white text-zinc-950 hover:bg-zinc-100 px-5 py-2.5 rounded-full text-sm font-medium" data-testid="dash-open-analysis">
                  Ver análise completa <ArrowRight className="w-4 h-4" />
                </Link>
                <Link to={`/plan/${latest.analysis_id}`} className="pill inline-flex items-center gap-2 border border-zinc-700 text-white hover:bg-zinc-900 px-5 py-2.5 rounded-full text-sm font-medium" data-testid="dash-open-plan">
                  <Compass className="w-4 h-4" /> Plano de estudos
                </Link>
                <Link to={`/map/${latest.analysis_id}`} className="pill inline-flex items-center gap-2 border border-zinc-700 text-white hover:bg-zinc-900 px-5 py-2.5 rounded-full text-sm font-medium" data-testid="dash-open-map">
                  <Network className="w-4 h-4" /> Mapa de aprendizagem
                </Link>
              </div>
            </div>

            {/* Evolution */}
            <div className="md:col-span-2 bg-white border border-zinc-200 rounded-2xl p-6">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-4">Evolução</div>
              <div className="h-56">
                <ResponsiveContainer>
                  <LineChart data={evolution}>
                    <CartesianGrid stroke="#f4f4f5" vertical={false} />
                    <XAxis dataKey="name" stroke="#a1a1aa" fontSize={12} axisLine={false} tickLine={false} />
                    <YAxis stroke="#a1a1aa" fontSize={12} axisLine={false} tickLine={false} domain={[0, 100]} />
                    <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e4e4e7" }} />
                    <Line type="monotone" dataKey="pct" stroke="#10b981" strokeWidth={2.5} dot={{ r: 4, fill: "#10b981" }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Cognitive Profile */}
            <div className="bg-white border border-zinc-200 rounded-2xl p-6">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-4">Perfil cognitivo</div>
              <div className="h-56">
                <ResponsiveContainer>
                  <RadarChart data={profileData}>
                    <PolarGrid stroke="#e4e4e7" />
                    <PolarAngleAxis dataKey="trait" fontSize={9} stroke="#71717a" />
                    <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar dataKey="value" stroke="#4f46e5" fill="#4f46e5" fillOpacity={0.15} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Strengths / Weaknesses */}
            <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-6">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-emerald-700 mb-3">Conteúdos fortes</div>
              <ul className="space-y-2 text-sm text-zinc-800">
                {(latest.strengths || []).slice(0, 5).map((s, i) => <li key={i}>· {s}</li>)}
              </ul>
            </div>
            <div className="bg-rose-50 border border-rose-100 rounded-2xl p-6 md:col-span-2">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-rose-700 mb-3">Padrões de erro a atacar</div>
              <ul className="space-y-2 text-sm text-zinc-800">
                {(latest.weaknesses || []).slice(0, 6).map((s, i) => <li key={i}>· {s}</li>)}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
