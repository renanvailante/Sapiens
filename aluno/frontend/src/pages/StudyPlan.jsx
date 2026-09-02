
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import EstadoDeErro from "../components/EstadoDeErro";
import { useCarregamento } from "../hooks/useCarregamento";
import { TrendingUp, Clock, ArrowRight, Target } from "lucide-react";

export default function StudyPlan() {
  const { analysisId } = useParams();
  const nav = useNavigate();
  const { dados: a, carregando, erro, recarregar } = useCarregamento(
    async () => (await api.get(`/analyses/${analysisId}`)).data,
    [analysisId],
  );
  if (carregando) return <div><Nav /><div className="p-10 text-white/60">Carregando...</div></div>;
  if (erro || !a) return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-14">
        <EstadoDeErro
          mensagem={erro || "Este plano não existe mais ou o link está incompleto."}
          aoTentarNovamente={recarregar}
          voltarPara="/history"
          voltarLabel="Ver meu histórico"
        />
      </div>
    </div>
  );
  const plan = a.study_plan || [];
  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-4">Recomendações</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="plan-title">
          O que você precisa estudar.
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">Cada lacuna abaixo foi ordenada pelo maior retorno esperado — não por matéria. Foque no que traz mais pontos, no menor tempo.</p>

        {plan.length === 0 ? (
          <div className="mt-10 text-white/60">Ainda não temos recomendações personalizadas. Faça uma prova para desbloquear.</div>
        ) : (
          <div className="mt-10 space-y-3">
            {plan.map((item, i) => (
              <div key={i} className="lift card-sapiens rounded-2xl p-6" data-testid={`plan-item-${i}`}>
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 bg-sapiens-accentSoft text-sapiens-accentDeep">
                    <Target className="w-4 h-4" strokeWidth={2} />
                  </div>
                  <div className="flex-1">
                    <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-sapiens-accentDeep mb-1">
                      {i === 0 ? "Maior lacuna encontrada" : "O Sapiens encontrou uma lacuna"}
                    </div>
                    <div className="font-display font-bold text-xl text-zinc-950 tracking-tight">{item.topic}</div>
                    <div className="mt-2 text-sm text-zinc-600 leading-relaxed">{item.why}</div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <span className="inline-flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full font-mono-alt text-xs">
                        <TrendingUp className="w-3 h-3" /> +{item.impact_points || item.impact || 0} pts
                      </span>
                      <span className="inline-flex items-center gap-1.5 text-zinc-600 bg-zinc-100 px-2.5 py-1 rounded-full font-mono-alt text-xs">
                        <Clock className="w-3 h-3" /> {item.hours || 2}h
                      </span>
                      <button
                        onClick={() => nav("/exams")}
                        className="pill btn-sapiens ml-auto inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-medium"
                        data-testid={`plan-cta-${i}`}
                      >
                        Treinar agora <ArrowRight className="w-3.5 h-3.5" />
                      </button>
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
