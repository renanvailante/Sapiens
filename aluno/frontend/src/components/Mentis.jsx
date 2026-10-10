/**
 * Mentis — a entidade cognitiva do Sapiens.
 *
 * É o mascote da plataforma, e a direção de arte tem uma regra que vale mais
 * que qualquer detalhe de desenho: **mentor, não bichinho**. Por isso aqui não
 * há animal, não há sorriso, não há salto elástico — há um núcleo de luz com
 * dois olhos, um anel em órbita e uma cauda em gota. O que ela faz é pulsar
 * devagar (`.mentis-halo`), girar a órbita (`.mentis-orbita`) e piscar de vez
 * em quando (`.mentis-olho`).
 *
 * Os olhos são deliberadamente ESTREITOS, não dois pontos redondos: ponto
 * redondo lê como companion de robô e puxa o registro para colega de estudo
 * gamificado, que é exatamente o tom que o produto descartou.
 *
 * `estado` muda a expressão sem trocar de desenho:
 *   neutra      — repouso
 *   analise     — olhos mais fechados, luz concentrada (está lendo)
 *   confirmando — leve inclinação e brilho estável (reconhece o avanço; NÃO
 *                 é "animada": mentor confirma, não comemora com confete)
 *
 * `variante="icone"` remove órbita e cauda. Em 16-24px (favicon, chip, botão)
 * o anel vira borrão e a gota some — o que sobrevive em qualquer escala é
 * núcleo + olhos, então em tamanho pequeno é só isso que se desenha.
 *
 * ---------------------------------------------------------------------------
 * REVISTO EM 2026-10-09 — ela virou a GUIA do produto
 * ---------------------------------------------------------------------------
 *
 * O dono pediu a Mentis conduzindo o aluno pela trilha do dia, "com muitas
 * animações, e até mesmo uma voz" (Duolingo como referência total). A forma
 * não mudou — continua núcleo de luz, olhos em cápsula, sem animal e sem
 * boca — e a regra "mentor, não bichinho" passou a valer para a FALA (sem
 * emoji, sem euforia), não para o movimento. Ela ganhou:
 *
 *   falando   — o núcleo "respira" no ritmo da fala e duas ondas saem do lado
 *               (é assim que ela fala sem ter boca);
 *   feliz     — os olhos viram dois arcos e ela dá um salto curto. É o único
 *               estado que celebra, e só aparece quando há o que celebrar
 *               (um passo da trilha feito, contado pelo servidor);
 *   surpresa  — olhos mais altos, para o prêmio pronto;
 *   `olhar`   — de -1 (esquerda) a 1 (direita): ela OLHA para o que aponta;
 *   `flutuar` — paira devagar, para quando ela está no conteúdo, não no chip.
 */
import { useEffect, useState } from "react";

export default function Mentis({
  className = "w-10 h-10",
  estado = "neutra",
  variante = "completa",
  animada = true,
  olhar = 0,
  flutuar = false,
  title,
}) {
  const icone = variante === "icone";
  const cls = (nome) => (animada ? nome : "");

  // Abertura vertical dos olhos por estado. `analise` fecha para uma fresta —
  // é o que o olho humano lê como concentração.
  const alturaOlho = { neutra: 5.2, analise: 2.4, confirmando: 4.2, falando: 5.2, feliz: 4.2, surpresa: 7.6 }[estado] ?? 5.2;
  const inclinacao = estado === "confirmando" ? -6 : estado === "feliz" ? -4 : 0;
  // O olhar desloca os dois olhos juntos, no máximo 4 unidades do viewBox:
  // mais que isso e eles saem do núcleo.
  const dx = Math.max(-1, Math.min(1, Number(olhar) || 0)) * (icone ? 5 : 4);
  const feliz = estado === "feliz";
  const falando = estado === "falando";

  const raiz = [
    className,
    animada && flutuar ? "mentis-flutua" : "",
    animada && feliz ? "mentis-feliz" : "",
    animada && falando ? "mentis-falando" : "",
  ].filter(Boolean).join(" ");

  return (
    <svg
      viewBox="0 0 100 100"
      className={raiz}
      data-estado={estado}
      role={title ? "img" : undefined}
      aria-label={title || undefined}
      aria-hidden={title ? undefined : "true"}
    >
      <defs>
        <radialGradient id="mentis-nucleo" cx="42%" cy="34%" r="72%">
          <stop offset="0%" stopColor="#BFF0FF" />
          <stop offset="38%" stopColor="#4FD9FF" />
          <stop offset="72%" stopColor="#2E7FD6" />
          <stop offset="100%" stopColor="#123A78" />
        </radialGradient>
        <radialGradient id="mentis-halo" cx="50%" cy="50%" r="50%">
          <stop offset="55%" stopColor="#4FD9FF" stopOpacity="0" />
          <stop offset="82%" stopColor="#4FD9FF" stopOpacity="0.34" />
          <stop offset="100%" stopColor="#8B7BFF" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="mentis-anel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4FD9FF" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#8B7BFF" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#4FD9FF" stopOpacity="0.9" />
        </linearGradient>
        <filter id="mentis-brilho" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Halo: a única parte que pulsa. Fica atrás de tudo. */}
      <circle cx="50" cy="47" r="44" fill="url(#mentis-halo)" className={cls("mentis-halo")} />

      {!icone && (
        <>
          {/* Cauda em gota — a entidade não pousa no chão, ela paira. */}
          <path
            d="M50 74 C40 82 44 95 50 97 C56 95 60 82 50 74 Z"
            fill="url(#mentis-nucleo)"
            opacity="0.42"
          />
          {/* Anel em órbita: elipse inclinada, girando devagar. */}
          <g className={cls("mentis-orbita")}>
            <ellipse
              cx="50" cy="47" rx="40" ry="15"
              fill="none" stroke="url(#mentis-anel)" strokeWidth="1.6"
              transform="rotate(-22 50 47)" opacity="0.75"
            />
            <circle cx="88" cy="38" r="2.4" fill="#BFF0FF" filter="url(#mentis-brilho)" />
          </g>
        </>
      )}

      {/* A fala: duas ondas saindo do lado direito do núcleo. Ela não tem
          boca (é luz, não bicho) — é assim que o desenho diz "está falando". */}
      {falando && animada && (
        <g className="mentis-ondas" fill="none" stroke="#9FE9FF" strokeLinecap="round">
          <path d={icone ? "M87 37 Q92 47 87 57" : "M82 38 Q88 47 82 56"} strokeWidth="2.6" />
          <path d={icone ? "M93 31 Q99 47 93 63" : "M89 32 Q97 47 89 62"} strokeWidth="2" opacity="0.7" />
        </g>
      )}

      {/* Núcleo */}
      <g className={falando && animada ? "mentis-nucleo-fala" : undefined} style={{ transformOrigin: "50px 47px" }}>
      <circle cx="50" cy="47" r={icone ? 34 : 27} fill="url(#mentis-nucleo)" />
      <circle
        cx="50" cy="47" r={icone ? 34 : 27}
        fill="none" stroke="#CBEEFF" strokeWidth="0.9" opacity="0.55"
      />
      {/* Reflexo especular: dá volume sem precisar de sombra interna. */}
      <ellipse cx={icone ? 39 : 41} cy={icone ? 33 : 36} rx={icone ? 9 : 7} ry={icone ? 6 : 4.6}
        fill="#FFFFFF" opacity="0.28" />

      {/* Olhos — cápsulas estreitas, nunca círculos. Feliz, viram arcos: o
          sorriso de quem não tem boca mora nos olhos. */}
      {feliz ? (
        <g
          fill="none"
          stroke="#041428"
          strokeWidth={icone ? 4 : 3.2}
          strokeLinecap="round"
          transform={`translate(${dx} 0) rotate(${inclinacao} 50 47)`}
        >
          <path d={icone ? "M34 50 Q39 41 44 50" : "M39 49 Q43 42.5 47 49"} />
          <path d={icone ? "M56 50 Q61 41 66 50" : "M53 49 Q57 42.5 61 49"} />
        </g>
      ) : (
        <g transform={`translate(${dx} 0)`} className="mentis-olhar">
          <g
            className={cls("mentis-olho")}
            fill="#041428"
            transform={`rotate(${inclinacao} 50 47)`}
            style={{ transformOrigin: "50px 47px" }}
          >
            <rect
              x={icone ? 35 : 40} y={47 - alturaOlho / 2}
              width={icone ? 8 : 6} height={alturaOlho} rx={icone ? 4 : 3}
            />
            <rect
              x={icone ? 57 : 54} y={47 - alturaOlho / 2}
              width={icone ? 8 : 6} height={alturaOlho} rx={icone ? 4 : 3}
            />
          </g>
        </g>
      )}
      </g>

      {/* Duas faíscas quando ela está feliz — curtas, e só neste estado. */}
      {feliz && animada && !icone && (
        <g className="mentis-faiscas" fill="#FFE29A">
          <path d="M18 22 l2 5 l5 2 l-5 2 l-2 5 l-2 -5 l-5 -2 l5 -2 z" />
          <path d="M82 14 l1.4 3.6 l3.6 1.4 l-3.6 1.4 l-1.4 3.6 l-1.4 -3.6 l-3.6 -1.4 l3.6 -1.4 z" />
        </g>
      )}
    </svg>
  );
}

/** Três pontos em onda — "a Mentis está pensando". Sem texto: o movimento já
 *  diz que há algo acontecendo, e uma frase aqui viraria ruído a cada turno. */
export function MentisDigitando({ className = "" }) {
  return (
    <span className={`inline-flex items-center gap-1 ${className}`} aria-label="A Mentis está escrevendo">
      {[0, 1, 2].map((i) => (
        <span key={i} className="mentis-ponto w-1.5 h-1.5 rounded-full bg-[#4FD9FF]" />
      ))}
    </span>
  );
}

// Frases curtas do estado de processamento — só aparecem enquanto HÁ uma
// chamada real em curso (`ativo` segue 1:1 a promise pendente de quem usa
// isto). Nunca uma etapa fixa fingindo trabalho que não está acontecendo:
// é rotação cosmética sobre uma espera real, não uma barra de progresso falsa.
const FRASES_PENSANDO = [
  "Estou analisando seu desempenho…",
  "Procurando um padrão nos seus erros.",
  "Estou calibrando a dificuldade.",
  "Estou escolhendo as questões mais úteis.",
  "Cruzando isso com o seu histórico.",
  "Verificando a evidência antes de responder.",
];

/** Mesmos pontinhos de `MentisDigitando`, com uma frase de status ao lado que
 *  troca a cada ~2s enquanto `ativo` for true. Começa num índice aleatório
 *  para não repetir sempre a mesma abertura entre uma chamada e outra. */
export function MentisPensando({ ativo, className = "" }) {
  const [i, setI] = useState(() => Math.floor(Math.random() * FRASES_PENSANDO.length));

  useEffect(() => {
    if (!ativo) return undefined;
    const id = setInterval(() => setI((prev) => (prev + 1) % FRASES_PENSANDO.length), 1900);
    return () => clearInterval(id);
  }, [ativo]);

  if (!ativo) return null;
  return (
    <div className={`inline-flex items-center gap-2 ${className}`} aria-live="polite">
      <MentisDigitando />
      <span className="text-xs text-white/50">{FRASES_PENSANDO[i]}</span>
    </div>
  );
}
