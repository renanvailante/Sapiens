import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import OnboardingTour from "../components/OnboardingTour";
import AulasParticularesModal from "../components/AulasParticularesModal";
import { ArrowRight, Sparkles, Flame, Zap, Target, Network, Trophy, ListChecks, Medal, Award, CheckCircle2, GraduationCap } from "lucide-react";
import { useAuth } from "../lib/auth";

// ---------------- Streak / progresso semanal ----------------
// Nunca inventa atividade: ambos derivam só de `dates` (dias com pelo menos
// um evento de behavior real), vindo de GET /firestore/students/me/activity.

function computeStreak(dates) {
  if (!dates?.length) return 0;
  const set = new Set(dates);
  const today = new Date();
  const cursor = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  // Se ainda não estudou hoje, o streak conta a partir de ontem (ainda "vivo").
  const todayKey = cursor.toISOString().slice(0, 10);
  if (!set.has(todayKey)) cursor.setUTCDate(cursor.getUTCDate() - 1);
  let streak = 0;
  while (set.has(cursor.toISOString().slice(0, 10))) {
    streak += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return streak;
}

function computeWeek(dates) {
  const set = new Set(dates || []);
  const today = new Date();
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
    d.setUTCDate(d.getUTCDate() - i);
    const key = d.toISOString().slice(0, 10);
    days.push({ key, active: set.has(key), isToday: i === 0 });
  }
  return days;
}

const WEEKDAY_LABEL = ["D", "S", "T", "Q", "Q", "S", "S"];

// ---------------- Conquistas ----------------
// Só 5, deliberadamente (o brief pede "poucas conquistas significativas") —
// cada uma computada de dados que já existem, nunca de um contador à parte
// que poderia divergir do real.
const ACHIEVEMENTS = [
  { id: "100q", icon: ListChecks, label: "100 questões", check: (ctx) => ctx.totalRespondidas >= 100 },
  { id: "streak7", icon: Flame, label: "7 dias seguidos", check: (ctx) => ctx.streak >= 7 },
  { id: "mastery80", icon: Medal, label: "1º domínio > 80%", check: (ctx) => ctx.hubs.some((h) => (h.mastery || 0) > 80) },
  { id: "mastery90", icon: Award, label: "90% em um tópico", check: (ctx) => ctx.hubs.some((h) => (h.mastery || 0) >= 90) },
  { id: "firstExam", icon: Trophy, label: "1º simulado completo", check: (ctx) => ctx.analyses.length >= 1 },
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

export default function Dashboard() {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState([]);
  const [sparks, setSparks] = useState(null);
  const [activityDates, setActivityDates] = useState([]);
  const [hubs, setHubs] = useState([]);
  const [totalRespondidas, setTotalRespondidas] = useState(0);
  const [rounds, setRounds] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [showAulasModal, setShowAulasModal] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    Promise.all([
      api.get("/analyses").then(({ data }) => data).catch(() => []),
      api.get("/firestore/students/me/sparks").then(({ data }) => data.sparks_balance).catch(() => null),
      api.get("/firestore/students/me/activity").then(({ data }) => data.dates || []).catch(() => []),
      api.get("/skills-map").then(({ data }) => data.hubs || []).catch(() => []),
      api.get("/firestore/students/me/respondidas").then(({ data }) => (data.item_ids || []).length).catch(() => 0),
      api.get("/firestore/students/me/rounds").then(({ data }) => data.rounds || []).catch(() => []),
    ]).then(([a, s, dates, h, respondidas, r]) => {
      setAnalyses(a);
      setSparks(s);
      setTotalRespondidas(respondidas);
      setActivityDates(dates);
      setHubs(h);
      setRounds(r);
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

  const achievementCtx = { totalRespondidas, streak, hubs, analyses };
  const achievements = ACHIEVEMENTS.map((a) => ({ ...a, unlocked: a.check(achievementCtx) }));

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
        <div className="mb-8">
          <div className="font-mono-alt text-xs uppercase tracking-[0.35em] text-white/50 mb-2">Painel</div>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-white" data-testid="dash-title">
            Olá, {user?.name?.split(" ")[0] || "aluno"}.
          </h1>
        </div>

        {/* Hero: continuar de onde parou */}
        {!latest ? (
          <div className="card-sapiens rounded-2xl p-10 text-center" data-tour="dash-continue">
            <div className="font-display text-2xl font-bold tracking-tight text-zinc-950">Sua primeira análise está a um clique.</div>
            <p className="mt-2 text-zinc-500 max-w-md mx-auto">Escolha uma prova, envie suas respostas e revelaremos os padrões cognitivos por trás delas.</p>
            <button onClick={() => nav("/exams")} className="pill btn-sapiens mt-6 inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-medium" data-testid="dash-cta-first">
              Começar <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="card-sapiens rounded-2xl p-8" data-testid="dash-continue" data-tour="dash-continue">
            <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-sapiens-accentDeep">Continue de onde parou · {latest.exam_label}</div>
            <div className="mt-4 font-display text-2xl md:text-3xl tracking-tight leading-tight text-zinc-950" data-testid="dash-headline">
              {latest.diagnostic_headline}
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link to={`/analysis/${latest.analysis_id}`} className="pill btn-sapiens inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium" data-testid="dash-open-analysis">
                Continuar <ArrowRight className="w-4 h-4" />
              </Link>
              <button onClick={() => nav("/exams")} className="pill inline-flex items-center gap-2 border border-zinc-200 text-sapiens-navy hover:border-sapiens-accent px-5 py-2.5 rounded-full text-sm font-medium" data-testid="dash-practice">
                Praticar questões
              </button>
            </div>
          </div>
        )}

        {/* Aulas particulares — CTA de alta visibilidade */}
        <div
          className="mt-4 rounded-2xl p-6 md:p-7 flex flex-col md:flex-row md:items-center gap-4 bg-gradient-to-r from-amber-300 to-amber-400 shadow-[0_20px_50px_-25px_rgba(217,158,10,0.6)]"
          data-testid="dash-aulas-particulares-banner"
        >
          <div className="w-12 h-12 rounded-xl bg-white/40 text-amber-950 flex items-center justify-center shrink-0">
            <GraduationCap className="w-6 h-6" strokeWidth={1.8} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-lg tracking-tight text-amber-950">Tenha aulas conosco</div>
            <div className="mt-1 text-sm text-amber-900/80">
              Precisa de reforço em alguma área? Solicite uma aula particular e fale direto com nossa equipe pelo WhatsApp.
            </div>
          </div>
          <button
            onClick={() => setShowAulasModal(true)}
            className="pill shrink-0 inline-flex items-center justify-center gap-2 bg-amber-950 text-amber-50 hover:brightness-110 px-6 py-3 rounded-full text-sm font-semibold"
            data-testid="dash-aulas-particulares-cta"
          >
            Solicitar aula <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Sequência · Semana · Sparks */}
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4" data-tour="dash-stats">
          <div className="card-sapiens rounded-2xl p-5" data-testid="dash-streak">
            <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
              <Flame className="w-3.5 h-3.5 text-amber-500" /> Sequência
            </div>
            <div className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-950">
              {streak} {streak === 1 ? "dia" : "dias"}
            </div>
          </div>

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

          <div className="card-sapiens rounded-2xl p-5" data-testid="dash-sparks">
            <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400">
              <Zap className="w-3.5 h-3.5 text-amber-500" /> Sparks
            </div>
            <div className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-950">{sparks ?? "—"}</div>
          </div>
        </div>

        {/* Domínio estimado por área + próxima ação */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
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

          <div className="card-sapiens rounded-2xl p-6 flex flex-col" data-testid="dash-recommendation" data-tour="dash-recommendation">
            <div className="flex items-center gap-2 font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-3">
              <Target className="w-3.5 h-3.5" /> Próxima ação
            </div>
            {weakestArea ? (
              <>
                <div className="font-display font-bold text-lg text-zinc-950 leading-snug">
                  O Sapiens encontrou uma lacuna.
                </div>
                <p className="mt-2 text-sm text-zinc-600 leading-relaxed flex-1">
                  Você está acertando {weakestArea.pct}% em <strong>{weakestArea.area}</strong> — a área com maior espaço para evoluir agora.
                </p>
                <Link
                  to={AREA_CODE_TO_LABEL[weakestArea.area] ? `/exams?area=${encodeURIComponent(AREA_CODE_TO_LABEL[weakestArea.area])}` : `/plan/${latest.analysis_id}`}
                  className="pill btn-sapiens mt-4 self-start inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium"
                  data-testid="dash-recommendation-cta"
                >
                  Treinar agora <ArrowRight className="w-4 h-4" />
                </Link>
              </>
            ) : weakestRound ? (
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
        </div>

        {/* Conquistas — poucas e significativas, nunca uma coleção de badges */}
        <div className="mt-4 card-sapiens rounded-2xl p-5" data-testid="dash-achievements" data-tour="dash-achievements">
          <div className="font-mono-alt text-[10px] uppercase tracking-[0.3em] text-zinc-400 mb-3">Conquistas</div>
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
      </div>

      {loaded && showTour && <OnboardingTour onDone={() => setShowTour(false)} />}
      <AulasParticularesModal open={showAulasModal} onClose={() => setShowAulasModal(false)} />
    </div>
  );
}
