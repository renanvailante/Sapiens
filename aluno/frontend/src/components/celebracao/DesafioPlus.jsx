import { Link } from "react-router-dom";
import { ArrowRight, Crown, Gift } from "lucide-react";
import { CaminhoDoPlus } from "./TelaDaOfensiva";
import { BENEFICIOS_DO_PLUS, fraseDoDesafio, horasRestantes, prazoDoPlus } from "../../lib/celebracao";
import { ROTAS } from "../../lib/rotas";

/**
 * O DESAFIO DOS 5 DIAS — a promessa à vista desde o primeiro acesso.
 *
 * Pedido do dono (2026-10-08): "quero que o aluno saiba desde o início que, se
 * mantiver a ofensiva de cinco dias, ganha dois dias como se fosse pago". Este
 * card é esse "desde o início": está na seção da sequência do Hoje desde a
 * conta nova (0 de 5), e anda um nó por dia estudado.
 *
 * Três estados, todos lidos de `engajamento.plus` (servidor):
 *
 * * **a caminho** — as cinco chamas, a caixa no fim e quanto falta;
 * * **Plus ativo** — o que está aberto e até quando, com o relógio REAL
 *   (`plus.ate`, gravado no servidor no instante da concessão);
 * * **já usado** — o card some. A promessa era de uma vez, e repetir a
 *   chamada para quem já ganhou seria prometer de novo o que não vem.
 */
export default function DesafioPlus({ plus, estudouHoje = false }) {
  if (!plus) return null;

  if (plus.ativo) {
    const prazo = prazoDoPlus(plus.ate);
    const horas = horasRestantes(plus.ate);
    return (
      <div className="plus-ativo superficie relative overflow-hidden p-4 sm:p-5" data-testid="desafio-plus-ativo">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <span className="coroa-plus flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl">
              <Crown className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="font-display text-lg font-extrabold tracking-tight text-white">
                <span className="texto-plus">Sapiens Plus</span> ativo
              </div>
              <div className="text-xs text-amber-100/80">
                {prazo ? `Vale ${prazo}` : "Prêmio da sua ofensiva de 5 dias"}
                {horas ? ` · faltam ${horas}h` : ""}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {BENEFICIOS_DO_PLUS.map((b) => (
              <span key={b.chave} className="chip border-amber-300/30 bg-amber-400/10 px-2.5 py-1 text-[11px] text-amber-100">
                {b.texto}
              </span>
            ))}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs font-semibold">
          <Link to={ROTAS.MENTIS} className="inline-flex items-center gap-1 text-[#7FD8FF] hover:underline">
            Abrir a Mentis <ArrowRight className="h-3 w-3" />
          </Link>
          <Link to={ROTAS.CURSOS} className="inline-flex items-center gap-1 text-[#7FD8FF] hover:underline">
            Ver os cursos <ArrowRight className="h-3 w-3" />
          </Link>
          <Link to={`${ROTAS.COMUNIDADE}?sala=vip`} className="inline-flex items-center gap-1 text-[#7FD8FF] hover:underline">
            Entrar na sala VIP <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>
    );
  }

  if (plus.conquistado) return null;

  const frase = fraseDoDesafio(plus);
  return (
    <div className="desafio-plus superficie relative overflow-hidden p-4 sm:p-5" data-testid="desafio-plus">
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="min-w-0 flex-1">
          <div className="secao-olho flex items-center gap-1.5 text-amber-200/90">
            <Gift className="h-3 w-3" /> Desafio dos {plus.meta_dias} dias
          </div>
          <p className="mt-1.5 font-display text-lg font-extrabold leading-snug tracking-tight text-white">
            {frase}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-white/55">
            Mentis ilimitada, todos os cursos e e-books e a sala VIP — como se você tivesse pago.
            {!estudouHoje && plus.progresso > 0 ? " Estude hoje para não voltar ao zero." : ""}
          </p>
        </div>
        <div className="shrink-0">
          <CaminhoDoPlus plus={plus} />
          <div className="mt-1.5 text-center font-mono-alt text-[11px] tabular-nums text-white/45">
            {plus.progresso}/{plus.meta_dias} dias
          </div>
        </div>
      </div>
    </div>
  );
}
