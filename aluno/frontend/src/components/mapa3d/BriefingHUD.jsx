import { motion } from "framer-motion";
import { Telescope, ChevronRight } from "lucide-react";
import { ESTADO_LABEL } from "./sceneBuilder";

/** Mostra o RÓTULO curto da missão, nunca a frase original da habilidade —
 * essa continua sendo dado interno, sem tela que a exiba.
 *
 * `Briefing` reestilizado como painel HUD ancorado — "expansão do mapa",
 * não modal administrativo: sem cortina cobrindo o mundo 3D inteiro, só uma
 * vinheta de um lado (o escurecimento de verdade vem do dolly da câmera).
 * Mesmo contrato de props do `Briefing` anterior — a página não muda. */
export default function BriefingHUD({ hab, onFechar, onIniciar }) {
  const bioma = hab.bioma;
  return (
    <motion.div
      // `pb-24` no celular, não `pb-3`: o mapa é `fixed inset-0` (a página não
      // rola), então o ícone da Mentis no canto inferior direito ficava
      // exatamente sobre o "Iniciar missão" — o botão que faz a tela existir.
      // A partir de `sm` o painel sai do rodapé e vai para a coluna da
      // direita, e a folga volta a ser a de sempre.
      className="fixed z-30 inset-x-0 bottom-0 sm:inset-x-auto sm:right-0 sm:top-16 sm:bottom-0 w-full sm:w-[400px] flex items-end sm:items-stretch px-3 pb-24 sm:p-4 pointer-events-none"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div
        className="hidden sm:block fixed inset-y-0 right-0 w-[440px] -z-10"
        style={{ background: "linear-gradient(to left, rgba(3,6,13,0.55), transparent)" }}
      />
      <motion.div
        className="card-sapiens rounded-2xl p-6 md:p-7 w-full max-h-[70dvh] sm:max-h-full overflow-y-auto pointer-events-auto"
        initial={{ x: 0, y: 24, opacity: 0, scale: 0.97 }}
        animate={{ x: 0, y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 12, opacity: 0 }}
        transition={{ type: "spring", damping: 24, stiffness: 260 }}
        data-testid="mapa-briefing"
      >
        <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-sapiens-accentDeep flex items-center gap-1.5">
          <Telescope className="w-3.5 h-3.5" /> {bioma.nome}
        </div>
        <h2 className="mt-2 font-display text-2xl font-extrabold tracking-tight text-zinc-950">
          Missão: {hab.rotulo}
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-zinc-600 italic">{bioma.ideia}</p>
        <div className="mt-4 rounded-xl bg-sapiens-accentSoft/60 border border-sapiens-accent/20 px-4 py-3 text-sm text-zinc-700">
          {bioma.resumo}
        </div>
        <div className="mt-4 text-xs font-mono-alt uppercase tracking-wide text-zinc-400">
          {ESTADO_LABEL[hab.estado]}
          {hab.respondidas > 0 && ` · ${hab.respondidas} tentativa(s)`}
        </div>
        <div className="mt-6 flex gap-3">
          <button
            onClick={onFechar}
            className="text-sm text-zinc-400 hover:text-zinc-600 px-2"
            data-testid="mapa-briefing-fechar"
          >
            Voltar ao mapa
          </button>
          <button
            onClick={onIniciar}
            className="pill flex-1 inline-flex items-center justify-center gap-2 text-sm font-medium btn-sapiens px-5 py-2.5 rounded-full"
            data-testid="mapa-briefing-iniciar"
          >
            Iniciar missão <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
