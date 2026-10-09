/**
 * O SOM DO SAPIENS — o "plim" do acerto, à moda do Duolingo.
 *
 * Pedido do dono em 2026-10-08: inspirar-se TOTALMENTE no Duolingo, com muito
 * mais coisa prendendo a atenção. No Duolingo metade da recompensa do acerto
 * é o som — o olho está no enunciado, e é o ouvido que fica sabendo primeiro.
 *
 * Três decisões:
 *
 * 1. **Sintetizado, não arquivo.** Cada som é meia dúzia de osciladores do
 *    Web Audio. Zero byte a mais no deploy, zero requisição, e nada para o
 *    aluno baixar (ver a regra "nenhum aluno baixa nada" em `inviolaveis.md`
 *    — não é download, mas também não é peso).
 * 2. **Ligado por padrão, com um botão de mudo sempre à vista** na tela de
 *    questão. A preferência é do aparelho (`localStorage`): quem estuda na
 *    biblioteca desliga uma vez e pronto.
 * 3. **Nunca quebra nada.** Navegador sem Web Audio, aba sem gesto do usuário,
 *    storage bloqueado: tudo vira silêncio, nunca erro.
 */

const CHAVE = "sapiens:som";
let contexto = null;

export function somLigado() {
  try {
    return localStorage.getItem(CHAVE) !== "0";
  } catch {
    return true;
  }
}

export function definirSom(ligado) {
  try {
    localStorage.setItem(CHAVE, ligado ? "1" : "0");
  } catch {
    /* storage bloqueado: vale só nesta página */
  }
  window.dispatchEvent(new CustomEvent("sapiens:som", { detail: ligado }));
}

function ctx() {
  if (typeof window === "undefined") return null;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  if (!contexto) {
    try {
      contexto = new AC();
    } catch {
      return null;
    }
  }
  if (contexto.state === "suspended") contexto.resume().catch(() => {});
  return contexto;
}

/** Uma nota: oscilador + envelope curto. `quando` é relativo a agora. */
function nota(ac, { freq, quando = 0, dur = 0.14, tipo = "sine", volume = 0.18, deslize = null }) {
  const t0 = ac.currentTime + quando;
  const osc = ac.createOscillator();
  const ganho = ac.createGain();
  osc.type = tipo;
  osc.frequency.setValueAtTime(freq, t0);
  if (deslize) osc.frequency.exponentialRampToValueAtTime(deslize, t0 + dur);
  ganho.gain.setValueAtTime(0.0001, t0);
  ganho.gain.exponentialRampToValueAtTime(volume, t0 + 0.012);
  ganho.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  osc.connect(ganho).connect(ac.destination);
  osc.start(t0);
  osc.stop(t0 + dur + 0.02);
}

// Notas (Hz). Mi5, Lá5, Dó6... o acerto sobe uma quarta, como o "plim-plim".
const N = { C5: 523.25, E5: 659.25, G5: 783.99, A5: 880, B5: 987.77, C6: 1046.5, E6: 1318.5, G6: 1568 };

const SONS = {
  /** Acerto: duas notas que sobem. Curto — a próxima questão não espera. */
  acerto: (ac) => {
    nota(ac, { freq: N.E5, dur: 0.11, tipo: "triangle", volume: 0.2 });
    nota(ac, { freq: N.A5, quando: 0.09, dur: 0.22, tipo: "triangle", volume: 0.22 });
    nota(ac, { freq: N.A5 * 2, quando: 0.09, dur: 0.18, tipo: "sine", volume: 0.05 });
  },
  /** Erro: um "bum" grave e macio. Informa sem castigar. */
  erro: (ac) => {
    nota(ac, { freq: 220, dur: 0.16, tipo: "triangle", volume: 0.16, deslize: 150 });
    nota(ac, { freq: 165, quando: 0.12, dur: 0.22, tipo: "sine", volume: 0.12, deslize: 110 });
  },
  /** Combo (3, 5, 10 seguidas): o acerto com uma nota a mais em cima. */
  combo: (ac) => {
    nota(ac, { freq: N.E5, dur: 0.09, tipo: "triangle", volume: 0.18 });
    nota(ac, { freq: N.A5, quando: 0.07, dur: 0.1, tipo: "triangle", volume: 0.2 });
    nota(ac, { freq: N.E6, quando: 0.14, dur: 0.26, tipo: "triangle", volume: 0.18 });
  },
  /** Moeda: resgate de missão, Sparks entrando. */
  moeda: (ac) => {
    nota(ac, { freq: N.B5, dur: 0.08, tipo: "square", volume: 0.07 });
    nota(ac, { freq: N.E6, quando: 0.07, dur: 0.3, tipo: "square", volume: 0.07 });
  },
  /** Fim de série: arpejo maior que resolve. */
  fim: (ac) => {
    [N.C5, N.E5, N.G5, N.C6].forEach((f, i) =>
      nota(ac, { freq: f, quando: i * 0.09, dur: 0.24, tipo: "triangle", volume: 0.17 }),
    );
    nota(ac, { freq: N.C6, quando: 0.36, dur: 0.5, tipo: "sine", volume: 0.12 });
  },
  /** Ofensiva: o "fuuu" da chama acendendo e um acorde em cima. */
  ofensiva: (ac) => {
    nota(ac, { freq: 180, dur: 0.45, tipo: "sawtooth", volume: 0.035, deslize: 720 });
    [N.E5, N.G5, N.C6].forEach((f) =>
      nota(ac, { freq: f, quando: 0.32, dur: 0.6, tipo: "triangle", volume: 0.1 }),
    );
  },
  /** O presente do Plus: fanfarra curta. */
  presente: (ac) => {
    [N.C5, N.E5, N.G5, N.C6, N.E6].forEach((f, i) =>
      nota(ac, { freq: f, quando: i * 0.07, dur: 0.2, tipo: "square", volume: 0.06 }),
    );
    [N.C6, N.E6, N.G6].forEach((f) =>
      nota(ac, { freq: f, quando: 0.4, dur: 0.8, tipo: "triangle", volume: 0.1 }),
    );
  },
};

/** Toca um som pelo nome. Silêncio se o aluno desligou ou se não há áudio. */
export function tocar(nome) {
  if (!somLigado()) return;
  const som = SONS[nome];
  if (!som) return;
  const ac = ctx();
  if (!ac) return;
  try {
    som(ac);
  } catch {
    /* um som que falha não pode derrubar a resposta */
  }
}
