import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Mentis from "./Mentis";
import { Lightbulb, ArrowRight, X, Repeat, TrendingDown, CalendarClock } from "lucide-react";

/**
 * Professor Invisível (Fase 2) — o momento em que o sistema fala primeiro.
 *
 * Até aqui o aluno precisava DESCOBRIR sozinho que tinha um padrão: o motor já
 * havia detectado, e a informação esperava um clique que talvez nunca viesse.
 * Isto é push sobre uma máquina de pull que já funcionava — o texto vem de
 * `intervencoes.previa()`, montado localmente a partir da intervenção
 * CATALOGADA do erro raiz. Nenhuma chamada de modelo, nenhum Spark.
 *
 * A disciplina de interrupção é o que separa isto de um pop-up, e é imposta no
 * servidor, não aqui: uma intervenção ativa por vez no aluno inteiro, cooldown
 * por par até o reteste, e dispensa contada como sinal. Por isso este painel é
 * INLINE, dentro do feedback da questão — nunca um modal que cobre a tela de
 * quem está no meio de uma prova.
 *
 * Quando a leitura é provisória, ele se apresenta como hipótese, com o mesmo
 * rigor do aviso do perfil. Um "descobrimos por que você erra" sobre anotação
 * não revisada seria transformar hipótese em fato — exatamente o que o portão
 * de crença existe para impedir.
 */

const MOTIVOS = {
  recorrencia: { icone: Repeat, rotulo: "Isto voltou" },
  deterioracao: { icone: TrendingDown, rotulo: "Isto caiu" },
  reteste_falho: { icone: CalendarClock, rotulo: "A revisão não saiu" },
};

export default function ProfessorInvisivel({ gatilho, onFechar }) {
  const nav = useNavigate();
  const [fechado, setFechado] = useState(false);

  if (!gatilho || fechado) return null;

  const motivo = MOTIVOS[gatilho.motivo] || MOTIVOS.recorrencia;
  const Icone = motivo.icone;
  const previa = gatilho.intervencao || {};

  const encerrar = async (rota) => {
    setFechado(true);
    onFechar?.();
    // O servidor é quem libera a vaga única e liga o cooldown. Falha aqui não
    // pode travar o aluno na questão: a vaga expira no próximo reteste de
    // qualquer forma.
    try {
      await api.post(`/revisao/intervencao/${rota}`);
    } catch {
      /* silencioso de propósito */
    }
  };

  return (
    <div
      className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/60 p-5"
      data-testid="professor-invisivel"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Mentis className="w-6 h-6 shrink-0" variante="icone" animada={false} />
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-amber-700">
            <Icone className="mr-1 inline h-3 w-3" />
            {motivo.rotulo}
          </div>
        </div>
        <button
          type="button"
          onClick={() => encerrar("dispensar")}
          className="shrink-0 rounded-full p-1 text-zinc-400 transition hover:bg-white hover:text-zinc-600"
          aria-label="Não é isso"
          data-testid="professor-invisivel-dispensar"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-2 font-display text-lg font-bold leading-snug tracking-tight text-zinc-950">
        {gatilho.processo_nome}
      </div>
      <p className="mt-1 text-sm leading-relaxed text-zinc-600">{gatilho.explicacao}</p>

      {previa.objetivo && (
        <div className="mt-4 rounded-xl border border-amber-100 bg-white/70 p-4">
          <div className="flex items-center gap-1.5 font-mono-alt text-[10px] font-bold uppercase tracking-wide text-amber-700">
            <Lightbulb className="h-3.5 w-3.5" /> O que treinar
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-zinc-700">{previa.objetivo}</p>
          {previa.como_praticar?.length > 0 && (
            <ol className="mt-3 space-y-1.5">
              {previa.como_praticar.slice(0, 3).map((p, i) => (
                <li key={i} className="flex gap-2 text-sm text-zinc-600">
                  <span className="font-mono-alt shrink-0 text-sapiens-accentDeep">{i + 1}.</span>
                  <span>{p}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {gatilho.aviso && (
        <p className="mt-3 text-xs leading-relaxed text-amber-800" data-testid="professor-invisivel-aviso">
          {gatilho.aviso}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => {
            encerrar("concluir");
            nav("/revisoes");
          }}
          className="pill btn-sapiens inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium"
          data-testid="professor-invisivel-trabalhar"
        >
          Trabalhar isto <ArrowRight className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => encerrar("dispensar")}
          className="pill inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-4 py-2 text-xs font-medium text-zinc-600 hover:border-zinc-300"
          data-testid="professor-invisivel-nao-e-isso"
        >
          Não é isso
        </button>
      </div>
    </div>
  );
}
