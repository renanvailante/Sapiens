import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight } from "lucide-react";

export default function ExamSelect() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/exams").then(({ data }) => { setExams(data); setLoading(false); });
  }, []);

  // group by year
  const grouped = exams.reduce((acc, e) => {
    (acc[e.year] = acc[e.year] || []).push(e);
    return acc;
  }, {});
  const years = Object.keys(grouped).sort((a, b) => Number(b) - Number(a));

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-14">
        <div className="mb-10">
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Passo 1 de 3</div>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="exam-select-title">
            Escolha uma prova
          </h1>
          <p className="mt-3 text-zinc-500 max-w-lg">Provas oficiais do ENEM disponíveis no banco. Novas provas podem ser importadas pelo painel admin.</p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="animate-pulse h-32 bg-zinc-100 rounded-2xl" />
            ))}
          </div>
        ) : years.length === 0 ? (
          <div className="text-zinc-500">Nenhuma prova disponível.</div>
        ) : (
          <div className="space-y-10">
            {years.map(y => (
              <div key={y}>
                <div className="mb-4 flex items-baseline gap-3">
                  <div className="font-display font-bold text-2xl text-zinc-950">ENEM {y}</div>
                  <div className="text-xs text-zinc-500 font-mono-alt">{grouped[y].length} caderno(s)</div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {grouped[y].map(e => (
                    <button
                      key={e.exam_id}
                      onClick={() => nav(`/exam/${e.exam_id}`)}
                      className="lift text-left bg-white border border-zinc-200 rounded-2xl p-6 hover:border-zinc-900"
                      data-testid={`exam-card-${e.exam_id}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">{e.color}</div>
                        <div className="text-xs text-zinc-400">{e.total_questions} questões</div>
                      </div>
                      <div className="mt-4 font-display font-bold text-lg tracking-tight text-zinc-950">{e.title}</div>
                      <div className="mt-1 text-sm text-zinc-500">{e.area}</div>
                      <div className="mt-6 flex items-center gap-2 text-sm text-zinc-900 font-medium">
                        Começar <ArrowRight className="w-4 h-4" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-14 text-sm text-zinc-500">
          <Link to="/admin" className="underline hover:text-zinc-900" data-testid="exam-select-admin-link">Painel admin — importar novas provas</Link>
        </div>
      </div>
    </div>
  );
}
