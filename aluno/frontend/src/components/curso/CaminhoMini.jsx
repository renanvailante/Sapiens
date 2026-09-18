import { Check, Play, Lock } from "lucide-react";

/**
 * UM PEDAÇO DO CAMINHO — não o caminho inteiro (`CaminhoDoCurso`), só os nós
 * ao redor de onde o aluno está, para caber no cartão de destaque do
 * catálogo embutido (`pages/Estudar.jsx`). É a mesma ideia visual do
 * Duolingo: ver o trecho andado convence mais do que um número de
 * porcentagem sozinho.
 *
 * Não conhece o título nem o estado real de nenhuma estação — só a CONTAGEM
 * (`total`, `concluidas`) que a listagem `/cursos` já manda (ver
 * `cursos_progresso.resumo_do_curso`). O caminho detalhado, com nome e
 * estado de cada estação, continua sendo `CaminhoDoCurso`, dentro do curso.
 */
const JANELA = 6;

export default function CaminhoMini({ total = 0, concluidas = 0, janela = JANELA, className = "" }) {
  if (!total) return null;
  const vencidas = Math.min(total, Math.max(0, concluidas));

  // Janela centrada em torno de onde o aluno está agora, com as pontas
  // presas nos limites do curso — sem isso um curso quase terminado (ex.:
  // 9 de 10) desenharia uma janela vazada além do último nó.
  let inicio = Math.max(0, vencidas - Math.floor(janela / 2));
  let fim = Math.min(total, inicio + janela);
  inicio = Math.max(0, fim - janela);

  const nos = Array.from({ length: fim - inicio }, (_, i) => {
    const idx = inicio + i;
    return idx < vencidas ? "vencida" : idx === vencidas ? "atual" : "bloqueada";
  });

  return (
    <div className={`flex items-center ${className}`} aria-hidden="true" data-testid="caminho-mini">
      {inicio > 0 && <span className="mr-1.5 shrink-0 text-xs text-white/25">···</span>}
      {nos.map((estado, i) => (
        <div key={i} className="flex items-center">
          <span
            className={[
              "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
              estado === "vencida" && "bg-gradient-to-br from-[#4FD9FF] to-[#8B7BFF] text-[#06122B]",
              estado === "atual" && "bg-white text-[#06122B] ring-2 ring-[#4FD9FF]/50",
              estado === "bloqueada" && "bg-white/10 text-white/25",
            ].filter(Boolean).join(" ")}
          >
            {estado === "vencida" ? (
              <Check className="h-3 w-3" strokeWidth={3} />
            ) : estado === "atual" ? (
              <Play className="h-3 w-3" />
            ) : (
              <Lock className="h-2.5 w-2.5" />
            )}
          </span>
          {i < nos.length - 1 && (
            <span
              className={`h-[3px] w-5 shrink-0 sm:w-7 ${
                estado === "vencida" ? "bg-gradient-to-r from-[#4FD9FF] to-[#8B7BFF]" : "bg-white/10"
              }`}
            />
          )}
        </div>
      ))}
      {fim < total && <span className="ml-1.5 shrink-0 text-xs text-white/25">···</span>}
    </div>
  );
}
