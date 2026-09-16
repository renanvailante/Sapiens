import { useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { ArrowRight, Lock, Check, X } from "lucide-react";
import { avaliarConquistas, GRUPOS } from "../lib/conquistas";

/**
 * As conquistas, clicáveis.
 *
 * Eram 22 pílulas de texto no fim do Painel, e a única informação que
 * carregavam era "acesa" ou "apagada" — um selo cinza que não diz quanto
 * falta nem o que fazer é enfeite, não objetivo. Agora cada uma é um alvo:
 * abre com o progresso real, a condição exata e o botão que leva ao lugar
 * onde ela é conquistada.
 *
 * Nenhuma conta nova: tudo vem de `lib/conquistas.js`, que computa a partir
 * dos mesmos dados que o Painel já carregou.
 */

function Medalha({ c, aoAbrir }) {
  const Icone = c.icon;
  return (
    <button
      type="button"
      onClick={() => aoAbrir(c)}
      className={[
        "macio group relative flex aspect-square flex-col items-center justify-center gap-1.5 border p-2 text-center",
        c.desbloqueada
          ? "medalha-viva border-sapiens-accent/40"
          : "border-white/10 bg-white/[0.03] hover:border-white/25 hover:bg-white/[0.06]",
      ].join(" ")}
      data-testid={`conquista-${c.id}`}
      data-unlocked={c.desbloqueada}
      title={c.label}
    >
      <Icone
        className={`h-5 w-5 shrink-0 ${c.desbloqueada ? "text-[#7FD8FF]" : "text-white/30"}`}
        strokeWidth={1.7}
      />
      <span
        className={`line-clamp-2 text-[10px] leading-tight ${
          c.desbloqueada ? "text-white/85" : "text-white/40"
        }`}
      >
        {c.label}
      </span>
      {/* A barra de progresso substitui o "apagado" binário: mesmo travada,
          a medalha diz o quão perto está. */}
      {!c.desbloqueada && c.percentual > 0 && (
        <span className="absolute inset-x-2.5 bottom-1.5 h-[3px] overflow-hidden rounded-full bg-white/10">
          <span
            className="block h-full rounded-full bg-gradient-to-r from-[#4FD9FF] to-[#8B7BFF]"
            style={{ width: `${c.percentual}%` }}
          />
        </span>
      )}
      {c.desbloqueada && (
        <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-[#4FD9FF] text-[#03060d]">
          <Check className="h-2.5 w-2.5" strokeWidth={3} />
        </span>
      )}
    </button>
  );
}

function Detalhe({ c, aoFechar }) {
  const Icone = c.icon;
  return createPortal(
    <div
      className="fixed inset-0 z-[60] flex items-end justify-center bg-black/70 p-0 sm:items-center sm:p-4"
      onClick={aoFechar}
      data-testid="conquista-detalhe"
    >
      <div
        className="w-full max-w-sm rounded-t-3xl border border-white/12 bg-[#0a1526] p-6 shadow-2xl sm:rounded-3xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-4">
          <div
            className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-[20px] border ${
              c.desbloqueada
                ? "medalha-viva border-sapiens-accent/40"
                : "border-white/10 bg-white/5"
            }`}
          >
            <Icone
              className={`h-7 w-7 ${c.desbloqueada ? "text-[#7FD8FF]" : "text-white/35"}`}
              strokeWidth={1.6}
            />
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-white/40">
              {c.grupo}
            </div>
            <h3 className="mt-1 font-display text-xl font-bold leading-tight tracking-tight text-white">
              {c.label}
            </h3>
          </div>
          <button
            type="button"
            onClick={aoFechar}
            className="-m-1 rounded-full p-1.5 text-white/40 hover:bg-white/10 hover:text-white"
            aria-label="Fechar"
            data-testid="conquista-detalhe-fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-4 text-sm leading-relaxed text-white/65">{c.descricao}</p>

        <div className="mt-5">
          <div className="flex items-baseline justify-between gap-2 text-xs">
            <span className="text-white/45">Para desbloquear: {c.condicao}</span>
            <span className="font-mono-alt font-bold text-white/85" data-testid="conquista-progresso">
              {Math.min(c.atual, c.alvo)}/{c.alvo}
            </span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#4FD9FF] to-[#8B7BFF] transition-[width] duration-500"
              style={{ width: `${c.percentual}%` }}
            />
          </div>
        </div>

        {c.desbloqueada ? (
          <p className="mt-4 inline-flex items-center gap-1.5 text-sm text-emerald-300">
            <Check className="h-4 w-4" /> Conquistada.
          </p>
        ) : (
          <p className="mt-4 inline-flex items-center gap-1.5 text-xs text-white/40">
            <Lock className="h-3.5 w-3.5" /> Faltam {c.alvo - c.atual} {c.unidade}.
          </p>
        )}

        <Link
          to={c.rota}
          onClick={aoFechar}
          className="pill btn-sapiens mt-5 inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium"
          data-testid="conquista-detalhe-cta"
        >
          {c.rotuloRota} <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>,
    document.body,
  );
}

/**
 * `limite` corta a grade (o Painel mostra as mais próximas de sair; a página
 * `/conquistas` mostra tudo agrupado). Sem `limite`, vem inteiro.
 */
export default function PainelDeConquistas({ contexto, limite, agrupado = false, testid = "conquistas" }) {
  const [aberta, setAberta] = useState(null);
  const todas = avaliarConquistas(contexto);
  const conquistadas = todas.filter((c) => c.desbloqueada);

  // Ordem do Painel: as conquistadas primeiro (são a prova), depois as mais
  // PERTO de sair — é a lista que faz o aluno querer voltar, e não a ordem
  // arbitrária do catálogo.
  const emOrdem = [...todas].sort((a, b) => {
    if (a.desbloqueada !== b.desbloqueada) return a.desbloqueada ? -1 : 1;
    return b.percentual - a.percentual;
  });
  const visiveis = limite ? emOrdem.slice(0, limite) : emOrdem;

  return (
    <div data-testid={testid}>
      {agrupado ? (
        GRUPOS.map((grupo) => {
          const doGrupo = todas.filter((c) => c.grupo === grupo);
          if (!doGrupo.length) return null;
          return (
            <section key={grupo} className="mb-8">
              <div className="mb-3 flex items-baseline justify-between gap-3">
                <h2 className="font-display text-lg font-bold tracking-tight text-white">{grupo}</h2>
                <span className="font-mono-alt text-[11px] text-white/35">
                  {doGrupo.filter((c) => c.desbloqueada).length}/{doGrupo.length}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-5 lg:grid-cols-6">
                {doGrupo.map((c) => (
                  <Medalha key={c.id} c={c} aoAbrir={setAberta} />
                ))}
              </div>
            </section>
          );
        })
      ) : (
        <div className="grid grid-cols-4 gap-2.5 sm:grid-cols-6 lg:grid-cols-8">
          {visiveis.map((c) => (
            <Medalha key={c.id} c={c} aoAbrir={setAberta} />
          ))}
        </div>
      )}

      {aberta && <Detalhe c={todas.find((c) => c.id === aberta.id)} aoFechar={() => setAberta(null)} />}

      {/* Devolvido para quem quiser mostrar o contador sem recalcular. */}
      <span className="hidden" data-testid={`${testid}-contagem`}>
        {conquistadas.length}/{todas.length}
      </span>
    </div>
  );
}
