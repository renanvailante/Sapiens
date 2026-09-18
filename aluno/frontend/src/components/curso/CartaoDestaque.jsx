import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import CapaDoCurso from "./CapaDoCurso";
import CaminhoMini from "./CaminhoMini";

/**
 * O CARTÃO GRANDE — o curso que o aluno estava fazendo, em destaque no topo
 * do catálogo embutido de `/estudar` (ver `pages/Cursos.jsx`, `embutido`).
 *
 * Por que maior que os outros: é o único item da tela que responde "o que eu
 * faço agora", e essa resposta pesa mais do que uma vitrine. O pedaço de
 * caminho andado (`CaminhoMini`) é o que carrega esse peso — uma trilha com
 * nó apagado convence mais do que um número de porcentagem sozinho.
 */
export default function CartaoDestaque({ curso }) {
  const p = curso.progresso || {};
  const proxima = p.proxima;

  return (
    <Link
      to={proxima ? `/cursos/${curso.curso_id}/estacao/${proxima.estacao_id}` : `/cursos/${curso.curso_id}`}
      className="superficie superficie-viva lift block overflow-hidden rounded-3xl p-5"
      data-testid="estudar-destaque"
    >
      <div className="flex items-start gap-4">
        <CapaDoCurso
          capa={curso.capa}
          altura="h-14"
          className="w-14 shrink-0 rounded-2xl"
          testid="estudar-destaque-capa"
        />
        <div className="min-w-0 flex-1">
          <div className="secao-olho">Continue de onde parou</div>
          <h2 className="mt-1 truncate font-display text-xl font-extrabold tracking-tight text-white">
            {curso.titulo}
          </h2>
          <p className="mt-1 truncate text-xs text-white/50">
            {proxima ? `Próxima: ${proxima.titulo}` : `${p.concluidas}/${p.estacoes} estações`}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-mono-alt text-2xl font-extrabold tabular-nums text-white">
            {p.percentual || 0}%
          </div>
          <ArrowRight className="ml-auto mt-1 h-3.5 w-3.5 text-white/30" />
        </div>
      </div>
      <CaminhoMini total={p.estacoes} concluidas={p.concluidas} className="mt-4" />
    </Link>
  );
}
