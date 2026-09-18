import { Check, Sparkles, X } from "lucide-react";
import { letrasCorretas } from "./Alternativas";

/**
 * O VEREDITO — a mesma devolutiva, venha a questão de onde vier.
 *
 * O aluno responde questão em cinco lugares do produto, e até aqui cada um
 * anunciava o resultado de um jeito: a prova com selo de 34px e o pulso de
 * recompensa no acerto, o treino com um retângulo pastel e uma linha em
 * negrito, as questões geradas com um terceiro desenho. Três gramáticas para
 * o único momento da sessão em que o aluno está mais atento — o instante
 * imediatamente depois de errar.
 *
 * As regras que esta peça carrega, e que valem agora em toda parte:
 *
 * 1. **O selo fala antes da palavra.** Um ícone de 34px à esquerda diz certo
 *    ou errado antes de qualquer texto ser lido.
 * 2. **Só o acerto comemora.** `.recompensa` pulsa uma vez no acerto e nunca
 *    no erro: comemorar o erro seria falso, e o erro tem tratamento próprio
 *    logo abaixo (a causa, a Mentis, a próxima ação).
 * 3. **O erro nunca termina em beco.** Quem erra precisa saber o que fazer em
 *    seguida, e é para isso que existe `children`: a explicação da Mentis, a
 *    intervenção sobre a causa raiz, o micro-diagnóstico. Quem chama decide
 *    QUAIS tratamentos cabem ali; o desenho do veredito não muda.
 *
 * A aparência continua morando no CSS (`index.css`, bloco "O veredito").
 */
export default function Veredito({
  resultado,
  explicacao = null,
  sparksGanhos = 0,
  children = null,
  testid = "veredito",
}) {
  if (!resultado) return null;

  const acertou = Boolean(resultado.acertou);
  const corretas = letrasCorretas(resultado);
  const titulo =
    resultado.feedback?.titulo ||
    (acertou
      ? "Você acertou!"
      : corretas.length
      ? `Resposta incorreta. Correta: ${corretas.join(" ou ")}.`
      : "Resposta incorreta.");

  // A explicação pode chegar como texto único (treino: `elucidacao`) ou como
  // lista de parágrafos (prova: `feedback.mensagens`). Uma normalização só,
  // para não haver dois entendimentos de "o que o sistema me explicou".
  const paragrafos = explicacao
    ? Array.isArray(explicacao)
      ? explicacao
      : [explicacao]
    : resultado.feedback?.mensagens || [];

  return (
    <div
      className={`veredito reveal mt-5 ${acertou ? "recompensa" : ""}`}
      data-acertou={acertou}
      data-testid={testid}
    >
      <span className="veredito-selo">
        {acertou ? <Check className="h-5 w-5" strokeWidth={3} /> : <X className="h-5 w-5" strokeWidth={3} />}
      </span>
      <div className="min-w-0 flex-1">
        <div className={`text-sm font-bold ${acertou ? "text-emerald-700" : "text-rose-700"}`}>
          {titulo}
        </div>

        {paragrafos.map((p, i) => (
          <p
            key={i}
            className={`mt-2 text-sm leading-relaxed ${acertou ? "text-emerald-800" : "text-rose-800"}`}
          >
            {p}
          </p>
        ))}

        {sparksGanhos > 0 && (
          <div
            className="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-amber-700"
            data-testid={`${testid}-sparks`}
          >
            <Sparkles className="h-3.5 w-3.5" /> +{sparksGanhos} {sparksGanhos === 1 ? "Spark" : "Sparks"}
          </div>
        )}

        {children}
      </div>
    </div>
  );
}
