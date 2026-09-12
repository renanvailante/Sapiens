import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import IntervencaoMentis from "../components/IntervencaoMentis";
import CardDeMelhora from "../components/CardDeMelhora";
import { ResumoDaFila } from "../components/FilaDeRevisao";
import Nav from "../components/Nav";
import OnboardingTour from "../components/OnboardingTour";
import AulasParticularesModal from "../components/AulasParticularesModal";
import Mentis from "../components/Mentis";
import { COMPETENCIAS_REDACAO } from "../constants/redacao";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import {
  ArrowRight, Sparkles, Flame, Zap, Target, Network, Trophy, ListChecks, Medal, Award,
  CheckCircle2, GraduationCap, CloudOff, RotateCw, Star, Rocket, Crown, Gem, Layers,
  CalendarDays, TrendingUp, BookOpen, Compass, Flag, PenLine, HelpCircle, PlayCircle,
  MessageSquareWarning,
} from "lucide-react";
import { useAuth } from "../lib/auth";

// ---------------- Streak / progresso semanal ----------------
// Nunca inventa atividade: ambos derivam só de `dates` (dias com pelo menos
// um evento de behavior real), vindo de GET /firestore/students/me/activity.

// Tudo aqui é calculado no fuso de São Paulo, não em UTC. O Brasil está em
// UTC-3: em UTC, quem respondia depois das 21h tinha a atividade contada no dia
// seguinte — a bolinha de "hoje" ficava apagada depois de estudar e a sequência
// podia zerar sozinha. É exatamente o horário em que vestibulando estuda, e a
// sequência é a mecânica que o traz de volta. O backend grava as datas no mesmo
// fuso (`firestore_service.dia_local`), então os dois lados combinam.
const FUSO_BR = "America/Sao_Paulo";

/** `YYYY-MM-DD` no fuso do aluno. `en-CA` porque é o locale cuja data curta já
 *  sai nesse formato — evita montar a string à mão a partir das partes. */
function diaLocal(data = new Date()) {
  return data.toLocaleDateString("en-CA", { timeZone: FUSO_BR });
}

/** Dia local deslocado de `dias` (negativo = passado). O deslocamento é feito
 *  ao meio-dia UTC para que o horário de verão, quando existir, nunca faça o
 *  passo de 24h cair no mesmo dia ou pular um. */
function diaLocalDeslocado(dias) {
  const base = new Date(`${diaLocal()}T12:00:00Z`);
  base.setUTCDate(base.getUTCDate() + dias);
  return base.toISOString().slice(0, 10);
}

function computeStreak(dates) {
  if (!dates?.length) return 0;
  const set = new Set(dates);
  // Se ainda não estudou hoje, o streak conta a partir de ontem (ainda "vivo").
  let offset = set.has(diaLocal()) ? 0 : -1;
  let streak = 0;
  while (set.has(diaLocalDeslocado(offset))) {
    streak += 1;
    offset -= 1;
  }
  return streak;
}

function computeWeek(dates) {
  const set = new Set(dates || []);
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const key = diaLocalDeslocado(-i);
    days.push({ key, active: set.has(key), isToday: i === 0 });
  }
  return days;
}

const WEEKDAY_LABEL = ["D", "S", "T", "Q", "Q", "S", "S"];

// ---------------- Conquistas ----------------
// Cada uma computada de dados que já existem, nunca de um contador à parte
// que poderia divergir do real.
const ACHIEVEMENTS = [
  { id: "10q", icon: CheckCircle2, label: "10 questões", check: (ctx) => ctx.totalRespondidas >= 10 },
  { id: "100q", icon: ListChecks, label: "100 questões", check: (ctx) => ctx.totalRespondidas >= 100 },
  { id: "250q", icon: Layers, label: "250 questões", check: (ctx) => ctx.totalRespondidas >= 250 },
  { id: "500q", icon: BookOpen, label: "500 questões", check: (ctx) => ctx.totalRespondidas >= 500 },
  { id: "1000q", icon: Crown, label: "1000 questões", check: (ctx) => ctx.totalRespondidas >= 1000 },
  { id: "streak3", icon: Flame, label: "3 dias seguidos", check: (ctx) => ctx.streak >= 3 },
  { id: "streak7", icon: Flame, label: "7 dias seguidos", check: (ctx) => ctx.streak >= 7 },
  { id: "streak14", icon: Rocket, label: "14 dias seguidos", check: (ctx) => ctx.streak >= 14 },
  { id: "streak30", icon: Star, label: "30 dias seguidos", check: (ctx) => ctx.streak >= 30 },
  { id: "streak60", icon: Gem, label: "60 dias seguidos", check: (ctx) => ctx.streak >= 60 },
  { id: "semanaPerfeita", icon: CalendarDays, label: "Semana perfeita", check: (ctx) => ctx.weekActiveDays >= 7 },
  { id: "mastery60", icon: Compass, label: "1º domínio > 60%", check: (ctx) => ctx.hubs.some((h) => (h.mastery || 0) > 60) },
  { id: "mastery80", icon: Medal, label: "1º domínio > 80%", check: (ctx) => ctx.hubs.some((h) => (h.mastery || 0) > 80) },
  { id: "mastery90", icon: Award, label: "90% em um tópico", check: (ctx) => ctx.hubs.some((h) => (h.mastery || 0) >= 90) },
  { id: "dominioTotal", icon: TrendingUp, label: "Domínio > 80% em 3 frentes", check: (ctx) => ctx.hubs.filter((h) => (h.mastery || 0) > 80).length >= 3 },
  { id: "firstExam", icon: Trophy, label: "1º simulado completo", check: (ctx) => ctx.analyses.length >= 1 },
  { id: "exam3", icon: Flag, label: "3 simulados completos", check: (ctx) => ctx.analyses.length >= 3 },
  { id: "exam10", icon: GraduationCap, label: "10 simulados completos", check: (ctx) => ctx.analyses.length >= 10 },
  { id: "rounds10", icon: Target, label: "10 rodadas de treino", check: (ctx) => ctx.rounds.length >= 10 },
  { id: "rounds50", icon: Network, label: "50 rodadas de treino", check: (ctx) => ctx.rounds.length >= 50 },
  { id: "primeiraRedacao", icon: PenLine, label: "1ª redação corrigida", check: (ctx) => ctx.redacoesCorrigidas >= 1 },
  { id: "redacao800", icon: Star, label: "800+ na redação", check: (ctx) => ctx.melhorRedacao >= 800 },
];

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

// Melhor rodada de 10 mais fraca entre os cadernos praticados (última
// tentativa de cada bloco) — usado como fallback de "próxima ação" quando o
// aluno pratica questão a questão e nunca upload um gabarito completo (o
// único caso que `latest.by_area` cobre). Sem isso, quem só usa a prática
// avulsa via `/exams` nunca sai de "ainda reunindo dados", mesmo respondendo
// centenas de questões — `analyses` continua vazio pra sempre nesse fluxo.
function weakestRoundBloco(rounds) {
  if (!rounds?.length) return null;
  const porBloco = {};
  for (const r of rounds) {
    const b = r.bloco || {};
    const chave = [b.banca, b.ano, b.prova, b.numero_min, b.numero_max].join("|");
    (porBloco[chave] = porBloco[chave] || []).push(r);
  }
  let pior = null;
  for (const lista of Object.values(porBloco)) {
    const ultima = [...lista].sort((a, b) => (a.created_at || "").localeCompare(b.created_at || "")).pop();
    if (!pior || (ultima.percentual_acerto ?? 100) < (pior.percentual_acerto ?? 100)) pior = ultima;
  }
  return pior;
}

/** O dia de HOJE no cronograma, no painel.
 *
 *  Só o dia, não a semana: o Painel responde "o que eu faço agora", e sete
 *  colunas aqui competiriam com a tela que já faz isso melhor. Quem quiser a
 *  semana clica no cabeçalho. */
function HojeNoCronograma({ semana }) {
  if (!semana) return null;
  const hoje = semana.dias?.find((d) => d.data === diaLocal());
  const temPlano = semana.plano?.desta_semana && semana.total_blocos > 0;
  const blocos = hoje?.blocos || [];
  const compromissos = hoje?.compromissos || [];

  // Sem cronograma montado E sem nenhum compromisso: o convite. Com plano mas
  // sem nada HOJE (dia de folga, por exemplo), a seção some em vez de anunciar
  // um vazio que está certo.
  if (!temPlano) {
    return (
      <section className="mt-8" data-testid="dash-cronograma-convite">
        <Link to="/cronograma" className="lift card-sapiens block rounded-2xl p-6 md:p-7">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
                <CalendarDays className="h-3.5 w-3.5" /> Cronograma
              </div>
              <p className="mt-2 font-display text-lg leading-snug tracking-tight text-zinc-950">
                Sua semana ainda não está montada.
              </p>
              <p className="mt-1 max-w-xl text-sm text-zinc-500">
                Diga (ou dite) seus compromissos e o Sapiens encaixa o estudo no que sobra —
                priorizando onde você ganha mais ponto no ENEM.
              </p>
            </div>
            <span className="pill btn-sapiens inline-flex shrink-0 items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium">
              Montar minha semana <ArrowRight className="h-4 w-4" />
            </span>
          </div>
        </Link>
      </section>
    );
  }

  if (!blocos.length && !compromissos.length) return null;

  return (
    <section className="mt-8" data-testid="dash-cronograma">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-2xl font-bold tracking-tight text-white">Hoje no seu cronograma</h2>
        <Link to="/cronograma" className="inline-flex items-center gap-1 text-xs text-[#7FD8FF] hover:underline">
          Ver a semana <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <p className="mb-4 text-sm text-white/55">
        {semana.total_concluidos}/{semana.total_blocos} blocos feitos nesta semana.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {compromissos.map((c) => (
          <div
            key={c.id}
            className="card-sapiens rounded-2xl p-4 opacity-80"
            data-testid={`dash-cronograma-compromisso-${c.id}`}
          >
            <span className="font-mono-alt text-[10px] uppercase tracking-[0.22em] text-zinc-400">
              {c.dia_inteiro ? "dia todo" : `${c.inicio}–${c.fim}`} · seu compromisso
            </span>
            <p className="mt-1 text-sm font-medium text-zinc-950">{c.titulo}</p>
          </div>
        ))}
        {blocos.map((b) => (
          <Link
            key={b.id}
            to={b.rota || "/cronograma"}
            className={`lift card-sapiens block rounded-2xl p-4 ${b.concluido ? "opacity-55" : ""}`}
            data-testid={`dash-cronograma-bloco-${b.id}`}
          >
            <span className="font-mono-alt text-[10px] uppercase tracking-[0.22em] text-zinc-400">
              {b.inicio}–{b.fim} · {b.frente_nome || b.tipo}
            </span>
            <p className={`mt-1 text-sm font-medium text-zinc-950 ${b.concluido ? "line-through" : ""}`}>
              {b.titulo}
            </p>
            {b.detalhe && <p className="mt-1 line-clamp-2 text-xs text-zinc-500">{b.detalhe}</p>}
          </Link>
        ))}
      </div>
    </section>
  );
}

// ---------------- Peças do painel ----------------

function Estatistica({ icone: Icone, rotulo, valor, sufixo, testid, tint = "text-amber-500" }) {
  return (
    <div className="card-sapiens rounded-2xl p-5" data-testid={testid}>
      <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
        {Icone && <Icone className={`w-3.5 h-3.5 ${tint}`} />} {rotulo}
      </div>
      <div className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-950">
        {valor}
        {sufixo && <span className="ml-1 text-sm font-medium text-zinc-400">{sufixo}</span>}
      </div>
    </div>
  );
}

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
  const [loaded, setLoaded] = useState(false);
  const [falhou, setFalhou] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [showAulasModal, setShowAulasModal] = useState(false);
  const nav = useNavigate();

  // Cada chamada tinha `.catch(() => valorVazio)`: com o backend fora do ar, o
  // painel carregava normalmente mostrando "0 dias de sequência", "Sparks —" e
  // "Ainda reunindo dados", e o aluno não tinha como distinguir isso de "meu
  // progresso sumiu". Alguém que acabou de estudar duas horas concluía que o
  // produto tinha perdido o trabalho dele.
  //
  // `allSettled` mantém a página utilizável quando UMA das chamadas falha, mas
  // agora registra que houve falha, para a tela dizer isso em vez de mostrar um
  // zero convincente.
  //
  // Todas são O(1): documento único do aluno no Firestore ou consulta
  // indexada no Mongo. Nenhuma varre eventos — ver
  // `project_aluno_disciplina_leitura_firestore`.
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
      // `total_respostas`, então recarregar o painel não revarre o histórico.
      api.get("/motor/perfil").then(({ data }) =>
        (data.habilidades_prioritarias || []).filter((l) => l.origem === "error_trace" && l.erro_dominante),
      ),
      // Agregado do banco de treino (uma leitura do mesmo documento) — é daqui
      // que saem as missões sugeridas e o deep-link `/treino?hab=`.
      api.get("/treino/habilidades").then(({ data }) => data.habilidades || []),
      api.get("/redacao", { params: { limit: 3 } }).then(({ data }) => data.items || []),
      // A fila de revisões de hoje. Uma leitura do MESMO documento do aluno —
      // o estado de revisão mora em `students/{uid}` junto do agregado —, e
      // não uma varredura do histórico.
      api.get("/revisao/fila").then(({ data }) => data),
      // A semana do aluno. `find_one` por chave primária no Mongo — o
      // cronograma é 1 documento por aluno, e a resposta já vem montada por
      // dia (ver `cronograma_routes._montar_semana`).
      api.get("/cronograma").then(({ data }) => data),
    ]).then((resultados) => {
      const [a, s, dates, h, respondidas, r, f, habs, reds, fila, semana] = resultados;
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
      setFalhou(resultados.some((res) => res.status === "rejected"));
      setLoaded(true);
    });
    // Tour de boas-vindas: só na primeira vez (`flags.onboarded === false` no
    // Firestore). Falha silenciosa — se o doc ainda não existir por uma
    // corrida com o provisionamento do login, o tour simplesmente não
    // aparece agora e tenta de novo no próximo carregamento do painel.
    api.get("/firestore/students/me/behavior")
      .then(({ data }) => { if (data?.flags?.onboarded === false) setShowTour(true); })
      .catch(() => {});
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const latest = analyses[0];
  const streak = computeStreak(activityDates);
  const week = computeWeek(activityDates);
  const weekActiveDays = week.filter((d) => d.active).length;

  const areaEntries = latest
    ? Object.entries(latest.by_area || {})
        .map(([area, v]) => ({ area, pct: v.total ? Math.round((100 * v.correct) / v.total) : 0, total: v.total }))
        .filter((e) => e.total > 0)
    : [];
  const weakestArea = areaEntries.length ? [...areaEntries].sort((a, b) => a.pct - b.pct)[0] : null;
  const weakestRound = !weakestArea ? weakestRoundBloco(rounds) : null;

  const rankedHubs = [...hubs].sort((a, b) => (b.mastery || 0) - (a.mastery || 0));
  const hasMasteryData = hubs.some((h) => (h.mastery || 0) > 0);

  // Redação: a última corrigida manda no card, e a competência de menor nota
  // vira um dos focos clicáveis.
  const ultimaRedacao = redacoes.find((r) => r.avaliacao) || null;
  const competenciaFraca = useMemo(() => {
    const comps = ultimaRedacao?.avaliacao?.competencias || [];
    if (!comps.length) return null;
    return [...comps].sort((a, b) => (a.nivel_pontos ?? 0) - (b.nivel_pontos ?? 0))[0];
  }, [ultimaRedacao]);
  const melhorRedacao = redacoes.reduce((m, r) => Math.max(m, r.avaliacao?.nota_total ?? 0), 0);

  // Missões sugeridas: primeiro o que o aluno já praticou e não domina, depois
  // o que ele ainda nem tocou. Nunca inventa ordem — `classificacao` e
  // `percentual` vêm do agregado real de treino.
  const missoes = useMemo(() => {
    const fracas = habilidades
      .filter((h) => h.respondidas > 0 && h.classificacao !== "forte")
      .sort((a, b) => (a.percentual ?? 100) - (b.percentual ?? 100));
    const intocadas = habilidades.filter((h) => !h.respondidas);
    return [...fracas, ...intocadas].slice(0, 4);
  }, [habilidades]);

  // "Onde focar agora": no máximo quatro cards, cada um com destino próprio.
  const focos = useMemo(() => {
    const lista = [];
    if (weakestArea) {
      const rotulo = AREA_CODE_TO_LABEL[weakestArea.area] || weakestArea.area;
      lista.push({
        key: `area-${weakestArea.area}`,
        titulo: rotulo,
        descricao: "A área com mais espaço para crescer no seu último gabarito.",
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
          descricao: "Existe uma missão curta do Treino exatamente sobre isto.",
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
        descricao: "Foi a competência que menos pontuou na sua última redação corrigida.",
        medida: `${competenciaFraca.nivel_pontos ?? 0}`,
        medidaLabel: "de 200",
        evidencia: `${competenciaFraca.nivel_pontos ?? 0} de 200 pontos nessa competência da redação`,
        treino: { href: "/redacao", rotulo: "Escrever de novo" },
      });
    }
    const hubFraco = [...hubs].filter((h) => (h.mastery || 0) > 0).sort((a, b) => a.mastery - b.mastery)[0];
    if (hubFraco && lista.length < 4) {
      lista.push({
        key: `hub-${hubFraco.hub}`,
        titulo: hubFraco.label,
        descricao: "Sua frente com o domínio estimado mais baixo até agora.",
        medida: `${hubFraco.mastery}%`,
        medidaLabel: "de domínio",
        evidencia: `${hubFraco.mastery}% de domínio estimado nessa frente`,
        treino: null,
      });
    }
    return lista.slice(0, 4);
  }, [weakestArea, habilidades, competenciaFraca, hubs]);

  // O que a Mentis recebe se o aluno perguntar algo daqui pelo ícone
  // flutuante — sem isso ela responde sem saber de que tela veio a pergunta.
  useDeclararContextoMentis(
    focos.length
      ? `No Painel. Ponto de atenção em destaque: "${focos[0].titulo}".`
      : "No Painel do Sapiens.",
  );

  const achievementCtx = {
    totalRespondidas, streak, hubs, analyses, rounds, weekActiveDays,
    redacoesCorrigidas: redacoes.filter((r) => r.avaliacao).length,
    melhorRedacao,
  };
  const achievements = ACHIEVEMENTS.map((a) => ({ ...a, unlocked: a.check(achievementCtx) }));
  const conquistadas = achievements.filter((a) => a.unlocked).length;

  if (!loaded) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="max-w-5xl mx-auto px-6 md:px-10 py-10 text-white/60">Preparando seu painel...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="max-w-5xl mx-auto px-6 md:px-10 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-2">Painel</div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="dash-title">
              Olá, {user?.name?.split(" ")[0] || "aluno"}.
            </h1>
          </div>
          <button
            onClick={() => setShowTour(true)}
            className="pill inline-flex items-center gap-1.5 text-xs text-white/55 hover:text-white bg-white/8 hover:bg-white/15 border border-white/10 px-3.5 py-2 rounded-full"
            data-testid="dash-rever-tour"
          >
            <HelpCircle className="w-3.5 h-3.5" /> Rever o guia
          </button>
        </div>

        {falhou && (
          <div
            className="mb-4 rounded-2xl border border-amber-300 bg-amber-50 px-5 py-4 flex flex-wrap items-center gap-3"
            data-testid="dash-erro-parcial"
          >
            <CloudOff className="w-5 h-5 text-amber-600 shrink-0" />
            <div className="flex-1 min-w-0 text-sm text-amber-900">
              <strong>Não conseguimos carregar tudo.</strong> Alguns números abaixo podem estar
              incompletos — isto é uma falha de conexão nossa, não perda do seu progresso.
            </div>
            <button
              onClick={carregar}
              className="pill inline-flex items-center gap-2 bg-amber-950 text-amber-50 hover:brightness-110 px-4 py-2 rounded-full text-xs font-semibold shrink-0"
              data-testid="dash-erro-retry"
            >
              <RotateCw className="w-3.5 h-3.5" /> Tentar de novo
            </button>
          </div>
        )}

        {/* HERO — a porta de entrada do produto. O botão principal abre a aba
            com todas as provas do ENEM; retomar o que estava em curso fica ao
            lado, nunca no lugar dele. */}
        <section className="card-sapiens rounded-3xl p-7 md:p-9" data-testid="dash-hero" data-tour="dash-hero">
          <div className="grid gap-7 md:grid-cols-[1.4fr_1fr] md:items-center">
            <div>
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-sapiens-accentDeep">
                Comece por aqui
              </div>
              <h2 className="mt-3 font-display text-3xl md:text-4xl font-extrabold tracking-tighter leading-[1.05] text-zinc-950">
                Todas as provas do ENEM, questão por questão.
              </h2>
              <p className="mt-3 text-sm md:text-base leading-relaxed text-zinc-600 max-w-lg">
                Escolha um caderno e responda. A cada dez questões o Sapiens fecha uma rodada e te
                devolve o que os seus erros têm em comum — e é disso que sai tudo o mais nesta tela.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => nav("/exams")}
                  className="pill btn-sapiens inline-flex items-center gap-2 px-6 py-3.5 rounded-full text-sm font-medium"
                  data-testid="dash-cta-provas"
                >
                  <PlayCircle className="w-4 h-4" /> Praticar provas do ENEM
                </button>
                {latest ? (
                  <Link
                    to={`/analysis/${latest.analysis_id}`}
                    className="pill inline-flex items-center gap-2 border border-zinc-200 text-sapiens-navy hover:border-sapiens-accent px-5 py-3 rounded-full text-sm font-medium"
                    data-testid="dash-open-analysis"
                  >
                    Continuar {latest.exam_label} <ArrowRight className="w-4 h-4" />
                  </Link>
                ) : (
                  <Link
                    to="/treino"
                    className="pill inline-flex items-center gap-2 border border-zinc-200 text-sapiens-navy hover:border-sapiens-accent px-5 py-3 rounded-full text-sm font-medium"
                    data-testid="dash-cta-treino"
                  >
                    <Compass className="w-4 h-4" /> Explorar o Treino
                  </Link>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-200 bg-white/70 p-5">
              {latest ? (
                <>
                  <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
                    Sua última leitura
                  </div>
                  <p className="mt-2 font-display text-lg leading-snug tracking-tight text-zinc-950" data-testid="dash-headline">
                    {latest.diagnostic_headline}
                  </p>
                </>
              ) : (
                <>
                  <div className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-zinc-400">
                    Sua primeira análise
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                    Responda as primeiras dez questões e o Sapiens já consegue dizer o que está por
                    trás dos seus erros — não só quantos foram.
                  </p>
                </>
              )}
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <div className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{totalRespondidas}</div>
                  <div className="text-[10px] uppercase tracking-wide text-zinc-400">questões</div>
                </div>
                <div>
                  <div className="font-display text-2xl font-extrabold tracking-tight text-zinc-950">{conquistadas}</div>
                  <div className="text-[10px] uppercase tracking-wide text-zinc-400">conquistas</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Sequência · Semana · Questões · Sparks */}
        <div className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-4" data-tour="dash-stats">
          <Estatistica icone={Flame} rotulo="Sequência" valor={streak} sufixo={streak === 1 ? "dia" : "dias"} testid="dash-streak" />

          <div className="card-sapiens rounded-2xl p-5" data-testid="dash-week">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Esta semana</div>
            <div className="mt-2 flex items-center justify-between">
              {week.map((d) => (
                <div key={d.key} className="flex flex-col items-center gap-1" data-testid={`dash-week-${d.key}`}>
                  <span className="text-[9px] text-zinc-400">{WEEKDAY_LABEL[new Date(d.key + "T00:00:00Z").getUTCDay()]}</span>
                  <span
                    className={`w-5 h-5 rounded-full ${d.active ? "bg-sapiens-accent" : "bg-zinc-100"} ${d.isToday ? "ring-2 ring-offset-2 ring-sapiens-accentSoft" : ""}`}
                  />
                </div>
              ))}
            </div>
            <div className="mt-2 text-xs text-zinc-500">{weekActiveDays}/7 dias com estudo</div>
          </div>

          <Estatistica icone={ListChecks} rotulo="Respondidas" valor={totalRespondidas} tint="text-sapiens-accentDeep" testid="dash-respondidas" />

          <Link to="/sparks" className="lift block" data-testid="dash-sparks-link">
            <Estatistica icone={Zap} rotulo="Sparks" valor={sparks ?? "—"} testid="dash-sparks" />
          </Link>
        </div>

        {/* HOJE NO CRONOGRAMA — vem antes das revisões e dos focos porque é a
            única seção com HORA: o resto do painel diz o que fazer, esta diz
            quando. Some sozinha quando o dia não tem nada marcado. */}
        <HojeNoCronograma semana={cronograma} />

        {/* REVISÕES DE HOJE — a fila viva. Vem antes de "Onde focar agora"
            porque tem data: focar é uma escolha, revisar é um compromisso que
            já foi marcado. Some quando não há nada marcado, em vez de virar um
            convite para uma tela vazia. */}
        {revisoes?.resumo?.questoes > 0 && (
          <section className="mt-8" data-testid="dash-revisoes">
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <h2 className="font-display text-2xl font-bold tracking-tight text-white">Revisões de hoje</h2>
              <Link to="/revisoes" className="inline-flex items-center gap-1 text-xs text-[#7FD8FF] hover:underline">
                Ver todas <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <p className="mb-4 text-sm text-white/55">
              Cada uma nasceu de um erro que o Sapiens conseguiu explicar — e a data de voltar a
              cobrar saiu daí.
            </p>
            <Link to="/revisoes" className="block" data-testid="dash-revisoes-link">
              <ResumoDaFila resumo={revisoes.resumo} />
            </Link>
          </section>
        )}

        {/* ONDE FOCAR AGORA — cada card leva a um lugar: a missão do Treino que
            trata aquilo, ou um pedido pronto à Mentis sobre aquilo. Nenhum
            card de erro morre em si mesmo. */}
        {focos.length > 0 && (
          <section className="mt-8" data-testid="dash-focos" data-tour="dash-foco">
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <h2 className="font-display text-2xl font-bold tracking-tight text-white">Onde focar agora</h2>
              <Link to="/cognitive-profile" className="text-xs text-[#7FD8FF] hover:underline inline-flex items-center gap-1">
                Ver perfil completo <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <p className="text-sm text-white/55 mb-4">
              Clique em qualquer card: ele abre a missão de treino daquele ponto, ou leva o assunto
              pronto para a Mentis.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
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
            </div>
          </section>
        )}

        {/* O que travou você — dificuldades com CAUSA identificada. Diferente
            de "Onde focar agora": ali a unidade é a matéria ou a habilidade;
            aqui é o modo de errar, e existe uma intervenção catalogada. */}
        {fracos.length > 0 && (
          <section className="mt-8" data-testid="dash-fracos">
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <h2 className="font-display text-2xl font-bold tracking-tight text-white">O que travou você</h2>
              <Link to="/cognitive-profile" className="text-xs text-[#7FD8FF] hover:underline inline-flex items-center gap-1">
                Ver todas <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <p className="text-sm text-white/55 mb-4">
              Não é a matéria — é o jeito de errar que se repete.
            </p>
            <div className="grid gap-4">
              {fracos.slice(0, 3).map((f) => {
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

        {/* Treino · Redação — as duas atividades da barra que não são a prova */}
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="card-sapiens rounded-2xl p-6 flex flex-col" data-testid="dash-treino" data-tour="dash-treino">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
                <Compass className="w-3.5 h-3.5" /> Treino
              </div>
              <Link to="/treino" className="text-xs text-sapiens-accentDeep hover:underline inline-flex items-center gap-1">
                Abrir o mapa <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="font-display font-bold text-lg text-zinc-950 leading-snug">
              {missoes.length ? "Suas próximas missões" : "O mapa está esperando você"}
            </div>
            {missoes.length ? (
              <div className="mt-3 space-y-2">
                {missoes.map((m) => (
                  <Link
                    key={m.hab_id}
                    to={`/treino?hab=${m.hab_id}`}
                    className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white/70 px-3.5 py-2.5 hover:border-sapiens-accent transition-colors"
                    data-testid={`dash-missao-${m.hab_id}`}
                  >
                    <span className="min-w-0 truncate text-sm text-zinc-700">{m.nome}</span>
                    <span className="shrink-0 font-mono-alt text-xs text-zinc-400">
                      {m.respondidas ? `${Math.round(m.percentual ?? 0)}%` : "nova"}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-zinc-600 leading-relaxed flex-1">
                Cada ponto de luz do mapa é uma missão curta. Domine um e o território ao redor se revela.
              </p>
            )}
          </div>

          <div className="card-sapiens rounded-2xl p-6 flex flex-col" data-testid="dash-redacao" data-tour="dash-redacao">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
                <PenLine className="w-3.5 h-3.5" /> Redação
              </div>
              <Link to="/redacao" className="text-xs text-sapiens-accentDeep hover:underline inline-flex items-center gap-1">
                Escrever <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            {ultimaRedacao ? (
              <>
                <div className="flex items-end gap-2">
                  <span className="font-display text-4xl font-extrabold tracking-tighter text-zinc-950" data-testid="dash-redacao-nota">
                    {ultimaRedacao.avaliacao.nota_total}
                  </span>
                  <span className="mb-1.5 text-sm text-zinc-400">/1000</span>
                </div>
                <div className="mt-1 text-sm text-zinc-500 truncate">{ultimaRedacao.redacao?.tema || "Sua última redação"}</div>
                <div className="mt-4 space-y-2">
                  {(ultimaRedacao.avaliacao.competencias || []).map((c) => (
                    <div key={c.id}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-zinc-600 truncate">{COMPETENCIAS_REDACAO[c.id] || c.id}</span>
                        <span className="font-mono-alt font-bold text-zinc-900 shrink-0">{c.nivel_pontos ?? 0}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-zinc-100 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-sapiens-accentSoft to-sapiens-accent"
                          style={{ width: `${Math.round(((c.nivel_pontos ?? 0) / 200) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <>
                <div className="font-display font-bold text-lg text-zinc-950 leading-snug">
                  Sua redação, corrigida nas cinco competências.
                </div>
                <p className="mt-2 text-sm text-zinc-600 leading-relaxed flex-1">
                  Escreva sobre um tema no padrão ENEM e receba a nota competência por competência —
                  e, se quiser, a leitura da Mentis sobre o que derrubou os pontos.
                </p>
                <Link
                  to="/redacao"
                  className="pill btn-sapiens mt-4 self-start inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium"
                  data-testid="dash-redacao-cta"
                >
                  Escrever uma redação <ArrowRight className="w-4 h-4" />
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Domínio estimado + próxima ação. A "próxima ação" só aparece quando
            NÃO há cards em "Onde focar agora": ali cada card já é a próxima
            ação, e clicável — repetir o mesmo conselho num segundo lugar só
            faria o aluno duvidar de qual dos dois seguir. */}
        <div className={`mt-4 grid grid-cols-1 gap-4 ${focos.length === 0 ? "md:grid-cols-2" : ""}`}>
          <div className="card-sapiens rounded-2xl p-6" data-testid="dash-mastery" data-tour="dash-mastery">
            <div className="flex items-center justify-between mb-4">
              <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Domínio estimado</div>
              <Link to="/cognitive-profile" className="text-xs text-sapiens-accentDeep hover:underline inline-flex items-center gap-1">
                <Network className="w-3.5 h-3.5" /> Mapa completo
              </Link>
            </div>
            {!hasMasteryData ? (
              <p className="text-sm text-zinc-500">Gere seu mapa cognitivo para ver seu domínio estimado por frente.</p>
            ) : (
              <div className="space-y-3">
                {rankedHubs.map((h) => (
                  <div key={h.hub} data-testid={`dash-mastery-${h.hub}`}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-zinc-700">{h.label}</span>
                      <span className="font-mono-alt font-bold text-zinc-900">{h.mastery}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-zinc-100 overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-sapiens-accentSoft to-sapiens-accent" style={{ width: `${h.mastery}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {focos.length === 0 && (
          <div className="card-sapiens rounded-2xl p-6 flex flex-col" data-testid="dash-recommendation" data-tour="dash-recommendation">
            <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-3">
              <Target className="w-3.5 h-3.5" /> Próxima ação
            </div>
            {weakestRound ? (
              <>
                <div className="font-display font-bold text-lg text-zinc-950 leading-snug">
                  O Sapiens encontrou uma lacuna.
                </div>
                <p className="mt-2 text-sm text-zinc-600 leading-relaxed flex-1">
                  Você acertou {weakestRound.percentual_acerto}% na rodada mais recente de{" "}
                  <strong>{[weakestRound.bloco?.banca, weakestRound.bloco?.ano, weakestRound.bloco?.prova].filter(Boolean).join(" ")}</strong> — vale reforçar esse caderno.
                </p>
                <button onClick={() => nav("/exams")} className="pill btn-sapiens mt-4 self-start inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium" data-testid="dash-recommendation-cta">
                  Treinar agora <ArrowRight className="w-4 h-4" />
                </button>
              </>
            ) : (
              <>
                <div className="font-display font-bold text-lg text-zinc-950 leading-snug">Ainda reunindo dados.</div>
                <p className="mt-2 text-sm text-zinc-600 leading-relaxed flex-1">Responda mais questões para o Sapiens identificar sua primeira lacuna.</p>
                <button onClick={() => nav("/exams")} className="pill btn-sapiens mt-4 self-start inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium">
                  <Sparkles className="w-4 h-4" /> Praticar
                </button>
              </>
            )}
          </div>
          )}
        </div>

        {/* Mentis — porta de entrada do chat. Fica acima do CTA de aulas de
            propósito: é a única superfície do produto que responde ao aluno
            sobre o histórico dele. */}
        <Link
          to="/mentis"
          className="lift card-sapiens mt-4 rounded-2xl p-6 md:p-7 flex flex-col md:flex-row md:items-center gap-4 group"
          data-testid="dash-mentis"
          data-tour="dash-mentis"
        >
          <Mentis className="w-14 h-14 shrink-0" estado="neutra" />
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-lg tracking-tight text-white">
              Pergunte à Mentis por que você erra.
            </div>
            <div className="mt-1 text-sm text-white/60">
              Ela lê o seu histórico inteiro antes da primeira palavra — processos fracos,
              amostra de cada um, padrão de erro por trás. Depois é conversa.
            </div>
          </div>
          <span className="pill btn-sapiens shrink-0 inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm">
            Conversar <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </Link>

        {/* Aulas particulares — CTA de alta visibilidade */}
        <div
          className="cta-calor mt-4 rounded-2xl p-6 md:p-7 flex flex-col md:flex-row md:items-center gap-4"
          data-testid="dash-aulas-particulares-banner"
          data-tour="dash-aulas"
        >
          <div className="w-12 h-12 rounded-xl bg-amber-300/15 border border-amber-300/25 text-amber-200 flex items-center justify-center shrink-0">
            <GraduationCap className="w-6 h-6" strokeWidth={1.8} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-lg tracking-tight text-amber-100">Tenha aulas conosco</div>
            <div className="mt-1 text-sm text-amber-100/70">
              Precisa de reforço em alguma área? Solicite uma aula particular e fale direto com nossa equipe pelo WhatsApp.
            </div>
          </div>
          <button
            onClick={() => setShowAulasModal(true)}
            className="btn-calor pill shrink-0 inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm"
            data-testid="dash-aulas-particulares-cta"
          >
            Solicitar aula <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Conquistas — cada uma computada de dados que já existem */}
        <div className="mt-4 card-sapiens rounded-2xl p-5" data-testid="dash-achievements" data-tour="dash-achievements">
          <div className="flex items-center justify-between mb-3">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">Conquistas</div>
            <div className="font-mono-alt text-[10px] text-zinc-400">{conquistadas}/{achievements.length}</div>
          </div>
          <div className="flex flex-wrap gap-3">
            {achievements.map((a) => (
              <div
                key={a.id}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-full border text-xs font-medium ${
                  a.unlocked ? "border-sapiens-accent bg-sapiens-accentSoft text-sapiens-navy" : "border-zinc-200 bg-zinc-50 text-zinc-400"
                }`}
                data-testid={`dash-achievement-${a.id}`}
                data-unlocked={a.unlocked}
              >
                {a.unlocked ? <CheckCircle2 className="w-3.5 h-3.5" /> : <a.icon className="w-3.5 h-3.5" />}
                {a.label}
              </div>
            ))}
          </div>
        </div>
        {/* Canal de reclamações e sugestões. Vive no menu "mais", mas um
            produto que só aceita reclamação de quem sabe procurar recebe
            reclamação de quase ninguém — daí esta linha no fim do Painel. */}
        <Link
          to="/sugestoes"
          state={{ de: "/dashboard" }}
          className="mt-4 flex flex-wrap items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-sm text-white/60 hover:text-white hover:border-white/20 transition-colors"
          data-testid="dash-sugestoes"
        >
          <MessageSquareWarning className="w-4 h-4" />
          Achou algo errado, ou tem uma ideia para o Sapiens?
          <span className="text-[#7FD8FF]">Fale com a equipe</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {loaded && showTour && <OnboardingTour onDone={() => setShowTour(false)} />}
      <AulasParticularesModal open={showAulasModal} onClose={() => setShowAulasModal(false)} />
    </div>
  );
}
