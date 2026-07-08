import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LogOut, Compass, History, Sparkles, Trash2 } from "lucide-react";

export default function Nav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="glass sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
        <Link to={user ? "/dashboard" : "/"} className="font-display text-2xl font-extrabold tracking-tighter" data-testid="nav-brand">
          Sapiens<span className="text-emerald-500">.</span>
        </Link>
        {user && (
          <div className="flex items-center gap-1 md:gap-3">
            <Link to="/dashboard" className="hidden md:flex items-center gap-2 text-sm text-zinc-600 hover:text-zinc-900 px-3 py-2 rounded-full" data-testid="nav-dashboard">
              <Sparkles className="w-4 h-4" /> Painel
            </Link>
            <Link to="/history" className="hidden md:flex items-center gap-2 text-sm text-zinc-600 hover:text-zinc-900 px-3 py-2 rounded-full" data-testid="nav-history">
              <History className="w-4 h-4" /> Histórico
            </Link>
            <Link to="/trash" className="hidden md:flex items-center gap-2 text-sm text-zinc-600 hover:text-zinc-900 px-3 py-2 rounded-full" data-testid="nav-trash">
              <Trash2 className="w-4 h-4" /> Lixeira
            </Link>
            <Link to="/exams" className="hidden md:flex items-center gap-2 text-sm text-zinc-600 hover:text-zinc-900 px-3 py-2 rounded-full" data-testid="nav-exams">
              <Compass className="w-4 h-4" /> Provas
            </Link>
            <button
              onClick={async () => { await logout(); nav("/"); }}
              className="pill flex items-center gap-2 text-sm font-medium bg-zinc-950 hover:bg-zinc-800 text-white px-4 py-2 rounded-full"
              data-testid="nav-logout"
            >
              <LogOut className="w-4 h-4" /> Sair
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
