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
 */
export default function Mentis({
  className = "w-10 h-10",
  estado = "neutra",
  variante = "completa",
  animada = true,
  title,
}) {
  const icone = variante === "icone";
  const cls = (nome) => (animada ? nome : "");

  // Abertura vertical dos olhos por estado. `analise` fecha para uma fresta —
  // é o que o olho humano lê como concentração.
  const alturaOlho = { neutra: 5.2, analise: 2.4, confirmando: 4.2 }[estado] ?? 5.2;
  const inclinacao = estado === "confirmando" ? -6 : 0;

  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
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

      {/* Núcleo */}
      <circle cx="50" cy="47" r={icone ? 34 : 27} fill="url(#mentis-nucleo)" />
      <circle
        cx="50" cy="47" r={icone ? 34 : 27}
        fill="none" stroke="#CBEEFF" strokeWidth="0.9" opacity="0.55"
      />
      {/* Reflexo especular: dá volume sem precisar de sombra interna. */}
      <ellipse cx={icone ? 39 : 41} cy={icone ? 33 : 36} rx={icone ? 9 : 7} ry={icone ? 6 : 4.6}
        fill="#FFFFFF" opacity="0.28" />

      {/* Olhos — cápsulas estreitas, nunca círculos. */}
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
