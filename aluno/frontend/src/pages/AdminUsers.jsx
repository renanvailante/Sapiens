import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";
import {
  ShieldCheck, ShieldOff, Zap, ListChecks, Ticket, Search, Receipt,
  X, Loader2, ArrowRight, AlertTriangle,
} from "lucide-react";

// Tela de contas do admin. Três coisas ao mesmo tempo, de propósito — é a
// única lista que tem TODO MUNDO: permissão (promover/revogar), estado do
// aluno (Sparks e questões, vindos do Firestore no mesmo GET) e a porta de
// entrada para a ficha individual.

function formatarData(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function formatarDia(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("pt-BR");
  } catch {
    return iso;
  }
}

function reais(centavos) {
  if (centavos == null) return "—";
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// `null` e `0` são respostas DIFERENTES: `null` é "o agregado deste aluno
// ainda não existe, não sei", `0` é "sei, e é zero". Mostrar 0 nos dois casos
// diria que um aluno com 300 questões nunca respondeu nada.
function numero(v) {
  return v == null ? "—" : v.toLocaleString("pt-BR");
}

function Metrica({ icone: Icone, valor, titulo, tom = "zinc" }) {
  const tons = {
    zinc: "text-zinc-500",
    amber: "text-amber-600",
    sky: "text-sky-600",
  };
  return (
    <div className="flex items-center gap-1.5 whitespace-nowrap" title={titulo}>
      <Icone className={`w-3.5 h-3.5 shrink-0 ${tons[tom]}`} />
      <span className="font-mono-alt text-sm font-semibold text-zinc-900">{valor}</span>
    </div>
  );
}

function LinhaFicha({ rotulo, valor }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 border-b border-zinc-100 last:border-0">
      <span className="text-xs text-zinc-500 shrink-0">{rotulo}</span>
      <span className="text-sm text-zinc-900 text-right break-words min-w-0">{valor ?? "—"}</span>
    </div>
  );
}

function BlocoFicha({ titulo, children }) {
  return (
    <div>
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500 mb-1">{titulo}</div>
      <div>{children}</div>
    </div>
  );
}

function FichaDoAluno({ userId, onFechar }) {
  const [ficha, setFicha] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let vivo = true;
    setFicha(null);
    setErro(null);
    api
      .get(`/admin/users/${encodeURIComponent(userId)}/detalhe`)
      .then(({ data }) => vivo && setFicha(data))
      .catch((e) => vivo && setErro(errMsg(e, "Não foi possível carregar a ficha do aluno.")));
    return () => { vivo = false; };
  }, [userId]);

  // Esc fecha: a ficha cobre a tela inteira e o mouse pode estar longe do X.
  useEffect(() => {
    const aoTeclar = (e) => e.key === "Escape" && onFechar();
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  const conta = ficha?.conta || {};
  const perfil = ficha?.perfil || {};
  const atividade = ficha?.atividade || {};
  const financeiro = ficha?.financeiro || {};

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8 bg-black/70 backdrop-blur-sm"
      onClick={onFechar}
      data-testid="admin-user-ficha"
    >
      {/* Altura limitada + corpo com rolagem PRÓPRIA. Centralizar um cartão
          mais alto que a tela e deixar a rolagem para o overlay torna o fim da
          ficha inalcançável — as últimas transações ficavam fora de alcance. */}
      <div
        className="card-sapiens rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-4 p-6 border-b border-zinc-100 shrink-0">
          <div className="w-12 h-12 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-600 font-display font-bold text-lg shrink-0">
            {conta.name?.[0]?.toUpperCase() || "?"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display text-xl font-extrabold tracking-tight text-zinc-950 truncate">
              {conta.name || userId}
            </div>
            <div className="text-sm text-zinc-500 truncate">{conta.email}</div>
            <div className="font-mono-alt text-[11px] text-zinc-400 truncate">{userId}</div>
          </div>
          <button
            onClick={onFechar}
            className="pill p-2 rounded-full hover:bg-white/10 text-zinc-500 shrink-0"
            aria-label="Fechar"
            data-testid="admin-user-ficha-fechar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {!ficha && !erro && (
          <div className="p-10 flex items-center justify-center gap-2 text-zinc-500 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" /> Carregando a ficha…
          </div>
        )}
        {erro && <div className="p-8 text-sm text-rose-600">{erro}</div>}

        {ficha && (
          // `min-h-0` não é enfeite: um filho de flex column tem
          // `min-height: auto` por padrão e se recusa a encolher abaixo do
          // próprio conteúdo, então o `overflow-y-auto` nunca entrava em ação
          // — o cartão só CORTAVA o fim da ficha, sem barra de rolagem.
          <div className="p-6 space-y-6 flex-1 min-h-0 overflow-y-auto">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="rounded-xl bg-amber-50 border border-amber-100 p-3">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-amber-700">Sparks</div>
                <div className="mt-0.5 font-display text-2xl font-extrabold tracking-tighter text-amber-900">
                  {numero(perfil.sparks_balance)}
                </div>
              </div>
              <div className="rounded-xl bg-sky-50 border border-sky-100 p-3">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-sky-700">Questões</div>
                <div className="mt-0.5 font-display text-2xl font-extrabold tracking-tighter text-sky-900">
                  {numero(perfil.questoes_respondidas)}
                </div>
              </div>
              <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-3">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-500">Dias ativos</div>
                <div className="mt-0.5 font-display text-2xl font-extrabold tracking-tighter text-zinc-900">
                  {numero(perfil.dias_ativos)}
                </div>
              </div>
              <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-3">
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-emerald-700">Gasto</div>
                <div className="mt-0.5 font-display text-2xl font-extrabold tracking-tighter text-emerald-900">
                  {reais(financeiro.gasto_centavos)}
                </div>
              </div>
            </div>

            {perfil.indisponivel && (
              <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                O estado do aluno (Sparks, questões, dias ativos) não pôde ser lido agora. Os dados
                da conta abaixo continuam corretos.
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <BlocoFicha titulo="Conta">
                <LinhaFicha rotulo="Entra por" valor={conta.provider} />
                <LinhaFicha rotulo="E-mail verificado" valor={conta.email_verificado ? "Sim" : "Não"} />
                <LinhaFicha rotulo="Acesso" valor={conta.is_admin ? "Administrador" : "Aluno"} />
                <LinhaFicha rotulo="Conta criada em" valor={formatarData(conta.created_at)} />
                <LinhaFicha
                  rotulo="Cupom no cadastro"
                  valor={
                    conta.promo_code ? (
                      <span className="font-mono-alt font-semibold">
                        {conta.promo_code}
                        {conta.promo_sparks != null && (
                          <span className="text-zinc-500 font-normal"> · {conta.promo_sparks} Sparks</span>
                        )}
                      </span>
                    ) : (
                      <span className="text-zinc-400">sem cupom</span>
                    )
                  }
                />
              </BlocoFicha>

              <BlocoFicha titulo="Estudo">
                <LinhaFicha rotulo="Questões respondidas" valor={numero(perfil.questoes_respondidas)} />
                <LinhaFicha rotulo="Questões distintas" valor={numero(perfil.itens_distintos)} />
                <LinhaFicha rotulo="Última atividade" valor={formatarData(perfil.ultima_atividade)} />
                <LinhaFicha
                  rotulo="Treino de habilidades"
                  valor={
                    perfil.treino
                      ? `${perfil.treino.respondidas} respondidas · ${perfil.treino.acertos} acertos`
                      : "—"
                  }
                />
                <LinhaFicha
                  rotulo="Revisão espaçada"
                  valor={
                    perfil.revisao
                      ? `${perfil.revisao.processos_acompanhados} processo(s)${perfil.revisao.intervencao_ativa ? " · intervenção ativa" : ""}`
                      : "—"
                  }
                />
              </BlocoFicha>

              <BlocoFicha titulo="Atividade no produto">
                <LinhaFicha rotulo="Análises de prova" valor={numero(atividade.analises)} />
                <LinhaFicha rotulo="Redações enviadas" valor={numero(atividade.redacoes)} />
                <LinhaFicha rotulo="Sessões com a Mentis" valor={numero(atividade.sessoes_mentis)} />
                <LinhaFicha rotulo="Reportes de questão" valor={numero(atividade.reportes_de_questao)} />
                <LinhaFicha rotulo="Reclamações e sugestões" valor={numero(atividade.sugestoes)} />
                <LinhaFicha rotulo="Pedidos de aula particular" valor={numero(atividade.aulas_particulares)} />
              </BlocoFicha>

              <BlocoFicha titulo="Financeiro">
                <LinhaFicha rotulo="Transações" valor={numero(financeiro.transacoes)} />
                <LinhaFicha rotulo="Pagas" valor={numero(financeiro.transacoes_pagas)} />
                <LinhaFicha rotulo="Sparks comprados" valor={numero(financeiro.sparks_comprados)} />
                <LinhaFicha
                  rotulo="Recarga automática"
                  valor={
                    financeiro.recarga_automatica
                      ? `${financeiro.recarga_automatica.active ? "Ativa" : "Inativa"} · a cada ${financeiro.recarga_automatica.frequency_days} dias`
                      : "não configurada"
                  }
                />
              </BlocoFicha>
            </div>

            {ficha.transacoes?.length > 0 && (
              <div>
                <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500 mb-2">
                  Últimas transações
                </div>
                <div className="space-y-1.5">
                  {ficha.transacoes.slice(0, 8).map((t, i) => (
                    <div
                      key={t.purchase_id || t.mp_payment_id || i}
                      className="flex items-center gap-3 text-sm border border-zinc-100 rounded-xl px-3 py-2"
                    >
                      <span className="text-zinc-500 font-mono-alt text-xs shrink-0">
                        {formatarDia(t.created_at)}
                      </span>
                      <span className="flex-1 min-w-0 truncate text-zinc-900">
                        {t.pacote_label || t.package_id} · {t.payment_method_id || "—"}
                      </span>
                      <span className="font-mono-alt text-xs text-zinc-600 shrink-0">{reais(t.price_cents)}</span>
                      <span
                        className={`text-[10px] font-mono-alt uppercase tracking-[0.2em] px-2 py-0.5 rounded-full shrink-0 ${
                          t.credited
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-amber-50 text-amber-700"
                        }`}
                      >
                        {t.credited ? "creditado" : t.status || "pendente"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-2 pt-2">
              <Link
                to="/admin/history"
                className="pill inline-flex items-center gap-1.5 text-xs font-medium px-3.5 py-2 rounded-full border border-zinc-200 hover:bg-white/10 text-zinc-700"
              >
                Histórico bruto de eventos <ArrowRight className="w-3 h-3" />
              </Link>
              <Link
                to="/admin/transacoes"
                className="pill inline-flex items-center gap-1.5 text-xs font-medium px-3.5 py-2 rounded-full border border-zinc-200 hover:bg-white/10 text-zinc-700"
              >
                Todas as transações <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminUsers() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [busca, setBusca] = useState("");
  const [aberto, setAberto] = useState(null);

  const load = () => api.get("/admin/users").then(({ data }) => setUsers(data));
  useEffect(() => { load(); }, []);

  const indisponivel = users.some((u) => u.sparks_indisponivel);

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return users;
    return users.filter((u) =>
      [u.name, u.email, u.user_id, u.promo_code].some((c) => (c || "").toLowerCase().includes(termo)),
    );
  }, [users, busca]);

  const totalSparks = users.reduce((s, u) => s + (u.sparks_balance || 0), 0);
  const totalQuestoes = users.reduce((s, u) => s + (u.questoes_respondidas || 0), 0);
  const comCupom = users.filter((u) => u.promo_code).length;

  const toggle = async (u) => {
    try {
      await api.patch(`/admin/users/${u.user_id}`, { is_admin: !u.is_admin });
      toast.success(!u.is_admin ? "Usuário promovido a admin." : "Acesso admin removido.");
      load();
    } catch (e) {
      toast.error(errMsg(e, "Falha ao atualizar."));
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Admin · Alunos</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-white" data-testid="admin-users-title">
          Alunos e permissões
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Cada aluno com o saldo de Sparks, quantas questões já respondeu e o cupom que usou no
          cadastro. Clique num aluno para abrir a ficha completa.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-2">
          <Link
            to="/admin/transacoes"
            className="btn-sapiens inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold"
            data-testid="admin-users-ver-transacoes"
          >
            <Receipt className="w-4 h-4" /> Ver transações
          </Link>
          <Link
            to="/admin/promo-codes"
            className="pill inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium border border-white/15 text-white/70 hover:text-white"
            data-testid="admin-users-ver-cupons"
          >
            <Ticket className="w-4 h-4" /> Uso dos cupons
          </Link>
        </div>

        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Contas</div>
            <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">{users.length}</div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Sparks em circulação</div>
            <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">
              {indisponivel ? "—" : totalSparks.toLocaleString("pt-BR")}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Questões respondidas</div>
            <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">
              {indisponivel ? "—" : totalQuestoes.toLocaleString("pt-BR")}
            </div>
          </div>
          <div className="card-sapiens rounded-2xl p-4">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Vieram com cupom</div>
            <div className="mt-1 font-display text-2xl font-extrabold tracking-tighter text-zinc-950">{comCupom}</div>
          </div>
        </div>

        {indisponivel && (
          <div className="mt-4 flex items-start gap-2 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-200">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            Saldo de Sparks e contagem de questões indisponíveis agora — as permissões abaixo
            continuam funcionando normalmente.
          </div>
        )}

        <div className="mt-6 relative">
          <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
          <input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome, e-mail, id ou cupom…"
            className="w-full card-sapiens rounded-2xl pl-11 pr-4 py-3 text-sm outline-none focus:border-sapiens-accent"
            data-testid="admin-users-busca"
          />
        </div>

        <div className="mt-4 space-y-2">
          {visiveis.length === 0 && (
            <div className="card-sapiens rounded-2xl p-8 text-center text-zinc-500 text-sm">
              Nenhum aluno encontrado.
            </div>
          )}
          {visiveis.map(u => (
            // O cartão inteiro abre a ficha; o botão de permissão para o
            // clique com `stopPropagation` para não abrir a ficha junto.
            <div
              key={u.user_id}
              role="button"
              tabIndex={0}
              onClick={() => setAberto(u.user_id)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), setAberto(u.user_id))}
              className="lift card-sapiens hover:border-sapiens-accent cursor-pointer rounded-2xl p-4 flex flex-wrap items-center gap-x-4 gap-y-3"
              data-testid={`admin-user-row-${u.user_id}`}
            >
              <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-600 font-display font-bold shrink-0">
                {u.name?.[0]?.toUpperCase() || "?"}
              </div>
              <div className="flex-1 min-w-[10rem]">
                <div className="font-display font-semibold text-zinc-900 truncate">{u.name}</div>
                <div className="text-sm text-zinc-500 truncate">{u.email}</div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                <Metrica
                  icone={Zap}
                  tom="amber"
                  valor={numero(u.sparks_balance)}
                  titulo="Saldo de Sparks"
                />
                <Metrica
                  icone={ListChecks}
                  tom="sky"
                  valor={numero(u.questoes_respondidas)}
                  titulo="Questões respondidas"
                />
              </div>

              {u.promo_code ? (
                <span
                  className="inline-flex items-center gap-1.5 text-[11px] font-mono-alt bg-violet-50 text-violet-700 border border-violet-100 px-2.5 py-1 rounded-full shrink-0"
                  title={`Cupom usado no cadastro${u.promo_sparks != null ? ` — ${u.promo_sparks} Sparks` : ""}`}
                  data-testid={`admin-user-cupom-${u.user_id}`}
                >
                  <Ticket className="w-3 h-3" /> {u.promo_code}
                </span>
              ) : (
                <span className="text-[11px] font-mono-alt text-zinc-300 shrink-0" title="Cadastro sem cupom">
                  sem cupom
                </span>
              )}

              {u.is_admin ? (
                <span className="inline-flex items-center gap-1.5 text-xs bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-1 rounded-full shrink-0">
                  <ShieldCheck className="w-3 h-3" /> admin
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs bg-zinc-100 text-zinc-500 px-2.5 py-1 rounded-full shrink-0">aluno</span>
              )}

              <button
                onClick={(e) => { e.stopPropagation(); toggle(u); }}
                disabled={me?.user_id === u.user_id && u.is_admin}
                className="pill text-xs font-medium px-3 py-2 rounded-full border border-zinc-200 hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                data-testid={`admin-user-toggle-${u.user_id}`}
              >
                {u.is_admin ? <><ShieldOff className="w-3.5 h-3.5 inline mr-1" /> Revogar</> : <><ShieldCheck className="w-3.5 h-3.5 inline mr-1" /> Promover</>}
              </button>
            </div>
          ))}
        </div>
      </div>

      {aberto && <FichaDoAluno userId={aberto} onFechar={() => setAberto(null)} />}
    </div>
  );
}
