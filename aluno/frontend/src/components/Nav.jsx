import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LogOut, Compass, History, Sparkles, Trash2, Zap, Brain, ShieldCheck } from "lucide-react";
import BrandMark from "./BrandMark";

export default function Nav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="glass sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
        <Link to={user ? "/dashboard" : "/"} className="flex items-center gap-2.5 font-display text-3xl font-extrabold tracking-tighter text-white" data-testid="nav-brand">
          <BrandMark className="w-8 h-8" />
          Sapiens
        </Link>
        {user && (
          <div className="flex items-center gap-1 md:gap-3">
            <Link to="/dashboard" className="hidden md:flex items-center gap-2 text-sm text-white/60 hover:text-white px-3 py-2 rounded-full transition-colors" data-testid="nav-dashboard">
              <Sparkles className="w-4 h-4" /> Painel
            </Link>
            <Link to="/history" className="hidden md:flex items-center gap-2 text-sm text-white/60 hover:text-white px-3 py-2 rounded-full transition-colors" data-testid="nav-history">
              <History className="w-4 h-4" /> Histórico
            </Link>
            <Link to="/trash" className="hidden md:flex items-center gap-2 text-sm text-white/60 hover:text-white px-3 py-2 rounded-full transition-colors" data-testid="nav-trash">
              <Trash2 className="w-4 h-4" /> Lixeira
            </Link>
            <Link to="/feed" className="hidden md:flex items-center gap-2 text-sm text-white/60 hover:text-white px-3 py-2 rounded-full transition-colors" data-testid="nav-feed">
              <Zap className="w-4 h-4" /> Feed
            </Link>
            <Link to="/cognitive-profile" className="hidden md:flex items-center gap-2 text-sm text-white/60 hover:text-white px-3 py-2 rounded-full transition-colors" data-testid="nav-cognitive">
              <Brain className="w-4 h-4" /> Cognitivo
            </Link>
            <Link to="/exams" className="hidden md:flex items-center gap-2 text-sm text-white/60 hover:text-white px-3 py-2 rounded-full transition-colors" data-testid="nav-exams">
              <Compass className="w-4 h-4" /> Provas
            </Link>
            {user.is_admin && (
              <Link to="/admin" className="pill inline-flex items-center gap-2 text-xs md:text-sm font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-400/30 hover:bg-emerald-500/25 px-3 py-2 rounded-full" data-testid="nav-admin">
                <ShieldCheck className="w-4 h-4" /> Admin
              </Link>
            )}
            <button
              onClick={async () => { await logout(); nav("/"); }}
              className="pill btn-sapiens flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-full"
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
