import { useState } from "react";
import { useNavigate } from "react-router-dom";
import MentisPedido from "./MentisPedido";
import Mentis from "./Mentis";
import { ArrowRight, Target, Compass } from "lucide-react";

/**
 * Card de dificuldade — a unidade visual de "aqui você tem espaço para
 * melhorar", em qualquer tela.
 *
 * Regra de produto (2026-09-09): **nenhum card de erro é um beco sem saída**.
 * Todo card que aponta uma falha tem de levar a um dos dois lugares onde ela
 * pode virar estudo:
 *
 *  1. uma missão específica do Treino (`/treino?hab=HAB-xx`, o mesmo
 *     deep-link que o mapa já aceita) ou a prática filtrada por área; ou
 *  2. um pedido à Mentis, com a mensagem já escrita sobre ESTE ponto — que
 *     nunca é enviado sozinho (ver `MentisPedido`).
 *
 * O card inteiro é clicável e vai para o destino principal: a missão quando
 * existe uma, o pedido à Mentis quando não existe. Os dois botões do rodapé
 * continuam ali para quem quer o outro caminho.
 */
export default function CardDeMelhora({
  titulo,
  descricao,
  rotuloTopo = "Ponto de atenção",
  medida,
  medidaLabel,
  treino,          // { href, rotulo } — opcional
  assunto,         // o que a Mentis recebe como assunto; cai no título
  evidencia,       // frase curta de medida ("42% de acerto em 30 questões")
  pedidos,         // sobrescreve os dois pedidos padrão, se a tela quiser
  onSaldo,
  children,        // conteúdo extra dentro do card (ex.: a intervenção da Mentis)
  testid = "card-melhora",
}) {
  const nav = useNavigate();
  const [pedindo, setPedindo] = useState(false);

  const irParaTreino = () => nav(treino.href);
  const abrirPedido = () => setPedindo(true);
  const principal = treino?.href ? irParaTreino : abrirPedido;

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={principal}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); principal(); } }}
        className="lift card-sapiens group cursor-pointer rounded-2xl p-5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-sapiens-accent"
        data-testid={testid}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 font-mono-alt text-[10px] uppercase tracking-[0.25em] text-amber-700">
              <Target className="w-3 h-3" /> {rotuloTopo}
            </div>
            <div className="mt-1.5 font-display font-bold text-lg leading-snug text-zinc-950">{titulo}</div>
            {descricao && <p className="mt-1 text-sm leading-relaxed text-zinc-600">{descricao}</p>}
          </div>
          {medida != null && (
            <div className="shrink-0 text-right">
              <div className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{medida}</div>
              {medidaLabel && <div className="text-[10px] uppercase tracking-wide text-zinc-400">{medidaLabel}</div>}
            </div>
          )}
        </div>

        {children && (
          // Clique dentro do conteúdo extra é dele, nunca do card: quem abre
          // uma intervenção paga não pode ser levado embora da tela por isso.
          <div className="mt-4" onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
            {children}
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {treino?.href && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); irParaTreino(); }}
              className="pill btn-sapiens inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium"
              data-testid={`${testid}-treinar`}
            >
              <Compass className="w-3.5 h-3.5" /> {treino.rotulo || "Treinar isto"}
            </button>
          )}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); abrirPedido(); }}
            className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-sapiens-navy hover:border-sapiens-accent"
            data-testid={`${testid}-mentis`}
          >
            <Mentis className="w-4 h-4" variante="icone" animada={false} /> Pedir à Mentis
          </button>
          <ArrowRight className="ml-auto w-4 h-4 text-zinc-400 transition-transform group-hover:translate-x-0.5" />
        </div>
      </div>

      {pedindo && (
        <MentisPedido
          aberto={pedindo}
          onFechar={() => setPedindo(false)}
          assunto={assunto || titulo}
          evidencia={evidencia}
          pedidos={pedidos}
          onSaldo={onSaldo}
          testid={`${testid}-pedido`}
        />
      )}
    </>
  );
}
