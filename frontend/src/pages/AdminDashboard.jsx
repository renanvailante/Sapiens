import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { FileText, Zap, Brain, Users, ClipboardList, ArrowRight, ShieldCheck, RefreshCw, Database } from "lucide-react";

function StatCard({ label, value, hint }) {
  return (
    <div className="bg-white border border-zinc-200 rounded-2xl p-5">
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
  { to: "/admin/history", icon: ClipboardList, title: "Histórico do Aluno",
    desc: "Response Event Store — histórico append-only por aluno com filtros." },
  { to: "/admin/users", icon: Users, title: "Usuários & permissões",
    desc: "Conceder ou revogar acesso administrativo aos usuários." },
];

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  useEffect(() => {
    api.get("/admin/summary").then(({ data }) => setSummary(data)).catch(() => {});
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/admin/firestore/sync");
      setLastSync(data);
      toast.success(`Firestore sincronizado: ${data.master_count} questões (master), ${data.public_count} publicadas para alunos.`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao sincronizar Firestore.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-12">
        <div className="flex items-center gap-3 mb-3">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500">Área administrativa</div>
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="admin-title">
          Painel de administração
        </h1>
        <p className="mt-3 text-zinc-500 max-w-2xl">
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
        <div className="mt-10 bg-white border border-zinc-200 rounded-2xl p-6 flex flex-col md:flex-row md:items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0">
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
            className="shrink-0 inline-flex items-center gap-2 rounded-xl bg-zinc-950 px-5 py-3 text-sm font-semibold text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Sincronizando…" : "Sincronizar Firestore"}
          </button>
        </div>

        {/* Sections */}
        <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
          {SECTIONS.map(s => (
            <Link key={s.to} to={s.to}
              className="lift bg-white border border-zinc-200 hover:border-zinc-900 rounded-2xl p-6 flex items-start gap-4"
              data-testid={`admin-section-${s.to.replace(/\//g, "-")}`}
            >
              <div className="w-11 h-11 rounded-xl bg-zinc-950 text-white flex items-center justify-center shrink-0">
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
