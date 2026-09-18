import { Check, Circle, Play, Trophy, Zap, Clock, ShieldCheck, Target } from "lucide-react";
import AnelDeProgresso from "../AnelDeProgresso";
import PassosDaEstacao from "./PassosDaEstacao";

/**
 * O TRILHO — todo o progresso da estação numa coluna só, à direita.
 *
 * Antes, o progresso de uma estação estava espalhado por quatro lugares: um
 * contador no cabeçalho, uma régua de segmentos de 6px no topo, um chip de
 * ganho que aparecia e sumia, e a frase do rodapé dizendo quanto faltava. Cada
 * peça dizia um pedaço, nenhuma dizia o estado — e como todas moravam fora do
 * campo de visão de quem estava respondendo, responder certo não movia nada
 * que o aluno conseguisse ver. Progresso que não se vê é progresso que não
 * existe.
 *
 * Aqui eles são UM objeto, fixo ao lado do conteúdo enquanto a estação rola:
 *
 * 1. **o anel** — acertos sobre o que conclui a estação, que é o único número
 *    capaz de terminar a aula;
 * 2. **as etapas**, uma linha cada, com o que já foi feito em cada uma e um
 *    clique para voltar a qualquer uma já alcançada;
 * 3. **o que esta visita rendeu** em Sparks e XP — e só o que o servidor de
 *    fato creditou;
 * 4. **o estado da estação**: em andamento, concluída ou pulada por domínio.
 *
 * **Não calcula nada.** Os acertos vêm do servidor (é ele quem corrige e quem
 * conclui) e o estado das etapas vem de `lib/etapas`, que é puro e testado. Uma
 * segunda contabilidade aqui divergiria da tela na primeira mudança de regra —
 * e a versão errada é sempre a que o aluno encontra.
 *
 * **Vale para todo curso.** O trilho não sabe o nome de nenhum: recebe etapas,
 * acertos e alvo. Qualquer estação publicada depois — de qualquer curso — cai
 * dentro dele sem uma linha de código nova.
 *
 * No celular não existe canto direito: `compacto` desenha a mesma informação
 * numa faixa acima do conteúdo, com a régua de segmentos no lugar da lista.
 */

const DOT = {
  cumprida: { Icone: Check, classe: "bg-gradient-to-br from-[#4FD9FF] to-[#8B7BFF] text-[#06122B]" },
  atual: { Icone: Play, classe: "bg-white/85 text-[#06122B]" },
  adiante: { Icone: Circle, classe: "bg-white/8 text-white/35" },
};

function estadoDaEstacao({ concluida, pulada, acertos, alvo }) {
  if (pulada) {
    return {
      Icone: ShieldCheck,
      cor: "text-violet-200",
      titulo: "Pulada por domínio",
      texto: "Você provou que já sabia isto. O conteúdo continua aqui para consulta.",
    };
  }
  if (concluida) {
    return {
      Icone: Trophy,
      cor: "text-amber-200",
      titulo: "Estação concluída",
      texto: "Refazer um exercício não tira o que você já concluiu.",
    };
  }
  const faltam = Math.max(0, (alvo || 0) - (acertos || 0));
  return {
    Icone: Target,
    cor: "text-white/80",
    titulo: faltam === 1 ? "Falta 1 acerto" : `Faltam ${faltam} acertos`,
    texto: "Errar não desfaz acerto: cada exercício certo fica contado.",
  };
}

/** Uma linha da lista de etapas. Clicável só onde o aluno já esteve — um
 *  atalho para uma tela que ele ainda não abriu seria um pular disfarçado. */
function LinhaDaEtapa({ passo, atual, alcancavel, aoIr }) {
  const estado = passo.cumprida ? "cumprida" : atual ? "atual" : "adiante";
  const { Icone, classe } = DOT[estado];
  const exercicios = passo.tipo === "exercicios";

  return (
    <li>
      <button
        type="button"
        onClick={() => alcancavel && aoIr?.(passo.indice)}
        disabled={!alcancavel}
        aria-current={atual ? "step" : undefined}
        className={[
          "flex w-full items-center gap-2.5 rounded-2xl px-2 py-2 text-left transition-colors",
          alcancavel ? "hover:bg-white/5" : "cursor-default",
          atual ? "bg-white/5" : "",
        ].join(" ")}
        data-testid={`trilho-etapa-${passo.indice}`}
        data-estado={estado}
      >
        <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${classe}`}>
          <Icone className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1">
          <span
            className={`block truncate text-[13px] font-semibold ${atual ? "text-white" : passo.cumprida ? "text-white/75" : "text-white/40"}`}
          >
            {passo.rotulo}
          </span>
          <span className="mt-0.5 block font-mono-alt text-[10px] uppercase tracking-[0.14em] text-white/30">
            {exercicios
              ? `${passo.feitos}/${passo.total} respondidas${passo.acertos ? ` · ${passo.acertos} certa${passo.acertos === 1 ? "" : "s"}` : ""}`
              : `${passo.feitos}/${passo.total} lidos`}
          </span>
        </span>
      </button>
    </li>
  );
}

function Ganho({ ganho }) {
  if (!ganho || (!ganho.sparks && !ganho.xp)) return null;
  return (
    <div className="mt-4 border-t border-white/8 pt-3" data-testid="trilho-ganho">
      <div className="secao-olho">Nesta visita</div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {ganho.sparks > 0 && (
          <span className="chip border-amber-300/30 bg-amber-400/10 text-amber-200">
            <Zap className="h-3 w-3" /> +{ganho.sparks} Sparks
          </span>
        )}
        {ganho.xp > 0 && (
          <span className="chip border-violet-300/30 bg-violet-400/10 text-violet-200">
            <Trophy className="h-3 w-3" /> +{ganho.xp} XP
          </span>
        )}
      </div>
    </div>
  );
}

export default function TrilhoDeProgresso({
  etapas = [],
  passos = [],
  etapaAtual = 0,
  aoIrParaEtapa,
  acertos = 0,
  alvo = 0,
  ganho = null,
  concluida = false,
  pulada = false,
  duracaoMinutos = null,
  compacto = false,
  className = "",
}) {
  const pct = alvo > 0 ? Math.min(100, Math.round((Math.min(acertos, alvo) / alvo) * 100)) : 0;
  const estado = estadoDaEstacao({ concluida, pulada, acertos, alvo });
  const cumpridas = new Set(passos.filter((p) => p.cumprida).map((p) => p.indice));

  if (compacto) {
    return (
      <section
        className={`superficie rounded-3xl px-4 py-3 ${className}`}
        data-testid="trilho-progresso-compacto"
        aria-label="Seu progresso nesta estação"
      >
        <div className="flex items-center gap-3">
          <AnelDeProgresso valor={pct} tamanho={46} espessura={5}>
            <span className="font-display text-[13px] font-extrabold leading-none text-white tabular-nums">
              {acertos}
            </span>
            <span className="font-mono-alt text-[8px] leading-none text-white/40">de {alvo}</span>
          </AnelDeProgresso>
          <div className="min-w-0 flex-1">
            <PassosDaEstacao etapas={etapas} atual={etapaAtual} cumpridas={cumpridas} />
            <p className="mt-1.5 truncate text-[11px] text-white/45">
              {concluida || pulada ? estado.titulo : `${estado.titulo} para concluir`}
              {ganho && (ganho.sparks > 0 || ganho.xp > 0)
                ? ` · +${ganho.sparks} Sparks · +${ganho.xp} XP`
                : ""}
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <aside
      className={`superficie rounded-3xl p-5 ${className}`}
      data-testid="trilho-progresso"
      aria-label="Seu progresso nesta estação"
    >
      <div className="secao-olho">Seu progresso</div>

      <div className="mt-3 flex items-center gap-4">
        <AnelDeProgresso valor={pct} tamanho={72} espessura={7} testid="trilho-anel">
          <span className="font-display text-lg font-extrabold leading-none text-white tabular-nums">
            {acertos}
          </span>
          <span className="mt-0.5 font-mono-alt text-[9px] uppercase tracking-[0.16em] text-white/40">
            de {alvo}
          </span>
        </AnelDeProgresso>
        <div className="min-w-0">
          <p className={`flex items-center gap-1.5 font-display text-[15px] font-bold tracking-tight ${estado.cor}`}>
            <estado.Icone className="h-4 w-4 shrink-0" />
            {estado.titulo}
          </p>
          <p className="mt-1 text-[12px] leading-snug text-white/45">{estado.texto}</p>
        </div>
      </div>

      {/* A barra some quando não há alvo (estação sem exercício que conte):
          uma barra que nunca enche é enfeite, e enfeite em cima de número é
          o jeito mais rápido de o aluno parar de acreditar no número. */}
      {alvo > 0 && (
        <div className="barra mt-4" data-cheia={acertos >= alvo} aria-hidden="true">
          <i style={{ width: `${pct}%` }} />
        </div>
      )}

      {passos.length > 1 && (
        <>
          <div className="secao-olho mt-5">Etapas</div>
          <ol className="mt-2 space-y-0.5" data-testid="trilho-etapas">
            {passos.map((passo) => (
              <LinhaDaEtapa
                key={passo.indice}
                passo={passo}
                atual={passo.indice === etapaAtual}
                // Já esteve aqui, ou já cumpriu: são as duas formas de uma
                // etapa ser um lugar de VOLTA, e não um atalho para a frente.
                alcancavel={passo.indice <= etapaAtual || passo.cumprida}
                aoIr={aoIrParaEtapa}
              />
            ))}
          </ol>
        </>
      )}

      <Ganho ganho={ganho} />

      {duracaoMinutos ? (
        <p className="mt-4 flex items-center gap-1.5 border-t border-white/8 pt-3 font-mono-alt text-[10px] uppercase tracking-[0.16em] text-white/30">
          <Clock className="h-3 w-3" /> cerca de {duracaoMinutos} min
        </p>
      ) : null}
    </aside>
  );
}
