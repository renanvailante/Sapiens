import { TrendingUp, Target, Info, Lightbulb } from "lucide-react";

// Peças visuais do diagnóstico real (nomes reais, amostra mínima declarada),
// compartilhadas entre a visão do próprio aluno (`pages/Diagnostico.jsx`) e a
// visão de admin (`pages/StudentHistory.jsx`) — mesma ferramenta, dois
// lugares, sem duplicar a lógica de apresentação.

export const NIVEL_LABEL = { por_dominio: "Domínio", por_competencia: "Competência", por_processo: "Processo cognitivo" };

export function RankingColuna({ titulo, nivel, dados }) {
  const fortes = dados?.fortes || [];
  const fracos = dados?.fracos || [];
  if (fortes.length === 0 && fracos.length === 0) return null;
  return (
    <div className="card-sapiens rounded-2xl p-5 md:p-6">
      <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400 mb-3">{titulo}</div>
      <div className="space-y-4">
        {fortes.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-emerald-700 mb-1.5">
              <TrendingUp className="w-3.5 h-3.5" /> Pontos fortes
            </div>
            <div className="space-y-1.5">
              {fortes.map((p) => (
                <div key={p.id} className="flex items-center justify-between gap-3 text-sm bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2" data-testid={`diag-forte-${nivel}-${p.id}`}>
                  <span className="text-zinc-700 min-w-0 truncate">{p.nome}</span>
                  <span className="font-mono-alt font-bold text-emerald-700 shrink-0">{p.percentual_acerto}% <span className="text-emerald-500 font-normal">({p.respondidas}q)</span></span>
                </div>
              ))}
            </div>
          </div>
        )}
        {fracos.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-rose-700 mb-1.5">
              <Target className="w-3.5 h-3.5" /> Pontos de atenção
            </div>
            <div className="space-y-1.5">
              {fracos.map((p) => (
                <div key={p.id} className="flex items-center justify-between gap-3 text-sm bg-rose-50 border border-rose-100 rounded-lg px-3 py-2" data-testid={`diag-fraco-${nivel}-${p.id}`}>
                  <span className="text-zinc-700 min-w-0 truncate">{p.nome}</span>
                  <span className="font-mono-alt font-bold text-rose-700 shrink-0">{p.percentual_acerto}% <span className="text-rose-500 font-normal">({p.respondidas}q)</span></span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function PadraoCard({ padrao }) {
  return (
    <div className="card-sapiens rounded-2xl p-5 md:p-6" data-testid={`diag-padrao-${padrao.processo_id}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">Processo com desempenho fraco</div>
          <div className="font-display font-bold text-lg text-zinc-950">{padrao.processo_nome}</div>
          <div className="text-xs text-zinc-500 mt-0.5">{padrao.percentual_acerto}% de acerto em {padrao.respondidas} questões respondidas</div>
        </div>
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-amber-800 bg-amber-100 border border-amber-200 rounded-full px-2.5 py-1 shrink-0">
          <Info className="w-3 h-3" /> fato do catálogo, não um veredito sobre você
        </span>
      </div>
      <div className="mt-4 pt-4 border-t border-zinc-100">
        <div className="text-xs font-bold uppercase tracking-wide text-zinc-500 mb-1">Erro comumente associado a este processo</div>
        <div className="text-sm font-semibold text-zinc-800">{padrao.erro_nome}</div>
        {padrao.erro_evidencia_observavel && (
          <div className="text-sm text-zinc-500 mt-1">{padrao.erro_evidencia_observavel}</div>
        )}
      </div>
      {padrao.intervencao_nome && (
        <div className="mt-3 flex items-start gap-2 text-sm bg-sky-50 border border-sky-100 rounded-lg px-3 py-2.5">
          <Lightbulb className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-sky-800">Abordagem sugerida:</span>{" "}
            <span className="text-sky-700">{padrao.intervencao_nome}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function RankingsPorNivel({ data }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <RankingColuna titulo={NIVEL_LABEL.por_dominio} nivel="dominio" dados={data?.por_dominio} />
      <RankingColuna titulo={NIVEL_LABEL.por_competencia} nivel="competencia" dados={data?.por_competencia} />
      <RankingColuna titulo={NIVEL_LABEL.por_processo} nivel="processo" dados={data?.por_processo} />
    </div>
  );
}

export function semDadosReais(data) {
  return (
    (data?.por_dominio?.fortes?.length || 0) === 0 &&
    (data?.por_dominio?.fracos?.length || 0) === 0 &&
    (data?.por_competencia?.fortes?.length || 0) === 0 &&
    (data?.por_competencia?.fracos?.length || 0) === 0 &&
    (data?.por_processo?.fortes?.length || 0) === 0 &&
    (data?.por_processo?.fracos?.length || 0) === 0
  );
}
