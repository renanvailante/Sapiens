import { useEffect, useState } from "react";
import { Bell, BellOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ModalInstalar, useInstalacao } from "./InstalarApp";
import {
  desligarNotificacoes, devePerguntar, inscricaoAtual, jaPerguntado, ligarNotificacoes, marcarPerguntado, medirAparelho,
} from "../lib/push";

/** A pergunta é a do dono do produto, palavra por palavra. */
export const PERGUNTA = "Quer que eu te avise quando seus trechos voltarem e quando sua sequência estiver em risco?";

const NOTA_IPHONE =
  "No iPhone, o aviso só chega com o Sapiens instalado na tela de início (iOS 16.4 ou mais novo). Instale, abra pelo ícone e ligue aqui de novo.";

/**
 * O PEDIDO — no fechamento de série, uma vez.
 *
 * Fica dentro do cartão do fechamento, abaixo da recompensa: é o momento em
 * que o aluno acabou de ver o que fez, e a pergunta fala de coisas que ele
 * conhece. Some para sempre depois de qualquer resposta (ver `lib/push.js`).
 */
export function PedidoDeNotificacao({ respondeuNaSerie }) {
  const { plataforma, instalado } = useInstalacao();
  const [visivel, setVisivel] = useState(false);
  const [situacao, setSituacao] = useState(null);
  const [ligando, setLigando] = useState(false);
  const [instalar, setInstalar] = useState(false);

  useEffect(() => {
    let ativo = true;
    const aparelho = medirAparelho(plataforma, instalado);
    inscricaoAtual().then((inscricao) => {
      if (!ativo) return;
      setSituacao(aparelho.situacao);
      setVisivel(devePerguntar({
        situacao: aparelho.situacao, jaPerguntado: jaPerguntado(), inscrito: Boolean(inscricao), respondeuNaSerie,
      }));
    });
    return () => { ativo = false; };
  }, [plataforma, instalado, respondeuNaSerie]);

  if (!visivel) return null;

  const dispensar = () => { marcarPerguntado(); setVisivel(false); };
  const ligar = async () => {
    if (situacao === "precisa_instalar") { setInstalar(true); return; }
    setLigando(true);
    try {
      const r = await ligarNotificacoes();
      if (r === "ativo") toast.success("Combinado. Um aviso por dia no máximo, e só quando houver motivo.");
      else toast("Tudo bem. Dá para ligar depois pelo Menu.");
      setVisivel(false);
    } catch (e) {
      toast.error(e?.message || "Não foi possível ligar as notificações agora.");
    } finally {
      setLigando(false);
    }
  };

  return (
    <div className="mt-5 rounded-xl border border-zinc-200 bg-zinc-50 p-4 cascata" data-testid="pedido-notificacao">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sapiens-accentSoft text-sapiens-navy">
          <Bell className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold leading-snug text-zinc-900">{PERGUNTA}</p>
          <p className="mt-1 text-xs leading-relaxed text-zinc-500">
            {situacao === "precisa_instalar"
              ? NOTA_IPHONE
              : "No máximo um aviso por dia, entre 8h e 21h, e só com algo seu para fazer. Desliga a qualquer hora pelo Menu."}
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <button
              onClick={ligar}
              disabled={ligando}
              className="pill btn-sapiens inline-flex w-full items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold disabled:opacity-60 sm:w-auto"
              data-testid="pedido-notificacao-sim"
            >
              {ligando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bell className="h-3.5 w-3.5" />}
              {situacao === "precisa_instalar" ? "Ver como instalar" : "Quero ser avisado"}
            </button>
            <button
              onClick={dispensar}
              className="pill inline-flex w-full items-center justify-center rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-zinc-600 sm:w-auto"
              data-testid="pedido-notificacao-nao"
            >
              Agora não
            </button>
          </div>
        </div>
      </div>
      <ModalInstalar aberto={instalar} aoFechar={() => { setInstalar(false); dispensar(); }} />
    </div>
  );
}

/**
 * O INTERRUPTOR do Menu — ligar e desligar a qualquer hora, sem depender de
 * ter visto o pedido. Lê o estado real do aparelho a cada abertura (a
 * permissão pode ter sido revogada nas configurações do celular).
 */
export function InterruptorDeNotificacao({ className = "" }) {
  const { plataforma, instalado } = useInstalacao();
  const [estado, setEstado] = useState({ carregando: true, inscrito: false, situacao: null });
  const [ocupado, setOcupado] = useState(false);
  const [instalar, setInstalar] = useState(false);

  useEffect(() => {
    let ativo = true;
    const aparelho = medirAparelho(plataforma, instalado);
    inscricaoAtual().then((inscricao) => {
      if (ativo) setEstado({ carregando: false, inscrito: Boolean(inscricao), situacao: aparelho.situacao });
    });
    return () => { ativo = false; };
  }, [plataforma, instalado]);

  if (estado.situacao === "indisponivel") return null;

  const alternar = async () => {
    if (ocupado || estado.carregando) return;
    if (estado.situacao === "precisa_instalar") { setInstalar(true); return; }
    if (estado.situacao === "bloqueado") {
      toast("As notificações estão bloqueadas neste navegador. Libere em Configurações › Notificações e ligue aqui de novo.");
      return;
    }
    setOcupado(true);
    try {
      if (estado.inscrito) {
        await desligarNotificacoes();
        setEstado((e) => ({ ...e, inscrito: false }));
        toast("Notificações desligadas neste aparelho.");
      } else {
        const r = await ligarNotificacoes();
        setEstado((e) => ({ ...e, inscrito: r === "ativo", situacao: r === "recusado" ? "bloqueado" : e.situacao }));
        if (r === "ativo") toast.success("Notificações ligadas neste aparelho.");
      }
    } catch (e) {
      toast.error(e?.message || "Não foi possível mudar as notificações agora.");
    } finally {
      setOcupado(false);
    }
  };

  const ligado = estado.inscrito;
  const Icone = ligado ? Bell : BellOff;
  return (
    <>
      <button
        type="button"
        role="switch"
        aria-checked={ligado}
        onClick={alternar}
        className={className}
        data-testid="menu-notificacoes"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center text-white/45 group-hover:text-white/75">
          {ocupado ? <Loader2 className="h-[18px] w-[18px] animate-spin" /> : <Icone className="h-[18px] w-[18px]" strokeWidth={1.9} />}
        </span>
        <span className="min-w-0 flex-1 truncate">Notificações</span>
        <span
          className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${ligado ? "bg-[#4FD9FF]/80" : "bg-white/15"}`}
          aria-hidden="true"
        >
          <span
            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform duration-200 ${ligado ? "translate-x-4" : "translate-x-0.5"}`}
          />
        </span>
      </button>
      <ModalInstalar aberto={instalar} aoFechar={() => setInstalar(false)} />
    </>
  );
}
