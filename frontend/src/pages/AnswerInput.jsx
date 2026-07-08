import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import { Camera, Keyboard, Loader2, Check } from "lucide-react";

const LETTERS = ["A", "B", "C", "D", "E"];

export default function AnswerInput() {
  const { examId } = useParams();
  const [exam, setExam] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({}); // question_id -> letter
  const [mode, setMode] = useState(null); // 'manual' | 'photo'
  const [ocrBusy, setOcrBusy] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef();
  const nav = useNavigate();

  useEffect(() => {
    api.get(`/exams/${examId}`).then(({ data }) => {
      setExam(data.exam);
      setQuestions(data.questions);
    });
  }, [examId]);

  const handleFile = async (file) => {
    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = String(reader.result || "");
      setOcrBusy(true);
      try {
        const { data } = await api.post("/vision/answer-sheet", { exam_id: examId, image_base64: b64 });
        const map = {};
        data.answers.forEach(a => {
          const q = questions.find(q => q.number === a.number);
          if (q) map[q.question_id] = a.letter || "";
        });
        setAnswers(map);
        toast.success("Cartão-resposta reconhecido. Revise e confirme.");
      } catch (e) {
        toast.error("Não conseguimos ler o cartão. Tente novamente ou preencha manualmente.");
      } finally {
        setOcrBusy(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        exam_id: examId,
        answers: questions.map(q => ({ question_id: q.question_id, letter: answers[q.question_id] || "" })),
      };
      const { data } = await api.post("/analyses", payload);
      nav(`/analysis/${data.analysis_id}`);
    } catch (e) {
      toast.error("Erro ao processar. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  };

  const answeredCount = Object.values(answers).filter(v => LETTERS.includes(v)).length;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-10">
        {exam && (
          <div className="mb-8">
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Passo 2 de 3 · {exam.title}</div>
            <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter text-zinc-950" data-testid="answer-title">
              Como você quer registrar suas respostas?
            </h1>
          </div>
        )}

        {!mode && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => setMode("photo")}
              className="lift text-left bg-white border border-zinc-200 rounded-2xl p-8 hover:border-zinc-900"
              data-testid="answer-mode-photo"
            >
              <Camera className="w-6 h-6 text-emerald-500" strokeWidth={1.6} />
              <div className="mt-6 font-display font-bold text-xl tracking-tight text-zinc-950">Fotografar cartão</div>
              <div className="mt-2 text-sm text-zinc-500">Nossa IA reconhece suas respostas. Você confirma antes da análise.</div>
            </button>
            <button
              onClick={() => setMode("manual")}
              className="lift text-left bg-white border border-zinc-200 rounded-2xl p-8 hover:border-zinc-900"
              data-testid="answer-mode-manual"
            >
              <Keyboard className="w-6 h-6 text-zinc-900" strokeWidth={1.6} />
              <div className="mt-6 font-display font-bold text-xl tracking-tight text-zinc-950">Digitar respostas</div>
              <div className="mt-2 text-sm text-zinc-500">Marque manualmente cada alternativa. Rápido e preciso.</div>
            </button>
          </div>
        )}

        {mode === "photo" && (
          <div className="mt-6 bg-white border border-zinc-200 rounded-2xl p-8">
            <div className="font-display font-bold text-xl text-zinc-950 tracking-tight">Envie a foto do cartão-resposta</div>
            <p className="text-sm text-zinc-500 mt-2">JPEG/PNG. A IA identifica as alternativas marcadas. Você poderá revisar antes da análise.</p>
            <input
              ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
              onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
              data-testid="answer-photo-input"
            />
            <div className="mt-6 flex items-center gap-3">
              <button
                onClick={() => fileRef.current?.click()}
                disabled={ocrBusy}
                className="pill inline-flex items-center gap-2 bg-zinc-950 hover:bg-zinc-800 disabled:opacity-60 text-white px-5 py-3 rounded-full text-sm font-medium"
                data-testid="answer-photo-upload"
              >
                {ocrBusy ? <><Loader2 className="w-4 h-4 animate-spin" /> Reconhecendo...</> : "Escolher imagem"}
              </button>
              <button
                onClick={() => setMode("manual")}
                className="text-sm text-zinc-500 hover:text-zinc-900 underline"
                data-testid="answer-photo-fallback"
              >
                Preferir digitar manualmente
              </button>
            </div>
          </div>
        )}

        {(mode === "manual" || (mode === "photo" && answeredCount > 0)) && (
          <div className="mt-8">
            <div className="mb-4 flex items-center justify-between">
              <div className="font-mono-alt text-xs uppercase tracking-[0.25em] text-zinc-500">
                Respondidas {answeredCount}/{questions.length}
              </div>
              <button
                onClick={submit} disabled={submitting}
                className="pill inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-60 text-white px-6 py-3 rounded-full text-sm font-medium"
                data-testid="answer-submit"
              >
                {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Analisando...</> : <><Check className="w-4 h-4" /> Confirmar e analisar</>}
              </button>
            </div>
            <div className="bg-white border border-zinc-200 rounded-2xl p-6 grid grid-cols-1 gap-3">
              {questions.map((q) => (
                <div key={q.question_id} className="flex items-center justify-between border-b border-zinc-100 last:border-0 py-3" data-testid={`answer-row-${q.number}`}>
                  <div className="flex items-center gap-3">
                    <div className="font-mono-alt text-xs w-8 text-zinc-500">Q{q.number}</div>
                    <div className="text-xs text-zinc-400 uppercase tracking-wider">{q.area} · {q.topic}</div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {LETTERS.map(l => {
                      const chosen = answers[q.question_id] === l;
                      return (
                        <button
                          key={l}
                          onClick={() => setAnswers(a => ({ ...a, [q.question_id]: chosen ? "" : l }))}
                          className={`pill w-9 h-9 rounded-full text-sm font-medium border ${chosen ? "bg-zinc-950 text-white border-zinc-950" : "border-zinc-200 text-zinc-700 hover:border-zinc-900"}`}
                          data-testid={`answer-choice-${q.number}-${l}`}
                        >
                          {l}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
