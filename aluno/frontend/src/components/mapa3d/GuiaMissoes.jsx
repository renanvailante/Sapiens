import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Compass, Lock, ChevronLeft, ChevronRight, Crosshair } from "lucide-react";
import { BIOMA_ARCHETYPES } from "./biomaArchetypes";

// Índice das missões, sobreposto ao mundo. Existe porque um continente
// grande o bastante para valer a pena explorar é grande o bastante para se
// perder dentro dele: o mapa continua sendo o assunto, e a lista é o sumário.
//
// "Trancada" aqui é LEITURA, não trava: o backend nunca bloqueou nada (o
// estado vem de distância no grafo, nunca de cadeado). O que a lista mostra
// é a mesma regra que a paisagem já conta — uma rota de pré-requisito fica
// interrompida no meio do caminho enquanto a habilidade de origem não estiver
// dominada. Clicar numa missão trancada continua levando a câmera até ela.

const ORDEM_ESTADO = { mastered: 0, in_progress: 1, available: 2, discovered: 3 };

function classificar(biomas, arestas) {
  const porId = {};
  for (const bioma of biomas) {
    for (const n of bioma.nodes) porId[n.hab_id] = { ...n, bioma };
  }

  // Pré-requisito ainda não dominado é o que tranca — a mesma condição que
  // interrompe a rota no mundo 3D.
  const dependencias = {};
  for (const a of arestas) {
    if (a.relation !== "prerequisito") continue;
    const fonte = porId[a.source];
    if (!fonte || fonte.estado === "mastered") continue;
    (dependencias[a.target] ??= []).push(fonte);
  }

  const grupos = { andamento: [], disponiveis: [], trancadas: [] };
  for (const no of Object.values(porId)) {
    if (no.estado === "unknown") continue; // ainda não revelado no mapa
    const presas = dependencias[no.hab_id];
    if (presas?.length) grupos.trancadas.push({ ...no, presas });
    else if (no.estado === "mastered" || no.estado === "in_progress") grupos.andamento.push(no);
    else grupos.disponiveis.push(no);
  }

  const ordenar = (lista) =>
    lista.sort(
      (a, b) =>
        (ORDEM_ESTADO[a.estado] ?? 9) - (ORDEM_ESTADO[b.estado] ?? 9) ||
        a.nome.localeCompare(b.nome, "pt-BR"),
    );
  return {
    andamento: ordenar(grupos.andamento),
    disponiveis: ordenar(grupos.disponiveis),
    trancadas: ordenar(grupos.trancadas),
  };
}

function Item({ no, focado, onFocar, trancada }) {
  const cor = BIOMA_ARCHETYPES[no.bioma.bioma_id]?.paleta.brilho ?? "#4FD9FF";
  return (
    <button
      onClick={() => onFocar(no.hab_id)}
      data-testid={`guia-item-${no.hab_id}`}
      className={`w-full text-left rounded-xl px-3 py-2.5 transition-colors border ${
        focado ? "bg-white/12 border-white/25" : "bg-white/[0.04] border-transparent hover:bg-white/[0.09]"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <span
          className="mt-1.5 w-2 h-2 rounded-full shrink-0"
          style={{ background: cor, boxShadow: trancada ? "none" : `0 0 10px ${cor}`, opacity: trancada ? 0.4 : 1 }}
        />
        <div className="min-w-0 flex-1">
          <div className={`text-[13px] leading-snug ${trancada ? "text-white/45" : "text-white/90"}`}>
            {no.nome}
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-[10px] font-mono-alt uppercase tracking-wider text-white/35">
            {no.bioma.nome}
            {trancada && (
              <>
                <Lock className="w-2.5 h-2.5" />
                {no.presas.some((p) => p.estado === "unknown")
                  ? "depende do que ainda não foi descoberto"
                  : `depende de ${no.presas[0].nome.toLowerCase()}`}
              </>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

function Secao({ titulo, cor, itens, focoAtual, onFocar, trancada = false }) {
  if (!itens.length) return null;
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 px-1 mb-1.5">
        <span className="h-px flex-1" style={{ background: `linear-gradient(90deg, ${cor}, transparent)` }} />
        <span className="font-mono-alt text-[10px] uppercase tracking-[0.24em]" style={{ color: cor }}>
          {titulo} · {itens.length}
        </span>
      </div>
      <div className="space-y-1">
        {itens.map((no) => (
          <Item key={no.hab_id} no={no} focado={focoAtual === no.hab_id} onFocar={onFocar} trancada={trancada} />
        ))}
      </div>
    </div>
  );
}

export default function GuiaMissoes({ biomas, arestas, focoAtual, onFocar, onLimparFoco }) {
  const [aberto, setAberto] = useState(() => typeof window === "undefined" || window.innerWidth >= 1024);
  const grupos = useMemo(() => classificar(biomas, arestas), [biomas, arestas]);

  return (
    <div className="absolute left-0 top-16 bottom-0 z-30 flex items-stretch pointer-events-none">
      <AnimatePresence initial={false}>
        {aberto && (
          <motion.aside
            key="guia"
            initial={{ x: -340, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -340, opacity: 0 }}
            transition={{ type: "spring", damping: 26, stiffness: 240 }}
            className="card-sapiens pointer-events-auto w-[320px] m-3 rounded-2xl flex flex-col overflow-hidden"
            data-testid="guia-missoes"
          >
            <div className="px-4 pt-4 pb-3">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-sapiens-accentDeep flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" /> Guia de missões
              </div>
              <button
                onClick={onLimparFoco}
                className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-white/50 hover:text-white/85 transition-colors"
                data-testid="guia-visao-geral"
              >
                <Crosshair className="w-3 h-3" /> Ver o continente inteiro
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-3 pb-4">
              <Secao titulo="Disponíveis" cor="#4FD9FF" itens={grupos.disponiveis} focoAtual={focoAtual} onFocar={onFocar} />
              <Secao titulo="Em andamento" cor="#35E0D8" itens={grupos.andamento} focoAtual={focoAtual} onFocar={onFocar} />
              <Secao titulo="Trancadas" cor="#A45BFF" itens={grupos.trancadas} focoAtual={focoAtual} onFocar={onFocar} trancada />
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <button
        onClick={() => setAberto((v) => !v)}
        className="pointer-events-auto self-start mt-3 -ml-1 h-11 w-7 rounded-r-xl bg-white/8 hover:bg-white/16 border border-l-0 border-white/12 text-white/70 flex items-center justify-center transition-colors"
        aria-label={aberto ? "Recolher guia de missões" : "Abrir guia de missões"}
        data-testid="guia-alternar"
      >
        {aberto ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>
    </div>
  );
}
