import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFilters } from "@/layout/AppLayout";
import { Panel, SemDado, formatPct, CalcBadge, EmptyState } from "@/components/common";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function AlunoView() {
  const { filters } = useFilters();
  const [alunos, setAlunos] = useState([]);
  const [alunoId, setAlunoId] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!filters.turma || !filters.periodo) return;
    api.get("/views/alunos", { params: { turma: filters.turma, periodo: filters.periodo } })
      .then(({ data }) => {
        setAlunos(data.alunos || []);
        setAlunoId((prev) => prev || data.alunos[0]?.aluno_id || "");
      });
  }, [filters.turma, filters.periodo]);

  useEffect(() => {
    if (!filters.turma || !filters.periodo || !alunoId) { setData(null); return; }
    setLoading(true);
    const params = { turma: filters.turma, periodo: filters.periodo, aluno_id: alunoId };
    if (filters.disciplina) params.disciplina = filters.disciplina;
    api.get("/views/aluno", { params })
      .then(({ data }) => setData(data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [filters.turma, filters.periodo, alunoId, filters.disciplina]);

  if (!filters.turma || !filters.periodo) {
    return <div className="p-6"><EmptyState hint="Selecione turma e período." /></div>;
  }

  return (
    <div className="p-6 space-y-4" data-testid="aluno-view">
      <div className="flex items-center gap-3">
        <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">Aluno</span>
        <Select value={alunoId} onValueChange={setAlunoId}>
          <SelectTrigger data-testid="aluno-select" className="h-8 min-w-[260px] text-xs">
            <SelectValue placeholder="Selecione um aluno" />
          </SelectTrigger>
          <SelectContent>
            {alunos.map((a) => (
              <SelectItem key={a.aluno_id} value={a.aluno_id}>
                {a.nome || "Sem nome"} · {a.aluno_id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading && <div className="text-sm text-muted-foreground">Carregando…</div>}

      {data && (
        <>
          <div className="border border-border p-4">
            <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Aluno</div>
            <div className="text-xl mt-0.5">{data.nome || <SemDado />}</div>
            <div className="text-[11px] font-mono text-muted-foreground mt-1">
              {data.aluno_id} · Turma {data.turma} · Período {data.periodo} · {data.versao_taxonomia}
            </div>
          </div>

          <Panel title="Desempenho por nó cognitivo"
                 subtitle="Comparado à média simples da turma"
                 right={<CalcBadge />}>
            <div className="overflow-x-auto border border-border">
              <table className="sapiens-table">
                <thead>
                  <tr>
                    <th>Disciplina</th>
                    <th>Nó</th>
                    <th className="num">Taxa erro (aluno)</th>
                    <th className="num">Média turma</th>
                    <th className="num">Δ aluno − turma</th>
                    <th className="num">Nº questões</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.length === 0 && (
                    <tr><td colSpan={6}><SemDado label="Sem nós para o filtro atual" /></td></tr>
                  )}
                  {data.rows.map((r) => {
                    const delta = r.taxa_erro_aluno != null && r.media_turma != null
                      ? r.taxa_erro_aluno - r.media_turma : null;
                    return (
                      <tr key={r.no_id}>
                        <td>{r.disciplina || <SemDado />}</td>
                        <td>
                          <div>{r.no_label || <SemDado />}</div>
                          <div className="text-[10px] font-mono text-muted-foreground">{r.no_id}</div>
                        </td>
                        <td className="num">{r.taxa_erro_aluno == null ? <SemDado /> : formatPct(r.taxa_erro_aluno)}</td>
                        <td className="num">{r.media_turma == null ? <SemDado /> : formatPct(r.media_turma)}</td>
                        <td className="num" style={{ color: delta == null ? undefined : delta > 0 ? "#B91C1C" : "#166534" }}>
                          {delta == null ? <SemDado /> : (delta > 0 ? "+" : "") + formatPct(delta)}
                        </td>
                        <td className="num">{r.num_questoes ?? <SemDado />}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
