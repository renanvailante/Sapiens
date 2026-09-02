"""Sapiens FastAPI application."""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
from pathlib import Path
from collections import Counter
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sapiens")

settings.exigir_config_valida()

import auth as auth_module
from auth import require_user
from models import User
import exam_routes as exam_module
import exam_images_routes as exam_images_module
import feed_routes as feed_module
import annotation_routes as annotation_module
import admin_routes as admin_module
import events_routes as events_module
import firestore_routes as firestore_module
import skills_map_routes as skills_map_module
import aulas_particulares_routes as aulas_particulares_module
import sparks_routes as sparks_module
import redacao_routes as redacao_module
import client_errors_routes as client_errors_module
import db_indexes
from enem_seed import migrate_and_seed
from feed_seed import seed_feed
from firestore_service import seed_all_students as _firestore_seed_students

client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
db = client[settings.DB_NAME]

auth_module.set_db(db)
exam_module.set_db(db)
exam_images_module.set_db(db)
feed_module.set_db(db)
annotation_module.set_db(db)
admin_module.set_db(db)
firestore_module.set_db(db)
aulas_particulares_module.set_db(db)
sparks_module.set_db(db)
redacao_module.set_db(db)
client_errors_module.set_db(db)

app = FastAPI(
    title="Sapiens",
    # Em produção a documentação interativa é superfície gratuita para mapear
    # o serviço; em desenvolvimento é a forma mais rápida de explorá-lo.
    docs_url=None if settings.IS_PRODUCTION else "/docs",
    redoc_url=None if settings.IS_PRODUCTION else "/redoc",
    openapi_url=None if settings.IS_PRODUCTION else "/openapi.json",
)
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "Sapiens", "status": "ok"}


# Projeção obrigatória de toda leitura de `questoes_public` que vai para o
# cliente. `alternativas.$[].correta` é o GABARITO: com ele na resposta, o
# aluno lê a alternativa certa na aba Rede do navegador antes de responder, e
# qualquer pessoa sem login baixa o banco inteiro com as respostas.
#
# Quem decide certo/errado é o servidor, em `POST /students/me/answer`
# (`firestore_routes.register_answer`), que lê a coleção direto e nunca depende
# do que o cliente afirma — então esconder o campo aqui não muda nada no fluxo
# de prática, só fecha o vazamento.
PROJECAO_SEM_GABARITO = {
    "_id": 0,
    "master_id": 0,
    "questao.alternativas.correta": 0,
}


@api_router.get("/questoes")
async def list_questoes_publico(
    limit: int = 100,
    banca: str | None = None,
    ano: int | None = None,
    prova: str | None = None,
    numero_min: int | None = None,
    numero_max: int | None = None,
    area: str | None = None,
    _: User = Depends(require_user),
):
    """Questões para a prática do aluno — **exige sessão** e nunca inclui o
    gabarito (ver `PROJECAO_SEM_GABARITO`).

    Era aberto e devolvia `correta` em cada alternativa: um `curl` sem login
    baixava o banco inteiro com as respostas, e o próprio aluno via o gabarito
    na aba Rede antes de responder. Os enunciados do ENEM são públicos (o INEP
    os publica), mas a anotação e o gabarito consolidados aqui não são, e
    Sparks — moeda comprada com dinheiro — são creditados por acerto.

    Le APENAS a colecao filtrada 'questoes_public' do Mongo (versao sem
    metadados internos). NUNCA le do Firestore nem da colecao master.

    `banca`/`ano`/`prova` restringem a um único caderno (banca+ano+cor).
    `numero_min`/`numero_max`, quando presentes, restringem a UM bloco de até
    45 questões dentro do caderno — uma prova/área real do ENEM (1-45,
    46-90, 91-135, 136-180); um caderno de dia inteiro (90 questões, 2 áreas)
    não é uma prova só. Os mesmos campos agrupam `/api/provas`. `area`
    restringe pela área ENEM canônica (`_AREAS_ENEM`) inferida de
    `fonte.disciplina`, cruzando cadernos — usado pela prática de lacuna
    recomendada no painel (uma área fraca, não um caderno específico). Sem
    nenhum filtro, devolve tudo (comportamento anterior, preservado).
    """
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 100
    filtro: dict = {}
    if banca:
        filtro["fonte.banca"] = banca
    if ano is not None:
        filtro["fonte.ano"] = ano
    if prova:
        filtro["fonte.prova"] = prova
    if numero_min is not None or numero_max is not None:
        cond: dict = {}
        if numero_min is not None:
            cond["$gte"] = numero_min
        if numero_max is not None:
            cond["$lte"] = numero_max
        filtro["fonte.numero"] = cond
    if area:
        pistas = [p for p, a in _AREAS_ENEM if a == area]
        if pistas:
            filtro["fonte.disciplina"] = {"$regex": "|".join(pistas), "$options": "i"}
        else:
            filtro["fonte.disciplina"] = area  # área desconhecida: match exato, devolve vazio se não bater
    cursor = db.questoes_public.find(
        filtro, PROJECAO_SEM_GABARITO
    ).sort("fonte.numero", 1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": items, "count": len(items)}


# Mapeia o `fonte.disciplina` livre (extraído pelo modelo, com variação de
# caixa e granularidade — ex.: "Física", "MATEMÁTICA E SUAS TECNOLOGIAS",
# "Ciências da Natureza") para a área oficial do ENEM, só para exibição do
# agrupamento em `/api/provas`. Não reescreve `fonte.disciplina` em lugar
# algum — é uma projeção de leitura, o dado armazenado não muda.
_AREAS_ENEM = [
    ("matemática", "Matemática"),
    ("natureza", "Ciências da Natureza"),
    ("física", "Ciências da Natureza"),
    ("química", "Ciências da Natureza"),
    ("biologia", "Ciências da Natureza"),
    ("linguagens", "Linguagens e Códigos"),
    ("humanas", "Ciências Humanas"),
]


def _area_enem(disciplina: str | None) -> str | None:
    if not disciplina:
        return None
    baixo = disciplina.strip().lower()
    for pista, area in _AREAS_ENEM:
        if pista in baixo:
            return area
    return disciplina.strip()


def _area_dominante(disciplinas_raw: "Counter[str]") -> list[str]:
    """A área do bloco é a MODA das disciplinas dos seus itens, não a união.

    Um bloco de 45 é, por estrutura do ENEM, sempre de uma área só. A extração
    automática de `fonte.disciplina` erra em um ou dois itens, e a união
    transformava um caderno 100% de Matemática em "Ciências da Natureza e
    Matemática" — um rótulo que descreve o ruído, não a prova. Empate é
    desfeito por ordem alfabética só para o resultado ser estável entre
    execuções (não acontece em corpus real).
    """
    contagem: Counter[str] = Counter()
    for disciplina, vezes in disciplinas_raw.items():
        if area := _area_enem(disciplina):
            contagem[area] += vezes
    if not contagem:
        return []
    maior = max(contagem.values())
    return [sorted(a for a, n in contagem.items() if n == maior)[0]]


BLOCO_TAMANHO = 45  # 1 prova/área real do ENEM. Um caderno de dia inteiro tem
# 2 blocos (90 questões): 1-45/46-90 no dia 1, 91-135/136-180 no dia 2. Juntar
# os 2 num só "caderno" escondia que são 2 provas distintas.


def _bloco_enem(numero: int | None) -> tuple[int, int] | None:
    """`(inicio, fim)` do bloco canônico de 45 que contém `numero` — sempre
    `(1,45)`, `(46,90)`, `(91,135)`, `(136,180)`, ... nunca o min/max do que
    por acaso está persistido (uma questão faltando não deve encolher o
    bloco nem misturá-lo com o vizinho)."""
    if numero is None:
        return None
    try:
        n = int(numero)
    except (TypeError, ValueError):
        return None
    if n < 1:
        return None
    idx = (n - 1) // BLOCO_TAMANHO
    inicio = idx * BLOCO_TAMANHO + 1
    return (inicio, inicio + BLOCO_TAMANHO - 1)


@api_router.get("/provas")
async def list_provas_publico(_: User = Depends(require_user)):
    """Cadernos disponíveis para prática — **exige sessão**, como `/questoes`:
    é o índice do mesmo acervo e não faz sentido expor a composição do banco a
    quem não entrou. Agrupa 'questoes_public' por (banca, ano, prova,
    bloco de 45 questões), a visão de 'prova' que o aluno escolhe antes de
    praticar. Mesma regra de fonte de dados de `/questoes`: só
    `questoes_public`, nunca Firestore nem a coleção master.

    Itens sem `fonte.numero` (sincronizados antes desta mudança, ou de outra
    fonte que não declara número) não entram em bloco algum — ficariam
    misturados com o bloco errado, o que é pior que não aparecer.
    """
    cursor = db.questoes_public.find({}, {"_id": 0, "fonte": 1})
    grupos: dict[tuple, dict] = {}
    async for doc in cursor:
        fonte = doc.get("fonte") or {}
        bloco = _bloco_enem(fonte.get("numero"))
        if bloco is None:
            continue
        chave = (fonte.get("banca"), fonte.get("ano"), fonte.get("prova"), bloco[0], bloco[1])
        g = grupos.setdefault(chave, {"count": 0, "disciplinas_raw": Counter()})
        g["count"] += 1
        if fonte.get("disciplina"):
            g["disciplinas_raw"][fonte["disciplina"]] += 1

    provas = []
    for (banca, ano, prova, numero_min, numero_max), g in grupos.items():
        areas = _area_dominante(g["disciplinas_raw"])
        provas.append(
            {
                "banca": banca,
                "ano": ano,
                "prova": prova,
                "numero_min": numero_min,
                "numero_max": numero_max,
                "count": g["count"],
                "total_bloco": BLOCO_TAMANHO,
                "disciplinas": areas,
            }
        )
    provas.sort(key=lambda p: (-(p["ano"] or 0), p["prova"] or "", p["numero_min"]))
    return {"provas": provas}


api_router.include_router(auth_module.router)
api_router.include_router(exam_module.router)
api_router.include_router(exam_images_module.router)
api_router.include_router(feed_module.router)
api_router.include_router(annotation_module.router)
api_router.include_router(admin_module.router)
api_router.include_router(events_module.router)
api_router.include_router(firestore_module.router)
api_router.include_router(skills_map_module.router)
api_router.include_router(aulas_particulares_module.router)
api_router.include_router(sparks_module.router)
api_router.include_router(redacao_module.router)
api_router.include_router(client_errors_module.router)
app.include_router(api_router)


# ----------------------------------------------------------------------------
# Health checks — fora do /api para que o balanceador não precise conhecer
# a estrutura da API.
# ----------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    """Liveness: o processo está de pé. Não toca em dependência alguma."""
    return {"status": "ok", "service": "aluno", "app_env": settings.APP_ENV}


@app.get("/ready")
async def ready() -> JSONResponse:
    """Readiness: as dependências respondem?

    O Firestore é verificado mas **não** derruba a prontidão: o app serve
    conteúdo e autentica sem ele; o que para é o registro de resposta. Marcar a
    instância como não-pronta por isso tiraria do ar também o que ainda
    funciona.
    """
    checks: dict[str, Any] = {}
    ok = True

    try:
        await client.admin.command("ping")
        checks["mongo"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["mongo"] = f"falhou: {type(exc).__name__}"
        ok = False

    try:
        import firestore_service as fs

        await asyncio.wait_for(asyncio.to_thread(fs.get_firestore), timeout=8)
        checks["firestore"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["firestore"] = f"indisponível: {type(exc).__name__}"

    try:
        from canonical_ontology import ontology_version

        checks["ontologia"] = ontology_version()
    except Exception as exc:  # noqa: BLE001
        checks["ontologia"] = f"falhou: {type(exc).__name__}"
        ok = False

    checks["gemini_configurado"] = bool(settings.GEMINI_API_KEY)
    # Só booleanos e o ambiente — nunca a credencial. É como se confere, de
    # fora, que as variáveis do Mercado Pago chegaram ao processo e que são as
    # de produção, sem precisar abrir o painel do Fly.
    resumo = settings.resumo()
    checks["mercadopago"] = {
        "access_token": resumo["mercadopago_configurado"],
        "public_key": resumo["mercadopago_public_key_configurada"],
        "webhook_secret": resumo["mercadopago_webhook_configurado"],
        "ambiente": resumo["mercadopago_ambiente"],
        # Loja desligada NÃO derruba a prontidão: o produto serve prática,
        # redação e diagnóstico sem vender nada.
        "loja_habilitada": resumo["loja_habilitada"],
        "loja_motivo": resumo["loja_motivo"],
    }

    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "degraded", "checks": checks},
    )


@app.exception_handler(Exception)
async def _erro_nao_tratado(request: Request, exc: Exception) -> JSONResponse:
    """Registra o traceback e devolve só um identificador ao cliente.

    Sem isto, um erro não tratado pode devolver detalhe interno na resposta —
    caminho de arquivo, estrutura do código, às vezes trecho de query.
    """
    incidente = secrets.token_hex(8)
    logger.exception("[%s] %s %s", incidente, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno.", "incidente": incidente},
    )


if not settings.CORS_ORIGINS:
    logger.warning(
        "CORS_ORIGINS não definido; liberando apenas localhost. Em produção o "
        "boot teria sido recusado."
    )

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS or [
        "http://localhost:3000", "http://localhost:3001", "http://localhost:3002",
    ],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Sincronização automática Firestore -> questoes_public. Sem isto, uma prova
# nova processada no pipeline só aparece para o aluno depois de um admin
# clicar em "Sincronizar Firestore" em /admin — o que já causou o problema
# relatado de "nenhuma questão disponível" com dado real já existente no
# Firestore. 300s (5min) por padrão: frequente o bastante para não incomodar
# quem processou uma prova agora, raro o bastante para não pressionar a cota
# de leitura do Firestore (50k/dia no plano gratuito) à toa.
FIRESTORE_AUTO_SYNC_SECONDS = int(os.environ.get("FIRESTORE_AUTO_SYNC_SECONDS", "300") or 300)


async def _auto_sync_loop():
    """Roda para sempre. Uma falha de sincronização (Firestore fora do ar,
    credencial expirada) é logada e o laço tenta de novo no próximo
    intervalo — nunca derruba o processo nem para de tentar.

    `FIRESTORE_AUTO_SYNC_SECONDS <= 0` desliga o laço (congelamento manual,
    ex.: durante saneamento do corpus). Sem esta guarda, 0 cai em
    `asyncio.sleep(0)` dentro de `while True` e vira um laço quente contra a
    cota de leitura do Firestore."""
    if FIRESTORE_AUTO_SYNC_SECONDS <= 0:
        logger.warning(
            "Auto-sync Firestore DESLIGADO (FIRESTORE_AUTO_SYNC_SECONDS=%d).",
            FIRESTORE_AUTO_SYNC_SECONDS,
        )
        return
    while True:
        await asyncio.sleep(FIRESTORE_AUTO_SYNC_SECONDS)
        try:
            resultado = await admin_module.run_firestore_sync(db)
            logger.info(
                "Auto-sync Firestore: %d itens (master), %d publicados.",
                resultado["master_count"], resultado["public_count"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Auto-sync Firestore falhou (tentando de novo em %ds): %s",
                FIRESTORE_AUTO_SYNC_SECONDS, exc,
            )


@app.on_event("startup")
async def _startup():
    # Antes de qualquer outra coisa: sem os índices, toda requisição
    # autenticada varre `user_sessions` inteira e o dedupe do webhook do
    # Mercado Pago não tem a trava atômica de que depende.
    resultado_indices = await db_indexes.criar_indices(db)
    logger.info(
        "Índices MongoDB: %d criados/confirmados, %d falharam.",
        resultado_indices["criados"], resultado_indices["falhas"],
    )

    if settings.SEED_DEMO_DATA:
        # Gabaritos de exemplo e conteúdo de feed autoral. Em produção isso
        # injetaria dado fictício no banco real — daí o gate.
        logger.info("SEED_DEMO_DATA ligado — semeando dados de demonstração.")
        await migrate_and_seed(db)
        await seed_feed(db)
    else:
        logger.info("SEED_DEMO_DATA desligado — nenhum dado de demonstração inserido.")

    # Firestore seed is best-effort: run in background with a timeout so a bad
    # Firebase credential can never block startup / freeze the event loop.
    async def _safe_firestore_seed():
        try:
            await asyncio.wait_for(_firestore_seed_students(db), timeout=20)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Firestore student seed skipped: %s", exc)

    asyncio.create_task(_safe_firestore_seed())
    asyncio.create_task(_auto_sync_loop())
    if not settings.MERCADOPAGO_HABILITADO:
        # Alto e claro: a loja fechada é uma condição operacional silenciosa —
        # o site funciona, ninguém reclama, e a receita é zero. Tem que estar
        # visível em `fly logs` no primeiro minuto.
        logger.warning(
            "LOJA DE SPARKS DESLIGADA (%s). O produto sobe normalmente e toda "
            "rota de compra devolve 503; o aluno segue ganhando Sparks "
            "praticando. Nenhuma cobrança é possível neste estado.",
            settings.MERCADOPAGO_MOTIVO_DESLIGADA,
        )
    else:
        logger.info("Loja de Sparks HABILITADA (ambiente: %s).",
                    settings.resumo()["mercadopago_ambiente"])

    logger.info(
        "Sapiens ready · %s · auto-sync Firestore a cada %ds",
        settings.resumo(), FIRESTORE_AUTO_SYNC_SECONDS,
    )


@app.on_event("shutdown")
async def _shutdown():
    client.close()
