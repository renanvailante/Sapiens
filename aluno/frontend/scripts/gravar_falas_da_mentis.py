"""Grava as falas da Mentis UMA VEZ, para o app tocar sem chamar API nenhuma.

Pedido do dono em 2026-10-19: a voz "como se fosse uma pessoa de verdade", e
"de graça e sem usar nenhuma API". A voz do aparelho é de graça mas soa como
leitor de tela; uma voz neural gerada a cada fala custaria por fala (ver
`Cerebro/produto/mentis.md`). O meio-termo é este: as falas são um catálogo
FIXO (`src/lib/falasGravadas.json`), gravado aqui com uma voz brasileira do
Gemini e publicado como arquivo estático (`public/voz/`). O aluno nunca
dispara geração; o Cloudflare só entrega MP3.

Rodar (com o Python do backend, que tem `httpx`, `dotenv` e `lameenc`):

    aluno/backend/venv/bin/python aluno/frontend/scripts/gravar_falas_da_mentis.py

Idempotente: só grava a fala cujo texto, tom, voz ou modelo mudou (o hash vai
no nome do arquivo e em `src/lib/falasGravadas.manifesto.json`). Mudou uma
frase no JSON? Rode de novo — `vozDaMentis.test.js` falha enquanto o áudio não
acompanhar o texto. Nunca troca de modelo sozinho: a voz do catálogo inteiro
tem de ser a mesma.

**A cota grátis é de 10 pedidos por dia por modelo** (medido em 2026-10-19:
"limit: 10 requests per day on Free Tier"). Por isso as falas do mesmo tom vão
num pedido SÓ, separadas por `<long pause>`, e o áudio é cortado nas N-1
maiores pausas — 24 falas cabem em 2 ou 3 pedidos. Se um corte não bater com o
tamanho do texto, aquele lote não é gravado (melhor faltar do que tocar a
frase errada). Em 429 ele para e retoma na próxima execução; em 503 tenta de
novo.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

AQUI = Path(__file__).resolve().parent
FRONT = AQUI.parent
CATALOGO = FRONT / "src" / "lib" / "falasGravadas.json"
MANIFESTO = FRONT / "src" / "lib" / "falasGravadas.manifesto.json"
PASTA = FRONT / "public" / "voz"
ENV_BACKEND = FRONT.parent / "backend" / ".env"

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
TAXA_HZ = 24000
MP3_KBPS = 48
# Silêncio que sobra nas pontas de cada fala: o tocador junta frases com uma
# pausa própria, então a da gravação não pode somar a ela.
LIMIAR_SILENCIO = 400
MARGEM_S = 0.06


def arquivos_da_fala(fid: str) -> list[Path]:
    """Os MP3 de UMA fala. Casamento exato: `pratica-*` casaria também os de
    `pratica-dirigida` e apagaria a fala vizinha."""
    import re

    molde = re.compile(rf"{re.escape(fid)}-[0-9a-f]{{10}}\.mp3")
    return [p for p in PASTA.glob("*.mp3") if molde.fullmatch(p.name)]


def hash_da_fala(voz: str, modelo: str, estilo: str, texto: str) -> str:
    """Mesma conta de `hashDaFala` em `vozDaMentis.test.js`."""
    return hashlib.sha256("||".join((voz, modelo, estilo, texto)).encode("utf-8")).hexdigest()[:10]


def aparar(pcm: bytes) -> bytes:
    n = len(pcm) // 2
    amostras = struct.unpack(f"<{n}h", pcm[: n * 2])
    margem = int(TAXA_HZ * MARGEM_S)
    ini = next((i for i, a in enumerate(amostras) if abs(a) > LIMIAR_SILENCIO), 0)
    fim = next((i for i in range(n - 1, -1, -1) if abs(amostras[i]) > LIMIAR_SILENCIO), n - 1)
    ini, fim = max(0, ini - margem), min(n, fim + margem)
    return pcm[ini * 2: fim * 2]


LOTE = 12  # falas por pedido: ~60 s de áudio, longe de qualquer teto de saída
# Ritmo plausível de fala (caracteres por segundo). Um pedaço fora disto é
# sinal de corte no lugar errado — duas frases juntas, ou meia frase.
RITMO_MIN, RITMO_MAX = 5.0, 24.0


def cortar(pcm: bytes, textos: list[str]) -> list[bytes] | None:
    """Corta o áudio de um lote entre as falas. Candidatos: os silêncios
    internos de pelo menos 0,2 s. Entre eles, escolhe os N-1 cujos pedaços
    mais se parecem com o tamanho esperado de cada texto (proporcional ao
    número de letras, com um piso por fala — "Bom dia!" é curto mas não
    instantâneo), preferindo as pausas mais longas, que são as `<long pause>`.
    Devolve None se algum pedaço ainda sair com duração incompatível."""
    import math

    n = len(pcm) // 2
    amostras = struct.unpack(f"<{n}h", pcm[: n * 2])
    quadro = int(TAXA_HZ * 0.02)
    mudo = [max((abs(a) for a in amostras[i:i + quadro]), default=0) <= LIMIAR_SILENCIO
            for i in range(0, n, quadro)]
    q = len(mudo)
    primeiro = next((i for i, m in enumerate(mudo) if not m), 0)
    ultimo = next((i for i in range(q - 1, -1, -1) if not mudo[i]), q - 1)
    cand, ini = [], None  # (meio, comprimento) de cada silêncio interno
    for i in range(primeiro, ultimo + 1):
        if mudo[i] and ini is None:
            ini = i
        elif not mudo[i] and ini is not None:
            if i - ini >= 10:  # 0,2 s
                cand.append(((ini + i) // 2, i - ini))
            ini = None
    k = len(textos) - 1
    if k == 0:
        return [aparar(pcm)]
    if len(cand) < k:
        return None

    pesos = [len(t) + 8 for t in textos]
    total = ultimo - primeiro
    esperado = [total * w / sum(pesos) for w in pesos]

    def custo(seg: float, exp: float) -> float:
        return ((seg - exp) / exp) ** 2

    # f[j][c]: melhor custo com a j-ésima divisa no candidato c.
    INF = float("inf")
    f = [[INF] * len(cand) for _ in range(k)]
    de = [[-1] * len(cand) for _ in range(k)]
    for c, (meio, comp) in enumerate(cand):
        f[0][c] = custo(meio - primeiro, esperado[0]) - 0.15 * math.log(comp)
    for j in range(1, k):
        for c, (meio, comp) in enumerate(cand):
            for b in range(c):
                if f[j - 1][b] == INF:
                    continue
                v = f[j - 1][b] + custo(meio - cand[b][0], esperado[j]) - 0.15 * math.log(comp)
                if v < f[j][c]:
                    f[j][c], de[j][c] = v, b
    melhor, c = INF, -1
    for cc, (meio, _) in enumerate(cand):
        if f[k - 1][cc] == INF:
            continue
        v = f[k - 1][cc] + custo(ultimo - meio, esperado[k])
        if v < melhor:
            melhor, c = v, cc
    if c < 0:
        return None
    escolhidos = []
    for j in range(k - 1, -1, -1):
        escolhidos.append(cand[c][0])
        c = de[j][c]
    escolhidos.reverse()

    limites = [0] + [m * quadro for m in escolhidos] + [n]
    partes = [aparar(pcm[limites[i] * 2: limites[i + 1] * 2]) for i in range(len(textos))]
    for parte, texto in zip(partes, textos):
        segundos = len(parte) / (2 * TAXA_HZ)
        ritmo = len(texto) / segundos if segundos else 0
        if not RITMO_MIN <= ritmo <= RITMO_MAX:
            print(f"   ritmo {ritmo:.1f} car/s em «{texto}» ({segundos:.1f}s)")
            return None
    return partes


def para_mp3(pcm: bytes) -> bytes:
    import lameenc

    enc = lameenc.Encoder()
    enc.set_bit_rate(MP3_KBPS)
    enc.set_in_sample_rate(TAXA_HZ)
    enc.set_channels(1)
    enc.set_quality(2)
    return bytes(enc.encode(pcm) + enc.flush())


class CotaDoDia(RuntimeError):
    pass


def sintetizar(chave: str, modelo: str, voz: str, estilo: str, texto: str) -> bytes:
    corpo = {
        "model": modelo,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": texto,
            "annotations": [{"type": "speech_metadata", "style": estilo}],
        }]}],
        "response_format": {"type": "audio", "mime_type": "audio/l16", "sample_rate": TAXA_HZ},
        "generation_config": {"speech_config": [{"voice": voz}]},
    }
    for tentativa in range(6):
        r = httpx.post(URL, json=corpo, headers={"x-goog-api-key": chave}, timeout=90)
        if r.status_code == 200:
            dados = [c["data"] for passo in r.json().get("steps", []) for c in passo.get("content", []) if c.get("data")]
            if not dados:
                raise RuntimeError("resposta sem áudio")
            return base64.b64decode(dados[0])
        if r.status_code == 429:
            raise CotaDoDia(r.text[:300])
        if r.status_code >= 500:
            espera = 5 * (tentativa + 1)
            print(f"   {r.status_code}, de novo em {espera}s")
            time.sleep(espera)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    raise RuntimeError("o modelo seguiu fora do ar")


def main() -> int:
    chave = os.environ.get("GEMINI_API_KEY") or dotenv_values(ENV_BACKEND).get("GEMINI_API_KEY")
    if not chave:
        print("GEMINI_API_KEY ausente (nem no ambiente, nem em aluno/backend/.env)")
        return 1
    cat = json.loads(CATALOGO.read_text("utf-8"))
    manifesto = json.loads(MANIFESTO.read_text("utf-8")) if MANIFESTO.exists() else {}
    PASTA.mkdir(parents=True, exist_ok=True)

    pendentes: dict[str, list[tuple[str, str, str]]] = {}
    for fid, fala in cat["falas"].items():
        estilo = cat["estilos"][fala["tom"]]
        h = hash_da_fala(cat["voz"], cat["modelo"], estilo, fala["texto"])
        if manifesto.get(fid) == h and (PASTA / f"{fid}-{h}.mp3").exists():
            continue
        pendentes.setdefault(fala["tom"], []).append((fid, fala["texto"], h))

    gravadas = 0
    try:
        for tom, itens in pendentes.items():
            estilo = cat["estilos"][tom]
            for i in range(0, len(itens), LOTE):
                lote = itens[i:i + LOTE]
                print(f"lote '{tom}': {', '.join(f for f, _, _ in lote)}")
                pcm = sintetizar(chave, cat["modelo"], cat["voz"], estilo,
                                 " <long pause> ".join(t for _, t, _ in lote))
                partes = cortar(pcm, [t for _, t, _ in lote])
                if partes is None:
                    print("   o corte não bateu com os textos — lote descartado")
                    continue
                for (fid, texto, h), parte in zip(lote, partes):
                    arquivo = PASTA / f"{fid}-{h}.mp3"
                    arquivo.write_bytes(para_mp3(parte))
                    for velho in arquivos_da_fala(fid):
                        if velho != arquivo:
                            velho.unlink()
                    manifesto[fid] = h
                    gravadas += 1
                    print(f"   {fid}: {len(parte) / (2 * TAXA_HZ):.1f}s, {arquivo.stat().st_size // 1024} KB")
    except CotaDoDia as exc:
        print(f"cota grátis do dia acabou — rode de novo amanhã. ({exc})")
    finally:
        # Fala que saiu do catálogo sai também do manifesto e da pasta.
        for fid in [f for f in manifesto if f not in cat["falas"]]:
            manifesto.pop(fid)
            for velho in arquivos_da_fala(fid):
                velho.unlink()
        MANIFESTO.write_text(json.dumps(dict(sorted(manifesto.items())), indent=2, ensure_ascii=False) + "\n", "utf-8")

    faltam = [f for f, fala in cat["falas"].items()
              if manifesto.get(f) != hash_da_fala(cat["voz"], cat["modelo"], cat["estilos"][fala["tom"]], fala["texto"])]
    print(f"{gravadas} gravada(s) agora; faltam {len(faltam)}{': ' + ', '.join(faltam) if faltam else ''}")
    return 0 if not faltam else 2


def conferir() -> int:
    """`--conferir`: transcreve cada MP3 do catálogo (um pedido só, num modelo
    de texto com cota própria) e compara com o texto esperado. É a prova de
    que o corte dos lotes pôs cada frase no arquivo certo — quem grava não
    consegue ouvir 24 arquivos a cada mudança."""
    import re
    import unicodedata

    chave = os.environ.get("GEMINI_API_KEY") or dotenv_values(ENV_BACKEND).get("GEMINI_API_KEY")
    cat = json.loads(CATALOGO.read_text("utf-8"))
    manifesto = json.loads(MANIFESTO.read_text("utf-8"))
    ids = [f for f in cat["falas"] if f in manifesto]
    partes = []
    for i, fid in enumerate(ids, 1):
        mp3 = (PASTA / f"{fid}-{manifesto[fid]}.mp3").read_bytes()
        partes.append({"text": f"[a{i}]"})
        partes.append({"inline_data": {"mime_type": "audio/mpeg", "data": base64.b64encode(mp3).decode()}})
    partes.append({"text": (
        f"São {len(ids)} arquivos de áudio INDEPENDENTES, cada um precedido do seu rótulo [a1]…[a{len(ids)}]. "
        "Transcreva literalmente cada um, em português, sem juntar nem dividir arquivos. "
        'Responda só com JSON: um objeto {"a1": "...", "a2": "...", ...} com exatamente uma chave por arquivo.'
    )})
    corpo = {"contents": [{"role": "user", "parts": partes}],
             "generationConfig": {"responseMimeType": "application/json"}}
    r = httpx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent",
                   json=corpo, headers={"x-goog-api-key": chave}, timeout=180)
    r.raise_for_status()
    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    por_rotulo = json.loads(texto)
    ouvidas = [por_rotulo.get(f"a{i}", "") for i in range(1, len(ids) + 1)]

    def norm(t: str) -> str:
        t = unicodedata.normalize("NFKD", t.lower())
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", t)).strip()

    # A fala é dita, não lida: "tá", "pra" e "descansa" no lugar de "está",
    # "para" e "descanse" são a voz soando natural, não corte errado. Corte
    # errado aparece como frase de OUTRA fala — similaridade lá embaixo.
    from difflib import SequenceMatcher

    erros = 0
    for fid, ouvida in zip(ids, ouvidas):
        esperado = cat["falas"][fid]["texto"]
        ok = SequenceMatcher(None, norm(ouvida), norm(esperado)).ratio() >= 0.8
        erros += not ok
        print(f"{'ok ' if ok else 'DIF'} {fid}: {ouvida}" + ("" if ok else f"   (esperado: {esperado})"))
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(conferir() if "--conferir" in sys.argv else main())
