import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";
import { ShieldCheck, ShieldOff } from "lucide-react";

export default function AdminUsers() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const load = () => api.get("/admin/users").then(({ data }) => setUsers(data));
  useEffect(() => { load(); }, []);

  const toggle = async (u) => {
    try {
      await api.patch(`/admin/users/${u.user_id}`, { is_admin: !u.is_admin });
      toast.success(!u.is_admin ? "Usuário promovido a admin." : "Acesso admin removido.");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Falha ao atualizar.");
    }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Admin · Usuários</div>
        <h1 className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950" data-testid="admin-users-title">
          Permissões
        </h1>
        <p className="mt-3 text-zinc-500 max-w-lg">Alterne o acesso administrativo por usuário. Você não pode remover seu próprio acesso.</p>

        <div className="mt-8 space-y-2">
          {users.map(u => (
            <div key={u.user_id} className="bg-white border border-zinc-200 rounded-2xl p-4 flex items-center gap-4" data-testid={`admin-user-row-${u.user_id}`}>
              <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-600 font-display font-bold">
                {u.name?.[0]?.toUpperCase() || "?"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-display font-semibold text-zinc-900">{u.name}</div>
                <div className="text-sm text-zinc-500 truncate">{u.email}</div>
              </div>
              <div className="text-xs font-mono-alt text-zinc-500">{u.provider}</div>
              {u.is_admin ? (
                <span className="inline-flex items-center gap-1.5 text-xs bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-1 rounded-full">
                  <ShieldCheck className="w-3 h-3" /> admin
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs bg-zinc-100 text-zinc-500 px-2.5 py-1 rounded-full">aluno</span>
              )}
              <button
                onClick={() => toggle(u)}
                disabled={me?.user_id === u.user_id && u.is_admin}
                className="pill text-xs font-medium px-3 py-1.5 rounded-full border border-zinc-200 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed"
                data-testid={`admin-user-toggle-${u.user_id}`}
              >
                {u.is_admin ? <><ShieldOff className="w-3.5 h-3.5 inline mr-1" /> Revogar</> : <><ShieldCheck className="w-3.5 h-3.5 inline mr-1" /> Promover</>}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
