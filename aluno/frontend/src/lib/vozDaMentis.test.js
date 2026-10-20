/**
 * A voz da Mentis: frases GRAVADAS (arquivos estáticos, sem API), com a voz do
 * aparelho como reserva. jsdom não tem Web Audio nem síntese — os dois são
 * dublês mínimos aqui.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const catalogo = require("./falasGravadas.json");
const manifesto = require("./falasGravadas.manifesto.json");

const PASTA_VOZ = path.join(__dirname, "..", "..", "public", "voz");

/** Mesma conta de `hash_da_fala` em `scripts/gravar_falas_da_mentis.py`. */
function hashDaFala(fala) {
  const estilo = catalogo.estilos[fala.tom];
  return crypto.createHash("sha256")
    .update([catalogo.voz, catalogo.modelo, estilo, fala.texto].join("||"), "utf8")
    .digest("hex")
    .slice(0, 10);
}

function carregar() {
  let mod;
  jest.isolateModules(() => {
    mod = require("./vozDaMentis");
  });
  return mod;
}

function dubleDaSintese() {
  const faladas = [];
  window.SpeechSynthesisUtterance = function Utt(texto) {
    this.texto = texto;
  };
  window.speechSynthesis = {
    getVoices: () => [],
    cancel: jest.fn(),
    speak: jest.fn((u) => faladas.push(u.texto)),
    addEventListener: () => {},
  };
  return faladas;
}

function dubleDoAudio({ suspenso = false } = {}) {
  const tocadas = [];
  const estado = { gesto: !suspenso };
  class Contexto {
    constructor() {
      this.state = suspenso ? "suspended" : "running";
      this.currentTime = 0;
      this.destination = {};
    }
    resume() {
      if (estado.gesto) this.state = "running";
      return Promise.resolve();
    }
    createBufferSource() {
      const fonte = { connect: () => {}, start: (t) => tocadas.push({ t, dur: fonte.buffer.duration }), stop: () => {} };
      return fonte;
    }
    decodeAudioData(_buf, ok) {
      const audio = { duration: 2 };
      ok?.(audio);
      return Promise.resolve(audio);
    }
  }
  window.AudioContext = Contexto;
  return { tocadas, estado };
}

function fetchDeMp3(tipo = "audio/mpeg") {
  return jest.fn(() =>
    Promise.resolve({ ok: true, status: 200, headers: { get: () => tipo }, arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) }),
  );
}

const esperarMuito = async () => {
  for (let i = 0; i < 20; i += 1) await new Promise((r) => setTimeout(r, 0));
};

beforeEach(() => {
  delete window.AudioContext;
  delete window.webkitAudioContext;
  delete window.speechSynthesis;
  delete window.SpeechSynthesisUtterance;
  global.fetch = undefined;
  localStorage.clear();
  localStorage.setItem("sapiens:voz-mentis", "1");
});

describe("o catálogo gravado", () => {
  test("todo áudio é do texto ATUAL: mudou a frase, regrave (scripts/gravar_falas_da_mentis.py)", () => {
    Object.entries(catalogo.falas).forEach(([id, fala]) => {
      const gravada = manifesto[id];
      if (!gravada) {
        // Ainda não gravada: precisa de uma reserva que já foi.
        expect({ id, reserva: fala.reserva && manifesto[fala.reserva] ? "ok" : "sem reserva gravada" }).toEqual({ id, reserva: "ok" });
        return;
      }
      expect({ id, hash: gravada }).toEqual({ id, hash: hashDaFala(fala) });
      expect(fs.existsSync(path.join(PASTA_VOZ, `${id}-${gravada}.mp3`))).toBe(true);
    });
  });

  test("nenhum arquivo ou manifesto sobrando", () => {
    Object.keys(manifesto).forEach((id) => expect(catalogo.falas[id]).toBeDefined());
    const esperados = new Set(Object.entries(manifesto).map(([id, h]) => `${id}-${h}.mp3`));
    fs.readdirSync(PASTA_VOZ).forEach((arq) => expect(esperados.has(arq)).toBe(true));
  });

  test("toda frase que o app pede existe no catálogo", () => {
    const fontes = ["../lib/trilhaDoDia.js", "../pages/BemVindo.jsx"].map((f) => fs.readFileSync(path.join(__dirname, f), "utf8"));
    const pedidas = new Set();
    fontes.forEach((src) => {
      // Toda string entre aspas numa linha que atribui ou empurra `voz`.
      src.split("\n").filter((l) => /\bvoz\b\s*(?:[:=]|\.push)/.test(l)).forEach((l) => {
        for (const m of l.matchAll(/(?:(\w+)=)?"([a-z]+(?:-[a-z0-9]+)*)"/g)) {
          if (!m[1] || m[1] === "voz") pedidas.add(m[2]); // `tamanho="p"` na mesma linha não é fala
        }
      });
      for (const m of src.matchAll(/"Bo[am] [a-z]+": "([a-z-]+)"/g)) pedidas.add(m[1]);
    });
    expect(pedidas.size).toBeGreaterThan(15);
    pedidas.forEach((id) => expect({ id, existe: Boolean(catalogo.falas[id]) }).toEqual({ id, existe: true }));
  });
});

test("frase sem gravação usa a reserva; frase desconhecida não tem arquivo", () => {
  const { arquivoDaFala } = carregar();
  expect(arquivoDaFala("bom-dia")).toBe(`/voz/bom-dia-${manifesto["bom-dia"]}.mp3`);
  const semGravacao = Object.keys(catalogo.falas).find((id) => !manifesto[id]);
  if (semGravacao) expect(arquivoDaFala(semGravacao)).toBe(arquivoDaFala(catalogo.falas[semGravacao].reserva));
  expect(arquivoDaFala("nao-existe")).toBeNull();
});

test("sem Web Audio, lê o balão com a voz do aparelho", () => {
  const faladas = dubleDaSintese();
  const { falar } = carregar();
  expect(falar("Revisão de «Proporção»", { voz: ["bom-dia"] })).toBe(true);
  expect(faladas).toEqual(["Revisão de Proporção"]);
});

test("toca as frases gravadas em sequência, com pausa entre elas, sem a voz do aparelho", async () => {
  const faladas = dubleDaSintese();
  const { tocadas } = dubleDoAudio();
  global.fetch = fetchDeMp3();
  const { falar } = carregar();
  const comecou = jest.fn();
  falar("Bom dia, Ana! Sua ofensiva de 3 dias espera por hoje.", { voz: ["bom-dia", "ofensiva-espera"], aoComecar: comecou });
  await esperarMuito();
  expect(global.fetch.mock.calls.map((c) => c[0])).toEqual([
    `/voz/bom-dia-${manifesto["bom-dia"]}.mp3`,
    `/voz/ofensiva-espera-${manifesto["ofensiva-espera"]}.mp3`,
  ]);
  expect(tocadas).toHaveLength(2);
  expect(tocadas[1].t).toBeGreaterThan(tocadas[0].t + tocadas[0].dur); // a pausa de fôlego
  expect(comecou).toHaveBeenCalled();
  expect(faladas).toEqual([]);
});

test("arquivo que não veio (o Cloudflare devolve HTML) → lê o balão com a voz do aparelho", async () => {
  const faladas = dubleDaSintese();
  dubleDoAudio();
  global.fetch = fetchDeMp3("text/html");
  const { falar } = carregar();
  falar("Boa noite, Ana!", { voz: ["boa-noite"] });
  await esperarMuito();
  expect(faladas).toEqual(["Boa noite, Ana!"]);
});

test("sem gesto ainda, a fala fica pendente e sai no primeiro toque", async () => {
  dubleDaSintese();
  const { tocadas, estado } = dubleDoAudio({ suspenso: true });
  global.fetch = fetchDeMp3();
  const { falar } = carregar();
  falar("Boa noite, Ana!", { voz: ["boa-noite"] });
  await new Promise((r) => setTimeout(r, 400));
  expect(tocadas).toHaveLength(0);

  estado.gesto = true;
  window.dispatchEvent(new Event("pointerdown"));
  await esperarMuito();
  expect(tocadas).toHaveLength(1);
});

test("voz desligada não baixa nem fala nada", () => {
  localStorage.setItem("sapiens:voz-mentis", "0");
  dubleDaSintese();
  dubleDoAudio();
  global.fetch = jest.fn();
  const { falar } = carregar();
  expect(falar("Oi.", { voz: ["bom-dia"] })).toBe(false);
  expect(global.fetch).not.toHaveBeenCalled();
});
