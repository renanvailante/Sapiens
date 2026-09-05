import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import { Crosshair, ChevronDown, ChevronRight, Lightbulb, ShieldAlert, ArrowDown, BookOpen, Loader2 } from "lucide-react";

// Motor Cognitivo — a fila do que melhorar, cada linha clicável, cada plano
// saído do Error Trace do próprio aluno (`/api/motor/*`).
//
// Diferente das outras duas telas cognitivas, de propósito:
// - /cognitive-profile: gamificação, nomes genéricos, custa Sparks.
// - /diagnostico: desempenho medido + fato geral do catálogo; não explica o
//   erro de ninguém.
// - esta: explica o erro CONCRETO (cadeia raiz -> consequência, tirada da
//   alternativa que o aluno marcou) e prescreve a intervenção catalogada
//   para a RAIZ. Gratuita: é agregação, não geração — nenhuma IA envolvida.
//
// A distinção raiz/consequência não é enfeite visual: tratar a manifestação
// de superfície na intervenção é pedagogicamente ineficaz, e é por isso que
// só a raiz aparece com intervenção.

const ORIGEM = {
  error_trace: {
    chip: "causa identificada",
    classe: "text-sky-800 bg-sky-100 border-sky-200",
  },
  desempenho: {
    chip: "só desempenho medido",
    classe: "text-zinc-600 bg-zinc-100 border-zinc-200",
  },
};

function Chip({ children, className = "" }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide border rounded-full px-2.5 py-1 ${className}`}>
      {children}
    </span>
  );
}

function Cadeia({ elos }) {
  return (
    <div className="space-y-1.5">
      {elos.map((e, i) => (
        <div key={e.ordem} className="flex items-start gap-2">
          <div className="shrink-0 pt-0.5">
            {i === 0 ? (
              <Chip className="text-rose-800 bg-rose-100 border-rose-200">raiz</Chip>
            ) : (
              <Chip className="text-zinc-500 bg-zinc-100 border-zinc-200">consequência</Chip>
            )}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-zinc-800">{e.erro_nome}</div>
            <div className="text-xs text-zinc-500">
              em {e.processo_nome} · confiança {e.confianca}
            </div>
          </div>
        </div>
      ))}
      {elos.length > 1 && (
        <div className="text-[11px] text-zinc-400 flex items-center gap-1 pt-1">
          <ArrowDown className="w-3 h-3" /> a intervenção trata a raiz, não a consequência
        </div>
      )}
    </div>
  );
}

function ItemRef({ item }) {
  if (!item) return null;
  const partes = [item.banca, item.ano, item.prova, item.numero ? `nº ${item.numero}` : null].filter(Boolean);
  return (
    <span className="font-mono-alt text-[11px] text-zinc-400">
      {partes.join(" · ")}
      {item.tema ? ` — ${item.tema}` : ""}
    </span>
  );
}

function Detalhe({ dados }) {
  const iv = dados.intervencao;
  const raizes = dados.evidencia?.como_raiz || [];
  const praticar = iv?.praticar?.itens || [];

  return (
    <div className="mt-4 pt-4 border-t border-zinc-100 space-y-5">
      {raizes.length > 0 && (
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-zinc-500 mb-2">
            O que aconteceu nas suas respostas
          </div>
          <div className="space-y-3">
            {raizes.slice(0, 4).map((t) => (
              <div key={t.trace_id} className="rounded-xl bg-zinc-50 border border-zinc-100 p-3">
                <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
                  <ItemRef item={t.item} />
                  <span className="font-mono-alt text-[11px] text-zinc-400">
                    você marcou {t.alternativa_escolhida}
                  </span>
                </div>
                <Cadeia elos={t.cadeia} />
                {t.porque_essa_alternativa_engana && (
                  <div className="mt-2 text-xs text-zinc-600 border-l-2 border-zinc-200 pl-2.5">
                    {t.porque_essa_alternativa_engana}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {iv && (
        <div className="rounded-xl bg-sky-50 border border-sky-100 p-4">
          <div className="flex items-center gap-2 mb-1.5">
            <Lightbulb className="w-4 h-4 text-sky-600 shrink-0" />
            <span className="font-display font-bold text-sky-900">
              {iv.intervencao_nome || "Prática dirigida"}
            </span>
            {iv.intervencao_id && (
              <span className="font-mono-alt text-[10px] text-sky-500">{iv.intervencao_id}</span>
            )}
          </div>
          <p className="text-sm text-sky-800">{iv.objetivo}</p>
          <ol className="mt-3 space-y-1.5">
            {(iv.como_praticar || []).map((passo, i) => (
              <li key={i} className="flex gap-2 text-sm text-sky-900">
                <span className="font-mono-alt text-sky-400 shrink-0">{i + 1}.</span>
                <span>{passo}</span>
              </li>
            ))}
          </ol>
          {iv.sinal_de_progresso && (
            <div className="mt-3 pt-3 border-t border-sky-100 text-xs text-sky-700">
              <span className="font-semibold">Você vai saber que melhorou quando:</span> {iv.sinal_de_progresso}
            </div>
          )}

          {(iv.acoes_do_seu_historico || []).length > 0 && (
            <div className="mt-4 pt-3 border-t border-sky-100">
              <div className="text-xs font-bold uppercase tracking-wide text-sky-700 mb-2">
                Aplicado às suas questões
              </div>
              <div className="space-y-2">
                {iv.acoes_do_seu_historico.map((a, i) => (
                  <div key={i} className="text-sm text-sky-900">
                    <ItemRef item={a.item} />
                    <div>{a.acao}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {(iv?.resolucoes_do_seu_historico || []).length > 0 && (
        <details className="rounded-xl border border-zinc-100 bg-white p-3">
          <summary className="cursor-pointer text-sm font-semibold text-zinc-700">
            Ver a resolução das questões que você errou
          </summary>
          <div className="mt-3 space-y-4">
            {iv.resolucoes_do_seu_historico.map((r, i) => (
              <div key={i}>
                <ItemRef item={r.item} />
                <ol className="mt-1.5 space-y-1">
                  {r.passos.map((p, j) => (
                    <li key={j} className="flex gap-2 text-sm text-zinc-700">
                      <span className="font-mono-alt text-zinc-400 shrink-0">{j + 1}.</span>
                      <span>{p}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </details>
      )}

      {praticar.length > 0 && (
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-zinc-500 mb-2 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5" /> Praticar esta habilidade
          </div>
          <div className="flex flex-wrap gap-2">
            {praticar.map((q) => (
              <Link
                key={q.item_id}
                to={`/questoes?banca=${encodeURIComponent(q.banca || "")}&ano=${q.ano || ""}&prova=${encodeURIComponent(q.prova || "")}`}
                className="pill text-xs font-medium bg-zinc-100 hover:bg-zinc-200 text-zinc-700 border border-zinc-200 rounded-full px-3 py-1.5"
              >
                {q.banca} {q.ano} · nº {q.numero}
              </Link>
            ))}
          </div>
          <div className="mt-2 text-[11px] text-zinc-400">
            {iv.praticar.total_disponivel} questão(ões) do acervo exercitam este processo e você ainda não respondeu.
          </div>
        </div>
      )}
    </div>
  );
}

function HabilidadeCard({ linha }) {
  const [aberto, setAberto] = useState(false);
  const [detalhe, setDetalhe] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const origem = ORIGEM[linha.origem] || ORIGEM.desempenho;

  const alternar = () => {
    const proximo = !aberto;
    setAberto(proximo);
    if (proximo && !detalhe && !carregando) {
      setCarregando(true);
      setErro(null);
      api
        .get(`/motor/habilidade/${linha.processo_id}`)
        .then((r) => setDetalhe(r.data))
        .catch((e) => setErro(errMsg(e, "Não foi possível abrir esta habilidade agora.")))
        .finally(() => setCarregando(false));
    }
  };

  return (
    <div className="card-sapiens rounded-2xl p-5 md:p-6" data-testid={`motor-habilidade-${linha.processo_id}`}>
      <button onClick={alternar} className="w-full text-left" data-testid={`motor-abrir-${linha.processo_id}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
              {linha.dominio_nome || "Processo cognitivo"}
            </div>
            <div className="font-display font-bold text-lg text-zinc-950">{linha.processo_nome}</div>
            {linha.definicao && <div className="text-xs text-zinc-500 mt-0.5">{linha.definicao}</div>}
          </div>
          <div className="shrink-0 pt-1 text-zinc-400">
            {aberto ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Chip className={origem.classe}>{origem.chip}</Chip>
          {linha.percentual_acerto !== null && (
            <span className="font-mono-alt text-xs text-zinc-500">
              {linha.percentual_acerto}% de acerto em {linha.respondidas}q
            </span>
          )}
          {linha.origem === "error_trace" && (
            <span className="font-mono-alt text-xs text-zinc-500">
              · raiz de {linha.ocorrencias_raiz} erro(s)
            </span>
          )}
        </div>
        {linha.erro_dominante && (
          <div className="mt-3 text-sm">
            <span className="text-zinc-500">Causa mais provável: </span>
            <span className="font-semibold text-zinc-800">{linha.erro_dominante.nome}</span>
            {linha.erro_dominante.evidencia_observavel && (
              <span className="text-zinc-500"> — {linha.erro_dominante.evidencia_observavel}</span>
            )}
          </div>
        )}
      </button>

      {aberto && carregando && (
        <div className="mt-4 flex items-center gap-2 text-sm text-zinc-500">
          <Loader2 className="w-4 h-4 animate-spin" /> Montando o plano...
        </div>
      )}
      {aberto && erro && <div className="mt-4 text-sm text-rose-600">{erro}</div>}
      {aberto && detalhe && <Detalhe dados={detalhe} />}
    </div>
  );
}

export default function Motor() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const load = () => {
    setLoading(true);
    setLoadError(null);
    api
      .get("/motor/perfil")
      .then((r) => setData(r.data))
      .catch((e) => setLoadError(errMsg(e, "Não foi possível carregar o motor agora.")))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) {
    return (
      <div>
        <Nav />
        <div className="p-10 text-white/60">Cruzando seus erros com o catálogo...</div>
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div>
        <Nav />
        <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
          <div className="text-white/60" data-testid="motor-load-error">{loadError || "Não foi possível carregar o motor agora."}</div>
          <button onClick={load} className="pill mt-4 text-sm font-medium btn-sapiens px-4 py-2 rounded-full" data-testid="motor-retry-btn">
            Tentar de novo
          </button>
        </div>
      </div>
    );
  }

  const fila = data.habilidades_prioritarias || [];
  const raizes = data.mapa_de_erros?.raizes || [];

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-4xl mx-auto px-6 md:px-10 py-12">
        <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3 flex items-center gap-2">
          <Crosshair className="w-3.5 h-3.5" /> Motor cognitivo
        </div>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="motor-title">
          Onde você trava — e o que fazer.
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Cada erro seu é reconstruído como uma cadeia: o que falhou primeiro e o que só veio depois. A intervenção
          trata a raiz. Tudo calculado aqui mesmo, a partir das alternativas que você marcou — sem IA, sem custo,
          sem Sparks.
        </p>

        <div className="mt-6 card-sapiens rounded-2xl p-4 md:p-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm" data-testid="motor-cobertura">
          <div>
            <span className="text-zinc-400">Erros analisados:</span>{" "}
            <span className="font-mono-alt font-bold text-zinc-800">{data.cobertura.erros}</span>
          </div>
          <div>
            <span className="text-zinc-400">Com causa reconstruída:</span>{" "}
            <span className="font-mono-alt font-bold text-zinc-800">
              {data.cobertura.erros_explicados} ({data.cobertura.percentual}%)
            </span>
          </div>
          <div>
            <span className="text-zinc-400">Mínimo por habilidade:</span>{" "}
            <span className="font-mono-alt font-bold text-zinc-800">{data.amostra_minima.tracos_raiz} erros</span>
          </div>
        </div>

        {data.aviso && (
          <div className="mt-4 card-sapiens rounded-2xl p-4 md:p-5 flex items-start gap-3" data-testid="motor-aviso-portao">
            <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-display font-bold text-zinc-950">Segurando por revisão humana</div>
              <p className="text-sm text-zinc-600 mt-1">{data.aviso}</p>
            </div>
          </div>
        )}

        {fila.length === 0 ? (
          <div className="mt-6 card-sapiens rounded-2xl p-6 text-center" data-testid="motor-vazio">
            <div className="font-display font-bold text-lg text-zinc-950">Ainda não dá para apontar nada.</div>
            <p className="mt-2 text-sm text-zinc-500 max-w-md mx-auto">
              Uma habilidade só entra nesta fila quando ela é a raiz de pelo menos {data.amostra_minima.tracos_raiz}{" "}
              erros seus. Um erro isolado não é padrão — é dado insuficiente.
            </p>
            <Link to="/exams" className="pill inline-flex mt-4 text-sm font-medium btn-sapiens px-4 py-2 rounded-full">
              Praticar questões
            </Link>
          </div>
        ) : (
          <div className="mt-8">
            <h2 className="font-display font-bold text-2xl text-white tracking-tight">Sua fila de intervenção</h2>
            <p className="mt-1 text-sm text-white/50 max-w-xl">
              Ordenada pela confiança acumulada de que aquela habilidade é a causa dos seus erros — não pela
              quantidade deles. Clique para abrir o plano.
            </p>
            <div className="mt-4 space-y-4">
              {fila.map((l) => (
                <HabilidadeCard key={l.processo_id} linha={l} />
              ))}
            </div>
          </div>
        )}

        {raizes.length > 0 && (
          <div className="mt-10">
            <h2 className="font-display font-bold text-2xl text-white tracking-tight">Mapa das causas raiz</h2>
            <div className="mt-4 card-sapiens rounded-2xl p-5 md:p-6 space-y-3">
              {raizes.map((r) => (
                <div key={r.erro_id} className="flex items-start justify-between gap-3 flex-wrap" data-testid={`motor-raiz-${r.erro_id}`}>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-zinc-800">{r.erro_nome}</div>
                    <div className="text-xs text-zinc-500">
                      {r.processos.map((p) => p.nome).join(", ")}
                      {r.intervencao_nome ? ` · ${r.intervencao_nome}` : ""}
                    </div>
                  </div>
                  <span className="font-mono-alt text-xs text-zinc-500 shrink-0">
                    {r.ocorrencias}x · peso {r.peso}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-8 text-[11px] text-white/30 max-w-xl">
          Metodologia: cada erro vira uma cadeia ordenada (Error Trace v{data.etrace_version}), lida da anotação da
          questão contra a ontologia v{data.ontology_version}. A intervenção sai sempre do elo raiz. Nenhuma
          atribuição é determinística — todo elo carrega confiança, e nada aqui altera o catálogo.
        </div>
      </div>
    </div>
  );
}
