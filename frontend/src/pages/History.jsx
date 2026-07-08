import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight } from "lucide-react";

export default function History() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/analyses").then(({ data }) => setItems(data)); }, []);
  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Histórico</div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="history-title">
          Sua trajetória.
        </h1>
        <div className="mt-10 space-y-3">
          {items.length === 0 && <div className="text-zinc-500">Sem análises ainda.</div>}
          {items.map(a => (
            <Link key={a.analysis_id} to={`/analysis/${a.analysis_id}`} className="lift block bg-white border border-zinc-200 rounded-2xl p-6" data-testid={`history-item-${a.analysis_id}`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-display font-bold text-lg tracking-tight text-zinc-950">{a.exam_label}</div>
                  <div className="text-sm text-zinc-500 mt-1">{new Date(a.created_at).toLocaleString("pt-BR")}</div>
                </div>
                <div className="text-right">
                  <div className="font-display font-extrabold text-2xl tracking-tighter text-zinc-950">{a.score}<span className="text-zinc-300">/{a.total}</span></div>
                  <div className="text-xs text-zinc-500 mt-1 inline-flex items-center gap-1">Abrir <ArrowRight className="w-3 h-3" /></div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
