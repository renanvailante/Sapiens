import { Sprout, Repeat, Lightbulb, CircleCheck, CircleX, Shuffle } from "lucide-react";

/**
 * Trajetória cognitiva (Fase 4) — a única evidência de que o produto funcionou.
 *
 * O aluno via um ESTADO. Não via uma MUDANÇA. E mudança é o que justifica tudo.
 *
 * A restrição mais delicada da proposta inteira mora aqui, e é de conteúdo, não
 * de layout: esta é a tela que narra causalidade ("trabalhamos isso, e você
 * melhorou"), que é a afirmação mais forte que o produto faz sobre alguém.
 * Enquanto o perfil for provisório — enquanto a anotação das questões não tiver
 * passado por revisão humana —, ela DESCREVE o que aconteceu e não afirma por
 * quê. O servidor decide isso em `nexo_causal`; a tela obedece. Não é
 * conservadorismo: é a diferença entre relatar e alegar.
 */

const MARCOS = {
  raiz: { icone: Repeat, cor: "text-rose-600", anel: "border-rose-200" },
  intervencao: { icone: Lightbulb, cor: "text-amber-600", anel: "border-amber-200" },
  reteste_ok: { icone: CircleCheck, cor: "text-emerald-600", anel: "border-emerald-200" },
  reteste_falho: { icone: CircleX, cor: "text-zinc-500", anel: "border-zinc-200" },
  transferencia: { icone: Shuffle, cor: "text-sky-600", anel: "border-sky-200" },
};

function dataCurta(iso) {
  try {
    return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  } catch {
    return "";
  }
}

/** A frase de fecho de uma habilidade. Duas versões: uma descreve, outra alega. */
function fecho(h, nexoCausal) {
  const ok = h.retestes?.acertos || 0;
  const transferiu = (h.transferencias?.acertos || 0) > 0;
  if (!ok) return null;
  if (!nexoCausal) {
    return transferiu
      ? "Você errou isto, praticou, acertou nas revisões e acertou também em outro contexto."
      : "Você errou isto, praticou e acertou nas revisões seguintes.";
  }
  return transferiu
    ? "Você tinha dificuldade com isto. Trabalhamos. Agora você aplica em situações diferentes."
    : "Você tinha dificuldade com isto. Trabalhamos, e o acerto se manteve nas revisões.";
}

export default function Trajetoria({ dados }) {
  const habilidades = dados?.habilidades || [];

  if (dados?.indisponivel) {
    return (
      <p className="text-sm text-zinc-500" data-testid="trajetoria-indisponivel">
        Não foi possível ler a sua trajetória agora. Tente de novo em alguns minutos.
      </p>
    );
  }

  if (habilidades.length === 0) {
    return (
      <p className="text-sm leading-relaxed text-zinc-600" data-testid="trajetoria-vazia">
        Ainda não há trajetória para mostrar. Ela começa quando o Sapiens identifica a causa de um
        erro seu e marca uma revisão — daí em diante, cada volta fica registrada aqui.
      </p>
    );
  }

  return (
    <div className="space-y-4" data-testid="trajetoria">
      {!dados.nexo_causal && dados.aviso && (
        <div
          className="rounded-2xl border border-amber-100 bg-amber-50 p-4 text-sm leading-relaxed text-amber-800"
          data-testid="trajetoria-aviso"
        >
          {dados.aviso}
        </div>
      )}

      {habilidades.map((h) => (
        <div key={h.processo_id} className="card-sapiens rounded-2xl p-5" data-testid={`trajetoria-${h.processo_id}`}>
          <div className="font-display text-lg font-bold tracking-tight text-zinc-950">{h.processo_nome}</div>

          <ol className="mt-4 space-y-0">
            {h.marcos.map((m, i) => {
              const cfg = MARCOS[m.tipo] || MARCOS.reteste_falho;
              const Icone = cfg.icone;
              const ultimo = i === h.marcos.length - 1;
              return (
                <li key={`${m.quando}-${i}`} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border bg-white ${cfg.anel}`}>
                      <Icone className={`h-3.5 w-3.5 ${cfg.cor}`} strokeWidth={2.2} />
                    </div>
                    {!ultimo && <div className="w-px flex-1 bg-zinc-200" />}
                  </div>
                  <div className={`min-w-0 ${ultimo ? "pb-0" : "pb-4"}`}>
                    <div className="font-mono-alt text-[10px] uppercase tracking-wide text-zinc-400">
                      {dataCurta(m.quando)}
                    </div>
                    <div className="text-sm text-zinc-700">{m.rotulo}</div>
                  </div>
                </li>
              );
            })}
          </ol>

          {fecho(h, dados.nexo_causal) && (
            <p className="mt-4 border-t border-zinc-100 pt-3 text-sm leading-relaxed text-zinc-600">
              {fecho(h, dados.nexo_causal)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
