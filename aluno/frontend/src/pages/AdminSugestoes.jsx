import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { MessageSquareWarning, Lightbulb, Bug, Heart, Send, Check, Loader2 } from "lucide-react";

// Fila de leitura das reclamações e sugestões dos alunos. Espelha os estados
// de `sugestoes_routes.py`: nova -> lida -> respondida. Responder é o único
// caminho para o estado final, porque é o único que devolve algo ao aluno.

const TIPO_META = {
  reclamacao: { rotulo: "Reclamação", icone: MessageSquareWarning },
  sugestao: { rotulo: "Sugestão", icone: Lightbulb },
  problema: { rotulo: "Algo quebrado", icone: Bug },
  elogio: { rotulo: "Elogio", icone: Heart },
};

const STATUS_CLS = {
  nova: "bg-amber-50 text-amber-700 border-amber-100",
  lida: "bg-sky-50 text-sky-700 border-sky-100",
  respondida: "bg-emerald-50 text-emerald-700 border-emerald-100",
};
const STATUS_LABEL = { nova: "Nova", lida: "Lida", respondida: "Respondida" };
const FILTROS = [
  { id: "", rotulo: "Todas" },
  { id: "nova", rotulo: "Novas" },
  { id: "lida", rotulo: "Lidas" },
  { id: "respondida", rotulo: "Respondidas" },
];

function formatarData(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function AdminSugestoes() {
  const [items, setItems] = useState([]);
  const [carregado, setCarregado] = useState(false);
  const [filtro, setFiltro] = useState("nova");
  const [rascunhos, setRascunhos] = useState({});
  const [ocupado, setOcupado] = useState(null);

  const carregar = () =>
    api
      .get("/admin/sugestoes")
      .then(({ data }) => setItems(data.items || []))
      .catch((e) => toast.error(errMsg(e, "Falha ao carregar as mensagens.")))
      .finally(() => setCarregado(true));

  useEffect(() => { carregar(); }, []);

  const visiveis = filtro ? items.filter((s) => s.status === filtro) : items;
  const contagem = (status) => items.filter((s) => s.status === status).length;

  const marcarLida = async (s) => {
    setOcupado(s.sugestao_id);
    try {
      await api.post(`/admin/sugestoes/${s.sugestao_id}/lida`);
      setItems((prev) => prev.map((x) => (x.sugestao_id === s.sugestao_id ? { ...x, status: "lida" } : x)));
    } catch (e) {
      toast.error(errMsg(e, "Falha ao marcar como lida."));
    } finally {
      setOcupado(null);
    }
  };

  const responder = async (s) => {
    const texto = (rascunhos[s.sugestao_id] || "").trim();
    if (!texto) return;
    setOcupado(s.sugestao_id);
    try {
      await api.post(`/admin/sugestoes/${s.sugestao_id}/responder`, { resposta: texto });
      setItems((prev) =>
        prev.map((x) => (x.sugestao_id === s.sugestao_id ? { ...x, status: "respondida", resposta: texto } : x)),
      );
      setRascunhos((r) => ({ ...r, [s.sugestao_id]: "" }));
      toast.success("Resposta enviada — o aluno vê na tela dele.");
    } catch (e) {
      toast.error(errMsg(e, "Falha ao responder."));
    } finally {
      setOcupado(null);
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="flex items-center gap-3 mb-3">
          <MessageSquareWarning className="w-4 h-4 text-sapiens-accent" />
          <div className="secao-olho">
            Admin · Reclamações e sugestões
          </div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-sugestoes-title">
          O que os alunos estão dizendo
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Mensagens sobre o produto — não sobre uma questão específica (essas ficam em Sugestões de
          correção). Responder devolve o texto direto para a tela do aluno.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {FILTROS.map((f) => (
            <button
              key={f.id || "todas"}
              onClick={() => setFiltro(f.id)}
              className={`pill rounded-full border px-4 py-2 text-xs font-medium transition ${
                filtro === f.id
                  ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy"
                  : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
              }`}
              data-testid={`admin-sugestoes-filtro-${f.id || "todas"}`}
            >
              {f.rotulo}
              {f.id && <span className="ml-1.5 text-zinc-400">{contagem(f.id)}</span>}
            </button>
          ))}
        </div>

        {!carregado ? (
          <div className="mt-8 flex items-center gap-2 text-sm text-white/60">
            <Loader2 className="w-4 h-4 animate-spin" /> Carregando...
          </div>
        ) : visiveis.length === 0 ? (
          <p className="mt-8 text-sm text-white/50" data-testid="admin-sugestoes-vazio">Nada nesta aba.</p>
        ) : (
          <div className="mt-6 space-y-3">
            {visiveis.map((s) => {
              const meta = TIPO_META[s.tipo] || TIPO_META.sugestao;
              const Icone = meta.icone;
              return (
                <div key={s.sugestao_id} className="card-sapiens rounded-2xl p-5" data-testid={`admin-sugestao-${s.sugestao_id}`}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <Icone className="w-3.5 h-3.5" />
                        <span className="font-medium text-zinc-700">{meta.rotulo}</span>
                        <span className="text-zinc-400">· {formatarData(s.created_at)}</span>
                      </div>
                      <div className="mt-1 text-sm text-zinc-600">
                        {s.student_nome} <span className="text-zinc-400">· {s.student_email}</span>
                      </div>
                    </div>
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${STATUS_CLS[s.status]}`}>
                      {STATUS_LABEL[s.status] || s.status}
                    </span>
                  </div>

                  <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-zinc-700">{s.mensagem}</p>
                  {s.contexto && (
                    <div className="mt-2 font-mono-alt text-[11px] text-zinc-400">veio de: {s.contexto}</div>
                  )}

                  {s.resposta ? (
                    <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50 p-3.5">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-700">Respondida</div>
                      <p className="mt-1 whitespace-pre-line text-sm text-zinc-700">{s.resposta}</p>
                    </div>
                  ) : (
                    <div className="mt-4">
                      <textarea
                        value={rascunhos[s.sugestao_id] || ""}
                        onChange={(e) => setRascunhos((r) => ({ ...r, [s.sugestao_id]: e.target.value.slice(0, 2000) }))}
                        rows={3}
                        placeholder="Responder ao aluno..."
                        className="w-full resize-none rounded-xl px-3.5 py-2.5 text-sm outline-none"
                        data-testid={`admin-sugestao-resposta-${s.sugestao_id}`}
                      />
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          onClick={() => responder(s)}
                          disabled={ocupado === s.sugestao_id || !(rascunhos[s.sugestao_id] || "").trim()}
                          className="pill btn-sapiens inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium disabled:opacity-40"
                          data-testid={`admin-sugestao-responder-${s.sugestao_id}`}
                        >
                          <Send className="w-3.5 h-3.5" /> Responder
                        </button>
                        {s.status === "nova" && (
                          <button
                            onClick={() => marcarLida(s)}
                            disabled={ocupado === s.sugestao_id}
                            className="pill inline-flex items-center gap-2 rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-zinc-500 hover:border-zinc-300 disabled:opacity-40"
                            data-testid={`admin-sugestao-lida-${s.sugestao_id}`}
                          >
                            <Check className="w-3.5 h-3.5" /> Marcar como lida
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
