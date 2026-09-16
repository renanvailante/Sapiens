import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Download, X, Share, Plus, MoreVertical, MonitorDown, Check } from "lucide-react";

/**
 * Instalar o Sapiens — ou pôr um atalho na tela inicial / no Dock.
 *
 * Não existe um caminho único: cada plataforma resolve isto de um jeito, e
 * fingir que existe um botão universal produz um botão que não funciona em
 * metade dos aparelhos. Então:
 *
 * * **Android (Chrome/Edge/Samsung) e desktop (Windows/macOS/Linux, Chrome ou
 *   Edge)** — instalação nativa de verdade, pelo evento `beforeinstallprompt`
 *   que o navegador dispara. Um clique, sem passo a passo. Depende do service
 *   worker (`public/sw.js`), que existe só para isto.
 * * **iOS / iPadOS** — o Safari NUNCA dispara aquele evento e não há API de
 *   instalação. O único caminho é Compartilhar › Adicionar à Tela de Início,
 *   feito à mão pelo aluno. A tela mostra os passos com os ícones certos.
 * * **macOS no Safari 17+** — Compartilhar › Adicionar ao Dock.
 * * **Firefox** — menu › Instalar / Adicionar à Tela Inicial.
 *
 * E quando o app JÁ está instalado (rodando em `standalone`), nada disso
 * aparece: oferecer instalação a quem já instalou é a forma mais rápida de o
 * aluno deixar de confiar no que a interface diz.
 */

const InstalacaoCtx = createContext(null);

function detectarPlataforma() {
  if (typeof navigator === "undefined") return "desconhecida";
  const ua = navigator.userAgent || "";
  const plataforma = navigator.platform || "";
  // iPad com "Solicitar site para computador" se declara Macintosh; o que o
  // entrega é ter tela sensível ao toque.
  const iPadOS = plataforma === "MacIntel" && (navigator.maxTouchPoints || 0) > 1;
  if (/iPhone|iPad|iPod/.test(ua) || iPadOS) return "ios";
  if (/Android/.test(ua)) return "android";
  if (/Mac/.test(plataforma) || /Mac OS X/.test(ua)) return "macos";
  if (/Win/.test(plataforma) || /Windows/.test(ua)) return "windows";
  return "desconhecida";
}

function detectarNavegador() {
  if (typeof navigator === "undefined") return "desconhecido";
  const ua = navigator.userAgent || "";
  if (/Firefox|FxiOS/.test(ua)) return "firefox";
  if (/Edg\//.test(ua)) return "edge";
  if (/CriOS|Chrome/.test(ua)) return "chrome";
  if (/Safari/.test(ua)) return "safari";
  return "desconhecido";
}

function estaInstalado() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

/**
 * Provedor global: guarda o evento de instalação que o navegador dispara UMA
 * vez, cedo, normalmente antes de qualquer tela pedir por ele. Sem guardar,
 * o evento se perde e a instalação nativa vira inalcançável.
 */
export function InstalacaoProvider({ children }) {
  const [evento, setEvento] = useState(null);
  const [instalado, setInstalado] = useState(estaInstalado);

  useEffect(() => {
    const aoPoderInstalar = (e) => {
      e.preventDefault(); // sem isto o Chrome mostra o próprio banner por cima
      setEvento(e);
    };
    const aoInstalar = () => {
      setEvento(null);
      setInstalado(true);
    };
    window.addEventListener("beforeinstallprompt", aoPoderInstalar);
    window.addEventListener("appinstalled", aoInstalar);
    return () => {
      window.removeEventListener("beforeinstallprompt", aoPoderInstalar);
      window.removeEventListener("appinstalled", aoInstalar);
    };
  }, []);

  const valor = useMemo(
    () => ({
      evento,
      instalado,
      plataforma: detectarPlataforma(),
      navegador: detectarNavegador(),
      limparEvento: () => setEvento(null),
    }),
    [evento, instalado],
  );

  return <InstalacaoCtx.Provider value={valor}>{children}</InstalacaoCtx.Provider>;
}

export function useInstalacao() {
  return useContext(InstalacaoCtx) || {
    evento: null, instalado: false, plataforma: "desconhecida",
    navegador: "desconhecido", limparEvento: () => {},
  };
}

// --------------------------------------------------------------------------
// Passo a passo por plataforma — só para quem NÃO tem instalação nativa.
// --------------------------------------------------------------------------

const PASSOS = {
  ios: {
    titulo: "Adicionar à Tela de Início",
    nota: "No iPhone e no iPad, a instalação é feita pelo Safari — nenhum navegador no iOS tem botão automático.",
    itens: [
      { icone: Share, texto: "Toque em Compartilhar, na barra do Safari." },
      { icone: Plus, texto: "Escolha “Adicionar à Tela de Início”." },
      { icone: Check, texto: "Confirme em “Adicionar”. O Sapiens vira um ícone como qualquer app." },
    ],
  },
  macos: {
    titulo: "Adicionar ao Dock",
    nota: "No Safari 17 ou mais novo. No Chrome ou no Edge, o botão de instalar aparece na barra de endereço.",
    itens: [
      { icone: Share, texto: "Clique em Compartilhar, na barra do Safari." },
      { icone: Plus, texto: "Escolha “Adicionar ao Dock”." },
      { icone: Check, texto: "Confirme. O Sapiens abre em janela própria, sem abas." },
    ],
  },
  windows: {
    titulo: "Instalar no Windows",
    nota: "No Chrome ou no Edge.",
    itens: [
      { icone: MonitorDown, texto: "Clique no ícone de instalar, à direita da barra de endereço." },
      { icone: MoreVertical, texto: "Ou abra o menu do navegador e procure “Instalar Sapiens”." },
      { icone: Check, texto: "O Sapiens ganha atalho no menu Iniciar e na barra de tarefas." },
    ],
  },
  android: {
    titulo: "Adicionar à tela inicial",
    nota: "No Chrome, Edge ou Samsung Internet.",
    itens: [
      { icone: MoreVertical, texto: "Abra o menu do navegador (os três pontos)." },
      { icone: Plus, texto: "Toque em “Instalar app” ou “Adicionar à tela inicial”." },
      { icone: Check, texto: "Confirme. O ícone vai para a sua tela inicial." },
    ],
  },
  desconhecida: {
    titulo: "Criar um atalho",
    nota: "O caminho muda de navegador para navegador.",
    itens: [
      { icone: MoreVertical, texto: "Abra o menu do seu navegador." },
      { icone: Plus, texto: "Procure por “Instalar”, “Adicionar à tela inicial” ou “Criar atalho”." },
      { icone: Check, texto: "Confirme e o Sapiens abre em janela própria." },
    ],
  },
};

export function ModalInstalar({ aberto, aoFechar }) {
  const { evento, plataforma, navegador, limparEvento } = useInstalacao();
  const [pedindo, setPedindo] = useState(false);

  const instalarAgora = useCallback(async () => {
    if (!evento) return;
    setPedindo(true);
    try {
      evento.prompt();
      await evento.userChoice;
    } finally {
      // O evento é de uso único: depois de `prompt()` ele não serve mais,
      // tenha o aluno aceitado ou não. Guardá-lo produziria um botão que não
      // faz nada no segundo clique.
      limparEvento();
      setPedindo(false);
      aoFechar?.();
    }
  }, [evento, limparEvento, aoFechar]);

  if (!aberto) return null;

  // Firefox no Android usa o menu, não o evento nativo.
  const chave = navegador === "firefox" && plataforma === "android" ? "android" : plataforma;
  const passos = PASSOS[chave] || PASSOS.desconhecida;

  return createPortal(
    <div
      className="fixed inset-0 z-[70] flex items-end justify-center bg-black/70 p-0 sm:items-center sm:p-4"
      onClick={aoFechar}
      data-testid="instalar-modal"
    >
      <div
        className="w-full max-w-sm rounded-t-3xl border border-white/12 bg-[#0a1526] p-6 shadow-2xl sm:rounded-3xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-white/40">
              Sapiens no seu aparelho
            </div>
            <h3 className="mt-1 font-display text-xl font-bold tracking-tight text-white">
              {evento ? "Instalar o Sapiens" : passos.titulo}
            </h3>
          </div>
          <button
            type="button"
            onClick={aoFechar}
            className="-m-1 rounded-full p-1.5 text-white/40 hover:bg-white/10 hover:text-white"
            aria-label="Fechar"
            data-testid="instalar-fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {evento ? (
          <>
            <p className="mt-3 text-sm leading-relaxed text-white/60">
              Abre em janela própria, direto do seu aparelho. Ocupa poucos megabytes.
            </p>
            <button
              type="button"
              onClick={instalarAgora}
              disabled={pedindo}
              className="pill btn-sapiens mt-5 inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3.5 text-sm font-medium disabled:opacity-60"
              data-testid="instalar-nativo"
            >
              <Download className="h-4 w-4" /> {pedindo ? "Abrindo…" : "Instalar agora"}
            </button>
          </>
        ) : (
          <>
            <ol className="mt-4 space-y-3">
              {passos.itens.map((p, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-[#7FD8FF]">
                    <p.icone className="h-3.5 w-3.5" />
                  </span>
                  <span className="text-sm leading-relaxed text-white/70">{p.texto}</span>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-xs leading-relaxed text-white/35">{passos.nota}</p>
          </>
        )}
      </div>
    </div>,
    document.body,
  );
}

/** O botão. Some sozinho quando o app já está instalado. */
export default function BotaoInstalar({ className = "", children, testid = "instalar-abrir" }) {
  const { instalado } = useInstalacao();
  const [aberto, setAberto] = useState(false);
  if (instalado) return null;
  return (
    <>
      <button type="button" onClick={() => setAberto(true)} className={className} data-testid={testid}>
        {children || (
          <>
            <Download className="h-4 w-4" /> Instalar o app
          </>
        )}
      </button>
      <ModalInstalar aberto={aberto} aoFechar={() => setAberto(false)} />
    </>
  );
}
