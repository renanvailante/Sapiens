import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft,
  Copy,
  Download,
  Trash2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  Pencil,
  Save,
  X,
  Play,
  BookOpen,
} from "lucide-react";
import api from "@/lib/api";
import { runInParallel } from "@/lib/parallel";
import JsonViewer from "@/components/JsonViewer";

const statusStyles = {
  pending: { color: "#52525B", icon: Loader2, label: "Aguardando", spin: false },
  processing: { color: "#002FA7", icon: Loader2, label: "Processando…", spin: true },
  done: { color: "#059669", icon: CheckCircle2, label: "OK", spin: false },
  error: { color: "#E11D48", icon: AlertCircle, label: "Erro", spin: false },
};

export default function BookResults({ book, concurrency = 3, onReset, onUpdate }) {
  const [phase, setPhase] = useState("manifest"); // manifest | processing | done
  const [expanded, setExpanded] = useState(new Set());
  const [editing, setEditing] = useState(null);
  const [editText, setEditText] = useState("");
  const [busy, setBusy] = useState(false);

  const items = book.items;

  const doneItems = useMemo(
    () => items.map((it, i) => ({ ...it, idx: i })).filter((it) => it.status === "done"),
    [items],
  );

  // Functional updaters — evitam stale-closure em tarefas paralelas
  const setItem = (i, patch) =>
    onUpdate((prev) => ({
      ...prev,
      items: prev.items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)),
    }));

  const removeItem = (i) =>
    onUpdate((prev) => ({ ...prev, items: prev.items.filter((_, idx) => idx !== i) }));

  const toggleSelect = (i) =>
    onUpdate((prev) => ({
      ...prev,
      items: prev.items.map((it, idx) => (idx === i ? { ...it, selected: !it.selected } : it)),
    }));

  const selectAll = (v) =>
    onUpdate((prev) => ({ ...prev, items: prev.items.map((it) => ({ ...it, selected: v })) }));

  const toggleExpand = (idx) =>
    setExpanded((prev) => {
      const s = new Set(prev);
      if (s.has(idx)) s.delete(idx);
      else s.add(idx);
      return s;
    });

  const selectedCount = items.filter((it) => it.selected).length;
  const allSelected = selectedCount === items.length && items.length > 0;

  const processSelected = async () => {
    const targets = items
      .map((it, i) => ({ ...it, i }))
      .filter((it) => it.selected && it.status !== "done");
    if (targets.length === 0) {
      toast.error("Nenhuma questão selecionada para processar.");
      return;
    }
    setBusy(true);
    setPhase("processing");

    const tasks = targets.map((it) => async () => {
      setItem(it.i, { status: "processing", error: null });
      try {
        const r = await api.post(
          `/book/${book.book_id}/process`,
          {
            question_number: it.question_number,
            question_title: it.question_title,
          },
          { timeout: 300000 },
        );
        setItem(it.i, { status: "done", result: r.data, error: null });
      } catch (e) {
        setItem(it.i, {
          status: "error",
          error: e?.response?.data?.detail || e.message || "Falha",
        });
      }
    });

    await runInParallel(tasks, concurrency);
    setBusy(false);
    setPhase("done");
    // Read latest state via functional updater no-op to compute counts
    onUpdate((prev) => {
      const ok = prev.items.filter((it) => it.status === "done").length;
      const err = prev.items.filter((it) => it.status === "error").length;
      if (err === 0) toast.success(`${ok}/${prev.items.length} questões processadas.`);
      else toast.warning(`${ok} ok · ${err} com erro.`);
      return prev;
    });
  };

  const collectSelectedJsons = () =>
    doneItems
      .filter((it) => it.selected)
      .map((it) => ({
        book_id: book.book_id,
        question_number: it.question_number,
        question_title: it.question_title,
        pipeline_id: it.result?.id,
        ontology_version: it.result?.ontology_version,
        pipeline: it.result?.pipeline,
      }));

  const copySelected = async () => {
    const arr = collectSelectedJsons();
    if (arr.length === 0) return toast.error("Nada selecionado para copiar.");
    await navigator.clipboard.writeText(JSON.stringify(arr, null, 2));
    toast.success(`${arr.length} JSON(s) copiado(s).`);
  };

  const exportSelected = () => {
    const arr = collectSelectedJsons();
    if (arr.length === 0) return toast.error("Nada selecionado para exportar.");
    const blob = new Blob([JSON.stringify(arr, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sapiens-caderno-${book.book_id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Arquivo com ${arr.length} JSON(s) baixado.`);
  };

  const retryOne = async (i) => {
    setItem(i, { status: "processing", error: null });
    try {
      const r = await api.post(
        `/book/${book.book_id}/process`,
        {
          question_number: items[i].question_number,
          question_title: items[i].question_title,
        },
        { timeout: 300000 },
      );
      setItem(i, { status: "done", result: r.data, error: null });
      toast.success("Reprocessada.");
    } catch (e) {
      setItem(i, {
        status: "error",
        error: e?.response?.data?.detail || e.message || "Falha",
      });
      toast.error("Falha ao reprocessar.");
    }
  };

  const deleteOne = async (i) => {
    const it = items[i];
    if (!window.confirm(`Excluir a questão nº ${it.question_number}?`)) return;
    if (it.result?.id) {
      try {
        await api.delete(`/pipeline/${it.result.id}`);
      } catch {
        toast.error("Falha ao excluir no servidor.");
        return;
      }
    }
    removeItem(i);
    toast.success("Excluída.");
  };

  const deleteSelected = async () => {
    const chosen = items
      .map((it, i) => ({ ...it, i }))
      .filter((it) => it.selected && it.status === "done");
    if (chosen.length === 0) return toast.error("Nada selecionado.");
    if (!window.confirm(`Excluir ${chosen.length} questão(ões)?`)) return;
    for (const c of chosen) {
      if (c.result?.id) {
        try {
          await api.delete(`/pipeline/${c.result.id}`);
        } catch { /* ignore */ }
      }
    }
    const chosenIdx = new Set(chosen.map((c) => c.i));
    onUpdate((prev) => ({
      ...prev,
      items: prev.items.filter((_, i) => !chosenIdx.has(i)),
    }));
    toast.success(`${chosen.length} excluída(s).`);
  };

  const startEdit = (i) => {
    setEditing(i);
    setEditText(JSON.stringify(items[i].result.pipeline, null, 2));
  };
  const cancelEdit = () => {
    setEditing(null);
    setEditText("");
  };
  const saveEdit = async (i) => {
    try {
      const parsed = JSON.parse(editText);
      const r = await api.put(`/pipeline/${items[i].result.id}`, { pipeline: parsed });
      setItem(i, { result: r.data });
      setEditing(null);
      toast.success("JSON atualizado.");
    } catch (e) {
      toast.error("Falha: " + (e?.response?.data?.detail || e.message));
    }
  };

  const doneCount = doneItems.length;
  const total = items.length;

  return (
    <div className="mt-2 space-y-6" data-testid="book-results">
      <button
        onClick={onReset}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        data-testid="book-new-btn"
      >
        <ArrowLeft className="h-4 w-4" /> Novo caderno
      </button>

      {/* Header */}
      <div className="border border-border bg-white">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <BookOpen className="h-5 w-5 text-primary" />
            <div>
              <div className="overline text-muted-foreground">Caderno</div>
              <div className="mt-1 text-xl font-black">
                {total} questão(ões) detectada(s)
                {phase !== "manifest" && (
                  <span className="ml-3 text-sm font-mono text-muted-foreground">
                    · {doneCount}/{total} processada(s)
                  </span>
                )}
              </div>
              <div className="mt-1 text-xs font-mono text-muted-foreground">
                book_id: {book.book_id}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="flex items-center gap-2 text-sm font-medium cursor-pointer select-none">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={(e) => selectAll(e.target.checked)}
                data-testid="book-select-all"
                className="h-4 w-4 accent-primary"
              />
              Selecionar todos ({selectedCount}/{total})
            </label>
            <button
              onClick={processSelected}
              disabled={busy || selectedCount === 0}
              data-testid="book-process-btn"
              className="flex items-center gap-1.5 bg-primary text-white px-4 py-2 text-xs font-bold hover:bg-foreground disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5" />
              {busy ? "Processando…" : `Processar ${selectedCount}`}
            </button>
            <BulkBtn onClick={copySelected} icon={Copy} label="Copiar JSONs" testId="book-copy" disabled={doneCount === 0} />
            <BulkBtn onClick={exportSelected} icon={Download} label="Exportar JSONs" testId="book-export" disabled={doneCount === 0} />
            <BulkBtn onClick={deleteSelected} icon={Trash2} label="Excluir" testId="book-delete" danger disabled={doneCount === 0} />
          </div>
        </div>
        <div className="h-1 bg-secondary">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${total ? (doneCount / total) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Items */}
      <div className="border border-border bg-white">
        {items.map((item, i) => {
          const style = statusStyles[item.status];
          const Icon = style.icon;
          const isDone = item.status === "done";
          const isErr = item.status === "error";
          const isExp = expanded.has(i);
          const isEditing = editing === i;
          const q = item.result?.pipeline?.questao || {};
          const cls = item.result?.pipeline?.classificacao || {};

          return (
            <div key={item.key} className="border-b border-border last:border-b-0" data-testid={`book-item-${i}`}>
              <div className="px-6 py-4 flex items-center gap-4 flex-wrap">
                <input
                  type="checkbox"
                  checked={item.selected}
                  onChange={() => toggleSelect(i)}
                  data-testid={`book-select-${i}`}
                  className="h-4 w-4 accent-primary"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs px-2 py-0.5 border border-primary text-primary">
                      Q{item.question_number}
                    </span>
                    <span className="font-medium truncate">{item.question_title || "(sem título)"}</span>
                    {item.tem_figura && (
                      <span className="font-mono text-[10px] px-1.5 py-0.5 border border-border text-muted-foreground">
                        c/ figura
                      </span>
                    )}
                    {item.paginas?.length > 0 && (
                      <span className="text-xs text-muted-foreground">· p. {item.paginas.join(", ")}</span>
                    )}
                    {isDone && q.disciplina && (
                      <span className="text-xs text-muted-foreground">· {q.disciplina}</span>
                    )}
                  </div>
                  {item.error && (
                    <div className="mt-1 text-xs text-destructive font-mono">{item.error}</div>
                  )}
                </div>

                <div
                  className="flex items-center gap-1.5 font-mono text-xs px-2 py-1 border"
                  style={{ borderColor: style.color, color: style.color }}
                >
                  <Icon className={`h-3 w-3 ${style.spin ? "animate-spin" : ""}`} />
                  {style.label}
                </div>

                {isErr && (
                  <IconBtn onClick={() => retryOne(i)} icon={Play} label="Repetir" testId={`book-retry-${i}`} />
                )}
                {isDone && (
                  <div className="flex items-center gap-1">
                    <IconBtn onClick={() => toggleExpand(i)} icon={isExp ? ChevronDown : ChevronRight} label={isExp ? "Ocultar" : "Ver JSON"} testId={`book-toggle-${i}`} />
                    <IconBtn onClick={() => startEdit(i)} icon={Pencil} label="Editar" testId={`book-edit-${i}`} />
                    <Link
                      to={`/questoes/${item.result.id}`}
                      className="flex items-center gap-1.5 border border-border bg-white px-3 py-1.5 text-xs font-medium hover:bg-foreground hover:text-white"
                      data-testid={`book-open-${i}`}
                    >
                      <ExternalLink className="h-3.5 w-3.5" /> Abrir
                    </Link>
                    <IconBtn onClick={() => deleteOne(i)} icon={Trash2} label="Excluir" testId={`book-delete-item-${i}`} danger />
                  </div>
                )}
              </div>

              {isDone && isExp && !isEditing && (
                <div className="px-6 pb-6 pt-2 border-t border-border bg-secondary/40">
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
                    <MiniStat label="Resposta" value={q.resposta_correta || "—"} mono />
                    <MiniStat label="Domínios" value={(cls.dominios || []).join(", ") || "—"} mono />
                    <MiniStat label="Processos" value={(cls.processos_cognitivos || []).map((p) => p.id).join(", ") || "—"} mono />
                  </div>
                  <JsonViewer data={item.result.pipeline} testId={`book-json-${i}`} />
                </div>
              )}
              {isDone && isEditing && (
                <div className="px-6 pb-6 pt-2 border-t border-border bg-secondary/40" data-testid={`book-edit-panel-${i}`}>
                  <div className="mb-3 flex items-center justify-between">
                    <div className="overline text-muted-foreground">Editar JSON</div>
                    <div className="flex items-center gap-2">
                      <IconBtn onClick={cancelEdit} icon={X} label="Cancelar" testId={`book-cancel-edit-${i}`} />
                      <button
                        data-testid={`book-save-edit-${i}`}
                        onClick={() => saveEdit(i)}
                        className="flex items-center gap-1.5 bg-primary text-white px-3 py-1.5 text-xs font-bold hover:bg-foreground"
                      >
                        <Save className="h-3 w-3" /> Salvar
                      </button>
                    </div>
                  </div>
                  <textarea
                    data-testid={`book-editor-${i}`}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full h-[400px] font-mono text-[12.5px] bg-white border border-border p-4"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {busy && (
        <div className="text-xs text-muted-foreground font-mono" data-testid="book-busy">
          Processando em paralelo (até {concurrency}) · mantenha esta aba aberta.
        </div>
      )}
    </div>
  );
}

function BulkBtn({ onClick, icon: Icon, label, testId, danger, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className={`flex items-center gap-1.5 border border-border px-3 py-1.5 text-xs font-medium disabled:opacity-40 ${
        danger
          ? "bg-white hover:bg-destructive hover:text-white hover:border-destructive"
          : "bg-white hover:bg-foreground hover:text-white"
      }`}
    >
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  );
}

function IconBtn({ onClick, icon: Icon, label, testId, danger }) {
  return (
    <button
      onClick={onClick}
      data-testid={testId}
      title={label}
      className={`flex items-center gap-1.5 border border-border bg-white px-3 py-1.5 text-xs font-medium ${
        danger ? "hover:bg-destructive hover:text-white hover:border-destructive" : "hover:bg-foreground hover:text-white"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function MiniStat({ label, value, mono }) {
  return (
    <div className="border border-border bg-white p-3">
      <div className="overline text-muted-foreground">{label}</div>
      <div className={`mt-1 text-sm ${mono ? "font-mono" : ""} break-words`}>{value}</div>
    </div>
  );
}
