import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  Radio, Zap, Clock, Video, Copy, Check, CalendarPlus, Bell,
  BellRing, Lock, ArrowRight, Sparkles, Trophy, Target, MessageCircleMore,
  PlayCircle, ShieldCheck, Infinity as Infinito, Medal,
} from "lucide-react";
import { api, errMsg } from "../lib/api";
import Nav, { avisarSparksMudou } from "../components/Nav";
import PedirWhatsApp from "../components/PedirWhatsApp";
import MentorUSP from "../components/MentorUSP";
import ContagemEnem from "../components/ContagemEnem";
import { useDeclararContextoMentis } from "../lib/mentisContexto";
import { marcarAcessoDaLive } from "../lib/live";
import { quintasAteAProva } from "../lib/enem";

/**
 * `/cursos` — a aba de Cursos e, principalmente, a AULA AO VIVO DE QUINTA.
 *
 * A página tem duas metades e uma hierarquia deliberada:
 *
 * **Em cima, a live.** É a única coisa aqui que existe hoje, acontece toda
 * semana e é paga (200 Sparks por edição). Quem dá a aula é o 1º colocado de
 * Medicina da USP — é esse o argumento, e ele aparece antes de qualquer outra
 * coisa da página, inclusive antes do preço.
 *
 * **Embaixo, os quatro cursos**, todos "em breve". Nenhum deles cobra nada:
 * a única ação possível é entrar na lista de avisados, e o card diz isso com
 * todas as letras em vez de fingir um botão de compra desabilitado.
 *
 * Tudo vem de `GET /cursos` numa chamada só — catálogo, horário da próxima
 * edição, se este aluno já pagou e o saldo dele. O link do Meet só chega ao
 * navegador de quem comprou (ver `cursos_routes._montar_live`).
 */

const DIAS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];

/** "quinta, 17 de setembro, às 20h" — a frase que a pessoa lê e já sabe se
 *  consegue estar lá. Data crua ISO não responde isso. */
function quandoPorExtenso(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const dia = DIAS[d.getDay()];
  const data = d.toLocaleDateString("pt-BR", { day: "numeric", month: "long" });
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${dia}, ${data}, às ${hora}`;
}

/** Contagem regressiva viva. É o que transforma "toda quinta" em "faltam 2
 *  dias" — a diferença entre uma informação e um motivo para agir agora. */
function useContagem(alvoIso) {
  // `alvoIso` chega `undefined` no primeiro render (a página ainda não
  // carregou): sem a guarda, `new Date(undefined)` vira `NaN` e a contagem
  // pisca "NaN" antes do primeiro tick.
  const [restante, setRestante] = useState(0);
  useEffect(() => {
    if (!alvoIso) return undefined;
    const tick = () => setRestante(Math.max(0, new Date(alvoIso) - Date.now()));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [alvoIso]);

  const s = Math.floor(restante / 1000);
  return {
    dias: Math.floor(s / 86400),
    horas: Math.floor((s % 86400) / 3600),
    minutos: Math.floor((s % 3600) / 60),
    segundos: s % 60,
    acabou: s <= 0,
  };
}

function Bloco({ valor, rotulo }) {
  return (
    <div className="min-w-[3.25rem] rounded-2xl border border-white/10 bg-black/30 px-3 py-2 text-center">
      <div className="font-display text-2xl font-extrabold tracking-tighter text-white tabular-nums">
        {String(valor).padStart(2, "0")}
      </div>
      <div className="font-mono-alt text-[9px] uppercase tracking-[0.2em] text-white/35">{rotulo}</div>
    </div>
  );
}

/** Link do Google Agenda para a edição — sem backend e sem autorização: é
 *  só uma URL montada com a data que já temos. */
function linkDaAgenda(live) {
  if (!live?.inicio) return null;
  const fmt = (iso) => new Date(iso).toISOString().replace(/[-:]|\.\d{3}/g, "");
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: `Sapiens · Aula ao vivo com o ${live.apresentador}`,
    dates: `${fmt(live.inicio)}/${fmt(live.fim)}`,
    details: live.tema
      ? `Tema desta edição: ${live.tema}. O link da sala fica na aba Cursos do Sapiens.`
      : "O link da sala fica na aba Cursos do Sapiens.",
  });
  return `https://calendar.google.com/calendar/render?${params}`;
}

const O_QUE_ACONTECE = [
  {
    icone: Target,
    titulo: "Questão por questão, ao vivo",
    texto: "Ele resolve na sua frente as questões que mais derrubam gente — e diz o que pensou antes de escrever a primeira linha.",
  },
  {
    icone: Trophy,
    titulo: "A rotina de quem passou em 1º",
    texto: "Quanto tempo, em que ordem, o que ele cortou e o que manteve. Sem fórmula mágica: o cronograma real de uma aprovação.",
  },
  {
    icone: MessageCircleMore,
    titulo: "Perguntas abertas no fim",
    texto: "Os últimos minutos são seus. Traga a dúvida que está te travando há semanas.",
  },
  {
    icone: Sparkles,
    titulo: "Toda semana, tema novo",
    texto: "Uma edição por quinta-feira. Quem entra uma vez volta na seguinte — e o assunto nunca repete.",
  },
];

export default function Cursos() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);
  const [comprando, setComprando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [marcando, setMarcando] = useState(null);
  const [comprandoCurso, setComprandoCurso] = useState(null);

  const carregar = useCallback(() => {
    api
      .get("/cursos")
      .then(({ data }) => {
        setDados(data);
        setErro(null);
        // O Painel anuncia a live sem chamar a API (ver `lib/live.js`); esta
        // marca é o que impede o anúncio de oferecer "garanta sua vaga" a
        // quem acabou de pagar.
        if (data.live?.tenho_acesso) marcarAcessoDaLive(data.live.edicao);
      })
      .catch((e) => setErro(errMsg(e, "Não foi possível carregar os cursos agora.")));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const live = dados?.live;
  const contagem = useContagem(live?.inicio);
  const saldo = live?.sparks_balance;
  const custo = live?.custo_sparks ?? 200;
  const podePagar = saldo == null || saldo >= custo;

  useDeclararContextoMentis(
    "Na aba Cursos, olhando a aula ao vivo de quinta-feira com o 1º colocado de Medicina da USP.",
  );

  const comprar = async () => {
    setComprando(true);
    try {
      const { data } = await api.post("/cursos/live/acesso", {});
      avisarSparksMudou();
      toast.success(
        data.cobrado
          ? "Vaga garantida! Te esperamos na quinta."
          : "Você já tem acesso a esta edição.",
      );
      carregar();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível garantir sua vaga."));
    } finally {
      setComprando(false);
    }
  };

  const copiarLink = async () => {
    try {
      await navigator.clipboard.writeText(live.link);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      toast.error("Não consegui copiar. Toque no link e copie à mão.");
    }
  };

  /** Pré-venda: cobra uma vez, o acesso é vitalício, e o aluno confirma
   *  sabendo que as aulas ainda não existem. */
  const comprarCurso = async (curso) => {
    setComprandoCurso(curso.curso_id);
    try {
      const { data } = await api.post(`/cursos/${curso.curso_id}/acesso`);
      avisarSparksMudou();
      toast.success(
        data.cobrado
          ? `"${curso.titulo}" é seu para sempre. Avisamos assim que abrir.`
          : "Você já tem acesso vitalício a este curso.",
      );
      carregar();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível concluir a compra."));
    } finally {
      setComprandoCurso(null);
    }
  };

  const alternarInteresse = async (curso) => {
    setMarcando(curso.curso_id);
    try {
      if (curso.tenho_interesse) {
        await api.delete(`/cursos/${curso.curso_id}/interesse`);
      } else {
        await api.post(`/cursos/${curso.curso_id}/interesse`);
        toast.success(`Beleza! Você é avisado assim que "${curso.titulo}" abrir.`);
      }
      carregar();
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível registrar seu interesse."));
    } finally {
      setMarcando(null);
    }
  };

  const agenda = useMemo(() => linkDaAgenda(live), [live]);
  // Aritmética, não retórica: cada quinta até a prova é uma aula que existe
  // ou não existe. Ver `lib/enem.js`.
  const quintasRestantes = quintasAteAProva();

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-6 py-8 md:px-10 md:py-10">
        {erro && (
          <div className="mb-6 rounded-2xl border border-amber-300/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
            {erro}
          </div>
        )}

        {/* O relógio primeiro: é ele que explica por que esta página importa
            hoje e não mês que vem. */}
        <div className="mb-6">
          <ContagemEnem comCta={false} testid="cursos-contagem-enem" />
        </div>

        {/* ---------------------------------------------------------------
            A LIVE. Primeira coisa da página, e a única que existe hoje.
            --------------------------------------------------------------- */}
        <section
          id="live"
          className="mapa-vitrine relative scroll-mt-24 overflow-hidden rounded-3xl p-6 md:p-8"
          data-testid="cursos-live"
        >
          <div className="relative grid gap-7 md:grid-cols-[1fr_auto] md:items-center">
            <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-rose-400/40 bg-rose-500/15 px-3 py-1.5 font-mono-alt text-[10px] font-bold uppercase tracking-[0.2em] text-rose-200">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-400" />
                </span>
                {live?.ao_vivo_agora ? "Acontecendo agora" : "Ao vivo · toda quinta"}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-white/60">
                <Clock className="h-3 w-3" /> {live ? quandoPorExtenso(live.inicio) : "—"}
              </span>
              {live?.duracao_minutos && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-white/60">
                  <Video className="h-3 w-3" /> {live.duracao_minutos} min · Google Meet
                </span>
              )}
            </div>

            <h1 className="mt-5 max-w-3xl font-display text-4xl font-extrabold leading-[1.02] tracking-tighter text-white md:text-6xl">
              {/* Cor sólida, e NÃO `.shimmer`: medido no navegador em
                  2026-09-15, o gradiente animado sobre `background-clip: text`
                  apaga a barriga do "P" em tamanho de display — a manchete
                  lia "USF" na maior parte dos quadros. A palavra mais
                  importante do anúncio não pode depender da fase de uma
                  animação para ser legível. */}
              Toda quinta, ao vivo, com o{" "}
              <span className="text-[#7FD8FF]">1º colocado de Medicina da USP</span>.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-white/65 md:text-lg">
              Não é aula gravada, não é resumo, não é PDF. É a pessoa que tirou o primeiro
              lugar no vestibular mais disputado do país resolvendo questão na sua frente e
              respondendo as suas perguntas — 90 minutos, uma vez por semana.
            </p>
            {quintasRestantes > 0 && (
              <p className="mt-3 max-w-2xl text-sm font-medium text-amber-200/90" data-testid="cursos-quintas-restantes">
                Até a prova cabem {quintasRestantes === 1 ? "só mais 1 aula" : `só mais ${quintasRestantes} aulas`}.
                A de quinta que passar não volta.
              </p>
            )}

            {live?.tema && (
              <div
                className="mt-5 inline-flex max-w-full items-center gap-2 rounded-2xl border border-[#4FD9FF]/25 bg-[#4FD9FF]/[0.08] px-4 py-3"
                data-testid="cursos-live-tema"
              >
                <PlayCircle className="h-4 w-4 shrink-0 text-[#7FD8FF]" />
                <span className="min-w-0 text-sm text-white/85">
                  <span className="font-mono-alt text-[10px] uppercase tracking-[0.2em] text-[#7FD8FF]">
                    Tema desta quinta ·{" "}
                  </span>
                  {live.tema}
                </span>
              </div>
            )}

            {/* Contagem regressiva — o "faltam 2 dias" que transforma
                informação em urgência honesta. */}
            {live && !live.ao_vivo_agora && !contagem.acabou && (
              <div className="mt-6 flex flex-wrap items-center gap-2" data-testid="cursos-contagem">
                <span className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-white/35">
                  Começa em
                </span>
                <div className="flex gap-2">
                  <Bloco valor={contagem.dias} rotulo="dias" />
                  <Bloco valor={contagem.horas} rotulo="horas" />
                  <Bloco valor={contagem.minutos} rotulo="min" />
                  <Bloco valor={contagem.segundos} rotulo="seg" />
                </div>
              </div>
            )}

            {/* ---- A porta: comprar, ou entrar se já comprou ---- */}
            <div className="mt-7">
              {live?.tenho_acesso ? (
                <div
                  className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-5"
                  data-testid="cursos-live-acesso"
                >
                  <div className="flex items-center gap-2 font-display text-lg font-bold tracking-tight text-emerald-200">
                    <ShieldCheck className="h-5 w-5" /> Sua vaga está garantida.
                  </div>
                  {live.link ? (
                    <>
                      <p className="mt-1 text-sm text-emerald-100/70">
                        {live.ao_vivo_agora
                          ? "A sala está aberta agora. Entra!"
                          : "A sala abre 30 minutos antes. Guarde o link — ele é só desta edição."}
                      </p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <a
                          href={live.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="pill btn-calor inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-sm"
                          data-testid="cursos-live-entrar"
                        >
                          <Video className="h-4 w-4" /> Entrar na sala
                        </a>
                        <button
                          onClick={copiarLink}
                          className="pill btn-vidro inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm"
                          data-testid="cursos-live-copiar"
                        >
                          {copiado ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                          {copiado ? "Copiado" : "Copiar link"}
                        </button>
                        {agenda && (
                          <a
                            href={agenda}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="pill btn-vidro inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm"
                            data-testid="cursos-live-agenda"
                          >
                            <CalendarPlus className="h-4 w-4" /> Pôr na agenda
                          </a>
                        )}
                      </div>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-emerald-100/70" data-testid="cursos-live-sem-link">
                      O link da sala é criado na véspera e aparece aqui automaticamente —
                      e também chega no seu WhatsApp. Você não precisa pagar de novo.
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    onClick={comprar}
                    disabled={comprando || !podePagar}
                    className="pill btn-calor inline-flex items-center gap-2 rounded-full px-7 py-4 text-sm disabled:opacity-60"
                    data-testid="cursos-live-comprar"
                  >
                    <Radio className="h-4 w-4" />
                    {comprando ? "Garantindo…" : `Garantir minha vaga · ${custo} Sparks`}
                  </button>
                  {!podePagar && (
                    <Link
                      to="/sparks"
                      className="pill btn-vidro inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm"
                      data-testid="cursos-live-sem-saldo"
                    >
                      <Zap className="h-4 w-4 text-amber-400" /> Você tem {saldo} — comprar Sparks
                    </Link>
                  )}
                  <span className="text-xs text-white/40">
                    Pagamento por edição. Vale só para a aula desta quinta.
                  </span>
                </div>
              )}
            </div>
            </div>

            {/* O rosto de quem dá a aula, do lado do preço. No celular ele
                vai para o fim do bloco em vez de empurrar a manchete para
                baixo da dobra. */}
            <div className="order-first flex justify-center md:order-none md:justify-end">
              <MentorUSP tamanho="m" testid="cursos-live-mentor" />
            </div>
          </div>
        </section>

        {/* Quem não tem WhatsApp na conta: é por ele que o link e o lembrete
            chegam. Logo abaixo da compra, que é o momento em que a pessoa
            mais quer ser avisada. */}
        <div className="mt-4">
          <PedirWhatsApp
            titulo="Receba o link da live no WhatsApp"
            motivo="A gente avisa uma hora antes da aula começar. Sem spam, sem lista de transmissão de propaganda."
            testid="cursos-pedir-whatsapp"
          />
        </div>

        {/* ---- O que acontece na aula ---- */}
        <section className="mt-10" data-testid="cursos-live-o-que-acontece">
          <h2 className="font-display text-xl font-bold tracking-tight text-white">
            O que acontece nos 90 minutos
          </h2>
          <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
            {O_QUE_ACONTECE.map((x) => (
              <div key={x.titulo} className="macio border border-white/10 bg-white/[0.035] p-4">
                <div className="flex items-start gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-[#7FD8FF]">
                    <x.icone className="h-4 w-4" strokeWidth={1.8} />
                  </span>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-white">{x.titulo}</div>
                    <div className="mt-1 text-xs leading-relaxed text-white/45">{x.texto}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ---------------------------------------------------------------
            OS CURSOS — todos em breve, nenhum cobra nada
            --------------------------------------------------------------- */}
        <section id="cursos" className="mt-12 scroll-mt-24" data-testid="cursos-catalogo">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="font-display text-2xl font-extrabold tracking-tighter text-white md:text-3xl">
              Cursos completos
            </h2>
            <span className="font-mono-alt text-[10px] uppercase tracking-[0.25em] text-white/35">
              Em produção · entre na lista
            </span>
          </div>
          <p className="mt-2 max-w-2xl text-sm text-white/55">
            Quatro trilhas do zero ao ENEM, gravadas{" "}
            <strong className="font-semibold text-white/85">pelo mesmo 1º colocado de
            Medicina da USP</strong> que dá a aula ao vivo de quinta — na ordem em que o
            conteúdo cobra, e não na ordem em que o livro apresenta.{" "}
            <strong className="font-semibold text-white/80">Ainda não abriram</strong>:
            quem garante agora paga uma vez e fica com o curso para sempre, sem pagar de
            novo quando ele entrar no ar.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2.5 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <MentorUSP tamanho="p" comSelo={false} testid="cursos-catalogo-mentor" />
            <div className="min-w-0 flex-1 text-sm text-white/60">
              <strong className="font-semibold text-white">Quem grava é ele.</strong> Os quatro
              cursos são feitos pela mesma pessoa que passou em 1º lugar em Medicina na USP —
              não é conteúdo de banco de apostila com nome de professor na capa.
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {(dados?.cursos || []).map((c) => (
              <article
                key={c.curso_id}
                className="macio flex flex-col border border-white/10 bg-white/[0.035] p-5"
                data-testid={`curso-${c.curso_id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-display text-lg font-bold leading-tight tracking-tight text-white">
                    {c.titulo}
                  </h3>
                  <span
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-amber-300/30 bg-amber-400/10 px-2.5 py-1 font-mono-alt text-[9px] font-bold uppercase tracking-[0.2em] text-amber-200"
                    data-testid={`curso-${c.curso_id}-selo`}
                  >
                    <Lock className="h-2.5 w-2.5" /> Em breve
                  </span>
                </div>

                <div className="mt-1.5 text-sm font-medium text-[#7FD8FF]">{c.chamada}</div>
                <p className="mt-2 text-xs leading-relaxed text-white/45">{c.descricao}</p>

                <ul className="mt-3 space-y-1">
                  {c.modulos.map((m) => (
                    <li key={m} className="flex items-start gap-2 text-xs text-white/55">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-[#4FD9FF]/60" />
                      {m}
                    </li>
                  ))}
                </ul>

                <div className="mt-4 border-t border-white/8 pt-3.5">
                  <div className="font-mono-alt text-[10px] uppercase tracking-[0.15em] text-white/30">
                    {c.carga} · {c.nivel}
                  </div>

                  {c.tenho_acesso ? (
                    <div
                      className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-3.5 py-3"
                      data-testid={`curso-${c.curso_id}-meu`}
                    >
                      <Infinito className="h-4 w-4 shrink-0 text-emerald-300" />
                      <span className="text-xs text-emerald-100/80">
                        <strong className="font-semibold text-emerald-200">Seu para sempre.</strong>{" "}
                        Avisamos no WhatsApp assim que as aulas entrarem no ar — sem pagar de novo.
                      </span>
                    </div>
                  ) : (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => comprarCurso(c)}
                        disabled={comprandoCurso === c.curso_id}
                        className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-5 py-3 text-xs font-medium disabled:opacity-50"
                        data-testid={`curso-${c.curso_id}-comprar`}
                      >
                        <Infinito className="h-3.5 w-3.5" />
                        {comprandoCurso === c.curso_id
                          ? "Garantindo…"
                          : `Acesso vitalício · ${c.custo_sparks} Sparks`}
                      </button>
                      <button
                        onClick={() => alternarInteresse(c)}
                        disabled={marcando === c.curso_id}
                        className={[
                          "pill inline-flex items-center gap-1.5 rounded-full px-4 py-2.5 text-xs font-medium disabled:opacity-50",
                          c.tenho_interesse
                            ? "border border-emerald-400/30 bg-emerald-500/15 text-emerald-200"
                            : "btn-vidro",
                        ].join(" ")}
                        data-testid={`curso-${c.curso_id}-avisar`}
                      >
                        {c.tenho_interesse ? (
                          <><BellRing className="h-3.5 w-3.5" /> Na lista</>
                        ) : (
                          <><Bell className="h-3.5 w-3.5" /> Só me avise</>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>

        {/* ---- A mentoria: a mesma pessoa, um a um, com fila ---- */}
        <Link
          to="/mentoria"
          className="lift mt-10 flex items-center gap-4 rounded-2xl border border-[#4FD9FF]/20 bg-[#4FD9FF]/[0.06] p-5 hover:border-[#4FD9FF]/45"
          data-testid="cursos-mentoria"
        >
          <MentorUSP tamanho="p" comSelo={false} testid="cursos-mentoria-foto" />
          <div className="min-w-0 flex-1">
            <div className="font-display text-base font-bold tracking-tight text-white">
              Quer ele só para você?
            </div>
            <div className="text-xs text-white/45">
              A mentoria é um a um, com o próprio 1º colocado. Uma pessoa, poucas vagas —
              entre na lista de espera.
            </div>
          </div>
          <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
        </Link>
      </div>
    </div>
  );
}
