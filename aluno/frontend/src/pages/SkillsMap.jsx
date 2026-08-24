import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import {
  Hash, Shapes, Workflow, Network, Languages, Microscope,
  Zap, RefreshCw, TrendingUp, Target, X,
  Trophy, AlertCircle, Flame, Repeat, Clock, ChevronDown, ChevronUp,
  TrendingDown, Minus, BarChart3, LayoutList, Hexagon as HexagonIcon,
} from "lucide-react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
} from "recharts";

// Mapa de Habilidades: camada puramente cosmética/gamificada. Rótulos,
// agrupamentos e a própria forma da árvore vêm do backend
// (cosmetic_skills_map.py) e são genéricos por design — nunca os nomes
// reais da ontologia. Nunca ler este componente (ou os dados que ele
// consome) como fonte de verdade pedagógica.
const HUB_ICON = { 1: Hash, 2: Shapes, 3: Workflow, 4: Network, 5: Languages, 6: Microscope };
const HUB_COLOR = { 1: "#f59e0b", 2: "#10b981", 3: "#8b5cf6", 4: "#f43f5e", 5: "#3b82f6", 6: "#14b8a6" };

function seedOf(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

// Curva orgânica hub -> item: bezier cúbica com leve "wobble" determinístico
// por folha, pra nenhum fio ficar reto ou paralelo aos outros.
function organicPath(x0, y0, x1, y1, seed) {
  const dx = x1 - x0;
  const dy = y1 - y0;
  const wobble = ((seed % 11) - 5) / 5;
  const c1x = x0 + dx * 0.4;
  const c1y = y0 + dy * 0.15 + wobble * 16;
  const c2x = x0 + dx * 0.72;
  const c2y = y1 - dy * 0.15 - wobble * 10;
  return `M ${x0} ${y0} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${x1} ${y1}`;
}

const NARRATIVE_STYLE = {
  resumo: { icon: BarChart3, color: "#3b82f6" },
  acerto: { icon: TrendingUp, color: "#10b981" },
  sparks: { icon: Zap, color: "#f59e0b" },
  melhor: { icon: Trophy, color: "#10b981" },
  pior: { icon: AlertCircle, color: "#f43f5e" },
  evolucao_up: { icon: TrendingUp, color: "#10b981" },
  evolucao_down: { icon: TrendingDown, color: "#f43f5e" },
  evolucao_estavel: { icon: Minus, color: "#71717a" },
  streak: { icon: Flame, color: "#f59e0b" },
  recorrente: { icon: Repeat, color: "#8b5cf6" },
  rodada: { icon: Clock, color: "#3b82f6" },
  vazio: { icon: Target, color: "#71717a" },
};

function NarrativeRow({ item, index }) {
  const [open, setOpen] = useState(false);
  const style = NARRATIVE_STYLE[item.type] || NARRATIVE_STYLE.resumo;
  const Icon = style.icon;
  const expandable = item.type === "rodada";
  return (
    <div
      className={"flex items-start gap-3 py-2.5 border-b border-zinc-100 last:border-0" + (expandable ? " cursor-pointer" : "")}
      onClick={() => expandable && setOpen((v) => !v)}
      data-testid={"sm-narrativa-" + index}
    >
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
        style={{ background: style.color + "1a", color: style.color }}
      >
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm text-zinc-700 leading-snug">{item.text}</p>
          {expandable && (open ? <ChevronUp className="w-3.5 h-3.5 text-zinc-400 shrink-0" /> : <ChevronDown className="w-3.5 h-3.5 text-zinc-400 shrink-0" />)}
        </div>
        {expandable && open && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {item.sparks_ganhos > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 border border-amber-100 rounded-full px-2 py-0.5">
                <Zap className="w-3 h-3" /> +{item.sparks_ganhos}
              </span>
            )}
            {(item.padroes || []).length > 0 ? (
              item.padroes.map((p) => (
                <span key={p} className="text-[11px] text-zinc-600 bg-zinc-100 rounded-full px-2 py-0.5">{p}</span>
              ))
            ) : (
              <span className="text-[11px] text-zinc-400">Sem padrão de erro recorrente nessa rodada.</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Ícone clicável em cada vértice do hexágono — troca de cor/preenchimento ao
// selecionar, e empurra o ícone um pouco além do raio padrão do tick.
function VertexTick(props) {
  const { x, y, cx, cy, payload, hubs, activeHub, onSelect } = props;
  const hub = (hubs || []).find((h) => h.label === payload.value);
  if (!hub) return null;
  const Icon = HUB_ICON[hub.hub] || Hash;
  const color = HUB_COLOR[hub.hub] || "#18181b";
  const isActive = activeHub === hub.hub;
  const dx = x - cx;
  const dy = y - cy;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const push = 14;
  const ix = x + (dx / dist) * push;
  const iy = y + (dy / dist) * push;
  return (
    <g
      transform={`translate(${ix},${iy})`}
      style={{ cursor: "pointer" }}
      onClick={() => onSelect(isActive ? null : hub.hub)}
      data-testid={"sm-vertex-" + hub.hub}
    >
      <circle r={16} fill={isActive ? color : "white"} stroke={color} strokeWidth={2} />
      <Icon x={-8} y={-8} width={16} height={16} color={isActive ? "white" : color} strokeWidth={2} />
    </g>
  );
}

function HubTreeCard({ hub, onLeaves, toggleLeaf }) {
  const Icon = HUB_ICON[hub.hub] || Hash;
  const color = HUB_COLOR[hub.hub] || "#18181b";
  const containerRef = useRef(null);
  const iconRef = useRef(null);
  const leafRefs = useRef(new Map());
  const [wires, setWires] = useState([]);

  useLayoutEffect(() => {
    const measure = () => {
      const c = containerRef.current;
      const ic = iconRef.current;
      if (!c || !ic) return;
      const cRect = c.getBoundingClientRect();
      const iRect = ic.getBoundingClientRect();
      const hx = iRect.left + iRect.width / 2 - cRect.left;
      const hy = iRect.top + iRect.height / 2 - cRect.top;
      const next = [];
      leafRefs.current.forEach((el, key) => {
        if (!el) return;
        const r = el.getBoundingClientRect();
        const lx = r.left - cRect.left;
        const ly = r.top + r.height / 2 - cRect.top;
        next.push({ key, d: organicPath(hx, hy, lx, ly, seedOf(key)) });
      });
      setWires(next);
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (containerRef.current) ro.observe(containerRef.current);
    window.addEventListener("resize", measure);
    return () => { ro.disconnect(); window.removeEventListener("resize", measure); };
  }, [hub]);

  return (
    <div className="card-sapiens rounded-2xl p-5" data-testid={"sm-hub-" + hub.hub}>
      <div className="flex items-center gap-3">
        <div
          ref={iconRef}
          className="w-12 h-12 rounded-full flex items-center justify-center shrink-0 text-white"
          style={{ background: color, boxShadow: `0 0 0 5px ${color}22` }}
        >
          <Icon className="w-5 h-5" strokeWidth={1.8} />
        </div>
        <div className="min-w-0">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">{hub.eyebrow}</div>
          <div className="font-display font-bold text-lg text-zinc-950 leading-tight truncate">{hub.label}</div>
        </div>
        <div className="ml-auto text-right shrink-0" data-testid={"sm-hub-mastery-" + hub.hub}>
          <div className="font-mono-alt text-lg font-bold" style={{ color }}>{hub.mastery}%</div>
          <div className="text-[9px] text-zinc-400 uppercase tracking-wide">dominado</div>
        </div>
      </div>

      <div ref={containerRef} className="relative mt-5">
        <svg className="absolute inset-0" width="100%" height="100%" style={{ overflow: "visible", pointerEvents: "none" }}>
          {wires.map((w) => (
            <path key={w.key} d={w.d} fill="none" stroke={color} strokeOpacity={0.4} strokeWidth={1.6} strokeLinecap="round" />
          ))}
        </svg>
        <div className="relative space-y-3">
          {(hub.branches || []).map((branch, bi) => (
            <div key={hub.hub + "-b" + bi}>
              <div className="text-[10.5px] font-semibold text-zinc-400 uppercase tracking-wide mb-1.5">{branch.name}</div>
              <div className="flex flex-wrap gap-2">
                {(branch.leaves || []).map((leaf, li) => {
                  const key = hub.hub + "-" + bi + "-" + li;
                  const on = onLeaves.has(key);
                  return (
                    <button
                      key={key}
                      ref={(el) => { if (el) leafRefs.current.set(key, el); else leafRefs.current.delete(key); }}
                      onClick={() => toggleLeaf(key)}
                      className="text-xs pl-3 pr-1.5 py-1.5 rounded-full border bg-white transition-colors flex items-center gap-1.5"
                      style={{ borderColor: on ? color : "#e4e4e7", color: on ? color : "#52525b" }}
                    >
                      {leaf.name}
                      <span
                        className="font-mono-alt font-bold rounded-full px-1.5 py-0.5 text-[10px]"
                        style={{ background: color + "1a", color }}
                      >
                        {Math.round(leaf.percent)}%
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Visão em lista hierárquica — mesma árvore de <HubTreeCard>, só que como
// texto indentado (hub > frente > item), pra quem prefere ler a evolução em
// vez de decifrar o hexágono.
function HierarchicalList({ hubs }) {
  return (
    <div className="card-sapiens rounded-2xl p-5 md:p-6 space-y-6" data-testid="sm-list-view">
      {(hubs || []).map((hub) => {
        const Icon = HUB_ICON[hub.hub] || Hash;
        const color = HUB_COLOR[hub.hub] || "#18181b";
        return (
          <div key={hub.hub}>
            <div className="flex items-center gap-2.5 mb-2">
              <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white" style={{ background: color }}>
                <Icon className="w-3.5 h-3.5" strokeWidth={1.8} />
              </div>
              <div className="font-display font-bold text-base text-zinc-950">{hub.label}</div>
              <div className="ml-auto font-mono-alt text-sm font-bold" style={{ color }}>{hub.mastery}%</div>
            </div>
            <div className="ml-3.5 pl-4 border-l border-zinc-200 space-y-1.5">
              {(hub.branches || []).flatMap((b) => b.leaves || []).map((leaf, i, arr) => (
                <div key={i} className="flex items-center gap-2 text-sm text-zinc-600">
                  <span className="text-zinc-300 font-mono-alt">{i === arr.length - 1 ? "└" : "├"}</span>
                  <span className="flex-1 truncate">{leaf.name}</span>
                  <span className="font-mono-alt font-bold text-xs" style={{ color }}>{Math.round(leaf.percent)}%</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function SkillsMap() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [onLeaves, setOnLeaves] = useState(() => new Set());
  const [activeHub, setActiveHub] = useState(null);
  const [view, setView] = useState("hexagono"); // 'hexagono' | 'lista'

  const load = () => {
    setLoading(true);
    setLoadError(null);
    api
      .get("/skills-map")
      .then((res) => setData(res.data))
      .catch((e) => setLoadError(errMsg(e, "Não foi possível carregar o mapa agora.")))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await api.post("/skills-map/generate");
      setData(res.data);
      toast.success("Mapa de habilidades atualizado.");
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível atualizar o mapa agora."));
    } finally {
      setGenerating(false);
    }
  };

  const toggleLeaf = (key) => {
    setOnLeaves((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const radarData = useMemo(() => {
    const hexagon = data?.hexagon;
    if (hexagon && hexagon.length) {
      return hexagon.map((h) => ({ label: h.label, value: Math.round(h.mastery * 100) }));
    }
    return (data?.hubs || []).map((h) => ({ label: h.label, value: 0 }));
  }, [data]);

  const activeHubData = useMemo(
    () => (activeHub != null ? (data?.hubs || []).find((h) => h.hub === activeHub) : null),
    [activeHub, data]
  );

  if (loading) {
    return (
      <div>
        <Nav />
        <div className="p-10 text-white/60">Compondo mapa...</div>
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div>
        <Nav />
        <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
          <div className="text-white/60" data-testid="sm-load-error">{loadError || "Não foi possível carregar o mapa agora."}</div>
          <button
            onClick={load}
            className="pill mt-4 text-sm font-medium btn-sapiens px-4 py-2 rounded-full"
            data-testid="sm-retry-btn"
          >
            Tentar de novo
          </button>
        </div>
      </div>
    );
  }

  const hasMap = Boolean(data?.hexagon);
  const balance = data?.sparks_balance ?? 0;
  const cost = data?.cost ?? 500;
  const canAfford = balance >= cost;
  const feedback = data?.feedback;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Mapa de habilidades</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="sm-title">
          Como você evolui.
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">
          Seis frentes amplas do seu raciocínio. Quanto mais afastado do centro, mais você já domina naquela frente.
        </p>

        <div className="mt-8 card-sapiens rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Saldo de Sparks</div>
            <div className="mt-2 font-display text-3xl font-bold tracking-tight flex items-center gap-2 text-zinc-950" data-testid="sm-sparks-balance">
              <Zap className="w-6 h-6 text-amber-500" fill="currentColor" />
              {balance}
            </div>
            {data?.updated_at && (
              <div className="mt-1 font-mono-alt text-[10px] text-zinc-400" data-testid="sm-updated-at">
                atualizado em {new Date(data.updated_at).toLocaleDateString("pt-BR")}
              </div>
            )}
          </div>
          <button
            onClick={generate}
            disabled={generating || !canAfford}
            className="pill btn-sapiens flex items-center gap-2 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2.5 rounded-full"
            data-testid="sm-generate-btn"
          >
            <RefreshCw className={"w-4 h-4 " + (generating ? "animate-spin" : "")} />
            {hasMap ? "Atualizar mapa" : "Gerar mapa"} · {cost} Sparks
          </button>
        </div>
        {!canAfford && (
          <div className="mt-2 text-xs text-red-400" data-testid="sm-insufficient-sparks">
            Saldo insuficiente para gerar o mapa ({balance} / {cost} Sparks).
          </div>
        )}

        <div className="mt-6 inline-flex items-center gap-1 rounded-full border border-white/15 p-1" data-testid="sm-view-toggle">
          <button
            onClick={() => setView("hexagono")}
            className={`pill inline-flex items-center gap-1.5 text-xs font-medium px-3.5 py-1.5 rounded-full ${view === "hexagono" ? "bg-white text-zinc-900" : "text-white/60 hover:text-white"}`}
            data-testid="sm-view-hexagono"
          >
            <HexagonIcon className="w-3.5 h-3.5" /> Hexágono
          </button>
          <button
            onClick={() => setView("lista")}
            className={`pill inline-flex items-center gap-1.5 text-xs font-medium px-3.5 py-1.5 rounded-full ${view === "lista" ? "bg-white text-zinc-900" : "text-white/60 hover:text-white"}`}
            data-testid="sm-view-lista"
          >
            <LayoutList className="w-3.5 h-3.5" /> Lista
          </button>
        </div>

        {view === "lista" ? (
          <div className="mt-4">
            <HierarchicalList hubs={data?.hubs} />
          </div>
        ) : (
        <div className="mt-4 card-sapiens rounded-2xl p-4 md:p-6" data-testid="sm-radar">
          <div style={{ width: "100%", height: 360 }}>
            <ResponsiveContainer>
              <RadarChart data={radarData} outerRadius="66%">
                <PolarGrid stroke="#e4e4e7" />
                <PolarAngleAxis
                  dataKey="label"
                  tick={<VertexTick hubs={data?.hubs} activeHub={activeHub} onSelect={setActiveHub} />}
                />
                <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                <Radar dataKey="value" stroke="#4A85E3" fill="#4A85E3" fillOpacity={0.15} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="text-center text-xs text-zinc-400 -mt-2">
            {hasMap ? "Toque em um ícone do hexágono para ver os itens daquela frente." : "Gere seu primeiro mapa para ver o hexágono preenchido."}
          </div>

          {activeHubData && (
            <div
              className="mt-4 reveal rounded-2xl p-5 md:p-6 border"
              style={{
                background: `linear-gradient(135deg, ${(HUB_COLOR[activeHubData.hub] || "#18181b")}14, transparent)`,
                borderColor: (HUB_COLOR[activeHubData.hub] || "#18181b") + "40",
              }}
              data-testid="sm-vertex-panel"
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-11 h-11 rounded-full flex items-center justify-center text-white shrink-0"
                  style={{ background: HUB_COLOR[activeHubData.hub] || "#18181b" }}
                >
                  {(() => { const Icon = HUB_ICON[activeHubData.hub] || Hash; return <Icon className="w-5 h-5" strokeWidth={1.8} />; })()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-display font-bold text-lg text-zinc-950">{activeHubData.label}</div>
                  <div className="text-xs font-mono-alt font-bold" style={{ color: HUB_COLOR[activeHubData.hub] }}>{activeHubData.mastery}% dominado</div>
                </div>
                <button
                  onClick={() => setActiveHub(null)}
                  className="text-zinc-400 hover:text-zinc-700 shrink-0"
                  data-testid="sm-vertex-panel-close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {(activeHubData.branches || []).flatMap((b) => b.leaves || []).map((leaf, i) => {
                  const color = HUB_COLOR[activeHubData.hub] || "#18181b";
                  return (
                    <span
                      key={i}
                      className="text-xs pl-3 pr-1.5 py-1.5 rounded-full border bg-white flex items-center gap-1.5"
                      style={{ borderColor: color + "55", color }}
                    >
                      {leaf.name}
                      <span className="font-mono-alt font-bold rounded-full px-1.5 py-0.5 text-[10px]" style={{ background: color + "1a", color }}>
                        {Math.round(leaf.percent)}%
                      </span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>
        )}

        {feedback && (
          <div className="mt-6 card-sapiens rounded-2xl p-5 md:p-6" data-testid="sm-feedback">
            <div className="font-display font-bold text-lg text-zinc-950" data-testid="sm-feedback-headline">
              {feedback.headline}
            </div>
            {(feedback.pontos_fortes?.length > 0 || feedback.pontos_fracos?.length > 0) && (
              <div className="mt-4 grid sm:grid-cols-2 gap-4">
                {feedback.pontos_fortes?.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-emerald-700 mb-2">
                      <TrendingUp className="w-3.5 h-3.5" /> Pontos fortes
                    </div>
                    <div className="space-y-1.5">
                      {feedback.pontos_fortes.map((p) => (
                        <div key={p.hub} className="flex items-center justify-between text-sm bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
                          <span className="text-zinc-700">{p.label}</span>
                          <span className="font-mono-alt font-bold text-emerald-700">{p.accuracy}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {feedback.pontos_fracos?.length > 0 && (
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-rose-700 mb-2">
                      <Target className="w-3.5 h-3.5" /> Pontos fracos
                    </div>
                    <div className="space-y-1.5">
                      {feedback.pontos_fracos.map((p) => (
                        <div key={p.hub} className="flex items-center justify-between text-sm bg-rose-50 border border-rose-100 rounded-lg px-3 py-2">
                          <span className="text-zinc-700">{p.label}</span>
                          <span className="font-mono-alt font-bold text-rose-700">{p.ocorrencias}×</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            <div className="mt-3 text-[11px] text-zinc-400" data-testid="sm-feedback-rounds">
              baseado em {feedback.rounds_analisadas} rodada(s) de 10 questões do seu histórico
            </div>
          </div>
        )}

        {feedback?.narrativa?.length > 0 && (
          <div className="mt-6 card-sapiens rounded-2xl p-5 md:p-6" data-testid="sm-narrativa">
            <div className="font-display font-bold text-lg text-zinc-950 mb-1">Seu histórico, questão por questão</div>
            <p className="text-xs text-zinc-400 mb-3">
              Resumo interativo montado a partir das suas rodadas de 10 questões — sem IA, só os seus números. Toque numa rodada para ver detalhes.
            </p>
            <div className="max-h-[420px] overflow-y-auto pr-1">
              {feedback.narrativa.map((item, i) => (
                <NarrativeRow key={i} item={item} index={i} />
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {(data?.hubs || []).map((hub) => (
            <HubTreeCard key={hub.hub} hub={hub} onLeaves={onLeaves} toggleLeaf={toggleLeaf} />
          ))}
        </div>
      </div>
    </div>
  );
}
