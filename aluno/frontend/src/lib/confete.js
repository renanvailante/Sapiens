/**
 * CONFETE — o fim de lição do Duolingo, num canvas que nasce e some sozinho.
 *
 * Até 2026-10-08 o produto se recusava a ter confete ("um confete que atrasa
 * a próxima questão", `index.css`). O dono pediu o contrário: inspiração
 * total no Duolingo e muito mais animação. A regra que sobrevive da decisão
 * antiga é a que importava: **o confete nunca bloqueia nada**. Ele é um
 * canvas com `pointer-events: none` por cima da tela, dura pouco mais de dois
 * segundos e se remove do DOM ao terminar — o aluno pode clicar em "próxima"
 * no meio da chuva.
 *
 * E ele só cai sobre coisa verdadeira: um acerto, uma série concluída, um dia
 * de ofensiva garantido, o presente do Plus. Nunca para enfeitar uma tela.
 *
 * `prefers-reduced-motion` desliga tudo.
 */

const CORES = ["#4FD9FF", "#8B7BFF", "#FFC85C", "#34D399", "#FF6B8B", "#FFFFFF"];

function movimentoReduzido() {
  try {
    return window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  } catch {
    return false;
  }
}

/**
 * Solta confete a partir de um ponto (em px da janela) ou de um elemento.
 *
 * @param {object} op
 * @param {Element} [op.de]        elemento de onde o confete sai (centro dele)
 * @param {number}  [op.x]         origem x, se não houver elemento (padrão: centro)
 * @param {number}  [op.y]         origem y (padrão: 35% da altura)
 * @param {number}  [op.quantidade] partículas (padrão 90)
 * @param {number}  [op.forca]     velocidade inicial (padrão 11)
 * @param {number}  [op.espalhar]  abertura do leque em graus (padrão 70)
 * @param {string[]} [op.cores]
 */
export function soltarConfete(op = {}) {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  if (movimentoReduzido()) return;

  let x = op.x ?? window.innerWidth / 2;
  let y = op.y ?? window.innerHeight * 0.35;
  if (op.de?.getBoundingClientRect) {
    const r = op.de.getBoundingClientRect();
    x = r.left + r.width / 2;
    y = r.top + r.height / 2;
  }

  const canvas = document.createElement("canvas");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = window.innerWidth * dpr;
  canvas.height = window.innerHeight * dpr;
  Object.assign(canvas.style, {
    position: "fixed",
    inset: "0",
    width: "100vw",
    height: "100vh",
    pointerEvents: "none",
    zIndex: "120",
  });
  canvas.setAttribute("aria-hidden", "true");
  canvas.dataset.testid = "confete";
  document.body.appendChild(canvas);
  const g = canvas.getContext("2d");
  if (!g) {
    canvas.remove();
    return;
  }
  g.scale(dpr, dpr);

  const quantidade = op.quantidade ?? 90;
  const forca = op.forca ?? 11;
  const espalhar = ((op.espalhar ?? 70) * Math.PI) / 180;
  const cores = op.cores || CORES;
  const pecas = Array.from({ length: quantidade }, () => {
    // Leque para cima, com um pouco de tudo para os lados.
    const angulo = -Math.PI / 2 + (Math.random() - 0.5) * espalhar * 2;
    const v = forca * (0.55 + Math.random() * 0.7);
    return {
      x,
      y,
      vx: Math.cos(angulo) * v,
      vy: Math.sin(angulo) * v,
      giro: Math.random() * Math.PI,
      vgiro: (Math.random() - 0.5) * 0.35,
      w: 6 + Math.random() * 6,
      h: 3 + Math.random() * 4,
      cor: cores[Math.floor(Math.random() * cores.length)],
      redondo: Math.random() < 0.3,
    };
  });

  const DURACAO = 2300;
  const inicio = performance.now();
  const quadro = (agora) => {
    const t = agora - inicio;
    g.clearRect(0, 0, window.innerWidth, window.innerHeight);
    const opacidade = t > DURACAO - 500 ? Math.max(0, (DURACAO - t) / 500) : 1;
    for (const p of pecas) {
      p.vy += 0.32; // gravidade
      p.vx *= 0.985; // ar
      p.vy *= 0.985;
      p.x += p.vx;
      p.y += p.vy;
      p.giro += p.vgiro;
      g.save();
      g.globalAlpha = opacidade;
      g.translate(p.x, p.y);
      g.rotate(p.giro);
      g.fillStyle = p.cor;
      if (p.redondo) {
        g.beginPath();
        g.arc(0, 0, p.h, 0, Math.PI * 2);
        g.fill();
      } else {
        // O "achatamento" que gira faz o papel parecer virar no ar.
        g.scale(1, Math.cos(p.giro * 2));
        g.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      }
      g.restore();
    }
    if (t < DURACAO) requestAnimationFrame(quadro);
    else canvas.remove();
  };
  requestAnimationFrame(quadro);
}

/** Duas rajadas dos cantos de baixo — a "chuva" das grandes conquistas. */
export function chuvaDeConfete() {
  if (typeof window === "undefined") return;
  const h = window.innerHeight;
  soltarConfete({ x: window.innerWidth * 0.15, y: h * 0.9, quantidade: 80, forca: 17, espalhar: 30 });
  soltarConfete({ x: window.innerWidth * 0.85, y: h * 0.9, quantidade: 80, forca: 17, espalhar: 30 });
  setTimeout(() => soltarConfete({ quantidade: 70, forca: 9, espalhar: 100 }), 250);
}
