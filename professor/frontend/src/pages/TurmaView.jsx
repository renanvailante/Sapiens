import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFilters } from "@/layout/AppLayout";
import { Panel, SemDado, formatPct, heatClass, CalcBadge, StatCard, EmptyState } from "@/components/common";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function TurmaView() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!filters.turma || !filters.periodo) { setData(null); return; }
    setLoading(true); setErr(null);
    const params = { turma: filters.turma, periodo: filters.periodo };
    if (filters.disciplina) params.disciplina = filters.disciplina;
    api.get("/views/turma", { params })
      .then(({ data }) => setData(data))
      .catch((e) => setErr(e.response?.data?.detail || "Erro"))
      .finally(() => setLoading(false));
  }, [filters.turma, filters.periodo, filters.disciplina]);

  const downloadCsv = () => {
    if (!filters.turma || !filters.periodo) return;
    const params = new URLSearchParams({ turma: filters.turma, periodo: filters.periodo });
    if (filters.disciplina) params.set("disciplina", filters.disciplina);
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/export/turma.csv?${params}`;
    window.open(url, "_blank");
  };

  if (!filters.turma || !filters.periodo) {
    return <div className="p-6"><EmptyState hint="Selecione turma e período nos filtros globais." /></div>;
  }
  if (loading) return <div className="p-6 text-sm text-muted-foreground">Carregando…</div>;
  if (err) return <div className="p-6"><EmptyState title={err} /></div>;
  if (!data) return null;

  return (
    <div className="p-6 space-y-4" data-testid="turma-view">
      {/* Metadata banner */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-border border border-border">
        <MetaBox label="Turma" value={data.turma} />
        <MetaBox label="Período" value={data.periodo} />
        <MetaBox label="Versão taxonomia" value={data.versao_taxonomia} mono />
        <MetaBox label="Data processamento" value={data.data_processamento} mono />
        <MetaBox label="Modelo análise" value={data.modelo_analise} mono />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="Total de alunos" value={data.total_alunos} testid="stat-alunos" />
        <StatCard label="Total de questões (soma)" value={data.total_questoes} testid="stat-questoes" />
        <div className="border border-border p-4 flex items-center">
          <CalcBadge />
        </div>
      </div>

      <Panel
        title="Matriz aluno × nó cognitivo"
        subtitle={`${data.nos.length} nós · ${data.rows.length} alunos · taxa de erro por célula`}
        testid="turma-matrix-panel"
        right={
          <Button
            data-testid="export-turma-csv-btn"
            variant="outline"
            size="sm"
            onClick={downloadCsv}
          >
            Exportar CSV
          </Button>
        }
      >
        <div className="overflow-x-auto border border-border">
          <table className="sapiens-table">
            <thead>
              <tr>
                <th className="sticky left-0 bg-white z-10">Aluno</th>
                {data.nos.map((n) => (
                  <th key={n.no_id} className="num" title={n.no_id}>
                    <div className="font-mono normal-case tracking-normal text-[10px] text-muted-foreground">{n.disciplina}</div>
                    <div className="normal-case tracking-normal text-[11px] text-foreground max-w-[120px] whitespace-normal">{n.no_label}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.aluno_id}>
                  <td className="sticky left-0 bg-white z-10">
                    <div className="text-[11px] font-mono text-muted-foreground">{r.aluno_id}</div>
                    <div className="text-sm">{r.nome || <SemDado />}</div>
                  </td>
                  {data.nos.map((n) => {
                    const c = r.cells[n.no_id];
                    const val = c?.taxa_erro;
                    return (
                      <td key={n.no_id} className={`num ${heatClass(val)}`}>
                        {val == null ? <SemDado /> : formatPct(val)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Legend />
      </Panel>
    </div>
  );
}

function MetaBox({ label, value, mono }) {
  return (
    <div className="bg-white p-3">
      <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className={"mt-1 text-sm " + (mono ? "font-mono" : "")}>
        {value == null || value === "" ? <SemDado /> : value}
      </div>
    </div>
  );
}

function Legend() {
  const bands = [
    { c: "heat-1", l: "0–20%" },
    { c: "heat-2", l: "20–40%" },
    { c: "heat-3", l: "40–60%" },
    { c: "heat-4", l: "60–80%" },
    { c: "heat-5", l: "80–100%" },
  ];
  return (
    <div className="mt-3 flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
      <span className="uppercase tracking-widest">Escala de taxa de erro:</span>
      {bands.map((b) => (
        <span key={b.c} className="flex items-center gap-1">
          <span className={`inline-block w-4 h-3 border border-border ${b.c}`} />
          {b.l}
        </span>
      ))}
      <span className="flex items-center gap-1">
        <span className="sem-dado" style={{ padding: "0 6px" }}>Sem dado</span>
      </span>
    </div>
  );
}
