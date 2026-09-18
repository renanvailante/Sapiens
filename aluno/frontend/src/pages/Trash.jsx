import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import EstadoDeErro from "../components/EstadoDeErro";
import { toast } from "sonner";
import { RotateCcw, Trash2, AlertTriangle } from "lucide-react";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "../components/ui/alert-dialog";

export default function Trash() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const nav = useNavigate();

  const load = () => {
    setLoading(true);
    setErro(null);
    api.get("/analyses", { params: { trash: true } })
      .then(({ data }) => setItems(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível carregar a lixeira.")))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const restore = async (a) => {
    try {
      await api.post(`/analyses/${a.analysis_id}/restore`);
      toast.success("Tentativa restaurada ao histórico.");
      load();
    } catch (e) { toast.error("Não foi possível restaurar."); }
  };
  const permanentDelete = async () => {
    try {
      await api.delete(`/analyses/${confirm.analysis_id}`);
      toast.success("Removida permanentemente.");
      setConfirm(null);
      load();
    } catch (e) { toast.error("Não foi possível excluir."); }
  };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="secao-olho">Lixeira</div>
        <h1 className="titulo-tela" data-testid="trash-title">
          Tentativas descartadas.
        </h1>
        <p className="mt-3 text-white/60 max-w-lg">Aqui ficam as análises que você removeu do histórico. Você pode restaurá-las a qualquer momento — ou excluí-las para sempre.</p>

        <div className="mt-10 space-y-3">
          {loading && <div className="text-white/60">Carregando...</div>}
          {!loading && erro && <EstadoDeErro mensagem={erro} aoTentarNovamente={load} voltarPara="/history" voltarLabel="Voltar ao histórico" />}
          {!loading && !erro && items.length === 0 && (
            <div className="card-sapiens rounded-2xl p-10 text-center">
              <div className="font-display text-2xl font-bold text-zinc-950">Lixeira vazia.</div>
              <p className="mt-2 text-zinc-500">Nada aqui — bem organizado.</p>
              <button onClick={() => nav("/history")} className="pill mt-6 btn-sapiens px-5 py-2.5 rounded-full text-sm font-medium" data-testid="trash-empty-back">
                Voltar ao histórico
              </button>
            </div>
          )}
          {!erro && items.map(a => (
            <div key={a.analysis_id} className="card-sapiens rounded-2xl p-5 md:p-6" data-testid={`trash-item-${a.analysis_id}`}>
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="font-display font-bold text-lg tracking-tight text-zinc-950">
                    {a.label || a.exam_label}
                  </div>
                  <div className="text-sm text-zinc-500 mt-1">
                    Feita em {new Date(a.created_at).toLocaleString("pt-BR")}
                    {a.deleted_at && <> · descartada em {new Date(a.deleted_at).toLocaleString("pt-BR")}</>}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-display font-extrabold text-2xl tracking-tighter text-zinc-400">
                    {a.score}<span className="text-zinc-200">/{a.total}</span>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <button onClick={() => restore(a)}
                  className="pill inline-flex items-center gap-2 border border-zinc-200 hover:bg-zinc-50 px-4 py-2 rounded-full text-sm font-medium text-zinc-900"
                  data-testid={`trash-restore-${a.analysis_id}`}>
                  <RotateCcw className="w-4 h-4" /> Restaurar
                </button>
                <button onClick={() => setConfirm(a)}
                  className="pill inline-flex items-center gap-2 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 px-4 py-2 rounded-full text-sm font-medium"
                  data-testid={`trash-delete-${a.analysis_id}`}>
                  <Trash2 className="w-4 h-4" /> Excluir permanentemente
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <AlertDialog open={!!confirm} onOpenChange={(v) => !v && setConfirm(null)}>
        <AlertDialogContent className="rounded-2xl">
          <AlertDialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-rose-50 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
              </div>
              <AlertDialogTitle className="font-display text-2xl tracking-tight">Excluir permanentemente?</AlertDialogTitle>
            </div>
            <AlertDialogDescription className="pt-2 text-zinc-600">
              Esta ação é irreversível. Todos os dados desta tentativa — respostas, diagnóstico, plano e mapa — serão removidos para sempre.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="delete-cancel" className="rounded-full">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={permanentDelete} data-testid="delete-confirm"
              className="rounded-full bg-rose-600 hover:bg-rose-700">
              Excluir para sempre
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
