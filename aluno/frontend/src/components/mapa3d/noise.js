// Hash + PRNG determinísticos — mesmo espírito do `_seed(hab_id) =
// int(sha1(hab_id)[:8], 16)` do backend (treino_grafo_v0_2.py), mas sem
// depender de hash criptográfico (isto nunca precisa ser imprevisível, só
// estável entre reloads e navegadores). Usado para jitter discreto (rotação
// de nó, variante de prop, ordem de balão). O campo de elevação contínuo do
// terreno usa `simplex-noise`, seedado por uma destas mesmas PRNGs, porque
// escrever Simplex/Perlin à mão é fácil de errar de um jeito que só aparece
// como artefato visual (grade alinhada ao eixo) difícil de diagnosticar.
import { createNoise2D } from "simplex-noise";

function xmur3(str) {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function seed() {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return h >>> 0;
  };
}

function mulberry32(seed) {
  let a = seed;
  return function random() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Valor determinístico e estável em [0,1) a partir de uma chave qualquer. */
export function hash01(key) {
  return mulberry32(xmur3(String(key))())();
}

const _noiseCache = new Map();

/** Função de ruído 2D determinística e cacheada por semente — a mesma
 * semente sempre produz a mesma superfície de ruído, em qualquer navegador. */
export function seededNoise2D(seed) {
  if (!_noiseCache.has(seed)) {
    const rng = mulberry32(xmur3(String(seed))());
    _noiseCache.set(seed, createNoise2D(rng));
  }
  return _noiseCache.get(seed);
}
