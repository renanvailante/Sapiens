import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import { LogOut, Compass, History, Zap, Brain, ShieldCheck, MoreHorizontal, Trash2, LayoutGrid, GraduationCap, PenLine, MessageCircle, BookOpen, ListChecks, MessageSquareWarning, CalendarClock } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "./ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetDescription } from "./ui/sheet";
import BrandMark from "./BrandMark";
import Mentis from "./Mentis";
import AulasParticularesModal from "./AulasParticularesModal";

// Única fonte da lista de navegação — usada tanto nos links visíveis em
// desktop (+ dropdown "mais") quanto no menu mobile, pra nunca divergir.
// A ordem dos quatro primários é decisão de produto (2026-09-09), não
// arbitrária: Painel (para onde tudo volta), Treino, Redação e Mentis — as
// quatro coisas que o aluno FAZ. "Provas" saiu da barra porque o Painel abre
// nelas com o botão principal, e "Cognitivo" porque é leitura de resultado,
// não atividade; as duas continuam a um clique, no menu "mais".
const PRIMARY_LINKS = [
  { to: "/dashboard", icon: LayoutGrid, label: "Painel", testid: "nav-dashboard", tour: "nav-dashboard" },
  { to: "/treino", icon: BookOpen, label: "Treino", testid: "nav-treino", tour: "nav-treino" },
  { to: "/redacao", icon: PenLine, label: "Redação", testid: "nav-redacao", tour: "nav-redacao" },
  { to: "/mentis", icon: MessageCircle, label: "Mentis", testid: "nav-mentis", tour: "nav-mentis", mascote: true },
];
const SECONDARY_LINKS = [
  { to: "/exams", icon: Compass, label: "Provas do ENEM", testid: "nav-exams" },
  { to: "/revisoes", icon: CalendarClock, label: "Revisões", testid: "nav-revisoes" },
  { to: "/cognitive-profile", icon: Brain, label: "Cognitivo", testid: "nav-cognitive" },
  { to: "/minhas-questoes", icon: ListChecks, label: "Minhas questões", testid: "nav-minhas-questoes" },
  { to: "/history", icon: History, label: "Histórico", testid: "nav-history" },
  { to: "/feed", icon: Zap, label: "Feed", testid: "nav-feed" },
  { to: "/sugestoes", icon: MessageSquareWarning, label: "Reclamações e sugestões", testid: "nav-sugestoes" },
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

// Menu mobile: mesmas ferramentas do desktop (Painel/Treino/Redação/Mentis +
// o que está no menu "mais" + Admin/Sair), num painel deslizante — no desktop a
// largura sobra pra links soltos na barra, no mobile não, então isto é a
// única forma de alcançar as mesmas telas ali.
function MobileMenu({ user, onLogout, open, setOpen, onOpenAulas }) {
  const nav = useNavigate();
  const { pathname } = useLocation();
  // `de` é a tela de onde a pessoa saiu — só a página de reclamações e
  // sugestões usa isso hoje, para o texto chegar à equipe já dizendo de qual
  // tela veio a queixa.
  const go = (to) => { setOpen(false); nav(to, { state: { de: pathname } }); };

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

        <div className="px-3">
          <button
            onClick={() => { setOpen(false); onOpenAulas(); }}
            className="btn-calor w-full flex items-center gap-3 text-left text-[15px] px-3 py-3.5 rounded-xl transition-all mb-2"
            data-testid="nav-mobile-aulas-particulares"
          >
            <GraduationCap className="w-4.5 h-4.5" /> Tenha aulas conosco
          </button>
        </div>

        <div className="px-3 flex-1 overflow-y-auto">
          {[...PRIMARY_LINKS, ...SECONDARY_LINKS].map((l) => (
            <button
              key={l.to}
              onClick={() => go(l.to)}
              className="w-full flex items-center gap-3 text-left text-[15px] text-white/80 hover:text-white hover:bg-white/8 px-3 py-3 rounded-xl transition-colors"
              data-testid={`nav-mobile-${l.testid}`}
            >
              {l.mascote ? <Mentis className="w-5 h-5" variante="icone" /> : <l.icon className="w-4.5 h-4.5" />} {l.label}
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
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [showAulasModal, setShowAulasModal] = useState(false);
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
        <Link to={user ? "/dashboard" : "/"} className="hidden md:flex items-center gap-2 lg:gap-2.5 font-display text-2xl lg:text-3xl font-extrabold tracking-tighter text-white" data-testid="nav-brand">
          <BrandMark className="w-7 h-7 lg:w-8 lg:h-8" />
          Sapiens
        </Link>
        {user && (
          <div className="flex items-center gap-1 md:gap-2 lg:gap-3">
            {/* Envelope próprio (e não os links soltos) porque o guia de
                primeira sessão aponta para a BARRA inteira num passo só. */}
            <div className="hidden md:flex items-center gap-0.5 lg:gap-2" data-tour="nav-primarios">
              {PRIMARY_LINKS.map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="flex items-center gap-1.5 lg:gap-2 text-sm text-white/60 hover:text-white px-2 lg:px-3 py-2 rounded-full transition-colors"
                  data-testid={l.testid}
                  data-tour={l.tour}
                >
                  {l.mascote ? <Mentis className="w-5 h-5" variante="icone" /> : <l.icon className="w-4 h-4" />} {l.label}
                </Link>
              ))}
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="hidden md:flex items-center justify-center text-white/60 hover:text-white w-9 h-9 rounded-full transition-colors" data-testid="nav-more" data-tour="nav-more">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="rounded-xl">
                {SECONDARY_LINKS.map((l) => (
                  <DropdownMenuItem key={l.to} onClick={() => nav(l.to, { state: { de: pathname } })} data-testid={l.testid}>
                    <l.icon className="w-4 h-4 mr-2" /> {l.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <button
              onClick={() => setShowAulasModal(true)}
              className="btn-calor pill hidden md:inline-flex shrink-0 items-center gap-2 whitespace-nowrap text-xs md:text-sm px-3.5 py-2 rounded-full"
              data-testid="nav-aulas-particulares"
              data-tour="nav-aulas"
            >
              <GraduationCap className="w-4 h-4" />
              {/* Rótulo inteiro só a partir de `xl`: entre 768 e 1280 a barra
                  já leva quatro links fixos, o saldo e — para admin — mais uma
                  pílula, e o texto longo era o que empurrava tudo para fora. */}
              <span className="hidden xl:inline">Tenha aulas conosco</span>
              <span className="xl:hidden">Aulas</span>
            </button>

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
              <LogOut className="w-4 h-4" /> <span className="hidden lg:inline">Sair</span>
            </button>

            <MobileMenu
              user={user}
              onLogout={doLogout}
              open={menuOpen}
              setOpen={setMenuOpen}
              onOpenAulas={() => setShowAulasModal(true)}
            />
          </div>
        )}
      </div>
      <AulasParticularesModal open={showAulasModal} onClose={() => setShowAulasModal(false)} />
    </div>
  );
}
