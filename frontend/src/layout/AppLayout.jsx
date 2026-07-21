import { useEffect, useState, createContext, useContext, useMemo } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

const FiltersCtx = createContext(null);
export const useFilters = () => useContext(FiltersCtx);

const NAV = [
  { to: "/turma", label: "Visão da turma", testid: "nav-turma" },
  { to: "/processo", label: "Processo cognitivo", testid: "nav-processo" },
  { to: "/aluno", label: "Aluno", testid: "nav-aluno" },
  { to: "/evolucao", label: "Evolução temporal", testid: "nav-evolucao" },
  { to: "/taxonomia", label: "Taxonomia", testid: "nav-taxonomia" },
  { to: "/import", label: "Importar dados", testid: "nav-import" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const [filters, setFilters] = useState({
    turma: "", periodo: "", disciplina: "", ano_escolar: "", banca: "", prova: "",
  });
  const [options, setOptions] = useState({
    turmas: [], periodos: [], disciplinas: [],
    anos_escolares: [], bancas: [], provas: [], versoes_taxonomia: [],
  });

  const refreshFilters = async () => {
    try {
      const { data } = await api.get("/filters");
      setOptions(data);
      // Default: pick first turma+periodo if empty
      setFilters((f) => ({
        ...f,
        turma: f.turma || data.turmas[0] || "",
        periodo: f.periodo || data.periodos[0] || "",
      }));
    } catch (e) {
      // silent
    }
  };

  useEffect(() => { refreshFilters(); }, []);

  const versaoAtual = useMemo(() => {
    // Versão referente ao turma+periodo selecionado; simplifica: exibe a mais recente encontrada
    return options.versoes_taxonomia?.slice(-1)[0] || "Sem dado";
  }, [options]);

  const doLogout = async () => {
    await logout();
    nav("/login");
  };

  const ctx = { filters, setFilters, options, refreshFilters };

  return (
    <FiltersCtx.Provider value={ctx}>
      <div className="min-h-screen flex flex-col bg-background">
        {/* Header */}
        <header className="border-b border-border bg-white sticky top-0 z-40">
          <div className="flex items-center justify-between px-6 h-14">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-[hsl(214_100%_34%)]" aria-hidden />
                <div>
                  <div className="text-sm font-semibold leading-none" style={{ fontFamily: 'Chivo, sans-serif' }}>
                    Sapiens Dashboard
                  </div>
                  <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground leading-none mt-0.5">
                    Observabilidade pedagógica
                  </div>
                </div>
              </div>
              <div
                data-testid="taxonomy-version-badge"
                className="hidden md:flex items-center gap-2 border border-border px-3 py-1 text-[11px] font-mono"
                title="Versão da taxonomia associada aos dados exibidos"
              >
                <span className="w-1.5 h-1.5 bg-amber-500" />
                <span className="text-muted-foreground uppercase tracking-wider">Taxonomia</span>
                <span className="text-foreground">{versaoAtual}</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-muted-foreground hidden sm:inline" data-testid="user-email">
                {user?.email}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={doLogout}
                data-testid="logout-btn"
                className="h-8"
              >
                Sair
              </Button>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex items-center border-t border-border overflow-x-auto">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                data-testid={n.testid}
                className={({ isActive }) =>
                  `px-4 h-10 flex items-center text-[13px] border-r border-border whitespace-nowrap transition-colors ` +
                  (isActive
                    ? "bg-[hsl(214_100%_34%)] text-white"
                    : "text-foreground hover:bg-[hsl(0_0%_96%)]")
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>

          {/* Global filters toolbar */}
          <div className="flex flex-wrap items-center gap-2 px-6 py-2 border-t border-border bg-[hsl(0_0%_98%)]">
            <FilterSelect label="Turma" value={filters.turma}
              onChange={(v) => setFilters({ ...filters, turma: v })}
              options={options.turmas} testid="filter-turma" />
            <FilterSelect label="Período" value={filters.periodo}
              onChange={(v) => setFilters({ ...filters, periodo: v })}
              options={options.periodos} testid="filter-periodo" />
            <FilterSelect label="Disciplina" value={filters.disciplina}
              onChange={(v) => setFilters({ ...filters, disciplina: v })}
              options={options.disciplinas} testid="filter-disciplina" allowClear />
            <FilterSelect label="Ano escolar" value={filters.ano_escolar}
              onChange={(v) => setFilters({ ...filters, ano_escolar: v })}
              options={options.anos_escolares} testid="filter-ano" allowClear />
            <FilterSelect label="Banca" value={filters.banca}
              onChange={(v) => setFilters({ ...filters, banca: v })}
              options={options.bancas} testid="filter-banca" allowClear />
            <FilterSelect label="Prova" value={filters.prova}
              onChange={(v) => setFilters({ ...filters, prova: v })}
              options={options.provas} testid="filter-prova" allowClear />
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="border-t border-border px-6 py-3 text-[11px] font-mono text-muted-foreground flex justify-between">
          <span>Sapiens Dashboard · Camada de visualização · Não gera diagnósticos</span>
          <span>Agregações rotuladas como &quot;Calculado pelo Dashboard&quot;</span>
        </footer>
      </div>
    </FiltersCtx.Provider>
  );
}

function FilterSelect({ label, value, onChange, options, testid, allowClear }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <Select value={value || undefined} onValueChange={(v) => onChange(v === "__all__" ? "" : v)}>
        <SelectTrigger
          data-testid={testid}
          className="h-7 min-w-[130px] text-xs border-border bg-white"
        >
          <SelectValue placeholder="Todos" />
        </SelectTrigger>
        <SelectContent>
          {allowClear && <SelectItem value="__all__">Todos</SelectItem>}
          {(options || []).map((o) => (
            <SelectItem key={o} value={o}>{o}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
