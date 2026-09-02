import { useCallback, useEffect, useState, useRef } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import EstadoDeErro from "../components/EstadoDeErro";
import { reduzirImagemParaEnvio } from "../lib/imagem";
import { toast } from "sonner";
import { Camera, Keyboard, Loader2, Check } from "lucide-react";

const LETTERS = ["A", "B", "C", "D", "E"];

export default function AnswerInput() {
  const { examId } = useParams();
  const [params] = useSearchParams();
  const language = params.get("lang") || "english";
  const [exam, setExam] = useState(null);
  const [numbers, setNumbers] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erroCarga, setErroCarga] = useState(null);
  const [answers, setAnswers] = useState({}); // number -> letter
  const [mode, setMode] = useState(null);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef();
  const nav = useNavigate();

  // Sem tratamento de erro, uma falha aqui deixava `numbers` vazio e o aluno
  // ainda conseguia escolher "Digitar respostas", ver uma lista vazia e enviar
  // um gabarito em branco.
  const carregar = useCallback(() => {
    setCarregando(true);
    setErroCarga(null);
    api.get(`/exams/${examId}?language=${language}`)
      .then(({ data }) => { setExam(data.exam); setNumbers(data.numbers); })
      .catch((e) => setErroCarga(errMsg(e, "Não foi possível carregar esta prova.")))
      .finally(() => setCarregando(false));
  }, [examId, language]);

  useEffect(() => { carregar(); }, [carregar]);

  const handleFile = async (file) => {
    setOcrBusy(true);
    try {
      // Redimensiona ANTES de enviar: a foto original de um celular moderno
      // vira ~11 MB de base64, que o servidor recusa (413) e que consumiria
      // dados móveis do aluno à toa. O OCR não precisa da resolução cheia.
      const b64 = await reduzirImagemParaEnvio(file);
      const { data } = await api.post("/vision/answer-sheet", { exam_id: examId, image_base64: b64 });
      const map = {};
      data.answers.forEach(a => { map[a.number] = (a.letter || "").toUpperCase(); });
      setAnswers(map);
      toast.success("Cartão-resposta reconhecido. Revise e confirme.");
    } catch (e) {
      toast.error(errMsg(e, "Não conseguimos ler o cartão. Tente outra foto ou preencha manualmente."));
    } finally {
      setOcrBusy(false);
    }
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        exam_id: examId,
        language,
        answers: numbers.map(n => ({ number: n, letter: answers[n] || "" })),
      };
      const { data } = await api.post("/analyses", payload);
      nav(`/analysis/${data.analysis_id}`);
    } catch (e) {
      toast.error(errMsg(e, "Erro ao processar. Tente novamente."));
    } finally { setSubmitting(false); }
  };

  const answeredCount = Object.values(answers).filter(v => LETTERS.includes(v)).length;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-10">
        {carregando && <div className="text-white/60">Carregando prova...</div>}
        {!carregando && erroCarga && (
          <EstadoDeErro mensagem={erroCarga} aoTentarNovamente={carregar} voltarPara="/exams" voltarLabel="Escolher outra prova" />
        )}
        {!carregando && !erroCarga && exam && (
          <div className="mb-8">
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">
              Passo 2 de 3 · {exam.title} · {language === "english" ? "Inglês" : "Espanhol"}
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter text-white" data-testid="answer-title">
              Como você quer registrar suas respostas?
            </h1>
          </div>
        )}

        {!carregando && !erroCarga && !mode && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button onClick={() => setMode("photo")} className="lift card-sapiens text-left rounded-2xl p-8 hover:border-sapiens-accent" data-testid="answer-mode-photo">
              <Camera className="w-6 h-6 text-sapiens-accent" strokeWidth={1.6} />
              <div className="mt-6 font-display font-bold text-xl tracking-tight text-zinc-950">Fotografar cartão</div>
              <div className="mt-2 text-sm text-zinc-500">Nossa IA reconhece suas respostas. Você confirma antes da análise.</div>
            </button>
            <button onClick={() => setMode("manual")} className="lift card-sapiens text-left rounded-2xl p-8 hover:border-sapiens-accent" data-testid="answer-mode-manual">
              <Keyboard className="w-6 h-6 text-sapiens-navy" strokeWidth={1.6} />
              <div className="mt-6 font-display font-bold text-xl tracking-tight text-zinc-950">Digitar respostas</div>
              <div className="mt-2 text-sm text-zinc-500">Marque manualmente cada alternativa. Rápido e preciso.</div>
            </button>
          </div>
        )}

        {mode === "photo" && (
          <div className="mt-6 card-sapiens rounded-2xl p-8">
            <div className="font-display font-bold text-xl text-zinc-950 tracking-tight">Envie a foto do cartão-resposta</div>
            <p className="text-sm text-zinc-500 mt-2">JPEG/PNG. A IA identifica as alternativas marcadas. Você poderá revisar antes da análise.</p>
            <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" capture="environment" className="hidden"
              onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
              data-testid="answer-photo-input" />
            <div className="mt-6 flex items-center gap-3">
              <button onClick={() => fileRef.current?.click()} disabled={ocrBusy}
                className="pill btn-sapiens inline-flex items-center gap-2 disabled:opacity-60 px-5 py-3 rounded-full text-sm font-medium"
                data-testid="answer-photo-upload">
                {ocrBusy ? <><Loader2 className="w-4 h-4 animate-spin" /> Reconhecendo...</> : "Escolher imagem"}
              </button>
              <button onClick={() => setMode("manual")} className="text-sm text-zinc-500 hover:text-zinc-900 underline" data-testid="answer-photo-fallback">
                Preferir digitar manualmente
              </button>
            </div>
          </div>
        )}

        {(mode === "manual" || (mode === "photo" && answeredCount > 0)) && (
          <div className="mt-8">
            <div className="mb-4 flex items-center justify-between">
              <div className="font-mono-alt text-xs uppercase tracking-[0.25em] text-white/50">
                Respondidas {answeredCount}/{numbers.length}
              </div>
              <button onClick={submit} disabled={submitting}
                className="pill btn-sapiens inline-flex items-center gap-2 disabled:opacity-60 px-6 py-3 rounded-full text-sm font-medium"
                data-testid="answer-submit">
                {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Analisando...</> : <><Check className="w-4 h-4" /> Confirmar e analisar</>}
              </button>
            </div>
            <div className="card-sapiens rounded-2xl p-4 md:p-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1">
              {numbers.map((n) => (
                <div key={n} className="flex items-center justify-between border-b border-zinc-100 last:border-0 py-2.5" data-testid={`answer-row-${n}`}>
                  <div className="font-mono-alt text-xs w-10 text-zinc-500">Q{n}</div>
                  <div className="flex items-center gap-1.5">
                    {LETTERS.map(l => {
                      const chosen = answers[n] === l;
                      return (
                        <button key={l}
                          onClick={() => setAnswers(a => ({ ...a, [n]: chosen ? "" : l }))}
                          className={`pill w-8 h-8 rounded-full text-xs font-semibold border transition-colors ${chosen ? "bg-sapiens-accent text-white border-sapiens-accent select-pop" : "border-zinc-200 text-zinc-700 hover:border-sapiens-accent"}`}
                          data-testid={`answer-choice-${n}-${l}`}>
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
