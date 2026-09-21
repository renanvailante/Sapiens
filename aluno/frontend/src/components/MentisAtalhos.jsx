import { useNavigate } from "react-router-dom";
import {
  Compass, ListChecks, Trophy, PlayCircle, PenLine, Brain, Zap, GraduationCap,
  CalendarDays, Sparkles,
} from "lucide-react";
import { ROTAS, ANCORAS, com } from "../lib/rotas";
import { nomeDoDestino } from "../lib/navegacao";

/**
 * Os atalhos da Mentis — a parte NAVEGAÇÃO da camada, separada da parte
 * conversa.
 *
 * Antes, o único jeito de a Mentis levar o aluno a algum lugar era ele gastar
 * Sparks perguntando. Isto aqui é de graça e não chama modelo nenhum: são
 * links. Existe porque a pergunta mais comum de aluno novo não é sobre
 * conteúdo, é "onde fica X" — e cobrar por essa resposta seria cobrar pedágio
 * de menu.
 *
 * Os destinos são os MESMOS que a Mentis pode escolher sozinha no campo
 * `acao.tipo = "ir"` (`mentis_routes.DESTINOS`), na mesma ordem de
 * importância do produto: o mapa primeiro.
 *
 * **O RÓTULO NÃO É ESCRITO AQUI.** Ele sai de `nomeDoDestino`, o vocabulário
 * único do produto. Esta lista chamava `/exams` de "Questões", `/progresso` de
 * "Meu desempenho" e `/agenda` de "Minha semana" — três nomes que não existiam
 * em nenhuma outra superfície, num chip que a Mentis mostra justamente para o
 * aluno novo, que é quem ainda está montando o mapa mental do produto.
 */

export const ATALHOS = [
  { rota: ROTAS.TREINO, icone: Compass },
  { rota: com(ROTAS.HOJE, ANCORAS.HOJE_MISSOES), icone: ListChecks, rotulo: "Missões do dia" },
  { rota: com(ROTAS.PROGRESSO, ANCORAS.PROGRESSO_CONQUISTAS), icone: Trophy },
  { rota: ROTAS.PROVAS, icone: PlayCircle },
  { rota: `${ROTAS.TREINO}?fonte=geradas`, icone: Sparkles },
  { rota: ROTAS.PROGRESSO, icone: Brain },
  { rota: ROTAS.REDACAO, icone: PenLine },
  { rota: ROTAS.AGENDA, icone: CalendarDays },
  { rota: ROTAS.SPARKS, icone: Zap },
  { rota: ROTAS.MENTORIA, icone: GraduationCap },
].map((a) => ({ ...a, rotulo: a.rotulo || nomeDoDestino(a.rota) }));

export default function MentisAtalhos({ compacto = false, limite }) {
  const nav = useNavigate();
  const itens = limite ? ATALHOS.slice(0, limite) : ATALHOS;

  return (
    <div data-testid="mentis-atalhos">
      <div className="mb-2 font-mono-alt text-[10px] uppercase tracking-[0.25em] text-white/30">
        Te levo direto · grátis
      </div>
      <div className="flex flex-wrap gap-1.5">
        {itens.map((a) => (
          <button
            key={a.rota}
            type="button"
            onClick={() => nav(a.rota)}
            className={`inline-flex items-center gap-1.5 rounded-full border border-white/12 bg-white/[0.04] text-white/70 transition hover:border-[#4FD9FF]/40 hover:bg-[#4FD9FF]/10 hover:text-white ${
              compacto ? "px-2.5 py-1.5 text-[11px]" : "px-3.5 py-2 text-xs"
            }`}
            data-testid={`mentis-atalho-${a.rota.replace(/[/#]/g, "-")}`}
          >
            <a.icone className="h-3.5 w-3.5" /> {a.rotulo}
          </button>
        ))}
      </div>
    </div>
  );
}
