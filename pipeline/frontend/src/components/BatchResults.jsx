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
} from "lucide-react";
import api from "@/lib/api";
import JsonViewer from "@/components/JsonViewer";

const statusStyles = {
  pending: { color: "#52525B", icon: Loader2, label: "Aguardando", spin: false },
  processing: { color: "#002FA7", icon: Loader2, label: "Processando…", spin: true },
  done: { color: "#059669", icon: CheckCircle2, label: "OK", spin: false },
  error: { color: "#E11D48", icon: AlertCircle, label: "Erro", spin: false },
};

export default function BatchResults({ items, busy, onReset, onItemUpdate, onItemRemove }) {
  const [selected, setSelected] = useState(() => new Set());
  const [expanded, setExpanded] = useState(() => new Set());
  const [editing, setEditing] = useState(null); // idx being edited
  const [editText, setEditText] = useState("");

  const doneItems = useMemo(
    () => items.map((it, i) => ({ ...it, idx: i })).filter((it) => it.status === "done"),
    [items],
  );

  const toggleSel = (idx) =>
    setSelected((prev) => {
      const s = new Set(prev);
      if (s.has(idx)) s.delete(idx);
      else s.add(idx);
      return s;
    });

  const toggleAll = () => {
    if (selected.size === doneItems.length && doneItems.length > 0) setSelected(new Set());
    else setSelected(new Set(doneItems.map((it) => it.idx)));
  };

  const toggleExpand = (idx) =>
    setExpanded((prev) => {
      const s = new Set(prev);
      if (s.has(idx)) s.delete(idx);
      else s.add(idx);
      return s;
    });

  const collectSelectedJsons = () =>
    doneItems
      .filter((it) => selected.has(it.idx))
      .map((it) => ({
        source_file: it.filename,
        pipeline_id: it.result?.id,
        ontology_version: it.result?.ontology_version,
        pipeline: it.result?.pipeline,
      }));

  const copySelected = async () => {
    const arr = collectSelectedJsons();
    if (arr.length === 0) {
      toast.error("Selecione pelo menos uma questão.");
      return;
    }
    await navigator.clipboard.writeText(JSON.stringify(arr, null, 2));
    toast.success(`${arr.length} JSON(s) copiado(s) para a área de transferência.`);
  };

  const exportSelected = () => {
    const arr = collectSelectedJsons();
    if (arr.length === 0) {
      toast.error("Selecione pelo menos uma questão.");
      return;
    }
    const blob = new Blob([JSON.stringify(arr, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sapiens-lote-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Arquivo com ${arr.length} JSON(s) baixado.`);
  };

  const deleteOne = async (item) => {
    if (!window.confirm(`Excluir a questão "${item.filename}"?`)) return;
    if (item.result?.id) {
      try {
        await api.delete(`/pipeline/${item.result.id}`);
      } catch (e) {
        toast.error("Falha ao excluir no servidor.");
        return;
      }
    }
    onItemRemove(item.idx);
    setSelected((prev) => {
      const s = new Set(prev);
      s.delete(item.idx);
      return s;
    });
    toast.success("Excluída.");
  };

  const deleteSelected = async () => {
    const chosen = doneItems.filter((it) => selected.has(it.idx));
    if (chosen.length === 0) {
      toast.error("Selecione pelo menos uma questão.");
      return;
    }
    if (!window.confirm(`Excluir ${chosen.length} questão(ões) selecionada(s)?`)) return;
    for (const c of chosen) {
      if (c.result?.id) {
        try {
          await api.delete(`/pipeline/${c.result.id}`);
        } catch {
          /* ignore individual failure */
        }
      }
    }
    // remove locally in reverse order to preserve indexes
    const toRemove = [...chosen].sort((a, b) => b.idx - a.idx);
    toRemove.forEach((c) => onItemRemove(c.idx));
    setSelected(new Set());
    toast.success(`${chosen.length} excluída(s).`);
  };

  const startEdit = (item) => {
    setEditing(item.idx);
    setEditText(JSON.stringify(item.result.pipeline, null, 2));
  };
  const cancelEdit = () => {
    setEditing(null);
    setEditText("");
  };
  const saveEdit = async (item) => {
    try {
      const parsed = JSON.parse(editText);
      const r = await api.put(`/pipeline/${item.result.id}`, { pipeline: parsed });
      onItemUpdate(item.idx, { result: r.data });
      setEditing(null);
      toast.success("JSON atualizado.");
    } catch (e) {
      toast.error("Falha: " + (e?.response?.data?.detail || e.message));
    }
  };

  const total = items.length;
  const okCount = doneItems.length;
  const errCount = items.filter((it) => it.status === "error").length;
  const allSelected = selected.size === okCount && okCount > 0;

  return (
    <div className="mt-2 space-y-6" data-testid="batch-results">
      <button
        onClick={onReset}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        data-testid="batch-new-btn"
      >
        <ArrowLeft className="h-4 w-4" /> Novo lote
      </button>

      {/* Header */}
      <div className="border border-border bg-white">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="overline text-muted-foreground">Lote em andamento</div>
            <div className="mt-1 text-xl font-black">
              {okCount}/{total} processadas
              {errCount > 0 && (
                <span className="ml-3 text-sm font-mono text-destructive">· {errCount} erro(s)</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="flex items-center gap-2 text-sm font-medium cursor-pointer select-none">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleAll}
                disabled={okCount === 0}
                data-testid="batch-select-all"
                className="h-4 w-4 accent-primary"
              />
              Selecionar todos ({selected.size}/{okCount})
            </label>
            <BulkBtn onClick={copySelected} icon={Copy} label="Copiar JSONs" testId="batch-copy" />
            <BulkBtn onClick={exportSelected} icon={Download} label="Exportar JSONs" testId="batch-export" />
            <BulkBtn onClick={deleteSelected} icon={Trash2} label="Excluir" testId="batch-delete" danger />
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-secondary">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${total ? (okCount / total) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Items */}
      <div className="border border-border bg-white">
        {items.map((item, i) => {
          const style = statusStyles[item.status];
          const Icon = style.icon;
          const isDone = item.status === "done";
          const isSel = selected.has(i);
          const isExp = expanded.has(i);
          const isEditing = editing === i;
          const q = item.result?.pipeline?.questao || {};
          const cls = item.result?.pipeline?.classificacao || {};

          return (
            <div key={item.key} className="border-b border-border last:border-b-0" data-testid={`batch-item-${i}`}>
              <div className="px-6 py-4 flex items-center gap-4 flex-wrap">
                <input
                  type="checkbox"
                  checked={isSel}
                  disabled={!isDone}
                  onChange={() => toggleSel(i)}
                  data-testid={`batch-select-${i}`}
                  className="h-4 w-4 accent-primary disabled:opacity-40"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs px-2 py-0.5 border border-border">
                      #{String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="font-medium truncate">{item.filename}</span>
                    {isDone && q.disciplina && (
                      <span className="text-xs text-muted-foreground">· {q.disciplina}</span>
                    )}
                    {isDone && q.tema && (
                      <span className="text-xs text-muted-foreground">· {q.tema}</span>
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

                {isDone && (
                  <div className="flex items-center gap-1">
                    <IconBtn
                      onClick={() => toggleExpand(i)}
                      icon={isExp ? ChevronDown : ChevronRight}
                      testId={`batch-toggle-${i}`}
                      label={isExp ? "Ocultar" : "Ver JSON"}
                    />
                    <IconBtn
                      onClick={() => startEdit(item.result ? { ...item, idx: i } : null)}
                      icon={Pencil}
                      testId={`batch-edit-${i}`}
                      label="Editar"
                    />
                    <Link
                      to={`/questoes/${item.result.id}`}
                      className="flex items-center gap-1.5 border border-border bg-white px-3 py-1.5 text-xs font-medium hover:bg-foreground hover:text-white"
                      data-testid={`batch-open-${i}`}
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Abrir
                    </Link>
                    <IconBtn
                      onClick={() => deleteOne({ ...item, idx: i })}
                      icon={Trash2}
                      testId={`batch-delete-${i}`}
                      label="Excluir"
                      danger
                    />
                  </div>
                )}
              </div>

              {isDone && isExp && !isEditing && (
                <div className="px-6 pb-6 pt-2 border-t border-border bg-secondary/40">
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
                    <MiniStat label="Resposta" value={q.resposta_correta || "—"} mono />
                    <MiniStat
                      label="Domínios"
                      value={(cls.dominios || []).join(", ") || "—"}
                      mono
                    />
                    <MiniStat
                      label="Processos"
                      value={(cls.processos_cognitivos || []).map((p) => p.id).join(", ") || "—"}
                      mono
                    />
                  </div>
                  <JsonViewer data={item.result.pipeline} testId={`batch-json-${i}`} />
                </div>
              )}

              {isDone && isEditing && (
                <div className="px-6 pb-6 pt-2 border-t border-border bg-secondary/40" data-testid={`batch-edit-panel-${i}`}>
                  <div className="mb-3 flex items-center justify-between">
                    <div className="overline text-muted-foreground">Editar JSON</div>
                    <div className="flex items-center gap-2">
                      <IconBtn onClick={cancelEdit} icon={X} label="Cancelar" testId={`batch-cancel-edit-${i}`} />
                      <button
                        data-testid={`batch-save-edit-${i}`}
                        onClick={() => saveEdit({ ...item, idx: i })}
                        className="flex items-center gap-1.5 bg-primary text-white px-3 py-1.5 text-xs font-bold hover:bg-foreground"
                      >
                        <Save className="h-3 w-3" /> Salvar
                      </button>
                    </div>
                  </div>
                  <textarea
                    data-testid={`batch-editor-${i}`}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full h-[400px] font-mono text-[12.5px] bg-white border border-border p-4"
                  />
                </div>
              )}
            </div>
          );
        })}
        {items.length === 0 && (
          <div className="px-6 py-10 text-center text-sm text-muted-foreground">
            Nenhuma questão no lote.
          </div>
        )}
      </div>

      {busy && (
        <div className="text-xs text-muted-foreground font-mono" data-testid="batch-busy">
          Processando lote… mantenha esta aba aberta.
        </div>
      )}
    </div>
  );
}

function BulkBtn({ onClick, icon: Icon, label, testId, danger }) {
  return (
    <button
      onClick={onClick}
      data-testid={testId}
      className={`flex items-center gap-1.5 border border-border px-3 py-1.5 text-xs font-medium ${
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
