import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Filter, ArrowRight, Trash2, Copy, Download, CloudUpload } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

export default function ProcessedQuestions() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selected, setSelected] = useState(() => new Set());
  const [filters, setFilters] = useState({
    q: "",
    disciplina: "",
    banca: "",
    ano: "",
    processo: "",
    competencia: "",
    dominio: "",
  });

  const fetchList = async (f = filters) => {
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(f).filter(([, v]) => v && v.trim())
      );
      const r = await api.get("/pipelines", { params });
      setRows(r.data);
      setSelected((prev) => {
        // manter apenas os ids que ainda existem
        const ids = new Set(r.data.map((x) => x.id));
        return new Set([...prev].filter((id) => ids.has(id)));
      });
    } catch (e) {
      toast.error("Falha ao carregar questões.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList({});
     
  }, []);

  const facets = useMemo(() => {
    const s = (k) => Array.from(new Set(rows.map((r) => r[k]).filter(Boolean))).sort();
    return {
      disciplina: s("disciplina"),
      banca: s("banca"),
      ano: s("ano"),
      dominio: Array.from(new Set(rows.flatMap((r) => r.dominios || []))).sort(),
      competencia: Array.from(new Set(rows.flatMap((r) => r.competencias || []))).sort(),
      processo: Array.from(new Set(rows.flatMap((r) => r.processos || []))).sort(),
    };
  }, [rows]);

  const allSelected = rows.length > 0 && selected.size === rows.length;
  const someSelected = selected.size > 0;

  const toggle = (id) =>
    setSelected((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      return s;
    });

  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(rows.map((r) => r.id)));
  };

  const fetchSelected = async () => {
    const ids = [...selected];
    const r = await api.post("/pipelines/bulk_get", { ids });
    return r.data.map((d) => ({
      pipeline_id: d.id,
      source_files: (d.artifacts?.originals || []).map((o) => o.filename),
      ontology_version: d.ontology_version,
      pipeline: d.pipeline,
    }));
  };

  const copySelected = async () => {
    if (!someSelected) return toast.error("Selecione pelo menos uma questão.");
    try {
      const arr = await fetchSelected();
      await navigator.clipboard.writeText(JSON.stringify(arr, null, 2));
      toast.success(`${arr.length} JSON(s) copiado(s).`);
    } catch (e) {
      toast.error("Falha ao copiar.");
    }
  };

  const exportSelected = async () => {
    if (!someSelected) return toast.error("Selecione pelo menos uma questão.");
    try {
      const arr = await fetchSelected();
      const blob = new Blob([JSON.stringify(arr, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sapiens-selecao-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Arquivo com ${arr.length} JSON(s) baixado.`);
    } catch (e) {
      toast.error("Falha ao exportar.");
    }
  };

  const deleteSelected = async () => {
    if (!someSelected) return toast.error("Selecione pelo menos uma questão.");
    if (!window.confirm(`Excluir ${selected.size} questão(ões) selecionada(s)?`)) return;
    try {
      const r = await api.post("/pipelines/bulk_delete", { ids: [...selected] });
      toast.success(`${r.data.deleted} excluída(s).`);
      setSelected(new Set());
      fetchList();
    } catch (e) {
      toast.error("Falha ao excluir em lote.");
    }
  };

  const delOne = async (id) => {
    if (!window.confirm("Excluir este pipeline?")) return;
    try {
      await api.delete(`/pipeline/${id}`);
      toast.success("Excluído.");
      fetchList();
    } catch (e) {
      toast.error("Falha ao excluir.");
    }
  };

  const syncAllFirestore = async () => {
    if (syncing) return;
    if (rows.length === 0) {
      return toast.error("Nenhuma questão para sincronizar.");
    }
    if (
      !window.confirm(
        `Sincronizar TODAS as ${rows.length} questão(ões) do banco interno com o Firestore (pasta "itens")?\n\n` +
          "Cada questão será salva individualmente usando seu ID único como título do documento. " +
          "Documentos órfãos (sem contraparte interna) serão removidos."
      )
    )
      return;
    setSyncing(true);
    try {
      const r = await api.post("/firestore/sync-all");
      const {
        collection: col,
        upserts,
        upsert_failures: uf,
        orphans_removed: orph,
        orphan_failures: of,
      } = r.data;
      toast.success(
        `Sincronização concluída na pasta "${col}": ${upserts} salva(s), ${orph} órfão(s) removido(s).` +
          (uf || of ? ` (${uf + of} falha(s))` : "")
      );
    } catch (e) {
      toast.error("Falha ao sincronizar com o Firestore.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="max-w-7xl px-8 py-10" data-testid="questoes-page">
      <div className="overline text-muted-foreground">Persistência</div>
      <h1 className="text-4xl font-black tracking-tight mt-1">Questões Processadas</h1>
      <p className="mt-3 text-sm text-muted-foreground max-w-2xl">
        Todos os pipelines cognitivos gerados ficam armazenados aqui, com os três
        artefatos: original, extração estruturada e pipeline final. Use os
        checkboxes para exportar ou excluir várias de uma vez.
      </p>

      {/* Filtros */}
      <div className="mt-8 border border-border bg-white">
        <div className="px-5 py-3 border-b border-border flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="overline text-muted-foreground">Filtros</span>
        </div>
        <div className="p-5 grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2 flex border border-border bg-white">
            <span className="p-2.5 border-r border-border">
              <Search className="h-4 w-4 text-muted-foreground" />
            </span>
            <input
              data-testid="filter-q"
              value={filters.q}
              onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
              placeholder="Buscar por tema, disciplina, enunciado…"
              className="flex-1 px-3 py-2 text-sm outline-none"
            />
          </div>
          <Select label="Disciplina" value={filters.disciplina} onChange={(v) => setFilters((f) => ({ ...f, disciplina: v }))} options={facets.disciplina} testId="filter-disciplina" />
          <Select label="Banca" value={filters.banca} onChange={(v) => setFilters((f) => ({ ...f, banca: v }))} options={facets.banca} testId="filter-banca" />
          <Select label="Ano" value={filters.ano} onChange={(v) => setFilters((f) => ({ ...f, ano: v }))} options={facets.ano} testId="filter-ano" />
          <Select label="Domínio" value={filters.dominio} onChange={(v) => setFilters((f) => ({ ...f, dominio: v }))} options={facets.dominio} testId="filter-dominio" />
          <Select label="Competência" value={filters.competencia} onChange={(v) => setFilters((f) => ({ ...f, competencia: v }))} options={facets.competencia} testId="filter-competencia" />
          <Select label="Processo" value={filters.processo} onChange={(v) => setFilters((f) => ({ ...f, processo: v }))} options={facets.processo} testId="filter-processo" />
        </div>
        <div className="px-5 py-3 border-t border-border flex items-center justify-end gap-2">
          <button
            data-testid="filters-clear"
            onClick={() => {
              const f = { q: "", disciplina: "", banca: "", ano: "", processo: "", competencia: "", dominio: "" };
              setFilters(f);
              fetchList(f);
            }}
            className="text-xs underline text-muted-foreground"
          >
            Limpar
          </button>
          <button
            data-testid="filters-apply"
            onClick={() => fetchList(filters)}
            className="bg-primary text-white px-4 py-2 text-sm font-medium hover:bg-foreground"
          >
            Aplicar filtros
          </button>
        </div>
      </div>

      {/* Bulk actions bar */}
      <div
        className="mt-6 border border-border bg-white flex items-center justify-between px-5 py-3 flex-wrap gap-3"
        data-testid="bulk-toolbar"
      >
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-medium cursor-pointer select-none">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleAll}
              disabled={rows.length === 0}
              data-testid="select-all"
              className="h-4 w-4 accent-primary"
            />
            Selecionar todos
          </label>
          <span
            className="font-mono text-xs text-muted-foreground"
            data-testid="selection-count"
          >
            {selected.size}/{rows.length} selecionada(s)
          </span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <BulkBtn onClick={copySelected} icon={Copy} label="Copiar JSONs" disabled={!someSelected} testId="bulk-copy" />
          <BulkBtn onClick={exportSelected} icon={Download} label="Exportar JSONs" disabled={!someSelected} testId="bulk-export" />
          <BulkBtn onClick={deleteSelected} icon={Trash2} label="Excluir" disabled={!someSelected} testId="bulk-delete" danger />
          <BulkBtn
            onClick={syncAllFirestore}
            icon={CloudUpload}
            label={syncing ? "Sincronizando…" : "Sincronizar Firestore"}
            disabled={syncing || rows.length === 0}
            testId="sync-firestore"
            primary
          />
        </div>
      </div>

      {/* Table */}
      <div className="mt-4 border border-border bg-white overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-secondary">
            <tr className="text-left">
              <Th className="w-10">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleAll}
                  disabled={rows.length === 0}
                  className="h-4 w-4 accent-primary"
                  data-testid="select-all-header"
                />
              </Th>
              <Th>Data</Th>
              <Th>Disciplina</Th>
              <Th>Tema</Th>
              <Th>Ano</Th>
              <Th>Resp.</Th>
              <Th>Domínios</Th>
              <Th>Processos</Th>
              <Th> </Th>
            </tr>
          </thead>
          <tbody data-testid="questoes-tbody">
            {loading && (
              <tr>
                <td colSpan={9} className="p-6 text-center text-muted-foreground">
                  Carregando…
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={9} className="p-10 text-center text-muted-foreground">
                  Nenhuma questão processada ainda. Vá para{" "}
                  <Link to="/gerador" className="text-primary underline">
                    Gerador de Pipeline
                  </Link>
                  .
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr
                key={r.id}
                className={`border-t border-border hover:bg-secondary ${selected.has(r.id) ? "bg-blue-50" : ""}`}
                data-testid={`row-${r.id}`}
              >
                <Td>
                  <input
                    type="checkbox"
                    checked={selected.has(r.id)}
                    onChange={() => toggle(r.id)}
                    className="h-4 w-4 accent-primary"
                    data-testid={`row-select-${r.id}`}
                  />
                </Td>
                <Td mono>{new Date(r.created_at).toLocaleDateString("pt-BR")}</Td>
                <Td>{r.disciplina || "—"}</Td>
                <Td>{r.tema || "—"}</Td>
                <Td mono>{r.ano || "—"}</Td>
                <Td mono className="text-emerald-700 font-bold">{r.resposta_correta || "—"}</Td>
                <Td>
                  <div className="flex flex-wrap gap-1">
                    {(r.dominios || []).slice(0, 3).map((d) => (
                      <span key={d} className="font-mono text-[10px] px-1.5 py-0.5 border border-primary text-primary">
                        {d}
                      </span>
                    ))}
                    {(r.dominios || []).length > 3 && (
                      <span className="font-mono text-[10px] text-muted-foreground">
                        +{r.dominios.length - 3}
                      </span>
                    )}
                  </div>
                </Td>
                <Td>
                  <div className="flex flex-wrap gap-1">
                    {(r.processos || []).slice(0, 3).map((p) => (
                      <span key={p} className="font-mono text-[10px] px-1.5 py-0.5 border border-border">
                        {p}
                      </span>
                    ))}
                    {(r.processos || []).length > 3 && (
                      <span className="font-mono text-[10px] text-muted-foreground">
                        +{r.processos.length - 3}
                      </span>
                    )}
                  </div>
                </Td>
                <Td>
                  <div className="flex items-center gap-1 justify-end">
                    <Link
                      to={`/questoes/${r.id}`}
                      className="p-1.5 hover:bg-foreground hover:text-white border border-border"
                      data-testid={`open-${r.id}`}
                      title="Ver/editar detalhes"
                    >
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                    <button
                      onClick={() => delOne(r.id)}
                      className="p-1.5 border border-border hover:bg-destructive hover:text-white"
                      data-testid={`delete-${r.id}`}
                      title="Excluir"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children, className = "" }) {
  return (
    <th className={`px-4 py-3 overline text-muted-foreground border-r border-border last:border-r-0 ${className}`}>
      {children}
    </th>
  );
}
function Td({ children, mono, className = "" }) {
  return (
    <td
      className={`px-4 py-3 align-top border-r border-border last:border-r-0 ${
        mono ? "font-mono text-xs" : ""
      } ${className}`}
    >
      {children}
    </td>
  );
}
function Select({ label, value, onChange, options, testId }) {
  return (
    <label className="flex flex-col text-xs">
      <span className="overline text-muted-foreground mb-1">{label}</span>
      <select
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-border bg-white p-2 text-sm outline-none"
      >
        <option value="">Todos</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
function BulkBtn({ onClick, icon: Icon, label, disabled, testId, danger, primary }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className={`flex items-center gap-1.5 border px-3 py-1.5 text-xs font-medium disabled:opacity-40 disabled:cursor-not-allowed ${
        danger
          ? "border-border bg-white hover:bg-destructive hover:text-white hover:border-destructive"
          : primary
          ? "border-primary bg-primary text-white hover:bg-foreground hover:border-foreground"
          : "border-border bg-white hover:bg-foreground hover:text-white"
      }`}
    >
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  );
}
