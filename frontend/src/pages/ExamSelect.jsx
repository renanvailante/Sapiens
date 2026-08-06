import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight, Check, X, RotateCw, Sparkles } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";

const APP_VERSION = "sapiens-web-1.0";

// ---------------- Fluxo principal: questões auditadas do Firestore ----------------
function QuestionRunner({ onExit }) {
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null); // { acertou, correta }
  const [submitting, setSubmitting] = useState(false);
  const [answered, setAnswered] = useState(0);
  const startRef = useRef(Date.now());
  const changesRef = useRef(0);

  useEffect(() => {
    let ativo = true;
    api.get("/questoes?limit=100")
      .then(({ data }) => { if (ativo) setItens(data.items || []); })
      .catch((e) => { if (ativo) setErro(e?.message || "Falha ao carregar"); })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, []);

  const item = itens[idx];
  const q = item?.questao || {};
  const fonte = item?.fonte || {};
  const alternativas = Array.isArray(q.alternativas) ? q.alternativas : [];

  const pick = (letra) => {
    if (result) return;
    if (selected !== null && selected !== letra) changesRef.current += 1;
    setSelected(letra);
  };

  const responder = async () => {
    if (!selected || submitting || !item) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/firestore/students/me/answer", {
        item_id: item.item_id,
        alternativa_escolhida: selected,
        tempo_resposta_segundos: Math.round((Date.now() - startRef.current) / 1000),
        numero_tentativas: 1,
        mudou_resposta: changesRef.current > 0,
        contexto_tipo: "pratica_questoes",
        prova_id: fonte.prova || null,
        dispositivo: "web",
        versao_aplicacao: APP_VERSION,
      });
      setResult(data);
      setAnswered((n) => n + 1);
    } catch (e) {
      setErro(e?.response?.data?.detail || "Não foi possível registrar a resposta.");
    } finally {
      setSubmitting(false);
    }
  };

  const proxima = () => {
    setSelected(null);
    setResult(null);
    changesRef.current = 0;
    startRef.current = Date.now();
    setIdx((i) => i + 1);
  };

  if (loading) return <div className="py-24 text-center text-zinc-500">Carregando questões…</div>;
  if (erro && itens.length === 0)
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700">Erro: {erro}</div>;
  if (itens.length === 0)
    return (
      <div className="bg-white border border-zinc-200 rounded-2xl p-10 text-center">
        <div className="font-display text-2xl font-bold text-zinc-950">Nenhuma questão disponível ainda.</div>
        <p className="mt-2 text-zinc-500">Peça a um admin para sincronizar o Firestore no painel administrativo.</p>
      </div>
    );

  if (idx >= itens.length)
    return (
      <div className="bg-white border border-zinc-200 rounded-2xl p-10 text-center">
        <div className="font-display text-2xl font-bold text-zinc-950">Você concluiu todas as questões! 🎉</div>
        <p className="mt-2 text-zinc-500">Respostas registradas: {answered}.</p>
        <button onClick={onExit} className="pill inline-flex items-center gap-2 mt-6 bg-zinc-950 hover:bg-zinc-800 text-white px-5 py-3 rounded-full text-sm font-medium">
          Voltar
        </button>
      </div>
    );

  const tags = [fonte.disciplina, fonte.ano, fonte.prova].filter(Boolean);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div className="font-mono-alt text-xs uppercase tracking-[0.25em] text-zinc-500">
          Questão {idx + 1} de {itens.length}
        </div>
        <button onClick={onExit} className="text-sm text-zinc-500 underline hover:text-zinc-900">Sair</button>
      </div>

      <article className="bg-white border border-zinc-200 rounded-2xl p-6 md:p-8">
        <div className="mb-4 flex flex-wrap gap-2">
          {tags.map((t, i) => (
            <span key={i} className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600">{t}</span>
          ))}
        </div>

        <p className="whitespace-pre-line text-[15px] leading-relaxed text-zinc-800">
          {q.enunciado || "(Sem enunciado)"}
        </p>

        <div className="mt-6 grid gap-2">
          {alternativas.map((alt) => {
            const letra = alt.letra;
            const isSelected = selected === letra;
            const isCorrect = result && letra === result.correta;
            const isWrongChoice = result && isSelected && !result.acertou;
            let cls = "border-zinc-200 bg-white hover:border-indigo-300";
            if (isCorrect) cls = "border-emerald-400 bg-emerald-50";
            else if (isWrongChoice) cls = "border-rose-400 bg-rose-50";
            else if (isSelected) cls = "border-indigo-500 bg-indigo-50";
            return (
              <button
                key={letra}
                onClick={() => pick(letra)}
                disabled={!!result}
                data-testid={`alt-${letra}`}
                className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition ${cls}`}
              >
                <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  isCorrect ? "bg-emerald-500 text-white" : isWrongChoice ? "bg-rose-500 text-white" : isSelected ? "bg-indigo-600 text-white" : "bg-zinc-100 text-zinc-600"
                }`}>
                  {isCorrect ? <Check className="w-4 h-4" /> : isWrongChoice ? <X className="w-4 h-4" /> : letra}
                </span>
                <span className="text-zinc-700">{alt.texto}</span>
              </button>
            );
          })}
        </div>

        {result && (
          <div className={`mt-5 rounded-xl px-4 py-4 ${result.acertou ? "bg-emerald-50" : "bg-rose-50"}`} data-testid="result-banner">
            <div className={`text-sm font-bold ${result.acertou ? "text-emerald-700" : "text-rose-700"}`}>
              {result.feedback?.titulo || (result.acertou ? "Você acertou!" : `Resposta incorreta. Correta: ${result.correta}.`)}
              {!result.acertou && <span className="ml-1 font-normal">(correta: {result.correta})</span>}
            </div>
            {(result.feedback?.mensagens || []).map((m, i) => (
              <p key={i} className={`mt-2 text-sm leading-relaxed ${result.acertou ? "text-emerald-800" : "text-rose-800"}`}>{m}</p>
            ))}
          </div>
        )}

        <div className="mt-6 flex justify-end">
          {!result ? (
            <button
              onClick={responder}
              disabled={!selected || submitting}
              data-testid="btn-responder"
              className="pill inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 disabled:opacity-40 text-white px-6 py-3 rounded-full text-sm font-medium"
            >
              {submitting ? "Registrando…" : "Responder"}
            </button>
          ) : (
            <button onClick={proxima} data-testid="btn-proxima" className="pill inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 text-white px-6 py-3 rounded-full text-sm font-medium">
              {idx + 1 < itens.length ? "Próxima questão" : "Concluir"} <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </article>
    </div>
  );
}

// ---------------- Secundário: praticar por ano (ENEM) — mantido como estava ----------------
function ExamsByYear() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/exams").then(({ data }) => { setExams(data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const grouped = exams.reduce((acc, e) => { (acc[e.year] = acc[e.year] || []).push(e); return acc; }, {});
  const years = Object.keys(grouped).sort((a, b) => Number(b) - Number(a));

  const goWithLanguage = (lang) => { nav(`/exam/${selected.exam_id}?lang=${lang}`); setSelected(null); };

  if (loading) return <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <div key={i} className="animate-pulse h-32 bg-zinc-100 rounded-2xl" />)}</div>;
  if (years.length === 0)
    return <div className="text-sm text-zinc-500">Nenhum gabarito importado ainda. <Link to="/admin" className="underline hover:text-zinc-900">Abrir painel admin</Link>.</div>;

  return (
    <div className="space-y-8">
      {years.map(y => (
        <div key={y}>
          <div className="mb-3 flex items-baseline gap-3">
            <div className="font-display font-bold text-xl text-zinc-950">ENEM {y}</div>
            <div className="text-xs text-zinc-500 font-mono-alt">{grouped[y].length} caderno(s)</div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {grouped[y].map(e => (
              <button key={e.exam_id} onClick={() => setSelected(e)} className="lift text-left bg-white border border-zinc-200 rounded-2xl p-6 hover:border-zinc-900" data-testid={`exam-card-${e.exam_id}`}>
                <div className="flex items-center justify-between">
                  <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Dia {e.day} · {e.color}</div>
                  <div className="text-xs text-zinc-400">{e.total_questions}q</div>
                </div>
                <div className="mt-4 font-display font-bold text-lg tracking-tight text-zinc-950">{e.title}</div>
                <div className="mt-2 text-xs text-zinc-500">
                  {e.has_english && <span className="mr-2">EN</span>}
                  {e.has_spanish && <span>ES</span>}
                </div>
                <div className="mt-6 flex items-center gap-2 text-sm text-zinc-900 font-medium">Escolher <ArrowRight className="w-4 h-4" /></div>
              </button>
            ))}
          </div>
        </div>
      ))}

      <Dialog open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogContent className="rounded-2xl">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight" data-testid="lang-dialog-title">Qual idioma você fez?</DialogTitle>
            <p className="text-sm text-zinc-500">Apenas as questões 1-5 mudam entre inglês e espanhol.</p>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3 mt-2">
            <button disabled={!selected?.has_english} onClick={() => goWithLanguage("english")} className="pill p-6 rounded-2xl border border-zinc-200 hover:border-zinc-900 disabled:opacity-40 disabled:cursor-not-allowed text-left" data-testid="lang-english">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500">Idioma</div>
              <div className="mt-2 font-display font-bold text-xl">Inglês</div>
            </button>
            <button disabled={!selected?.has_spanish} onClick={() => goWithLanguage("spanish")} className="pill p-6 rounded-2xl border border-zinc-200 hover:border-zinc-900 disabled:opacity-40 disabled:cursor-not-allowed text-left" data-testid="lang-spanish">
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

export default function ExamSelect() {
  const [mode, setMode] = useState("hub"); // 'hub' | 'practice'

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-14">
        {mode === "practice" ? (
          <QuestionRunner onExit={() => setMode("hub")} />
        ) : (
          <>
            <div className="mb-10">
              <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Provas</div>
              <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="exam-select-title">
                Pratique questões
              </h1>
              <p className="mt-3 text-zinc-500 max-w-lg">Questões auditadas, uma de cada vez. Suas respostas são registradas para revelar seus padrões cognitivos.</p>
            </div>

            {/* Principal: fluxo de questões do Firestore */}
            <button
              onClick={() => setMode("practice")}
              data-testid="start-practice"
              className="lift w-full text-left bg-zinc-950 text-white rounded-3xl p-8 flex items-center gap-5 hover:bg-zinc-800"
            >
              <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center shrink-0">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="font-display font-extrabold text-2xl tracking-tight">Começar prática de questões</div>
                <div className="mt-1 text-sm text-white/70">Fluxo questão por questão · feedback imediato de certo/errado</div>
              </div>
              <ArrowRight className="w-6 h-6" />
            </button>

            {/* Secundário: praticar por ano (ENEM) */}
            <div className="mt-14">
              <div className="flex items-center gap-3 mb-1">
                <RotateCw className="w-4 h-4 text-zinc-400" />
                <div className="font-mono-alt text-xs uppercase tracking-[0.3em] text-zinc-500">Opção secundária</div>
              </div>
              <h2 className="font-display text-2xl font-bold tracking-tight text-zinc-950">Praticar por ano (ENEM)</h2>
              <p className="mt-2 mb-6 text-sm text-zinc-500">Provas oficiais completas por edição do ENEM.</p>
              <ExamsByYear />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
