import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";

export default function ExamSelect() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/exams").then(({ data }) => { setExams(data); setLoading(false); });
  }, []);

  const grouped = exams.reduce((acc, e) => { (acc[e.year] = acc[e.year] || []).push(e); return acc; }, {});
  const years = Object.keys(grouped).sort((a, b) => Number(b) - Number(a));

  const goWithLanguage = (lang) => {
    nav(`/exam/${selected.exam_id}?lang=${lang}`);
    setSelected(null);
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-14">
        <div className="mb-10">
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Passo 1 de 3</div>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="exam-select-title">
            Escolha uma prova
          </h1>
          <p className="mt-3 text-zinc-500 max-w-lg">Provas oficiais do ENEM. Novos gabaritos podem ser importados pelo painel admin — basta colar do site do INEP.</p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(4)].map((_, i) => <div key={i} className="animate-pulse h-32 bg-zinc-100 rounded-2xl" />)}
          </div>
        ) : years.length === 0 ? (
          <div className="bg-white border border-zinc-200 rounded-2xl p-10 text-center">
            <div className="font-display text-2xl font-bold text-zinc-950">Nenhum gabarito importado ainda.</div>
            <p className="mt-2 text-zinc-500">Vá ao painel admin e cole um gabarito oficial do INEP.</p>
            <Link to="/admin" className="pill inline-flex items-center gap-2 mt-6 bg-zinc-950 hover:bg-zinc-800 text-white px-5 py-3 rounded-full text-sm font-medium" data-testid="exam-select-goto-admin">
              Abrir painel admin
            </Link>
          </div>
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
                      onClick={() => setSelected(e)}
                      className="lift text-left bg-white border border-zinc-200 rounded-2xl p-6 hover:border-zinc-900"
                      data-testid={`exam-card-${e.exam_id}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Dia {e.day} · {e.color}</div>
                        <div className="text-xs text-zinc-400">{e.total_questions}q</div>
                      </div>
                      <div className="mt-4 font-display font-bold text-lg tracking-tight text-zinc-950">{e.title}</div>
                      <div className="mt-2 text-xs text-zinc-500">
                        {e.has_english && <span className="mr-2">EN</span>}
                        {e.has_spanish && <span>ES</span>}
                      </div>
                      <div className="mt-6 flex items-center gap-2 text-sm text-zinc-900 font-medium">
                        Escolher <ArrowRight className="w-4 h-4" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-14 text-sm text-zinc-500">
          <Link to="/admin" className="underline hover:text-zinc-900" data-testid="exam-select-admin-link">Painel admin — importar novos gabaritos</Link>
        </div>
      </div>

      <Dialog open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogContent className="rounded-2xl">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight" data-testid="lang-dialog-title">
              Qual idioma você fez?
            </DialogTitle>
            <p className="text-sm text-zinc-500">Apenas as questões 1-5 mudam entre inglês e espanhol.</p>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3 mt-2">
            <button
              disabled={!selected?.has_english}
              onClick={() => goWithLanguage("english")}
              className="pill p-6 rounded-2xl border border-zinc-200 hover:border-zinc-900 disabled:opacity-40 disabled:cursor-not-allowed text-left"
              data-testid="lang-english"
            >
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500">Idioma</div>
              <div className="mt-2 font-display font-bold text-xl">Inglês</div>
            </button>
            <button
              disabled={!selected?.has_spanish}
              onClick={() => goWithLanguage("spanish")}
              className="pill p-6 rounded-2xl border border-zinc-200 hover:border-zinc-900 disabled:opacity-40 disabled:cursor-not-allowed text-left"
              data-testid="lang-spanish"
            >
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500">Idioma</div>
              <div className="mt-2 font-display font-bold text-xl">Espanhol</div>
            </button>
          </div>
          <DialogFooter />
        </DialogContent>
      </Dialog>
    </div>
  );
}
