import { Check } from "lucide-react";

/**
 * A régua de etapas no alto da estação — onde estou, quanto falta.
 *
 * Um segmento por etapa, não uma barra contínua: a barra responde "quanto por
 * cento", que é a pergunta errada aqui. A pergunta é "quantas telas faltam", e
 * ela se responde contando, de relance, sem ler número nenhum.
 *
 * O segmento cumprido não fica só cheio: ganha o traço da marca. É a mesma
 * luz da barra de progresso e do anel — a luz do produto é uma só.
 */
export default function PassosDaEstacao({ etapas, atual, cumpridas }) {
  if (etapas.length < 2) return null;

  return (
    <nav
      className="flex items-center gap-1.5"
      aria-label={`Etapa ${atual + 1} de ${etapas.length}`}
      data-testid="passos"
    >
      {etapas.map((etapa, i) => {
        const feita = cumpridas.has(i);
        const aqui = i === atual;
        return (
          <div
            key={i}
            className={[
              "h-1.5 flex-1 rounded-full transition-all duration-300",
              feita ? "bg-gradient-to-r from-[#4FD9FF] to-[#8B7BFF]"
                : aqui ? "bg-white/40"
                : "bg-white/10",
            ].join(" ")}
            data-estado={feita ? "feita" : aqui ? "atual" : "adiante"}
            title={etapa.rotulo}
          />
        );
      })}
      <span className="ml-1.5 shrink-0 font-mono-alt text-[10px] text-white/40 tabular-nums">
        {cumpridas.size >= etapas.length ? (
          <Check className="h-3 w-3 text-emerald-300" />
        ) : (
          `${atual + 1}/${etapas.length}`
        )}
      </span>
    </nav>
  );
}
