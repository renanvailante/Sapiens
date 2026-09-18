import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, errMsg } from "../lib/api";
import Nav from "../components/Nav";
import {
  Compass, Check, X, Loader2, ArrowLeft, ArrowRight, Sparkles, Waves,
  PartyPopper, Telescope,
} from "lucide-react";
import ReportarQuestao from "../components/ReportarQuestao";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { MapaMundo3D, BriefingHUD, GuiaMissoes, aplicarProgressao } from "../components/mapa3d";
import { ESTADO_LABEL } from "../components/mapa3d/sceneBuilder";

// A aba Treino deixou de ser uma grade de 56 cartões — as mesmas 56
// habilidades agora são pontos de um único grafo de exploração
// (`/treino/mapa`, ver `treino_grafo_v0_2.py`), agrupados em 6 biomas de
// experiência (Perceber/Relacionar/Representar/Investigar/Integrar/Decidir
// — uma camada de produto, não a ontologia). Decisão de produto
// (2026-09-06): nenhum HAB-xx, DOM-xx, PROC-xx ou COMP-xx real aparece na
// tela — só o nome da habilidade (já é uma frase em português) e o nome do
// bioma.
//
// Não existe "território bloqueado": cada habilidade tem um `estado`
// (unknown/discovered/available/in_progress/mastered) calculado no backend
// pela distância no grafo até o que o aluno já praticou. Dominar uma
// habilidade estende essa distância e revela vizinhos no mapa seguinte —
// sem cadeado nenhum, só fog-of-war.
//
// Aceita `?hab=HAB-03` para abrir direto o briefing de uma habilidade — usado
// pelos deep-links do Motor Cognitivo.

// ESTADO_LABEL agora vem de components/mapa3d/sceneBuilder.js (mesmos 5
// rótulos de sempre); VIEW_W/VIEW_H, BIOMA_TINTS e estiloEstado() eram só do
// renderizador SVG antigo e foram substituídos pelo mundo 3D em mapa3d/.

const DIFICULDADE_LABEL = { FACIL: "Fácil", MEDIO_FACIL: "Médio-fácil", MEDIO: "Médio", DIFICIL: "Difícil" };

function contarVisiveis(mapaData) {
  if (!mapaData) return 0;
  return mapaData.biomas.reduce((acc, b) => acc + b.nodes.filter((n) => n.estado !== "unknown").length, 0);
}

// NoHabilidade, BiomaCamada, MapaCanvas e Briefing viraram o mundo 3D em
// components/mapa3d/ (MapaMundo3D + BriefingHUD) — mesmo contrato de dados,
// renderização substituída.

// ---------- Tabela de questão (reaproveitado) ----------

function TabelaQuestao({ tabela }) {
  if (!tabela) return null;
  return (
    <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-200">
      <table className="w-full border-collapse text-sm" data-testid="treino-tabela">
        <thead>
          <tr className="bg-zinc-50">
            {tabela.headers.map((h, i) => (
              <th key={i} className="border-b border-zinc-200 px-3 py-2 text-left font-bold text-zinc-700 whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tabela.rows.map((row, i) => (
            <tr key={i} className={i % 2 === 1 ? "bg-zinc-50/60" : ""}>
              {row.map((cell, j) => (
                <td key={j} className="border-b border-zinc-100 px-3 py-2 text-zinc-700 whitespace-nowrap">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------- Missão (o antigo Runner, com contextualização e desfecho) ----------

function Missao({ hab, onSair, onConcluida }) {
  const bioma = hab.bioma;
  useDeclararContextoMentis(`Praticando a habilidade "${hab.nome}" no Treino.`);
  const [base, setBase] = useState(null);
  const [idx, setIdx] = useState(0);
  const [selecionada, setSelecionada] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sparksMissao, setSparksMissao] = useState(0);

  useEffect(() => {
    setCarregando(true);
    setErro(null);
    api
      .get(`/treino/habilidade/${hab.hab_id}/base`)
      .then(({ data }) => setBase(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível abrir esta missão agora.")))
      .finally(() => setCarregando(false));
  }, [hab.hab_id]);

  const questao = base?.questoes?.[idx];
  const ultima = base && idx === base.questoes.length - 1;

  const responder = (letra) => {
    if (resultado || enviando) return;
    setSelecionada(letra);
    setEnviando(true);
    api
      .post(`/treino/habilidade/${hab.hab_id}/responder`, { indice: questao.indice, alternativa: letra })
      .then(({ data }) => {
        setResultado(data);
        if (data.sparks_ganhos > 0) setSparksMissao((s) => s + data.sparks_ganhos);
      })
      .catch((e) => setErro(errMsg(e, "Não foi possível registrar sua resposta.")))
      .finally(() => setEnviando(false));
  };

  const proxima = () => {
    if (ultima) {
      onConcluida({ sparksMissao, respondidas: resultado.respondidas, classificacao: resultado.classificacao });
      return;
    }
    setSelecionada(null);
    setResultado(null);
    setIdx((i) => i + 1);
  };

  if (carregando) {
    return (
      <div className="flex items-center gap-2 text-sm text-white/60 py-10">
        <Loader2 className="w-4 h-4 animate-spin" /> Preparando a missão...
      </div>
    );
  }
  if (erro && !base) return <div className="text-sm text-rose-300 py-6">{erro}</div>;
  if (!questao) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <button onClick={onSair} className="inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white" data-testid="treino-sair-runner">
          <ArrowLeft className="w-4 h-4" /> Abandonar missão
        </button>
        <div className="flex items-center gap-1.5" data-testid="mapa-missao-progresso">
          {base.questoes.map((_, i) => (
            <span
              key={i}
              className={`h-1.5 rounded-full transition-all ${i < idx ? "w-4 bg-sapiens-accent" : i === idx ? "w-6 bg-sapiens-accentDeep" : "w-1.5 bg-white/15"}`}
            />
          ))}
        </div>
      </div>

      <article className="card-sapiens leitura-clara rounded-2xl p-6 md:p-8" data-testid="treino-questao-card">
        <div className="mb-1 flex items-center justify-between">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-zinc-400">
            {bioma.nome} · {DIFICULDADE_LABEL[questao.dificuldade]}
          </div>
          <ReportarQuestao itemId={`TREINO:${hab.hab_id}:${questao.indice}`} />
        </div>
        <p className="whitespace-pre-line text-[15px] leading-relaxed text-zinc-800">{questao.enunciado_antes}</p>
        <TabelaQuestao tabela={questao.tabela} />
        {questao.enunciado_depois && (
          <p className="mt-3 whitespace-pre-line text-[15px] leading-relaxed text-zinc-800">{questao.enunciado_depois}</p>
        )}

        <div className="mt-6 grid gap-2">
          {questao.alternativas.map((alt) => {
            const letra = alt.letra;
            const isSelected = selecionada === letra;
            const isCorrect = resultado && resultado.gabarito.includes(letra);
            const isWrongChoice = resultado && isSelected && !resultado.acertou;
            let cls = "border-zinc-200 bg-white hover:border-sapiens-accent hover:shadow-sm";
            if (isCorrect) cls = "border-emerald-400 bg-emerald-50";
            else if (isWrongChoice) cls = "border-rose-400 bg-rose-50";
            else if (isSelected) cls = "border-sapiens-accent bg-sapiens-accentSoft/60 shadow-sm";
            return (
              <button
                key={letra}
                onClick={() => responder(letra)}
                disabled={!!resultado || enviando}
                data-testid={`treino-alt-${letra}`}
                className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition ${cls}`}
              >
                <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  isCorrect ? "bg-emerald-500 text-white" : isWrongChoice ? "bg-rose-500 text-white" : isSelected ? "bg-sapiens-accent text-white" : "bg-zinc-100 text-zinc-600"
                }`}>
                  {isCorrect ? <Check className="w-4 h-4" /> : isWrongChoice ? <X className="w-4 h-4" /> : letra}
                </span>
                <span className="text-zinc-700">{alt.texto}</span>
              </button>
            );
          })}
        </div>

        {erro && <div className="mt-3 text-sm text-rose-600">{erro}</div>}

        <AnimatePresence>
          {resultado && (
            <motion.div
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className={`mt-5 rounded-xl px-4 py-4 ${resultado.acertou ? "bg-emerald-50" : "bg-rose-50"}`}
              data-testid="treino-resultado"
            >
              <div className={`text-sm font-bold ${resultado.acertou ? "text-emerald-700" : "text-rose-700"}`}>
                {resultado.acertou ? "Você acertou!" : `Resposta incorreta. Gabarito: ${resultado.gabarito.join(" ou ")}.`}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-zinc-700">{resultado.elucidacao}</p>
              {resultado.sparks_ganhos > 0 && (
                <div className="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-amber-700">
                  <Sparkles className="w-3.5 h-3.5" /> +{resultado.sparks_ganhos} Spark
                </div>
              )}

              <div className="mt-4 rounded-lg bg-white/70 border border-zinc-200 px-3.5 py-3 flex gap-2.5 items-start">
                <Waves className="w-4 h-4 text-sapiens-accentDeep shrink-0 mt-0.5" />
                <p className="text-xs leading-relaxed text-zinc-600">
                  <span className="font-bold text-zinc-700">Onde isso aparece: </span>
                  {bioma.resumo}
                </p>
              </div>

              <button onClick={proxima} className="pill mt-4 inline-flex text-sm font-medium btn-sapiens px-4 py-2 rounded-full" data-testid="treino-proxima">
                {ultima ? "Concluir missão" : "Próxima questão"}
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </article>
    </div>
  );
}

// ---------- Painel "praticar mais" (geração de questões novas — beta) ----------

function PainelGerar({ habId, sparksPorQuestao }) {
  const [quantidade, setQuantidade] = useState(5);
  const [dificuldade, setDificuldade] = useState("MEDIO");
  const [enviando, setEnviando] = useState(false);
  const [resposta, setResposta] = useState(null);
  const [erro, setErro] = useState(null);

  const custoTotal = sparksPorQuestao * quantidade;

  const pedir = () => {
    setEnviando(true);
    setErro(null);
    const idempotency_key = `treino-${habId}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    api
      .post(`/treino/habilidade/${habId}/gerar`, { quantidade, dificuldade, idempotency_key })
      .then(({ data }) => setResposta(data))
      .catch((e) => setErro(errMsg(e, "Não foi possível processar o pedido agora.")))
      .finally(() => setEnviando(false));
  };

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white/60 p-5" data-testid="treino-painel-gerar">
      <div className="flex items-center gap-2 font-display font-bold text-base text-zinc-950">
        <PartyPopper className="w-5 h-5 text-sapiens-accentDeep" /> Praticar mais nesta habilidade
      </div>
      {resposta ? (
        <div
          className={`mt-3 rounded-xl border p-3.5 ${
            resposta.status === "ok" ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"
          }`}
          data-testid="treino-gerar-resposta"
        >
          <div className={`font-display font-bold text-sm ${resposta.status === "ok" ? "text-emerald-900" : "text-amber-900"}`}>
            {resposta.status === "ok" ? "Questões prontas" : "Não foi possível agora"}
          </div>
          <p className={`mt-1 text-xs ${resposta.status === "ok" ? "text-emerald-800" : "text-amber-800"}`}>{resposta.mensagem}</p>
          {resposta.status === "ok" && (
            <Link
              to={`/minhas-questoes?hab_id=${habId}`}
              className="pill mt-3 inline-flex items-center gap-1.5 text-xs font-medium btn-sapiens px-4 py-2 rounded-full"
              data-testid="treino-gerar-ver"
            >
              Fazer essas questões <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      ) : (
        <>
          <p className="mt-1 text-xs text-zinc-500">Cada questão nova custa {sparksPorQuestao} Sparks.</p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="text-xs">
              <div className="font-bold text-zinc-500 mb-1">Quantidade</div>
              <input
                type="number" min={1} max={10} value={quantidade}
                onChange={(e) => setQuantidade(Math.max(1, Math.min(10, Number(e.target.value) || 1)))}
                className="w-16 rounded-lg border border-zinc-200 px-2.5 py-1.5 text-sm"
                data-testid="treino-gerar-quantidade"
              />
            </label>
            <label className="text-xs">
              <div className="font-bold text-zinc-500 mb-1">Dificuldade</div>
              <select
                value={dificuldade} onChange={(e) => setDificuldade(e.target.value)}
                className="rounded-lg border border-zinc-200 px-2.5 py-1.5 text-sm" data-testid="treino-gerar-dificuldade"
              >
                {Object.keys(DIFICULDADE_LABEL).map((d) => <option key={d} value={d}>{DIFICULDADE_LABEL[d]}</option>)}
              </select>
            </label>
            <div className="text-xs font-bold text-zinc-700">Total: {custoTotal} Sparks</div>
          </div>
          {erro && <div className="mt-2 text-xs text-rose-600">{erro}</div>}
          <button
            onClick={pedir} disabled={enviando}
            className="pill mt-3 inline-flex items-center gap-2 text-xs font-medium btn-sapiens px-4 py-2 rounded-full disabled:opacity-50"
            data-testid="treino-gerar-btn"
          >
            {enviando ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Pedir {quantidade} nova(s)
          </button>
        </>
      )}
    </div>
  );
}

// ---------- Aprofundar com a Mentis (conceito sob demanda, cacheado) ----------

function AprofundarConceito({ habId, habNome, habRotulo, custoConceito, onSparks }) {
  const [estado, setEstado] = useState("idle");
  const [paragrafos, setParagrafos] = useState(null);
  const [cobrado, setCobrado] = useState(null);
  const [erro, setErro] = useState(null);

  const pedir = () => {
    setEstado("carregando");
    setErro(null);
    api
      .post("/treino/conceito/explicar", { hab_id: habId, conceito: habNome })
      .then(({ data }) => {
        setParagrafos(data.paragrafos);
        setCobrado(data.cobrado);
        onSparks?.(data.sparks_balance);
        setEstado("pronto");
      })
      .catch((e) => { setErro(errMsg(e, "Não foi possível aprofundar esse conceito agora.")); setEstado("erro"); });
  };

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white/60 p-5" data-testid="mapa-aprofundar">
      <div className="flex items-center gap-2 font-display font-bold text-base text-zinc-950">
        <Waves className="w-5 h-5 text-sapiens-accentDeep" /> Aprofundar com a Mentis
      </div>
      {estado === "pronto" ? (
        <div className="mt-3 space-y-2.5" data-testid="mapa-mergulho-texto">
          {!cobrado && <div className="text-[11px] text-zinc-400">Você já tinha desbloqueado isso — sem custo.</div>}
          {paragrafos.map((p, i) => <p key={i} className="text-sm leading-relaxed text-zinc-700">{p}</p>)}
        </div>
      ) : (
        <>
          <p className="mt-1.5 text-sm text-zinc-600">
            Peça à Mentis uma explicação mais profunda desta missão ({habRotulo}), com um exemplo do mundo real.
          </p>
          {erro && <div className="mt-2 text-xs text-rose-600">{erro}</div>}
          <button
            onClick={pedir} disabled={estado === "carregando"}
            className="pill mt-3 inline-flex items-center gap-2 text-xs font-medium btn-sapiens px-4 py-2 rounded-full disabled:opacity-50"
            data-testid="mapa-aprofundar-btn"
          >
            {estado === "carregando" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Aprofundar · {custoConceito} Sparks
          </button>
        </>
      )}
    </div>
  );
}

// ---------- Desfecho da missão ----------

function DesfechoMissao({ hab, resultado, novosPontos, custoPorQuestao, custoConceito, onSparks, onFechar }) {
  const bioma = hab.bioma;
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mt-6 space-y-5" data-testid="mapa-desfecho">
      <div className="card-sapiens rounded-2xl p-6 text-center">
        <div className="mx-auto w-12 h-12 rounded-full bg-sapiens-accentSoft flex items-center justify-center">
          <Check className="w-6 h-6 text-sapiens-accentDeep" />
        </div>
        <div className="mt-3 font-display text-xl font-extrabold text-zinc-950">Missão concluída</div>
        <div className="mt-1 text-sm text-zinc-500">
          {ESTADO_LABEL[resultado.classificacao === "forte" ? "mastered" : "in_progress"]} em {hab.rotulo}
        </div>
        {resultado.sparksMissao > 0 && (
          <div className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold text-amber-700 bg-amber-50 px-3 py-1.5 rounded-full">
            <Sparkles className="w-4 h-4" /> +{resultado.sparksMissao} Sparks nesta missão
          </div>
        )}
      </div>

      <AnimatePresence>
        {novosPontos > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            className="rounded-2xl border border-sapiens-accent/40 bg-gradient-to-br from-sapiens-navy to-sapiens-navyDeep p-6 text-center"
            data-testid="mapa-novo-territorio"
          >
            <Telescope className="w-6 h-6 text-sapiens-accent mx-auto" />
            <div className="mt-2 font-display text-lg font-extrabold text-white">
              {novosPontos === 1 ? "Um novo ponto surgiu no mapa" : `${novosPontos} novos pontos surgiram no mapa`}
            </div>
            <p className="mt-1 text-sm text-white/70">O território ao redor de {hab.rotulo} se revelou um pouco mais.</p>
          </motion.div>
        )}
      </AnimatePresence>

      <AprofundarConceito habId={hab.hab_id} habNome={hab.nome} habRotulo={hab.rotulo} custoConceito={custoConceito} onSparks={onSparks} />

      <PainelGerar habId={hab.hab_id} sparksPorQuestao={custoPorQuestao} />

      <div className="text-center">
        <button onClick={onFechar} className="pill inline-flex items-center gap-2 text-sm font-medium text-white/70 hover:text-white bg-white/8 hover:bg-white/15 border border-white/10 px-5 py-2.5 rounded-full" data-testid="mapa-voltar">
          Voltar ao mapa <ArrowLeft className="w-4 h-4 rotate-180" />
        </button>
      </div>
    </motion.div>
  );
}

// ---------- Página ----------

export default function TreinoHabilidades() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [mapaData, setMapaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [custoPorQuestao, setCustoPorQuestao] = useState(3);

  const [briefingHab, setBriefingHab] = useState(null);
  const [missaoHab, setMissaoHab] = useState(null);
  const [desfecho, setDesfecho] = useState(null); // { hab, resultado, novosPontos }
  // Foco pedido pelo guia lateral: move só a câmera, sem abrir missão —
  // por isso é estado próprio, e não `briefingHab`.
  const [focoLista, setFocoLista] = useState(null);

  const carregar = useCallback(() => {
    setLoading(true);
    setErro(null);
    return api
      .get("/treino/mapa")
      .then(({ data }) => { setMapaData(data); return data; })
      .catch((e) => { setErro(errMsg(e, "Não foi possível carregar o mapa agora.")); return null; })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    api.get("/treino/precos").then(({ data }) => setCustoPorQuestao(data.custo_por_questao)).catch(() => {});
  }, []);

  // Camada de progressão: o backend continua mandando as 56 habilidades com
  // o estado de sempre; aqui se decide o que já está acessível, o que é só
  // vislumbre e o que segue oculto. Nada de ontologia, id ou conteúdo muda.
  const biomasVisiveis = useMemo(
    () => (mapaData ? aplicarProgressao(mapaData.biomas, mapaData.arestas) : []),
    [mapaData],
  );

  const nodeIndex = useMemo(() => {
    const idx = {};
    biomasVisiveis.forEach((bioma) => {
      bioma.nodes.forEach((n) => { idx[n.hab_id] = { ...n, bioma }; });
    });
    return idx;
  }, [biomasVisiveis]);

  // Deep-link ?hab=HAB-03 (Motor Cognitivo) — abre o briefing direto quando o mapa carrega.
  useEffect(() => {
    const habId = searchParams.get("hab");
    if (!habId || !nodeIndex[habId] || briefingHab || missaoHab) return;
    setBriefingHab(nodeIndex[habId]);
  }, [searchParams, nodeIndex, briefingHab, missaoHab]);

  const abrirBriefing = (hab) => {
    setBriefingHab(hab);
    setSearchParams({ hab: hab.hab_id });
  };

  const fecharBriefing = () => {
    setBriefingHab(null);
    setSearchParams({});
  };

  const iniciarMissao = () => {
    setMissaoHab(briefingHab);
    setBriefingHab(null);
  };

  const concluirMissao = async (resultado) => {
    const hab = missaoHab;
    const visiveisAntes = contarVisiveis(mapaData);
    const novoMapa = await carregar();
    const novosPontos = novoMapa ? Math.max(0, contarVisiveis(novoMapa) - visiveisAntes) : 0;
    setDesfecho({ hab, resultado, novosPontos });
    setMissaoHab(null);
  };

  const sairMissao = () => {
    setMissaoHab(null);
    setSearchParams({});
  };

  const fecharDesfecho = () => {
    setDesfecho(null);
    setSearchParams({});
  };

  const atualizarSparks = (saldo) => {
    setMapaData((m) => (m ? { ...m, sparks_balance: saldo } : m));
  };

  // No modo mapa o mundo ocupa a tela inteira, em sangria: sem card, sem
  // título, sem legenda. A navegação flutua por cima. Missão e desfecho
  // continuam no layout de leitura de sempre — ali o assunto é texto.
  const modoMapa = !loading && !erro && !missaoHab && !desfecho;

  if (modoMapa) {
    return (
      <div className="fixed inset-0 overflow-hidden" style={{ background: "#04070f" }}>
        <MapaMundo3D
          biomas={biomasVisiveis}
          nodeIndex={nodeIndex}
          arestas={mapaData.arestas}
          onClickHab={abrirBriefing}
          focusHabId={briefingHab?.hab_id ?? focoLista}
          onFecharFoco={fecharBriefing}
        />

        <div className="absolute inset-x-0 top-0 z-40">
          <Nav />
        </div>

        <GuiaMissoes
          biomas={biomasVisiveis}
          arestas={mapaData.arestas}
          focoAtual={briefingHab?.hab_id ?? focoLista}
          onFocar={setFocoLista}
          onLimparFoco={() => setFocoLista(null)}
        />

        <AnimatePresence>
          {briefingHab && (
            <BriefingHUD hab={briefingHab} onFechar={fecharBriefing} onIniciar={iniciarMissao} />
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-6xl mx-auto px-5 py-7 md:px-10 md:py-10">
        <div className="secao-olho flex items-center gap-1.5">
          <Compass className="w-3.5 h-3.5" /> Mapa de exploração
        </div>
        <h1 className="titulo-tela" data-testid="treino-title">
          Existe sempre um território novo para descobrir.
        </h1>
        <p className="mt-3 text-white/60 max-w-xl">
          Cada ponto de luz é uma missão curta. Explore, domine pontos e observe o mapa se revelar ao redor deles.
        </p>

        {loading ? (
          <div className="mt-10 flex items-center gap-2 text-sm text-white/60">
            <Loader2 className="w-4 h-4 animate-spin" /> Revelando o mapa...
          </div>
        ) : erro ? (
          <div className="mt-6 card-sapiens rounded-2xl p-6 text-center">
            <div className="text-zinc-600">{erro}</div>
            <button onClick={carregar} className="pill mt-4 text-sm font-medium btn-sapiens px-4 py-2 rounded-full">Tentar de novo</button>
          </div>
        ) : missaoHab ? (
          <div className="mt-8">
            <Missao hab={missaoHab} onSair={sairMissao} onConcluida={concluirMissao} />
          </div>
        ) : (
          <DesfechoMissao
            hab={desfecho.hab}
            resultado={desfecho.resultado}
            novosPontos={desfecho.novosPontos}
            custoPorQuestao={custoPorQuestao}
            custoConceito={mapaData.custo_conceito}
            onSparks={atualizarSparks}
            onFechar={fecharDesfecho}
          />
        )}
      </div>

      <AnimatePresence>
        {briefingHab && (
          <BriefingHUD hab={briefingHab} onFechar={fecharBriefing} onIniciar={iniciarMissao} />
        )}
      </AnimatePresence>
    </div>
  );
}
