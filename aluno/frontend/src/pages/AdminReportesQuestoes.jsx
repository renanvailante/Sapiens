import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Flag, Check, X, Sparkles } from "lucide-react";

const STATUS_STYLE = {
  pendente: "bg-amber-50 text-amber-700 border-amber-100",
  aprovada: "bg-emerald-50 text-emerald-700 border-emerald-100",
  rejeitada: "bg-zinc-100 text-zinc-500 border-zinc-200",
};

const STATUS_LABEL = { pendente: "Pendente", aprovada: "Aprovada", rejeitada: "Rejeitada" };

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function AdminReportesQuestoes() {
  const [items, setItems] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [filter, setFilter] = useState("pendente");
  const [busyId, setBusyId] = useState(null);

  const load = () =>
    api.get("/admin/reportes-questoes").then(({ data }) => {
      setItems(data.items);
      setLoaded(true);
    });
  useEffect(() => { load(); }, []);

  const visible = filter ? items.filter((r) => r.status === filter) : items;

  // Índice por questão: cada item_id vira um grupo, com todas as
  // reclamações daquela questão juntas — é o "índice" pedido, para o admin
  // ver de uma vez tudo que já foi dito sobre a mesma questão.
  const grupos = useMemo(() => {
    const porItem = new Map();
    for (const r of visible) {
      if (!porItem.has(r.item_id)) porItem.set(r.item_id, []);
      porItem.get(r.item_id).push(r);
    }
    return Array.from(porItem.entries());
  }, [visible]);

  const resolver = async (r, acao) => {
    setBusyId(r.report_id);
    try {
      const { data } = await api.post(`/admin/reportes-questoes/${r.report_id}/${acao}`);
      setItems((prev) => prev.map((x) => (x.report_id === r.report_id ? { ...x, status: acao === "aprovar" ? "aprovada" : "rejeitada" } : x)));
      if (acao === "aprovar") {
        toast.success(`Aprovado — ${r.student_nome} ganhou ${data.sparks_creditados} Sparks.`);
      } else {
        toast.message("Sugestão rejeitada.");
      }
    } catch (e) {
      toast.error(errMsg(e, "Falha ao processar."));
    } finally {
      setBusyId(null);
    }
  };

  const contagem = (status) => items.filter((r) => r.status === status).length;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="flex items-center gap-3 mb-3">
          <Flag className="w-4 h-4 text-sapiens-accent" />
          <div className="secao-olho">Admin · Sugestões de correção</div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-reportes-title">
          O que os alunos reportaram
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">
          Agrupado por questão. Aprovar credita 5 Sparks para o aluno que reportou.
        </p>

        <div className="mt-8 flex flex-wrap gap-2">
          <button
            onClick={() => setFilter("")}
            className={`pill text-xs font-medium px-3.5 py-2 rounded-full border ${filter === "" ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy" : "border-white/15 text-white/60 hover:text-white"}`}
            data-testid="admin-reportes-filter-all"
          >
            Todas ({items.length})
          </button>
          {Object.keys(STATUS_LABEL).map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`pill text-xs font-medium px-3.5 py-2 rounded-full border ${filter === s ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy" : "border-white/15 text-white/60 hover:text-white"}`}
              data-testid={`admin-reportes-filter-${s}`}
            >
              {STATUS_LABEL[s]} ({contagem(s)})
            </button>
          ))}
        </div>

        <div className="mt-6 space-y-6">
          {loaded && grupos.length === 0 && (
            <div className="card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
              Nenhuma sugestão {filter ? "com esse status" : "ainda"}.
            </div>
          )}
          {grupos.map(([itemId, reportes]) => (
            <div key={itemId} className="card-sapiens rounded-2xl p-5" data-testid={`admin-reportes-grupo-${itemId}`}>
              <div className="font-mono-alt text-xs text-zinc-500 mb-3">
                Questão <span className="font-bold text-zinc-800">{itemId}</span> · {reportes.length} sugestão(ões)
              </div>
              <div className="space-y-3 divide-y divide-zinc-100">
                {reportes.map((r) => (
                  <div key={r.report_id} className="pt-3 first:pt-0" data-testid={`admin-reportes-row-${r.report_id}`}>
                    <div className="flex flex-col md:flex-row md:items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <div className="font-semibold text-zinc-900 text-sm">{r.student_nome}</div>
                          <span className="font-mono-alt text-[10px] text-zinc-400">{r.student_id}</span>
                          <span className={`inline-flex items-center text-[11px] font-medium border px-2 py-0.5 rounded-full ${STATUS_STYLE[r.status] || STATUS_STYLE.pendente}`}>
                            {STATUS_LABEL[r.status] || r.status}
                          </span>
                        </div>
                        <div className="mt-0.5 text-xs text-zinc-400">{formatDate(r.created_at)}</div>
                        <p className="mt-2 text-sm text-zinc-700 leading-relaxed">{r.texto}</p>
                      </div>
                      {r.status === "pendente" && (
                        <div className="flex items-stretch gap-2 shrink-0">
                          <button
                            onClick={() => resolver(r, "aprovar")}
                            disabled={busyId === r.report_id}
                            className="pill inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-semibold border border-emerald-200 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                            data-testid={`admin-reportes-aprovar-${r.report_id}`}
                          >
                            <Check className="w-3.5 h-3.5" /> Aprovar · <Sparkles className="w-3 h-3" />5
                          </button>
                          <button
                            onClick={() => resolver(r, "rejeitar")}
                            disabled={busyId === r.report_id}
                            className="pill inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-semibold border border-zinc-200 text-zinc-500 hover:bg-zinc-50 disabled:opacity-50"
                            data-testid={`admin-reportes-rejeitar-${r.report_id}`}
                          >
                            <X className="w-3.5 h-3.5" /> Rejeitar
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
