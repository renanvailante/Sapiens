import { useNavigate } from "react-router-dom";
import { ArrowRight, Compass } from "lucide-react";

/**
 * "Vou te levar lá."
 *
 * A Mentis deixou de ser um chat que descreve o caminho ("abra a aba Treino,
 * depois procure o mapa") para virar a camada que LEVA. O backend valida o
 * destino contra uma lista fechada (`mentis_routes.DESTINOS`) antes de isto
 * chegar aqui, então o botão nunca aponta para uma rota inventada nem para
 * fora do produto.
 *
 * Navegar é grátis, e o botão diz isso: o que custar Sparks, custa na tela de
 * destino, com o preço à vista — mesma regra das outras ações.
 */
export default function MentisAcaoIr({ acao }) {
  const nav = useNavigate();
  if (!acao || acao.tipo !== "ir" || !acao.rota) return null;

  return (
    <button
      type="button"
      onClick={() => nav(acao.rota)}
      className="pill mt-2 inline-flex items-center gap-1.5 rounded-full border border-[#4FD9FF]/30 bg-[#4FD9FF]/10 px-3.5 py-2 text-xs font-medium text-[#BFE7FF] transition hover:border-[#4FD9FF]/50 hover:bg-[#4FD9FF]/15"
      data-testid="mentis-acao-ir"
      data-destino={acao.destino}
    >
      <Compass className="h-3.5 w-3.5" />
      {acao.rotulo} <ArrowRight className="h-3 w-3" />
    </button>
  );
}
