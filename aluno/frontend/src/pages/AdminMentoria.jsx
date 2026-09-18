import { useEffect, useState } from "react";
import { MENTOR } from "../lib/mentor";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Medal, MessageCircle, Zap } from "lucide-react";

// Os VALORES são os que já estão gravados no banco desde a época de "aulas
// particulares" (ver `backend/mentoria_routes.py`); o que mudou é o rótulo,
// porque a coisa que eles descrevem hoje é uma FILA, não um pedido de aula.
const STATUS_OPTIONS = [
  { value: "pendente", label: "Na fila" },
  { value: "em_andamento", label: "Conversando" },
  { value: "concluida", label: "Virou mentoria" },
  { value: "cancelada", label: "Saiu da fila" },
];

const STATUS_STYLE = {
  pendente: "bg-amber-50 text-amber-700 border-amber-100",
  em_andamento: "bg-sky-50 text-sky-700 border-sky-100",
  concluida: "bg-emerald-50 text-emerald-700 border-emerald-100",
  cancelada: "bg-zinc-100 text-zinc-500 border-zinc-200",
};

function whatsappLink(raw) {
  const digitos = (raw || "").replace(/\D/g, "");
  const comPais = digitos.length <= 11 ? `55${digitos}` : digitos;
  return `https://wa.me/${comPais}`;
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function AdminMentoria() {
  const [requests, setRequests] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [filter, setFilter] = useState("");

  const load = () => api.get("/mentoria").then(({ data }) => { setRequests(data); setLoaded(true); });
  useEffect(() => { load(); }, []);

  const updateStatus = async (r, status) => {
    try {
      await api.patch(`/mentoria/${r.request_id}`, { status });
      toast.success("Status atualizado.");
      setRequests((prev) => prev.map((x) => (x.request_id === r.request_id ? { ...x, status } : x)));
    } catch (e) {
      toast.error(errMsg(e, "Falha ao atualizar status."));
    }
  };

  const visible = filter ? requests.filter((r) => r.status === filter) : requests;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="flex items-center gap-3 mb-3">
          <Medal className="w-4 h-4 text-sapiens-accent" />
          <div className="secao-olho">Admin · Mentoria</div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-mentoria-title">
          Lista de espera da mentoria
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Quem está esperando a mentoria com o {MENTOR.nome}, da chegada mais
          recente para a mais antiga. Fale pelo WhatsApp e mova a pessoa na fila — o aluno vê a
          própria posição, então tirar alguém de "na fila" muda o número que os outros enxergam.
        </p>

        <div className="mt-8 flex flex-wrap gap-2">
          <button
            onClick={() => setFilter("")}
            className={`pill text-xs font-medium px-3.5 py-2 rounded-full border ${filter === "" ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy" : "border-white/15 text-white/60 hover:text-white"}`}
            data-testid="admin-mentoria-filter-all"
          >
            Todos ({requests.length})
          </button>
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s.value}
              onClick={() => setFilter(s.value)}
              className={`pill text-xs font-medium px-3.5 py-2 rounded-full border ${filter === s.value ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy" : "border-white/15 text-white/60 hover:text-white"}`}
              data-testid={`admin-mentoria-filter-${s.value}`}
            >
              {s.label} ({requests.filter((r) => r.status === s.value).length})
            </button>
          ))}
        </div>

        <div className="mt-6 space-y-3">
          {loaded && visible.length === 0 && (
            <div className="card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
              Ninguém {filter ? "com esse status" : "na fila ainda"}.
            </div>
          )}
          {visible.map((r) => (
            <div key={r.request_id} className="card-sapiens rounded-2xl p-5" data-testid={`admin-mentoria-row-${r.request_id}`}>
              <div className="flex flex-col md:flex-row md:items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="font-display font-bold text-zinc-950">{r.nome_completo}</div>
                    <span className={`inline-flex items-center text-[11px] font-medium border px-2 py-0.5 rounded-full ${STATUS_STYLE[r.status] || STATUS_STYLE.pendente}`}>
                      {STATUS_OPTIONS.find((s) => s.value === r.status)?.label || r.status}
                    </span>
                  </div>
                  {/* Os TRÊS contatos, em linhas próprias. Até 2026-09-17 a
                      linha trazia só o WhatsApp: a fila passou a custar 50
                      Sparks, e quem pagou merece ser alcançável por mais de um
                      caminho — número trocado é a causa mais comum de um
                      pedido morrer sem resposta. `email` é `null` nos pedidos
                      anteriores a essa data, e a linha some sozinha. */}
                  <div className="mt-1 space-y-0.5 text-sm text-zinc-500">
                    {r.email && (
                      <div>
                        <a href={`mailto:${r.email}`} className="hover:text-zinc-900 hover:underline">
                          {r.email}
                        </a>
                      </div>
                    )}
                    <div className="flex flex-wrap items-center gap-x-2">
                      <span>{r.whatsapp}</span>
                      <span className="text-zinc-300">·</span>
                      <span>{formatDate(r.created_at)}</span>
                      {r.sparks_cobrados > 0 && (
                        <>
                          <span className="text-zinc-300">·</span>
                          <span className="inline-flex items-center gap-1 text-amber-700">
                            <Zap className="h-3 w-3" /> {r.sparks_cobrados} Sparks
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {r.areas.map((a) => (
                      <span key={a} className="text-[11px] bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full">{a}</span>
                    ))}
                  </div>
                  {r.descricao && (
                    <p className="mt-3 text-sm text-zinc-700 leading-relaxed">{r.descricao}</p>
                  )}
                </div>

                <div className="flex md:flex-col items-stretch gap-2 shrink-0 md:w-48">
                  <a
                    href={whatsappLink(r.whatsapp)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="pill btn-sapiens flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-full text-xs font-semibold"
                    data-testid={`admin-mentoria-whatsapp-${r.request_id}`}
                  >
                    <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
                  </a>
                  <select
                    value={r.status}
                    onChange={(e) => updateStatus(r, e.target.value)}
                    className="border border-zinc-200 rounded-xl px-3 py-2 text-xs bg-white outline-none focus:border-zinc-900"
                    data-testid={`admin-mentoria-status-${r.request_id}`}
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
