import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import IntervencaoMentis from "../components/IntervencaoMentis";
import CardDeMelhora from "../components/CardDeMelhora";
import { ResumoDaFila } from "../components/FilaDeRevisao";
import Nav, { EVENTO_SPARKS } from "../components/Nav";
import PainelDeProgresso from "../components/PainelDeProgresso";
import OnboardingTour from "../components/OnboardingTour";
import PainelDeConquistas from "../components/PainelDeConquistas";
import BotaoInstalar from "../components/InstalarApp";
import TrilhaDeMissoes from "../components/TrilhaDeMissoes";
import Mentis from "../components/Mentis";
import { COMPETENCIAS_REDACAO } from "../constants/redacao";
import { computeStreak, computeWeek, diaLocal } from "../lib/atividade";
import { avaliarConquistas } from "../lib/conquistas";
import { faixaDeDominio } from "../lib/dominio";
import { proximaQuinta, temAcessoLocal } from "../lib/live";
import PedirWhatsApp from "../components/PedirWhatsApp";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import {
  ArrowRight, Sparkles, Compass, Target, Trophy, CloudOff, RotateCw, PlayCircle,
  MessageSquareWarning, Users, GraduationCap, PenLine, Brain, Zap, CalendarDays,
  HelpCircle, Download, ChevronRight, Radio, Video,
} from "lucide-react";
import { useAuth } from "../lib/auth";

/**
 * O Painel — reescrito em 2026-09-15.
 *
 * O que ele era: catorze seções empilhadas, cada uma com um parágrafo
 * explicando a própria filosofia, dez CTAs concorrentes na mesma dobra, e a
 * peça de maior impacto visual do produto (o Mapa de Treino) reduzida a um
 * card de texto no meio da página, abaixo de quatro banners.
 *
 * O que ele é agora, nesta ordem e por este motivo:
 *
 *   1. **O Mapa** — em cinco segundos o aluno vê o que o Sapiens é. É a única
 *      superfície que mostra o produto em vez de descrevê-lo.
 *   2. **Ofensiva, nível, liga e missões do dia** — o que mudou desde ontem.
 *   3. **Conquistas** — agora clicáveis: progresso, condição e caminho.
 *   4. **Onde focar** — as dificuldades com destino, numa seção só (antes
 *      eram duas, "Onde focar agora" e "O que travou você", com cards do
 *      mesmo formato e a mesma promessa).
 *   5. **Hoje** — o que tem hora marcada: cronograma e revisões.
 *   6. **Ferramentas** — o resto do produto em grade, visível. Antes morava
 *      atrás de um menu "…" de dez linhas.
 *
 * Saíram: o parágrafo de manifesto de cada seção, o card "Próxima ação" (que
 * repetia o conselho que os cards de foco já davam), a tira de estatísticas
 * (o saldo já vive na barra; o total de questões vive no mapa) e os três
 * banners de largura total que competiam entre si.
 */

// `by_area` (do fluxo de gabarito/Analysis) usa códigos ENEM curtos; o filtro
// `area` de GET /questoes (fluxo de banco de questões) usa os rótulos
// canônicos de `_AREAS_ENEM` (server.py) — esta é a ÚNICA ponte entre as duas
// taxonomias, só para o CTA "Treinar agora" abrir a prática já filtrada.
const AREA_CODE_TO_LABEL = {
  CN: "Ciências da Natureza",
  MT: "Matemática",
  CH: "Ciências Humanas",
  LC: "Linguagens e Códigos",
  "LC-Idioma": "Linguagens e Códigos",
};

// Total de habilidades do mapa de treino (`HAB-01`..`HAB-56`). Usado só para
// desenhar "quantos pontos de 56" — o mapa de verdade é servido por
// `/treino/mapa`, e esta tela não o carrega de propósito: seriam dezenas de
// kB e uma cena 3D para um card de resumo.
const TOTAL_HABILIDADES = 56;

/** O dia de HOJE no cronograma. Só o dia, não a semana: o Painel responde "o
 *  que eu faço agora", e sete colunas aqui competiriam com a tela que já faz
 *  isso melhor. */
function HojeNoCronograma({ semana }) {
  if (!semana) return null;
  const hoje = semana.dias?.find((d) => d.data === diaLocal());
  const temPlano = semana.plano?.desta_semana && semana.total_blocos > 0;
  const blocos = hoje?.blocos || [];
  const compromissos = hoje?.compromissos || [];

  if (!temPlano) {
    return (
      <Link
        to="/cronograma"
        className="lift flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 hover:border-white/25"
        data-testid="dash-cronograma-convite"
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-[#7FD8FF]">
          <CalendarDays className="h-4.5 w-4.5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-display text-base font-bold tracking-tight text-white">
            Montar minha semana
          </span>
          <span className="block text-xs text-white/45">Grátis. O Sapiens encaixa o estudo no que sobra.</span>
        </span>
        <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
      </Link>
    );
  }

  if (!blocos.length && !compromissos.length) return null;

  return (
    <section data-testid="dash-cronograma">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-lg font-bold tracking-tight text-white">Hoje</h2>
        <Link to="/cronograma" className="-my-2 inline-flex items-center gap-1 py-2 text-xs text-[#7FD8FF] hover:underline">
          {semana.total_concluidos}/{semana.total_blocos} na semana <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <div className="grid gap-2.5 sm:grid-cols-2">
        {compromissos.map((c) => (
          <div
            key={c.id}
            className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 opacity-70"
            data-testid={`dash-cronograma-compromisso-${c.id}`}
          >
            <span className="font-mono-alt text-[10px] uppercase tracking-[0.22em] text-white/35">
              {c.dia_inteiro ? "dia todo" : `${c.inicio}–${c.fim}`}
            </span>
            <p className="mt-1 text-sm text-white/70">{c.titulo}</p>
          </div>
        ))}
        {blocos.map((b) => (
          <Link
            key={b.id}
            to={b.rota || "/cronograma"}
            className={`lift rounded-2xl border border-white/10 bg-white/[0.04] p-4 hover:border-white/25 ${b.concluido ? "opacity-50" : ""}`}
            data-testid={`dash-cronograma-bloco-${b.id}`}
          >
            <span className="font-mono-alt text-[10px] uppercase tracking-[0.22em] text-[#7FD8FF]/70">
              {b.inicio}–{b.fim} · {b.frente_nome || b.tipo}
            </span>
            <p className={`mt-1 text-sm font-medium text-white ${b.concluido ? "line-through" : ""}`}>
              {b.titulo}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}

/** Um azulejo da grade de ferramentas. `selo` mostra um número real quando
 *  existe (nota da redação, questões geradas) — nunca um enfeite. */
/**
 * O anúncio da aula ao vivo de quinta — a faixa mais chamativa do Painel
 * depois do Mapa, e de propósito: é o único compromisso com HORA MARCADA que
 * o produto tem com o aluno, e quem não souber que ela existe não entra.
 *
 * Não faz chamada nenhuma (ver `lib/live.js`): a data sai do relógio e o
 * estado real mora em `/cursos`, que é para onde o clique leva.
 */
function ChamadaDaLive() {
  const { edicao, inicio, aoVivoAgora } = proximaQuinta();
  const jaTenho = temAcessoLocal(edicao);
  const dias = Math.max(0, Math.ceil((inicio - Date.now()) / 86400000));
  const quando = inicio.toLocaleDateString("pt-BR", { day: "numeric", month: "long" });
  const hora = inicio.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  return (
    <Link
      to="/cursos"
      className="lift mt-6 flex flex-wrap items-center gap-4 rounded-2xl border border-rose-400/25 bg-gradient-to-r from-rose-500/[0.12] via-amber-400/[0.07] to-transparent p-5 hover:border-rose-400/50"
      data-testid="dash-live"
      data-tour="dash-live"
    >
      <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-rose-400/30 bg-rose-500/15 text-rose-200">
        <Radio className="h-5 w-5" strokeWidth={1.8} />
        <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-80" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
        </span>
      </span>
      <div className="min-w-0 flex-1">
        <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-rose-300/80">
          {aoVivoAgora ? "Acontecendo agora" : "Ao vivo · toda quinta"}
        </div>
        <div className="mt-0.5 font-display text-base font-bold leading-tight tracking-tight text-white md:text-lg">
          Aula ao vivo com o 1º colocado de Medicina da USP
        </div>
        <div className="mt-0.5 text-xs text-white/50">
          {aoVivoAgora
            ? "A sala está aberta. Entre agora."
            : `${quando}, às ${hora} · ${dias === 0 ? "é hoje" : dias === 1 ? "amanhã" : `faltam ${dias} dias`}`}
          {!jaTenho && " · 200 Sparks"}
        </div>
      </div>
      <span
        className={`pill inline-flex shrink-0 items-center gap-2 rounded-full px-5 py-3 text-xs font-semibold ${
          jaTenho ? "btn-vidro" : "btn-calor"
        }`}
      >
        {jaTenho ? <><Video className="h-4 w-4" /> Sua vaga está garantida</> : <>Garantir minha vaga <ArrowRight className="h-3.5 w-3.5" /></>}
      </span>
    </Link>
  );
}

function Ferramenta({ to, icone: Icone, nome, selo, destaque, testid, onClick, tour }) {
  const Conteudo = (
    <>
      <span
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border ${
          destaque ? "border-amber-300/30 bg-amber-300/15 text-amber-200" : "border-white/10 bg-white/5 text-white/60"
        }`}
      >
        <Icone className="h-5 w-5" strokeWidth={1.8} />
      </span>
      <span className="min-w-0 flex-1 text-left">
        <span className={`block text-sm font-medium ${destaque ? "text-amber-100" : "text-white"}`}>{nome}</span>
        {selo && <span className="mt-0.5 block text-[11px] text-white/40">{selo}</span>}
      </span>
      <ChevronRight className="h-4 w-4 shrink-0 text-white/20" />
    </>
  );
  const classe = [
    "macio flex items-center gap-3 border p-4",
    destaque
      ? "border-amber-300/25 bg-amber-300/[0.07] hover:border-amber-300/50"
      : "border-white/10 bg-white/[0.035] hover:border-white/25 hover:bg-white/[0.07]",
  ].join(" ");

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={classe} data-testid={testid} data-tour={tour}>
        {Conteudo}
      </button>
    );
  }
  return (
    <Link to={to} className={classe} data-testid={testid} data-tour={tour}>
      {Conteudo}
    </Link>
  );
}

// Marca de "o guia já abriu nesta sessão do navegador". Ver
// `abrirGuiaDaSessao`, dentro do componente.
const GUIA_DA_SESSAO = "sapiens:guia-da-sessao";

export default function Dashboard() {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState([]);
  const [sparks, setSparks] = useState(null);
  const [activityDates, setActivityDates] = useState([]);
  const [hubs, setHubs] = useState([]);
  const [totalRespondidas, setTotalRespondidas] = useState(0);
  const [rounds, setRounds] = useState([]);
  const [fracos, setFracos] = useState([]);
  const [habilidades, setHabilidades] = useState([]);
  const [redacoes, setRedacoes] = useState([]);
  const [revisoes, setRevisoes] = useState(null);
  const [cronograma, setCronograma] = useState(null);
  const [onboarding, setOnboarding] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [falhou, setFalhou] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const nav = useNavigate();
  const { hash } = useLocation();
  const [params, setParams] = useSearchParams();

  // Todas as chamadas são O(1): documento único do aluno no Firestore ou
  // consulta indexada no Mongo. Nenhuma varre eventos — ver
  // `project_aluno_disciplina_leitura_firestore`.
  //
  // `allSettled` mantém a página utilizável quando UMA falha, mas registra
  // que houve falha: sem isso, o backend fora do ar produzia um painel
  // impecável mostrando "0 dias de sequência" e "Sparks —", e o aluno não
  // tinha como distinguir isso de "meu progresso sumiu".
  const carregar = useCallback(() => {
    setFalhou(false);
    Promise.allSettled([
      api.get("/analyses").then(({ data }) => data),
      api.get("/firestore/students/me/sparks").then(({ data }) => data.sparks_balance),
      api.get("/firestore/students/me/activity").then(({ data }) => data.dates || []),
      api.get("/skills-map").then(({ data }) => data.hubs || []),
      api.get("/firestore/students/me/respondidas").then(({ data }) => (data.item_ids || []).length),
      api.get("/firestore/students/me/rounds").then(({ data }) => data.rounds || []),
      // Pontos fracos COM causa raiz identificada — é o que torna a
      // dificuldade clicável e tratável. Memorizado no servidor por
      // `total_respostas`.
      api.get("/motor/perfil").then(({ data }) =>
        (data.habilidades_prioritarias || []).filter((l) => l.origem === "error_trace" && l.erro_dominante),
      ),
      api.get("/treino/habilidades").then(({ data }) => data.habilidades || []),
      api.get("/redacao", { params: { limit: 3 } }).then(({ data }) => data.items || []),
      api.get("/revisao/fila").then(({ data }) => data),
      api.get("/cronograma").then(({ data }) => data),
      // O que o aluno declarou no primeiro acesso: 1 `find_one` por chave
      // primária no Mongo. É daqui que sai a meta que o cabeçalho mostra.
      api.get("/onboarding").then(({ data }) => data),
    ]).then((resultados) => {
      const [a, s, dates, h, respondidas, r, f, habs, reds, fila, semana, onb] = resultados;
      const valor = (res, vazio) => (res.status === "fulfilled" ? res.value : vazio);

      setAnalyses(valor(a, []));
      setSparks(valor(s, null));
      setActivityDates(valor(dates, []));
      setHubs(valor(h, []));
      setTotalRespondidas(valor(respondidas, 0));
      setRounds(valor(r, []));
      setFracos(valor(f, []));
      setHabilidades(valor(habs, []));
      setRedacoes(valor(reds, []));
      setRevisoes(valor(fila, null));
      setCronograma(valor(semana, null));
      setOnboarding(valor(onb, null));
      setFalhou(resultados.some((res) => res.status === "rejected"));
      setLoaded(true);
    });
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  // Uma vez por SESSÃO do navegador, não uma vez na vida: quem entra na
  // plataforma vê o guia; quem recarrega a página no meio do estudo, não — a
  // marca sobrevive ao F5 da mesma aba e morre quando a aba fecha. Entrar de
  // novo (login novo, aba nova) mostra o guia de novo, que é o pedido.
  //
  // `sessionStorage` e não `localStorage` de propósito: em `localStorage` a
  // marca duraria para sempre e o guia voltaria a ser uma vez na vida.
  const marcarGuiaDaSessao = useCallback(() => {
    try { sessionStorage.setItem(GUIA_DA_SESSAO, "1"); } catch { /* armazenamento bloqueado */ }
  }, []);

  const abrirGuiaDaSessao = useCallback(() => {
    try {
      if (sessionStorage.getItem(GUIA_DA_SESSAO)) return;
    } catch { /* armazenamento bloqueado: mostra o guia, é o comportamento pedido */ }
    marcarGuiaDaSessao();
    setShowTour(true);
  }, [marcarGuiaDaSessao]);

  // O guia da Mentis. Três portas: `?guia=1` (com que `/bem-vindo` termina),
  // os botões "Guia" / "Rever o guia", e a ABERTURA AUTOMÁTICA a cada entrada
  // na plataforma. A porta antiga (`flags.onboarded === false` no Firestore)
  // continua mandando o aluno para `/bem-vindo` — o tour é a segunda metade
  // daquela conversa, não um onboarding paralelo.
  // `?guia=1` num efeito próprio, que OUVE a URL: quem clica em "Rever o guia"
  // no lançador já estando no Painel só muda a query — não há remontagem, e um
  // efeito de montagem não veria esse clique nunca.
  useEffect(() => {
    if (!params.get("guia")) return;
    marcarGuiaDaSessao();
    setShowTour(true);
    const limpo = new URLSearchParams(params);
    limpo.delete("guia");
    setParams(limpo, { replace: true });
  }, [params, setParams, marcarGuiaDaSessao]);

  useEffect(() => {
    if (params.get("guia")) return; // tratado no efeito acima
    // `sessionStorage`: a marca que `/bem-vindo` deixa ao ser pulado ou
    // concluído. Sem ela, um PUT que falhou (rede oscilando) deixava
    // `flags.onboarded` em `false` no servidor e esta linha mandava o aluno
    // de volta ao onboarding — que o devolveria para cá — em laço.
    let jaPassouPeloBemVindo = false;
    try {
      jaPassouPeloBemVindo = Boolean(sessionStorage.getItem("sapiens:onboarding-visto"));
    } catch { /* navegador com armazenamento bloqueado: segue o fluxo normal */ }
    if (jaPassouPeloBemVindo) {
      abrirGuiaDaSessao();
      return;
    }
    api.get("/firestore/students/me/behavior")
      .then(({ data }) => {
        // Primeiro acesso de todos: `/bem-vindo` vem antes, e ele termina
        // mandando para cá com `?guia=1`. Abrir o tour aqui só faria o balão
        // piscar meio segundo antes do redirecionamento.
        if (data?.flags?.onboarded === false) nav("/bem-vindo", { replace: true });
        else abrirGuiaDaSessao();
      })
      // Falha de rede não pode custar o guia: ele não depende de nada do
      // servidor para ser exibido.
      .catch(() => abrirGuiaDaSessao());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // `/dashboard#missoes` é o endereço que a Mentis e o guia usam para levar
  // às missões do dia. O React Router empurra a URL sem rolar a página (é
  // navegação de aplicação, não do documento), então a rolagem é feita aqui —
  // depois do `loaded`, senão o alvo ainda não existe no DOM.
  useEffect(() => {
    if (!loaded || hash !== "#missoes") return;
    document.getElementById("missoes")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [loaded, hash]);

  // O saldo muda DENTRO desta página (resgatar missão credita sem trocar de
  // rota). Só o saldo é relido — recarregar o painel a cada moeda seria pagar
  // dez chamadas por uma.
  useEffect(() => {
    const relerSaldo = () =>
      api.get("/firestore/students/me/sparks")
        .then(({ data }) => setSparks(data.sparks_balance))
        .catch(() => {});
    window.addEventListener(EVENTO_SPARKS, relerSaldo);
    return () => window.removeEventListener(EVENTO_SPARKS, relerSaldo);
  }, []);

  const latest = analyses[0];
  const streak = computeStreak(activityDates);
  const weekActiveDays = computeWeek(activityDates).filter((d) => d.active).length;

  const areaEntries = latest
    ? Object.entries(latest.by_area || {})
        .map(([area, v]) => ({ area, pct: v.total ? Math.round((100 * v.correct) / v.total) : 0, total: v.total }))
        .filter((e) => e.total > 0)
    : [];
  const weakestArea = areaEntries.length ? [...areaEntries].sort((a, b) => a.pct - b.pct)[0] : null;

  const rankedHubs = [...hubs].sort((a, b) => (b.mastery || 0) - (a.mastery || 0));
  const hasMasteryData = hubs.some((h) => (h.mastery || 0) > 0);

  const ultimaRedacao = redacoes.find((r) => r.avaliacao) || null;
  const competenciaFraca = useMemo(() => {
    const comps = ultimaRedacao?.avaliacao?.competencias || [];
    if (!comps.length) return null;
    return [...comps].sort((a, b) => (a.nivel_pontos ?? 0) - (b.nivel_pontos ?? 0))[0];
  }, [ultimaRedacao]);
  const melhorRedacao = redacoes.reduce((m, r) => Math.max(m, r.avaliacao?.nota_total ?? 0), 0);

  // A ordem das missões (o que já foi praticado e não domina primeiro, depois
  // o que ainda nem foi tocado) mora em `TrilhaDeMissoes` — é ela que desenha
  // o caminho, e duas cópias da mesma ordem em telas diferentes divergem.
  const pontosTocados = habilidades.filter((h) => h.respondidas > 0).length;
  const pontosDominados = habilidades.filter((h) => h.classificacao === "forte").length;

  // "Onde focar": área mais fraca do último gabarito, habilidades fracas do
  // treino, competência fraca da redação e — logo depois — as dificuldades
  // com CAUSA identificada. Uma seção só: antes eram duas, com o mesmo
  // formato de card e a mesma promessa, e o aluno tinha de descobrir sozinho
  // por que a mesma coisa aparecia em dois lugares.
  const focos = useMemo(() => {
    const lista = [];
    if (weakestArea) {
      const rotulo = AREA_CODE_TO_LABEL[weakestArea.area] || weakestArea.area;
      lista.push({
        key: `area-${weakestArea.area}`,
        titulo: rotulo,
        descricao: "Sua área mais fraca no último gabarito.",
        medida: `${weakestArea.pct}%`,
        medidaLabel: "de acerto",
        evidencia: `${weakestArea.pct}% de acerto em ${weakestArea.total} questões dessa área`,
        treino: AREA_CODE_TO_LABEL[weakestArea.area]
          ? { href: `/exams?area=${encodeURIComponent(rotulo)}`, rotulo: "Praticar a área" }
          : null,
      });
    }
    habilidades
      .filter((h) => h.respondidas > 0 && h.classificacao === "fraco")
      .sort((a, b) => (a.percentual ?? 100) - (b.percentual ?? 100))
      .slice(0, 2)
      .forEach((h) => {
        lista.push({
          key: `hab-${h.hab_id}`,
          titulo: h.nome,
          descricao: "Há uma missão curta do mapa sobre isto.",
          medida: `${Math.round(h.percentual ?? 0)}%`,
          medidaLabel: "no treino",
          evidencia: `${h.acertos} de ${h.respondidas} questões certas nessa habilidade`,
          treino: { href: `/treino?hab=${h.hab_id}`, rotulo: "Abrir a missão" },
        });
      });
    if (competenciaFraca) {
      const rotulo = COMPETENCIAS_REDACAO[competenciaFraca.id] || competenciaFraca.id;
      lista.push({
        key: `red-${competenciaFraca.id}`,
        titulo: `Redação · ${rotulo}`,
        descricao: "A competência que menos pontuou.",
        medida: `${competenciaFraca.nivel_pontos ?? 0}`,
        medidaLabel: "de 200",
        evidencia: `${competenciaFraca.nivel_pontos ?? 0} de 200 pontos nessa competência da redação`,
        treino: { href: "/redacao", rotulo: "Escrever de novo" },
      });
    }
    return lista.slice(0, 3);
  }, [weakestArea, habilidades, competenciaFraca]);

  useDeclararContextoMentis(
    focos.length ? `No Painel. Ponto de atenção em destaque: "${focos[0].titulo}".` : "No Painel do Sapiens.",
  );

  const conquistas = avaliarConquistas({
    totalRespondidas, streak, hubs, analyses, rounds, weekActiveDays,
    redacoesCorrigidas: redacoes.filter((r) => r.avaliacao).length,
    melhorRedacao,
  });
  const feitas = conquistas.filter((c) => c.desbloqueada).length;

  if (!loaded) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="mx-auto max-w-5xl px-6 py-10 text-white/60 md:px-10">Preparando seu painel...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-6 py-8 md:px-10 md:py-10">
        {/* CABEÇALHO — nome, meta declarada e a porta do guia. Nada mais. */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h1
              className="font-display text-3xl font-extrabold tracking-tighter text-white md:text-4xl"
              data-testid="dash-title"
            >
              Olá, {user?.name?.split(" ")[0] || "aluno"}.
            </h1>
            {onboarding?.meta && (
              <span
                className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/60"
                data-testid="dash-meta"
                title="Sua meta declarada no primeiro acesso"
              >
                <Target className="h-3.5 w-3.5 text-[#7FD8FF]" />
                Meta: {onboarding.meta.acertos_min}–{onboarding.meta.acertos_max} acertos
              </span>
            )}
          </div>
          <button
            onClick={() => setShowTour(true)}
            // `ml-auto`: a 375px o cabeçalho quebra em duas linhas e, sem
            // isto, o botão do guia caía alinhado à ESQUERDA embaixo do nome,
            // parecendo um segundo título.
            className="pill ml-auto inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/8 px-3.5 py-2 text-xs text-white/55 hover:bg-white/15 hover:text-white"
            data-testid="dash-rever-tour"
          >
            <HelpCircle className="h-3.5 w-3.5" /> Guia
          </button>
        </div>

        {falhou && (
          <div
            className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border border-amber-300/30 bg-amber-500/10 px-5 py-4"
            data-testid="dash-erro-parcial"
          >
            <CloudOff className="h-5 w-5 shrink-0 text-amber-300" />
            <div className="min-w-0 flex-1 text-sm text-amber-100">
              <strong>Não conseguimos carregar tudo.</strong> É falha de conexão nossa, não perda do seu progresso.
            </div>
            <button
              onClick={carregar}
              className="pill inline-flex shrink-0 items-center gap-2 rounded-full bg-amber-950 px-4 py-2 text-xs font-semibold text-amber-50 hover:brightness-110"
              data-testid="dash-erro-retry"
            >
              <RotateCw className="h-3.5 w-3.5" /> Tentar de novo
            </button>
          </div>
        )}

        {/* ---------------------------------------------------------------
            1. O MAPA. A vitrine do produto, e a primeira coisa na página.
            --------------------------------------------------------------- */}
        <section className="mapa-vitrine relative overflow-hidden rounded-3xl p-6 md:p-8" data-testid="dash-hero" data-tour="dash-mapa">
          <div className="relative grid gap-6 md:grid-cols-[1.35fr_1fr] md:items-center">
            <div>
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-[#7FD8FF]/80">
                Mapa de Treino
              </div>
              <h2 className="mt-2 font-display text-3xl font-extrabold leading-[1.05] tracking-tighter text-white md:text-4xl">
                {pontosTocados > 0
                  ? "Seu território continua se revelando."
                  : "Um mapa de 56 pontos. Você começa com um."}
              </h2>
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => nav("/treino")}
                  className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-sm font-medium"
                  data-testid="dash-cta-mapa"
                >
                  <Compass className="h-4 w-4" /> Abrir o mapa
                </button>
                <button
                  onClick={() => nav("/exams")}
                  className="pill btn-vidro inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm"
                  data-testid="dash-cta-provas"
                  data-tour="dash-provas"
                >
                  <PlayCircle className="h-4 w-4" /> Provas do ENEM
                </button>
              </div>

              {/* Os números que provam o mapa, sem uma frase para explicá-los. */}
              <div className="mt-6 flex flex-wrap gap-x-7 gap-y-3">
                {[
                  { n: pontosTocados, de: TOTAL_HABILIDADES, rotulo: "pontos explorados" },
                  { n: pontosDominados, rotulo: "dominados" },
                  { n: totalRespondidas, rotulo: "questões" },
                ].map((x) => (
                  <div key={x.rotulo}>
                    <div className="font-display text-2xl font-extrabold tracking-tight text-white">
                      {x.n}
                      {x.de != null && <span className="text-base text-white/30">/{x.de}</span>}
                    </div>
                    <div className="text-[10px] uppercase tracking-wide text-white/35">{x.rotulo}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* A trilha. O caminho de entrada no mapa — e a peça que faz o
                Painel PARECER o produto em vez de descrevê-lo. */}
            <div className="rounded-[26px] border border-white/10 bg-black/25 p-4 pb-9">
              <div className="mb-3 text-center font-mono-alt text-[10px] uppercase tracking-[0.25em] text-white/35">
                Seu caminho
              </div>
              <TrilhaDeMissoes habilidades={habilidades} limite={4} testid="dash-trilha" />
            </div>
          </div>
        </section>

        {/* A AULA AO VIVO DE QUINTA — logo abaixo do Mapa, que é a primeira
            dobra. É o único compromisso com hora marcada do produto. */}
        <ChamadaDaLive />

        {/* Quem ainda não tem WhatsApp na conta (conta antiga, ou entrou pelo
            Google): é por ele que o link da live chega. Some sozinho depois
            de respondido. */}
        <div className="mt-4">
          <PedirWhatsApp compacto testid="dash-pedir-whatsapp" />
        </div>

        {/* DOMÍNIO POR FRENTE — com NOME, não só porcentagem (ver
            `lib/dominio.js`: a régua da escola não é esta, e o aluno não
            deveria ter de inventar uma). Some inteira enquanto não há medida,
            em vez de mostrar quatro barras zeradas. */}
        {hasMasteryData && (
          <section className="mt-6" data-testid="dash-mastery" data-tour="dash-mastery">
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <h2 className="font-display text-lg font-bold tracking-tight text-white">Seu domínio</h2>
              <Link to="/cognitive-profile" className="-my-2 inline-flex items-center gap-1 py-2 text-xs text-[#7FD8FF] hover:underline">
                Detalhes <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="grid gap-2.5 sm:grid-cols-2">
              {rankedHubs.map((h) => {
                const faixa = faixaDeDominio(h.mastery);
                return (
                  <div
                    key={h.hub}
                    className="macio border border-white/10 bg-white/[0.035] p-4"
                    data-testid={`dash-mastery-${h.hub}`}
                  >
                    <div className="mb-2 flex items-baseline justify-between gap-2">
                      <span className="truncate text-sm text-white/80">{h.label}</span>
                      <span
                        className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold"
                        style={{ color: faixa.cor, background: `${faixa.cor}1F` }}
                      >
                        {faixa.nome}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full transition-[width] duration-500"
                        style={{ width: `${faixa.valor}%`, background: `linear-gradient(90deg, ${faixa.cor}, #8B7BFF)` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ---------------------------------------------------------------
            2. OFENSIVA · NÍVEL · LIGA · MISSÕES DO DIA
            `id="missoes"`: a Mentis e o guia levam direto até aqui.
            --------------------------------------------------------------- */}
        <div className="mt-8 scroll-mt-24" id="missoes" data-tour="dash-missoes">
          <PainelDeProgresso />
        </div>

        {/* ---------------------------------------------------------------
            3. CONQUISTAS — clicáveis
            --------------------------------------------------------------- */}
        <section className="mt-8" data-testid="dash-achievements" data-tour="dash-conquistas">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="flex items-center gap-2 font-display text-lg font-bold tracking-tight text-white">
              <Trophy className="h-4 w-4 text-[#7FD8FF]" /> Conquistas
            </h2>
            <Link to="/conquistas" className="-my-2 inline-flex items-center gap-1 py-2 text-xs text-[#7FD8FF] hover:underline">
              {feitas}/{conquistas.length} <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <PainelDeConquistas
            contexto={{
              totalRespondidas, streak, hubs, analyses, rounds, weekActiveDays,
              redacoesCorrigidas: redacoes.filter((r) => r.avaliacao).length,
              melhorRedacao,
            }}
            limite={8}
            testid="dash-conquistas-grade"
          />
        </section>

        {/* ---------------------------------------------------------------
            4. ONDE FOCAR — uma seção só, cada card com destino próprio
            --------------------------------------------------------------- */}
        {(focos.length > 0 || fracos.length > 0) && (
          <section className="mt-8" data-testid="dash-focos" data-tour="dash-foco">
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <h2 className="font-display text-lg font-bold tracking-tight text-white">Onde focar</h2>
              <Link to="/cognitive-profile" className="-my-2 inline-flex items-center gap-1 py-2 text-xs text-[#7FD8FF] hover:underline">
                Ver tudo <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {focos.map((f) => (
                <CardDeMelhora
                  key={f.key}
                  titulo={f.titulo}
                  descricao={f.descricao}
                  medida={f.medida}
                  medidaLabel={f.medidaLabel}
                  treino={f.treino}
                  assunto={f.titulo}
                  evidencia={f.evidencia}
                  onSaldo={setSparks}
                  testid={`dash-foco-${f.key}`}
                />
              ))}
              {/* Dificuldades com CAUSA identificada. Mesmo formato de card,
                  mesma seção: a diferença (modo de errar x matéria) aparece
                  no rótulo do topo, não numa segunda seção com outro título. */}
              {fracos.slice(0, 2).map((f) => {
                const hab = (f.habilidades || [])[0];
                return (
                  <CardDeMelhora
                    key={f.processo_id}
                    rotuloTopo="Causa identificada"
                    titulo={f.erro_dominante.nome}
                    descricao={f.processo_nome}
                    medida={f.percentual_acerto != null ? `${Math.round(f.percentual_acerto)}%` : null}
                    medidaLabel="de acerto"
                    treino={hab ? { href: `/treino?hab=${hab.id}`, rotulo: "Treinar isto" } : null}
                    assunto={f.processo_nome}
                    evidencia={`padrão de erro "${f.erro_dominante.nome}" identificado nas minhas respostas`}
                    onSaldo={setSparks}
                    testid={`dash-intervencao-${f.processo_id}`}
                  >
                    <IntervencaoMentis
                      erroId={f.erro_dominante.id}
                      processoId={f.processo_id}
                      causaNome={f.erro_dominante.nome}
                      processoNome={f.processo_nome}
                      sparks={sparks}
                      onSparks={setSparks}
                      testid={`dash-intervencao-${f.processo_id}-tratamento`}
                    />
                  </CardDeMelhora>
                );
              })}
            </div>
          </section>
        )}

        {/* ---------------------------------------------------------------
            5. HOJE — o que tem hora marcada
            --------------------------------------------------------------- */}
        <div className="mt-8 space-y-3" data-tour="dash-hoje">
          <HojeNoCronograma semana={cronograma} />
          {revisoes?.resumo?.questoes > 0 && (
            <Link to="/revisoes" className="block" data-testid="dash-revisoes">
              <ResumoDaFila resumo={revisoes.resumo} />
            </Link>
          )}
        </div>

        {/* ---------------------------------------------------------------
            6. A MENTIS — uma linha, não um banner de três
            --------------------------------------------------------------- */}
        <Link
          to="/mentis"
          className="lift mt-8 flex items-center gap-4 rounded-2xl border border-[#4FD9FF]/20 bg-[#4FD9FF]/[0.06] p-4 hover:border-[#4FD9FF]/45"
          data-testid="dash-mentis"
          data-tour="dash-mentis"
        >
          <Mentis className="h-11 w-11 shrink-0" estado="neutra" />
          <div className="min-w-0 flex-1">
            <div className="font-display text-base font-bold tracking-tight text-white">
              Pergunte à Mentis por que você erra.
            </div>
            <div className="text-xs text-white/45">Ela lê o seu histórico inteiro antes da primeira palavra.</div>
          </div>
          <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
        </Link>

        {/* ---------------------------------------------------------------
            7. FERRAMENTAS — o resto do produto, visível
            --------------------------------------------------------------- */}
        <section className="mt-8" data-testid="dash-ferramentas">
          <h2 className="mb-3 font-display text-lg font-bold tracking-tight text-white">Ferramentas</h2>
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            <Ferramenta
              to="/redacao"
              icone={PenLine}
              nome="Redação"
              selo={ultimaRedacao ? `Sua melhor: ${melhorRedacao}/1000` : "Nota nas 5 competências"}
              testid="dash-redacao"
              tour="dash-redacao"
            />
            <Ferramenta
              to="/minhas-questoes"
              icone={Sparkles}
              nome="Questões geradas"
              selo="A Mentis cria sobre a sua lacuna"
              testid="dash-minhas-questoes"
              tour="dash-gerar"
            />
            <Ferramenta
              to="/cognitive-profile"
              icone={Brain}
              nome="Meu desempenho"
              selo="Por que você erra, não quanto"
              testid="dash-desempenho"
              tour="dash-desempenho"
            />
            <Ferramenta
              to="/sparks"
              icone={Zap}
              nome="Sparks"
              selo={sparks != null ? `Saldo: ${sparks}` : "Saldo e pacotes"}
              testid="dash-sparks"
              tour="dash-sparks"
            />
            <Ferramenta
              to="/comunidade"
              icone={Users}
              nome="Comunidade"
              selo="Responder rende Sparks"
              testid="dash-comunidade"
              tour="dash-comunidade"
            />
            <Ferramenta
              to="/cursos"
              icone={Radio}
              nome="Aula ao vivo de quinta"
              selo="Com o 1º colocado de Medicina da USP · 200 Sparks"
              destaque
              testid="dash-cursos"
              tour="dash-cursos"
            />
            <Ferramenta
              to="/aulas"
              icone={GraduationCap}
              nome="Aulas com a USP"
              selo="Aula particular com alunos de Medicina da USP"
              destaque
              testid="dash-aulas-particulares-cta"
              tour="dash-aulas"
            />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2" data-tour="dash-extras">
            {/* Some sozinho quando o Sapiens já está instalado. */}
            <BotaoInstalar
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-2 text-xs text-white/50 transition-colors hover:text-white"
              testid="dash-instalar"
            >
              <Download className="h-3.5 w-3.5" /> Instalar o Sapiens no aparelho
            </BotaoInstalar>
            <Link
              to="/sugestoes"
              state={{ de: "/dashboard" }}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-2 text-xs text-white/50 transition-colors hover:text-white"
              data-testid="dash-sugestoes"
            >
              <MessageSquareWarning className="h-3.5 w-3.5" /> Achou um erro? Tem uma ideia?
            </Link>
          </div>
        </section>
      </div>

      {loaded && showTour && <OnboardingTour onDone={() => setShowTour(false)} />}
    </div>
  );
}
