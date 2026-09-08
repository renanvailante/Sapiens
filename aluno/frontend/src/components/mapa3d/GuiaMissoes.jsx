import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Compass, ChevronLeft, ChevronRight, ChevronDown, Crosshair } from "lucide-react";
import { BIOMA_ARCHETYPES } from "./biomaArchetypes";
import IconeMissao from "./IconeMissao";
import { destravadaPor } from "./progressao";

// Trilha de missões, sobreposta ao mundo. Não é um menu de badges: é o mapa
// da coleção — cada região é uma trilha, as missões aparecem na ordem em que
// se abrem, ligadas por um trilho contínuo, e o que ainda não foi alcançado
// aparece como silhueta sem nome.
//
// Nunca exibe a frase original da habilidade nem o código interno: só o
// rótulo curto e o sigilo (ver missoes.js / glifos.js).

const ANEL_ESTADO = {
  mastered: { anel: 1, preenchido: true },
  in_progress: { anel: 0.75, preenchido: false },
  available: { anel: 0.5, preenchido: false },
};

function Ladrilho({ no, cor, silhueta, selecionado }) {
  const forca = ANEL_ESTADO[no.estado] ?? { anel: 0.28, preenchido: false };
  return (
    <span
      className="relative shrink-0 grid place-items-center rounded-xl transition-colors"
      style={{
        width: 40,
        height: 40,
        background: silhueta ? "rgba(255,255,255,0.03)" : `${cor}14`,
        border: `1px solid ${silhueta ? "rgba(255,255,255,0.08)" : `${cor}${selecionado ? "" : "55"}`}`,
        boxShadow: silhueta ? "none" : `0 0 ${selecionado ? 22 : 12}px -6px ${cor}`,
      }}
    >
      <IconeMissao
        familia={no.familia}
        variante={no.variante}
        cor={silhueta ? "#8FA6C4" : cor}
        opacidade={silhueta ? 0.32 : 0.55 + forca.anel * 0.45}
        tamanho={22}
      />
      {no.estado === "mastered" && (
        <span
          className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full"
          style={{ background: cor, boxShadow: `0 0 8px ${cor}` }}
        />
      )}
    </span>
  );
}

function Linha({ no, cor, primeiro, ultimo, selecionado, onFocar, dependencias }) {
  const silhueta = no.acesso === "entrevisto";
  return (
    <button
      onClick={() => onFocar(no.hab_id)}
      data-testid={`guia-item-${no.hab_id}`}
      className={`relative w-full text-left flex items-center gap-3 pl-6 pr-2 py-1.5 rounded-xl transition-colors ${
        selecionado ? "bg-white/10" : "hover:bg-white/[0.06]"
      }`}
    >
      {/* Trilho: o fio que liga uma missão à seguinte dentro da região. */}
      <span
        className="absolute left-[13px] w-px"
        style={{
          top: primeiro ? "50%" : 0,
          bottom: ultimo ? "50%" : 0,
          background: silhueta
            ? "repeating-linear-gradient(180deg, rgba(255,255,255,0.16) 0 3px, transparent 3px 7px)"
            : `linear-gradient(180deg, ${cor}55, ${cor}22)`,
        }}
      />
      <span
        className="absolute left-[9px] w-2 h-2 rounded-full"
        style={{ background: silhueta ? "rgba(255,255,255,0.2)" : cor, boxShadow: silhueta ? "none" : `0 0 8px ${cor}` }}
      />

      <Ladrilho no={no} cor={cor} silhueta={silhueta} selecionado={selecionado} />

      <span className="min-w-0 flex-1">
        <span className={`block text-[13px] leading-tight ${silhueta ? "text-white/35 italic" : "text-white/90"}`}>
          {silhueta ? "não alcançado" : no.rotulo}
        </span>
        <span className="block mt-0.5 font-mono-alt text-[9.5px] uppercase tracking-[0.16em] text-white/35 truncate">
          {silhueta
            ? dependencias.length
              ? `pratique ${dependencias[0].rotulo}`
              : "adiante na trilha"
            : no.estado === "mastered"
              ? "dominada"
              : no.estado === "in_progress"
                ? "em progresso"
                : "disponível"}
        </span>
      </span>
    </button>
  );
}

function Regiao({ bioma, arestas, biomas, focoAtual, onFocar, aberto, onAlternar }) {
  const cor = BIOMA_ARCHETYPES[bioma.bioma_id]?.paleta.brilho ?? "#4FD9FF";

  // Ordem da trilha: o que já foi praticado primeiro, depois o que está
  // aberto, e por último o que ainda é silhueta — a mesma ordem em que a
  // região se abre para o aluno.
  const ordem = { mastered: 0, in_progress: 1, available: 2, discovered: 3 };
  const visiveis = useMemo(
    () =>
      bioma.nodes
        .filter((n) => n.acesso !== "oculto")
        .sort((a, b) => (ordem[a.estado] ?? 9) - (ordem[b.estado] ?? 9) || a.rotulo.localeCompare(b.rotulo, "pt-BR")),
    [bioma.nodes], // eslint-disable-line react-hooks/exhaustive-deps
  );

  if (!visiveis.length) return null;
  const abertas = visiveis.filter((n) => n.acesso === "acessivel").length;

  return (
    <section className="mb-3">
      {/* A região inteira recolhe: com seis trilhas abertas a lista come a
          tela, e o mapa é que deveria estar ocupando esse espaço. */}
      <button
        onClick={() => onAlternar(bioma.bioma_id)}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/[0.05] transition-colors"
        aria-expanded={aberto}
        data-testid={`guia-regiao-${bioma.bioma_id}`}
      >
        <ChevronDown
          className="w-3 h-3 shrink-0 transition-transform"
          style={{ color: cor, transform: aberto ? "none" : "rotate(-90deg)" }}
        />
        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: cor, boxShadow: `0 0 8px ${cor}` }} />
        <span className="font-mono-alt text-[10px] uppercase tracking-[0.26em]" style={{ color: cor }}>
          {bioma.nome}
        </span>
        <span className="h-px flex-1" style={{ background: `linear-gradient(90deg, ${cor}44, transparent)` }} />
        <span className="font-mono-alt text-[10px] text-white/30 shrink-0">
          {abertas}/{bioma.nodes.length}
        </span>
      </button>

      {/* Renderização condicional direta, sem animação de saída: com
          `AnimatePresence` a saída não completava e a trilha continuava
          ocupando a tela mesmo recolhida — que é justamente o espaço que
          este controle existe para devolver ao mapa. */}
      {aberto && (
          <motion.div
            key="trilha"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="relative"
          >
            {visiveis.map((no, i) => (
              <Linha
                key={no.hab_id}
                no={no}
                cor={cor}
                primeiro={i === 0}
                ultimo={i === visiveis.length - 1}
                selecionado={focoAtual === no.hab_id}
                onFocar={onFocar}
                dependencias={no.acesso === "entrevisto" ? destravadaPor(no.hab_id, biomas, arestas) : []}
              />
            ))}
          </motion.div>
      )}
    </section>
  );
}

export default function GuiaMissoes({ biomas, arestas, focoAtual, onFocar, onLimparFoco }) {
  const [aberto, setAberto] = useState(() => typeof window === "undefined" || window.innerWidth >= 1024);
  const [recolhidas, setRecolhidas] = useState(() => new Set());
  const alternarRegiao = (id) =>
    setRecolhidas((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(id)) proximo.delete(id);
      else proximo.add(id);
      return proximo;
    });

  const total = useMemo(() => biomas.reduce((acc, b) => acc + b.nodes.length, 0), [biomas]);
  const abertas = useMemo(
    () => biomas.reduce((acc, b) => acc + b.nodes.filter((n) => n.acesso === "acessivel").length, 0),
    [biomas],
  );

  return (
    <div className="absolute left-0 top-16 bottom-0 z-30 flex items-stretch pointer-events-none">
      <AnimatePresence initial={false}>
        {aberto && (
          <motion.aside
            key="guia"
            initial={{ x: -360, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -360, opacity: 0 }}
            transition={{ type: "spring", damping: 26, stiffness: 240 }}
            className="card-sapiens pointer-events-auto w-[330px] m-3 rounded-2xl flex flex-col overflow-hidden"
            data-testid="guia-missoes"
          >
            <div className="px-4 pt-4 pb-3 border-b border-white/[0.06]">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-sapiens-accentDeep flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" /> Trilhas
              </div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="font-display text-2xl font-extrabold text-white leading-none">{abertas}</span>
                <span className="text-[11px] text-white/40">de {total} territórios abertos</span>
              </div>
              <div className="mt-2 h-1 rounded-full bg-white/[0.07] overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(abertas / Math.max(total, 1)) * 100}%`,
                    background: "linear-gradient(90deg, #4FD9FF, #A45BFF)",
                  }}
                />
              </div>
              <button
                onClick={onLimparFoco}
                className="mt-2.5 inline-flex items-center gap-1.5 text-[11px] text-white/45 hover:text-white/85 transition-colors"
                data-testid="guia-visao-geral"
              >
                <Crosshair className="w-3 h-3" /> Ver o continente inteiro
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-3">
              {biomas.map((bioma) => (
                <Regiao
                  key={bioma.bioma_id}
                  bioma={bioma}
                  biomas={biomas}
                  arestas={arestas}
                  focoAtual={focoAtual}
                  onFocar={onFocar}
                  aberto={!recolhidas.has(bioma.bioma_id)}
                  onAlternar={alternarRegiao}
                />
              ))}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <button
        onClick={() => setAberto((v) => !v)}
        className="pointer-events-auto self-start mt-3 -ml-1 h-11 w-7 rounded-r-xl bg-white/8 hover:bg-white/16 border border-l-0 border-white/12 text-white/70 flex items-center justify-center transition-colors"
        aria-label={aberto ? "Recolher trilhas" : "Abrir trilhas"}
        data-testid="guia-alternar"
      >
        {aberto ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>
    </div>
  );
}
