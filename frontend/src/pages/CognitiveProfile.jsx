import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { Brain, AlertCircle } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell,
} from "recharts";

export default function CognitiveProfile() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/cognitive-profile").then(({ data }) => { setData(data); setLoading(false); });
  }, []);

  if (loading) return <div><Nav /><div className="p-10 text-zinc-500">Compondo perfil...</div></div>;

  const processes = data?.processes || [];
  const errorTypes = data?.error_types || [];
  const misconceptions = data?.misconceptions || [];
  const coverage = data?.coverage ?? 0;

  const chart = processes.map(p => ({ name: p.cognitive_process_id, acc: p.weighted_accuracy || p.accuracy }));

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Perfil cognitivo</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="cp-title">
          Como você pensa.
        </h1>
        <p className="mt-3 text-zinc-500 max-w-lg">
          Este painel usa anotações cognitivas oficiais (não inferidas pelo Sapiens) para mostrar sua performance por processo cognitivo, tipos de erro recorrentes e misconceptions.
        </p>

        {processes.length === 0 ? (
          <div className="mt-10 bg-white border border-zinc-200 rounded-2xl p-10 text-center">
            <Brain className="w-8 h-8 text-zinc-400 mx-auto" strokeWidth={1.4} />
            <div className="mt-4 font-display font-bold text-2xl text-zinc-950">Ainda sem cobertura cognitiva.</div>
            <p className="mt-2 text-zinc-500 text-sm max-w-md mx-auto">
              O painel só ativa quando as questões respondidas por você têm anotações cognitivas no banco. Peça ao admin para importar as anotações via <Link to="/admin/annotations" className="underline">painel de anotações</Link>.
            </p>
          </div>
        ) : (
          <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-3 bg-zinc-950 text-white rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Cobertura de anotações</div>
                <div className="mt-2 font-display text-3xl font-bold tracking-tight" data-testid="cp-coverage">
                  {coverage}%
                </div>
              </div>
              <div className="text-sm text-zinc-400 max-w-md">
                {data.matched_questions} de {data.total_questions} questões respondidas têm anotação cognitiva. Quanto maior a cobertura, mais precisa a inferência de perfil.
              </div>
            </div>

            <div className="md:col-span-2 bg-white border border-zinc-200 rounded-2xl p-6">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-4">Acurácia por processo cognitivo (ponderada por peso de ativação)</div>
              <div className="h-80">
                <ResponsiveContainer>
                  <BarChart data={chart} layout="vertical" margin={{ left: 60 }}>
                    <XAxis type="number" domain={[0, 100]} stroke="#a1a1aa" fontSize={11} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" stroke="#71717a" fontSize={11} width={110} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e4e4e7" }} />
                    <Bar dataKey="acc" radius={[0, 6, 6, 0]}>
                      {chart.map((d, i) => <Cell key={i} fill={d.acc >= 60 ? "#10b981" : d.acc >= 40 ? "#f59e0b" : "#f43f5e"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white border border-zinc-200 rounded-2xl p-6">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-3">Detalhamento</div>
              <div className="space-y-3">
                {processes.slice(0, 8).map(p => (
                  <div key={p.cognitive_process_id} className="border-b border-zinc-100 last:border-0 pb-2" data-testid={`cp-process-${p.cognitive_process_id}`}>
                    <div className="flex items-center justify-between">
                      <div className="font-mono-alt text-xs text-zinc-900">{p.cognitive_process_id}</div>
                      <div className="text-xs font-mono-alt text-zinc-500">{p.correct}/{p.encountered}</div>
                    </div>
                    <div className="mt-1 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                      <div className="h-full bg-zinc-900" style={{ width: `${p.weighted_accuracy || p.accuracy}%` }} />
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-zinc-500 font-mono-alt uppercase tracking-wider">
                      dif. média local: {p.avg_local_difficulty} · papel:
                      {Object.entries(p.papel_distribution).map(([k, v]) => <span key={k} className="px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-700 normal-case tracking-normal font-normal">{k} ×{v}</span>)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {errorTypes.length > 0 && (
              <div className="md:col-span-2 bg-rose-50 border border-rose-100 rounded-2xl p-6">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-rose-700 mb-3 flex items-center gap-2">
                  <AlertCircle className="w-3.5 h-3.5" /> Tipos de erro frequentes
                </div>
                <div className="flex flex-wrap gap-2">
                  {errorTypes.map(e => (
                    <span key={e.error_type_id} className="text-sm bg-white px-3 py-1.5 rounded-full border border-rose-100" data-testid={`cp-err-${e.error_type_id}`}>
                      #{e.error_type_id} · <span className="font-mono-alt text-xs text-rose-600">{e.count}×</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {misconceptions.length > 0 && (
              <div className="bg-amber-50 border border-amber-100 rounded-2xl p-6">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-amber-700 mb-3">Misconceptions detectadas</div>
                <ul className="space-y-1.5 text-sm text-zinc-800">
                  {misconceptions.map((m, i) => <li key={i}>· {m.label} <span className="text-amber-700 font-mono-alt text-xs">({m.count}×)</span></li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
