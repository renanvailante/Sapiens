import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import Nav from "../components/Nav";
import { api, errMsg } from "../lib/api";
import { ShieldCheck, Loader2, Check, Trash2, Flag } from "lucide-react";

/**
 * Fila de moderação do mural.
 *
 * Existe desde o lançamento, não depois: o público é majoritariamente menor de
 * idade, e uma comunidade sem fila de moderação é uma decisão de não moderar.
 *
 * Três reportes de pessoas DIFERENTES já tiram a publicação do ar
 * automaticamente (`comunidade.REPORTES_PARA_OCULTAR`) — é uma suspensão
 * preventiva, não uma condenação: o conteúdo continua aqui inteiro, o autor
 * continua vendo o dele, e é esta tela que decide.
 */

function Cartao({ item, tipo, aoModerar }) {
  const [agindo, setAgindo] = useState(null);
  const reportes = (item.reportada_por || []).length;

  const agir = async (acao) => {
    setAgindo(acao);
    try {
      await api.post(`/comunidade/admin/${tipo}/${item.duvida_id || item.resposta_id}/${acao}`);
      toast.success(acao === "restaurar" ? "Devolvido ao mural." : "Removido do mural.");
      aoModerar();
    } catch (err) {
      toast.error(errMsg(err, "Não foi possível moderar."));
    } finally {
      setAgindo(null);
    }
  };

  return (
    <div className="card-sapiens rounded-2xl p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono-alt rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em] text-white/50">
          {tipo}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-rose-400/25 bg-rose-500/10 px-2 py-0.5 text-[10px] text-rose-200">
          <Flag className="h-3 w-3" /> {reportes} {reportes === 1 ? "reporte" : "reportes"}
        </span>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] ${
            item.status === "em_revisao"
              ? "border-amber-400/25 bg-amber-500/10 text-amber-200"
              : item.status === "removida"
              ? "border-rose-400/25 bg-rose-500/10 text-rose-200"
              : "border-emerald-400/25 bg-emerald-500/10 text-emerald-200"
          }`}
        >
          {item.status}
        </span>
      </div>

      {item.titulo && (
        <h3 className="mt-2.5 font-display text-base font-bold tracking-tight text-zinc-950">{item.titulo}</h3>
      )}
      <p className="mt-1.5 whitespace-pre-wrap text-sm text-zinc-500">{item.corpo}</p>
      <p className="mt-2 text-xs text-white/40">
        {item.autor_nome} · {new Date(item.created_at).toLocaleString("pt-BR")}
      </p>

      <div className="mt-4 flex gap-2">
        <button
          onClick={() => agir("restaurar")}
          disabled={agindo !== null}
          className="pill btn-vidro inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs disabled:opacity-50"
        >
          {agindo === "restaurar" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
          Manter no mural
        </button>
        <button
          onClick={() => agir("remover")}
          disabled={agindo !== null}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-rose-400/30 bg-rose-500/15 px-3.5 py-1.5 text-xs text-rose-200 hover:bg-rose-500/25 disabled:opacity-50"
        >
          {agindo === "remover" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
          Remover
        </button>
      </div>
    </div>
  );
}

export default function AdminComunidade() {
  const [fila, setFila] = useState({ duvidas: [], respostas: [] });
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(() => {
    setCarregando(true);
    api
      .get("/comunidade/admin/fila")
      .then(({ data }) => setFila(data))
      .catch(() => setFila({ duvidas: [], respostas: [] }))
      .finally(() => setCarregando(false));
  }, []);

  useEffect(carregar, [carregar]);

  const total = fila.duvidas.length + fila.respostas.length;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-6 py-12 md:px-10">
        <div className="font-mono-alt mb-3 flex items-center gap-2 text-xs uppercase tracking-[0.35em] text-white/50">
          <ShieldCheck className="h-3.5 w-3.5" /> Admin · Comunidade
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-comunidade-title">
          Fila de moderação
        </h1>
        <p className="mt-3 text-white/60">
          {total === 0
            ? "Nada reportado no momento."
            : `${total} ${total === 1 ? "publicação reportada" : "publicações reportadas"}.`}
        </p>

        {carregando ? (
          <div className="mt-8 flex items-center gap-2 text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
          </div>
        ) : (
          <div className="mt-8 space-y-3">
            {fila.duvidas.map((d) => (
              <Cartao key={d.duvida_id} item={d} tipo="duvida" aoModerar={carregar} />
            ))}
            {fila.respostas.map((r) => (
              <Cartao key={r.resposta_id} item={r} tipo="resposta" aoModerar={carregar} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
