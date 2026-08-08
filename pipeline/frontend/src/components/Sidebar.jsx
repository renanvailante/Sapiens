import { NavLink } from "react-router-dom";
import { LayoutDashboard, Network, Sparkles, ListTree } from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard" },
  { to: "/ontologia", label: "Ontologia Cognitiva", icon: Network, testId: "nav-ontologia" },
  { to: "/gerador", label: "Gerador de Pipeline", icon: Sparkles, testId: "nav-gerador" },
  { to: "/questoes", label: "Questões Processadas", icon: ListTree, testId: "nav-questoes" },
];

export default function Sidebar() {
  return (
    <aside
      data-testid="sidebar"
      className="hidden md:flex md:flex-col w-72 shrink-0 border-r border-border bg-white"
    >
      <div className="px-6 py-8 border-b border-border">
        <div className="overline text-muted-foreground">Sapiens</div>
        <div className="mt-1 text-2xl font-black tracking-tight text-foreground">
          Anotador Cognitivo
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          Motor de anotação de vestibulares
        </div>
      </div>

      <nav className="flex-1 py-6">
        <div className="overline px-6 mb-3 text-muted-foreground">Navegação</div>
        <ul className="grid-lines border-y border-border">
          {links.map(({ to, label, icon: Icon, testId }) => (
            <li key={to}>
              <NavLink
                data-testid={testId}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-6 py-3 text-sm transition-colors ${
                    isActive
                      ? "bg-foreground text-white"
                      : "text-foreground hover:bg-secondary"
                  }`
                }
              >
                <Icon className="h-4 w-4" strokeWidth={2} />
                <span className="font-medium">{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="px-6 py-6 border-t border-border">
        <div className="overline text-muted-foreground mb-2">Motor</div>
        <div className="font-mono text-xs text-foreground">gemini-3-flash</div>
        <div className="mt-3 overline text-muted-foreground mb-1">Versão</div>
        <div className="font-mono text-xs text-muted-foreground">Sapiens · 0.1.0</div>
      </div>
    </aside>
  );
}
