import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { Brain, ChevronRight } from "lucide-react";

const LEVEL_LABEL = {
  dominio: "Domínio",
  competencia: "Competência",
  processo: "Processo",
  habilidade: "Habilidade",
};

// Achata a árvore em lista plana (recursão em função pura — evita o bug do
// Babel ao compilar componentes JSX auto-recursivos).
function flatten(nodes, depth, ancestors, out) {
  (nodes || []).forEach((n) => {
    const hasChildren = Array.isArray(n.children) && n.children.length > 0;
    out.push({
      code: n.code,
      nome: n.nome,
      level: n.level,
      answered: Boolean(n.answered),
      depth,
      hasChildren,
      ancestors,
    });
    if (hasChildren) flatten(n.children, depth + 1, ancestors.concat(n.code), out);
  });
  return out;
}

function nameClass(level, answered) {
  let size = "text-sm";
  if (level === "dominio") size = "font-display font-bold text-lg";
  else if (level === "competencia") size = "font-semibold text-sm";
  const color = answered ? "text-zinc-950" : "text-zinc-400";
  return "mt-0.5 leading-snug " + size + " " + color;
}

export default function CognitiveProfile() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(() => new Set());

  useEffect(() => {
    api.get("/cognitive-profile").then((res) => {
      setData(res.data);
      // Colapsa processos por padrão (esconde habilidades até expandir).
      const flat = flatten(res.data && res.data.ontology_tree, 0, [], []);
      const initial = new Set();
      flat.forEach((n) => {
        if (n.level === "processo" && n.hasChildren) initial.add(n.code);
      });
      setCollapsed(initial);
      setLoading(false);
    });
  }, []);

  const flat = useMemo(
    () => flatten(data && data.ontology_tree, 0, [], []),
    [data]
  );

  const stats = useMemo(() => {
    let answered = 0;
    let total = 0;
    flat.forEach((n) => {
      if (n.level === "processo") {
        total += 1;
        if (n.answered) answered += 1;
      }
    });
    return { answered, total };
  }, [flat]);

  const toggle = (code) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  if (loading) {
    return (
      <div>
        <Nav />
        <div className="p-10 text-zinc-500">Compondo perfil...</div>
      </div>
    );
  }

  // Visível se nenhum ancestral está colapsado.
  const visible = flat.filter((n) => n.ancestors.every((a) => !collapsed.has(a)));

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Perfil cognitivo</div>
        <h1
          className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950"
          data-testid="cp-title"
        >
          Como você pensa.
        </h1>
        <p className="mt-3 text-zinc-500 max-w-lg">
          Rede cognitiva Sapiens v1.4 — domínio, competência, processo e habilidade.
          Nós <span className="text-zinc-900 font-medium">destacados</span> foram acionados pelas questões que você respondeu;
          os <span className="text-zinc-400">esmaecidos</span> ainda não.
        </p>

        <div className="mt-8 bg-zinc-950 text-white rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Processos ativados</div>
            <div className="mt-2 font-display text-3xl font-bold tracking-tight" data-testid="cp-covered">
              {stats.answered}
              <span className="text-zinc-500 text-xl"> / {stats.total}</span>
            </div>
          </div>
          <div className="flex items-center gap-5 text-sm text-zinc-300">
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-white" /> Respondido
            </span>
            <span className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-zinc-600" /> Não respondido
            </span>
          </div>
        </div>

        <div className="mt-6 bg-white border border-zinc-200 rounded-2xl p-4 md:p-6" data-testid="cp-tree">
          {visible.length === 0 ? (
            <div className="text-center py-10">
              <Brain className="w-8 h-8 text-zinc-400 mx-auto" strokeWidth={1.4} />
              <div className="mt-4 font-display font-bold text-xl text-zinc-950">Ontologia indisponível.</div>
            </div>
          ) : (
            <div>
              {visible.map((n) => {
                const isCollapsed = collapsed.has(n.code);
                const rowClass =
                  "group flex items-start gap-2 py-1.5 rounded-lg px-2 transition-colors " +
                  (n.hasChildren ? "cursor-pointer hover:bg-zinc-50" : "") +
                  (n.depth === 0 ? " mt-2 border-t border-zinc-100 pt-3 first:mt-0 first:border-0 first:pt-1.5" : "");
                const chevronClass =
                  "mt-0.5 w-4 h-4 shrink-0 transition-transform " +
                  (isCollapsed ? "" : "rotate-90 ") +
                  (n.answered ? "text-zinc-500" : "text-zinc-300");
                const codeClass =
                  "font-mono-alt text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded " +
                  (n.answered ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-400");
                const levelClass =
                  "text-[9px] uppercase tracking-[0.25em] font-mono-alt " +
                  (n.answered ? "text-zinc-400" : "text-zinc-300");
                return (
                  <div
                    key={n.code}
                    className={rowClass}
                    style={{ marginLeft: n.depth * 20 }}
                    onClick={() => n.hasChildren && toggle(n.code)}
                    data-testid={"node-" + n.code}
                    data-answered={n.answered}
                  >
                    {n.hasChildren ? (
                      <ChevronRight className={chevronClass} strokeWidth={2} />
                    ) : (
                      <span
                        className="mt-2 ml-1 mr-1 w-1.5 h-1.5 rounded-full shrink-0"
                        style={{ background: n.answered ? "#18181b" : "#d4d4d8" }}
                      />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={codeClass}>{n.code}</span>
                        <span className={levelClass}>{LEVEL_LABEL[n.level]}</span>
                      </div>
                      <div className={nameClass(n.level, n.answered)}>{n.nome}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
