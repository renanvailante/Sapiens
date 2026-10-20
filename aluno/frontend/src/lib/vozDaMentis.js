/**
 * A VOZ DA MENTIS — a fala do balão, em voz alta.
 *
 * Pedido do dono em 2026-10-09: a Mentis como guia, "com muitas animações, e
 * até mesmo uma voz". Em 2026-10-19: "muito mais natural, como se fosse uma
 * pessoa de verdade falando" — e "de graça e sem usar nenhuma API".
 *
 * Por isso a voz é GRAVADA. As frases que ela diz são um catálogo fixo
 * (`falasGravadas.json`), gravado uma única vez com uma voz brasileira neural
 * (`scripts/gravar_falas_da_mentis.py`) e publicado como MP3 em `public/voz/`.
 * Tocar é baixar um arquivo estático: nenhuma API, nenhum custo por fala,
 * nenhum texto do aluno saindo do aparelho. O que muda de aluno para aluno
 * (nome, números, títulos) continua escrito no balão; a voz diz a ideia com
 * frases inteiras, emendadas com uma pausa de gente.
 *
 * Reserva: sem Web Audio, ou com um arquivo que não carregou, ela lê o texto
 * do balão com a síntese do próprio aparelho (`speechSynthesis`), a voz de
 * antes — a guia nunca emudece.
 *
 * O que não mudou:
 * - **Desligada por padrão**, com o botão de ligar sempre no balão. Uma frase
 *   inteira falada sem aviso no ônibus ou na sala de aula é constrangimento.
 *   Quem liga uma vez fica com ela ligada (`localStorage`, por aparelho).
 * - **Nunca quebra nada.** O navegador só toca som depois de um gesto do aluno
 *   na página. Antes disso a fala fica PENDENTE e sai no primeiro toque, se o
 *   balão ainda estiver na tela; o texto continua no balão de qualquer jeito.
 * - **Uma fala de cada vez.** Falar corta a anterior; sair da tela cala.
 */
import catalogo from "./falasGravadas.json";
import manifesto from "./falasGravadas.manifesto.json";

const CHAVE = "sapiens:voz-mentis";
export const EVENTO_VOZ = "sapiens:voz-mentis";

// Entre uma frase gravada e a seguinte: o fôlego de quem fala.
const PAUSA_ENTRE_FRASES = 0.32;

function sinteseDisponivel() {
  try {
    return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  } catch {
    return false;
  }
}

function classeDeAudio() {
  try {
    return typeof window !== "undefined" ? window.AudioContext || window.webkitAudioContext || null : null;
  } catch {
    return null;
  }
}

function gravadaDisponivel() {
  try {
    return Boolean(classeDeAudio() && typeof fetch === "function");
  } catch {
    return false;
  }
}

export function vozDisponivel() {
  return gravadaDisponivel() || sinteseDisponivel();
}

export function vozLigada() {
  try {
    return localStorage.getItem(CHAVE) === "1";
  } catch {
    return false;
  }
}

export function definirVoz(ligada) {
  try {
    localStorage.setItem(CHAVE, ligada ? "1" : "0");
  } catch {
    /* storage bloqueado: vale só nesta página */
  }
  if (!ligada) calar();
  try {
    window.dispatchEvent(new CustomEvent(EVENTO_VOZ, { detail: ligada }));
  } catch {
    /* fora do navegador */
  }
}

/** O texto que se fala: sem as aspas angulares e sem o que não se pronuncia. */
export function textoFalavel(texto) {
  return String(texto || "")
    .replace(/[«»"“”]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * O arquivo de uma fala do catálogo, ou `null`. Fala ainda não gravada usa a
 * `reserva` declarada no catálogo (uma frase vizinha já gravada) — é o que
 * deixa acrescentar uma frase nova antes de a cota grátis do dia permitir
 * gravá-la.
 */
export function arquivoDaFala(id) {
  const fala = catalogo.falas[id];
  if (!fala) return null;
  const hash = manifesto[id];
  if (hash) return `${process.env.PUBLIC_URL || ""}/voz/${id}-${hash}.mp3`;
  return fala.reserva ? arquivoDaFala(fala.reserva) : null;
}

// ---------------------------------------------------------------- a voz gravada

let contexto = null;
let falaAtual = null; // { fontes, pendente }
const audios = new Map(); // url -> Promise<AudioBuffer>: cada frase baixa uma vez por página

function obterContexto() {
  if (contexto) return contexto;
  const Classe = classeDeAudio();
  if (!Classe) return null;
  try {
    contexto = new Classe();
  } catch {
    contexto = null;
  }
  return contexto;
}

/** O navegador só libera som depois de um gesto. No primeiro toque em
 *  qualquer lugar, o contexto destrava e a fala pendente (se houver) sai. */
function aoPrimeiroGesto() {
  const ctx = contexto;
  if (ctx && ctx.state !== "running") {
    try {
      ctx.resume();
    } catch {
      /* segue suspenso: a próxima fala tenta de novo */
    }
  }
  const pendente = falaAtual?.pendente;
  if (pendente) {
    falaAtual.pendente = null;
    pendente();
  }
}

if (typeof window !== "undefined") {
  try {
    ["pointerdown", "keydown", "touchend"].forEach((ev) =>
      window.addEventListener(ev, aoPrimeiroGesto, { capture: true, passive: true }),
    );
  } catch {
    /* fora do navegador */
  }
}

function tentarDestravar(ctx) {
  if (ctx.state === "running") return Promise.resolve(true);
  return Promise.race([
    Promise.resolve(ctx.resume?.()).then(() => ctx.state === "running", () => false),
    new Promise((r) => setTimeout(() => r(false), 300)),
  ]);
}

function decodificar(ctx, buffer) {
  return new Promise((resolve, reject) => {
    try {
      const p = ctx.decodeAudioData(buffer, resolve, reject);
      if (p && typeof p.then === "function") p.then(resolve, reject);
    } catch (e) {
      reject(e);
    }
  });
}

function carregar(ctx, url) {
  if (!audios.has(url)) {
    const promessa = fetch(url)
      .then((r) => {
        // O Cloudflare devolve o index.html (200) para arquivo ausente: o
        // tipo é o que diz se veio áudio.
        if (!r.ok || !(r.headers.get("content-type") || "").includes("audio")) throw new Error("sem áudio");
        return r.arrayBuffer();
      })
      .then((b) => decodificar(ctx, b));
    promessa.catch(() => audios.delete(url));
    audios.set(url, promessa);
  }
  return audios.get(url);
}

/**
 * Toca as frases gravadas em sequência. Resolve `true` quando tocou (ou ficou
 * pendente de um gesto) e `false` quando não havia como — aí quem chamou cai
 * na voz do aparelho.
 */
async function falarGravado(fala, ids, { aoComecar, aoTerminar }) {
  const ctx = obterContexto();
  if (!ctx) return false;
  const urls = ids.map(arquivoDaFala);
  if (!urls.length || urls.some((u) => !u)) return false;

  let buffers;
  try {
    buffers = await Promise.all(urls.map((u) => carregar(ctx, u)));
  } catch {
    return false;
  }
  if (falaAtual !== fala) return true; // já foi substituída: nada a tocar

  const tocar = () => {
    if (falaAtual !== fala) return;
    let quando = ctx.currentTime + 0.05;
    let ultima = null;
    buffers.forEach((buf) => {
      const fonte = ctx.createBufferSource();
      fonte.buffer = buf;
      fonte.connect(ctx.destination);
      fonte.start(quando);
      quando += buf.duration + PAUSA_ENTRE_FRASES;
      fala.fontes.push(fonte);
      ultima = fonte;
    });
    aoComecar?.();
    if (ultima) {
      ultima.onended = () => {
        if (falaAtual === fala) falaAtual = null;
        aoTerminar?.();
      };
    }
  };

  if (await tentarDestravar(ctx)) tocar();
  else fala.pendente = tocar;
  return true;
}

// ------------------------------------------------------- a voz do aparelho

/** A melhor voz em português do Brasil que o aparelho tiver. As vozes
 *  "naturais"/"online" (Edge, Chrome) soam muito menos robóticas que a voz
 *  padrão do sistema, então elas vêm primeiro; depois as femininas conhecidas
 *  (a Mentis é "ela" em todo o produto); depois qualquer pt-BR; depois
 *  qualquer português. */
export function escolherVoz(vozes) {
  const lista = Array.isArray(vozes) ? vozes : [];
  const br = lista.filter((v) => /^pt[-_]BR/i.test(v.lang || ""));
  const pt = lista.filter((v) => /^pt/i.test(v.lang || ""));
  const pref = (v) => /natural|online|neural/i.test(v.name || "");
  const fem = (v) => /luciana|francisca|thalita|vit[oó]ria|maria|female|feminina|google portugu[eê]s do brasil/i.test(v.name || "");
  return (
    br.find((v) => pref(v) && fem(v)) ||
    br.find(pref) ||
    br.find(fem) ||
    br[0] ||
    pt[0] ||
    null
  );
}

let vozEscolhida = null;

function vozDoAparelho() {
  if (vozEscolhida) return vozEscolhida;
  try {
    vozEscolhida = escolherVoz(window.speechSynthesis.getVoices());
  } catch {
    vozEscolhida = null;
  }
  return vozEscolhida;
}

// As vozes chegam assíncronas no Chrome: a primeira `getVoices()` costuma
// voltar vazia. Quando a lista muda, a escolha é refeita.
if (sinteseDisponivel()) {
  try {
    window.speechSynthesis.addEventListener?.("voiceschanged", () => {
      vozEscolhida = null;
    });
  } catch {
    /* navegador antigo: fica com a voz padrão */
  }
}

function falarNoAparelho(texto, { aoComecar, aoTerminar }) {
  if (!sinteseDisponivel() || !texto) {
    aoTerminar?.();
    return false;
  }
  try {
    const sintese = window.speechSynthesis;
    sintese.cancel();
    const fala = new window.SpeechSynthesisUtterance(texto);
    const voz = vozDoAparelho();
    if (voz) fala.voice = voz;
    fala.lang = voz?.lang || "pt-BR";
    // Tom e velocidade naturais: o 1.08 de antes deixava a voz do sistema
    // ainda mais artificial.
    fala.rate = 1;
    fala.pitch = 1;
    fala.volume = 1;
    if (aoComecar) fala.onstart = aoComecar;
    if (aoTerminar) {
      fala.onend = aoTerminar;
      fala.onerror = aoTerminar;
    }
    sintese.speak(fala);
    return true;
  } catch {
    aoTerminar?.();
    return false;
  }
}

// ---------------------------------------------------------------- a porta

/**
 * Fala. `voz` é a lista de frases gravadas (ids de `falasGravadas.json`) que
 * dizem o balão; `texto` é o balão escrito, lido pela voz do aparelho só se
 * as gravações não puderem tocar. Corta a fala anterior — a Mentis nunca fala
 * duas coisas ao mesmo tempo. `aoComecar`/`aoTerminar` deixam o desenho dela
 * "falar" junto. Devolve `false` quando nem tentou (voz desligada, sem voz
 * nenhuma, nada a dizer).
 */
export function falar(texto, { voz = [], forcar = false, aoComecar, aoTerminar } = {}) {
  if (!vozDisponivel()) return false;
  if (!forcar && !vozLigada()) return false;
  const limpo = textoFalavel(texto);
  const ids = (Array.isArray(voz) ? voz : [voz]).filter(Boolean);
  if (!limpo && !ids.length) return false;
  calar();

  if (forcar) {
    // O toque no alto-falante É o gesto que destrava o som.
    try {
      obterContexto()?.resume?.();
    } catch {
      /* segue */
    }
  }

  const fala = { fontes: [], pendente: null };
  falaAtual = fala;
  const ganchos = { aoComecar, aoTerminar };

  if (!ids.length || !gravadaDisponivel()) return falarNoAparelho(limpo, ganchos);

  falarGravado(fala, ids, ganchos)
    .catch(() => false)
    .then((tocou) => {
      if (!tocou && falaAtual === fala) falarNoAparelho(limpo, ganchos);
    });
  return true;
}

export function calar() {
  const fala = falaAtual;
  falaAtual = null;
  if (fala) {
    fala.fontes.forEach((f) => {
      try {
        f.onended = null;
        f.stop();
      } catch {
        /* já parou */
      }
    });
  }
  try {
    if (sinteseDisponivel()) window.speechSynthesis.cancel();
  } catch {
    /* nada a calar */
  }
}
