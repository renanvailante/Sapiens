import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { createPortal } from "react-dom";
import { toast } from "sonner";
import { BookmarkPlus, Check, Loader2, Zap } from "lucide-react";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useContextoMentisAtual } from "../lib/mentisContexto";
import { avisarSparksMudou } from "./Nav";
import {
  avisarLembretesMudou,
  dentroDeCampo,
  lembravelMaisProximo,
  montarPayload,
  normalizar,
  pontoGrosso,
  posicionarBotao,
  resumir,
  retanguloDaSelecao,
  rotaAceitaCaptura,
  textoSuficiente,
} from "../lib/lembretes";

/**
 * "Lembrar-me com a Mentis" — a camada de captura, montada UMA vez.
 *
 * O aluno seleciona qualquer trecho em qualquer tela do app e aparece um botão
 * flutuante que guarda aquilo na fila de Revisões por 10 Sparks. É o mesmo
 * gesto no desktop (soltar o mouse) e no celular (seleção por toque), e existe
 * também para OBJETOS que não são texto: qualquer elemento com `data-lembrar`
 * responde a clique-direito ou toque longo.
 *
 * **Por que aqui e não em cada página.** Este componente mora ao lado do
 * `MentisWidget` e da `BarraInferior` em `App.js`, pela mesma razão que eles:
 * o produto tem quase quarenta telas, e uma funcionalidade "de todo lugar"
 * implementada tela a tela é uma funcionalidade que a próxima tela nova não
 * vai ter. Ele escuta o `document` inteiro; nenhuma página precisa saber que
 * ele existe.
 *
 * **O que uma página PODE fazer, se quiser.** Marcar um objeto com
 * `data-lembrar="descrição do objeto"` (e, opcionalmente,
 * `data-lembrar-ref="curso:estacao-3"`) habilita o gesto sobre algo que não é
 * texto selecionável. É opcional por desenho: sem nenhum atributo em lugar
 * nenhum, a seleção de texto já cobre o produto inteiro.
 *
 * **O preço fica ESCRITO no botão**, e é a única proteção contra o toque
 * errado — remover da fila depois é de graça, mas não devolve Sparks (ver
 * `lembretes_routes.remover`). Um trecho já guardado mostra "Já está na sua
 * fila" em vez de um preço: o servidor não cobraria de novo, e um botão que
 * anuncia 10 Sparks para não cobrar nada mente sobre o próprio preço.
 */

const CUSTO_PADRAO = 10;
// Medido no navegador: o rótulo inteiro pede 162px, e com o ícone, o selo de
// preço e os respiros o botão fecha em 272. Com 230 o próprio nome da
// funcionalidade saía truncado ("Lembrar-me com a…") — um botão que corta o
// que ele faz, justamente onde precisa convencer alguém a gastar 10 Sparks.
// Cabe com folga nos 375px de um iPhone SE (272 + 2 × 12 de margem).
const LARGURA = 272;
// 40px de alvo de toque — acima do piso de ~32px da casa
// (`project_aluno_mobile_invariantes`, invariante 3).
const ALTURA = 40;
const ESPERA_SELECAO = 180;

export default function LembrarComAMentis() {
  const { user, loading } = useAuth() || {};
  const location = useLocation();
  const contextoTela = useContextoMentisAtual();

  const [alvo, setAlvo] = useState(null); // { texto, tipo, ref, rect }
  const [pos, setPos] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [guardados, setGuardados] = useState(() => new Set());

  const emVoo = useRef(false);
  const timer = useRef(null);
  const toqueLongo = useRef(null);
  const ativo = rotaAceitaCaptura(location.pathname) && !loading && !!user;

  const fechar = useCallback(() => {
    setAlvo(null);
    setPos(null);
  }, []);

  /** Mede a seleção atual e decide se há botão a mostrar. `toque` muda o lado
   *  em que ele nasce — ver `posicionarBotao`. */
  const avaliarSelecao = useCallback((toque) => {
    const sel = window.getSelection?.();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return fechar();
    const texto = sel.toString();
    if (!textoSuficiente(texto)) return fechar();
    const range = sel.getRangeAt(0);
    if (dentroDeCampo(range.commonAncestorContainer)) return fechar();

    const rect = retanguloDaSelecao(range);
    if (!rect.width && !rect.height) return fechar();
    setAlvo({ texto, tipo: "texto", ref: "", rect });
    setPos(
      posicionarBotao(rect, {
        vw: window.innerWidth,
        vh: window.innerHeight,
        largura: LARGURA,
        altura: ALTURA,
        toque,
      }),
    );
    return undefined;
  }, [fechar]);

  /** Um objeto marcado com `data-lembrar`. O retângulo é o do próprio
   *  elemento, então o botão nasce colado nele. */
  const avaliarObjeto = useCallback((elemento, toque) => {
    const achado = lembravelMaisProximo(elemento);
    if (!achado || !textoSuficiente(achado.texto)) return false;
    const r = achado.elemento.getBoundingClientRect();
    const rect = { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
    setAlvo({ texto: achado.texto, tipo: "objeto", ref: achado.ref, rect });
    setPos(
      posicionarBotao(rect, {
        vw: window.innerWidth,
        vh: window.innerHeight,
        largura: LARGURA,
        altura: ALTURA,
        toque,
      }),
    );
    return true;
  }, []);

  // --- os gestos ---------------------------------------------------------
  useEffect(() => {
    if (!ativo) return undefined;

    const agendar = (toque) => {
      clearTimeout(timer.current);
      // A seleção só está estável depois que o navegador termina de ajustá-la
      // — no toque ela ainda cresce por alguns quadros depois do `touchend`.
      timer.current = setTimeout(() => avaliarSelecao(toque), ESPERA_SELECAO);
    };

    const aoSoltarMouse = (e) => {
      if (e.target?.closest?.('[data-lembrar-ui="1"]')) return;
      // `pontoGrosso()` e não `false`: num celular o `mouseup` também chega,
      // e tratá-lo como mouse poria o botão por cima do balão nativo.
      agendar(pontoGrosso());
    };
    const aoSoltarToque = () => agendar(true);

    const aoMudarSelecao = () => {
      const sel = window.getSelection?.();
      // Só o CANCELAMENTO é tratado aqui, na hora: a seleção sumiu, o botão
      // some junto. Mostrar por este evento faria o botão piscar a cada
      // quadro enquanto o aluno ainda arrasta.
      if (!sel || sel.isCollapsed) {
        clearTimeout(timer.current);
        setAlvo((atual) => (atual?.tipo === "objeto" ? atual : null));
        setPos((atual) => (atual && alvo?.tipo === "objeto" ? atual : null));
      }
    };

    const aoMenuContexto = (e) => {
      // Clique-direito sobre um objeto marcado abre o NOSSO botão em vez do
      // menu do navegador. Fora de um objeto marcado, o menu do navegador
      // continua sendo dele — este componente não sequestra a página.
      if (avaliarObjeto(e.target, pontoGrosso())) e.preventDefault();
    };

    const aoComecarToque = (e) => {
      const el = e.target;
      if (!lembravelMaisProximo(el)) return;
      clearTimeout(toqueLongo.current);
      toqueLongo.current = setTimeout(() => avaliarObjeto(el, true), 500);
    };
    const cancelarToqueLongo = () => clearTimeout(toqueLongo.current);

    const aoTeclar = (e) => { if (e.key === "Escape") fechar(); };
    // Rolar ou girar o aparelho invalida a posição medida. Fechar é mais
    // honesto que redesenhar: o botão descreve um trecho, e um trecho que
    // saiu da tela não é mais o que o aluno está vendo.
    const aoRolar = () => fechar();

    document.addEventListener("mouseup", aoSoltarMouse);
    document.addEventListener("touchend", aoSoltarToque);
    document.addEventListener("selectionchange", aoMudarSelecao);
    document.addEventListener("contextmenu", aoMenuContexto);
    document.addEventListener("touchstart", aoComecarToque, { passive: true });
    document.addEventListener("touchmove", cancelarToqueLongo, { passive: true });
    document.addEventListener("touchend", cancelarToqueLongo);
    document.addEventListener("keydown", aoTeclar);
    window.addEventListener("scroll", aoRolar, true);
    window.addEventListener("resize", aoRolar);

    return () => {
      clearTimeout(timer.current);
      clearTimeout(toqueLongo.current);
      document.removeEventListener("mouseup", aoSoltarMouse);
      document.removeEventListener("touchend", aoSoltarToque);
      document.removeEventListener("selectionchange", aoMudarSelecao);
      document.removeEventListener("contextmenu", aoMenuContexto);
      document.removeEventListener("touchstart", aoComecarToque);
      document.removeEventListener("touchmove", cancelarToqueLongo);
      document.removeEventListener("touchend", cancelarToqueLongo);
      document.removeEventListener("keydown", aoTeclar);
      window.removeEventListener("scroll", aoRolar, true);
      window.removeEventListener("resize", aoRolar);
    };
  }, [ativo, avaliarSelecao, avaliarObjeto, fechar, alvo?.tipo]);

  // Trocar de tela fecha o botão: ele descreve um trecho da tela anterior.
  useEffect(() => { fechar(); }, [location.pathname, fechar]);

  const jaGuardado = alvo ? guardados.has(normalizar(alvo.texto)) : false;

  async function guardar() {
    if (!alvo || emVoo.current) return;
    if (jaGuardado) { fechar(); return; }
    emVoo.current = true;
    setSalvando(true);
    try {
      const { data } = await api.post(
        "/lembretes",
        montarPayload({
          texto: alvo.texto,
          pathname: location.pathname,
          titulo: document.title,
          contexto: contextoTela,
          tipo: alvo.tipo,
          ref: alvo.ref,
        }),
      );
      setGuardados((s) => new Set(s).add(normalizar(alvo.texto)));
      avisarSparksMudou();
      // A aba de Revisões pode estar aberta AGORA, atrás do toast.
      avisarLembretesMudou();
      window.getSelection?.()?.removeAllRanges();
      toast.success(
        data?.ja_estava ? "Isto já estava na sua fila." : "Guardado para revisar com a Mentis.",
        {
          description: data?.ja_estava
            ? "Nada foi cobrado de novo."
            : `−${data?.cobrado ?? CUSTO_PADRAO} Sparks · aparece na aba Revisões.`,
        },
      );
      fechar();
    } catch (e) {
      const status = e?.response?.status;
      toast.error(
        errMsg(e, "Não foi possível guardar agora."),
        status === 402 ? { description: "Recarregue Sparks para continuar guardando pontos." } : undefined,
      );
    } finally {
      emVoo.current = false;
      setSalvando(false);
    }
  }

  if (!ativo || !alvo || !pos) return null;

  return createPortal(
    <div
      data-lembrar-ui="1"
      className="lembrar-surge fixed z-[70]"
      style={{ left: pos.x, top: pos.y, width: LARGURA }}
      // O botão não pode roubar a seleção que ele descreve: no Safari, um
      // `mousedown` fora do texto colapsa o range antes de o clique chegar.
      onMouseDown={(e) => e.preventDefault()}
      data-testid="lembrar-flutuante"
    >
      <button
        type="button"
        onClick={guardar}
        disabled={salvando}
        style={{ height: ALTURA }}
        className="pill btn-sapiens flex w-full items-center justify-center gap-2 rounded-full px-4 text-[13px] font-medium shadow-xl disabled:opacity-60"
        title={resumir(alvo.texto, 140)}
        data-testid="lembrar-botao"
      >
        {salvando ? (
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
        ) : jaGuardado ? (
          <Check className="h-4 w-4 shrink-0" />
        ) : (
          <BookmarkPlus className="h-4 w-4 shrink-0" />
        )}
        <span className="truncate">
          {jaGuardado ? "Já está na sua fila" : "Lembrar-me com a Mentis"}
        </span>
        {!jaGuardado && (
          <span className="inline-flex shrink-0 items-center gap-0.5 rounded-full bg-black/25 px-1.5 py-0.5 text-[11px]">
            <Zap className="h-3 w-3" />
            {CUSTO_PADRAO}
          </span>
        )}
      </button>
    </div>,
    document.body,
  );
}
