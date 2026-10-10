import { Star, Trophy } from "lucide-react";
import { Chama } from "../celebracao/TelaDaOfensiva";

/**
 * O PLACAR DO TOPO — a barra de cima do Duolingo (chama, nível, liga).
 *
 * Três números que o aluno vê sem procurar, porque são os que mudam com o que
 * ele faz HOJE. O detalhe de cada um (a semana da ofensiva, o congelador, a
 * tabela da liga) continua em "Seu ritmo", mais abaixo; tocar num chip leva
 * até lá. Nenhum número aqui é calculado na tela: os três vêm de
 * `/engajamento/me`, e sem ele o placar simplesmente não aparece.
 */
export default function HudDoDia({ engajamento, aoTocar, testid = "hud-dia" }) {
  if (!engajamento) return null;
  const o = engajamento.ofensiva || {};
  const n = engajamento.nivel || null;
  const l = engajamento.liga || null;
  const acesa = (o.dias || 0) > 0 && Boolean(o.estudou_hoje);

  return (
    <div className="flex min-w-0 items-center gap-1.5 sm:gap-2" data-testid={testid}>
      <button
        type="button"
        onClick={aoTocar}
        className={`hud-chip ${acesa ? "hud-chip-chama" : ""}`}
        aria-label={`Ofensiva de ${o.dias || 0} ${o.dias === 1 ? "dia" : "dias"}${acesa ? ", garantida hoje" : ""}`}
        data-testid={`${testid}-ofensiva`}
      >
        <Chama tamanho={20} acesa={acesa} className="chama-mini shrink-0" />
        <span className="tabular-nums">{o.dias || 0}</span>
      </button>
      {n && (
        <button type="button" onClick={aoTocar} className="hud-chip" aria-label={`Nível ${n.nivel}, ${n.percentual}% para o próximo`} data-testid={`${testid}-nivel`}>
          <Star className="h-4 w-4 text-[#9FE9FF]" fill="currentColor" />
          <span className="tabular-nums">Nv {n.nivel}</span>
          <span className="hud-xp" aria-hidden="true"><i style={{ width: `${Math.max(0, Math.min(100, n.percentual || 0))}%` }} /></span>
        </button>
      )}
      {l?.minha_posicao ? (
        <button type="button" onClick={aoTocar} className="hud-chip" aria-label={`${l.minha_posicao}º lugar na liga ${l.nome}`} data-testid={`${testid}-liga`}>
          <Trophy className="h-4 w-4" style={{ color: l.cor }} />
          <span className="tabular-nums">{l.minha_posicao}º</span>
        </button>
      ) : null}
    </div>
  );
}
