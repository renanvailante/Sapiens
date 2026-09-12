import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg} from "../lib/api";
import Nav from "../components/Nav";
import { FileText, Zap, Brain, Users, ClipboardList, ArrowRight, ShieldCheck, RefreshCw, Database, GraduationCap, Flag, Ticket, Gift, MessageSquareWarning } from "lucide-react";

function StatCard({ label, value, hint }) {
  return (
    <div className="card-sapiens rounded-2xl p-5">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500">{label}</div>
      <div className="mt-2 font-display text-3xl font-extrabold tracking-tighter text-zinc-950">{value ?? "—"}</div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </div>
  );
}

const SECTIONS = [
  { to: "/admin/answer-keys", icon: FileText, title: "Gabaritos ENEM",
    desc: "Importar gabaritos oficiais colados do INEP (inglês + espanhol)." },
  { to: "/admin/feed", icon: Zap, title: "Feed",
    desc: "Criar, editar, publicar e reordenar os cards do feed vertical." },
  { to: "/admin/annotations", icon: Brain, title: "Anotações cognitivas",
    desc: "Ingerir JSONs anotados por IA especializada — versionados, verbatim." },
  { to: "/admin/curadoria", icon: ShieldCheck, title: "Curadoria",
    desc: "Oferta de itens por processo, revisão humana do elo raiz e o Sapiens Lab. É o que destrava o portão de crença." },
  { to: "/admin/aulas-particulares", icon: GraduationCap, title: "Aulas particulares",
    desc: "Ver e responder solicitações de aula particular dos alunos." },
  { to: "/admin/reportes-questoes", icon: Flag, title: "Sugestões de correção",
    desc: "Reportes da bandeira em cada questão, agrupados por questão. Aprovar credita 5 Sparks." },
  { to: "/admin/sugestoes", icon: MessageSquareWarning, title: "Reclamações e sugestões",
    desc: "O que os alunos dizem sobre o produto. Responder devolve o texto para a tela deles." },
  { to: "/admin/promo-codes", icon: Ticket, title: "Códigos de promoção",
    desc: "Criar e gerenciar códigos que dão Sparks de bônus no cadastro." },
  { to: "/admin/history", icon: ClipboardList, title: "Histórico do Aluno",
    desc: "Response Event Store — histórico append-only por aluno com filtros." },
  { to: "/admin/users", icon: Users, title: "Usuários & permissões",
    desc: "Conceder ou revogar acesso administrativo aos usuários." },
];

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  const [grantEmail, setGrantEmail] = useState("");
  const [grantAmount, setGrantAmount] = useState("");
  const [granting, setGranting] = useState(false);
  useEffect(() => {
    api.get("/admin/summary").then(({ data }) => setSummary(data)).catch(() => {});
  }, []);

  const handleGrant = async (e) => {
    e.preventDefault();
    const valor = parseInt(grantAmount, 10);
    if (!grantEmail.trim() || !valor || valor < 1) {
      toast.error("Informe um e-mail e uma quantidade de Sparks válida.");
      return;
    }
    setGranting(true);
    try {
      await api.post("/admin/sparks/grant", { email: grantEmail.trim(), amount: valor, motivo: "Crédito manual via painel admin" });
      toast.success(`${valor} Sparks creditados para ${grantEmail.trim()}.`);
      setGrantEmail("");
      setGrantAmount("");
    } catch (e2) {
      toast.error(errMsg(e2, "Falha ao creditar Sparks."));
    } finally {
      setGranting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/admin/firestore/sync");
      setLastSync(data);
      toast.success(`Firestore sincronizado: ${data.master_count} questões (master), ${data.public_count} publicadas para alunos.`);
    } catch (e) {
      toast.error(errMsg(e, "Falha ao sincronizar Firestore."));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-12">
        <div className="flex items-center gap-3 mb-3">
          <ShieldCheck className="w-4 h-4 text-sapiens-accent" />
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50">Área administrativa</div>
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="admin-title">
          Painel de administração
        </h1>
        <p className="mt-3 text-white/60 max-w-2xl">
          Aqui vive tudo que só admins podem ver: importação de gabaritos, gestão do feed, anotações cognitivas, histórico consolidado dos alunos e permissões.
        </p>

        {/* Summary */}
        <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Provas" value={summary?.exams} hint={`${summary?.answer_keys ?? 0} gabaritos`} />
          <StatCard label="Análises ativas" value={summary?.analyses_active} hint={`${summary?.analyses_trashed ?? 0} na lixeira`} />
          <StatCard label="Usuários" value={summary?.users} hint={`${summary?.admins ?? 0} admins`} />
          <StatCard label="Anotações" value={summary?.annotations} hint="ITEMs anotados" />
          <StatCard label="Feed" value={summary?.feed_items} hint={`${summary?.feed_items_published ?? 0} publicados`} />
          <StatCard label="Interações no feed" value={summary?.feed_interactions} hint="Eventos brutos" />
        </div>

        {/* Firestore sync */}
        <div className="mt-10 card-sapiens rounded-2xl p-6 flex flex-col md:flex-row md:items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white flex items-center justify-center shrink-0">
            <Database className="w-5 h-5" strokeWidth={1.7} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-lg tracking-tight text-zinc-950">Sincronizar Firestore</div>
            <div className="mt-1 text-sm text-zinc-500">
              Importa todas as questões e o schema completo do Firestore para a base interna (master, editável só no admin) e regenera a versão filtrada que o aluno acessa.
            </div>
            {lastSync && (
              <div className="mt-2 text-xs text-emerald-600">
                Última sincronização: {lastSync.master_count} no master · {lastSync.public_count} publicadas.
              </div>
            )}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            data-testid="btn-sync-firestore"
            className="shrink-0 btn-sapiens inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Sincronizando…" : "Sincronizar Firestore"}
          </button>
        </div>

        {/* Crédito manual de Sparks: ferramenta de suporte/teste — ajusta o
            saldo de um aluno por e-mail, sem passar por compra nem cupom. */}
        <form onSubmit={handleGrant} className="mt-10 card-sapiens rounded-2xl p-6 flex flex-col md:flex-row gap-4 md:items-end">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white flex items-center justify-center shrink-0">
            <Gift className="w-5 h-5" strokeWidth={1.7} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-lg tracking-tight text-zinc-950 mb-3">Creditar Sparks manualmente</div>
            <div className="flex flex-col md:flex-row gap-3">
              <input
                type="email" value={grantEmail} onChange={(e) => setGrantEmail(e.target.value)}
                placeholder="email@aluno.com"
                className="flex-1 border border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:border-sapiens-accent outline-none"
                data-testid="admin-grant-sparks-email"
              />
              <input
                type="number" min={1} value={grantAmount} onChange={(e) => setGrantAmount(e.target.value)}
                placeholder="Quantidade"
                className="w-full md:w-40 border border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:border-sapiens-accent outline-none"
                data-testid="admin-grant-sparks-amount"
              />
              <button
                type="submit" disabled={granting}
                className="btn-sapiens shrink-0 rounded-xl px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
                data-testid="admin-grant-sparks-submit"
              >
                {granting ? "Creditando…" : "Creditar"}
              </button>
            </div>
          </div>
        </form>

        {/* Painel do professor: app separado, só vitrine — visualiza dado já
            processado aqui, nunca gera diagnóstico próprio (ver a própria
            tela de login dele). Link externo, não rota interna. */}
        <a
          href="https://sapiens-professor.pages.dev"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-10 lift card-sapiens hover:border-sapiens-accent rounded-2xl p-6 flex items-start gap-4"
          data-testid="admin-link-professor"
        >
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white flex items-center justify-center shrink-0">
            <GraduationCap className="w-5 h-5" strokeWidth={1.7} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-lg tracking-tight text-zinc-950">Painel do professor</div>
            <div className="mt-1 text-sm text-zinc-500">App separado, com visão por turma/aluno/processo e evolução no tempo — abre em outra aba.</div>
            <div className="mt-3 flex items-center gap-1 text-xs text-zinc-900 font-medium">Abrir <ArrowRight className="w-3 h-3" /></div>
          </div>
        </a>

        {/* Sections */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {SECTIONS.map(s => (
            <Link key={s.to} to={s.to}
              className="lift card-sapiens hover:border-sapiens-accent rounded-2xl p-6 flex items-start gap-4"
              data-testid={`admin-section-${s.to.replace(/\//g, "-")}`}
            >
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white flex items-center justify-center shrink-0">
                <s.icon className="w-5 h-5" strokeWidth={1.7} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-display font-bold text-lg tracking-tight text-zinc-950">{s.title}</div>
                <div className="mt-1 text-sm text-zinc-500">{s.desc}</div>
                <div className="mt-3 flex items-center gap-1 text-xs text-zinc-900 font-medium">
                  Abrir <ArrowRight className="w-3 h-3" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
