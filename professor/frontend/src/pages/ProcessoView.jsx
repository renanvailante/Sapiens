import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useFilters } from "@/layout/AppLayout";
import { Panel, SemDado, formatPct, CalcBadge, StatCard, EmptyState } from "@/components/common";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";

export default function ProcessoView() {
  const { filters } = useFilters();
  const [nos, setNos] = useState([]);
  const [noId, setNoId] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  // load list of nós from turma view first
  useEffect(() => {
    if (!filters.turma || !filters.periodo) return;
    api.get("/views/turma", { params: { turma: filters.turma, periodo: filters.periodo } })
      .then(({ data }) => {
        setNos(data.nos || []);
        setNoId((prev) => prev || (data.nos[0]?.no_id ?? ""));
      })
      .catch(() => setNos([]));
  }, [filters.turma, filters.periodo]);

  useEffect(() => {
    if (!filters.turma || !filters.periodo || !noId) { setData(null); return; }
    setLoading(true);
    api.get("/views/processo", { params: { turma: filters.turma, periodo: filters.periodo, no_id: noId } })
      .then(({ data }) => setData(data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [filters.turma, filters.periodo, noId]);

  if (!filters.turma || !filters.periodo) {
    return <div className="p-6"><EmptyState hint="Selecione turma e período." /></div>;
  }

  return (
    <div className="p-6 space-y-4" data-testid="processo-view">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-[11px] font-mono uppercase tracking-widest text-muted-foreground">Processo cognitivo (nó)</span>
        <Select value={noId} onValueChange={setNoId}>
          <SelectTrigger data-testid="processo-no-select" className="h-8 min-w-[300px] text-xs">
            <SelectValue placeholder="Selecione um nó" />
          </SelectTrigger>
          <SelectContent>
            {nos.map((n) => (
              <SelectItem key={n.no_id} value={n.no_id}>
                {n.disciplina} · {n.no_label} <span className="font-mono text-muted-foreground">({n.no_id})</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading && <div className="text-sm text-muted-foreground">Carregando…</div>}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Média da taxa de erro" value={formatPct(data.media_taxa_erro)} testid="stat-media" />
            <StatCard label="Total de alunos" value={data.total_alunos} />
            <StatCard label="Total de questões (soma)" value={data.total_questoes} />
            <div className="border border-border p-4">
              <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Disciplina(s)</div>
              <div className="mt-1 text-sm">
                {data.disciplinas?.length ? data.disciplinas.join(", ") : <SemDado />}
              </div>
              <div className="mt-2"><CalcBadge /></div>
            </div>
          </div>

          <Panel title="Distribuição de alunos por faixa de taxa de erro"
                 subtitle={`Nó: ${data.no_label || data.no_id}`}
                 right={<CalcBadge />}>
            {data.distribuicao?.some((d) => d.alunos > 0) ? (
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <BarChart data={data.distribuicao}>
                    <CartesianGrid strokeDasharray="1 3" stroke="#e5e5e5" vertical={false} />
                    <XAxis dataKey="faixa" tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                    <Tooltip cursor={{ fill: "#f3f4f6" }} contentStyle={{ borderRadius: 0, border: "1px solid #e5e5e5", fontSize: 12 }} />
                    <Bar dataKey="alunos" fill="#0047AB" isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <EmptyState title="Sem dado" hint="Nenhum aluno com taxa de erro registrada para este nó." />}
          </Panel>

          <Panel title="Alunos neste processo cognitivo" subtitle={`${data.alunos.length} alunos`}>
            <div className="overflow-x-auto border border-border">
              <table className="sapiens-table">
                <thead>
                  <tr>
                    <th>Aluno</th>
                    <th className="num">Taxa de erro</th>
                    <th className="num">Nº de questões</th>
                  </tr>
                </thead>
                <tbody>
                  {data.alunos.map((a) => (
                    <tr key={a.aluno_id}>
                      <td>
                        <div className="text-[11px] font-mono text-muted-foreground">{a.aluno_id}</div>
                        <div>{a.nome || <SemDado />}</div>
                      </td>
                      <td className="num">{a.taxa_erro == null ? <SemDado /> : formatPct(a.taxa_erro)}</td>
                      <td className="num">{a.num_questoes ?? <SemDado />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
