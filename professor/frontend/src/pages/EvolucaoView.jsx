import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFilters } from "@/layout/AppLayout";
import { Panel, SemDado, formatPct, CalcBadge, EmptyState } from "@/components/common";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";

export default function EvolucaoView() {
  const { filters } = useFilters();
  const [nos, setNos] = useState([]);
  const [noId, setNoId] = useState("");
  const [alunos, setAlunos] = useState([]);
  const [alunoId, setAlunoId] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!filters.turma) return;
    // Fetch turma at first period to populate options
    if (filters.periodo) {
      api.get("/views/turma", { params: { turma: filters.turma, periodo: filters.periodo } })
        .then(({ data }) => setNos(data.nos || [])).catch(() => setNos([]));
      api.get("/views/alunos", { params: { turma: filters.turma, periodo: filters.periodo } })
        .then(({ data }) => setAlunos(data.alunos || [])).catch(() => setAlunos([]));
    }
  }, [filters.turma, filters.periodo]);

  useEffect(() => {
    if (!filters.turma) { setData(null); return; }
    const params = { turma: filters.turma };
    if (noId) params.no_id = noId;
    if (alunoId) params.aluno_id = alunoId;
    if (filters.disciplina) params.disciplina = filters.disciplina;
    api.get("/views/evolucao", { params })
      .then(({ data }) => setData(data))
      .catch(() => setData(null));
  }, [filters.turma, noId, alunoId, filters.disciplina]);

  if (!filters.turma) {
    return <div className="p-6"><EmptyState hint="Selecione uma turma." /></div>;
  }

  const chartData = (data?.series || []).map((s) => ({
    periodo: s.periodo,
    taxa: s.media_taxa_erro == null ? null : Number((s.media_taxa_erro * 100).toFixed(2)),
    versao: s.versao_taxonomia,
  }));

  return (
    <div className="p-6 space-y-4" data-testid="evolucao-view">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">Nó</span>
          <Select value={noId || "__all__"} onValueChange={(v) => setNoId(v === "__all__" ? "" : v)}>
            <SelectTrigger data-testid="evolucao-no-select" className="h-8 min-w-[240px] text-xs">
              <SelectValue placeholder="Todos os nós" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Todos os nós (média)</SelectItem>
              {nos.map((n) => (
                <SelectItem key={n.no_id} value={n.no_id}>{n.no_label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">Aluno</span>
          <Select value={alunoId || "__all__"} onValueChange={(v) => setAlunoId(v === "__all__" ? "" : v)}>
            <SelectTrigger data-testid="evolucao-aluno-select" className="h-8 min-w-[220px] text-xs">
              <SelectValue placeholder="Turma inteira" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Turma inteira</SelectItem>
              {alunos.map((a) => (
                <SelectItem key={a.aluno_id} value={a.aluno_id}>{a.nome || a.aluno_id}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {data?.versoes_multiplas && (
        <div
          data-testid="version-warning"
          className="border-l-4 border-amber-500 bg-amber-50 p-3 text-sm"
        >
          <strong className="font-mono uppercase text-[11px] tracking-widest">Aviso</strong>{" "}
          Comparação entre períodos com versões diferentes de taxonomia:{" "}
          <span className="font-mono">{(data.versoes_encontradas || []).join(" · ")}</span>. IDs
          e descrições de nós podem ter mudado entre versões.
        </div>
      )}

      <Panel
        title="Evolução da taxa de erro média entre períodos"
        subtitle={`Turma ${data?.turma || filters.turma}`}
        right={<CalcBadge />}
      >
        {chartData.some((c) => c.taxa != null) ? (
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="1 3" stroke="#e5e5e5" vertical={false} />
                <XAxis dataKey="periodo" tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                <Tooltip
                  contentStyle={{ borderRadius: 0, border: "1px solid #e5e5e5", fontSize: 12 }}
                  formatter={(v) => v == null ? "Sem dado" : `${v}%`}
                  labelFormatter={(l) => `Período ${l}`}
                />
                <Line type="linear" dataKey="taxa" stroke="#0047AB" strokeWidth={2}
                      dot={{ r: 4, fill: "#0047AB" }} isAnimationActive={false}
                      connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState title="Sem dado" hint="Não há valores agregáveis para os filtros atuais." />
        )}

        <div className="mt-4 overflow-x-auto border border-border">
          <table className="sapiens-table">
            <thead>
              <tr>
                <th>Período</th>
                <th>Versão taxonomia</th>
                <th className="num">Taxa erro média</th>
                <th className="num">Nº alunos</th>
                <th className="num">Nº questões</th>
              </tr>
            </thead>
            <tbody>
              {(data?.series || []).map((s) => (
                <tr key={s.periodo}>
                  <td className="font-mono">{s.periodo || <SemDado />}</td>
                  <td className="text-xs font-mono">{s.versao_taxonomia || <SemDado />}</td>
                  <td className="num">{s.media_taxa_erro == null ? <SemDado /> : formatPct(s.media_taxa_erro)}</td>
                  <td className="num">{s.num_alunos ?? <SemDado />}</td>
                  <td className="num">{s.num_questoes ?? <SemDado />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
