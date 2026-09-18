import { useEffect, useMemo, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Check, X, ChevronDown, ChevronRight, Filter, RefreshCw, Stethoscope } from "lucide-react";
import { RankingsPorNivel, PadraoCard, semDadosReais } from "../components/PerfilCognitivoView";
import { toast } from "sonner";

// Lê o schema canônico definido em
// pipeline/docs/behavior/07 behavior student 1.4.md — sem reshape de campos.
function Expandable({ ev }) {
  const [open, setOpen] = useState(false);
  const resposta = ev.resposta || {};
  const desempenho = ev.desempenho || {};
  const contexto = ev.contexto || {};
  const metadados = ev.metadados || {};
  return (
    <div className="card-sapiens rounded-2xl" data-testid={`hist-event-${ev.event_id}`}>
      <div className="p-4 flex items-center gap-4">
        <button onClick={() => setOpen(o => !o)} className="p-1 hover:bg-zinc-100 rounded" data-testid={`hist-toggle-${ev.event_id}`}>
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-mono-alt ${resposta.acertou ? "bg-emerald-500/10 text-emerald-700" : "bg-rose-500/10 text-rose-700"}`}>
          {resposta.acertou ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono-alt uppercase tracking-[0.2em] text-zinc-500">
            {ev.timestamp ? new Date(ev.timestamp).toLocaleString("pt-BR") : "—"} · {contexto.origem || "—"} · v{ev.item_schema_version || "?"}
          </div>
          <div className="mt-1 font-display font-semibold text-zinc-900 truncate">{ev.item_id}</div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs font-mono-alt text-zinc-500">escolhida</div>
          <div className="font-display text-lg font-bold text-zinc-900">{resposta.alternativa_escolhida || "—"}</div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs font-mono-alt text-zinc-500">tempo</div>
          <div className="font-display text-sm font-semibold text-zinc-900">
            {desempenho.tempo_resposta_segundos != null ? `${Math.round(desempenho.tempo_resposta_segundos)}s` : "—"}
          </div>
        </div>
        <span className={`text-[10px] font-mono-alt uppercase tracking-[0.25em] px-2 py-1 rounded-full ${
          ev.status === "anulada" ? "bg-amber-50 text-amber-700"
          : ev.status === "cancelada" ? "bg-zinc-100 text-zinc-500"
          : ev.status === "corrigida" ? "bg-blue-50 text-blue-700"
          : "bg-emerald-50 text-emerald-700"
        }`}>{ev.status || "respondida"}</span>
      </div>
      {open && (
        <div className="border-t border-zinc-100 p-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500 mb-2">Contexto</div>
            <div className="text-zinc-700 space-y-1">
              <div>Aluno: <span className="font-mono-alt">{ev.student_id}</span></div>
              <div>Tentativa: <span className="font-mono-alt">{ev.attempt_id}</span></div>
              <div>Prova: {contexto.prova_id || "—"}</div>
              <div>Tentativas: {desempenho.numero_tentativas ?? "—"} {desempenho.mudou_resposta ? "(mudou de resposta)" : ""}</div>
              <div className="text-xs text-zinc-500">item_hash: <span className="font-mono-alt">{ev.item_hash?.slice(0, 16) || "—"}…</span></div>
            </div>
          </div>
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500 mb-2">Metadados técnicos</div>
            <div className="text-zinc-700 space-y-1">
              <div>Dispositivo: {metadados.dispositivo || "—"}</div>
              <div>Versão do app: {metadados.versao_aplicacao || "—"}</div>
              <div>schema_version: <span className="font-mono-alt">{ev.schema_version || "—"}</span></div>
              {/* Obrigatório desde o behavior 1.1: sem ele o evento é indatável
                  e não pode ser reinterpretado numa mudança MAIOR da ontologia. */}
              <div>ontology_version: <span className="font-mono-alt">{ev.ontology_version || "—"}</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Narrativa (briefing gerado por IA, no máximo 1x por semana por aluno — ver
// `perfil_cognitivo_service.py`) e o histórico de snapshots semanais, que dão
// o "evoluiu ou piorou" que o desempenho ao vivo sozinho não mostra.
function PerfilCognitivo({ studentId, perfil, perfilLoading, perfilError, historico, onAtualizar, atualizando }) {
  if (perfilLoading) return <div className="mt-8 text-white/60">Carregando perfil cognitivo...</div>;
  if (perfilError) return <div className="mt-8 text-white/60" data-testid="perfil-erro">{perfilError}</div>;
  if (!perfil) return null;

  const vazio = semDadosReais(perfil);

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 font-mono-alt text-xs uppercase tracking-[0.3em] text-white/50">
          <Stethoscope className="w-3.5 h-3.5" /> Perfil cognitivo real
          {perfil.periodo && <span className="text-white/30">· {perfil.periodo}</span>}
        </div>
        <button
          onClick={() => onAtualizar(studentId)}
          disabled={atualizando}
          className="pill text-xs font-medium btn-sapiens flex items-center gap-1.5 px-3 py-1.5 rounded-full disabled:opacity-50"
          data-testid="perfil-atualizar-btn"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${atualizando ? "animate-spin" : ""}`} /> Atualizar agora
        </button>
      </div>

      {vazio ? (
        <div className="mt-4 card-sapiens rounded-2xl p-6 text-center">
          <div className="font-display font-bold text-lg text-zinc-950">Ainda sem amostra suficiente.</div>
          <p className="mt-2 text-sm text-zinc-500">Este aluno precisa responder mais questões num mesmo processo cognitivo (mínimo: {perfil.amostra_minima}).</p>
        </div>
      ) : (
        <>
          {perfil.narrativa && (
            <div className="mt-4 card-sapiens rounded-2xl p-5 md:p-6" data-testid="perfil-narrativa">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400 mb-2">Briefing (IA, gerado 1x/semana)</div>
              <p className="text-sm text-zinc-700 leading-relaxed whitespace-pre-line">{perfil.narrativa}</p>
            </div>
          )}
          <div className="mt-4">
            <RankingsPorNivel data={perfil} />
          </div>
          {perfil.padroes_associados?.length > 0 && (
            <div className="mt-4 space-y-4">
              {perfil.padroes_associados.map((p) => <PadraoCard key={p.processo_id} padrao={p} />)}
            </div>
          )}
        </>
      )}

      {historico?.length > 1 && (
        <div className="mt-4 card-sapiens rounded-2xl p-5 md:p-6 overflow-x-auto" data-testid="perfil-historico">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400 mb-3">Evolução por período</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-zinc-400 text-xs uppercase tracking-wide">
                <th className="pb-2 pr-4">Período</th>
                <th className="pb-2 pr-4">Cobertura</th>
                <th className="pb-2">Maior ponto de atenção</th>
              </tr>
            </thead>
            <tbody>
              {historico.map((h) => {
                const pior = h.por_processo?.fracos?.[0];
                return (
                  <tr key={h.periodo} className="border-t border-zinc-100">
                    <td className="py-2 pr-4 font-mono-alt text-zinc-700">{h.periodo}</td>
                    <td className="py-2 pr-4 text-zinc-600">{h.coverage}%</td>
                    <td className="py-2 text-zinc-600">
                      {pior ? `${pior.nome} (${pior.percentual_acerto}%)` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function StudentHistory() {
  const [students, setStudents] = useState([]);
  const [aluno, setAluno] = useState("");
  const [history, setHistory] = useState(null);
  const [perfil, setPerfil] = useState(null);
  const [perfilHistorico, setPerfilHistorico] = useState([]);
  const [perfilLoading, setPerfilLoading] = useState(false);
  const [perfilError, setPerfilError] = useState(null);
  const [atualizando, setAtualizando] = useState(false);

  useEffect(() => { api.get("/students").then(({ data }) => setStudents(data)); }, []);

  const loadPerfil = async (studentId) => {
    setPerfilLoading(true);
    setPerfilError(null);
    try {
      const [{ data: atual }, { data: hist }] = await Promise.all([
        api.get(`/students/${encodeURIComponent(studentId)}/perfil`),
        api.get(`/students/${encodeURIComponent(studentId)}/perfil/historico`),
      ]);
      setPerfil(atual);
      setPerfilHistorico(hist.snapshots || []);
    } catch (e) {
      setPerfilError(errMsg(e, "Não foi possível carregar o perfil cognitivo."));
    } finally {
      setPerfilLoading(false);
    }
  };

  const atualizarPerfil = async (studentId) => {
    setAtualizando(true);
    try {
      await api.post(`/students/${encodeURIComponent(studentId)}/perfil/atualizar`);
      await loadPerfil(studentId);
      toast.success("Perfil cognitivo atualizado.");
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível atualizar agora."));
    } finally {
      setAtualizando(false);
    }
  };

  const load = async (studentId) => {
    if (!studentId) return;
    const { data } = await api.get(`/students/${encodeURIComponent(studentId)}/history`);
    setHistory(data);
    loadPerfil(studentId);
  };

  const grouped = useMemo(() => {
    if (!history) return [];
    const byDay = new Map();
    for (const ev of history.events) {
      const d = ev.timestamp ? new Date(ev.timestamp).toLocaleDateString("pt-BR") : "sem data";
      if (!byDay.has(d)) byDay.set(d, []);
      byDay.get(d).push(ev);
    }
    return Array.from(byDay.entries());
  }, [history]);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="secao-olho">Admin · Histórico do Aluno</div>
        <h1 className="titulo-tela" data-testid="hist-title">
          Behavior Event Store
        </h1>
        <p className="mt-3 text-white/60 max-w-2xl">
          Fonte única: <code className="font-mono-alt text-xs">students/{"{uid}"}/behavior</code> no Firestore, no schema
          definido em <code className="font-mono-alt text-xs">pipeline/docs/behavior</code>. Append-only — cada evento é imutável.
        </p>

        {/* Filters */}
        <div className="mt-8 card-sapiens rounded-2xl p-5">
          <div className="flex items-center gap-2 text-xs font-mono-alt uppercase tracking-[0.25em] text-zinc-500 mb-4">
            <Filter className="w-3.5 h-3.5" /> Aluno
          </div>
          <select value={aluno} onChange={e => { setAluno(e.target.value); load(e.target.value); }}
            className="border border-zinc-200 rounded-xl px-3 py-2 text-sm bg-white outline-none focus:border-zinc-900 w-full md:w-96"
            data-testid="hist-student-select">
            <option value="">Selecione o aluno…</option>
            {students.map(s => (
              <option key={s.student_id} value={s.student_id}>
                {s.nome || s.student_id} · {s.count} evento(s)
              </option>
            ))}
          </select>
        </div>

        {/* Summary */}
        {history?.summary && (
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatMini label="Eventos" value={history.summary.total} />
            <StatMini label="Acurácia" value={`${history.summary.accuracy}%`} />
            <StatMini label="Tempo médio" value={`${history.summary.avg_tempo_resposta_segundos}s`} />
            <StatMini label="Status" value={Object.entries(history.summary.by_status || {}).map(([k, v]) => `${k}:${v}`).join(" · ") || "—"} />
          </div>
        )}

        {/* Perfil cognitivo real (parametrizado) */}
        {history && (
          <PerfilCognitivo
            studentId={aluno}
            perfil={perfil}
            perfilLoading={perfilLoading}
            perfilError={perfilError}
            historico={perfilHistorico}
            onAtualizar={atualizarPerfil}
            atualizando={atualizando}
          />
        )}

        {/* Timeline (bruta, evento a evento) */}
        {history && (
          <div className="mt-10 space-y-6">
            <div className="font-mono-alt text-xs uppercase tracking-[0.3em] text-white/50">Eventos brutos</div>
            {grouped.length === 0 && <div className="text-white/60">Sem eventos registrados para este aluno.</div>}
            {grouped.map(([day, entries]) => (
              <div key={day}>
                <div className="font-mono-alt text-xs uppercase tracking-[0.3em] text-white/50 mb-2">{day}</div>
                <div className="space-y-2">
                  {entries.map(ev => <Expandable key={ev.event_id} ev={ev} />)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatMini({ label, value }) {
  return (
    <div className="card-sapiens rounded-2xl p-4">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">{label}</div>
      <div className="mt-1 font-display text-xl font-extrabold tracking-tighter text-zinc-950">{value ?? "—"}</div>
    </div>
  );
}
