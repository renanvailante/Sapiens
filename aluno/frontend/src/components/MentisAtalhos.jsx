import { useNavigate } from "react-router-dom";
import {
  Compass, ListChecks, Trophy, PlayCircle, PenLine, Brain, Zap, GraduationCap,
  CalendarDays, Sparkles,
} from "lucide-react";

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
 */

export const ATALHOS = [
  { rota: "/treino", icone: Compass, rotulo: "Mapa de Treino" },
  { rota: "/dashboard#missoes", icone: ListChecks, rotulo: "Missões" },
  { rota: "/conquistas", icone: Trophy, rotulo: "Conquistas" },
  { rota: "/exams", icone: PlayCircle, rotulo: "Questões" },
  { rota: "/minhas-questoes", icone: Sparkles, rotulo: "Questões que gerei" },
  { rota: "/cognitive-profile", icone: Brain, rotulo: "Meu desempenho" },
  { rota: "/redacao", icone: PenLine, rotulo: "Redação" },
  { rota: "/cronograma", icone: CalendarDays, rotulo: "Minha semana" },
  { rota: "/sparks", icone: Zap, rotulo: "Sparks" },
  { rota: "/mentoria", icone: GraduationCap, rotulo: "Mentoria com a USP" },
];

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
