import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Upload, RefreshCw, ChevronDown, ChevronRight, RotateCcw, FileCode2 } from "lucide-react";
import api from "@/lib/api";
import JsonViewer from "@/components/JsonViewer";

const SECTIONS = [
  { key: "dominios", label: "Domínios Cognitivos", accent: "#002FA7" },
  { key: "competencias", label: "Competências", accent: "#059669" },
  { key: "processos_cognitivos", label: "Processos Cognitivos", accent: "#09090B" },
  { key: "habilidades_observaveis", label: "Habilidades Observáveis", accent: "#7C3AED" },
  { key: "tipos_erro", label: "Tipos de Erro", accent: "#E11D48" },
  { key: "intervencoes_pedagogicas", label: "Intervenções Pedagógicas", accent: "#52525B" },
];

export default function Ontology() {
  const [ontology, setOntology] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [openSection, setOpenSection] = useState("dominios");
  const [openItem, setOpenItem] = useState({});
  const inputRef = useRef(null);

  // Pipeline schema (estrutura JSON do output do motor)
  const [schema, setSchema] = useState(null);
  const [schemaSummary, setSchemaSummary] = useState(null);
  const [showSchemaRaw, setShowSchemaRaw] = useState(false);
  const schemaInputRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const [r, sr] = await Promise.all([
        api.get("/ontology"),
        api.get("/schema"),
      ]);
      setOntology(r.data);
      setSchema(sr.data.schema);
      setSchemaSummary(sr.data.summary);
    } catch (e) {
      toast.error("Falha ao carregar ontologia/schema");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleUpload = async (file) => {
    if (!file) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post("/ontology/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 180000,
      });
      toast.success("Ontologia importada com sucesso");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao importar ontologia");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Restaurar a ontologia semente (versão 1.0.0-seed)?")) return;
    setBusy(true);
    try {
      await api.post("/ontology/reset");
      toast.success("Ontologia restaurada para a versão 1.0.0-seed");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao restaurar ontologia");
    } finally {
      setBusy(false);
    }
  };

  const handleSchemaUpload = async (file) => {
    if (!file) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await api.post("/schema/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,
      });
      setSchema(r.data.schema);
      setSchemaSummary(r.data.summary);
      toast.success("Schema importado com sucesso");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao importar schema");
    } finally {
      setBusy(false);
      if (schemaInputRef.current) schemaInputRef.current.value = "";
    }
  };

  const handleSchemaReset = async () => {
    if (!window.confirm("Restaurar o schema padrão embutido do motor?")) return;
    setBusy(true);
    try {
      const r = await api.post("/schema/reset");
      setSchema(r.data.schema);
      setSchemaSummary(r.data.summary);
      toast.success("Schema restaurado para o padrão embutido");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao restaurar schema");
    } finally {
      setBusy(false);
    }
  };

  const toggleItem = (section, id) =>
    setOpenItem((s) => ({ ...s, [`${section}:${id}`]: !s[`${section}:${id}`] }));

  const counts = ontology
    ? Object.fromEntries(SECTIONS.map((s) => [s.key, (ontology[s.key] || []).length]))
    : {};

  return (
    <div className="max-w-6xl px-8 py-10" data-testid="ontology-page">
      <div className="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <div className="overline text-muted-foreground">Base de Conhecimento</div>
          <h1 className="text-4xl font-black tracking-tight mt-1">Ontologia Cognitiva</h1>
          <p className="mt-3 text-sm text-muted-foreground max-w-2xl">
            Única fonte autorizada de classificação. O motor cognitivo utiliza
            exclusivamente os IDs abaixo — jamais inventa novos.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept=".json,.yaml,.yml,.md,.markdown,.txt,.docx,.pdf"
            className="hidden"
            onChange={(e) => handleUpload(e.target.files?.[0])}
            data-testid="ontology-file-input"
          />
          <input
            ref={schemaInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => handleSchemaUpload(e.target.files?.[0])}
            data-testid="schema-file-input"
          />
          <button
            data-testid="ontology-import-btn"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            className="flex items-center gap-2 bg-primary text-white px-4 py-2.5 text-sm font-medium hover:bg-foreground disabled:opacity-60"
          >
            <Upload className="h-4 w-4" /> {busy ? "Processando…" : "Importar Ontologia"}
          </button>
          <button
            data-testid="schema-import-btn"
            onClick={() => schemaInputRef.current?.click()}
            disabled={busy}
            className="flex items-center gap-2 border border-primary text-primary bg-white px-4 py-2.5 text-sm font-medium hover:bg-primary hover:text-white disabled:opacity-60"
            title="Importar o JSON do schema de anotação (estrutura do pipeline)"
          >
            <FileCode2 className="h-4 w-4" /> Importar Schema
          </button>
          <button
            data-testid="ontology-reset-btn"
            onClick={handleReset}
            disabled={busy}
            className="flex items-center gap-2 border border-border bg-white px-4 py-2.5 text-sm font-medium hover:bg-foreground hover:text-white disabled:opacity-60"
            title="Restaura a ontologia semente original"
          >
            <RotateCcw className="h-4 w-4" /> Resetar para versão 1.0
          </button>
          <button
            data-testid="ontology-reload"
            onClick={load}
            className="p-2.5 border border-border bg-white hover:bg-secondary"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Meta */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-0 border border-border bg-white">
        <MetaCell label="Versão" value={ontology?.version} mono testId="onto-version" />
        <MetaCell
          label="Importada em"
          value={
            ontology?.imported_at
              ? new Date(ontology.imported_at).toLocaleString("pt-BR")
              : "—"
          }
          testId="onto-imported-at"
        />
        <MetaCell
          label="Arquivo de origem"
          value={ontology?.source_filename || "—"}
          testId="onto-source"
        />
        <MetaCell
          label="Total de elementos"
          value={
            ontology
              ? SECTIONS.reduce((a, s) => a + (ontology[s.key] || []).length, 0)
              : 0
          }
          mono
          testId="onto-total"
        />
      </div>

      {/* Sections */}
      <div className="mt-8 border border-border bg-white">
        {SECTIONS.map((s) => {
          const items = ontology?.[s.key] || [];
          const isOpen = openSection === s.key;
          return (
            <div key={s.key} className="border-b border-border last:border-b-0">
              <button
                data-testid={`ontology-section-${s.key}`}
                onClick={() => setOpenSection(isOpen ? null : s.key)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-secondary text-left"
              >
                <div className="flex items-center gap-3">
                  <span
                    className="inline-block h-2 w-2"
                    style={{ backgroundColor: s.accent }}
                  />
                  <span className="font-bold">{s.label}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    ({counts[s.key] ?? 0})
                  </span>
                </div>
                {isOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
              {isOpen && (
                <ul className="border-t border-border">
                  {items.length === 0 && (
                    <li className="px-6 py-4 text-sm text-muted-foreground">
                      Nenhum item nesta categoria.
                    </li>
                  )}
                  {items.map((it) => {
                    const id = it.id || JSON.stringify(it).slice(0, 30);
                    const opened = openItem[`${s.key}:${id}`];
                    return (
                      <li key={id} className="border-b border-border last:border-b-0">
                        <button
                          data-testid={`onto-item-${id}`}
                          onClick={() => toggleItem(s.key, id)}
                          className="w-full flex items-center gap-4 px-6 py-3 hover:bg-secondary text-left"
                        >
                          <span className="font-mono text-xs px-2 py-0.5 border border-border">
                            {it.id || "—"}
                          </span>
                          <span className="flex-1 text-sm font-medium">
                            {it.nome || it.name || "(sem nome)"}
                          </span>
                          {it.dominio && (
                            <span className="font-mono text-[10px] text-muted-foreground">
                              {it.dominio}
                            </span>
                          )}
                          {opened ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                        </button>
                        {opened && (
                          <div className="px-6 pb-4 pt-1 text-sm text-muted-foreground leading-relaxed border-l-2 ml-6" style={{ borderColor: s.accent }}>
                            {it.descricao || it.description || "Sem descrição."}
                            {it.categoria && (
                              <div className="mt-2 overline text-muted-foreground">
                                categoria · {it.categoria}
                              </div>
                            )}
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {/* Raw */}
      <div className="mt-8">
        <button
          data-testid="ontology-toggle-raw"
          onClick={() => setShowRaw((v) => !v)}
          className="text-sm underline text-muted-foreground"
        >
          {showRaw ? "Ocultar" : "Mostrar"} JSON bruto da ontologia
        </button>
        {showRaw && ontology && (
          <div className="mt-3">
            <JsonViewer data={ontology} testId="ontology-raw-json" />
          </div>
        )}
      </div>

      {/* Schema de anotação */}
      <div className="mt-12 border border-border bg-white" data-testid="schema-section">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <FileCode2 className="h-4 w-4 text-primary" />
            <div>
              <div className="font-bold">Schema de Anotação (JSON)</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Estrutura JSON que o motor cognitivo usa para produzir cada
                pipeline. Independente da ontologia.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="font-mono text-[11px] px-2 py-1 border border-border text-muted-foreground"
              data-testid="schema-version"
            >
              {schemaSummary?.version || "—"}
              {schemaSummary?.is_default ? " · builtin" : ""}
            </span>
            <button
              onClick={handleSchemaReset}
              disabled={busy || schemaSummary?.is_default}
              className="text-xs underline text-muted-foreground disabled:opacity-40"
              data-testid="schema-reset-btn"
              title="Voltar ao schema padrão embutido"
            >
              Resetar schema
            </button>
          </div>
        </div>
        <div className="px-6 py-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <MetaCell label="Nome" value={schemaSummary?.name || "—"} testId="schema-name" />
          <MetaCell
            label="Importado em"
            value={
              schemaSummary?.imported_at
                ? new Date(schemaSummary.imported_at).toLocaleString("pt-BR")
                : "—"
            }
            testId="schema-imported-at"
          />
          <MetaCell
            label="Arquivo de origem"
            value={schemaSummary?.source_filename || "—"}
            testId="schema-source"
          />
        </div>
        <div className="px-6 pb-5">
          <button
            data-testid="schema-toggle-raw"
            onClick={() => setShowSchemaRaw((v) => !v)}
            className="text-sm underline text-muted-foreground"
          >
            {showSchemaRaw ? "Ocultar" : "Mostrar"} JSON do schema
          </button>
          {showSchemaRaw && schema && (
            <div className="mt-3">
              <JsonViewer data={schema} testId="schema-raw-json" />
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div className="mt-8 text-sm text-muted-foreground">Carregando ontologia…</div>
      )}
    </div>
  );
}

function MetaCell({ label, value, mono, testId }) {
  return (
    <div className="p-5 border-r border-b border-border last:border-r-0 md:border-b-0">
      <div className="overline text-muted-foreground">{label}</div>
      <div
        data-testid={testId}
        className={`mt-2 text-sm ${mono ? "font-mono" : ""} break-words`}
      >
        {value ?? "—"}
      </div>
    </div>
  );
}
