import { useState } from "react";
import { toast } from "sonner";
import {
  Copy,
  Download,
  CheckCircle2,
  RotateCw,
  Pencil,
  Save,
  X,
  ChevronDown,
  ChevronRight,
  ArrowLeft,
} from "lucide-react";
import api from "@/lib/api";
import JsonViewer from "@/components/JsonViewer";

function Tag({ children, color = "#09090B", testId }) {
  return (
    <span
      data-testid={testId}
      className="inline-flex items-center gap-1 font-mono text-[11px] px-2 py-1 border"
      style={{ borderColor: color, color }}
    >
      {children}
    </span>
  );
}

function Section({ title, count, children, testId }) {
  return (
    <div className="border border-border bg-white" data-testid={testId}>
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <div className="overline text-muted-foreground">{title}</div>
        <div className="font-mono text-xs text-muted-foreground">{count}</div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

export default function PipelineResult({ data, onReset, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [busy, setBusy] = useState(false);
  const [openProc, setOpenProc] = useState({});

  const pipeline = data.pipeline || {};
  const questao = pipeline.questao || {};
  const cls = pipeline.classificacao || {};

  const jsonStr = JSON.stringify(pipeline, null, 2);

  const copyJson = async () => {
    await navigator.clipboard.writeText(jsonStr);
    toast.success("JSON copiado.");
  };
  const downloadJson = () => {
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pipeline-${data.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Download iniciado.");
  };
  const validateJson = () => {
    try {
      JSON.parse(jsonStr);
      const missing = [];
      if (!questao.enunciado) missing.push("questao.enunciado");
      if (!cls.dominios) missing.push("classificacao.dominios");
      if (!cls.processos_cognitivos) missing.push("classificacao.processos_cognitivos");
      if (missing.length)
        toast.warning(`JSON válido, mas campos ausentes: ${missing.join(", ")}`);
      else toast.success("JSON válido e completo.");
    } catch (e) {
      toast.error("JSON inválido: " + e.message);
    }
  };

  const regenerate = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/pipeline/${data.id}/regenerate`);
      onUpdate(r.data);
      toast.success("Pipeline regenerado.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao regenerar.");
    } finally {
      setBusy(false);
    }
  };

  const startEdit = () => {
    setEditText(jsonStr);
    setEditing(true);
  };
  const saveEdit = async () => {
    setBusy(true);
    try {
      const parsed = JSON.parse(editText);
      const r = await api.put(`/pipeline/${data.id}`, { pipeline: parsed });
      onUpdate(r.data);
      setEditing(false);
      toast.success("Pipeline atualizado manualmente.");
    } catch (e) {
      toast.error("Falha: " + (e?.response?.data?.detail || e.message));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-2 space-y-6" data-testid="pipeline-result">
      <button
        onClick={onReset}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        data-testid="new-pipeline-btn"
      >
        <ArrowLeft className="h-4 w-4" /> Gerar outra questão
      </button>

      {/* Header block */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 border border-border bg-white">
        <div className="lg:col-span-8 p-6 border-b lg:border-b-0 lg:border-r border-border">
          <div className="overline text-muted-foreground">Questão detectada</div>
          <div className="mt-2 text-xl font-bold" data-testid="questao-tema">
            {questao.tema || "Tema não identificado"}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            <span data-testid="questao-disciplina">{questao.disciplina || "—"}</span>
            {questao.banca && <> · <span>{questao.banca}</span></>}
            {questao.ano && <> · <span>{questao.ano}</span></>}
          </div>
          <p
            className="mt-4 text-sm leading-relaxed whitespace-pre-wrap"
            data-testid="questao-enunciado"
          >
            {questao.enunciado || "—"}
          </p>
          {questao.alternativas?.length > 0 && (
            <ul className="mt-4 space-y-1" data-testid="alternativas-list">
              {questao.alternativas.map((a) => (
                <li
                  key={a.letra}
                  className={`flex gap-3 text-sm py-1 px-2 border-l-2 ${
                    a.letra === questao.resposta_correta
                      ? "border-emerald-600 bg-emerald-50"
                      : "border-transparent"
                  }`}
                >
                  <span className="font-mono font-bold w-6">{a.letra})</span>
                  <span>{a.texto}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="lg:col-span-4 p-6 space-y-4">
          <div>
            <div className="overline text-muted-foreground">Resposta correta</div>
            <div
              className="mt-1 text-3xl font-black text-emerald-700 font-mono"
              data-testid="resposta-correta"
            >
              {questao.resposta_correta || "—"}
            </div>
          </div>
          <div>
            <div className="overline text-muted-foreground">Confiança do motor</div>
            <div className="mt-1 font-mono text-sm">
              {pipeline.meta?.confianca ?? "—"}
            </div>
          </div>
          <div>
            <div className="overline text-muted-foreground">Ontologia usada</div>
            <div className="mt-1 font-mono text-xs">
              {data.ontology_version || "—"}
            </div>
          </div>
          <div className="pt-2 flex flex-wrap gap-2">
            <ActionBtn onClick={copyJson} icon={Copy} label="Copiar" testId="btn-copy" />
            <ActionBtn onClick={downloadJson} icon={Download} label="Baixar" testId="btn-download" />
            <ActionBtn onClick={validateJson} icon={CheckCircle2} label="Validar" testId="btn-validate" />
            <ActionBtn onClick={regenerate} icon={RotateCw} label="Regenerar" disabled={busy} testId="btn-regenerate" />
            <ActionBtn onClick={editing ? () => setEditing(false) : startEdit} icon={editing ? X : Pencil} label={editing ? "Cancelar" : "Editar"} testId="btn-edit" />
          </div>
        </div>
      </div>

      {/* Classification grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Section title="Domínios" count={cls.dominios?.length ?? 0} testId="section-dominios">
          <div className="flex flex-wrap gap-2">
            {(cls.dominios || []).map((d) => (
              <Tag key={d} color="#002FA7" testId={`tag-dom-${d}`}>{d}</Tag>
            ))}
            {(cls.dominios || []).length === 0 && (
              <span className="text-xs text-muted-foreground">Nenhum domínio.</span>
            )}
          </div>
        </Section>

        <Section title="Competências" count={cls.competencias?.length ?? 0} testId="section-competencias">
          <div className="flex flex-wrap gap-2">
            {(cls.competencias || []).map((c) => (
              <Tag key={c} color="#059669" testId={`tag-comp-${c}`}>{c}</Tag>
            ))}
            {(cls.competencias || []).length === 0 && (
              <span className="text-xs text-muted-foreground">Nenhuma competência.</span>
            )}
          </div>
        </Section>

        <Section title="Tipos de erro" count={cls.tipos_erro_previstos?.length ?? 0} testId="section-erros">
          <div className="flex flex-wrap gap-2">
            {(cls.tipos_erro_previstos || []).map((t) => (
              <Tag key={t} color="#E11D48" testId={`tag-err-${t}`}>{t}</Tag>
            ))}
            {(cls.tipos_erro_previstos || []).length === 0 && (
              <span className="text-xs text-muted-foreground">Nenhum tipo previsto.</span>
            )}
          </div>
        </Section>
      </div>

      {/* Cognitive processes with explicability */}
      <Section
        title="Processos Cognitivos"
        count={cls.processos_cognitivos?.length ?? 0}
        testId="section-processos"
      >
        <ul>
          {(cls.processos_cognitivos || []).map((p, i) => {
            const isOpen = openProc[p.id + i];
            const papelColor = {
              nuclear: "#002FA7",
              secundario: "#52525B",
              facilitador: "#059669",
            }[p.papel] || "#09090B";
            return (
              <li key={p.id + i} className="border-b border-border last:border-b-0 py-3">
                <div className="flex items-center gap-3 flex-wrap">
                  <Tag color={papelColor} testId={`tag-proc-${p.id}`}>{p.id}</Tag>
                  <span
                    className="font-mono text-[10px] uppercase tracking-widest"
                    style={{ color: papelColor }}
                  >
                    {p.papel || "—"}
                  </span>
                  <button
                    data-testid={`proc-justify-${p.id}`}
                    onClick={() => setOpenProc((s) => ({ ...s, [p.id + i]: !isOpen }))}
                    className="ml-auto flex items-center gap-1 text-xs underline text-muted-foreground"
                  >
                    {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                    {isOpen ? "Ocultar justificativa" : "Mostrar justificativa"}
                  </button>
                </div>
                {isOpen && (
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 pl-1 border-l-2 ml-2" style={{ borderColor: papelColor }}>
                    <Justify title="Trechos do enunciado" items={p.justificativa?.trechos_enunciado} />
                    <Justify title="Elementos da figura" items={p.justificativa?.elementos_figura} />
                    <Justify title="Regras da ontologia" items={p.justificativa?.regras_ontologia} />
                    <Justify title="Por que este papel" text={p.justificativa?.por_que_este_papel} />
                  </div>
                )}
              </li>
            );
          })}
          {(cls.processos_cognitivos || []).length === 0 && (
            <li className="text-xs text-muted-foreground">
              Nenhum processo cognitivo identificado.
            </li>
          )}
        </ul>
      </Section>

      {/* Distratores */}
      <Section
        title="Distratores"
        count={cls.distratores?.length ?? 0}
        testId="section-distratores"
      >
        <ul className="space-y-3">
          {(cls.distratores || []).map((d, i) => (
            <li key={i} className="flex items-start gap-4">
              <span className="font-mono font-bold text-lg w-6">{d.alternativa}</span>
              <div className="flex-1">
                <Tag color="#E11D48">{d.tipo_erro_id}</Tag>
                <p className="mt-1 text-sm text-muted-foreground">{d.explicacao}</p>
              </div>
            </li>
          ))}
          {(cls.distratores || []).length === 0 && (
            <li className="text-xs text-muted-foreground">Nenhum distrator anotado.</li>
          )}
        </ul>
      </Section>

      {/* Full JSON */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="overline text-muted-foreground">JSON completo</div>
          {editing && (
            <button
              data-testid="btn-save-edit"
              onClick={saveEdit}
              disabled={busy}
              className="flex items-center gap-2 bg-primary text-white px-3 py-1.5 text-xs font-bold hover:bg-foreground disabled:opacity-50"
            >
              <Save className="h-3 w-3" /> Salvar edição
            </button>
          )}
        </div>
        {editing ? (
          <textarea
            data-testid="json-editor"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className="w-full h-[500px] font-mono text-[12.5px] bg-white border border-border p-4"
          />
        ) : (
          <JsonViewer data={pipeline} testId="pipeline-json" />
        )}
      </div>
    </div>
  );
}

function ActionBtn({ onClick, icon: Icon, label, disabled, testId }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="flex items-center gap-1.5 border border-border bg-white px-3 py-1.5 text-xs font-medium hover:bg-foreground hover:text-white disabled:opacity-50"
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function Justify({ title, items, text }) {
  const hasItems = Array.isArray(items) && items.length > 0;
  return (
    <div className="pl-3">
      <div className="overline text-muted-foreground mb-1">{title}</div>
      {hasItems ? (
        <ul className="list-disc pl-5 text-sm space-y-1">
          {items.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      ) : text ? (
        <p className="text-sm">{text}</p>
      ) : (
        <p className="text-xs text-muted-foreground">Não informado.</p>
      )}
    </div>
  );
}
