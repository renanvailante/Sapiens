import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";

export default function LearningMap() {
  const { analysisId } = useParams();
  const [a, setA] = useState(null);
  const [selected, setSelected] = useState(null);
  useEffect(() => { api.get(`/analyses/${analysisId}`).then(({ data }) => setA(data)); }, [analysisId]);

  const { nodes, edges } = useMemo(() => {
    const lm = a?.learning_map || { nodes: [], edges: [] };
    return { nodes: lm.nodes || [], edges: lm.edges || [] };
  }, [a]);

  // Simple radial layout so we don't need heavy libs.
  const positioned = useMemo(() => {
    if (!nodes.length) return [];
    const cx = 300, cy = 240, r = 170;
    return nodes.map((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
      return { ...n, x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });
  }, [nodes]);

  const nodeById = Object.fromEntries(positioned.map(n => [n.id, n]));

  if (!a) return <div><Nav /><div className="p-10 text-zinc-500">Carregando mapa...</div></div>;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-4">Mapa de aprendizagem</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="map-title">
          A causa-raiz por trás do erro.
        </h1>
        <p className="mt-3 text-zinc-500 max-w-lg">Você errou no sintoma. Estude aqui a raiz. Nós conectamos o problema à cadeia de pré-requisitos.</p>

        {positioned.length === 0 ? (
          <div className="mt-10 text-zinc-500">Mapa em construção.</div>
        ) : (
          <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 bg-white border border-zinc-200 rounded-2xl p-4">
              <svg viewBox="0 0 600 480" className="w-full h-[480px]" data-testid="map-svg">
                <defs>
                  <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#a1a1aa" />
                  </marker>
                </defs>
                {edges.map((e, i) => {
                  const s = nodeById[e.source], t = nodeById[e.target];
                  if (!s || !t) return null;
                  return <line key={i} x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#e4e4e7" strokeWidth={1.5} markerEnd="url(#arrow)" />;
                })}
                {positioned.map((n) => {
                  const m = Math.max(0, Math.min(100, Number(n.mastery ?? 50)));
                  const color = m >= 65 ? "#10b981" : m >= 40 ? "#f59e0b" : "#f43f5e";
                  const active = selected?.id === n.id;
                  return (
                    <g key={n.id} onClick={() => setSelected(n)} className="cursor-pointer" data-testid={`map-node-${n.id}`}>
                      <circle cx={n.x} cy={n.y} r={active ? 26 : 22} fill="white" stroke={color} strokeWidth={active ? 3 : 2} />
                      <text x={n.x} y={n.y + 4} textAnchor="middle" fontSize={10} fontWeight={700} fill="#09090b">{Math.round(m)}</text>
                      <text x={n.x} y={n.y + 42} textAnchor="middle" fontSize={11} fill="#52525b">{n.label}</text>
                    </g>
                  );
                })}
              </svg>
            </div>
            <div className="bg-white border border-zinc-200 rounded-2xl p-6">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500 mb-3">Nó selecionado</div>
              {selected ? (
                <div>
                  <div className="font-display font-bold text-xl text-zinc-950 tracking-tight">{selected.label}</div>
                  <div className="mt-2 text-sm text-zinc-500">Domínio estimado: {Math.round(selected.mastery ?? 0)}%</div>
                  <div className="mt-4 text-sm text-zinc-600 leading-relaxed">
                    {edges.filter(e => e.target === selected.id).map((e, i) => (
                      <div key={i} className="mb-2">← Depende de <span className="font-medium text-zinc-900">{nodeById[e.source]?.label}</span> — {e.reason}</div>
                    ))}
                    {edges.filter(e => e.source === selected.id).map((e, i) => (
                      <div key={i} className="mb-2">→ Habilita <span className="font-medium text-zinc-900">{nodeById[e.target]?.label}</span></div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-zinc-500">Toque em um nó para explorar suas dependências e causas-raiz.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
