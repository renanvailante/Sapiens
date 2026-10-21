import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ArrowLeft, SkipForward, Check, Loader2, Target } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import BalaoDaMentis from "../components/caminho/BalaoDaMentis";
import Logo from "../components/Logo";
import VideoDoMentor from "../components/VideoDoMentor";
import { MENTOR } from "../lib/mentor";
import { CaminhoDoPlus, Chama } from "../components/celebracao/TelaDaOfensiva";
import { BENEFICIOS_DO_PLUS } from "../lib/celebracao";
import { tocar } from "../lib/som";

/**
 * O primeiro acesso: um vídeo curto e três perguntas, conduzidas pela Mentis.
 *
 * Três decisões que valem mais que o layout:
 *
 * 1. **Tudo é pulável.** "Pular introdução" no vídeo, "Pular" em cada etapa e
 *    o X no canto. Um onboarding que prende o aluno na primeira sessão é o
 *    jeito mais rápido de perder alguém que só queria ver o produto.
 * 2. **Cada etapa salva sozinha** (`PUT /onboarding` é parcial). Fechar o
 *    navegador no meio não apaga o que já foi respondido.
 * 3. **As respostas têm consequência de verdade** — o tempo declarado vira a
 *    janela do Cronograma, a dificuldade declarada entra na ordem das frentes
 *    enquanto não houver medida, e a meta vira o alvo que o Painel persegue.
 *    Ver `onboarding_routes.py`. Um formulário de boas-vindas que não muda
 *    nada depois é só um pedágio.
 *
 * No fim, o guia da Mentis abre por cima do Painel (`/dashboard?guia=1`).
 *
 * **O vídeo da primeira etapa (2026-09-17)** é o mesmo de apresentação do
 * mentor que a landing já usa (`VideoDoMentor` + `lib/mentor.js`) — não um
 * vídeo de boas-vindas à parte. Antes disso a etapa desenhava só o LUGAR de
 * um vídeo que nunca chegou a existir: quem via a landing via {MENTOR.nome}
 * contando quem é antes de criar conta, e quem criava conta via um retângulo
 * vazio com um ícone de play morto — a primeira interação de quem já era
 * aluno era pior que a de quem ainda nem tinha entrado.
 */

// "desafio" (2026-10-08): o dono pediu que o aluno saiba DESDE O INÍCIO que
// 5 dias de ofensiva valem 2 dias de Sapiens Plus. É a última coisa que ele
// ouve antes de entrar — e a primeira que vê no Hoje (`DesafioPlus`).
const ETAPAS = ["video", "dificuldades", "objetivo", "meta", "desafio"];

const AREAS = [
  { chave: "matematica", rotulo: "Matemática" },
  { chave: "natureza", rotulo: "Natureza" },
  { chave: "linguagens", rotulo: "Linguagens" },
  { chave: "humanas", rotulo: "Humanas" },
  { chave: "redacao", rotulo: "Redação" },
];

const TEMPOS = [
  { minutos: 10, rotulo: "10 min" },
  { minutos: 30, rotulo: "30 min" },
  { minutos: 60, rotulo: "1 h" },
  { minutos: 120, rotulo: "2 h" },
  { minutos: 240, rotulo: "4 h" },
  { minutos: 480, rotulo: "8 h" },
];

// A tabela é do servidor (`onboarding_routes.METAS`, servida em
// `opcoes.metas`); esta cópia é só a reserva até a resposta chegar, no mesmo
// espírito dos `*_PADRAO` de preço. Mudou lá, muda aqui.
const METAS_RESERVA = [
  { nivel: "basico", rotulo: "Básico", acertos_min: 70, acertos_max: 100 },
  { nivel: "medio", rotulo: "Médio", acertos_min: 100, acertos_max: 130 },
  { nivel: "avancado", rotulo: "Avançado", acertos_min: 130, acertos_max: 160 },
];

const OBJETIVOS_SUGERIDOS = [
  "Passar em Medicina",
  "Entrar numa federal",
  "Melhorar minha nota do ano passado",
  "Organizar meus estudos",
];

/** A fala da Mentis no topo de cada etapa. Curta: ela guia, não disserta.
 *
 *  Desde 2026-10-09 é o MESMO balão do Hoje (`caminho/BalaoDaMentis`): ela
 *  flutua, "fala" enquanto o texto entra e tem o botão de voz. O primeiro
 *  acesso é onde o aluno conhece a guia — ela precisa ser a mesma que ele vai
 *  encontrar na trilha logo depois. */
function FalaDaMentis({ texto, subtexto, voz }) {
  return <BalaoDaMentis titulo={texto} texto={subtexto || ""} frases={voz ? [voz] : []} tamanho="p" olhar={0.4} testid="onb-mentis" />;
}

function Slider({ area, valor, aoMudar }) {
  const n = valor ?? 5;
  return (
    <div data-testid={`onb-slider-${area.chave}`}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <label htmlFor={`slider-${area.chave}`} className="text-sm font-medium text-white/85">
          {area.rotulo}
        </label>
        <span className="font-mono-alt text-sm font-bold text-[#7FD8FF]">{n}</span>
      </div>
      <input
        id={`slider-${area.chave}`}
        type="range"
        min={0}
        max={10}
        step={1}
        value={n}
        onChange={(e) => aoMudar(area.chave, Number(e.target.value))}
        className="slider-bio w-full"
        aria-label={`Dificuldade em ${area.rotulo}, de 0 a 10`}
      />
    </div>
  );
}

export default function BemVindo() {
  const nav = useNavigate();
  const { user } = useAuth();
  const [etapa, setEtapa] = useState(0);
  const [dificuldades, setDificuldades] = useState({});
  const [objetivo, setObjetivo] = useState("");
  const [minutos, setMinutos] = useState(null);
  const [meta, setMeta] = useState(null);
  const [metas, setMetas] = useState(METAS_RESERVA);
  const [salvando, setSalvando] = useState(false);
  // Os números do desafio vêm do servidor (`engajamento.PLUS_META_DIAS`), não
  // daqui: a promessa e quem a cumpre leem a mesma constante.
  const [plus, setPlus] = useState(null);
  useEffect(() => {
    api.get("/engajamento/me").then(({ data }) => setPlus(data?.plus || null)).catch(() => {});
  }, []);

  const primeiroNome = (user?.name || "").split(" ")[0] || "";

  // Quem já concluiu não é perguntado de novo — chegar aqui pelo link direto
  // simplesmente volta para o Painel.
  useEffect(() => {
    api.get("/onboarding")
      .then(({ data }) => {
        if (data?.concluido) nav("/hoje", { replace: true });
        const doServidor = data?.opcoes?.metas;
        if (Array.isArray(doServidor) && doServidor.length) setMetas(doServidor);
      })
      .catch(() => {});
  }, [nav]);

  /** A marca que impede o laço: o Painel só devolve o aluno para cá enquanto
   *  ela não existe. Necessária porque os `PUT` abaixo falham em silêncio —
   *  se a rede cair exatamente no "concluir", `flags.onboarded` continua
   *  `false` no servidor e as duas telas se empurrariam sem parar. */
  const marcarVisto = useCallback(() => {
    try { sessionStorage.setItem("sapiens:onboarding-visto", "1"); } catch { /* sem storage, segue */ }
  }, []);

  /** Salva o que a etapa produziu. Falha em silêncio de propósito: o aluno
   *  não pode ficar preso no onboarding porque a rede oscilou. */
  const salvarParcial = useCallback((campos) => {
    api.put("/onboarding", campos).catch(() => {});
  }, []);

  const concluir = useCallback(() => {
    setSalvando(true);
    marcarVisto();
    api.put("/onboarding", {
      dificuldades,
      objetivo: objetivo.trim() || undefined,
      minutos_por_dia: minutos || undefined,
      meta: meta || undefined,
      concluido: true,
    })
      .catch(() => {})
      // `guia=1`: o Painel abre e a Mentis começa o tour por cima dele. É a
      // continuação da mesma conversa, não um segundo onboarding.
      .finally(() => nav("/hoje?guia=1", { replace: true }));
  }, [dificuldades, objetivo, minutos, meta, nav, marcarVisto]);

  const pularTudo = useCallback(() => {
    // Pular também conclui: perguntar de novo a cada login quem já disse
    // "agora não" é a definição de insistência.
    marcarVisto();
    api.put("/onboarding", { concluido: true }).catch(() => {});
    nav("/hoje", { replace: true });
  }, [nav, marcarVisto]);

  const avancar = () => {
    if (etapa >= ETAPAS.length - 1) {
      tocar("ofensiva");
      return concluir();
    }
    setEtapa((i) => i + 1);
  };

  const nome = ETAPAS[etapa];

  const podeAvancar = useMemo(() => {
    if (nome === "objetivo") return Boolean(minutos);
    if (nome === "meta") return Boolean(meta);
    return true;
  }, [nome, minutos, meta]);

  return (
    <div className="min-h-screen">
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col px-6 py-8 md:px-10 md:py-12">
        <div className="flex items-center justify-between gap-3">
          <Logo tamanho="p" testid="onb-marca" />
          <button
            type="button"
            onClick={pularTudo}
            className="chip pill px-3 py-1.5 text-[11px]"
            data-testid="onb-pular-tudo"
          >
            Pular
          </button>
        </div>

        {/* Quatro traços: o aluno vê de saída que isto acaba rápido.
            Três estados, não dois: o PASSADO é uma linha acesa cheia, o ATUAL
            também acende mas com halo (é onde ele está), e o futuro é trilho.
            Com dois estados, "onde estou" e "o que já fiz" eram a mesma cor e
            a barra só dizia quanto falta. */}
        <div className="mt-6 flex gap-1.5" data-testid="onb-progresso">
          {ETAPAS.map((e, i) => (
            <span
              key={e}
              data-estado={i < etapa ? "feito" : i === etapa ? "atual" : "futuro"}
              className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                i < etapa
                  ? "bg-[#4FD9FF]"
                  : i === etapa
                  ? "bg-gradient-to-r from-[#4FD9FF] to-[#8B7BFF] shadow-[0_0_12px_-2px_rgba(79,217,255,0.9)]"
                  : "bg-white/10"
              }`}
            />
          ))}
        </div>

        <div className="flex flex-1 flex-col justify-center py-8">
          {/* ---------------- Vídeo ---------------- */}
          {nome === "video" && (
            <section className="reveal" data-testid="onb-video">
              <h1 className="titulo-heroi">
                {primeiroNome ? `Bem-vindo, ${primeiroNome}.` : "Bem-vindo ao Sapiens."}
              </h1>
              <p className="mt-3 text-white/55">
                Você está a três passos de saber exatamente o que estudar. Antes
                do primeiro, conheça quem desenhou o plano: {MENTOR.nome},{" "}
                {MENTOR.titulo.toLowerCase()}.
              </p>

              <VideoDoMentor className="mt-6" testid="onb-video-mentor" />

              <div className="mt-6 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={avancar}
                  className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-sm font-medium"
                  data-testid="onb-video-continuar"
                >
                  Continuar <ArrowRight className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={avancar}
                  className="pill btn-vidro inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm"
                  data-testid="onb-pular-video"
                >
                  <SkipForward className="h-4 w-4" /> Pular introdução
                </button>
              </div>
            </section>
          )}

          {/* ---------------- Etapa 1: dificuldades ---------------- */}
          {nome === "dificuldades" && (
            <section className="reveal" data-testid="onb-dificuldades">
              <FalaDaMentis
                texto="Onde você sente mais dificuldade?"
                subtexto="0 = tranquilo · 10 = é o meu maior problema"
                voz="onb-dificuldades"
              />
              <div className="mt-7 space-y-5">
                {AREAS.map((a) => (
                  <Slider
                    key={a.chave}
                    area={a}
                    valor={dificuldades[a.chave]}
                    aoMudar={(chave, v) => setDificuldades((d) => ({ ...d, [chave]: v }))}
                  />
                ))}
              </div>
              <p className="mt-6 text-xs leading-relaxed text-white/30">
                Isto é o seu palpite, e vale só até eu ter medida. Assim que você responder questões,
                o número real toma o lugar.
              </p>
            </section>
          )}

          {/* ---------------- Etapa 2: objetivo + tempo ---------------- */}
          {nome === "objetivo" && (
            <section className="reveal" data-testid="onb-objetivo">
              <FalaDaMentis texto="Qual é o seu principal objetivo com o Sapiens?" voz="onb-objetivo" />
              <input
                value={objetivo}
                onChange={(e) => setObjetivo(e.target.value.slice(0, 180))}
                placeholder="Em uma frase…"
                className="mt-5 w-full rounded-xl border border-white/12 bg-white/5 px-4 py-3.5 text-sm text-white outline-none placeholder:text-white/25 focus:border-[#4FD9FF]/60"
                data-testid="onb-objetivo-input"
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {OBJETIVOS_SUGERIDOS.map((o) => (
                  <button
                    key={o}
                    type="button"
                    onClick={() => setObjetivo(o)}
                    className={`rounded-full border px-3.5 py-2 text-xs transition ${
                      objetivo === o
                        ? "border-[#4FD9FF]/60 bg-[#4FD9FF]/15 text-white"
                        : "border-white/12 bg-white/5 text-white/60 hover:border-white/25 hover:text-white"
                    }`}
                  >
                    {o}
                  </button>
                ))}
              </div>

              <div className="mt-9">
                <h3 className="font-display text-lg font-bold tracking-tight text-white">
                  Quanto tempo por dia você quer estudar?
                </h3>
                <p className="mt-1 text-sm text-white/45">É com isso que eu monto a sua semana.</p>
                <div className="mt-4 grid grid-cols-3 gap-2.5">
                  {TEMPOS.map((t) => (
                    <button
                      key={t.minutos}
                      type="button"
                      onClick={() => setMinutos(t.minutos)}
                      className={`rounded-2xl border px-3 py-4 text-center transition ${
                        minutos === t.minutos
                          ? "border-[#4FD9FF]/60 bg-[#4FD9FF]/15 text-white"
                          : "border-white/12 bg-white/[0.04] text-white/65 hover:border-white/25 hover:text-white"
                      }`}
                      data-testid={`onb-tempo-${t.minutos}`}
                    >
                      <span className="font-display text-lg font-bold tracking-tight">{t.rotulo}</span>
                    </button>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* ---------------- Etapa 3: meta ENEM 2026 ---------------- */}
          {nome === "meta" && (
            <section className="reveal" data-testid="onb-meta">
              <FalaDaMentis
                texto="Onde você quer chegar no ENEM 2026?"
                subtexto="Acertos nas 180 questões objetivas. Dá para mudar depois."
                voz="onb-meta"
              />
              <div className="mt-7 space-y-3">
                {metas.map((m) => {
                  const ativo = meta === m.nivel;
                  return (
                    <button
                      key={m.nivel}
                      type="button"
                      onClick={() => setMeta(m.nivel)}
                      className={`flex w-full items-center gap-4 rounded-2xl border px-5 py-4 text-left transition ${
                        ativo
                          ? "border-[#4FD9FF]/60 bg-[#4FD9FF]/12"
                          : "border-white/12 bg-white/[0.04] hover:border-white/25"
                      }`}
                      data-testid={`onb-meta-${m.nivel}`}
                    >
                      <span
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
                          ativo ? "border-[#4FD9FF]/50 bg-[#4FD9FF]/20 text-[#7FD8FF]" : "border-white/10 bg-white/5 text-white/35"
                        }`}
                      >
                        {ativo ? <Check className="h-5 w-5" /> : <Target className="h-5 w-5" />}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-display text-lg font-bold tracking-tight text-white">
                          {m.rotulo}
                        </span>
                        <span className="block text-sm text-white/50">
                          {m.acertos_min}–{m.acertos_max} acertos
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* ---------------- Etapa 4: o desafio dos 5 dias ---------------- */}
          {nome === "desafio" && (
            <section className="reveal text-center" data-testid="onb-desafio">
              <div className="relative mx-auto inline-flex">
                <span className="chama-aura" aria-hidden="true" />
                <Chama tamanho={96} />
              </div>
              <div className="secao-olho mt-4 text-amber-200/90">Seu primeiro desafio</div>
              <h2 className="mt-2 font-display text-2xl font-extrabold leading-snug tracking-tight text-white md:text-3xl">
                {plus
                  ? <>Estude {plus.meta_dias} dias seguidos e ganhe {plus.presente_dias} dias de <span className="texto-plus">Sapiens Plus</span>.</>
                  : <>Mantenha a sua ofensiva e ganhe dias de <span className="texto-plus">Sapiens Plus</span>.</>}
              </h2>
              <p className="mx-auto mt-2 max-w-md text-sm text-white/55">
                Uma questão por dia já acende a chama. Sem pagar nada: é o prêmio por voltar.
              </p>
              {plus && (
                <div className="mt-6">
                  <CaminhoDoPlus plus={{ ...plus, progresso: 0, faltam: plus.meta_dias }} />
                </div>
              )}
              <ul className="mx-auto mt-6 max-w-sm space-y-2 text-left">
                {BENEFICIOS_DO_PLUS.map((b) => (
                  <li key={b.chave} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-400 text-[#2a1600]">
                      <Check className="h-3.5 w-3.5" strokeWidth={3.5} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-white">{b.texto}</span>
                      <span className="block text-xs text-white/50">{b.detalhe}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        {nome !== "video" && (
          <div className="flex items-center justify-between gap-3 pb-2">
            <button
              type="button"
              onClick={() => setEtapa((i) => Math.max(0, i - 1))}
              className="inline-flex items-center gap-1.5 py-2 text-xs text-white/40 hover:text-white/80"
              data-testid="onb-voltar"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Voltar
            </button>
            <button
              type="button"
              onClick={() => {
                // Cada etapa grava o que produziu antes de sair dela.
                if (nome === "dificuldades") salvarParcial({ dificuldades });
                if (nome === "objetivo") {
                  salvarParcial({
                    objetivo: objetivo.trim() || undefined,
                    minutos_por_dia: minutos || undefined,
                  });
                }
                avancar();
              }}
              disabled={!podeAvancar || salvando}
              className="pill btn-sapiens inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-sm font-medium disabled:opacity-40"
              data-testid="onb-avancar"
            >
              {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {nome === "desafio" ? "Aceitar o desafio" : "Continuar"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
