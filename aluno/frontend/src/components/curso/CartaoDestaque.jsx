import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { glifoDaCapa } from "./CapaDoCurso";
import CaminhoMini from "./CaminhoMini";

/**
 * O CARTÃO GRANDE — o curso que o aluno estava fazendo, no topo do catálogo
 * embutido de `/estudar` (ver `pages/Cursos.jsx`, `embutido`).
 *
 * Por que maior que os outros: é o único item da tela que responde "o que eu
 * faço agora", e essa resposta pesa mais do que uma vitrine. O pedaço de
 * caminho andado (`CaminhoMini`) é o que carrega esse peso — uma trilha com
 * nó apagado convence mais do que um número de porcentagem sozinho.
 *
 * 2026-10-10: virou `.cartao-gordo` (a mesma peça dos cartões abaixo dele) com
 * um botão "Continuar" escrito. A versão anterior passava `w-14` à capa, que
 * já tinha `w-full`: a capa virava uma barra da largura do card e o título
 * era empurrado para fora da tela.
 */
export default function CartaoDestaque({ curso }) {
  const p = curso.progresso || {};
  const proxima = p.proxima;
  const Glifo = glifoDaCapa(curso.capa);
  const para = curso.capa?.para || "#2F6BFF";

  return (
    <Link
      to={proxima ? `/cursos/${curso.curso_id}/estacao/${proxima.estacao_id}` : `/cursos/${curso.curso_id}`}
      className="cartao-gordo gap-4 p-4 sm:p-5"
      style={{
        "--de": curso.capa?.de || "#4FD9FF",
        "--para": para,
        "--pe": `color-mix(in srgb, ${para} 55%, #03060D)`,
        "--tinta": "#BFE7FF",
      }}
      data-testid="estudar-destaque"
    >
      <div className="flex items-center gap-4">
        <span className="cartao-gordo-icone" style={{ width: 64, height: 64, borderRadius: 20 }} aria-hidden="true">
          <Glifo strokeWidth={2} style={{ width: 32, height: 32 }} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-[#9BE7FF]">
            Continue de onde parou
          </div>
          <h2 className="cartao-gordo-titulo cartao-gordo-titulo--g mt-0.5">{curso.titulo}</h2>
          <p className="cartao-gordo-sub mt-0.5 truncate">
            {proxima ? `Próxima: ${proxima.titulo}` : `${p.concluidas}/${p.estacoes} estações`}
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3 overflow-hidden">
          <CaminhoMini total={p.estacoes} concluidas={p.concluidas} />
          <span className="shrink-0 font-display text-sm font-extrabold tabular-nums text-white/80">
            {p.percentual || 0}%
          </span>
        </div>
        <span className="btn-sapiens inline-flex shrink-0 items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-bold">
          Continuar <ArrowRight className="h-4 w-4" />
        </span>
      </div>
    </Link>
  );
}
