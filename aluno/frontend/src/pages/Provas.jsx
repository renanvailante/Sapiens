import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api, API, errMsg} from "../lib/api";
import CabecaDeSecao from "../components/estudar/CabecaDeSecao";
import CartaoDeCaderno from "../components/estudar/CartaoDeCaderno";
import { agruparPorEdicao, rotuloDoCaderno } from "../lib/cadernos";
import { ArrowRight, Check, X, RotateCw, Sparkles, ChevronLeft, Crosshair, Loader2, Flame, Zap, Volume2, VolumeX, Target, Timer, Trophy, ScrollText } from "lucide-react";
import { toast } from "sonner";
import { avisarSparksMudou } from "../components/Navegacao";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import FormulaMath from "../components/FormulaMath";
import Mentis from "../components/Mentis";
import IntervencaoMentis from "../components/IntervencaoMentis";
import ProfessorInvisivel from "../components/ProfessorInvisivel";
import Microdiagnostico from "../components/Microdiagnostico";
import Alternativas from "../components/questao/Alternativas";
import Comemoracoes from "../components/celebracao/Comemoracoes";
import { PedidoDeNotificacao } from "../components/PedidoDeNotificacao";
import { elogio, reagirAResposta } from "../lib/reacao";
import { tocar, somLigado, definirSom } from "../lib/som";
import { chuvaDeConfete } from "../lib/confete";
import ReportarQuestao from "../components/ReportarQuestao";
import { ROTAS, ANCORAS, com } from "../lib/rotas";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { saidaDoDiagnostico, TOTAL_DO_DIAGNOSTICO } from "../lib/diagnostico";
import { MISSOES } from "../components/mapa3d/missoes";
import {
  abrirPraticaDirigida, resumoDaSerie, fraseDoFechamento, pontoRepetido, TETO_QUESTOES, recompensaDaSerie,
} from "../lib/praticaDirigida";

const APP_VERSION = "sapiens-web-1.0";
// Preço nunca é escrito no JS (`economia-de-sparks.md`): os dois abaixo são
// só a RESERVA enquanto `GET /mentis/precos` não responde — o número que a
// tela escreve vem das constantes que cobram. Até 2026-10-01 eram o próprio
// preço, espelhado à mão.
const EXPLICACAO_PADRAO = 7;
const RESUMO_RODADA_PADRAO = 15;

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
/** O progresso da prova.
 *
 *  Passou a usar `.barra`, a barra do sistema, em 2026-09-16. Ela tinha
 *  degradê próprio (`accentSoft -> accent`), altura própria e trilho próprio —
 *  três decisões de cor tomadas nesta tela, sem relação com as outras cinco
 *  barras do produto. Agora é a mesma luz de tudo, e o `data-cheia` faz o
 *  brilho correr por dentro dela quando a prova acaba.
 *
 *  As duas chamadas vivem sobre superfície ESCURA (a tela da prova e o card de
 *  conclusão), então não há variante clara; `tone` fica só porque a chamada de
 *  conclusão ainda o passa. */
function ProgressoProva({ respondidas, total, pulso, combo = false, rotulo = "Progresso da prova" }) {
  const pct = total > 0 ? Math.min(100, Math.round((respondidas / total) * 100)) : 0;
  return (
    <div className="mb-5" data-testid="progresso-prova">
      <div className="mb-2 flex items-center justify-between">
        <span className="secao-olho">{rotulo}</span>
        <span className="font-mono-alt text-xs font-bold tabular-nums text-white" data-testid="progresso-contador">
          {respondidas}/{total}
        </span>
      </div>
      <div
        className={`barra transition-shadow duration-300 ${pulso ? "ring-2 ring-[#4FD9FF]/70 ring-offset-2 ring-offset-[#050a14]" : ""}`}
        data-cheia={pct >= 100}
        data-combo={combo}
      >
        <i style={{ width: `${pct}%` }} data-testid="progresso-barra" data-pct={pct} />
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

/**
 * O FECHAMENTO DE UMA SÉRIE — a última tela de qualquer conjunto de questões.
 *
 * Era "Você concluiu todas as questões! 🎉" e um botão "Voltar": o momento
 * em que o aluno mais sabe sobre o próprio desempenho era o único sem
 * nenhuma informação e sem nenhum caminho. Quem terminava uma revisão, uma
 * prova inteira ou uma série dirigida recebia a mesma tela, e ela mandava
 * para trás.
 *
 * Agora ela responde as três perguntas de quem acabou de terminar:
 *
 *   1. **como foi** — acertos desta série (só desta sessão; o que já vinha
 *      respondido ao abrir não entra, porque não foi feito agora);
 *   2. **mudou alguma coisa** — na prática dirigida, a comparação com o
 *      histórico daquele ponto (`resumoDaSerie`), descritiva e com amostra
 *      mínima dos dois lados;
 *   3. **e agora** — uma saída concreta: o ponto em que dois erros desta
 *      série começaram, mais questões do mesmo ponto, ou o Próximo Passo do
 *      Hoje (que a esta altura já foi recalculado com estas respostas).
 */
/**
 * O MOMENTO DE RECOMPENSA do fim da série — o que o Duolingo faz no fim de cada
 * lição, com a régua da casa: só número que o servidor já contou
 * (`engajamento.py`, linha ética). O XP é a diferença real entre o começo e o
 * fim da série; a sequência é a ofensiva, que só conta dia com estudo de
 * verdade; a missão cumprida é a do dia, com o prêmio fixo e anunciado — e o
 * resgate acontece aqui, sem mandar o aluno para outra tela buscar o que já
 * ganhou. Sem dado, a peça não aparece.
 */
function RecompensaDaSerie({ estado, xpInicial, melhorSequencia }) {
  const [resgatando, setResgatando] = useState(null);
  const [resgatadas, setResgatadas] = useState(() => new Set());

  const { xp: xpGanho, diaGarantido, seguidas, prontas } = recompensaDaSerie(estado, xpInicial, melhorSequencia, resgatadas);

  const resgatar = async (m) => {
    setResgatando(m.id);
    try {
      const { data } = await api.post(`/engajamento/missoes/${m.id}/resgatar`);
      setResgatadas((s) => new Set(s).add(m.id));
      tocar("moeda");
      toast.success(`+${data.sparks_ganhos} Sparks e +${data.xp_ganho} XP.`);
      avisarSparksMudou();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível resgatar agora."));
    } finally {
      setResgatando(null);
    }
  };

  const itens = [
    xpGanho > 0 && { chave: "xp", icone: Zap, cor: "text-amber-500", texto: `+${xpGanho} XP nesta série` },
    diaGarantido > 0 && {
      chave: "ofensiva", icone: Flame, cor: "text-orange-500",
      texto: diaGarantido === 1 ? "Hoje já conta: sua sequência começou" : `Dia ${diaGarantido} da sua sequência garantido`,
    },
    seguidas > 0 && { chave: "seguidas", icone: Check, cor: "text-emerald-600", texto: `${seguidas} acertos seguidos` },
  ].filter(Boolean);

  if (!itens.length && !prontas.length) return null;
  return (
    <div className="mt-5 space-y-2.5" data-testid="serie-recompensa">
      {itens.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {itens.map((i) => (
            <span
              key={i.chave}
              className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs font-semibold text-zinc-800"
              data-testid={`serie-recompensa-${i.chave}`}
            >
              <i.icone className={`h-3.5 w-3.5 ${i.cor}`} /> {i.texto}
            </span>
          ))}
        </div>
      )}
      {prontas.map((m) => (
        <div
          key={m.id}
          className="flex flex-col items-stretch gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 sm:flex-row sm:items-center"
          data-testid={`serie-missao-${m.id}`}
        >
          <div className="min-w-0 flex-1 text-sm text-amber-900">
            <span className="font-semibold">Missão do dia cumprida:</span> {m.titulo}
          </div>
          <button
            onClick={() => resgatar(m)}
            disabled={resgatando === m.id}
            className="pill btn-sapiens inline-flex w-full items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold disabled:opacity-60 sm:w-auto"
            data-testid={`serie-missao-resgatar-${m.id}`}
          >
            {resgatando === m.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Resgatar +{m.sparks} Sparks
          </button>
        </div>
      ))}
    </div>
  );
}

/** "1min 42s" — o tempo da série, medido nesta sessão. */
function duracao(segundos) {
  if (!(segundos > 0)) return null;
  const m = Math.floor(segundos / 60);
  const s = Math.round(segundos % 60);
  return m > 0 ? `${m}:${String(s).padStart(2, "0")}` : `${s}s`;
}

/** O PLACAR do fim da lição — as três caixinhas do Duolingo. Cada número é
 *  medido: XP é a diferença real de `/engajamento/me` (some sem ela), a
 *  precisão é acerto desta série, o tempo é o relógio desta sessão. */
function PlacarDaSerie({ xp, percentual, segundos }) {
  const caixas = [
    xp > 0 && { classe: "placar-xp", rotulo: "XP total", icone: Zap, valor: `+${xp}` },
    percentual != null && {
      classe: "placar-precisao",
      rotulo: percentual >= 90 ? "Incrível" : percentual >= 70 ? "Ótimo" : "Precisão",
      icone: Target,
      valor: `${percentual}%`,
    },
    duracao(segundos) && { classe: "placar-tempo", rotulo: "Tempo", icone: Timer, valor: duracao(segundos) },
  ].filter(Boolean);
  if (!caixas.length) return null;
  return (
    <div className="mt-5 grid grid-cols-3 gap-2.5 sm:max-w-md" data-testid="serie-placar">
      {caixas.map((c, i) => (
        <div key={c.classe} className={`placar ${c.classe}`} style={{ animationDelay: `${250 + i * 160}ms` }}>
          <div className="placar-cabeca">{c.rotulo}</div>
          <div className="placar-corpo">
            <c.icone className="h-5 w-5" /> {c.valor}
          </div>
        </div>
      ))}
    </div>
  );
}

function FechamentoDaSerie({ respostas, filtro, onExit, abrindo, aoPraticar, xpInicial = null, melhorSequencia = 0, segundos = 0 }) {
  // O fechamento aparece no lugar da última questão, abaixo do cabeçalho da
  // série. No celular isso o deixava a 600px do topo — o resultado existia e
  // não era visto. Ele rola até si ao montar.
  const ref = useRef(null);
  const trofeu = useRef(null);
  const dirigida = filtro?.dirigida || null;
  const resumo = resumoDaSerie(respostas, dirigida);
  // O estado de engajamento DEPOIS da série: o XP ganho, o dia de ofensiva
  // garantido, a missão cumprida e — se este foi o primeiro estudo do dia —
  // a tela da chama. Uma leitura só para as quatro peças.
  const [estado, setEstado] = useState(null);
  useEffect(() => {
    ref.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    let ativo = true;
    if (resumo.total > 0) {
      // A fanfarra do fim de lição, e confete saindo do troféu.
      tocar("fim");
      setTimeout(() => (resumo.percentual >= 60 ? chuvaDeConfete() : null), 350);
      api.get("/engajamento/me").then(({ data }) => { if (ativo) setEstado(data); }).catch(() => {});
    }
    return () => { ativo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // O diagnóstico do primeiro acesso termina no PLANO enquanto ele não existe
  // (`lib/diagnostico.js`). Quem já tem plano e refez as dez volta à trilha.
  const diagnostico = Boolean(filtro?.diagnostico);
  const [planoFeito, setPlanoFeito] = useState(false);
  useEffect(() => {
    if (!diagnostico) return undefined;
    let ativo = true;
    api.get("/onboarding").then(({ data }) => { if (ativo) setPlanoFeito(Boolean(data?.concluido)); }).catch(() => {});
    return () => { ativo = false; };
  }, [diagnostico]);
  const saida = diagnostico ? saidaDoDiagnostico({ planoFeito }) : { rota: ROTAS.HOJE, rotulo: "Continuar a trilha" };
  const xpGanho = recompensaDaSerie(estado, xpInicial, melhorSequencia).xp;
  // O tempo congela no instante em que a série acabou; sem isto ele andaria a
  // cada nova renderização do fechamento.
  const [tempo] = useState(segundos);
  const frase = fraseDoFechamento(resumo);
  // Dentro de uma série dirigida, dois erros no mesmo ponto são o próprio
  // ponto da série — dizer isso de novo seria redundante.
  const repetido = !dirigida ? resumo.repetido : null;
  const mais = dirigida?.processoId && dirigida.restantes > 0 ? Math.min(TETO_QUESTOES, dirigida.restantes) : 0;
  // A missão do mapa que exercita o mesmo processo — a ponte prova → Treino.
  // O rótulo é o do mapa ("Proporção I"), o mesmo que o aluno vê lá.
  const missaoLigada = (dirigida?.habilidades || []).map((id) => ({ id, rotulo: MISSOES[id]?.rotulo })).find((m) => m.rotulo);

  const titulo = dirigida
    ? "Série concluída"
    : diagnostico
      ? "Diagnóstico concluído"
      : filtro?.origem === "revisao"
      ? "Revisão concluída"
      : filtro?.banca
        ? "Caderno concluído"
        : "Questões concluídas";

  // O olho diz DE QUÊ era a série; o título já diz que ela acabou.
  const olho =
    dirigida?.foco ||
    (diagnostico ? "Seu diagnóstico" : null) ||
    (filtro?.origem === "revisao"
      ? "Revisão espaçada"
      : [filtro?.banca, filtro?.ano].filter(Boolean).join(" ") || filtro?.area || "Prática");

  const botaoSecundario = "pill btn-vidro inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm";

  return (
    <div ref={ref} className="card-sapiens scroll-mt-24 rounded-2xl p-7 md:p-10" data-testid="serie-fechamento">
      {/* A chama do dia vem DEPOIS do placar, como no Duolingo: abrir as duas
          juntas apagaria o placar que o aluno acabou de ganhar. */}
      {estado && <Comemoracoes engajamento={estado} atraso={2600} />}
      {resumo.total > 0 && (
        <div ref={trofeu} className="trofeu-salta mb-4 inline-flex" aria-hidden="true">
          <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-200 to-amber-500 text-amber-950 shadow-[0_5px_0_0_#92400e,0_0_40px_-8px_rgba(251,191,36,0.9)]">
            <Trophy className="h-8 w-8" />
          </span>
        </div>
      )}
      <div className="secao-olho">{olho}</div>
      <div className="mt-1.5 font-display text-2xl font-bold text-zinc-950" data-testid="serie-fechamento-titulo">
        {resumo.total > 0 ? `${titulo}: ${resumo.acertos} de ${resumo.total}` : titulo}
      </div>
      <p className="mt-2 max-w-lg text-sm leading-relaxed text-zinc-500">
        {resumo.total === 0
          ? "Você já tinha respondido todas as questões deste conjunto. Cada resposta está registrada no seu histórico."
          : frase || "Cada resposta desta série já entrou no seu histórico — é com elas que o próximo passo é escolhido."}
      </p>

      {/* No diagnóstico o padrão é o ACHADO — a promessa do anúncio ("o
          Sapiens encontra esse padrão") — e sobe para logo abaixo do placar
          de acertos, antes do XP e da missão. */}
      {repetido && diagnostico && (
        <p className="mt-3 max-w-lg text-sm leading-relaxed text-zinc-600" data-testid="serie-fechamento-repetido">
          <span className="font-semibold text-zinc-800">
            {repetido.vezes} dos seus erros começaram no mesmo ponto.
          </span>{" "}
          Não é falta de estudo: é um padrão — e dá para treinar só ele.
        </p>
      )}

      {diagnostico && !planoFeito && resumo.total > 0 && (
        <p className="mt-3 max-w-lg text-sm leading-relaxed text-zinc-600" data-testid="diagnostico-proximo">
          <span className="font-semibold text-zinc-800">Agora, o seu plano da semana.</span>{" "}
          Três perguntas — o seu tempo, a sua meta e o que pesa mais para você — e a semana sai montada a partir delas e do que você acabou de responder.
        </p>
      )}

      {dirigida?.sinal && resumo.total > 0 && (
        <p className="mt-3 max-w-lg text-sm leading-relaxed text-zinc-600" data-testid="serie-fechamento-sinal">
          <span className="font-semibold text-zinc-800">O que observar daqui para a frente:</span> {dirigida.sinal}
        </p>
      )}

      {resumo.total > 0 && <PlacarDaSerie xp={xpGanho} percentual={resumo.percentual} segundos={tempo} />}

      {resumo.total > 0 && <RecompensaDaSerie estado={estado} xpInicial={xpInicial} melhorSequencia={melhorSequencia} />}

      {/* O pedido de aviso no celular: aqui, e não no primeiro acesso, porque
          a pergunta fala do que o aluno acabou de fazer (`lib/push.js`). */}
      <PedidoDeNotificacao respondeuNaSerie={resumo.total > 0} />

      {repetido && !diagnostico && (
        <p className="mt-3 max-w-lg text-sm leading-relaxed text-zinc-600" data-testid="serie-fechamento-repetido">
          <span className="font-semibold text-zinc-800">{repetido.vezes} erros desta série começaram no mesmo ponto.</span>{" "}
          Vale praticar só ele agora, com questões que você ainda não viu.
        </p>
      )}

      {/* UMA saída grande, sempre a mesma: de volta à trilha do dia, onde o
          nó que esta série cumpriu acende e a Mentis diz qual é o próximo
          (2026-10-09, o "CONTINUAR" do fim de lição do Duolingo). Até aqui
          eram até cinco botões do mesmo tamanho — praticar o ponto, mais do
          ponto, próximo passo, mapa, voltar — e o aluno tinha de decidir
          entre eles logo depois de terminar. As outras continuam, menores,
          embaixo: são escolha, não o caminho. */}
      <Link
        to={saida.rota}
        className="pill btn-sapiens btn-grande mt-7 inline-flex w-full items-center justify-center gap-2.5 sm:w-auto sm:min-w-[18rem]"
        data-testid="serie-proximo-passo"
      >
        {saida.rotulo} <ArrowRight className="h-5 w-5" />
      </Link>

      <div className="mt-4 flex flex-col gap-2.5 sm:flex-row sm:flex-wrap">
        {repetido && (
          <button
            onClick={() => aoPraticar(repetido.processoId, { tipo: "repetido", linha: { processo_id: repetido.processoId } })}
            disabled={abrindo}
            className={botaoSecundario}
            data-testid="serie-praticar-ponto"
          >
            {abrindo ? <>Separando as questões <Loader2 className="h-4 w-4 animate-spin" /></> : <><Crosshair className="h-4 w-4" /> Praticar esse ponto</>}
          </button>
        )}
        {mais > 0 && (
          <button
            onClick={() => aoPraticar(dirigida.processoId, {
              tipo: dirigida.tipo,
              // Só o id: o rótulo do ponto sai de `lib/rotulosDoMotor`.
              linha: { processo_id: dirigida.processoId, erro_dominante: dirigida.erroId || null },
            })}
            disabled={abrindo}
            className={botaoSecundario}
            data-testid="serie-mais-do-ponto"
          >
            {abrindo ? <>Separando as questões <Loader2 className="h-4 w-4 animate-spin" /></> : <>Mais {mais} deste ponto <ArrowRight className="h-4 w-4" /></>}
          </button>
        )}
        {missaoLigada && (
          <Link
            to={`${ROTAS.TREINO}?hab=${encodeURIComponent(missaoLigada.id)}`}
            className={botaoSecundario}
            data-testid="serie-missao-ligada"
          >
            Treinar no mapa: {missaoLigada.rotulo}
          </Link>
        )}
        {filtro?.origem === "revisao" ? (
          <Link to={com(ROTAS.AGENDA, ANCORAS.AGENDA_REVISOES)} className={botaoSecundario} data-testid="serie-voltar-revisoes">
            Voltar às revisões
          </Link>
        ) : !dirigida && !diagnostico ? (
          <button onClick={onExit} className={botaoSecundario} data-testid="serie-voltar">
            {filtro?.banca ? "Escolher outro caderno" : "Voltar"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

/** Mudo / som, sempre à vista na tela de questão. A escolha é do aparelho
 *  (`lib/som.js`): quem estuda na biblioteca desliga uma vez e pronto. */
function BotaoDeSom() {
  const [ligado, setLigado] = useState(somLigado);
  const alternar = () => {
    const novo = !ligado;
    definirSom(novo);
    setLigado(novo);
    if (novo) tocar("acerto");
  };
  return (
    <button
      type="button"
      onClick={alternar}
      className="chip pill"
      aria-label={ligado ? "Desligar o som" : "Ligar o som"}
      aria-pressed={ligado}
      title={ligado ? "Som ligado" : "Som desligado"}
      data-testid="questao-som"
    >
      {ligado ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
    </button>
  );
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
  const [resumoIA, setResumoIA] = useState(null); // { loading, erro } da leitura paga da Mentis sobre a rodada aberta
  const startRef = useRef(Date.now());
  const changesRef = useRef(0);
  const respostasSessaoRef = useRef([]); // [{item_id, alternativa_escolhida, acertou, causa_raiz}], só desta sessão
  const rodadaPendenteRef = useRef(null); // devolutiva de rodada já buscada, aguardando o clique em "avançar"
  const rodadasProcessadasRef = useRef(new Set()); // evita chamar /rodada/concluir 2x pela mesma rodada nesta sessão
  const navegar = useNavigate();
  const [abrindoPonto, setAbrindoPonto] = useState(false);

  // A prática dirigida avisa a Mentis do que está sendo trabalhado: quem abre
  // o chat no meio da série encontra uma tutora que sabe o ponto e o porquê.
  const dirigida = filtro?.dirigida || null;
  useDeclararContextoMentis(
    dirigida?.foco
      ? `Fazendo uma série de questões dirigida ao ponto "${dirigida.foco}"${dirigida.erro ? `, onde o erro que mais se repete é "${dirigida.erro}"` : ""}.`
      : "",
  );

  /** Do erro repetido para a prática só dele. O que já foi respondido está
   *  gravado, então sair daqui no meio de uma prova não perde nada. */
  const praticarPonto = (processoId, escolha) => {
    if (!processoId || abrindoPonto) return;
    setAbrindoPonto(true);
    abrirPraticaDirigida({ api, navegar, processoId, escolha }).finally(() => setAbrindoPonto(false));
  };

  // Preços e direitos: o saldo já traz os `direitos` (um documento só), e
  // quem tem a Mentis ilimitada não paga nenhuma das duas leituras desta tela.
  const [precos, setPrecos] = useState(null);
  const [ilimitada, setIlimitada] = useState(false);
  const [xpInicial, setXpInicial] = useState(null);
  // Acertos seguidos NESTA sessão — o "combo" do Duolingo, feito de resposta
  // real. Aparece a partir de 3 (dois seguidos acontecem por acaso).
  const [seguidas, setSeguidas] = useState(0);
  const melhorSequenciaRef = useRef(0);
  const [elogioAtual, setElogioAtual] = useState("Você acertou!");
  // Quando a série começou NESTA sessão — o placar do fim mostra o tempo.
  const inicioSerieRef = useRef(Date.now());
  useEffect(() => {
    let ativo = true;
    api.get("/firestore/students/me/sparks")
      .then(({ data }) => {
        if (!ativo) return;
        setSparks(data.sparks_balance);
        setIlimitada(Boolean(data.direitos?.mentis_ilimitada));
      })
      .catch(() => {});
    api.get("/mentis/precos").then(({ data }) => { if (ativo) setPrecos(data); }).catch(() => {});
    // O XP no começo da série: o fechamento mostra a diferença REAL, e não
    // uma conta feita aqui com valores que o servidor é quem decide.
    api.get("/engajamento/me")
      .then(({ data }) => { if (ativo) setXpInicial(data?.nivel?.xp_total ?? null); })
      .catch(() => {});
    return () => { ativo = false; };
  }, []);
  const MENTIS_COST = precos?.explicacao ?? EXPLICACAO_PADRAO;
  const RESUMO_RODADA_COST = precos?.resumo_rodada ?? RESUMO_RODADA_PADRAO;
  const semSaldoExplicacao = !ilimitada && sparks != null && sparks < MENTIS_COST;
  const semSaldoResumo = !ilimitada && sparks != null && sparks < RESUMO_RODADA_COST;

  useEffect(() => {
    let ativo = true;
    const params = new URLSearchParams({ limit: "100" });
    if (filtro?.banca) params.set("banca", filtro.banca);
    if (filtro?.ano) params.set("ano", filtro.ano);
    if (filtro?.prova) params.set("prova", filtro.prova);
    if (filtro?.numero_min) params.set("numero_min", filtro.numero_min);
    if (filtro?.numero_max) params.set("numero_max", filtro.numero_max);
    if (filtro?.area) params.set("area", filtro.area);
    if (filtro?.item_ids?.length) params.set("item_ids", filtro.item_ids.join(","));

    Promise.all([
      api.get(filtro?.diagnostico ? "/questoes/diagnostico" : `/questoes?${params.toString()}`),
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
  // `Alternativas` recebe figura já resolvida em `{ src }`: a peça
  // compartilhada não conhece o formato de asset do corpus, e não deveria.
  const figurasParaAlternativas = Object.fromEntries(
    Object.entries(figurasPorAlternativa).map(([letra, a]) => [letra, { src: urlAssetVisual(a) }]),
  );
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
      const proximaSeguida = data.acertou ? seguidas + 1 : 0;
      melhorSequenciaRef.current = Math.max(melhorSequenciaRef.current, proximaSeguida);
      setSeguidas(proximaSeguida);
      setElogioAtual(elogio());
      // O "plim" e o confetinho — e, nos marcos de combo, um som maior.
      reagirAResposta(Boolean(data.acertou), { seguidas: proximaSeguida });
      setPulso(true);
      setTimeout(() => setPulso(false), 700);
      respostasSessaoRef.current.push({
        item_id: item.item_id, alternativa_escolhida: selected, acertou: data.acertou,
        // O ponto em que este erro começou — já veio na resposta, de graça.
        // É o que permite dizer, no fim da rodada, que dois erros tiveram a
        // mesma origem.
        causa_raiz: data.causa_raiz || null,
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
      // A última rodada de uma lista SEM bloco (revisão, prática dirigida,
      // prática por área) não paga Sparks e termina exatamente onde o
      // fechamento da série começa. Mostrar as duas seria dizer a mesma coisa
      // duas vezes — e, na série dirigida, sugerir "praticar esse ponto" a
      // quem está praticando justamente ele. O fechamento cobre tudo.
      const fimSemBloco = posicao === itens.length && !filtro?.banca;
      if (rodadaNum && !fimSemBloco && !rodadasProcessadasRef.current.has(rodadaNum)) {
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
          // Dois erros desta rodada com a mesma raiz: vira uma saída concreta
          // na devolutiva, em vez de só um número.
          repetido: pontoRepetido(janela),
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
        // A leitura da Mentis NÃO é mais disparada aqui. Ela era: toda rodada
        // de 10 questões chamava o Gemini sozinha, sem pedido e sem cobrança.
        // Desde 17/09 a rota cobra (`RESUMO_SESSAO_COST`), e cobrar por uma
        // chamada automática seria débito-surpresa no meio da prática — então
        // ela virou um botão dentro da devolutiva, com o preço escrito.
        //
        // A devolutiva determinística abaixo (acertos, evolução, padrões
        // calculados localmente, Sparks da rodada) continua automática e de
        // graça: ela não custa uma chamada de IA e nunca custou.
        //
        // `janelaIA` viaja junto porque o botão precisa das MESMAS respostas
        // desta rodada; recalcular na hora do clique daria outra janela, já
        // que o aluno seguiu respondendo enquanto o modal não abriu.
        const resRodada = await Promise.allSettled([pedidoRodada]).then((r) => r[0]);

        if (resRodada?.status === "fulfilled" && resRodada.value) {
          const rd = resRodada.value.data;
          devolutiva = { ...devolutiva, ...rd };
          if (typeof rd.sparks_balance === "number") setSparks(rd.sparks_balance);
        }
        // A leitura paga recebe só o que o contrato dela pede — `causa_raiz`
        // é um campo nosso, da tela.
        devolutiva.janelaIA = janela.length >= 10
          ? janela.map(({ item_id, alternativa_escolhida, acertou }) => ({ item_id, alternativa_escolhida, acertou }))
          : null;

        rodadaPendenteRef.current = devolutiva;
      }
    } catch (e) {
      setErro(errMsg(e, "Não foi possível registrar a resposta."));
    } finally {
      setSubmitting(false);
    }
  };

  // Enter responde/avança. As letras A–E não estão mais aqui: elas moram em
  // `components/questao/Alternativas`, que é quem desenha as opções — assim
  // o treino e as questões geradas ganharam o mesmo atalho sem ninguém ter
  // de lembrar de copiá-lo. Quem faz 45 questões seguidas passa a maior
  // parte do tempo nesta tela, e tirar a mão do teclado a cada questão é
  // atrito puro.
  useEffect(() => {
    const aoTeclar = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const alvo = e.target?.tagName;
      if (alvo === "INPUT" || alvo === "TEXTAREA") return;
      if (e.key !== "Enter") return;
      e.preventDefault();
      if (!result && selected && !submitting) responder();
      else if (result && !submitting) avancar();
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

  // A leitura da Mentis sobre a rodada inteira. Paga e PEDIDA — até 17/09
  // saía sozinha e de graça ao fim de cada rodada, que era a maior fuga de
  // Sparks do app. O que o aluno vê sem pedir (e sem pagar) continua sendo a
  // devolutiva determinística, que não usa IA nenhuma.
  //
  // O servidor devolve `degradado: true` quando o modelo respondeu o texto
  // neutro de indisponibilidade; nesse caso ele mesmo já estornou, e aqui só
  // resta dizer isso em vez de mostrar um resumo vazio como se fosse leitura.
  const pedirResumoDaRodada = async () => {
    const janela = rodadaResumo?.janelaIA;
    if (!janela || resumoIA?.loading) return;
    setResumoIA({ loading: true });
    try {
      const { data } = await api.post(
        "/firestore/students/me/sessao/diagnostico",
        { respostas: janela },
      );
      if (typeof data.sparks_balance === "number") setSparks(data.sparks_balance);
      if (data.degradado) {
        setResumoIA({ erro: "A Mentis não conseguiu ler esta rodada agora. Seus Sparks foram devolvidos." });
        return;
      }
      // `padroes_de_erro` da IA é uma lista de strings; a da rodada é uma
      // lista de objetos `{nome}` — nunca sobrescrever uma com a outra.
      const { padroes_de_erro: _padroesIA, ...iaCampos } = data;
      setRodadaResumo((r) => ({ ...r, ...iaCampos }));
      setResumoIA(null);
    } catch (e) {
      setResumoIA({ erro: errMsg(e, "Não foi possível gerar a leitura agora.") });
    }
  };

  // A devolutiva determinística já foi buscada em `responder()`, no mesmo
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
    setResumoIA(null);
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
      <FechamentoDaSerie
        respostas={respostasSessaoRef.current}
        filtro={filtro}
        onExit={onExit}
        xpInicial={xpInicial}
        melhorSequencia={melhorSequenciaRef.current}
        segundos={Math.round((Date.now() - inicioSerieRef.current) / 1000)}
        abrindo={abrindoPonto}
        aoPraticar={praticarPonto}
      />
    );

  const tags = [fonte.disciplina, fonte.ano, fonte.prova].filter(Boolean);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="secao-olho">
          Questão {idx + 1} de {itens.length}
        </div>
        <div className="flex items-center gap-2">
          {sparks != null && (
            <span
              className="chip border-amber-300/25 bg-amber-400/10 px-2.5 py-1 text-amber-100"
              data-testid="sparks-balance"
            >
              <Sparkles className="h-3.5 w-3.5 text-amber-300" /> {sparks}
            </span>
          )}
          {/* Sair era um texto sublinhado em cinza. Numa tela em que tudo o
              mais é botão, a única porta de saída não pode ser a única coisa
              que não parece clicável. */}
          <BotaoDeSom />
          <button onClick={onExit} className="chip pill" data-testid="questao-sair">Sair</button>
        </div>
      </div>

      <ProgressoProva
        respondidas={Math.min(answered, itens.length)}
        total={itens.length}
        pulso={pulso}
        combo={seguidas >= 3}
        rotulo={filtro?.diagnostico ? "Seu diagnóstico" : undefined}
      />

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
              <span key={i} className="rounded-full bg-sapiens-accentSoft px-3 py-1 text-xs font-semibold text-sapiens-navy">{t}</span>
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

        {/* A gramática das alternativas mora em `components/questao` desde
            2026-09-17. Ela nasceu aqui e continua idêntica — o que mudou é
            que o treino e as questões geradas passaram a usar ESTA, em vez
            de cada tela desenhar o seu próprio verde. */}
        <div className="mt-6">
          <Alternativas
            alternativas={alternativas}
            selecionada={selected}
            resultado={result}
            aoEscolher={pick}
            figurasPorLetra={figurasParaAlternativas}
            aoAmpliarFigura={setLightbox}
            testidPrefixo="alt"
          />
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
          <div
            className={`veredito veredito-sobe mt-5 ${result.acertou ? "recompensa" : ""}`}
            data-acertou={result.acertou}
            data-testid="result-banner"
          >
            {/* O selo. Um ícone de 34px à esquerda diz "certo" ou "errado"
                antes de qualquer palavra ser lida — e é ele que carrega o
                pulso de recompensa no acerto. */}
            <span className="veredito-selo">
              {result.acertou ? <Check className="h-5 w-5" strokeWidth={3} /> : <X className="h-5 w-5" strokeWidth={3} />}
            </span>
            <div className="min-w-0 flex-1">
              <div className={`text-sm font-bold ${result.acertou ? "text-emerald-700" : "text-rose-700"}`}>
                {result.feedback?.titulo || (result.acertou ? elogioAtual : "Resposta incorreta.")}
                {!result.acertou && <span className="ml-1 font-normal">(correta: {result.correta})</span>}
                {result.acertou && seguidas >= 3 && (
                  // O combo do Duolingo: o número é de acertos REAIS desta
                  // sessão, e o selo só nasce a partir de 3.
                  <span key={seguidas} className="combo-selo ml-2 align-middle" data-testid="questao-seguidas">
                    <Flame className="h-3.5 w-3.5" /> {seguidas} seguidas
                  </span>
                )}
              </div>
              {(result.feedback?.mensagens || []).map((m, i) => (
                <p key={i} className={`mt-2 text-sm leading-relaxed ${result.acertou ? "text-emerald-800" : "text-rose-800"}`}>{m}</p>
              ))}

            {!explicacao?.paragrafos && (
              <button
                onClick={pedirExplicacao}
                disabled={explicacao?.loading || semSaldoExplicacao}
                data-testid="mentis-explicacao-btn"
                className="mt-3 inline-flex items-center gap-2 rounded-full border border-sapiens-navy/15 bg-white px-3.5 py-2 text-xs font-bold text-sapiens-navy shadow-sm transition hover:border-sapiens-accent hover:shadow disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Mentis className="w-4 h-4" variante="icone" estado={explicacao?.loading ? "analise" : "neutra"} />
                {explicacao?.loading
                  ? "Mentis está pensando…"
                  : semSaldoExplicacao
                  ? `Saldo insuficiente (${MENTIS_COST} Sparks)`
                  : ilimitada
                  ? "Solução da Mentis · incluída no seu pacote"
                  : `Solução da Mentis · ${MENTIS_COST} Sparks`}
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
                  custo={precos?.intervencao ?? null}
                  ilimitada={ilimitada}
                  testid="mentis-intervencao"
                  evidencia={[{ banca: item?.fonte?.banca, ano: item?.fonte?.ano, numero: item?.fonte?.numero,
                               detalhe: `você marcou ${selected}` }]}
                />
              </div>
            )}

            {/* Fase 3: a micropergunta vem junto da resposta, quando o
                distrator marcado tem cadeia anotada e o par ainda tem poucas
                confirmações. `null` na maioria das questões, de propósito. */}
            <Microdiagnostico pergunta={result.microdiagnostico} />

            {/* Fase 2: o Professor Invisível. Também veio na mesma resposta, e
                também é `null` quase sempre — uma intervenção ativa por vez,
                com cooldown por par, decidido no servidor. Inline, nunca modal:
                interromper quem está no meio de uma prova com uma janela seria
                a diferença entre um professor e um pop-up. */}
            <ProfessorInvisivel gatilho={result.professor_invisivel} />

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
        <DialogContent className="rounded-2xl max-w-md max-h-[85dvh] overflow-y-auto" data-testid="rodada-devolutiva">
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
                  {/* O visto verde é de quem foi bem. Pintado em toda rodada,
                      ele parabenizava um 2/10 — e quem acabou de errar oito
                      percebe que a tela não está olhando para ele. */}
                  {rodadaResumo.percentual_acerto >= 60 && <Check className="w-6 h-6 text-emerald-500" />}
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

              {rodadaResumo.repetido && (
                <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3.5" data-testid="rodada-ponto-repetido">
                  <div className="text-sm font-semibold text-zinc-900">
                    {rodadaResumo.repetido.vezes} erros desta rodada começaram no mesmo ponto.
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-zinc-600">
                    Dá para praticar só ele agora, com questões novas. O que você já respondeu fica
                    guardado, e esta prova continua de onde parou quando você voltar.
                  </p>
                  <button
                    onClick={() => praticarPonto(rodadaResumo.repetido.processoId, { tipo: "repetido", linha: { processo_id: rodadaResumo.repetido.processoId } })}
                    disabled={abrindoPonto}
                    data-testid="rodada-ponto-repetido-btn"
                    className="pill btn-contorno mt-3 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-bold disabled:opacity-50"
                  >
                    {abrindoPonto ? <>Separando as questões <Loader2 className="h-3.5 w-3.5 animate-spin" /></> : <><Crosshair className="h-3.5 w-3.5" /> Praticar esse ponto</>}
                  </button>
                </div>
              )}

              {/* A leitura da Mentis: só aparece se o aluno pedir, e o preço
                  está escrito no botão. O que está acima dela nesta caixa é
                  tudo determinístico e de graça — a separação é proposital,
                  para ninguém pagar achando que pagou pela contagem. */}
              {!rodadaResumo.headline && rodadaResumo.janelaIA && (
                <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3.5" data-testid="rodada-pedir-ia">
                  <div className="text-sm font-semibold text-zinc-900">
                    Quer a leitura da Mentis sobre estas {rodadaResumo.janelaIA.length} questões?
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-zinc-600">
                    Ela procura o padrão por trás dos erros — o que se repete, e não quantos você acertou.
                  </p>
                  <button
                    onClick={pedirResumoDaRodada}
                    disabled={resumoIA?.loading || semSaldoResumo}
                    data-testid="rodada-pedir-ia-btn"
                    className="pill btn-sapiens mt-3 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {resumoIA?.loading
                      ? "A Mentis está lendo a rodada…"
                      : semSaldoResumo
                      ? `Saldo insuficiente (${RESUMO_RODADA_COST} Sparks)`
                      : ilimitada
                      ? "Ler com a Mentis · incluída no seu pacote"
                      : `Ler com a Mentis · ${RESUMO_RODADA_COST} Sparks`}
                  </button>
                  {resumoIA?.erro && (
                    <p className="mt-2 text-xs font-medium text-rose-600" data-testid="rodada-pedir-ia-erro">
                      {resumoIA.erro}
                    </p>
                  )}
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

function ProvasGrid({ onSelect, onExit, embutido = false }) {
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

  const grupos = agruparPorEdicao(provas);
  const rotuloDoAlvo = resetAlvo ? rotuloDoCaderno(resetAlvo) : null;

  return (
    <div>
      {/* "Voltar" só na tela própria (`/estudar/provas`). Dentro do Estudar
          ele levava ao Hoje no meio de uma seção — um botão de sair que não
          sai de nada que o aluno abriu. */}
      {!embutido && (
        <button onClick={onExit} className="mb-6 inline-flex items-center gap-1.5 text-sm text-white/60 hover:text-white">
          <ChevronLeft className="w-4 h-4" /> Voltar
        </button>
      )}

      {loading && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => <div key={i} className="animate-pulse h-44 bg-white/10 rounded-3xl" />)}
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

      {/* OS CADERNOS, por edição — 2026-10-10. Um cartão por área (o título
          é a matéria, com cor e glifo próprios) em vez da linha
          "ENEM 2023 · Caderno Azul" que cortava em "ENEM 20…" e deixava seis
          cadernos com a mesma cara. A edição sobe para o cabeçalho do grupo.
          A regra de nome, cor e dia é pura e testada: `lib/cadernos.js`. */}
      {!loading && !erro && grupos.length > 0 && (
        <div className="space-y-8" data-testid="provas-grade">
          {grupos.map((g) => (
            <section key={g.chave} data-testid={`provas-edicao-${g.chave.replace(/\|/g, "-")}`}>
              <div className="mb-3 flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                <h3 className="font-display text-lg font-extrabold tracking-tight text-white">{g.titulo}</h3>
                <span className="text-sm font-semibold text-white/55">{g.caderno}</span>
              </div>
              <ul className="grid grid-cols-2 gap-x-3 gap-y-5 sm:gap-x-4 md:grid-cols-4">
                {g.itens.map((p, i) => (
                  <CartaoDeCaderno
                    key={`${_blocoKey(p)}-${i}`}
                    prova={p}
                    respondidas={progresso[_blocoKey(p)]?.respondidas || 0}
                    ultima={roundStats[_blocoKey(p)]?.lastAccuracy ?? null}
                    aoAbrir={onSelect}
                    aoReiniciar={setResetAlvo}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <Dialog open={!!resetAlvo} onOpenChange={(v) => !v && setResetAlvo(null)}>
        <DialogContent className="rounded-2xl" data-testid="dialog-reiniciar-prova">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Reiniciar esta prova?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-zinc-600 leading-relaxed">
            Você vai poder responder {rotuloDoAlvo?.titulo} do {rotuloDoAlvo?.edicao} ({rotuloDoAlvo?.caderno}) do começo.
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

  const goWithLanguage = (lang) => { nav(`${ROTAS.PROVAS}/${selected.exam_id}?lang=${lang}`); setSelected(null); };

  if (loading) return <div className="grid grid-cols-2 gap-4 md:grid-cols-4">{[...Array(2)].map((_, i) => <div key={i} className="animate-pulse h-40 bg-white/10 rounded-3xl" />)}</div>;
  if (years.length === 0)
    return <div className="text-sm text-white/60">Nenhuma prova completa disponível ainda. Use a prática por caderno acima.</div>;

  // Uma lista só, do ano mais novo para o mais velho e pelo dia — o ano já
  // está escrito em cada cartão, e um cabeçalho por ano para dois cartões era
  // mais título do que conteúdo.
  const provasInteiras = years.flatMap((y) => [...grouped[y]].sort((a, b) => (a.day || 0) - (b.day || 0)));

  return (
    <div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-5 sm:gap-x-4 md:grid-cols-4">
        {provasInteiras.map((e) => (
          <li key={e.exam_id} className="list-none">
            <button
              type="button"
              onClick={() => setSelected(e)}
              className="cartao-gordo h-full w-full gap-3 p-4"
              style={{ "--de": "#C4B5FD", "--para": "#6A6BF0", "--pe": "#3A2F9A", "--tinta": "#D9D2FF" }}
              data-testid={`exam-card-${e.exam_id}`}
            >
              <span className="cartao-gordo-icone" aria-hidden="true">
                <ScrollText strokeWidth={2.2} />
              </span>
              <div className="min-w-0">
                <div className="cartao-gordo-titulo">ENEM {e.year}</div>
                <div className="cartao-gordo-sub mt-0.5">
                  {e.day}º dia{e.color ? ` · ${capitalizar(String(e.color))}` : ""}
                </div>
              </div>
              <div className="mt-auto flex items-center justify-between gap-2">
                <span className="text-xs font-semibold tabular-nums text-white/65">{e.total_questions} questões</span>
                <span className="cartao-gordo-acao">
                  Escolher <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
                </span>
              </div>
            </button>
          </li>
        ))}
      </ul>

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

/**
 * PRATICAR — a escolha do caderno e o motor de responder.
 *
 * `embutido` existe desde 2026-09-18, quando esta tela e "Cursos" viraram uma
 * aba só (`pages/Estudar.jsx`): ela passa a devolver só o conteúdo, sem casca
 * nem `<Nav />`, para caber na coluna da direita.
 *
 * `onModo` é o que faz a aba unida funcionar sem mover uma linha do motor de
 * prova. Quando o aluno escolhe um caderno, esta tela troca para `practice` —
 * e responder questão numa coluna de 560px, com o catálogo de cursos ao lado
 * disputando atenção, seria pior do que as duas abas separadas. Em vez de
 * mudar o `QuestionRunner`, ela AVISA a página, que recolhe a outra coluna e
 * devolve a largura inteira. O motor continua exatamente como está.
 */
/**
 * POR QUE ESTAS QUESTÕES — o cabeçalho da prática dirigida.
 *
 * A Mentis explicando a escolha, sem chamar modelo nenhum: o texto é montado
 * aqui com o que o motor já tinha (o ponto, o erro que mais se repete nele) e
 * com o enquadramento escrito à mão em `intervencoes._ENQUADRAMENTO`, que até
 * hoje só existia no servidor. Quem abre uma série sem saber por que ela foi
 * escolhida responde como responderia a uma prova qualquer; quem sabe o que
 * está treinando lê o enunciado procurando exatamente aquilo.
 *
 * Curto de propósito: uma frase de porquê, e os dois passos FECHADOS num
 * `<details>`. Aberto, o cabeçalho media 514px a 375px e empurrava o
 * enunciado para fora da primeira tela — explicar a escolha não pode custar
 * o começo rápido. O resto do enquadramento aparece no fechamento.
 */
function CabecalhoDirigido({ dirigida, total }) {
  const d = dirigida || {};
  const n = total === 1 ? "esta questão" : `estas ${total} questões`;
  const porque =
    d.tipo === "causa" && d.erro
      ? `Escolhi ${n} porque, nos seus erros, o que mais se repete neste ponto é «${d.erro}».`
      : d.tipo === "traco"
        ? `Escolhi ${n} porque é neste ponto que mais erros seus começam.`
        : d.tipo === "desempenho"
          ? `Escolhi ${n} porque é neste ponto que a sua medida está mais baixa.`
          : d.tipo === "repetido"
            ? `Escolhi ${n} porque mais de um erro seu começou neste ponto.`
            : `Escolhi ${n} para este ponto.`;

  return (
    <div className="mb-6" data-testid="practice-dirigida-header">
      <div className="secao-olho flex items-center gap-1.5">
        <Crosshair className="h-3.5 w-3.5" /> Prática dirigida
      </div>
      <h1 className="titulo-tela">{d.foco || "O ponto em que você mais tropeça"}</h1>
      <div className="superficie mt-4 flex items-start gap-3 p-4">
        <Mentis className="mt-0.5 h-7 w-7 shrink-0" variante="icone" />
        <div className="min-w-0 text-sm leading-relaxed text-white/70">
          <p>{porque} Nenhuma delas você respondeu antes.</p>
          {(d.objetivo || d.comoPraticar?.length > 0) && (
            <details className="mt-2 group" data-testid="practice-dirigida-passos">
              <summary className="cursor-pointer py-1 text-xs font-semibold text-[#7FD8FF]">
                O objetivo e como atacar estas questões
              </summary>
              {d.objetivo && <p className="mt-1.5 text-white/70">{d.objetivo}</p>}
              <ul className="mt-1.5 space-y-1 text-white/60">
                {(d.comoPraticar || []).map((passo, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="font-mono-alt text-[#7FD8FF]">{i + 1}.</span>
                    <span className="min-w-0">{passo}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {d.provisorio && (
            <p className="mt-1.5 text-xs text-white/45" data-testid="practice-dirigida-provisorio">
              Leitura provisória: aponta onde olhar primeiro, não é um veredito sobre você.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/** O filtro de uma lista de questões por id: a revisão espaçada manda só os
 *  ids; a prática dirigida manda também o porquê, no `state` da navegação. */
function filtroPorIds(itemIdsParam, dirigida) {
  return {
    item_ids: itemIdsParam.split(",").filter(Boolean),
    origem: dirigida ? "padrao" : "revisao",
    dirigida: dirigida || null,
  };
}

export default function Provas({ embutido = false, onModo = null }) {
  const [params] = useSearchParams();
  const areaParam = params.get("area");
  const itemIdsParam = params.get("item_ids");
  // `?diagnostico=1`: as dez do primeiro acesso, para onde o cadastro leva
  // (`lib/diagnostico.js`). O servidor escolhe quais; esta tela só responde.
  const diagnosticoParam = params.get("diagnostico") === "1";
  const nav = useNavigate();
  const location = useLocation();
  const dirigidaDaNavegacao = location.state?.dirigida || null;
  // "Praticar" abre DIRETO nos cadernos. Havia um modo `hub` antes deste:
  // uma tela inteira cujo conteúdo era um botão escrito "Começar prática de
  // questões" e, abaixo, a lista por ano. Um clique inteiro para dizer sim a
  // uma pergunta que o aluno já tinha respondido ao clicar em "Praticar" —
  // a definição de interstício.
  //
  // A opção secundária (provas oficiais por edição do ENEM) não sumiu: ela
  // agora mora ao pé da própria grade de cadernos, que é onde alguém
  // procurando "o ENEM 2019 inteiro" já está olhando.
  const [mode, setMode] = useState(areaParam || itemIdsParam || diagnosticoParam ? "practice" : "provas"); // 'provas' | 'practice'
  const [filtro, setFiltro] = useState(
    itemIdsParam
      ? filtroPorIds(itemIdsParam, dirigidaDaNavegacao)
      : diagnosticoParam
        ? { diagnostico: true }
        : areaParam
          ? { area: areaParam }
          : null,
  ); // { banca, ano, prova, disciplinas, count } | { area } | { item_ids, origem, dirigida } | { diagnostico }

  // "Mais deste ponto" e "Praticar esse ponto" navegam para ESTA MESMA rota
  // com outros ids. O React Router não remonta a página nesse caso, então o
  // filtro é refeito aqui — e o `key` do QuestionRunner (abaixo) garante que
  // a série nova começa limpa, sem a contagem da anterior.
  const ultimaNavegacao = useRef(location.key);
  useEffect(() => {
    if (location.key === ultimaNavegacao.current) return;
    ultimaNavegacao.current = location.key;
    if (!itemIdsParam) return;
    setFiltro(filtroPorIds(itemIdsParam, dirigidaDaNavegacao));
    setMode("practice");
  }, [location.key, itemIdsParam, dirigidaDaNavegacao]);

  const escolherProva = (p, opts) => { setFiltro({ ...p, reiniciar: !!opts?.reiniciar }); setMode("practice"); };

  // A página que hospeda precisa saber se estamos escolhendo ou respondendo.
  useEffect(() => { onModo?.(mode); }, [mode, onModo]);

  const conteudo = (
    <>
        {mode === "practice" && filtro?.area && (
          <div className="mb-6" data-testid="practice-area-header">
            <div className="secao-olho">Lacuna recomendada</div>
            <h1 className="titulo-tela">
              Praticando {filtro.area}
            </h1>
          </div>
        )}
        {mode === "practice" && filtro?.diagnostico && (
          <div className="mb-6" data-testid="practice-diagnostico-header">
            <div className="secao-olho">Primeiro passo</div>
            <h1 className="titulo-tela">{TOTAL_DO_DIAGNOSTICO} questões curtas, de todas as áreas.</h1>
            <p className="mt-2 max-w-lg text-sm leading-relaxed text-white/60">
              Cada resposta mostra à Mentis como você pensa — não quanto você sabe. É com elas que o seu plano é montado.
            </p>
          </div>
        )}
        {mode === "practice" && filtro?.origem === "revisao" && (
          <div className="mb-6" data-testid="practice-revisao-header">
            <div className="secao-olho">Revisão espaçada</div>
            <h1 className="titulo-tela">
              {filtro.item_ids.length > 1
                ? `${filtro.item_ids.length} questões marcadas para hoje.`
                : "A questão que estava marcada para hoje."}
            </h1>
          </div>
        )}
        {mode === "practice" && filtro?.origem === "padrao" && (
          <CabecalhoDirigido dirigida={filtro.dirigida} total={filtro.item_ids.length} />
        )}
        {mode === "practice" ? (
          <QuestionRunner
            key={location.key}
            filtro={filtro}
            onExit={() => (
              filtro?.area || filtro?.diagnostico || filtro?.origem === "padrao"
                ? nav(ROTAS.HOJE)
                : filtro?.origem === "revisao"
                  ? nav(com(ROTAS.AGENDA, ANCORAS.AGENDA_REVISOES))
                  : setMode("provas")
            )}
          />
        ) : mode === "provas" ? (
          <>
            {/* O cabeçalho: no Estudar é uma SEÇÃO (ícone, título e uma frase,
                a mesma peça do catálogo de cursos logo abaixo); na tela própria
                (`/estudar/provas`) continua sendo o título da página. O relógio
                do ENEM subiu para o cabeçalho do Estudar em 2026-10-10. */}
            {embutido ? (
              <CabecaDeSecao
                icone={Target}
                titulo="Provas do ENEM"
                frase="Escolha uma matéria: 45 questões de uma prova real. Cada resposta ensina o Sapiens sobre você."
                cor={{ de: "#5FDCFF", para: "#3E86E8", pe: "#1F4F95" }}
                testid="exam-select-title"
              />
            ) : (
              <div className="mb-10">
                <div className="secao-olho">Praticar</div>
                <h1 className="titulo-tela" data-testid="exam-select-title">
                  Escolha um caderno
                </h1>
                <p className="mt-3 max-w-lg text-white/60">
                  Cada caderno tem 45 questões de uma área, de uma prova real. Cada questão
                  que você responde aqui vira informação sobre você.
                </p>
              </div>
            )}
            <ProvasGrid onSelect={escolherProva} onExit={() => nav("/hoje")} embutido={embutido} />

            {/* A prova oficial inteira, por edição. Fica ao PÉ da grade e não
                numa tela anterior: quem procura "o ENEM 2019 completo" já está
                olhando para cadernos quando pensa nisso. */}
            <div className="mt-12">
              <CabecaDeSecao
                nivel={3}
                icone={ScrollText}
                titulo="Ou a prova inteira"
                frase="O dia inteiro de prova, na ordem oficial — como no dia do ENEM."
                cor={{ de: "#C4B5FD", para: "#6A6BF0", pe: "#3A2F9A" }}
                testid="provas-inteiras-cabeca"
              />
              <ExamsByYear />
            </div>
          </>
        ) : null}
    </>
  );

  if (embutido) return conteudo;

  return (
    <div className="min-h-screen">
      <div className="max-w-3xl mx-auto px-5 py-7 md:px-10 md:py-10">{conteudo}</div>
    </div>
  );
}
