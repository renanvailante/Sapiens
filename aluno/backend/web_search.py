"""Busca web pública — a fonte de URLs REAIS do Pesquisador IA de Aquisição.

**Por que este módulo existe (achado de 2026-09-21).** A descoberta de leads
era feita com `ai_service.generate_grounded_json`, isto é, o Gemini com
`tools=[google_search]`. Medido contra a API real, **com a chave de produção,
de dentro do container do Fly**: toda chamada com essa tool responde
`429 RESOURCE_EXHAUSTED`, em 100% das tentativas, em `gemini-3-flash-preview`,
`gemini-3.5-flash`, `gemini-3.6-flash` e `gemini-flash-latest`. A mesma chave,
no mesmo instante, responde normalmente SEM a tool. Ou seja: a quota de
*grounding* desta chave é zero (é um recurso de tier pago), e nenhuma troca de
modelo, retry ou timeout conserta isso — é billing, não código.

O efeito era pior que a falha: `descobrir_leads` capturava a exceção num
`except Exception` e devolvia `[], 0`, e a rodada reportava
`"0/40 leads novos encontrados (fontes públicas verificáveis não renderam
mais candidatos válidos)"`. O sistema **atribuía a uma ausência de resultados
o que era uma falha de infraestrutura**. Nunca deixe uma falha de fonte
parecer um resultado vazio — ver `RodadaBusca.estado`, que sobe até o resumo
da rodada.

**O que este módulo faz.** Busca web pública, sem chave, sem login, sem
cookie, sem scraping de conta privada: só o que um motor de busca já publica
para qualquer visitante. Devolve URL + título + trecho, exatamente como o
motor entregou. Nada aqui é escrito por IA — é daqui que sai a garantia de
que uma URL existe, e é por isso que `acquisition_research` só aceita
candidato cuja URL veio deste módulo.

**O que foi MEDIDO de dentro do Fly em 2026-09-21, não suposto.** Busca web
gratuita a partir de IP de datacenter é hostil, e cada número abaixo veio de
uma execução real no container de produção:

| fonte | resultado |
|---|---|
| `html.duckduckgo.com/html/` | 200 com resultados em **2 de 12** consultas; as outras 10 voltaram `202` com captcha ("select all squares containing a duck") |
| `lite.duckduckgo.com/lite/` | mesmo captcha (mesmo backend) |
| `bing.com/search?format=RSS` | funciona, mas `bing.com/robots.txt` traz `Disallow: /search` — **não usamos**, decisão de conformidade, não de capacidade |
| `bing.com/news/search?format=RSS` | funciona, robots PERMITE (`/news/search` não casa com `/search`), e entrega a URL real do artigo |
| `yep.com` 403 · `ecosia` 403 · `brave` 429 · `stract` 404 · `4get` 401 · instâncias SearXNG 429/HTML | inutilizáveis |
| `api.mwmbl.org`, `api.marginalia.nu` | respondem, mas o índice é anglófono e de nicho — irrelevante para criadores brasileiros |
| YouTube Data API e Custom Search com a `GEMINI_API_KEY` | `401 "API keys are not supported by this API"` — a chave do AI Studio não vale fora da Gemini API |

**Daí as três capacidades deste módulo, e não uma só.** Nenhuma fonte
gratuita sozinha sustenta uma rodada; a feature só é confiável se a falha de
uma não zerar as outras:

1. `buscar()` — busca web genérica (`site:instagram.com ...`). Provedores em
   ordem: Google CSE (oficial, 100 consultas/dia grátis, entra sozinho quando
   `GOOGLE_CSE_KEY`+`GOOGLE_CSE_CX` existem) e DuckDuckGo HTML (melhor-esforço,
   com backoff — o captcha é intermitente, não permanente).
2. `buscar_artigos()` — Bing News RSS, que devolve páginas públicas reais
   (exatamente os artigos do tipo "20 perfis do Instagram para estudar para o
   ENEM").
3. `extrair_perfis_de_pagina()` — lê uma página pública, respeitando o
   robots.txt dela, e extrai os perfis que ela LINKA. A proveniência aqui é a
   mais forte das três: o perfil existe porque uma página pública, nomeável e
   datada, aponta para ele.

`html.duckduckgo.com/robots.txt` traz `User-agent: * / Allow: /` (lido em
2026-09-21) — e, ainda assim, `_robots_permite` relê e aplica o robots em
runtime, porque uma regra que só existe num comentário não é uma regra. Não
confundir com `duckduckgo.com/robots.txt`, que proíbe `/html` e `/lite` NO
DOMÍNIO PRINCIPAL; `html.duckduckgo.com` é outro host, com robots próprio e
permissivo.

**Custo.** Zero por consulta em dinheiro; o custo real é tempo e educação com
o servidor do outro. Daí as três defesas: cache persistente
(`db.web_search_cache`, TTL de `_CACHE_HORAS`), intervalo mínimo entre
requisições ao mesmo provedor (`_INTERVALO_MINIMO_SEGUNDOS`, serializado por
lock) e teto de resultados por consulta. Uma rodada repetida dentro do TTL
não toca a rede nenhuma vez.
"""
from __future__ import annotations

import asyncio
import hashlib
import html as html_mod
import logging
import os
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

import httpx

logger = logging.getLogger("sapiens.web_search")

PROVEDOR_DDG = "duckduckgo_html"
PROVEDOR_CSE = "google_cse"

# User-Agent de navegador real: o endpoint HTML do DuckDuckGo devolve página
# vazia para User-Agent de script. Isto não é evasão de bloqueio — o robots
# do host permite o caminho e é relido em runtime; é só o formato que o
# renderizador do lado de lá espera.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_TIMEOUT_SEGUNDOS = float(os.environ.get("WEB_SEARCH_TIMEOUT", "20") or 20)
_INTERVALO_MINIMO_SEGUNDOS = float(os.environ.get("WEB_SEARCH_INTERVALO", "2.0") or 2.0)
_CACHE_HORAS = float(os.environ.get("WEB_SEARCH_CACHE_HORAS", "72") or 72)
_LIMITE_PADRAO = 20
_MAX_SNIPPET = 400

COLECAO_CACHE = "web_search_cache"


@dataclass
class ResultadoBusca:
    """Um resultado como o MOTOR o entregou. Nenhum campo aqui é escrito por
    IA — é o registro de proveniência que torna o lead verificável."""

    url: str
    titulo: str
    snippet: str
    provedor: str
    consulta: str
    buscado_em: str

    def como_dict(self) -> dict[str, Any]:
        return {
            "url": self.url, "titulo": self.titulo, "snippet": self.snippet,
            "provedor": self.provedor, "consulta": self.consulta, "buscado_em": self.buscado_em,
        }

    @classmethod
    def de_dict(cls, d: dict[str, Any]) -> "ResultadoBusca":
        return cls(
            url=d.get("url", ""), titulo=d.get("titulo", ""), snippet=d.get("snippet", ""),
            provedor=d.get("provedor", ""), consulta=d.get("consulta", ""),
            buscado_em=d.get("buscado_em", ""),
        )


@dataclass
class RodadaBusca:
    """O resultado de UMA consulta, com o porquê quando não há resultado.

    `estado` existe para que o chamador nunca precise adivinhar a diferença
    entre "a busca funcionou e não achou nada" (`vazio`) e "a busca não
    aconteceu" (`erro`/`bloqueado_robots`) — a confusão exata que derrubou o
    Pesquisador original."""

    consulta: str
    resultados: list[ResultadoBusca] = field(default_factory=list)
    provedor: str | None = None
    estado: str = "ok"            # ok | cache | vazio | erro | bloqueado_robots
    erro: str | None = None
    tentativas: list[dict[str, str]] = field(default_factory=list)  # por provedor: o que houve


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chave_cache(provedor: str, consulta: str, limite: int) -> str:
    bruto = f"{provedor}|{consulta.strip().lower()}|{limite}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:32]


# --------------------------------------------------------------- robots.txt
#
# Cache em memória por host (24 h). Um fetch de robots por host por dia é
# barato; reler a cada consulta seria dobrar o tráfego que estamos tentando
# manter educado.

_ROBOTS_CACHE: dict[str, tuple[float, Any]] = {}
_ROBOTS_TTL_SEGUNDOS = 24 * 3600


async def _robots_permite(url: str) -> bool:
    """Aplica o robots.txt do host em runtime. Falha ao BUSCAR o robots não
    bloqueia (é o comportamento padrão da web: ausência de robots = permitido);
    uma regra explícita de `Disallow` bloqueia."""
    from urllib.robotparser import RobotFileParser

    partes = urllib.parse.urlparse(url)
    host = f"{partes.scheme}://{partes.netloc}"
    agora = time.monotonic()
    em_cache = _ROBOTS_CACHE.get(host)
    if em_cache and (agora - em_cache[0]) < _ROBOTS_TTL_SEGUNDOS:
        parser = em_cache[1]
    else:
        parser = RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as cliente:
                resp = await cliente.get(f"{host}/robots.txt", headers={"User-Agent": _USER_AGENT})
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
            else:
                parser.allow_all = True
        except Exception:  # noqa: BLE001
            logger.warning("robots.txt de %s não pôde ser lido; seguindo como permitido.", host)
            parser.allow_all = True
        _ROBOTS_CACHE[host] = (agora, parser)
    try:
        return bool(parser.can_fetch(_USER_AGENT, url))
    except Exception:  # noqa: BLE001
        return True


# ------------------------------------------------- rate limit por provedor
#
# Serializa as requisições de um provedor e garante um intervalo mínimo entre
# elas. O lock é por PROCESSO (o backend do aluno roda numa máquina); não é um
# rate limit distribuído e não pretende ser.

_LOCKS: dict[str, asyncio.Lock] = {}
_ULTIMA_REQUISICAO: dict[str, float] = {}


def _lock_de(provedor: str) -> asyncio.Lock:
    if provedor not in _LOCKS:
        _LOCKS[provedor] = asyncio.Lock()
    return _LOCKS[provedor]


# ------------------------------------------------------- circuit breaker
#
# Quando o DuckDuckGo bane o IP do Fly, ele bane por um tempo: TODA consulta
# seguinte falha. Sem isto, cada uma ainda paga 3 tentativas mais backoff de
# 4 s e 8 s — uma rodada de 9 nichos gastava minutos só para colecionar o
# mesmo erro. Depois de `_FALHAS_ATE_PAUSAR` falhas seguidas o provedor é
# pausado, e a rodada segue direto para as outras fontes. Um sucesso zera.

_FALHAS_ATE_PAUSAR = int(os.environ.get("WEB_SEARCH_FALHAS_ATE_PAUSAR", "3") or 3)
_PAUSA_SEGUNDOS = float(os.environ.get("WEB_SEARCH_PAUSA", "900") or 900)
_FALHAS: dict[str, int] = {}
_PAUSADO_ATE: dict[str, float] = {}


def _esta_pausado(provedor: str) -> float:
    """Segundos restantes de pausa, ou 0 quando o provedor está liberado."""
    ate = _PAUSADO_ATE.get(provedor, 0.0)
    return max(0.0, ate - time.monotonic())


def _marcar_falha(provedor: str) -> None:
    _FALHAS[provedor] = _FALHAS.get(provedor, 0) + 1
    if _FALHAS[provedor] >= _FALHAS_ATE_PAUSAR:
        _PAUSADO_ATE[provedor] = time.monotonic() + _PAUSA_SEGUNDOS
        logger.warning(
            "Busca web: provedor=%s pausado por %.0fs após %d falhas seguidas.",
            provedor, _PAUSA_SEGUNDOS, _FALHAS[provedor],
        )


def _marcar_sucesso(provedor: str) -> None:
    _FALHAS.pop(provedor, None)
    _PAUSADO_ATE.pop(provedor, None)


async def _esperar_vez(provedor: str) -> None:
    ultima = _ULTIMA_REQUISICAO.get(provedor)
    if ultima is not None:
        falta = _INTERVALO_MINIMO_SEGUNDOS - (time.monotonic() - ultima)
        if falta > 0:
            await asyncio.sleep(falta)
    _ULTIMA_REQUISICAO[provedor] = time.monotonic()


# ------------------------------------------------------- provedor: DuckDuckGo

_RE_BLOCO = re.compile(r'<div class="result[ "][^>]*>', re.I)
_RE_LINK = re.compile(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
_RE_SNIPPET = re.compile(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.I | re.S)
_RE_TAG = re.compile(r"<[^>]+>")


def _texto(bruto: str) -> str:
    return " ".join(html_mod.unescape(_RE_TAG.sub(" ", bruto or "")).split())


def _resolver_redirecionamento(href: str) -> str:
    """O DuckDuckGo às vezes embrulha o link em `//duckduckgo.com/l/?uddg=...`.
    A URL final está no parâmetro — é ela que vale como fonte."""
    if href.startswith("//"):
        href = "https:" + href
    partes = urllib.parse.urlparse(href)
    if partes.netloc.endswith("duckduckgo.com") and partes.path.startswith("/l/"):
        alvo = urllib.parse.parse_qs(partes.query).get("uddg")
        if alvo:
            return alvo[0]
    return href


def _eh_anuncio(href: str) -> bool:
    return "duckduckgo.com/y.js" in href or "ad_provider=" in href


_DDG_TENTATIVAS = int(os.environ.get("WEB_SEARCH_DDG_TENTATIVAS", "3") or 3)
_DDG_BACKOFF_BASE = float(os.environ.get("WEB_SEARCH_DDG_BACKOFF", "4") or 4)

_CABECALHOS_NAVEGADOR = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Referer": "https://html.duckduckgo.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
}


class BloqueadoPelaFonte(RuntimeError):
    """A fonte recusou a requisição (captcha/anomalia). É o oposto de "não
    achei nada": a busca não aconteceu. Tem nome próprio para que
    `RodadaBusca.estado` possa dizer isso ao admin em vez de reportar zero."""


async def _buscar_ddg(consulta: str, limite: int) -> list[ResultadoBusca]:
    """O captcha do DuckDuckGo para IP de datacenter é INTERMITENTE (medido:
    2 de 12 consultas passaram numa rajada). Um retry com backoff converte
    parte das recusas em resultado; o que não converter vira
    `BloqueadoPelaFonte`, nunca lista vazia."""
    endpoint = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": consulta, "kl": "br-pt"})
    if not await _robots_permite(endpoint):
        raise PermissionError("robots.txt do DuckDuckGo não permite este caminho.")

    corpo = ""
    for tentativa in range(_DDG_TENTATIVAS):
        async with httpx.AsyncClient(timeout=_TIMEOUT_SEGUNDOS, follow_redirects=True) as cliente:
            resp = await cliente.get(endpoint, headers=_CABECALHOS_NAVEGADOR)
        resp.raise_for_status()
        corpo = resp.text
        if "result__a" in corpo:
            break
        if not re.search(r"anomaly|captcha|challenge|unusual traffic", corpo, re.I):
            return []  # resposta legítima sem resultado para esta consulta
        if tentativa < _DDG_TENTATIVAS - 1:
            await asyncio.sleep(_DDG_BACKOFF_BASE * (tentativa + 1))
    else:
        raise BloqueadoPelaFonte(
            f"DuckDuckGo respondeu com verificação anti-bot em {_DDG_TENTATIVAS} tentativas."
        )

    blocos = _RE_BLOCO.split(corpo)
    agora = _agora_iso()
    saida: list[ResultadoBusca] = []
    vistos: set[str] = set()
    for bloco in blocos:
        link = _RE_LINK.search(bloco)
        if not link:
            continue
        href, titulo_bruto = link.group(1), link.group(2)
        if _eh_anuncio(href):
            continue
        url = _resolver_redirecionamento(html_mod.unescape(href))
        if not url.startswith("http") or url in vistos:
            continue
        vistos.add(url)
        snip = _RE_SNIPPET.search(bloco)
        saida.append(ResultadoBusca(
            url=url,
            titulo=_texto(titulo_bruto)[:300],
            snippet=_texto(snip.group(1) if snip else "")[:_MAX_SNIPPET],
            provedor=PROVEDOR_DDG,
            consulta=consulta,
            buscado_em=agora,
        ))
        if len(saida) >= limite:
            break
    return saida


# --------------------------------------------- provedor: Google Custom Search
#
# API oficial, 100 consultas/dia no free tier, sem cartão. Fica inativo
# enquanto as variáveis não existirem — nada quebra por não configurá-lo, e
# configurá-lo passa a ser a fonte primária (melhor cobertura que o HTML do
# DuckDuckGo, e termos de uso explícitos em vez de inferidos de robots).

def _cse_configurado() -> bool:
    return bool(os.environ.get("GOOGLE_CSE_KEY") and os.environ.get("GOOGLE_CSE_CX"))


async def _buscar_cse(consulta: str, limite: int) -> list[ResultadoBusca]:
    chave, cx = os.environ["GOOGLE_CSE_KEY"], os.environ["GOOGLE_CSE_CX"]
    agora = _agora_iso()
    saida: list[ResultadoBusca] = []
    # A API devolve no máximo 10 por página; paginamos só o necessário.
    for inicio in range(1, min(limite, 30) + 1, 10):
        async with httpx.AsyncClient(timeout=_TIMEOUT_SEGUNDOS) as cliente:
            resp = await cliente.get("https://www.googleapis.com/customsearch/v1", params={
                "key": chave, "cx": cx, "q": consulta, "num": 10, "start": inicio, "hl": "pt-BR",
            })
        resp.raise_for_status()
        itens = (resp.json() or {}).get("items") or []
        for item in itens:
            url = item.get("link") or ""
            if not url.startswith("http"):
                continue
            saida.append(ResultadoBusca(
                url=url,
                titulo=(item.get("title") or "")[:300],
                snippet=(item.get("snippet") or "")[:_MAX_SNIPPET],
                provedor=PROVEDOR_CSE, consulta=consulta, buscado_em=agora,
            ))
            if len(saida) >= limite:
                return saida
        if len(itens) < 10:
            break
    return saida


Provedor = Callable[[str, int], Awaitable[list[ResultadoBusca]]]


def provedores_ativos() -> list[tuple[str, Provedor]]:
    """Ordem de tentativa. O CSE, quando configurado, vem primeiro: é API
    oficial com termos explícitos."""
    ativos: list[tuple[str, Provedor]] = []
    if _cse_configurado():
        ativos.append((PROVEDOR_CSE, _buscar_cse))
    ativos.append((PROVEDOR_DDG, _buscar_ddg))
    return ativos


# ---------------------------------------------------------------- cache + API

async def _ler_cache(db, chave: str, max_idade_horas: float) -> list[ResultadoBusca] | None:
    if db is None:
        return None
    try:
        doc = await db[COLECAO_CACHE].find_one({"_id": chave})
    except Exception:  # noqa: BLE001
        logger.exception("Cache de busca: leitura falhou (seguindo sem cache).")
        return None
    if not doc:
        return None
    try:
        gravado = datetime.fromisoformat(doc.get("buscado_em", ""))
    except ValueError:
        return None
    if gravado.tzinfo is None:
        gravado = gravado.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - gravado > timedelta(hours=max_idade_horas):
        return None
    return [ResultadoBusca.de_dict(r) for r in (doc.get("resultados") or [])]


async def _gravar_cache(db, chave: str, consulta: str, provedor: str,
                        resultados: list[ResultadoBusca]) -> None:
    if db is None:
        return
    try:
        await db[COLECAO_CACHE].update_one(
            {"_id": chave},
            {"$set": {
                "consulta": consulta, "provedor": provedor, "buscado_em": _agora_iso(),
                "resultados": [r.como_dict() for r in resultados],
            }},
            upsert=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Cache de busca: gravação falhou (resultado ainda é válido).")


async def buscar(db, consulta: str, *, limite: int = _LIMITE_PADRAO,
                 max_idade_horas: float | None = None) -> RodadaBusca:
    """Uma consulta pública. NUNCA levanta: devolve `RodadaBusca` com
    `estado` explicando o que houve, para que a falha de uma consulta não
    derrube a rodada inteira do chamador."""
    consulta = (consulta or "").strip()
    rodada = RodadaBusca(consulta=consulta)
    if not consulta:
        rodada.estado = "vazio"
        return rodada

    idade = _CACHE_HORAS if max_idade_horas is None else max_idade_horas
    for nome, funcao in provedores_ativos():
        chave = _chave_cache(nome, consulta, limite)
        em_cache = await _ler_cache(db, chave, idade)
        if em_cache is not None:
            rodada.resultados, rodada.provedor = em_cache, nome
            rodada.estado = "cache" if em_cache else "vazio"
            rodada.tentativas.append({"provedor": nome, "resultado": f"cache ({len(em_cache)})"})
            return rodada

        pausa = _esta_pausado(nome)
        if pausa:
            rodada.tentativas.append({
                "provedor": nome,
                "resultado": f"pausado após falhas seguidas (volta em {pausa:.0f}s)",
            })
            continue

        try:
            async with _lock_de(nome):
                await _esperar_vez(nome)
                resultados = await funcao(consulta, limite)
        except PermissionError as exc:
            rodada.tentativas.append({"provedor": nome, "resultado": f"robots: {exc}"})
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("Busca web: provedor=%s consulta=%r falhou: %s", nome, consulta, exc)
            _marcar_falha(nome)
            rodada.tentativas.append({"provedor": nome, "resultado": f"{type(exc).__name__}: {exc}"[:200]})
            continue

        _marcar_sucesso(nome)
        await _gravar_cache(db, chave, consulta, nome, resultados)
        rodada.resultados, rodada.provedor = resultados, nome
        rodada.estado = "ok" if resultados else "vazio"
        rodada.tentativas.append({"provedor": nome, "resultado": f"ok ({len(resultados)})"})
        return rodada

    rodada.estado = "erro"
    rodada.erro = "; ".join(f"{t['provedor']}: {t['resultado']}" for t in rodada.tentativas) or "nenhum provedor ativo"
    return rodada


# ------------------------------------------------- artigos (Bing News RSS)
#
# Por que notícia serve para descobrir influenciador: a imprensa educacional
# brasileira publica, todo ano, exatamente o artigo de que a prospecção
# precisa — "20 perfis do Instagram que ajudam na revisão do ENEM". Cada um
# desses artigos é uma página pública, datada e nomeável que LINKA dezenas de
# perfis reais. É a fonte de proveniência mais forte das três, e a única que
# não depende de um motor de busca aceitar nosso IP.
#
# `bing.com/news/search` é permitido pelo robots do Bing (verificado com
# `RobotFileParser`, não a olho: `Disallow: /search` não casa com
# `/news/search`), e o `<link>` do feed carrega a URL real do artigo no
# parâmetro `url=` — diferente do Google News RSS, cujo link é um token
# opaco que só o JavaScript da página resolve.

PROVEDOR_BING_NEWS = "bing_news_rss"
_RE_ITEM = re.compile(r"<item>(.*?)</item>", re.S | re.I)
_RE_TITULO_XML = re.compile(r"<title>(.*?)</title>", re.S | re.I)
_RE_DESC_XML = re.compile(r"<description>(.*?)</description>", re.S | re.I)
_RE_LINK_XML = re.compile(r"<link>(.*?)</link>", re.S | re.I)


def _url_real_do_bing(link: str) -> str | None:
    link = html_mod.unescape((link or "").strip())
    if "bing.com" not in link:
        return link if link.startswith("http") else None
    alvo = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("url")
    return alvo[0] if alvo else None


async def _buscar_bing_news(consulta: str, limite: int) -> list[ResultadoBusca]:
    endpoint = "https://www.bing.com/news/search?" + urllib.parse.urlencode(
        {"q": consulta, "format": "RSS", "cc": "br", "setlang": "pt-br"}
    )
    if not await _robots_permite(endpoint):
        raise PermissionError("robots.txt do Bing não permite /news/search.")

    async with httpx.AsyncClient(timeout=_TIMEOUT_SEGUNDOS, follow_redirects=True) as cliente:
        resp = await cliente.get(endpoint, headers={"User-Agent": _USER_AGENT,
                                                    "Accept-Language": "pt-BR,pt;q=0.9"})
    resp.raise_for_status()
    agora = _agora_iso()
    saida: list[ResultadoBusca] = []
    vistos: set[str] = set()
    for item in _RE_ITEM.findall(resp.text):
        link = _RE_LINK_XML.search(item)
        url = _url_real_do_bing(link.group(1)) if link else None
        if not url or url in vistos:
            continue
        vistos.add(url)
        titulo = _RE_TITULO_XML.search(item)
        desc = _RE_DESC_XML.search(item)
        saida.append(ResultadoBusca(
            url=url,
            titulo=_texto(titulo.group(1) if titulo else "")[:300],
            snippet=_texto(desc.group(1) if desc else "")[:_MAX_SNIPPET],
            provedor=PROVEDOR_BING_NEWS, consulta=consulta, buscado_em=agora,
        ))
        if len(saida) >= limite:
            break
    return saida


async def buscar_artigos(db, consulta: str, *, limite: int = _LIMITE_PADRAO,
                         max_idade_horas: float | None = None) -> RodadaBusca:
    """Páginas públicas (artigos) sobre um tema. Mesma disciplina de `buscar`:
    nunca levanta, sempre explica."""
    consulta = (consulta or "").strip()
    rodada = RodadaBusca(consulta=consulta)
    if not consulta:
        rodada.estado = "vazio"
        return rodada

    idade = _CACHE_HORAS if max_idade_horas is None else max_idade_horas
    chave = _chave_cache(PROVEDOR_BING_NEWS, consulta, limite)
    em_cache = await _ler_cache(db, chave, idade)
    if em_cache is not None:
        rodada.resultados, rodada.provedor = em_cache, PROVEDOR_BING_NEWS
        rodada.estado = "cache" if em_cache else "vazio"
        return rodada

    pausa = _esta_pausado(PROVEDOR_BING_NEWS)
    if pausa:
        rodada.estado = "erro"
        rodada.erro = f"pausado após falhas seguidas (volta em {pausa:.0f}s)"
        rodada.tentativas.append({"provedor": PROVEDOR_BING_NEWS, "resultado": rodada.erro})
        return rodada

    try:
        async with _lock_de(PROVEDOR_BING_NEWS):
            await _esperar_vez(PROVEDOR_BING_NEWS)
            resultados = await _buscar_bing_news(consulta, limite)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Busca de artigos: consulta=%r falhou: %s", consulta, exc)
        _marcar_falha(PROVEDOR_BING_NEWS)
        rodada.estado = "erro"
        rodada.erro = f"{type(exc).__name__}: {exc}"[:200]
        rodada.tentativas.append({"provedor": PROVEDOR_BING_NEWS, "resultado": rodada.erro})
        return rodada

    _marcar_sucesso(PROVEDOR_BING_NEWS)
    await _gravar_cache(db, chave, consulta, PROVEDOR_BING_NEWS, resultados)
    rodada.resultados, rodada.provedor = resultados, PROVEDOR_BING_NEWS
    rodada.estado = "ok" if resultados else "vazio"
    return rodada


# ------------------------------------------- perfis linkados numa página
#
# Extração DETERMINÍSTICA: só o que a página literalmente linka. Nenhuma IA
# participa desta etapa — é aqui que nasce a garantia "esta URL existe e
# alguém público apontou para ela".

# O lookahead de delimitador é obrigatório nos TRÊS: sem ele, o handle é
# cortado no primeiro caractere fora da classe e nasce um perfil que não
# existe. Foi o que aconteceu na primeira medição — `youtube.com/@Estudantes…`
# virou `@Est`, uma URL inventada por acidente de regex. Um perfil truncado é
# exatamente o tipo de dado falso que este módulo existe para impedir.
_DELIMITADOR = r"""(?=["'\s<>)\]?&#/]|$)"""
_RE_PERFIL = {
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{2,30})/?" + _DELIMITADOR, re.I),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/(@[A-Za-z0-9._-]{2,30})/?" + _DELIMITADOR, re.I),
    "tiktok": re.compile(r"https?://(?:www\.)?tiktok\.com/(@[A-Za-z0-9._-]{2,30})/?" + _DELIMITADOR, re.I),
}

# Handles institucionais de veículos e plataformas que aparecem no rodapé de
# quase toda página de notícia. Não são lead de ninguém, e sem esta lista eles
# seriam o resultado MAIS frequente da estratégia de artigos.
_PERFIS_INSTITUCIONAIS = {
    "jornaloglobo", "oglobo", "estadao", "folhadespaulo", "folha", "uol", "g1",
    "portalr7", "r7", "terra", "terragora", "cnnbrasil", "band", "sbtnews",
    "recordtv", "veja", "revistaveja", "istoe", "exame", "metropoles", "uolnoticias",
    "techtudo", "techtudo_oficial", "guiadoestudante", "correiobraziliense",
    "gazetadopovo", "otempo", "hojeemdia", "acritica", "portalacritica", "viva.noticia",
    "opovoonline", "opovo", "diariodonordeste", "jornalnacional", "youtube", "instagram",
    "tiktok", "facebook", "whatsapp", "google", "spotify", "netflix",
}

# Caminhos do próprio site que parecem handle mas não são conta de ninguém.
_NAO_SAO_PERFIS = {
    "p", "reel", "reels", "explore", "accounts", "about", "tv", "stories", "directory",
    "popular", "legal", "developer", "developers", "privacy", "terms", "help", "api",
    "web", "graphql", "oauth", "challenge", "emails", "session", "static", "topics",
    "channel", "watch", "playlist", "results", "feed", "shorts", "embed", "user", "c",
    "tag", "discover", "music", "live", "foryou", "upload", "login", "signup",
}

_MAX_PAGINA_BYTES = 2_000_000

# `instagram.com/embed.js` casa com o padrão de handle e não é conta de
# ninguém. Recurso estático da própria página, nunca perfil.
_RE_ARQUIVO = re.compile(r"\.(js|css|json|png|jpe?g|gif|svg|ico|php|html?|xml|woff2?)$", re.I)


@dataclass
class PerfilNaPagina:
    """Um perfil encontrado numa página pública, com a prova de onde veio.

    `mencionado_no_texto` é o sinal de qualidade que separa lead de ruído, e
    saiu da medição de 2026-09-21: todo perfil que o artigo de fato DISCUTE
    (`@dosesdahistoria`, `@prof.barbaragarbinato`, `@profgabrielcabral`)
    aparece no texto visível da página; todo link institucional de rodapé
    (`jornaloglobo`, `portal_ig`, `tiktokbrasil`) aparece só no HTML. É um
    filtro barato e de precisão alta — e, como tudo aqui, o descarte fica
    registrado com motivo em vez de sumir."""

    plataforma: str
    identificador: str
    url: str
    pagina_url: str
    pagina_titulo: str
    contexto: str          # trecho de texto da página ao redor da menção
    encontrado_em: str
    mencionado_no_texto: bool = False


_SUFIXOS_DE_HOST = {"com", "net", "org", "br", "www", "noticias", "blog", "portal", "amp"}


def _marcas_do_host(host: str) -> set[str]:
    """Rótulos do domínio que servem para reconhecer a conta do próprio
    veículo — `capricho.abril.com.br` → {capricho, abril}."""
    return {r for r in host.split(".") if r and r not in _SUFIXOS_DE_HOST and len(r) > 2}


def _eh_do_proprio_veiculo(handle: str, marcas: set[str]) -> bool:
    """A lista fixa de veículos nunca fica completa — `capricho`,
    `tiktokbrasil` e `jornalextra` escaparam dela numa medição real. Esta
    regra é estrutural: se o handle É um rótulo do domínio da página, ou o
    contém (`jornalextra` em `extra.globo.com`), é a conta institucional de
    quem publicou a página, não um lead."""
    limpo = handle.replace(".", "").replace("_", "").replace("-", "")
    for marca in marcas:
        if marca == limpo or (len(marca) >= 5 and marca in limpo):
            return True
    return False


def _eh_conta_da_plataforma(handle: str) -> bool:
    """`tiktokbrasil`, `instagrambr`, `youtubebrasil` — conta oficial da rede
    social, presente em qualquer matéria que fale dela."""
    limpo = handle.replace(".", "").replace("_", "").replace("-", "")
    return any(limpo.startswith(rede) for rede in ("tiktok", "instagram", "youtube", "facebook", "whatsapp"))


def _contexto_ao_redor(texto_limpo: str, termo: str, janela: int = 220) -> str:
    pos = texto_limpo.lower().find(termo.lower())
    if pos < 0:
        return ""
    inicio = max(0, pos - janela // 2)
    return texto_limpo[inicio:inicio + janela].strip()


async def extrair_perfis_de_pagina(
    url_pagina: str, *, titulo_pagina: str = "", plataformas: tuple[str, ...] = ("instagram", "youtube", "tiktok"),
    ignorar_proprio_host: bool = True,
) -> tuple[list[PerfilNaPagina], str | None]:
    """Lê uma página pública e devolve `(perfis, erro)`. Respeita o robots.txt
    do host da página — uma página que o robots proíbe é PULADA, e o motivo
    volta em `erro` para virar linha de auditoria, não silêncio.

    `ignorar_proprio_host` descarta o perfil institucional do próprio veículo
    (o link do Instagram do jornal no rodapé), que apareceria em toda página
    e não é lead de ninguém."""
    if not await _robots_permite(url_pagina):
        return [], "robots.txt da página não permite leitura automatizada"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SEGUNDOS, follow_redirects=True) as cliente:
            resp = await cliente.get(url_pagina, headers={
                "User-Agent": _USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}: {exc}"[:180]

    corpo = resp.text[:_MAX_PAGINA_BYTES]
    texto_limpo = _texto(corpo)
    host_pagina = urllib.parse.urlparse(str(resp.url)).netloc.lower()
    marcas_do_host = _marcas_do_host(host_pagina)
    agora = _agora_iso()

    achados: list[PerfilNaPagina] = []
    vistos: set[tuple[str, str]] = set()
    for plataforma in plataformas:
        padrao = _RE_PERFIL.get(plataforma)
        if not padrao:
            continue
        for bruto in padrao.findall(corpo):
            handle = bruto.strip()
            nu = handle.lstrip("@").lower()
            if not nu or nu in _NAO_SAO_PERFIS or nu in _PERFIS_INSTITUCIONAIS or nu.isdigit():
                continue
            if _RE_ARQUIVO.search(nu):
                continue  # `embed.js`, `sprite.css` — recurso da página, não perfil
            if ignorar_proprio_host and _eh_do_proprio_veiculo(nu, marcas_do_host):
                continue
            if _eh_conta_da_plataforma(nu):
                continue
            chave = (plataforma, nu)
            if chave in vistos:
                continue
            vistos.add(chave)
            base = {"instagram": "https://www.instagram.com/", "youtube": "https://www.youtube.com/",
                    "tiktok": "https://www.tiktok.com/"}[plataforma]
            contexto = _contexto_ao_redor(texto_limpo, handle.lstrip("@"))
            achados.append(PerfilNaPagina(
                plataforma=plataforma, identificador=handle,
                url=f"{base}{handle}" if plataforma != "instagram" else f"{base}{nu}/",
                pagina_url=str(resp.url), pagina_titulo=titulo_pagina[:300],
                contexto=contexto, encontrado_em=agora,
                mencionado_no_texto=bool(contexto),
            ))
    return achados, None
