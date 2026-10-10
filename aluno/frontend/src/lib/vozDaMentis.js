/**
 * A VOZ DA MENTIS — a fala do balão, em voz alta.
 *
 * Pedido do dono em 2026-10-09: a Mentis como guia, "com muitas animações, e
 * até mesmo uma voz". Três decisões, as mesmas de `lib/som.js`:
 *
 * 1. **A voz é do aparelho** (`speechSynthesis`, a síntese de fala que já vem
 *    no navegador). Zero arquivo, zero requisição, zero custo de API — e
 *    nenhum texto do aluno sai do aparelho para ser falado. Navegador sem
 *    síntese em português: o botão nem aparece.
 * 2. **Desligada por padrão**, com o botão de ligar sempre no balão. Ao
 *    contrário do "plim" do acerto, uma frase inteira falada sem aviso no
 *    ônibus ou na sala de aula é constrangimento, não recompensa. Quem liga
 *    uma vez fica com ela ligada (`localStorage`, por aparelho).
 * 3. **Nunca quebra nada.** O Chrome só fala depois de um gesto do aluno na
 *    página; antes disso a chamada é silenciosa, e o texto continua no balão.
 */

const CHAVE = "sapiens:voz-mentis";
export const EVENTO_VOZ = "sapiens:voz-mentis";

export function vozDisponivel() {
  try {
    return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  } catch {
    return false;
  }
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

function vozAtual() {
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
if (vozDisponivel()) {
  try {
    window.speechSynthesis.addEventListener?.("voiceschanged", () => {
      vozEscolhida = null;
    });
  } catch {
    /* navegador antigo: fica com a voz padrão */
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
 * Fala um texto. Corta a fala anterior — a Mentis nunca fala duas coisas ao
 * mesmo tempo. `aoComecar`/`aoTerminar` deixam o desenho dela "falar" junto.
 * Devolve `false` quando não falou (voz desligada, sem síntese, sem texto).
 */
export function falar(texto, { forcar = false, aoComecar, aoTerminar } = {}) {
  if (!vozDisponivel()) return false;
  if (!forcar && !vozLigada()) return false;
  const limpo = textoFalavel(texto);
  if (!limpo) return false;
  try {
    const sintese = window.speechSynthesis;
    sintese.cancel();
    const fala = new window.SpeechSynthesisUtterance(limpo);
    const voz = vozAtual();
    if (voz) fala.voice = voz;
    fala.lang = voz?.lang || "pt-BR";
    fala.rate = 1.04;
    fala.pitch = 1.08;
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

export function calar() {
  try {
    if (vozDisponivel()) window.speechSynthesis.cancel();
  } catch {
    /* nada a calar */
  }
}
