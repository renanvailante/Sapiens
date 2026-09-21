import { ArrowRight } from "lucide-react";

/**
 * A ESTEIRA — ERRO → ANÁLISE → HABILIDADE → PRÓXIMO ESTUDO.
 *
 * Quatro caixas e três setas. No celular a esteira é **vertical** e as setas
 * apontam para baixo; no desktop ela deita.
 *
 * Por que não uma fileira rolável horizontal no celular: uma esteira que
 * precisa ser arrastada esconde o último passo, e o último passo é o único
 * que diz o que a pessoa ganha. O produto já tem `TiraRolavel` para fileiras
 * de catálogo — ali o que está cortado é "mais do mesmo", aqui seria a
 * conclusão.
 *
 * As setas giram por CSS (`rotate-90` até `md`), não por dois conjuntos de
 * ícones montados condicionalmente: um ícone só, uma transformação.
 */
export default function FeatureFlow({ passos, nota = null, testid = "ads-esteira" }) {
  return (
    <section data-testid={testid}>
      <div className="flex flex-col items-stretch gap-2 md:flex-row md:items-stretch">
        {passos.map((passo, i) => (
          <div key={passo.rotulo} className="flex flex-col items-center gap-2 md:flex-1 md:flex-row">
            <div className="superficie flex w-full flex-1 flex-col justify-center rounded-2xl px-4 py-4 text-center">
              <div className="font-mono-alt text-[10px] font-semibold uppercase tracking-[0.22em] text-[#7FD8FF]/75">
                {passo.rotulo}
              </div>
              <p className="mt-2 text-[13px] leading-snug text-white/70">{passo.corpo}</p>
            </div>
            {i < passos.length - 1 && (
              <ArrowRight
                className="h-4 w-4 shrink-0 rotate-90 text-white/25 md:rotate-0"
                aria-hidden="true"
              />
            )}
          </div>
        ))}
      </div>
      {nota && (
        <p className="mt-5 text-center text-[13px] leading-relaxed text-white/50" data-testid={`${testid}-nota`}>
          {nota}
        </p>
      )}
    </section>
  );
}
