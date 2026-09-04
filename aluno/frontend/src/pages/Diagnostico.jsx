import { useEffect, useState } from "react";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Stethoscope } from "lucide-react";
import { RankingsPorNivel, PadraoCard, semDadosReais } from "../components/PerfilCognitivoView";

// Diagnóstico real: diferente do Mapa de Habilidades (/cognitive-profile,
// cosmético e gamificado por decisão de produto — nomes genéricos, custa
// Sparks), esta página mostra nome real de domínio/competência/processo e só
// afirma um ponto fraco/forte quando há amostra suficiente (`amostra_minima`
// vinda do backend). Gratuita: é leitura/agregação, não geração de conteúdo.
//
// "Padrões associados" NÃO é uma atribuição de causa ao aluno — é um fato
// geral do catálogo pedagógico (Ontologia Sapiens) aplicado a um processo
// onde o desempenho medido do aluno é fraco. O rótulo de cada card deixa
// isso explícito; ver `annotation_service.compute_diagnostico_real` no
// backend para a regra completa (só aparece quando o processo tem EXATAMENTE
// um tipo de erro catalogado — nunca por chute entre vários).
//
// Os componentes visuais (`RankingsPorNivel`, `PadraoCard`) são compartilhados
// com a visão de admin em `pages/StudentHistory.jsx` — mesma ferramenta, duas
// telas, sem duplicar a lógica de apresentação.

export default function Diagnostico() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const load = () => {
    setLoading(true);
    setLoadError(null);
    api
      .get("/diagnostico")
      .then((res) => setData(res.data))
      .catch((e) => setLoadError(errMsg(e, "Não foi possível carregar o diagnóstico agora.")))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) {
    return (
      <div>
        <Nav />
        <div className="p-10 text-white/60">Calculando diagnóstico...</div>
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div>
        <Nav />
        <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
          <div className="text-white/60" data-testid="diag-load-error">{loadError || "Não foi possível carregar o diagnóstico agora."}</div>
          <button onClick={load} className="pill mt-4 text-sm font-medium btn-sapiens px-4 py-2 rounded-full" data-testid="diag-retry-btn">
            Tentar de novo
          </button>
        </div>
      </div>
    );
  }

  const semDados = semDadosReais(data);

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3 flex items-center gap-2">
          <Stethoscope className="w-3.5 h-3.5" /> Diagnóstico real
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="diag-title">
          O que os seus erros revelam.
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Nomes reais, dados reais: desempenho medido por domínio, competência e processo cognitivo, calculado só a
          partir das questões que você já respondeu — sem IA, sem inventar padrão a partir de uma questão isolada.
        </p>

        <div className="mt-6 card-sapiens rounded-2xl p-4 md:p-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm" data-testid="diag-metadata">
          <div>
            <span className="text-zinc-400">Questões analisadas:</span>{" "}
            <span className="font-mono-alt font-bold text-zinc-800">{data.matched_events}</span>
            {data.unmatched_events > 0 && (
              <span className="text-zinc-400"> ({data.unmatched_events} sem anotação cognitiva ainda)</span>
            )}
          </div>
          <div>
            <span className="text-zinc-400">Cobertura:</span>{" "}
            <span className="font-mono-alt font-bold text-zinc-800">{data.coverage}%</span>
          </div>
          <div>
            <span className="text-zinc-400">Amostra mínima por item:</span>{" "}
            <span className="font-mono-alt font-bold text-zinc-800">{data.amostra_minima} questões</span>
          </div>
        </div>

        {semDados ? (
          <div className="mt-6 card-sapiens rounded-2xl p-6 text-center" data-testid="diag-vazio">
            <div className="font-display font-bold text-lg text-zinc-950">Ainda não há diagnóstico suficiente.</div>
            <p className="mt-2 text-sm text-zinc-500 max-w-md mx-auto">
              Responda mais questões praticando — a partir de {data.amostra_minima} respostas num mesmo processo
              cognitivo, o desempenho real começa a aparecer aqui.
            </p>
          </div>
        ) : (
          <>
            <div className="mt-6">
              <RankingsPorNivel data={data} />
            </div>

            {data.padroes_associados?.length > 0 && (
              <div className="mt-8">
                <h2 className="font-display font-bold text-2xl text-white tracking-tight">Onde focar agora</h2>
                <p className="mt-1 text-sm text-white/50 max-w-xl">
                  Processos com desempenho real fraco, cruzados com o catálogo pedagógico da Sapiens — só quando há
                  exatamente um tipo de erro catalogado para aquele processo, nunca por suposição.
                </p>
                <div className="mt-4 space-y-4">
                  {data.padroes_associados.map((p) => (
                    <PadraoCard key={p.processo_id} padrao={p} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        <div className="mt-8 text-[11px] text-white/30 max-w-xl">
          Metodologia: nenhum ponto forte ou fraco é declarado com menos de {data.amostra_minima} respostas no mesmo
          nó. "Onde focar agora" não afirma que você cometeu um erro específico — mostra um fato geral do catálogo
          pedagógico associado a um processo onde seu desempenho medido é fraco.
        </div>
      </div>
    </div>
  );
}
