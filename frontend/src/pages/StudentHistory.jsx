import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { Check, X, ChevronDown, ChevronRight, Filter } from "lucide-react";

function Expandable({ entry }) {
  const [open, setOpen] = useState(false);
  const ev = entry.event;
  const item = entry.item || {};
  const gabarito = item.payload?.item?.gabarito;
  const processos = item.payload?.processos_ativados || [];
  const distratores = item.payload?.analise_distratores || [];
  const distractor = distratores.find(d => d.alternativa === ev.alternativa_escolhida);
  return (
    <div className="bg-white border border-zinc-200 rounded-2xl" data-testid={`hist-event-${ev.evento_id}`}>
      <div className="p-4 flex items-center gap-4">
        <button onClick={() => setOpen(o => !o)} className="p-1 hover:bg-zinc-100 rounded" data-testid={`hist-toggle-${ev.evento_id}`}>
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono-alt ${ev.acertou ? "bg-emerald-500/10 text-emerald-700" : "bg-rose-500/10 text-rose-700"}`}>
          {ev.acertou ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">
            {new Date(ev.data_hora_resposta).toLocaleString("pt-BR")} · {ev.contexto?.origem || "—"} · v{ev.item_schema_version}
          </div>
          <div className="mt-1 font-display font-semibold text-zinc-900 truncate">
            {ev.item_id} <span className="text-zinc-400 font-normal">— {item.disciplina || "sem anotação"}</span>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs font-mono-alt text-zinc-500">escolhida</div>
          <div className="font-display text-lg font-bold text-zinc-900">{ev.alternativa_escolhida}</div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs font-mono-alt text-zinc-500">gabarito</div>
          <div className="font-display text-lg font-bold text-emerald-600">{gabarito || "?"}</div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs font-mono-alt text-zinc-500">tempo</div>
          <div className="font-display text-sm font-semibold text-zinc-900">{Math.round(ev.tempo_resposta_seg)}s</div>
        </div>
        <span className={`text-[10px] font-mono-alt uppercase tracking-[0.25em] px-2 py-1 rounded-full ${
          ev.status === "anulada" ? "bg-amber-50 text-amber-700"
          : ev.status === "cancelada" ? "bg-zinc-100 text-zinc-500"
          : ev.status === "corrigida" ? "bg-blue-50 text-blue-700"
          : "bg-emerald-50 text-emerald-700"
        }`}>{ev.status}</span>
      </div>
      {open && (
        <div className="border-t border-zinc-100 p-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500 mb-2">Contexto</div>
            <div className="text-zinc-700 space-y-1">
              <div>Aluno: <span className="font-mono-alt">{ev.aluno_id}</span></div>
              <div>Turma: {ev.turma || "—"}</div>
              <div>Avaliação: {ev.contexto?.avaliacao_id || "—"} / sessão {ev.contexto?.sessao_id || "—"}</div>
              <div>Versão da prova: {ev.contexto?.versao_prova || "—"}</div>
              <div className="text-xs text-zinc-500">item_hash: <span className="font-mono-alt">{ev.item_hash?.slice(0, 16)}…</span></div>
            </div>
          </div>
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500 mb-2">Cognição (via join com ITEM)</div>
            {item.payload ? (
              <div className="space-y-2 text-zinc-700">
                <div>Processos ativados: {processos.map(p => <span key={p.cognitive_process_id} className="mr-1 px-1.5 py-0.5 rounded bg-zinc-100 text-xs font-mono-alt">{p.cognitive_process_id}</span>)}</div>
                {!ev.acertou && distractor && (
                  <div className="mt-2 rounded-xl bg-rose-50 border border-rose-100 p-3">
                    <div className="text-[10px] font-mono-alt uppercase tracking-[0.2em] text-rose-700">Erro na alternativa {distractor.alternativa} · tipo #{distractor.error_type_id}</div>
                    <div className="mt-1 text-sm text-zinc-800">{distractor.explicacao}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-zinc-500 text-xs">Sem anotação disponível para este ITEM.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function StudentHistory() {
  const [students, setStudents] = useState([]);
  const [aluno, setAluno] = useState("");
  const [origem, setOrigem] = useState("");
  const [disciplina, setDisciplina] = useState("");
  const [fromISO, setFromISO] = useState("");
  const [toISO, setToISO] = useState("");
  const [history, setHistory] = useState(null);

  useEffect(() => { api.get("/students").then(({ data }) => setStudents(data)); }, []);

  const load = async (studentId) => {
    if (!studentId) return;
    const params = {};
    if (origem) params.origem = origem;
    if (disciplina) params.disciplina = disciplina;
    if (fromISO) params.from = new Date(fromISO).toISOString();
    if (toISO) params.to = new Date(toISO).toISOString();
    const { data } = await api.get(`/students/${encodeURIComponent(studentId)}/history`, { params });
    setHistory(data);
  };

  const grouped = useMemo(() => {
    if (!history) return [];
    const byDay = new Map();
    for (const r of history.responses) {
      const d = new Date(r.event.data_hora_resposta).toLocaleDateString("pt-BR");
      if (!byDay.has(d)) byDay.set(d, []);
      byDay.get(d).push(r);
    }
    return Array.from(byDay.entries());
  }, [history]);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Admin · Histórico do Aluno</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="hist-title">
          Response Event Store
        </h1>
        <p className="mt-3 text-zinc-500 max-w-2xl">
          Fonte única e permanente das respostas. Append-only. Cada evento é imutável — anulações e correções geram novo evento com o mesmo <code className="font-mono-alt text-xs">attempt_id</code>. Cognição vem via <b>join</b> com a anotação do ITEM, nunca duplicada aqui.
        </p>

        {/* Filters */}
        <div className="mt-8 bg-white border border-zinc-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 text-xs font-mono-alt uppercase tracking-[0.25em] text-zinc-500 mb-4">
            <Filter className="w-3.5 h-3.5" /> Filtros
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <select value={aluno} onChange={e => { setAluno(e.target.value); load(e.target.value); }}
              className="border border-zinc-200 rounded-xl px-3 py-2 text-sm bg-white outline-none focus:border-zinc-900"
              data-testid="hist-student-select">
              <option value="">Selecione o aluno…</option>
              {students.map(s => (
                <option key={s.aluno_id} value={s.aluno_id}>
                  {s.aluno_id} {s.turma ? `(${s.turma})` : ""} · {s.count} resp.
                </option>
              ))}
            </select>
            <input value={origem} onChange={e => setOrigem(e.target.value)} placeholder="origem: simulado, prova…"
              className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900" data-testid="hist-origem" />
            <input value={disciplina} onChange={e => setDisciplina(e.target.value)} placeholder="disciplina"
              className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900" data-testid="hist-disciplina" />
            <input type="date" value={fromISO} onChange={e => setFromISO(e.target.value)}
              className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900" data-testid="hist-from" />
            <input type="date" value={toISO} onChange={e => setToISO(e.target.value)}
              className="border border-zinc-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-zinc-900" data-testid="hist-to" />
          </div>
          <button onClick={() => load(aluno)}
            className="pill mt-4 bg-zinc-950 hover:bg-zinc-800 text-white px-5 py-2 rounded-full text-sm font-medium"
            data-testid="hist-apply">Aplicar</button>
        </div>

        {/* Summary */}
        {history?.summary && (
          <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatMini label="Respostas" value={history.summary.total_responses} />
            <StatMini label="Acurácia" value={`${history.summary.accuracy}%`} />
            <StatMini label="Tempo médio" value={`${history.summary.avg_time_seg}s`} />
            <StatMini label="Intervenções" value={history.summary.interventions_count} />
            <StatMini label="Status" value={Object.entries(history.summary.by_status || {}).map(([k, v]) => `${k}:${v}`).join(" · ") || "—"} />
          </div>
        )}

        {/* Timeline */}
        {history && (
          <div className="mt-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-2 space-y-6">
                <div className="font-display font-bold text-xl tracking-tight text-zinc-950">Respostas</div>
                {grouped.length === 0 && <div className="text-zinc-500">Sem respostas para os filtros.</div>}
                {grouped.map(([day, entries]) => (
                  <div key={day}>
                    <div className="font-mono-alt text-xs uppercase tracking-[0.3em] text-zinc-500 mb-2">{day}</div>
                    <div className="space-y-2">
                      {entries.map(entry => <Expandable key={entry.event.evento_id} entry={entry} />)}
                    </div>
                  </div>
                ))}
              </div>
              <div className="md:col-span-1">
                <div className="font-display font-bold text-xl tracking-tight text-zinc-950 mb-3">Intervenções</div>
                {history.interventions.length === 0 ? (
                  <div className="text-sm text-zinc-500 bg-white border border-zinc-200 rounded-2xl p-4">
                    Nenhuma intervenção pedagógica registrada.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {history.interventions.map(i => (
                      <div key={i.evento_id} className="bg-white border border-zinc-200 rounded-2xl p-4" data-testid={`hist-interv-${i.evento_id}`}>
                        <div className="text-[10px] font-mono-alt uppercase tracking-[0.3em] text-zinc-500">
                          {new Date(i.data_hora_aplicacao).toLocaleString("pt-BR")}
                        </div>
                        <div className="mt-1 font-display font-semibold text-zinc-900">{i.tipo_intervencao}</div>
                        <div className="text-sm text-zinc-600">Processo: <span className="font-mono-alt">{i.cognitive_process_id}</span></div>
                        <div className="text-xs text-zinc-500">Aplicada por: {i.aplicada_por}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatMini({ label, value }) {
  return (
    <div className="bg-white border border-zinc-200 rounded-2xl p-4">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">{label}</div>
      <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">{value ?? "—"}</div>
    </div>
  );
}
