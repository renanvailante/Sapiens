import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import { LogOut, Compass, History, Zap, Brain, ShieldCheck, MoreHorizontal, Trash2, LayoutGrid } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "./ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "./ui/sheet";
import BrandMark from "./BrandMark";

// Única fonte da lista de navegação — usada tanto nos links visíveis em
// desktop (+ dropdown "mais") quanto no menu mobile, pra nunca divergir.
const PRIMARY_LINKS = [
  { to: "/dashboard", icon: LayoutGrid, label: "Painel", testid: "nav-dashboard" },
  { to: "/exams", icon: Compass, label: "Provas", testid: "nav-exams" },
  { to: "/cognitive-profile", icon: Brain, label: "Cognitivo", testid: "nav-cognitive", tour: "nav-cognitive" },
];
const SECONDARY_LINKS = [
  { to: "/history", icon: History, label: "Histórico", testid: "nav-history" },
  { to: "/feed", icon: Zap, label: "Feed", testid: "nav-feed" },
  { to: "/trash", icon: Trash2, label: "Lixeira", testid: "nav-trash" },
];

// Saldo de Sparks — sempre visível (mesmo no mobile), mas discreto: um chip
// pequeno, sem chamar mais atenção que os links de navegação.
function SparksChip() {
  const [sparks, setSparks] = useState(null);
  useEffect(() => {
    let ativo = true;
    api.get("/firestore/students/me/sparks").then(({ data }) => { if (ativo) setSparks(data.sparks_balance); }).catch(() => {});
    return () => { ativo = false; };
  }, []);
  if (sparks == null) return null;
  return (
    <Link
      to="/sparks"
      className="inline-flex items-center gap-1.5 text-xs font-medium text-white/70 hover:text-white bg-white/8 hover:bg-white/15 border border-white/10 px-3 py-1.5 rounded-full transition-colors"
      data-testid="nav-sparks"
      data-tour="nav-sparks"
    >
      <Zap className="w-3.5 h-3.5 text-amber-400" /> {sparks}
    </Link>
  );
}

// Menu mobile: mesmas ferramentas do desktop (Painel/Provas/Cognitivo +
// Histórico/Feed/Lixeira + Admin/Sair), num painel deslizante — no desktop a
// largura sobra pra links soltos na barra, no mobile não, então isto é a
// única forma de alcançar as mesmas telas ali.
function MobileMenu({ user, onLogout, open, setOpen }) {
  const nav = useNavigate();
  const go = (to) => { setOpen(false); nav(to); };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent
        side="left"
        className="w-[80vw] max-w-xs border-r border-white/10 p-0 flex flex-col"
        style={{ background: "rgba(9,17,31,0.97)", backdropFilter: "blur(16px)" }}
        data-testid="nav-mobile-sheet"
      >
        <SheetTitle className="sr-only">Menu</SheetTitle>
        <SheetDescription className="sr-only">Navegação do Sapiens</SheetDescription>

        <div className="px-5 pt-6 pb-4 flex items-center gap-2 font-display text-2xl font-extrabold tracking-tighter text-white">
          <BrandMark className="w-6 h-6" />
          Sapiens
        </div>

        <div className="px-3 flex-1 overflow-y-auto">
          {[...PRIMARY_LINKS, ...SECONDARY_LINKS].map((l) => (
            <button
              key={l.to}
              onClick={() => go(l.to)}
              className="w-full flex items-center gap-3 text-left text-[15px] text-white/80 hover:text-white hover:bg-white/8 px-3 py-3 rounded-xl transition-colors"
              data-testid={`nav-mobile-${l.testid}`}
            >
              <l.icon className="w-4.5 h-4.5" /> {l.label}
            </button>
          ))}
          {user.is_admin && (
            <button
              onClick={() => go("/admin")}
              className="w-full flex items-center gap-3 text-left text-[15px] text-emerald-300 hover:bg-emerald-500/10 px-3 py-3 rounded-xl transition-colors"
              data-testid="nav-mobile-admin"
            >
              <ShieldCheck className="w-4.5 h-4.5" /> Admin
            </button>
          )}
        </div>

        <div className="px-5 pb-6 pt-3 border-t border-white/10">
          <button
            onClick={async () => { setOpen(false); await onLogout(); }}
            className="pill btn-sapiens w-full flex items-center justify-center gap-2 text-sm font-medium px-4 py-3 rounded-full"
            data-testid="nav-mobile-logout"
          >
            <LogOut className="w-4 h-4" /> Sair
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default function Nav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const doLogout = async () => { await logout(); nav("/"); };

  return (
    <div className="glass sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
        {user ? (
          <button
            onClick={() => setMenuOpen(true)}
            className="md:hidden flex items-center justify-center w-10 h-10 rounded-xl bg-sapiens-accent/20 border border-sapiens-accent/50 text-white active:scale-95 transition-transform"
            data-testid="nav-mobile-trigger"
            aria-label="Abrir menu"
          >
            <BrandMark className="w-5 h-5" />
          </button>
        ) : (
          <span className="md:hidden" />
        )}
        <Link to={user ? "/dashboard" : "/"} className="hidden md:flex items-center gap-2.5 font-display text-3xl font-extrabold tracking-tighter text-white" data-testid="nav-brand">
          <BrandMark className="w-8 h-8" />
          Sapiens
        </Link>
        {user && (
          <div className="flex items-center gap-1 md:gap-3">
            {PRIMARY_LINKS.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                className="hidden md:flex items-center gap-2 text-sm text-white/60 hover:text-white px-3 py-2 rounded-full transition-colors"
                data-testid={l.testid}
                data-tour={l.tour}
              >
                <l.icon className="w-4 h-4" /> {l.label}
              </Link>
            ))}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="hidden md:flex items-center justify-center text-white/60 hover:text-white w-9 h-9 rounded-full transition-colors" data-testid="nav-more">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="rounded-xl">
                {SECONDARY_LINKS.map((l) => (
                  <DropdownMenuItem key={l.to} onClick={() => nav(l.to)} data-testid={l.testid}>
                    <l.icon className="w-4 h-4 mr-2" /> {l.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <SparksChip />

            {user.is_admin && (
              <Link to="/admin" className="hidden md:inline-flex pill items-center gap-2 text-xs md:text-sm font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-400/30 hover:bg-emerald-500/25 px-3 py-2 rounded-full" data-testid="nav-admin">
                <ShieldCheck className="w-4 h-4" /> Admin
              </Link>
            )}
            <button
              onClick={doLogout}
              className="hidden md:flex pill btn-sapiens items-center gap-2 text-sm font-medium px-4 py-2 rounded-full"
              data-testid="nav-logout"
            >
              <LogOut className="w-4 h-4" /> <span className="hidden sm:inline">Sair</span>
            </button>

            <MobileMenu user={user} onLogout={doLogout} open={menuOpen} setOpen={setMenuOpen} />
          </div>
        )}
      </div>
    </div>
  );
}
