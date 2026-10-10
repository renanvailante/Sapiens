import { useEffect, useMemo, useRef, useState } from "react";
import {
  CalendarClock, Check, Clock, Compass, Gift, Loader2, RotateCw, Star, Target, Trophy, Users, X, Zap,
} from "lucide-react";

/**
 * O DESENHO DA TRILHA DO DIA — o caminho do Duolingo.
 *
 * A regra (`lib/trilhaDoDia.js`) decide os nós; aqui só se desenha. Três
 * coisas copiadas de propósito do Duolingo, porque são elas que fazem o aluno
 * não precisar pensar:
 *
 *   1. **Um nó aceso.** O atual pulsa e tem a etiqueta "COMEÇAR" saltando em
 *      cima. Os outros pendentes ficam em névoa — tocáveis, mas quietos.
 *   2. **Tocar abre um cartão logo abaixo do nó** com o que é, por que, o
 *      prêmio e UM botão. Nada de página intermediária.
 *   3. **O feito fica feito.** Nó concluído vira azul cheio com um visto; o
 *      prêmio pronto vira baú dourado que treme até ser aberto.
 *
 * O serpenteio é fixo (mesma régua de `TrilhaDeMissoes`): coordenadas
 * calculadas, não layout de fluxo, para o caminho não mudar de forma quando
 * um rótulo quebra em duas linhas.
 */

const ICONES = {
  revisao: RotateCw,
  agenda: CalendarClock,
  pratica: Target,
  treino: Compass,
  comunidade: Users,
  estrela: Star,
  trofeu: Trophy,
};

// Deslocamento horizontal de cada nó a partir do centro (px). Oito passos e
// a volta — o "S" do Duolingo.
// Teto de 64px: com o rótulo de 128px embaixo, o nó mais afastado ainda cabe
// nos 280px úteis de um celular de 320px.
const SERPENTE = [0, 44, 64, 44, 0, -44, -64, -44];
const PASSO = 124;
const TOPO = 58;
const RAIO = 38;

function classeDoNo(no) {
  if (no.estado === "resgatar") return "no-dia no-dia-bau";
  if (no.estado === "feito") return no.tipo === "trofeu" ? "no-dia no-dia-trofeu" : "no-dia no-dominado";
  if (no.atual) return "no-dia no-atual";
  if (no.estado === "bloqueado" || no.estado === "espera") return "no-dia no-novo";
  return "no-dia no-dia-proximo";
}

function IconeDoNo({ no }) {
  if (no.estado === "resgatar") return <Gift className="h-8 w-8" strokeWidth={2.2} />;
  if (no.estado === "feito" && no.tipo !== "trofeu") return <Check className="h-8 w-8" strokeWidth={3} />;
  if (no.estado === "espera") return <Clock className="h-7 w-7" strokeWidth={2.2} />;
  const Icone = ICONES[no.icone] || Star;
  return <Icone className="h-8 w-8" strokeWidth={2.2} />;
}

/** Anel de progresso em volta do nó (missão com alvo): o "2 de 5" do
 *  servidor, desenhado. Só aparece com progresso parcial — cheio, o nó já
 *  diz "feito"; vazio, um anel apagado é ruído. */
function Anel({ progresso }) {
  if (!progresso || progresso.feito <= 0 || progresso.feito >= progresso.alvo) return null;
  const r = RAIO + 7;
  const c = 2 * Math.PI * r;
  const frac = progresso.feito / progresso.alvo;
  return (
    <svg
      className="pointer-events-none absolute"
      style={{ left: -7, top: -7 }}
      width={(RAIO + 7) * 2}
      height={(RAIO + 7) * 2}
      aria-hidden="true"
    >
      <circle cx={r} cy={r} r={r - 3} fill="none" stroke="rgba(150,200,255,0.16)" strokeWidth="5" />
      <circle
        cx={r} cy={r} r={r - 3}
        fill="none" stroke="#FFC85C" strokeWidth="5" strokeLinecap="round"
        strokeDasharray={`${c * frac} ${c}`}
        transform={`rotate(-90 ${r} ${r})`}
      />
    </svg>
  );
}

function Premio({ premio }) {
  if (!premio || (!premio.sparks && !premio.xp)) return null;
  return (
    <span className="inline-flex items-center gap-2 text-xs font-bold">
      {premio.sparks > 0 && (
        <span className="inline-flex items-center gap-1 text-amber-200"><Zap className="h-3.5 w-3.5" />+{premio.sparks}</span>
      )}
      {premio.xp > 0 && <span className="text-[#9FE9FF]">+{premio.xp} XP</span>}
    </span>
  );
}

function Cartao({ no, aoExecutar, aoFechar, ocupado }) {
  const pronto = no.estado === "resgatar";
  const feito = no.estado === "feito";
  const parado = no.estado === "espera" || no.estado === "bloqueado";
  return (
    <div className="no-dia-cartao" role="dialog" aria-label={no.titulo} data-testid={`trilha-dia-cartao-${no.chave}`}>
      <button type="button" onClick={aoFechar} className="no-dia-cartao-fechar" aria-label="Fechar">
        <X className="h-4 w-4" />
      </button>
      <p className="pr-7 font-display text-lg font-extrabold leading-snug tracking-tight text-white">{no.titulo}</p>
      {no.detalhe && <p className="mt-1 text-sm leading-relaxed text-white/65">{no.detalhe}</p>}
      <div className="mt-2.5 flex flex-wrap items-center gap-3">
        {no.progresso && (
          <span className="font-mono-alt text-xs tabular-nums text-white/55">
            {no.progresso.feito}/{no.progresso.alvo}
          </span>
        )}
        <Premio premio={no.premio} />
      </div>
      {!parado && (
        <button
          type="button"
          onClick={() => aoExecutar(no)}
          disabled={ocupado}
          className={`pill mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3.5 text-[15px] font-extrabold uppercase tracking-wide ${pronto ? "btn-calor" : "btn-sapiens"} disabled:opacity-60`}
          data-testid={`trilha-dia-cta-${no.chave}`}
        >
          {ocupado ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {pronto ? "Abrir o baú" : feito ? "Fazer de novo" : no.cta || "Começar"}
        </button>
      )}
    </div>
  );
}

export default function TrilhaDoDia({ trilha, aoExecutar, ocupado = null, novos = [], testid = "trilha-dia" }) {
  const nos = trilha?.nos || [];
  const [aberto, setAberto] = useState(null);
  const raiz = useRef(null);

  // Clique fora fecha o cartão — o mesmo gesto do Duolingo.
  useEffect(() => {
    if (!aberto) return undefined;
    const fora = (e) => {
      if (raiz.current && !raiz.current.contains(e.target)) setAberto(null);
    };
    document.addEventListener("pointerdown", fora);
    return () => document.removeEventListener("pointerdown", fora);
  }, [aberto]);

  const pontos = useMemo(
    () => nos.map((_, i) => ({ x: SERPENTE[i % SERPENTE.length], y: TOPO + i * PASSO })),
    [nos],
  );
  const altura = TOPO + Math.max(0, nos.length - 1) * PASSO + 92;
  const indiceAtual = nos.findIndex((n) => n.atual);

  // O caminho em coordenadas de um SVG de 240px de largura centrado.
  const meio = 120;
  const caminho = pontos
    .map((p, i) => {
      if (i === 0) return `M ${meio + p.x} ${p.y}`;
      const a = pontos[i - 1];
      return `C ${meio + a.x} ${a.y + PASSO / 2} ${meio + p.x} ${p.y - PASSO / 2} ${meio + p.x} ${p.y}`;
    })
    .join(" ");
  // O trecho já andado vai até o nó aceso (ou até o fim, com o dia completo).
  const ateAqui = indiceAtual >= 0 ? indiceAtual : nos.length - 1;
  const andado = pontos
    .slice(0, ateAqui + 1)
    .map((p, i, arr) => {
      if (i === 0) return `M ${meio + p.x} ${p.y}`;
      const a = arr[i - 1];
      return `C ${meio + a.x} ${a.y + PASSO / 2} ${meio + p.x} ${p.y - PASSO / 2} ${meio + p.x} ${p.y}`;
    })
    .join(" ");

  if (!nos.length) return null;

  return (
    <section className="relative" data-testid={testid} data-tour="trilha-dia" ref={raiz}>
      <div className="relative mx-auto" style={{ height: altura, maxWidth: 360 }}>
        <svg
          className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2"
          width="240"
          height={altura}
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="trilha-dia-luz" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4FD9FF" />
              <stop offset="100%" stopColor="#8B7BFF" />
            </linearGradient>
          </defs>
          <path d={caminho} fill="none" stroke="rgba(150,200,255,0.12)" strokeWidth="18" strokeLinecap="round" />
          {andado && ateAqui > 0 && (
            <path d={andado} fill="none" stroke="url(#trilha-dia-luz)" strokeOpacity="0.55" strokeWidth="6" strokeLinecap="round" className="trilha-dia-andado" />
          )}
          <path d={caminho} fill="none" stroke="rgba(79,217,255,0.32)" strokeWidth="2" strokeLinecap="round" strokeDasharray="1 10" />
        </svg>

        {nos.map((no, i) => {
          const p = pontos[i];
          const novo = novos.includes(no.chave);
          const ehAberto = aberto === no.chave;
          return (
            <div
              key={no.chave}
              className="absolute left-1/2"
              style={{ top: p.y - RAIO, transform: `translateX(calc(-50% + ${p.x}px))`, zIndex: ehAberto ? 30 : 10 - Math.min(i, 9) }}
            >
              <div className="relative flex flex-col items-center">
                {/* A etiqueta "COMEÇAR" do Duolingo: salta em cima do nó aceso
                    e diz, sem precisar ler mais nada, onde tocar. */}
                {no.atual && !ehAberto && (
                  <span className={`no-dia-chamada ${no.estado === "resgatar" ? "no-dia-chamada-bau" : ""}`} aria-hidden="true">
                    {no.estado === "resgatar" ? "Abrir" : "Começar"}
                  </span>
                )}
                <div className="relative">
                  <Anel progresso={no.progresso} />
                  <button
                    type="button"
                    onClick={() => setAberto(ehAberto ? null : no.chave)}
                    className={`${classeDoNo(no)} ${novo ? "no-dia-novo" : ""}`}
                    aria-expanded={ehAberto}
                    aria-label={`${no.titulo}${no.estado === "feito" ? " — feito" : no.atual ? " — próximo passo" : ""}`}
                    data-testid={`${testid}-no-${no.chave}`}
                    data-estado={no.estado}
                    data-atual={no.atual || undefined}
                    data-tour={no.atual ? "dash-agora" : undefined}
                  >
                    <IconeDoNo no={no} />
                  </button>
                </div>
                <span
                  className={`pointer-events-none mt-2.5 w-32 text-center text-[13px] font-semibold leading-tight line-clamp-2 ${
                    no.atual ? "text-white" : no.estado === "feito" ? "text-white/60" : "text-white/40"
                  }`}
                >
                  {no.titulo}
                </span>

                {ehAberto && (
                  <div className="absolute top-full z-30 mt-2" style={{ transform: `translateX(${-p.x}px)` }}>
                    <Cartao
                      no={no}
                      ocupado={ocupado === no.chave}
                      aoFechar={() => setAberto(null)}
                      aoExecutar={(n) => {
                        aoExecutar?.(n);
                        if (n.estado !== "resgatar") setAberto(null);
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
