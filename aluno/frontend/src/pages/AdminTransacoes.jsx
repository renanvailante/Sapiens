import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Receipt, Search, Zap, ArrowRight, CreditCard, QrCode, RefreshCw } from "lucide-react";

// Toda cobrança de Sparks já registrada — aprovada ou não. A fonte é a
// auditoria de cobrança (`sparks_payments`), e não o crédito no Firestore: uma
// tela que só mostrasse compras creditadas esconderia exatamente o caso que se
// vem investigar aqui (o Pix abandonado, o cartão recusado, o pagamento preso).

const FILTROS = [
  { id: "", rotulo: "Todas" },
  { id: "creditadas", rotulo: "Creditadas" },
  { id: "pendentes", rotulo: "Em aberto" },
  { id: "recusadas", rotulo: "Recusadas" },
];

const STATUS_CLS = {
  approved: "bg-emerald-50 text-emerald-700 border-emerald-100",
  pending: "bg-amber-50 text-amber-700 border-amber-100",
  in_process: "bg-amber-50 text-amber-700 border-amber-100",
  authorized: "bg-sky-50 text-sky-700 border-sky-100",
  rejected: "bg-rose-50 text-rose-700 border-rose-100",
  cancelled: "bg-zinc-100 text-zinc-500 border-zinc-200",
  refunded: "bg-zinc-100 text-zinc-500 border-zinc-200",
  charged_back: "bg-rose-50 text-rose-700 border-rose-100",
};

// O Mercado Pago devolve a bandeira do cartão no mesmo campo em que devolve
// "pix" — por isso um só rótulo para as duas coisas.
function metodo(id) {
  if (!id) return { rotulo: "—", icone: CreditCard };
  if (id === "pix") return { rotulo: "Pix", icone: QrCode };
  return { rotulo: id.replace(/_/g, " "), icone: CreditCard };
}

function reais(centavos) {
  if (centavos == null) return "—";
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function dataLegivel(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
  } catch {
    return iso;
  }
}

function classeDeStatus(t) {
  return STATUS_CLS[t.status] || "bg-zinc-100 text-zinc-500 border-zinc-200";
}

export default function AdminTransacoes() {
  const [items, setItems] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [carregado, setCarregado] = useState(false);
  const [filtro, setFiltro] = useState("");
  const [busca, setBusca] = useState("");
  const [recarregando, setRecarregando] = useState(false);

  const carregar = () =>
    api
      .get("/admin/transacoes")
      .then(({ data }) => { setItems(data.items || []); setResumo(data.resumo || null); })
      .catch((e) => console.error(errMsg(e, "Falha ao carregar as transações.")))
      .finally(() => { setCarregado(true); setRecarregando(false); });

  useEffect(() => { carregar(); }, []);

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    return items.filter((t) => {
      if (filtro === "creditadas" && !t.credited) return false;
      if (filtro === "pendentes" && (t.credited || ["rejected", "cancelled", "refunded", "charged_back"].includes(t.status))) return false;
      if (filtro === "recusadas" && !["rejected", "cancelled", "refunded", "charged_back"].includes(t.status)) return false;
      if (!termo) return true;
      return [t.aluno_nome, t.aluno_email, t.user_id, t.package_id, t.mp_payment_id, t.payment_method_id]
        .some((c) => (c || "").toLowerCase().includes(termo));
    });
  }, [items, filtro, busca]);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="flex items-center gap-3 mb-3">
          <Receipt className="w-4 h-4 text-sapiens-accent" />
          <div className="secao-olho">Admin · Transações</div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-transacoes-title">
          Transações de Sparks
        </h1>
        <p className="mt-3 text-white/60 max-w-2xl">
          Quem comprou, quanto tinha de Sparks antes, qual pacote levou, quando e por qual forma de
          pagamento. Cobranças recusadas e em aberto aparecem junto — é nelas que mora o problema
          quando um aluno diz que pagou e não recebeu.
        </p>

        {resumo && (
          <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Transações</div>
              <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">{resumo.total}</div>
            </div>
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Creditadas</div>
              <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">{resumo.creditadas}</div>
            </div>
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Receita</div>
              <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">{reais(resumo.receita_centavos)}</div>
            </div>
            <div className="card-sapiens rounded-2xl p-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Sparks vendidos</div>
              <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">
                {(resumo.sparks_vendidos || 0).toLocaleString("pt-BR")}
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-2">
          {FILTROS.map((f) => (
            <button
              key={f.id || "todas"}
              onClick={() => setFiltro(f.id)}
              className={`pill rounded-full border px-4 py-2 text-xs font-medium transition ${
                filtro === f.id
                  ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy"
                  : "border-white/15 text-white/60 hover:text-white"
              }`}
              data-testid={`admin-transacoes-filtro-${f.id || "todas"}`}
            >
              {f.rotulo}
            </button>
          ))}
          <button
            onClick={() => { setRecarregando(true); carregar(); }}
            className="pill ml-auto inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2 text-xs font-medium text-white/60 hover:text-white"
            data-testid="admin-transacoes-recarregar"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${recarregando ? "animate-spin" : ""}`} /> Atualizar
          </button>
        </div>

        <div className="mt-4 relative">
          <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
          <input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por aluno, e-mail, pacote ou id do pagamento…"
            className="w-full card-sapiens rounded-2xl pl-11 pr-4 py-3 text-sm outline-none focus:border-sapiens-accent"
            data-testid="admin-transacoes-busca"
          />
        </div>

        <div className="mt-4 space-y-2">
          {carregado && visiveis.length === 0 && (
            <div className="card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
              Nenhuma transação nesse recorte.
            </div>
          )}

          {visiveis.map((t, i) => {
            const m = metodo(t.payment_method_id);
            return (
              <div
                key={t.purchase_id || t.mp_payment_id || i}
                className="card-sapiens rounded-2xl p-4"
                data-testid={`admin-transacao-${t.purchase_id || t.mp_payment_id || i}`}
              >
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  <div className="flex-1 min-w-[12rem]">
                    <div className="font-display font-semibold text-zinc-900 truncate">
                      {t.aluno_nome || <span className="text-zinc-400">aluno não identificado</span>}
                    </div>
                    <div className="text-sm text-zinc-500 truncate">{t.aluno_email || t.user_id || "—"}</div>
                  </div>

                  <div className="min-w-[8rem]">
                    <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">Pacote</div>
                    <div className="text-sm font-semibold text-zinc-900">{t.pacote_label}</div>
                  </div>

                  <div className="min-w-[6rem]">
                    <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">Valor</div>
                    <div className="text-sm font-semibold text-zinc-900">{reais(t.price_cents)}</div>
                  </div>

                  <div className="min-w-[7rem]">
                    <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">Pagamento</div>
                    <div className="text-sm font-semibold text-zinc-900 inline-flex items-center gap-1.5 capitalize">
                      <m.icone className="w-3.5 h-3.5 text-zinc-500" /> {m.rotulo}
                    </div>
                  </div>

                  <div className="min-w-[9rem]">
                    <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">Saldo do aluno</div>
                    <div className="text-sm font-semibold text-zinc-900 inline-flex items-center gap-1.5">
                      {t.saldo_antes == null ? (
                        <span className="text-zinc-400" title="Compra anterior ao registro de saldo (15/09/2026)">—</span>
                      ) : (
                        <>
                          <Zap className="w-3.5 h-3.5 text-amber-500" />
                          {t.saldo_antes.toLocaleString("pt-BR")}
                          <ArrowRight className="w-3 h-3 text-zinc-400" />
                          {(t.saldo_apos ?? t.saldo_antes + (t.sparks_amount || 0)).toLocaleString("pt-BR")}
                        </>
                      )}
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-mono-alt uppercase tracking-[0.2em] border px-2.5 py-1 rounded-full shrink-0 ${classeDeStatus(t)}`}
                  >
                    {t.credited ? "creditado" : t.status || "—"}
                  </span>
                </div>

                <div className="mt-3 pt-3 border-t border-zinc-100 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono-alt text-[11px] text-zinc-400">
                  {/* Timestamp cru ao lado do formatado: é o que se cola numa
                      busca no painel do Mercado Pago sem ambiguidade de fuso. */}
                  <span className="text-zinc-600">{dataLegivel(t.created_at)}</span>
                  <span>{t.created_at || "—"}</span>
                  <span>+{(t.sparks_amount || 0).toLocaleString("pt-BR")} Sparks</span>
                  {t.source && <span>origem: {t.source === "auto_recharge" ? "recarga automática" : "compra avulsa"}</span>}
                  {t.mp_payment_id && <span>MP {t.mp_payment_id}</span>}
                  {t.status_detail && <span>{t.status_detail}</span>}
                  {t.unmatched && <span className="text-rose-500">sem vínculo com aluno</span>}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-8">
          <Link
            to="/admin/users"
            className="pill inline-flex items-center gap-1.5 rounded-full border border-white/15 px-4 py-2 text-xs font-medium text-white/60 hover:text-white"
          >
            Voltar para alunos e permissões
          </Link>
        </div>
      </div>
    </div>
  );
}
