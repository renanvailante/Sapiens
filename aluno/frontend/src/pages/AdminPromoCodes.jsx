import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Ticket, Plus, Trash2, Users, ChevronDown, ChevronRight } from "lucide-react";

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export default function AdminPromoCodes() {
  const [codes, setCodes] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [code, setCode] = useState("");
  const [amount, setAmount] = useState("");
  const [creating, setCreating] = useState(false);
  const [aberto, setAberto] = useState(null);
  const [totalComCupom, setTotalComCupom] = useState(null);

  // `/uso` devolve o catálogo JÁ enriquecido com quem usou cada código — é
  // um superconjunto de `/admin/promo-codes`, então uma chamada só serve a
  // tela inteira (criar/ativar/excluir continuam usando as rotas de sempre).
  const load = () =>
    api.get("/admin/promo-codes/uso").then(({ data }) => {
      setCodes(data.items || []);
      setTotalComCupom(data.total_alunos_com_cupom ?? null);
      setLoaded(true);
    });
  useEffect(() => { load(); }, []);

  const criar = async (e) => {
    e.preventDefault();
    const valor = parseInt(amount, 10);
    if (!code.trim() || !valor || valor < 1) {
      toast.error("Informe um código e uma quantidade de Sparks válida.");
      return;
    }
    setCreating(true);
    try {
      const { data } = await api.post("/admin/promo-codes", { code: code.trim(), sparks_amount: valor });
      setCodes((prev) => [{ ...data, alunos: [], alunos_count: 0, usos_sem_vinculo: 0 }, ...prev]);
      setCode("");
      setAmount("");
      toast.success(`Código ${data.code} criado.`);
    } catch (e2) {
      toast.error(errMsg(e2, "Falha ao criar código."));
    } finally {
      setCreating(false);
    }
  };

  const alternarAtivo = async (c) => {
    try {
      const { data } = await api.patch(`/admin/promo-codes/${c.code}`, { active: !c.active });
      // Preserva os campos de uso: o PATCH devolve só o documento do catálogo.
      setCodes((prev) => prev.map((x) => (x.code === c.code ? { ...x, ...data } : x)));
    } catch (e) {
      toast.error(errMsg(e, "Falha ao atualizar código."));
    }
  };

  const excluir = async (c) => {
    if (!window.confirm(`Excluir o código ${c.code}? Isso não afeta quem já usou.`)) return;
    try {
      await api.delete(`/admin/promo-codes/${c.code}`);
      setCodes((prev) => prev.filter((x) => x.code !== c.code));
      toast.success("Código excluído.");
    } catch (e) {
      toast.error(errMsg(e, "Falha ao excluir código."));
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="flex items-center gap-3 mb-3">
          <Ticket className="w-4 h-4 text-sapiens-accent" />
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">Admin · Códigos de promoção</div>
        </div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-promo-title">
          Códigos de promoção
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">
          Quem se cadastra sem código ganha o bônus padrão de Sparks. Com um código ativo, ganha a quantidade programada aqui em vez do padrão.
        </p>
        {totalComCupom != null && (
          <p className="mt-2 text-white/40 text-sm max-w-lg">
            {totalComCupom} conta(s) com cupom registrado. O vínculo aluno↔cupom passou a ser
            gravado em 15/09/2026 — cadastros anteriores contam em “usos” sem aparecer na lista de
            alunos.
          </p>
        )}

        <form onSubmit={criar} className="mt-8 card-sapiens rounded-2xl p-6 flex flex-col md:flex-row gap-3 md:items-end">
          <div className="flex-1">
            <label className="block text-xs font-medium text-zinc-500 mb-1">Código</label>
            <input
              value={code} onChange={(e) => setCode(e.target.value)}
              placeholder="EX: BEMVINDO2026"
              className="w-full border border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:border-sapiens-accent outline-none uppercase"
              data-testid="admin-promo-input-code"
            />
          </div>
          <div className="w-full md:w-40">
            <label className="block text-xs font-medium text-zinc-500 mb-1">Sparks</label>
            <input
              type="number" min={1} value={amount} onChange={(e) => setAmount(e.target.value)}
              placeholder="200"
              className="w-full border border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:border-sapiens-accent outline-none"
              data-testid="admin-promo-input-amount"
            />
          </div>
          <button
            type="submit" disabled={creating}
            className="btn-sapiens inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
            data-testid="admin-promo-create"
          >
            <Plus className="w-4 h-4" /> {creating ? "Criando…" : "Criar código"}
          </button>
        </form>

        <div className="mt-6 space-y-3">
          {loaded && codes.length === 0 && (
            <div className="card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
              Nenhum código de promoção criado ainda.
            </div>
          )}
          {codes.map((c) => (
            <div key={c.code} className="card-sapiens rounded-2xl p-5 flex flex-col md:flex-row md:items-center gap-4" data-testid={`admin-promo-row-${c.code}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono-alt font-bold text-zinc-950 tracking-wide">{c.code}</span>
                  <span className={`inline-flex items-center text-[11px] font-medium border px-2 py-0.5 rounded-full ${c.active ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-zinc-100 text-zinc-500 border-zinc-200"}`}>
                    {c.active ? "Ativo" : "Desativado"}
                  </span>
                </div>
                <div className="mt-1 text-sm text-zinc-500">
                  {c.sparks_amount} Sparks · usado {c.usos || 0}x
                  {c.created_at && <> · criado em {formatDate(c.created_at)}</>}
                  {c.excluido && <> · <span className="text-rose-500">excluído do catálogo</span></>}
                </div>
                <button
                  onClick={() => setAberto(aberto === c.code ? null : c.code)}
                  // `flex-wrap`: com o aviso de usos antigos a linha passa da
                  // largura da coluna, e um `inline-flex` sem quebra mantinha
                  // a altura de uma linha só — o rótulo sumia atrás do card.
                  className="mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-left text-xs font-medium text-zinc-600 hover:underline"
                  data-testid={`admin-promo-alunos-${c.code}`}
                >
                  {aberto === c.code ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  <Users className="w-3.5 h-3.5" />
                  {c.alunos_count} aluno(s) com este cupom
                  {c.usos_sem_vinculo > 0 && (
                    <span className="text-zinc-400">
                      (+{c.usos_sem_vinculo} uso(s) anteriores ao registro)
                    </span>
                  )}
                </button>
                {aberto === c.code && (
                  <div className="mt-3 space-y-1.5">
                    {c.alunos.length === 0 && (
                      <div className="text-xs text-zinc-400">Nenhuma conta vinculada a este cupom.</div>
                    )}
                    {c.alunos.map((a) => (
                      <div key={a.user_id} className="flex items-center gap-3 border border-zinc-100 rounded-xl px-3 py-2">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-zinc-900 truncate">{a.name}</div>
                          <div className="text-xs text-zinc-500 truncate">{a.email}</div>
                        </div>
                        <div className="text-xs font-mono-alt text-zinc-400 shrink-0">{formatDate(a.created_at)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => alternarAtivo(c)}
                  className="pill text-xs font-medium px-3.5 py-2 rounded-full border border-white/15 text-white/70 hover:text-white"
                  data-testid={`admin-promo-toggle-${c.code}`}
                >
                  {c.active ? "Desativar" : "Ativar"}
                </button>
                <button
                  onClick={() => excluir(c)}
                  className="pill text-xs font-medium px-3 py-2 rounded-full border border-red-900/20 text-red-400 hover:bg-red-950/20"
                  data-testid={`admin-promo-delete-${c.code}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
