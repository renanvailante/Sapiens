import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, API, errMsg} from "../lib/api";
import Nav from "../components/Nav";
import { ArrowRight, Check, X, RotateCw, Sparkles, BookOpen, ChevronLeft } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import FormulaMath from "../components/FormulaMath";
import Mentis from "../components/Mentis";
import IntervencaoMentis from "../components/IntervencaoMentis";
import ReportarQuestao from "../components/ReportarQuestao";

const APP_VERSION = "sapiens-web-1.0";
const MENTIS_COST = 7; // espelha EXPLICACAO_COST em mentis_routes.py — só p/ desabilitar o botão sem saldo, o servidor é quem cobra de fato

// "AMARELO" -> "Amarelo" — só para exibição das cores de caderno do ENEM.
const capitalizar = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s);

// ---------------- Rodadas de 10 (a última fecha com o que sobrar: 5, num
// bloco de 45) — os mesmos limites que o backend usa em `_rodada_range`
// (firestore_routes.py). `total=45` -> [10,20,30,40,45].
const RODADA_TAMANHO = 10;
function limitesDeRodada(total) {
  const limites = [];
  for (let b = RODADA_TAMANHO; b < total; b += RODADA_TAMANHO) limites.push(b);
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
// Dimensões intrínsecas a partir da `ancora` verificada no saneamento
// (Fase 3): bbox em pontos do PDF + dpi medido do recorte. Sem isto o
// navegador não sabe a proporção antes de baixar a imagem e a página salta.
// Assets `incerta` não têm âncora — e aí não se inventa dimensão nenhuma.
// Elementos visuais (imagem/gráfico/tabela/fórmula) são endereçados por
// conteúdo (`asset.src` = "{sha256}.png"), já enviados junto do próprio
// deploy do frontend em /exam-assets — recortes de provas do ENEM já
// públicas pelo INEP, não dado do aluno. Sem proxy autenticado pelo backend:
// não há backend do pipeline em produção pra servir esses bytes hoje.
function urlAssetVisual(asset) {
  return asset?.src ? `/exam-assets/${asset.src}` : null;
}

function dimensoesIntrinsecas(asset) {
  const a = asset?.ancora;
  const bbox = a?.bbox;
  const dpi = parseFloat(a?.dpi);
  if (!Array.isArray(bbox) || bbox.length !== 4 || !Number.isFinite(dpi) || dpi <= 0) return {};
  const [x0, y0, x1, y1] = bbox;
  const w = Math.round(((x1 - x0) * dpi) / 72);
  const h = Math.round(((y1 - y0) * dpi) / 72);
  return w > 0 && h > 0 ? { width: w, height: h } : {};
}

function QuestionRunner({ filtro, onExit }) {
  const [lightbox, setLightbox] = useState(null);
  const [itens, setItens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [idx, setIdx] = useState(0);
  const [retomado, setRetomado] = useState(0); // quantas já vinham respondidas ao abrir
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null); // { acertou, correta }
  const [submitting, setSubmitting] = useState(false);
  const [answered, setAnswered] = useState(0);
  const [rodadaResumo, setRodadaResumo] = useState(null); // devolutiva unificada da rodada (10/10, 5/5 etc.): Sparks + IA juntos
  const [pulso, setPulso] = useState(false); // destaque breve na barra ao responder
  const [sparks, setSparks] = useState(null);
  const [explicacao, setExplicacao] = useState(null); // { loading, paragrafos, erro } — da questão ATUAL, some ao avançar
  const startRef = useRef(Date.now());
  const changesRef = useRef(0);
  const respostasSessaoRef = useRef([]); // [{item_id, alternativa_escolhida, acertou}], só desta sessão
  const rodadaPendenteRef = useRef(null); // devolutiva de rodada já buscada, aguardando o clique em "avançar"
  const rodadasProcessadasRef = useRef(new Set()); // evita chamar /rodada/concluir e /sessao/diagnostico 2x pela mesma rodada nesta sessão

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
    if (filtro?.area) params.set("area", filtro.area);

    Promise.all([
      api.get(`/questoes?${params.toString()}`),
      api.get("/firestore/students/me/respondidas").catch(() => ({ data: { item_ids: [] } })),
    ])
      .then(([{ data }, { data: prog }]) => {
        if (!ativo) return;
        const lista = data.items || [];
        // Reiniciar a prova ignora de propósito o que já foi respondido: o
        // aluno quer refazer do zero. Cada resposta ainda vira um evento
        // NOVO em `/students/me/answer` (nunca sobrescreve nem apaga o
        // histórico), só não repete Sparks de rodadas já concedidas.
        let comeco = 0;
        if (!filtro?.reiniciar) {
          const respondidasSet = new Set(prog.item_ids || []);
          const primeiraPendente = lista.findIndex((it) => !respondidasSet.has(it.item_id));
          comeco = primeiraPendente === -1 ? lista.length : primeiraPendente;
        }
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
  const todosVisualAssets = Array.isArray(q.visual_assets) ? q.visual_assets : [];
  // Figura-por-alternativa (Q158/163/165/178 do saneamento de 2022): asset
  // com `papel === "alternativa_figura"` + `letra` renderiza dentro do botão
  // da própria alternativa, não na lista geral de figuras do enunciado.
  const figurasPorAlternativa = todosVisualAssets
    .filter((a) => a.papel === "alternativa_figura" && a.letra)
    .reduce((acc, a) => { acc[a.letra] = a; return acc; }, {});
  const figurasPrincipais = [...todosVisualAssets]
    .filter((a) => a.papel !== "alternativa_figura")
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0));

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

      // Fim de rodada (10/10, ..., ou 5/5 na última): busca a devolutiva já
      // aqui (mesmo request-cycle da resposta, para minimizar a janela em
      // que um fechamento de aba perderia a rodada) — mas só EXIBE ao
      // clicar em avançar, para não interromper o aluno no meio da leitura
      // do feedback desta questão.
      //
      // Um único checkpoint (posição geral no bloco/lista, não contagem de
      // respostas desta sessão) alimenta a MESMA devolutiva com duas fontes
      // independentes, disparadas em paralelo:
      //  - Sparks + estatística determinística do bloco (só quando há
      //    `banca`: prática por área não tem identidade de bloco);
      //  - narrativa de IA (`/sessao/diagnostico`), quando a janela desta
      //    rodada já tem as 10 respostas exigidas pelo endpoint.
      // Cada fonte falha de forma independente e nunca bloqueia a prática —
      // sempre sobra pelo menos a devolutiva local computada abaixo.
      const posicao = idx + 1;
      const rodadaNum = rodadaNaPosicao(posicao, itens.length);
      if (rodadaNum && !rodadasProcessadasRef.current.has(rodadaNum)) {
        rodadasProcessadasRef.current.add(rodadaNum);

        // A janela precisa ser a da RODADA, não a da sessão: quem retomava na
        // questão 26 e chegava na 30 fechava a "rodada 3" com 5 respostas, e o
        // resumo de IA (que exige 10) era simplesmente pulado. `posicao` já é a
        // posição no bloco, então o começo da rodada sai dela.
        const inicioRodada = Math.max(0, posicao - RODADA_TAMANHO);
        const janela = respostasSessaoRef.current.slice(-(posicao - inicioRodada));
        const acertosJanela = janela.filter((r) => r.acertou).length;
        let devolutiva = {
          rodada: rodadaNum,
          acertos: acertosJanela,
          total: janela.length,
          percentual_acerto: janela.length > 0 ? Math.round((100 * acertosJanela) / janela.length) : 0,
          evolucao: null,
          padroes_de_erro: [],
          sparks_ganhos: 0,
          sparks_balance: sparks,
        };

        const pedidoRodada = filtro?.banca
          ? api.post("/firestore/students/me/rodada/concluir", {
              bloco: {
                banca: filtro.banca, ano: filtro.ano, prova: filtro.prova,
                numero_min: filtro.numero_min, numero_max: filtro.numero_max,
              },
              rodada: rodadaNum,
            })
          : null;
        const pedidoIA = janela.length >= 10
          ? api.post("/firestore/students/me/sessao/diagnostico", { respostas: janela })
          : null;

        const [resRodada, resIA] = await Promise.allSettled([pedidoRodada, pedidoIA]);

        if (resRodada?.status === "fulfilled" && resRodada.value) {
          const rd = resRodada.value.data;
          devolutiva = { ...devolutiva, ...rd };
          if (typeof rd.sparks_balance === "number") setSparks(rd.sparks_balance);
        }
        if (resIA?.status === "fulfilled" && resIA.value) {
          // `padroes_de_erro` da IA é uma lista de strings; a da rodada
          // (acima) é uma lista de objetos `{nome}` — nunca sobrescrever.
          const { padroes_de_erro: _padroesIA, ...iaCampos } = resIA.value.data;
          devolutiva = { ...devolutiva, ...iaCampos };
        }

        rodadaPendenteRef.current = devolutiva;
      }
    } catch (e) {
      setErro(errMsg(e, "Não foi possível registrar a resposta."));
    } finally {
      setSubmitting(false);
    }
  };

  // Atalhos: A-E escolhem, Enter responde/avança. Quem faz 45 questões
  // seguidas passa a maior parte do tempo aqui, e tirar a mão do teclado a
  // cada questão é atrito puro.
  useEffect(() => {
    const aoTeclar = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const alvo = e.target?.tagName;
      if (alvo === "INPUT" || alvo === "TEXTAREA") return;

      const letra = e.key.toUpperCase();
      if (!result && "ABCDE".includes(letra) && letra.length === 1) {
        const existe = alternativas.some((a) => a.letra === letra && a.texto);
        if (existe) { e.preventDefault(); pick(letra); }
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        if (!result && selected && !submitting) responder();
        else if (result && !submitting) avancar();
      }
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  });

  const proxima = () => {
    setSelected(null);
    setResult(null);
    setExplicacao(null);
    changesRef.current = 0;
    startRef.current = Date.now();
    setIdx((i) => i + 1);
  };

  // Explicação completa da Mentis: paga (MENTIS_COST Sparks), cacheada por
  // item no servidor — pedir de novo na MESMA questão (outro aluno, ou este
  // aluno revisitando) não gera texto novo nem cobra uma segunda chamada ao
  // Gemini, mas ainda cobra os Sparks (o valor entregue é o mesmo).
  const pedirExplicacao = async () => {
    if (!item || explicacao?.loading || explicacao?.paragrafos) return;
    setExplicacao({ loading: true });
    try {
      const { data } = await api.post("/mentis/explicacao", { item_id: item.item_id });
      setExplicacao({ paragrafos: data.paragrafos });
      if (typeof data.sparks_balance === "number") setSparks(data.sparks_balance);
    } catch (e) {
      setExplicacao({ erro: errMsg(e, "Não foi possível gerar a explicação agora.") });
    }
  };

  // A devolutiva (Sparks + IA) já foi buscada em `responder()`, no mesmo
  // checkpoint — aqui só decide se ela está pronta pra mostrar ou se já foi
  // consumida (então é só avançar pra próxima questão).
  const avancar = () => {
    if (rodadaPendenteRef.current) {
      const rd = rodadaPendenteRef.current;
      rodadaPendenteRef.current = null;
      setRodadaResumo(rd);
      return;
    }
    proxima();
  };

  const continuarAposRodada = () => {
    setRodadaResumo(null);
    avancar();
  };

  if (loading) return <div className="py-24 text-center text-white/70">Carregando questões…</div>;
  if (erro && itens.length === 0)
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700 shadow-[0_20px_50px_-25px_rgba(6,16,36,0.55)]">Erro: {erro}</div>;
  if (itens.length === 0)
    return (
      <div className="card-sapiens rounded-2xl p-10 text-center">
        <div className="font-display text-2xl font-bold text-zinc-950">Nenhuma questão disponível ainda.</div>
        <p className="mt-2 text-zinc-500">Estamos preparando novas provas. Volte em breve.</p>
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

      {/* `leitura-clara`: a única superfície clara que sobrou no produto. Numa
          prova de 45 questões, enunciado longo em vidro escuro cansa — conforto
          de leitura ganha da coerência visual quando os dois brigam. Ver a seção
          "Superfície de leitura longa" em index.css. */}
      <article className="card-sapiens leitura-clara rounded-2xl p-6 md:p-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-2">
            {tags.map((t, i) => (
              <span key={i} className="rounded-full bg-sapiens-accentSoft px-3 py-1 text-xs font-medium text-sapiens-navy">{t}</span>
            ))}
          </div>
          <ReportarQuestao itemId={item.item_id} />
        </div>

        <p className="whitespace-pre-line text-[15px] leading-relaxed text-zinc-800">
          {q.enunciado || "(Sem enunciado)"}
        </p>

        {/* `papel === "alternativa_figura"` renderiza DENTRO do botão da
            alternativa correspondente (abaixo), não aqui — senão a mesma
            imagem apareceria duas vezes. */}
        {Array.isArray(figurasPrincipais) && figurasPrincipais.length > 0 ? (
          figurasPrincipais.map((asset) => {
            const visualSrc = urlAssetVisual(asset);
            const visualAlt = `${asset.type || "Elemento visual"} da questão`;
            if (asset.type === "formula") {
              return (
                <FormulaMath
                  key={asset.asset_id}
                  asset={asset}
                  imgSrc={visualSrc}
                  imgAlt={visualAlt}
                  className="mt-4 max-w-full cursor-zoom-in rounded-lg border border-zinc-200"
                  testId="questao-visual-asset-formula"
                  imgProps={dimensoesIntrinsecas(asset)}
                  onClick={() => setLightbox({ src: visualSrc, alt: visualAlt })}
                  onError={(e) => { e.currentTarget.style.display = "none"; }}
                />
              );
            }
            return (
              <img
                key={asset.asset_id}
                src={visualSrc}
                alt={visualAlt}
                className="mt-4 max-w-full cursor-zoom-in rounded-lg border border-zinc-200"
                data-testid="questao-visual-asset"
                loading="lazy"
                {...dimensoesIntrinsecas(asset)}
                onClick={() => setLightbox({ src: visualSrc, alt: visualAlt })}
                onError={(e) => { e.currentTarget.style.display = "none"; }}
              />
            );
          })
        ) : (
          q.recursos?.imagens?.some((img) => img?.arquivo) && (
            <img
              key={item.item_id}
              src={`${API}/exam-images/${item.item_id}`}
              alt="Imagem da questão"
              className="mt-4 max-w-full rounded-lg border border-zinc-200"
              data-testid="questao-imagem"
              loading="lazy"
              onError={(e) => { e.currentTarget.style.display = "none"; }}
            />
          )
        )}

        <div className="mt-6 grid gap-2">
          {alternativas.map((alt) => {
            const letra = alt.letra;
            const isSelected = selected === letra;
            const isCorrect = result && letra === result.correta;
            const isWrongChoice = result && isSelected && !result.acertou;
            const figuraAlt = figurasPorAlternativa[letra];
            let cls = "border-zinc-200 bg-white hover:border-sapiens-accent hover:shadow-sm";
            if (isCorrect) cls = "border-emerald-400 bg-emerald-50";
            else if (isWrongChoice) cls = "border-rose-400 bg-rose-50";
            else if (isSelected) cls = "border-sapiens-accent bg-sapiens-accentSoft/60 shadow-sm";
            return (
              <button
                key={letra}
                onClick={() => pick(letra)}
                disabled={!!result || !alt.texto}
                data-testid={`alt-${letra}`}
                className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition ${cls} ${isSelected && !result ? "select-pop" : ""}`}
              >
                <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors ${
                  isCorrect ? "bg-emerald-500 text-white" : isWrongChoice ? "bg-rose-500 text-white" : isSelected ? "bg-sapiens-accent text-white" : "bg-zinc-100 text-zinc-600"
                }`}>
                  {isCorrect ? <Check className="w-4 h-4" /> : isWrongChoice ? <X className="w-4 h-4" /> : letra}
                </span>
                <span className="flex flex-col gap-2">
                  {figuraAlt && (
                    <img
                      src={urlAssetVisual(figuraAlt)}
                      alt={`Alternativa ${letra}`}
                      className="max-w-[220px] cursor-zoom-in rounded-lg border border-zinc-200 bg-white"
                      loading="lazy"
                      data-testid={`alt-${letra}-figura`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setLightbox({
                          src: urlAssetVisual(figuraAlt),
                          alt: `Alternativa ${letra}`,
                        });
                      }}
                      onError={(e) => { e.currentTarget.style.display = "none"; }}
                    />
                  )}
                  {alt.texto ? (
                    <span className="text-zinc-700">{alt.texto}</span>
                  ) : (
                    // EST-02: 18 itens do corpus têm alternativa sem texto. Antes
                    // disto o botão vinha em branco, clicável, e o aluno podia
                    // "responder" uma alternativa que não existe na prova.
                    <span className="text-zinc-400 italic">
                      Alternativa indisponível — esta questão está em correção.
                    </span>
                  )}
                </span>
              </button>
            );
          })}
        </div>

        {lightbox && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
            onClick={() => setLightbox(null)}
            role="dialog"
            aria-modal="true"
            aria-label="Elemento visual ampliado"
            data-testid="visual-lightbox"
          >
            {/* Fechar visível + Esc: clicar no fundo funcionava, mas não é
                descobrível, e no celular a imagem costuma ocupar a tela toda. */}
            <button
              onClick={(e) => { e.stopPropagation(); setLightbox(null); }}
              className="absolute top-4 right-4 text-white/70 hover:text-white bg-white/10 rounded-full p-2"
              aria-label="Fechar imagem"
              data-testid="lightbox-fechar"
            >
              <X className="w-5 h-5" />
            </button>
            <img src={lightbox.src} alt={lightbox.alt} className="max-h-full max-w-full rounded-lg bg-white" />
          </div>
        )}

        {result && (
          <div className={`mt-5 rounded-xl px-4 py-4 reveal ${result.acertou ? "bg-emerald-50" : "bg-rose-50"}`} data-testid="result-banner">
            <div className={`text-sm font-bold ${result.acertou ? "text-emerald-700" : "text-rose-700"}`}>
              {result.feedback?.titulo || (result.acertou ? "Você acertou!" : `Resposta incorreta. Correta: ${result.correta}.`)}
              {!result.acertou && <span className="ml-1 font-normal">(correta: {result.correta})</span>}
            </div>
            {(result.feedback?.mensagens || []).map((m, i) => (
              <p key={i} className={`mt-2 text-sm leading-relaxed ${result.acertou ? "text-emerald-800" : "text-rose-800"}`}>{m}</p>
            ))}

            {!explicacao?.paragrafos && (
              <button
                onClick={pedirExplicacao}
                disabled={explicacao?.loading || (sparks != null && sparks < MENTIS_COST)}
                data-testid="mentis-explicacao-btn"
                className="mt-3 inline-flex items-center gap-2 rounded-full border border-sapiens-navy/15 bg-white px-3.5 py-2 text-xs font-bold text-sapiens-navy shadow-sm transition hover:border-sapiens-accent hover:shadow disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Mentis className="w-4 h-4" variante="icone" estado={explicacao?.loading ? "analise" : "neutra"} />
                {explicacao?.loading
                  ? "A Mentis está lendo a questão…"
                  : sparks != null && sparks < MENTIS_COST
                  ? `Saldo insuficiente (${MENTIS_COST} Sparks)`
                  : `Saiba mais com a Mentis · ${MENTIS_COST} Sparks`}
              </button>
            )}
            {explicacao?.erro && (
              <p className="mt-2 text-xs font-medium text-rose-600" data-testid="mentis-explicacao-erro">{explicacao.erro}</p>
            )}
            {/* Causa raiz: veio junto da própria resposta (`register_answer` já
                tinha o item na mão), então não custou nenhuma leitura extra
                descobrir que existe uma dificuldade tratável aqui. */}
            {!result.acertou && result.causa_raiz && (
              <div className="mt-3">
                <IntervencaoMentis
                  erroId={result.causa_raiz.erro_id}
                  processoId={result.causa_raiz.processo_id}
                  sparks={sparks}
                  onSparks={setSparks}
                  testid="mentis-intervencao"
                  evidencia={[{ banca: item?.fonte?.banca, ano: item?.fonte?.ano, numero: item?.fonte?.numero,
                               detalhe: `você marcou ${selected}` }]}
                />
              </div>
            )}

            {explicacao?.paragrafos && (
              <div className="mt-4 rounded-xl border border-zinc-200 bg-white/80 p-4" data-testid="mentis-explicacao">
                <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-sapiens-navy">
                  <Mentis className="w-4 h-4" variante="icone" /> Explicação completa da Mentis
                </div>
                {explicacao.paragrafos.map((p, i) => (
                  <p key={i} className="mt-2 text-sm leading-relaxed text-zinc-700">{p}</p>
                ))}
              </div>
            )}
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
              <kbd className="hidden md:inline text-[10px] opacity-60 font-mono-alt">Enter</kbd>
            </button>
          ) : (
            <button
              onClick={avancar}
              disabled={submitting}
              data-testid="btn-proxima"
              className="pill btn-sapiens inline-flex items-center gap-2 disabled:opacity-40 px-6 py-3 rounded-full text-sm font-medium"
            >
              {submitting
                ? "Preparando devolutiva…"
                : idx + 1 < itens.length ? "Próxima questão" : "Concluir"} <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </article>

      <Dialog open={!!rodadaResumo} onOpenChange={(v) => { if (!v) continuarAposRodada(); }}>
        <DialogContent className="rounded-2xl max-w-md max-h-[85vh] overflow-y-auto" data-testid="rodada-devolutiva">
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

              {rodadaResumo.headline && (
                <div data-testid="rodada-resumo-ia">
                  <div className="font-display text-base font-bold text-zinc-900">{rodadaResumo.headline}</div>
                  {rodadaResumo.body && (
                    <p className="mt-1.5 text-sm leading-relaxed text-zinc-700 whitespace-pre-line">{rodadaResumo.body}</p>
                  )}
                </div>
              )}
              {rodadaResumo.pontos_fortes?.length > 0 && (
                <div>
                  <div className="text-xs font-bold uppercase tracking-wide text-emerald-700">Pontos fortes</div>
                  <ul className="mt-1.5 space-y-1 text-sm text-zinc-700">
                    {rodadaResumo.pontos_fortes.map((p, i) => <li key={i}>· {p}</li>)}
                  </ul>
                </div>
              )}
              {rodadaResumo.pontos_de_atencao?.length > 0 && (
                <div>
                  <div className="text-xs font-bold uppercase tracking-wide text-amber-700">Pontos de atenção</div>
                  <ul className="mt-1.5 space-y-1 text-sm text-zinc-700">
                    {rodadaResumo.pontos_de_atencao.map((p, i) => <li key={i}>· {p}</li>)}
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
const MINUTOS_POR_QUESTAO = 1.5; // heurística fixa, só para uma estimativa de tempo — não vem de telemetria real.

function _blocoKey(p) {
  return [p.banca || "", p.ano || "", p.prova || "", p.numero_min || "", p.numero_max || ""].join("|");
}

// Agrega o histórico de rodadas (cada uma já é uma tentativa real, com
// acertos/total) por caderno — a base de "desempenho anterior" e "comparação
// com tentativas anteriores" pedida pro simulado virar uma experiência
// contínua, sem inventar nada além do que já foi respondido.
function _statsPorBloco(rounds) {
  const byBloco = {};
  for (const r of rounds || []) {
    const key = _blocoKey(r.bloco || {});
    const list = (byBloco[key] = byBloco[key] || []);
    list.push(r);
  }
  const stats = {};
  for (const [key, list] of Object.entries(byBloco)) {
    const ordered = [...list].sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
    const last = ordered[ordered.length - 1];
    const best = ordered.reduce((m, r) => Math.max(m, r.percentual_acerto || 0), 0);
    stats[key] = {
      roundsCompleted: new Set(ordered.map((r) => r.rodada)).size,
      lastAccuracy: last?.percentual_acerto ?? null,
      bestAccuracy: best,
      previousAccuracy: ordered.length > 1 ? ordered[ordered.length - 2].percentual_acerto : null,
      attempts: ordered.length,
    };
  }
  return stats;
}

// Progresso REAL de cada bloco (quantas o aluno já respondeu, de
// `/students/me/provas-progresso`) — nunca o tamanho do bloco sincronizado,
// que é só o total disponível, não quanto já foi feito.
function _progressoPorBloco(provasProgresso) {
  const stats = {};
  for (const p of provasProgresso || []) {
    stats[_blocoKey(p)] = { respondidas: p.respondidas || 0, total: p.total || 0 };
  }
  return stats;
}

function ProvasGrid({ onSelect, onExit }) {
  const [provas, setProvas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [roundStats, setRoundStats] = useState({});
  const [progresso, setProgresso] = useState({});
  const [resetAlvo, setResetAlvo] = useState(null); // prova aguardando confirmação de reinício

  const carregarProgresso = () => {
    api.get("/firestore/students/me/provas-progresso")
      .then(({ data }) => setProgresso(_progressoPorBloco(data.provas)))
      .catch(() => {});
  };

  useEffect(() => {
    let ativo = true;
    api.get("/provas")
      .then(({ data }) => { if (ativo) setProvas(data.provas || []); })
      .catch((e) => { if (ativo) setErro(e?.message || "Falha ao carregar"); })
      .finally(() => { if (ativo) setLoading(false); });
    api.get("/firestore/students/me/rounds")
      .then(({ data }) => { if (ativo) setRoundStats(_statsPorBloco(data.rounds)); })
      .catch(() => {});
    carregarProgresso();
    return () => { ativo = false; };
  }, []);

  const confirmarReinicio = () => {
    const p = resetAlvo;
    setResetAlvo(null);
    onSelect(p, { reiniciar: true });
  };

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
          <p className="mt-2 text-zinc-500">Estamos preparando novas provas. Volte em breve.</p>
        </div>
      )}

      {!loading && !erro && provas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {provas.map((p, i) => {
            const stats = roundStats[_blocoKey(p)];
            const prog = progresso[_blocoKey(p)];
            const respondidas = Math.min(prog?.respondidas || 0, p.count || 0);
            const pct = p.count > 0 ? Math.round((100 * respondidas) / p.count) : 0;
            const concluida = p.count > 0 && respondidas >= p.count;
            const expectedRounds = Math.ceil((p.count || 0) / 10);
            const remaining = Math.max(0, (p.count || 0) - (stats?.roundsCompleted || 0) * 10);
            const etaMin = Math.max(1, Math.round(remaining * MINUTOS_POR_QUESTAO));
            const delta = stats && stats.previousAccuracy != null ? Math.round(stats.lastAccuracy - stats.previousAccuracy) : null;
            return (
              <div
                key={`${p.banca}-${p.ano}-${p.prova}-${p.numero_min}-${i}`}
                className="relative lift card-sapiens rounded-2xl p-6"
              >
                {respondidas > 0 && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setResetAlvo(p); }}
                    title="Reiniciar prova"
                    data-testid={`prova-reset-${p.banca}-${p.ano}-${p.prova}-${p.numero_min}`}
                    className="absolute top-4 right-4 z-10 text-zinc-300 hover:text-rose-500 transition-colors"
                  >
                    <RotateCw className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => onSelect(p)}
                  data-testid={`prova-card-${p.banca}-${p.ano}-${p.prova}-${p.numero_min}`}
                  className="w-full text-left"
                >
                  <div className="flex items-center gap-2 pr-6">
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

                  {stats && (
                    <div className="mt-4 flex flex-wrap items-center gap-2" data-testid={`prova-stats-${p.banca}-${p.ano}-${p.prova}-${p.numero_min}`}>
                      <span className="text-[11px] font-mono-alt font-bold text-sapiens-accentDeep bg-sapiens-accentSoft px-2 py-1 rounded-full">
                        última: {stats.lastAccuracy}%
                      </span>
                      {delta != null && delta !== 0 && (
                        <span className={`text-[11px] font-mono-alt font-bold px-2 py-1 rounded-full ${delta > 0 ? "text-emerald-700 bg-emerald-50" : "text-rose-700 bg-rose-50"}`}>
                          {delta > 0 ? "+" : ""}{delta} p.p. vs. anterior
                        </span>
                      )}
                      <span className="text-[11px] font-mono-alt text-zinc-500 bg-zinc-100 px-2 py-1 rounded-full">
                        {stats.roundsCompleted}/{expectedRounds} rodadas
                      </span>
                    </div>
                  )}

                  <div className="mt-4" data-testid={`prova-progresso-${p.banca}-${p.ano}-${p.prova}-${p.numero_min}`}>
                    <div className="mb-1.5 flex items-center justify-between text-xs font-mono-alt text-zinc-400">
                      <span>{respondidas}/{p.count} respondidas{remaining > 0 && !concluida ? ` · ~${etaMin} min` : ""}</span>
                      <span>{pct}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-zinc-100 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-sapiens-accentSoft to-sapiens-accent transition-all duration-500 ease-out"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>

                  <div className="mt-3 flex items-center justify-end">
                    <span className="inline-flex items-center gap-1.5 text-sm text-zinc-900 font-medium">
                      {concluida ? "Ver resultado" : respondidas > 0 ? "Continuar" : "Praticar"} <ArrowRight className="w-4 h-4" />
                    </span>
                  </div>
                </button>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={!!resetAlvo} onOpenChange={(v) => !v && setResetAlvo(null)}>
        <DialogContent className="rounded-2xl" data-testid="dialog-reiniciar-prova">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Reiniciar esta prova?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-zinc-600 leading-relaxed">
            Você vai poder responder {resetAlvo?.banca} {resetAlvo?.ano} · Caderno {resetAlvo && capitalizar(resetAlvo.prova)} do começo.
            Questões já respondidas não dão Sparks de novo, e seu histórico de respostas nunca é apagado — cada tentativa fica registrada.
          </p>
          <DialogFooter>
            <button
              onClick={() => setResetAlvo(null)}
              data-testid="btn-cancelar-reinicio"
              className="pill inline-flex items-center justify-center px-5 py-2.5 rounded-full text-sm font-medium border border-zinc-200 text-zinc-700 hover:border-zinc-300"
            >
              Cancelar
            </button>
            <button
              onClick={confirmarReinicio}
              data-testid="btn-confirmar-reinicio"
              className="pill btn-sapiens inline-flex items-center justify-center px-5 py-2.5 rounded-full text-sm font-medium"
            >
              Reiniciar prova
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
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
    return <div className="text-sm text-white/60">Nenhuma prova completa disponível ainda. Use a prática por caderno acima.</div>;

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
  const [params] = useSearchParams();
  const areaParam = params.get("area");
  const nav = useNavigate();
  const [mode, setMode] = useState(areaParam ? "practice" : "hub"); // 'hub' | 'provas' | 'practice'
  const [filtro, setFiltro] = useState(areaParam ? { area: areaParam } : null); // { banca, ano, prova, disciplinas, count } | { area }

  const escolherProva = (p, opts) => { setFiltro({ ...p, reiniciar: !!opts?.reiniciar }); setMode("practice"); };

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-3xl mx-auto px-6 md:px-10 py-14">
        {mode === "practice" && filtro?.area && (
          <div className="mb-6" data-testid="practice-area-header">
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-3">Lacuna recomendada</div>
            <h1 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter text-white">
              Praticando {filtro.area}
            </h1>
          </div>
        )}
        {mode === "practice" ? (
          <QuestionRunner filtro={filtro} onExit={() => (filtro?.area ? nav("/dashboard") : setMode("provas"))} />
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
