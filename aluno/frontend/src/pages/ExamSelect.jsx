import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errMsg} from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight, Check, X, RotateCw, Sparkles, BookOpen, ChevronLeft } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";

const APP_VERSION = "sapiens-web-1.0";

// "AMARELO" -> "Amarelo" — só para exibição das cores de caderno do ENEM.
const capitalizar = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s);

// ---------------- Rodadas de 10 (a última fecha com o que sobrar: 5, num
// bloco de 45) — os mesmos limites que o backend usa em `_rodada_range`
// (firestore_routes.py). `total=45` -> [10,20,30,40,45].
function limitesDeRodada(total) {
  const limites = [];
  for (let b = 10; b < total; b += 10) limites.push(b);
  if (total > 0) limites.push(total);
  return limites;
}

// Devolve o número da rodada (1-based) quando `posicao` (quantidade de
// questões já respondidas NESTE bloco, contando a que acabou de ser
// respondida) é exatamente um limite de rodada — senão `null`.
function rodadaNaPosicao(posicao, total) {
  const idx = limitesDeRodada(total).indexOf(posicao);
  return idx === -1 ? null : idx + 1;
}

// ---------------- Barra de progresso da prova (0 -> 45/45) ----------------
// Sem estado próprio: `respondidas` é sempre a contagem já persistida
// (behavior events reais), nunca um valor fictício — a mesma fonte usada
// para retomar a prova.
function ProgressoProva({ respondidas, total, pulso, tone = "light" }) {
  const pct = total > 0 ? Math.min(100, Math.round((respondidas / total) * 100)) : 0;
  const onDark = tone === "light"; // "light" = texto claro, para uso sobre o fundo azul da prova
  return (
    <div className="mb-5" data-testid="progresso-prova">
      <div className="mb-1.5 flex items-center justify-between">
        <span className={`font-mono-alt text-[10px] uppercase tracking-[0.25em] ${onDark ? "text-white/70" : "text-zinc-500"}`}>Progresso da prova</span>
        <span className={`font-mono-alt text-xs font-bold ${onDark ? "text-white" : "text-zinc-700"}`} data-testid="progresso-contador">
          {respondidas}/{total}
        </span>
      </div>
      <div
        className={`h-2.5 w-full rounded-full overflow-hidden transition-shadow duration-300 ${onDark ? "bg-white/15" : "bg-zinc-100"} ${
          pulso ? `ring-2 ring-sapiens-accent ring-offset-2 ${onDark ? "ring-offset-sapiens-navy" : "ring-offset-white"}` : ""
        }`}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-sapiens-accentSoft to-sapiens-accent transition-all duration-700 ease-out"
          style={{ width: `${pct}%` }}
          data-testid="progresso-barra"
          data-pct={pct}
        />
      </div>
    </div>
  );
}

// ---------------- Fluxo principal: questões auditadas do Firestore ----------------
// `filtro`, quando presente ({ banca, ano, prova, numero_min, numero_max }),
// restringe às questões de UM bloco (prova real de até 45 questões) — o que
// o aluno escolheu em <ProvasGrid>. Sem filtro, mantém o comportamento
// anterior (todas as questões públicas).
//
// Retomar de onde parou: não existe um "ponto de parada" gravado à parte.
// Cada resposta já vira um evento de behavior no instante em que é enviada
// (POST /students/me/answer) — abandonar no meio nunca perde nada. Ao
// reabrir o mesmo bloco, cruzamos os itens dele com
// GET /students/me/respondidas e pulamos para o primeiro item ainda sem
// resposta. "Onde ele parou" = "o próximo item sem evento de behavior".
function QuestionRunner({ filtro, onExit }) {
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [idx, setIdx] = useState(0);
  const [retomado, setRetomado] = useState(0); // quantas já vinham respondidas ao abrir
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null); // { acertou, correta }
  const [submitting, setSubmitting] = useState(false);
  const [answered, setAnswered] = useState(0);
  const [resumoSessao, setResumoSessao] = useState(null); // resposta de /sessao/diagnostico
  const [carregandoResumo, setCarregandoResumo] = useState(false);
  const [rodadaResumo, setRodadaResumo] = useState(null); // devolutiva determinística da rodada (10/10, 5/5 etc.)
  const [pulso, setPulso] = useState(false); // destaque breve na barra ao responder
  const [sparks, setSparks] = useState(null);
  const startRef = useRef(Date.now());
  const changesRef = useRef(0);
  const respostasSessaoRef = useRef([]); // [{item_id, alternativa_escolhida, acertou}], só desta sessão
  const resumoMostradoParaRef = useRef(0); // evita mostrar o mesmo resumo 2x
  const rodadaPendenteRef = useRef(null); // devolutiva de rodada já buscada, aguardando o clique em "avançar"
  const rodadasProcessadasRef = useRef(new Set()); // evita chamar /rodada/concluir 2x pela mesma rodada nesta sessão

  useEffect(() => {
    let ativo = true;
    api.get("/firestore/students/me/sparks")
      .then(({ data }) => { if (ativo) setSparks(data.sparks_balance); })
      .catch(() => {});
    return () => { ativo = false; };
  }, []);

  useEffect(() => {
    let ativo = true;
    const params = new URLSearchParams({ limit: "100" });
    if (filtro?.banca) params.set("banca", filtro.banca);
    if (filtro?.ano) params.set("ano", filtro.ano);
    if (filtro?.prova) params.set("prova", filtro.prova);
    if (filtro?.numero_min) params.set("numero_min", filtro.numero_min);
    if (filtro?.numero_max) params.set("numero_max", filtro.numero_max);

    Promise.all([
      api.get(`/questoes?${params.toString()}`),
      api.get("/firestore/students/me/respondidas").catch(() => ({ data: { item_ids: [] } })),
    ])
      .then(([{ data }, { data: prog }]) => {
        if (!ativo) return;
        const lista = data.items || [];
        const respondidasSet = new Set(prog.item_ids || []);
        const primeiraPendente = lista.findIndex((it) => !respondidasSet.has(it.item_id));
        const comeco = primeiraPendente === -1 ? lista.length : primeiraPendente;
        setItens(lista);
        setIdx(comeco);
        setRetomado(comeco);
        setAnswered(comeco);
      })
      .catch((e) => { if (ativo) setErro(e?.message || "Falha ao carregar"); })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, [filtro]);

  const item = itens[idx];
  const q = item?.questao || {};
  const fonte = item?.fonte || {};
  const alternativas = Array.isArray(q.alternativas) ? q.alternativas : [];

  const pick = (letra) => {
    if (result) return;
    if (selected !== null && selected !== letra) changesRef.current += 1;
    setSelected(letra);
  };

  const responder = async () => {
    if (!selected || submitting || !item) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/firestore/students/me/answer", {
        item_id: item.item_id,
        alternativa_escolhida: selected,
        tempo_resposta_segundos: Math.round((Date.now() - startRef.current) / 1000),
        numero_tentativas: 1,
        mudou_resposta: changesRef.current > 0,
        contexto_tipo: "pratica_questoes",
        prova_id: fonte.prova || null,
        dispositivo: "web",
        versao_aplicacao: APP_VERSION,
      });
      setResult(data);
      setAnswered((n) => n + 1);
      setPulso(true);
      setTimeout(() => setPulso(false), 700);
      respostasSessaoRef.current.push({
        item_id: item.item_id, alternativa_escolhida: selected, acertou: data.acertou,
      });

      // Fim de rodada (10/10, ..., ou 5/5 na última): busca a devolutiva +
      // Sparks já aqui (mesmo request-cycle da resposta, para minimizar a
      // janela em que um fechamento de aba perderia a rodada) — mas só
      // EXIBE ao clicar em avançar, para não interromper o aluno no meio da
      // leitura do feedback desta questão.
      const posicao = idx + 1;
      const rodadaNum = filtro && rodadaNaPosicao(posicao, itens.length);
      if (rodadaNum && !rodadasProcessadasRef.current.has(rodadaNum)) {
        rodadasProcessadasRef.current.add(rodadaNum);
        try {
          const { data: rd } = await api.post("/firestore/students/me/rodada/concluir", {
            bloco: {
              banca: filtro.banca, ano: filtro.ano, prova: filtro.prova,
              numero_min: filtro.numero_min, numero_max: filtro.numero_max,
            },
            rodada: rodadaNum,
          });
          rodadaPendenteRef.current = rd;
          if (typeof rd.sparks_balance === "number") setSparks(rd.sparks_balance);
        } catch {
          // nunca bloqueia a prática — mesmo princípio do resumo de sessão
        }
      }
    } catch (e) {
      setErro(errMsg(e, "Não foi possível registrar a resposta."));
    } finally {
      setSubmitting(false);
    }
  };

  const proxima = () => {
    setSelected(null);
    setResult(null);
    changesRef.current = 0;
    startRef.current = Date.now();
    setIdx((i) => i + 1);
  };

  // A cada 10 respostas DESTA sessão (não conta o que já vinha de uma
  // retomada), busca o resumo de padrões antes de seguir para a próxima
  // questão. Nunca bloqueia a prática: se o resumo falhar (ex.: Gemini
  // fora do ar), segue direto sem mostrar nada — é um bônus, não um
  // requisito para continuar respondendo.
  //
  // Quando a devolutiva da rodada (determinística, sem IA) e este resumo de
  // sessão (LLM) caem na MESMA resposta — o caso comum de quem começa o
  // bloco do zero, já que ambos os contadores começam em 0 juntos — a
  // devolutiva da rodada é a experiência principal: mostra ela e marca este
  // checkpoint de 10 como já tratado, para NUNCA chamar `diagnose_sessao` (e
  // gastar Gemini) nem duplicar feedback nesse momento. Fora dessa
  // coincidência — por exemplo, retomando o bloco no meio, onde a 10ª
  // resposta desta sessão cai numa posição que não é limite de rodada — o
  // resumo de sessão continua funcionando exatamente como antes.
  const avancar = async () => {
    if (rodadaPendenteRef.current) {
      const rd = rodadaPendenteRef.current;
      rodadaPendenteRef.current = null;
      const nAgora = respostasSessaoRef.current.length;
      if (nAgora > 0 && nAgora % 10 === 0) resumoMostradoParaRef.current = nAgora;
      setRodadaResumo(rd);
      return;
    }
    const n = respostasSessaoRef.current.length;
    if (n > 0 && n % 10 === 0 && resumoMostradoParaRef.current !== n) {
      resumoMostradoParaRef.current = n;
      setCarregandoResumo(true);
      try {
        const { data } = await api.post("/firestore/students/me/sessao/diagnostico", {
          respostas: respostasSessaoRef.current,
        });
        setSelected(null);
        setResult(null);
        changesRef.current = 0;
        startRef.current = Date.now();
        setResumoSessao(data);
      } catch {
        proxima();
      } finally {
        setCarregandoResumo(false);
      }
      return;
    }
    proxima();
  };

  const continuarAposResumo = () => {
    setResumoSessao(null);
    proxima();
  };

  const continuarAposRodada = () => {
    setRodadaResumo(null);
    // Reentra em avancar(): o checkpoint de 10 já foi marcado como tratado
    // (ver comentário acima) quando os dois coincidem, então isto NUNCA
    // dispara o resumo de sessão logo em seguida — só avança a questão.
    avancar();
  };

  if (loading) return <div className="py-24 text-center text-white/70">Carregando questões…</div>;
  if (erro && itens.length === 0)
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700 shadow-[0_20px_50px_-25px_rgba(6,16,36,0.55)]">Erro: {erro}</div>;
  if (itens.length === 0)
    return (
      <div className="card-sapiens rounded-2xl p-10 text-center">
        <div className="font-display text-2xl font-bold text-zinc-950">Nenhuma questão disponível ainda.</div>
        <p className="mt-2 text-zinc-500">Peça a um admin para sincronizar o Firestore no painel administrativo.</p>
      </div>
    );

  if (resumoSessao)
    return (
      <div className="card-sapiens rounded-2xl p-6 md:p-8">
        <div className="font-mono-alt text-xs uppercase tracking-[0.3em] text-sapiens-accentDeep mb-2">
          Resumo da sessão · {respostasSessaoRef.current.length} questões
        </div>
        <div className="font-display text-2xl font-bold tracking-tight text-zinc-950" data-testid="resumo-sessao-headline">
          {resumoSessao.headline}
        </div>
        <p className="mt-3 text-[15px] leading-relaxed text-zinc-700 whitespace-pre-line">{resumoSessao.body}</p>

        {resumoSessao.pontos_fortes?.length > 0 && (
          <div className="mt-5">
            <div className="text-xs font-bold uppercase tracking-wide text-emerald-700">Pontos fortes</div>
            <ul className="mt-1.5 space-y-1 text-sm text-zinc-700">
              {resumoSessao.pontos_fortes.map((p, i) => <li key={i}>· {p}</li>)}
            </ul>
          </div>
        )}
        {resumoSessao.pontos_de_atencao?.length > 0 && (
          <div className="mt-4">
            <div className="text-xs font-bold uppercase tracking-wide text-amber-700">Pontos de atenção</div>
            <ul className="mt-1.5 space-y-1 text-sm text-zinc-700">
              {resumoSessao.pontos_de_atencao.map((p, i) => <li key={i}>· {p}</li>)}
            </ul>
          </div>
        )}
        {resumoSessao.padroes_de_erro?.length > 0 && (
          <div className="mt-4">
            <div className="text-xs font-bold uppercase tracking-wide text-rose-700">Padrões de erro</div>
            <ul className="mt-1.5 space-y-1 text-sm text-zinc-700">
              {resumoSessao.padroes_de_erro.map((p, i) => <li key={i}>· {p}</li>)}
            </ul>
          </div>
        )}

        <button
          onClick={continuarAposResumo}
          data-testid="btn-continuar-apos-resumo"
          className="pill btn-sapiens inline-flex items-center gap-2 mt-6 px-6 py-3 rounded-full text-sm font-medium"
        >
          Continuar praticando <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    );

  if (idx >= itens.length)
    return (
      <div className="card-sapiens rounded-2xl p-10 text-center">
        <ProgressoProva respondidas={itens.length} total={itens.length} pulso={false} tone="dark" />
        <div className="font-display text-2xl font-bold text-zinc-950">Você concluiu todas as questões! 🎉</div>
        <p className="mt-2 text-zinc-500">Respostas registradas: {answered}.</p>
        <button onClick={onExit} className="pill btn-sapiens inline-flex items-center gap-2 mt-6 px-5 py-3 rounded-full text-sm font-medium">
          Voltar
        </button>
      </div>
    );

  const tags = [fonte.disciplina, fonte.ano, fonte.prova].filter(Boolean);

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <div className="font-mono-alt text-xs uppercase tracking-[0.25em] text-white/70">
          Questão {idx + 1} de {itens.length}
        </div>
        <div className="flex items-center gap-3">
          {sparks != null && (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2.5 py-1 text-xs font-bold text-amber-700"
              data-testid="sparks-balance"
            >
              <Sparkles className="w-3.5 h-3.5" /> {sparks}
            </span>
          )}
          <button onClick={onExit} className="text-sm text-white/60 underline hover:text-white">Sair</button>
        </div>
      </div>

      <ProgressoProva respondidas={Math.min(answered, itens.length)} total={itens.length} pulso={pulso} />

      {retomado > 0 && idx === retomado && (
        <div className="mb-4 rounded-xl bg-white/10 border border-white/20 px-4 py-2.5 text-sm text-white">
          Retomando de onde você parou — {retomado} já respondida(s) nesta prova.
        </div>
      )}

      <article className="card-sapiens rounded-2xl p-6 md:p-8">
        <div className="mb-4 flex flex-wrap gap-2">
          {tags.map((t, i) => (
            <span key={i} className="rounded-full bg-sapiens-accentSoft px-3 py-1 text-xs font-medium text-sapiens-navy">{t}</span>
          ))}
        </div>

        <p className="whitespace-pre-line text-[15px] leading-relaxed text-zinc-800">
          {q.enunciado || "(Sem enunciado)"}
        </p>

        {q.recursos?.imagens?.length > 0 && (
          <img
            key={item.item_id}
            src={`/exam-images/${item.item_id}.png`}
            alt="Imagem da questão"
            className="mt-4 max-w-full rounded-lg border border-zinc-200"
            data-testid="questao-imagem"
            onError={(e) => { e.currentTarget.style.display = "none"; }}
          />
        )}

        <div className="mt-6 grid gap-2">
          {alternativas.map((alt) => {
            const letra = alt.letra;
            const isSelected = selected === letra;
            const isCorrect = result && letra === result.correta;
            const isWrongChoice = result && isSelected && !result.acertou;
            let cls = "border-zinc-200 bg-white hover:border-sapiens-accent hover:shadow-sm";
            if (isCorrect) cls = "border-emerald-400 bg-emerald-50";
            else if (isWrongChoice) cls = "border-rose-400 bg-rose-50";
            else if (isSelected) cls = "border-sapiens-accent bg-sapiens-accentSoft/60 shadow-sm";
            return (
              <button
                key={letra}
                onClick={() => pick(letra)}
                disabled={!!result}
                data-testid={`alt-${letra}`}
                className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition ${cls} ${isSelected && !result ? "select-pop" : ""}`}
              >
                <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors ${
                  isCorrect ? "bg-emerald-500 text-white" : isWrongChoice ? "bg-rose-500 text-white" : isSelected ? "bg-sapiens-accent text-white" : "bg-zinc-100 text-zinc-600"
                }`}>
                  {isCorrect ? <Check className="w-4 h-4" /> : isWrongChoice ? <X className="w-4 h-4" /> : letra}
                </span>
                <span className="text-zinc-700">{alt.texto}</span>
              </button>
            );
          })}
        </div>

        {result && (
          <div className={`mt-5 rounded-xl px-4 py-4 reveal ${result.acertou ? "bg-emerald-50" : "bg-rose-50"}`} data-testid="result-banner">
            <div className={`text-sm font-bold ${result.acertou ? "text-emerald-700" : "text-rose-700"}`}>
              {result.feedback?.titulo || (result.acertou ? "Você acertou!" : `Resposta incorreta. Correta: ${result.correta}.`)}
              {!result.acertou && <span className="ml-1 font-normal">(correta: {result.correta})</span>}
            </div>
            {(result.feedback?.mensagens || []).map((m, i) => (
              <p key={i} className={`mt-2 text-sm leading-relaxed ${result.acertou ? "text-emerald-800" : "text-rose-800"}`}>{m}</p>
            ))}
          </div>
        )}

        <div className="mt-6 flex justify-end">
          {!result ? (
            <button
              onClick={responder}
              disabled={!selected || submitting}
              data-testid="btn-responder"
              className="pill btn-sapiens inline-flex items-center gap-2 disabled:opacity-40 px-6 py-3 rounded-full text-sm font-medium"
            >
              {submitting ? "Registrando…" : "Responder"}
            </button>
          ) : (
            <button
              onClick={avancar}
              disabled={carregandoResumo}
              data-testid="btn-proxima"
              className="pill btn-sapiens inline-flex items-center gap-2 disabled:opacity-40 px-6 py-3 rounded-full text-sm font-medium"
            >
              {carregandoResumo
                ? "Analisando padrões desta sessão…"
                : idx + 1 < itens.length ? "Próxima questão" : "Concluir"} <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </article>

      <Dialog open={!!rodadaResumo} onOpenChange={(v) => { if (!v) continuarAposRodada(); }}>
        <DialogContent className="rounded-2xl max-w-md" data-testid="rodada-devolutiva">
          {rodadaResumo && (
            <>
              <DialogHeader>
                <div className="font-mono-alt text-xs uppercase tracking-[0.3em] text-sapiens-accentDeep mb-1">
                  Rodada {rodadaResumo.rodada} concluída
                </div>
                <DialogTitle
                  className="font-display text-3xl font-extrabold tracking-tight text-zinc-950 flex items-center gap-2"
                  data-testid="rodada-acertos"
                >
                  {rodadaResumo.acertos}/{rodadaResumo.total}
                  <Check className="w-6 h-6 text-emerald-500" />
                </DialogTitle>
              </DialogHeader>

              {rodadaResumo.sparks_ganhos > 0 && (
                <div
                  className="flex items-center justify-between rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 animate-in zoom-in-95 duration-300"
                  data-testid="rodada-sparks-ganhos"
                >
                  <div className="flex items-center gap-2 font-bold text-amber-700">
                    <Sparkles className="w-5 h-5" /> +{rodadaResumo.sparks_ganhos} Sparks
                  </div>
                  <div className="font-mono-alt text-xs text-amber-700">saldo: {rodadaResumo.sparks_balance}</div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl bg-zinc-50 px-3 py-2.5">
                  <div className="text-xs text-zinc-500">Acerto na rodada</div>
                  <div className="font-bold text-zinc-900 text-lg">{rodadaResumo.percentual_acerto}%</div>
                </div>
                <div className="rounded-xl bg-zinc-50 px-3 py-2.5">
                  <div className="text-xs text-zinc-500">Evolução</div>
                  <div
                    className={`font-bold text-lg ${
                      rodadaResumo.evolucao > 0 ? "text-emerald-600" : rodadaResumo.evolucao < 0 ? "text-rose-600" : "text-zinc-900"
                    }`}
                    data-testid="rodada-evolucao"
                  >
                    {rodadaResumo.evolucao == null
                      ? "—"
                      : `${rodadaResumo.evolucao > 0 ? "+" : ""}${rodadaResumo.evolucao} p.p.`}
                  </div>
                </div>
              </div>

              {rodadaResumo.padroes_de_erro?.length > 0 && (
                <div data-testid="rodada-padroes-erro">
                  <div className="text-xs font-bold uppercase tracking-wide text-rose-700">Padrões observados nesta rodada</div>
                  <ul className="mt-1.5 space-y-1 text-sm text-zinc-700">
                    {rodadaResumo.padroes_de_erro.map((p, i) => <li key={i}>· {p.nome}</li>)}
                  </ul>
                </div>
              )}

              <DialogFooter>
                <button
                  onClick={continuarAposRodada}
                  data-testid="btn-continuar-rodada"
                  className="pill btn-sapiens inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm font-medium"
                >
                  Continuar praticando <ArrowRight className="w-4 h-4" />
                </button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------- Seleção de caderno: agrupado por banca/ano/cor ----------------
// GET /api/provas agrupa `questoes_public` por (banca, ano, prova) — cada
// grupo é um caderno real já sincronizado do Firestore (nunca inventado
// aqui). `onSelect` recebe exatamente esses 3 campos, usados como filtro em
// <QuestionRunner>.
function ProvasGrid({ onSelect, onExit }) {
  const [provas, setProvas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    let ativo = true;
    api.get("/provas")
      .then(({ data }) => { if (ativo) setProvas(data.provas || []); })
      .catch((e) => { if (ativo) setErro(e?.message || "Falha ao carregar"); })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, []);

  return (
    <div>
      <button onClick={onExit} className="mb-6 inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white">
        <ChevronLeft className="w-4 h-4" /> Voltar
      </button>

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(2)].map((_, i) => <div key={i} className="animate-pulse h-32 bg-white/10 rounded-2xl" />)}
        </div>
      )}

      {erro && !loading && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700">Erro: {erro}</div>
      )}

      {!loading && !erro && provas.length === 0 && (
        <div className="card-sapiens rounded-2xl p-10 text-center">
          <div className="font-display text-2xl font-bold text-zinc-950">Nenhuma prova disponível ainda.</div>
          <p className="mt-2 text-zinc-500">Peça a um admin para sincronizar o Firestore no painel administrativo.</p>
        </div>
      )}

      {!loading && !erro && provas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {provas.map((p, i) => (
            <button
              key={`${p.banca}-${p.ano}-${p.prova}-${p.numero_min}-${i}`}
              onClick={() => onSelect(p)}
              data-testid={`prova-card-${p.banca}-${p.ano}-${p.prova}-${p.numero_min}`}
              className="lift card-sapiens text-left rounded-2xl p-6 hover:border-sapiens-accent"
            >
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sapiens-accent to-sapiens-navy text-white flex items-center justify-center shrink-0">
                  <BookOpen className="w-5 h-5" strokeWidth={1.7} />
                </div>
                <div className="min-w-0">
                  <div className="font-display font-bold text-lg tracking-tight text-zinc-950 truncate">
                    {p.banca} {p.ano} · Caderno {capitalizar(p.prova)}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {p.disciplinas.join(" e ") || "Disciplina não informada"} · Questões {p.numero_min}–{p.numero_max}
                  </div>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs font-mono-alt text-zinc-400">
                  {p.count}{p.total_bloco && p.count < p.total_bloco ? ` de ${p.total_bloco}` : ""} questão(ões)
                </span>
                <span className="inline-flex items-center gap-1.5 text-sm text-zinc-900 font-medium">
                  Praticar <ArrowRight className="w-4 h-4" />
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------- Secundário: praticar por ano (ENEM) — mantido como estava ----------------
function ExamsByYear() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/exams").then(({ data }) => { setExams(data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const grouped = exams.reduce((acc, e) => { (acc[e.year] = acc[e.year] || []).push(e); return acc; }, {});
  const years = Object.keys(grouped).sort((a, b) => Number(b) - Number(a));

  const goWithLanguage = (lang) => { nav(`/exam/${selected.exam_id}?lang=${lang}`); setSelected(null); };

  if (loading) return <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <div key={i} className="animate-pulse h-32 bg-white/10 rounded-2xl" />)}</div>;
  if (years.length === 0)
    return <div className="text-sm text-white/60">Nenhum gabarito importado ainda. <Link to="/admin" className="underline hover:text-white">Abrir painel admin</Link>.</div>;

  return (
    <div className="space-y-8">
      {years.map(y => (
        <div key={y}>
          <div className="mb-3 flex items-baseline gap-3">
            <div className="font-display font-bold text-xl text-zinc-950">ENEM {y}</div>
            <div className="text-xs text-zinc-500 font-mono-alt">{grouped[y].length} caderno(s)</div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {grouped[y].map(e => (
              <button key={e.exam_id} onClick={() => setSelected(e)} className="lift card-sapiens text-left rounded-2xl p-6 hover:border-sapiens-accent" data-testid={`exam-card-${e.exam_id}`}>
                <div className="flex items-center justify-between">
                  <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-500">Dia {e.day} · {e.color}</div>
                  <div className="text-xs text-zinc-400">{e.total_questions}q</div>
                </div>
                <div className="mt-4 font-display font-bold text-lg tracking-tight text-zinc-950">{e.title}</div>
                <div className="mt-2 text-xs text-zinc-500">
                  {e.has_english && <span className="mr-2">EN</span>}
                  {e.has_spanish && <span>ES</span>}
                </div>
                <div className="mt-6 flex items-center gap-2 text-sm text-zinc-900 font-medium">Escolher <ArrowRight className="w-4 h-4" /></div>
              </button>
            ))}
          </div>
        </div>
      ))}

      <Dialog open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogContent className="rounded-2xl">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight" data-testid="lang-dialog-title">Qual idioma você fez?</DialogTitle>
            <p className="text-sm text-zinc-500">Apenas as questões 1-5 mudam entre inglês e espanhol.</p>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3 mt-2">
            <button disabled={!selected?.has_english} onClick={() => goWithLanguage("english")} className="pill p-6 rounded-2xl border border-zinc-200 hover:border-sapiens-accent disabled:opacity-40 disabled:cursor-not-allowed text-left" data-testid="lang-english">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500">Idioma</div>
              <div className="mt-2 font-display font-bold text-xl">Inglês</div>
            </button>
            <button disabled={!selected?.has_spanish} onClick={() => goWithLanguage("spanish")} className="pill p-6 rounded-2xl border border-zinc-200 hover:border-sapiens-accent disabled:opacity-40 disabled:cursor-not-allowed text-left" data-testid="lang-spanish">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-500">Idioma</div>
              <div className="mt-2 font-display font-bold text-xl">Espanhol</div>
            </button>
          </div>
          <DialogFooter />
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ExamSelect() {
  const [mode, setMode] = useState("hub"); // 'hub' | 'provas' | 'practice'
  const [filtro, setFiltro] = useState(null); // { banca, ano, prova, disciplinas, count }

  const escolherProva = (p) => { setFiltro(p); setMode("practice"); };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-14">
        {mode === "practice" ? (
          <QuestionRunner filtro={filtro} onExit={() => setMode("provas")} />
        ) : mode === "provas" ? (
          <>
            <div className="mb-10">
              <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Provas</div>
              <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white">
                Escolha um caderno
              </h1>
              <p className="mt-3 text-white/60 max-w-lg">Cada caderno é uma prova real, agrupada por banca, ano e cor.</p>
            </div>
            <ProvasGrid onSelect={escolherProva} onExit={() => setMode("hub")} />
          </>
        ) : (
          <>
            <div className="mb-10">
              <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Provas</div>
              <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="exam-select-title">
                Pratique questões
              </h1>
              <p className="mt-3 text-white/60 max-w-lg">Questões auditadas, uma de cada vez. Suas respostas são registradas para revelar seus padrões cognitivos.</p>
            </div>

            {/* Principal: escolher um caderno (banca/ano/cor) e praticar */}
            <button
              onClick={() => setMode("provas")}
              data-testid="start-practice"
              className="lift btn-sapiens w-full text-left rounded-3xl p-8 flex items-center gap-5"
            >
              <div className="w-12 h-12 rounded-2xl bg-white/15 flex items-center justify-center shrink-0">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="font-display font-extrabold text-2xl tracking-tight">Começar prática de questões</div>
                <div className="mt-1 text-sm text-white/70">Escolha uma prova · feedback imediato de certo/errado</div>
              </div>
              <ArrowRight className="w-6 h-6" />
            </button>

            {/* Secundário: praticar por ano (ENEM) */}
            <div className="mt-14">
              <div className="flex items-center gap-3 mb-1">
                <RotateCw className="w-4 h-4 text-white/40" />
                <div className="font-mono-alt text-xs uppercase tracking-[0.3em] text-white/50">Opção secundária</div>
              </div>
              <h2 className="font-display text-2xl font-bold tracking-tight text-white">Praticar por ano (ENEM)</h2>
              <p className="mt-2 mb-6 text-sm text-white/60">Provas oficiais completas por edição do ENEM.</p>
              <ExamsByYear />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
