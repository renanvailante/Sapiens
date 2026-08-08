import { useState } from "react";
import { toast } from "sonner";
import {
  Upload,
  FileText,
  Image as ImageIcon,
  X,
  Sparkles,
  Package,
  BookOpen,
} from "lucide-react";
import api from "@/lib/api";
import { runInParallel } from "@/lib/parallel";
import PipelineResult from "@/components/PipelineResult";
import BatchResults from "@/components/BatchResults";
import BookResults from "@/components/BookResults";

const CONCURRENCY = 3;

const MODES = [
  {
    id: "single",
    label: "Uma questão",
    icon: FileText,
    hint: "Todos os arquivos são UMA questão (PDF + figuras).",
  },
  {
    id: "batch",
    label: "Lote",
    icon: Package,
    hint: `Cada arquivo é UMA questão. Até ${CONCURRENCY} em paralelo.`,
  },
  {
    id: "book",
    label: "Caderno / prova",
    icon: BookOpen,
    hint: "Um PDF com várias questões. O motor separa e processa cada uma.",
  },
];

export default function PipelineGenerator() {
  const [mode, setMode] = useState("single");
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [batch, setBatch] = useState(null);
  const [book, setBook] = useState(null); // {book_id, files, manifest, items}

  const onSelect = (list) => {
    const arr = Array.from(list || []).filter((f) => {
      const ok = /\.(pdf|png|jpe?g|webp)$/i.test(f.name);
      if (!ok) toast.error(`Formato inválido: ${f.name}`);
      return ok;
    });
    setFiles((prev) => [...prev, ...arr]);
  };

  const onDrop = (e) => {
    e.preventDefault();
    onSelect(e.dataTransfer.files);
  };

  const removeAt = (i) => setFiles((prev) => prev.filter((_, idx) => idx !== i));

  const generateSingle = async () => {
    setBusy(true);
    setResult(null);
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    try {
      const r = await api.post("/pipeline/generate", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300000,
      });
      setResult(r.data);
      toast.success("Pipeline cognitivo gerado.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao gerar pipeline.");
    } finally {
      setBusy(false);
    }
  };

  const generateBatch = async () => {
    setBusy(true);
    const initial = files.map((f) => ({
      key: `${f.name}-${f.lastModified}-${f.size}`,
      filename: f.name,
      status: "pending",
      result: null,
      error: null,
    }));
    setBatch(initial);
    const current = [...initial];

    const tasks = files.map((f, i) => async () => {
      current[i] = { ...current[i], status: "processing" };
      setBatch([...current]);
      const fd = new FormData();
      fd.append("files", f);
      try {
        const r = await api.post("/pipeline/generate", fd, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 300000,
        });
        current[i] = { ...current[i], status: "done", result: r.data };
      } catch (e) {
        current[i] = {
          ...current[i],
          status: "error",
          error: e?.response?.data?.detail || e.message || "Falha",
        };
      }
      setBatch([...current]);
      return current[i];
    });

    await runInParallel(tasks, CONCURRENCY);

    const okCount = current.filter((r) => r.status === "done").length;
    const errCount = current.filter((r) => r.status === "error").length;
    if (errCount === 0) toast.success(`${okCount} questões processadas.`);
    else toast.warning(`${okCount} ok · ${errCount} com erro.`);
    setBusy(false);
  };

  const uploadBook = async () => {
    setBusy(true);
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    try {
      toast.info("Enviando caderno para o servidor…");
      const up = await api.post("/book/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 180000,
      });
      toast.info("Identificando questões no caderno…");
      const mf = await api.post(`/book/${up.data.id}/manifest`, null, {
        timeout: 300000,
      });
      const manifest = mf.data.manifest || [];
      if (manifest.length === 0) {
        toast.error("Nenhuma questão detectada no caderno.");
        setBusy(false);
        return;
      }
      setBook({
        book_id: up.data.id,
        files: up.data.files,
        manifest,
        items: manifest.map((q, i) => ({
          key: `${up.data.id}-${q.numero || i}`,
          question_number: String(q.numero || i + 1),
          question_title: q.titulo || "",
          paginas: q.paginas || [],
          disciplina: q.disciplina || null,
          tem_figura: !!q.tem_figura,
          selected: true,
          status: "pending",
          result: null,
          error: null,
        })),
      });
      toast.success(`${manifest.length} questões detectadas.`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao processar caderno.");
    } finally {
      setBusy(false);
    }
  };

  const generate = () => {
    if (files.length === 0) {
      toast.error("Anexe pelo menos um arquivo.");
      return;
    }
    if (mode === "single") return generateSingle();
    if (mode === "batch") return generateBatch();
    if (mode === "book") return uploadBook();
  };

  const reset = () => {
    setResult(null);
    setBatch(null);
    setBook(null);
    setFiles([]);
  };

  return (
    <div className="max-w-7xl px-8 py-10" data-testid="pipeline-generator-page">
      <div className="overline text-muted-foreground">Motor</div>
      <h1 className="text-4xl font-black tracking-tight mt-1">Gerador de Pipeline</h1>
      <p className="mt-3 text-sm text-muted-foreground max-w-2xl">
        Três modos de entrada. Em <b>lote</b> e <b>caderno</b>, até {CONCURRENCY} questões
        são processadas em paralelo mantendo cada JSON vinculado à sua origem.
      </p>

      {!result && !batch && !book && (
        <>
          {/* Mode selector */}
          <div className="mt-8 border border-border bg-white grid grid-cols-1 md:grid-cols-3" data-testid="mode-selector">
            {MODES.map((m) => {
              const Icon = m.icon;
              const active = mode === m.id;
              return (
                <button
                  key={m.id}
                  data-testid={`mode-${m.id}`}
                  onClick={() => setMode(m.id)}
                  className={`text-left px-5 py-4 border-b md:border-b-0 md:border-r last:border-r-0 border-border transition-colors ${
                    active ? "bg-foreground text-white" : "bg-white hover:bg-secondary"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    <span className="font-bold">{m.label}</span>
                  </div>
                  <div className={`mt-1 text-xs ${active ? "text-white/70" : "text-muted-foreground"}`}>
                    {m.hint}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Upload */}
          <div
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            className="mt-6 border-2 border-dashed border-border bg-white p-10 text-center"
            data-testid="dropzone"
          >
            <div className="mx-auto h-12 w-12 flex items-center justify-center border border-border">
              <Upload className="h-5 w-5" />
            </div>
            <div className="mt-4 text-lg font-bold">
              {mode === "batch" && "Arraste várias questões (cada arquivo = 1 questão)"}
              {mode === "book" && "Arraste o PDF do caderno (com todas as questões)"}
              {mode === "single" && "Arraste PDF, PNG ou JPG aqui"}
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              {mode === "batch" && `Cada arquivo será enviado ao motor separadamente (paralelismo ${CONCURRENCY}).`}
              {mode === "book" && "Você pode incluir também imagens complementares. O sistema detecta as questões e processa cada uma individualmente."}
              {mode === "single" && "Ou selecione múltiplos arquivos (a questão pode conter várias figuras)."}
            </div>
            <label className="inline-flex mt-6 cursor-pointer">
              <input
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.webp,image/*,application/pdf"
                className="hidden"
                onChange={(e) => onSelect(e.target.files)}
                data-testid="pipeline-file-input"
              />
              <span className="bg-foreground text-white px-4 py-2.5 text-sm font-medium hover:bg-primary">
                Selecionar arquivos
              </span>
            </label>
          </div>

          {files.length > 0 && (
            <div className="mt-6 border border-border bg-white" data-testid="file-list">
              <div className="px-6 py-3 border-b border-border overline text-muted-foreground">
                {files.length} arquivo(s) selecionado(s)
              </div>
              <ul>
                {files.map((f, i) => {
                  const isImg = f.type.startsWith("image/");
                  return (
                    <li
                      key={`${f.name}-${i}`}
                      className="px-6 py-3 border-b border-border last:border-b-0 flex items-center gap-4"
                    >
                      {isImg ? (
                        <ImageIcon className="h-4 w-4 text-primary" />
                      ) : (
                        <FileText className="h-4 w-4 text-primary" />
                      )}
                      <span className="flex-1 text-sm font-medium truncate">{f.name}</span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {(f.size / 1024).toFixed(1)} KB
                      </span>
                      <button
                        onClick={() => removeAt(i)}
                        className="p-1 hover:bg-secondary"
                        data-testid={`remove-file-${i}`}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <div className="mt-8 flex items-center gap-3">
            <button
              data-testid="generate-pipeline-btn"
              onClick={generate}
              disabled={busy || files.length === 0}
              className="flex items-center gap-2 bg-primary text-white px-6 py-3 text-sm font-bold hover:bg-foreground disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" />
              {busy && "Processando com Gemini 3 Pro…"}
              {!busy && mode === "single" && "Gerar Pipeline"}
              {!busy && mode === "batch" && `Gerar ${files.length || ""} pipeline(s)`}
              {!busy && mode === "book" && "Analisar caderno"}
            </button>
            {busy && (
              <div className="text-xs text-muted-foreground font-mono" data-testid="busy-hint">
                Leitura multimodal em curso · pode levar ~30-60s por questão.
              </div>
            )}
          </div>
        </>
      )}

      {result && (
        <PipelineResult data={result} onReset={reset} onUpdate={setResult} />
      )}

      {batch && (
        <BatchResults
          items={batch}
          busy={busy}
          onReset={reset}
          onItemUpdate={(i, patch) =>
            setBatch((prev) => prev.map((it, idx) => (idx === i ? { ...it, ...patch } : it)))
          }
          onItemRemove={(i) => setBatch((prev) => prev.filter((_, idx) => idx !== i))}
        />
      )}

      {book && (
        <BookResults
          book={book}
          concurrency={CONCURRENCY}
          onReset={reset}
          onUpdate={setBook}
        />
      )}
    </div>
  );
}
