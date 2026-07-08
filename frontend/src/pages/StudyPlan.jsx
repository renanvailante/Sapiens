import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { TrendingUp, Clock } from "lucide-react";

export default function StudyPlan() {
  const { analysisId } = useParams();
  const [a, setA] = useState(null);
  useEffect(() => { api.get(`/analyses/${analysisId}`).then(({ data }) => setA(data)); }, [analysisId]);
  if (!a) return <div><Nav /><div className="p-10 text-zinc-500">Carregando...</div></div>;
  const plan = a.study_plan || [];
  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-4">Plano de estudos</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="plan-title">
          O que estudar primeiro.
        </h1>
        <p className="mt-3 text-zinc-500 max-w-lg">Ordenamos pelo maior retorno esperado — não por matéria. Foque no que traz mais pontos, no menor tempo.</p>

        {plan.length === 0 ? (
          <div className="mt-10 text-zinc-500">Ainda não temos um plano personalizado. Faça uma prova para desbloquear.</div>
        ) : (
          <div className="mt-10 space-y-3">
            {plan.map((item, i) => (
              <div key={i} className="lift bg-white border border-zinc-200 rounded-2xl p-6" data-testid={`plan-item-${i}`}>
                <div className="flex items-start gap-4">
                  <div className="font-display font-extrabold text-3xl text-zinc-300 tracking-tighter w-10">{String(i + 1).padStart(2, "0")}</div>
                  <div className="flex-1">
                    <div className="font-display font-bold text-xl text-zinc-950 tracking-tight">{item.topic}</div>
                    <div className="mt-2 text-sm text-zinc-600 leading-relaxed">{item.why}</div>
                    <div className="mt-4 flex items-center gap-4 text-xs">
                      <span className="inline-flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full font-mono-alt">
                        <TrendingUp className="w-3 h-3" /> +{item.impact_points || item.impact || 0} pts
                      </span>
                      <span className="inline-flex items-center gap-1.5 text-zinc-600 bg-zinc-100 px-2.5 py-1 rounded-full font-mono-alt">
                        <Clock className="w-3 h-3" /> {item.hours || 2}h
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
