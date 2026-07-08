import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";
import { ArrowRight, MoreVertical, Eye, Pencil, Trash2 } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from "../components/ui/dropdown-menu";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";

export default function History() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [renameTarget, setRenameTarget] = useState(null);
  const [newLabel, setNewLabel] = useState("");
  const nav = useNavigate();

  const load = () => {
    setLoading(true);
    api.get("/analyses").then(({ data }) => { setItems(data); setLoading(false); });
  };
  useEffect(() => { load(); }, []);

  const openRename = (a) => { setRenameTarget(a); setNewLabel(a.label || a.exam_label); };
  const doRename = async () => {
    try {
      await api.patch(`/analyses/${renameTarget.analysis_id}/rename`, { label: newLabel });
      toast.success("Tentativa renomeada.");
      setRenameTarget(null);
      load();
    } catch (e) { toast.error("Não foi possível renomear."); }
  };
  const trash = async (a) => {
    try {
      await api.post(`/analyses/${a.analysis_id}/trash`);
      toast.success("Movido para a lixeira.");
      load();
    } catch (e) { toast.error("Não foi possível mover."); }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-zinc-500 mb-3">Histórico</div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-zinc-950" data-testid="history-title">
              Sua trajetória.
            </h1>
            <p className="mt-3 text-zinc-500 max-w-lg">Cada tentativa é armazenada individualmente. Refazer uma prova nunca sobrescreve a análise anterior.</p>
          </div>
          <Link to="/trash" className="pill inline-flex items-center gap-2 border border-zinc-200 hover:bg-zinc-50 text-zinc-900 px-4 py-2 rounded-full text-sm font-medium" data-testid="history-trash-link">
            <Trash2 className="w-4 h-4" /> Lixeira
          </Link>
        </div>

        <div className="mt-10 space-y-3">
          {loading && <div className="text-zinc-500">Carregando...</div>}
          {!loading && items.length === 0 && (
            <div className="bg-white border border-zinc-200 rounded-2xl p-10 text-center">
              <div className="font-display text-2xl font-bold text-zinc-950">Sem tentativas ainda.</div>
              <p className="mt-2 text-zinc-500">Analise sua primeira prova para começar seu histórico.</p>
              <button onClick={() => nav("/exams")} className="pill mt-6 bg-zinc-950 hover:bg-zinc-800 text-white px-6 py-3 rounded-full text-sm font-medium" data-testid="history-empty-cta">
                Analisar uma prova
              </button>
            </div>
          )}
          {items.map(a => (
            <div key={a.analysis_id} className="lift bg-white border border-zinc-200 rounded-2xl p-5 md:p-6" data-testid={`history-item-${a.analysis_id}`}>
              <div className="flex items-center justify-between gap-4">
                <button onClick={() => nav(`/analysis/${a.analysis_id}`)} className="flex-1 text-left">
                  <div className="font-display font-bold text-lg tracking-tight text-zinc-950">
                    {a.label || a.exam_label}
                  </div>
                  <div className="text-sm text-zinc-500 mt-1">{new Date(a.created_at).toLocaleString("pt-BR")}</div>
                </button>
                <div className="text-right">
                  <div className="font-display font-extrabold text-2xl tracking-tighter text-zinc-950">
                    {a.score}<span className="text-zinc-300">/{a.total}</span>
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">{a.percent}%</div>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="p-2 rounded-full hover:bg-zinc-100" data-testid={`history-menu-${a.analysis_id}`}>
                      <MoreVertical className="w-5 h-5 text-zinc-500" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="rounded-xl">
                    <DropdownMenuItem onClick={() => nav(`/analysis/${a.analysis_id}`)} data-testid={`history-view-${a.analysis_id}`}>
                      <Eye className="w-4 h-4 mr-2" /> Ver análise
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => openRename(a)} data-testid={`history-rename-${a.analysis_id}`}>
                      <Pencil className="w-4 h-4 mr-2" /> Renomear
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => trash(a)} className="text-rose-600 focus:text-rose-700" data-testid={`history-trash-${a.analysis_id}`}>
                      <Trash2 className="w-4 h-4 mr-2" /> Mover para lixeira
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <div className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
                Abrir <ArrowRight className="w-3 h-3" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <Dialog open={!!renameTarget} onOpenChange={(v) => !v && setRenameTarget(null)}>
        <DialogContent className="rounded-2xl">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Renomear tentativa</DialogTitle>
          </DialogHeader>
          <input value={newLabel} onChange={e => setNewLabel(e.target.value)}
            className="mt-2 w-full border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:border-zinc-900 outline-none"
            placeholder="Ex.: Simulado antes da matrícula"
            data-testid="rename-input" />
          <DialogFooter className="mt-4">
            <button onClick={() => setRenameTarget(null)} className="pill px-4 py-2 rounded-full text-sm font-medium border border-zinc-200 hover:bg-zinc-50" data-testid="rename-cancel">Cancelar</button>
            <button onClick={doRename} className="pill px-4 py-2 rounded-full text-sm font-medium bg-zinc-950 hover:bg-zinc-800 text-white" data-testid="rename-save">Salvar</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
