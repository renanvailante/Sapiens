import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight, Sparkles } from "lucide-react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from "recharts";

export default function Diagnostic() {
  const { analysisId } = useParams();
  const [a, setA] = useState(null);
  const [phase, setPhase] = useState("insight"); // 'insight' | 'score'
  const nav = useNavigate();

  useEffect(() => {
    api.get(`/analyses/${analysisId}`).then(({ data }) => setA(data));
  }, [analysisId]);

  if (!a) return (
    <div>
      <Nav />
      <div className="max-w-3xl mx-auto p-10 text-zinc-500 font-medium">Compondo seu diagnóstico...</div>
    </div>
  );

  const areaData = Object.entries(a.by_area || {}).map(([area, v]) => ({
    area, correct: v.correct, total: v.total, pct: v.total ? Math.round(100 * v.correct / v.total) : 0,
  }));
  const profileData = Object.entries(a.cognitive_profile || {}).map(([k, v]) => ({ trait: k, value: Number(v) }));

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-14">
        {phase === "insight" ? (
          <div className="reveal">
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-6">Diagnóstico Sapiens</div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950 leading-[1.02]" data-testid="diag-headline">
              {a.diagnostic_headline || "Seu desempenho revela um padrão que a nota não mostra."}
            </h1>
            <div className="mt-8 space-y-4 text-lg text-zinc-700 leading-relaxed" data-testid="diag-body">
              {(a.diagnostic_body || "").split(/\n+/).map((p, i) => <p key={i}>{p}</p>)}
            </div>

            {(a.strengths?.length || a.weaknesses?.length) ? (
              <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-6">
                  <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-emerald-700">Domínios</div>
                  <ul className="mt-3 space-y-2 text-sm text-zinc-800">
                    {a.strengths.map((s, i) => <li key={i}>· {s}</li>)}
                  </ul>
                </div>
                <div className="bg-rose-50 border border-rose-100 rounded-2xl p-6">
                  <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-rose-700">Padrões de erro</div>
                  <ul className="mt-3 space-y-2 text-sm text-zinc-800">
                    {a.weaknesses.map((s, i) => <li key={i}>· {s}</li>)}
                  </ul>
                </div>
              </div>
            ) : null}

            <div className="mt-10 flex items-center gap-3">
              <button
                onClick={() => setPhase("score")}
                className="pill inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 text-white px-6 py-3 rounded-full text-sm font-medium"
                data-testid="diag-see-numbers"
              >
                Ver os números <ArrowRight className="w-4 h-4" />
              </button>
              <Link to={`/plan/${a.analysis_id}`} className="pill inline-flex items-center gap-2 border border-zinc-200 hover:bg-zinc-50 px-5 py-3 rounded-full text-sm font-medium text-zinc-900" data-testid="diag-see-plan">
                <Sparkles className="w-4 h-4" /> Meu plano
              </Link>
            </div>
          </div>
        ) : (
          <div className="reveal">
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-6">Nota bruta</div>
            <div className="flex items-baseline gap-6">
              <div className="font-display text-8xl font-extrabold tracking-tighter text-zinc-950" data-testid="diag-score">
                {a.score}<span className="text-zinc-300">/{a.total}</span>
              </div>
              <div className="text-2xl text-zinc-500 font-display font-semibold">{a.percent}%</div>
            </div>

            <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white border border-zinc-200 rounded-2xl p-6">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-4">Acertos por área</div>
                <div className="h-56">
                  <ResponsiveContainer>
                    <BarChart data={areaData}>
                      <XAxis dataKey="area" stroke="#a1a1aa" fontSize={12} axisLine={false} tickLine={false} />
                      <YAxis stroke="#a1a1aa" fontSize={12} axisLine={false} tickLine={false} />
                      <Tooltip cursor={{ fill: "#fafafa" }} contentStyle={{ borderRadius: 8, border: "1px solid #e4e4e7" }} />
                      <Bar dataKey="pct" radius={[6, 6, 0, 0]}>
                        {areaData.map((d, i) => <Cell key={i} fill={d.pct >= 60 ? "#10b981" : "#f43f5e"} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="bg-white border border-zinc-200 rounded-2xl p-6">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-4">Perfil cognitivo</div>
                <div className="h-56">
                  <ResponsiveContainer>
                    <RadarChart data={profileData}>
                      <PolarGrid stroke="#e4e4e7" />
                      <PolarAngleAxis dataKey="trait" fontSize={9} stroke="#71717a" />
                      <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar dataKey="value" stroke="#09090b" fill="#09090b" fillOpacity={0.15} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="mt-8 flex items-center gap-3">
              <button onClick={() => nav(`/plan/${a.analysis_id}`)} className="pill bg-zinc-950 hover:bg-zinc-800 text-white px-6 py-3 rounded-full text-sm font-medium" data-testid="diag-go-plan">
                Ver plano de estudos
              </button>
              <button onClick={() => nav(`/map/${a.analysis_id}`)} className="pill border border-zinc-200 hover:bg-zinc-50 px-6 py-3 rounded-full text-sm font-medium text-zinc-900" data-testid="diag-go-map">
                Mapa de aprendizagem
              </button>
              <button onClick={() => nav("/dashboard")} className="text-sm text-zinc-500 hover:text-zinc-900 underline" data-testid="diag-go-dash">
                Ir para o painel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
