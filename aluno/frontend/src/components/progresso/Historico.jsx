import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowRight, MoreVertical, Eye, Pencil, Trash2, TrendingUp, TrendingDown,
  RotateCcw, AlertTriangle, Loader2,
} from "lucide-react";
import { api, errMsg } from "../../lib/api";
import EstadoDeErro from "../EstadoDeErro";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from "../ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "../ui/alert-dialog";
import { ROTAS } from "../../lib/rotas";

/**
 * O HISTÓRICO — e a lixeira como FILTRO dele, não como outra tela.
 *
 * `/history` e `/trash` eram duas rotas para a mesma lista, com dois
 * cabeçalhos, dois carregamentos e um link de ida e volta entre elas. O Menu
 * já as anunciava numa linha só ("Tudo o que você já resolveu — e a lixeira do
 * que apagou"), o que é a admissão de que são a mesma coisa: **a segunda é a
 * primeira com `?trash=true`**, literalmente, no mesmo endpoint.
 *
 * Aqui é um alternador de duas posições. A lixeira deixa de ser um lugar aonde
 * se vai e vira o que ela sempre foi: um estado das mesmas tentativas.
 *
 * `?apagados=1` na URL abre direto nos descartados — é para onde `/trash`
 * redireciona, e é o que mantém vivo o link antigo.
 *
 * ---------------------------------------------------------------------------
 * O QUE ESTA LISTA GUARDA, E POR QUE ELA CONTINUA EXISTINDO
 * ---------------------------------------------------------------------------
 *
 * Cada linha é um simulado corrigido pelo fluxo antigo de gabarito, com o
 * diagnóstico (`/analysis/:id`) e o plano (`/plan/:id`) que saíram dele. Esse
 * fluxo é um snapshot: não reage ao que o aluno demonstrou ontem e não tem
 * noção de tempo — quem faz isso hoje é a fila de revisão, dentro da Agenda.
 *
 * Mas ele é **o registro do próprio aluno**, e apagar o passado de alguém para
 * limpar a arquitetura é a troca errada. Ele sai da navegação e vira uma seção
 * do Progresso, que é onde a pergunta "o que eu já fiz" é feita.
 */

function Vazio({ apagados, aoVoltar }) {
  const nav = useNavigate();
  return (
    <div className="card-sapiens rounded-2xl p-10 text-center">
      <div className="font-display text-2xl font-bold text-zinc-950">
        {apagados ? "Lixeira vazia." : "Sem tentativas ainda."}
      </div>
      <p className="mt-2 text-zinc-500">
        {apagados
          ? "Nada aqui — bem organizado."
          : "Corrija o seu primeiro simulado para começar o histórico."}
      </p>
      <button
        onClick={() => (apagados ? aoVoltar() : nav(ROTAS.PROVAS))}
        className="pill btn-sapiens mt-6 rounded-full px-5 py-2.5 text-sm font-medium"
        data-testid={apagados ? "historico-vazio-voltar" : "historico-vazio-praticar"}
      >
        {apagados ? "Ver o histórico" : "Escolher um caderno"}
      </button>
    </div>
  );
}

export default function Historico() {
  const [params, setParams] = useSearchParams();
  const apagados = params.get("apagados") === "1";

  const [items, setItems] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [renomeando, setRenomeando] = useState(null);
  const [rotulo, setRotulo] = useState("");
  const [confirmar, setConfirmar] = useState(null);
  const nav = useNavigate();

  // Sem o `.catch`, uma falha de rede deixava a lista em "Carregando..." para
  // sempre — sem mensagem e sem saída.
  const carregar = useCallback(() => {
    setCarregando(true);
    setErro(null);
    api
      .get("/analyses", apagados ? { params: { trash: true } } : undefined)
      .then(({ data }) => setItems(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível carregar o seu histórico.")))
      .finally(() => setCarregando(false));
  }, [apagados]);

  useEffect(carregar, [carregar]);

  const alternar = (paraApagados) => {
    const novo = new URLSearchParams(params);
    if (paraApagados) novo.set("apagados", "1");
    else novo.delete("apagados");
    // `replace`: alternar um filtro não é navegar. Sem isso, três toques no
    // alternador enchem o histórico do navegador e o botão "voltar" do
    // aparelho deixa de sair da aba.
    setParams(novo, { replace: true });
  };

  // `items` vem mais recente primeiro. Para cada tentativa, compara com a
  // ANTERIOR do mesmo exame — é o que faz um simulado refeito ser uma
  // experiência contínua e não um evento isolado.
  const delta = (a) => {
    const anteriores = items.filter((x) => x.exam_label === a.exam_label && x.created_at < a.created_at);
    if (!anteriores.length) return null;
    const ultima = anteriores.reduce((m, x) => (x.created_at > m.created_at ? x : m));
    return a.percent - ultima.percent;
  };

  const renomear = async () => {
    try {
      await api.patch(`/analyses/${renomeando.analysis_id}/rename`, { label: rotulo });
      toast.success("Tentativa renomeada.");
      setRenomeando(null);
      carregar();
    } catch {
      toast.error("Não foi possível renomear.");
    }
  };

  const descartar = async (a) => {
    try {
      await api.post(`/analyses/${a.analysis_id}/trash`);
      toast.success("Movida para os apagados.");
      carregar();
    } catch {
      toast.error("Não foi possível mover.");
    }
  };

  const restaurar = async (a) => {
    try {
      await api.post(`/analyses/${a.analysis_id}/restore`);
      toast.success("Tentativa restaurada ao histórico.");
      carregar();
    } catch {
      toast.error("Não foi possível restaurar.");
    }
  };

  const excluir = async () => {
    try {
      await api.delete(`/analyses/${confirmar.analysis_id}`);
      toast.success("Removida permanentemente.");
      setConfirmar(null);
      carregar();
    } catch {
      toast.error("Não foi possível excluir.");
    }
  };

  return (
    <div>
      {/* O alternador. Duas posições, e a segunda é a primeira com um filtro —
          por isso ele é um seletor, e não um link para outra tela. */}
      <div
        className="inline-flex rounded-full border border-white/12 bg-white/5 p-1"
        role="tablist"
        data-testid="historico-filtro"
      >
        {[
          { id: false, rotulo: "Minhas tentativas" },
          { id: true, rotulo: "Apagadas" },
        ].map((op) => (
          <button
            key={String(op.id)}
            type="button"
            role="tab"
            aria-selected={apagados === op.id}
            onClick={() => alternar(op.id)}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-colors ${
              apagados === op.id ? "bg-white/12 text-white" : "text-white/50 hover:text-white/80"
            }`}
            data-testid={`historico-filtro-${op.id ? "apagadas" : "ativas"}`}
          >
            {op.rotulo}
          </button>
        ))}
      </div>

      <div className="mt-5 space-y-3">
        {carregando && (
          <div className="flex items-center gap-2 text-sm text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando…
          </div>
        )}
        {!carregando && erro && <EstadoDeErro mensagem={erro} aoTentarNovamente={carregar} />}
        {!carregando && !erro && items.length === 0 && (
          <Vazio apagados={apagados} aoVoltar={() => alternar(false)} />
        )}

        {!erro && items.map((a) => (
          <div
            key={a.analysis_id}
            className={`card-sapiens rounded-2xl p-5 md:p-6 ${apagados ? "" : "lift"}`}
            data-testid={`historico-item-${a.analysis_id}`}
          >
            <div className="flex items-center justify-between gap-4">
              {apagados ? (
                <div className="min-w-0 flex-1">
                  <div className="font-display text-lg font-bold tracking-tight text-zinc-950">
                    {a.label || a.exam_label}
                  </div>
                  <div className="mt-1 text-sm text-zinc-500">
                    Feita em {new Date(a.created_at).toLocaleString("pt-BR")}
                    {a.deleted_at && <> · descartada em {new Date(a.deleted_at).toLocaleString("pt-BR")}</>}
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => nav(`${ROTAS.ANALISE.replace(":analysisId", a.analysis_id)}`)}
                  className="min-w-0 flex-1 text-left"
                >
                  <div className="font-display text-lg font-bold tracking-tight text-zinc-950">
                    {a.label || a.exam_label}
                  </div>
                  <div className="mt-1 text-sm text-zinc-500">
                    {new Date(a.created_at).toLocaleString("pt-BR")}
                  </div>
                </button>
              )}

              <div className="text-right">
                <div
                  className={`font-display text-2xl font-extrabold tracking-tighter ${
                    apagados ? "text-zinc-400" : "text-zinc-950"
                  }`}
                >
                  {a.score}
                  <span className={apagados ? "text-zinc-200" : "text-zinc-300"}>/{a.total}</span>
                </div>
                {!apagados && (
                  <div className="mt-1 flex items-center justify-end gap-1.5">
                    <span className="text-xs text-zinc-500">{a.percent}%</span>
                    {(() => {
                      const d = delta(a);
                      if (d == null || d === 0) return null;
                      const subiu = d > 0;
                      return (
                        <span
                          className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-mono-alt text-[10px] font-bold ${
                            subiu ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
                          }`}
                          data-testid={`historico-delta-${a.analysis_id}`}
                        >
                          {subiu ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
                          {subiu ? "+" : ""}{d}
                        </span>
                      );
                    })()}
                  </div>
                )}
              </div>

              {!apagados && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      className="rounded-full p-2 hover:bg-zinc-100"
                      data-testid={`historico-menu-${a.analysis_id}`}
                      aria-label="Ações da tentativa"
                    >
                      <MoreVertical className="h-5 w-5 text-zinc-500" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="rounded-xl">
                    <DropdownMenuItem onClick={() => nav(`${ROTAS.ANALISE.replace(":analysisId", a.analysis_id)}`)}>
                      <Eye className="mr-2 h-4 w-4" /> Ver diagnóstico
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setRenomeando(a); setRotulo(a.label || a.exam_label); }}>
                      <Pencil className="mr-2 h-4 w-4" /> Renomear
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => descartar(a)}
                      className="text-rose-600 focus:text-rose-700"
                      data-testid={`historico-descartar-${a.analysis_id}`}
                    >
                      <Trash2 className="mr-2 h-4 w-4" /> Apagar
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>

            {apagados ? (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <button
                  onClick={() => restaurar(a)}
                  className="pill inline-flex items-center gap-2 rounded-full border border-zinc-200 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
                  data-testid={`historico-restaurar-${a.analysis_id}`}
                >
                  <RotateCcw className="h-4 w-4" /> Restaurar
                </button>
                <button
                  onClick={() => setConfirmar(a)}
                  className="pill inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-100"
                  data-testid={`historico-excluir-${a.analysis_id}`}
                >
                  <Trash2 className="h-4 w-4" /> Excluir permanentemente
                </button>
              </div>
            ) : (
              <div className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
                Abrir <ArrowRight className="h-3 w-3" />
              </div>
            )}
          </div>
        ))}
      </div>

      <Dialog open={Boolean(renomeando)} onOpenChange={(v) => !v && setRenomeando(null)}>
        <DialogContent className="rounded-2xl">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Renomear tentativa</DialogTitle>
          </DialogHeader>
          <input
            autoFocus
            value={rotulo}
            onChange={(e) => setRotulo(e.target.value)}
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none"
            data-testid="historico-renomear-campo"
          />
          <DialogFooter>
            <button
              onClick={() => setRenomeando(null)}
              className="pill rounded-full border border-zinc-200 px-5 py-2.5 text-sm font-medium text-zinc-700"
            >
              Cancelar
            </button>
            <button
              onClick={renomear}
              disabled={!rotulo.trim()}
              className="pill btn-sapiens rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
              data-testid="historico-renomear-salvar"
            >
              Salvar
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(confirmar)} onOpenChange={(v) => !v && setConfirmar(null)}>
        <AlertDialogContent className="rounded-2xl">
          <AlertDialogHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-rose-50">
                <AlertTriangle className="h-5 w-5 text-rose-600" />
              </div>
              <AlertDialogTitle className="font-display text-2xl tracking-tight">
                Excluir permanentemente?
              </AlertDialogTitle>
            </div>
            <AlertDialogDescription className="pt-2 text-zinc-600">
              Esta ação é irreversível. Todos os dados desta tentativa — respostas, diagnóstico e
              plano — serão removidos para sempre.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="historico-excluir-cancelar" className="rounded-full">
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={excluir}
              data-testid="historico-excluir-confirmar"
              className="rounded-full bg-rose-600 hover:bg-rose-700"
            >
              Excluir para sempre
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
