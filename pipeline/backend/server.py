"""Sapiens Cognitive Annotator — FastAPI backend."""
from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv

# Load .env BEFORE local imports so modules that read env at import time
# (e.g. firestore_sync.COLLECTION_NAME) get the correct values.
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

import batch_queue
import gemini_telemetry
from cognitive_engine import (
    DEFAULT_PIPELINE_SCHEMA,
    parse_ontology_with_gemini,
    run_book_manifest,
    run_cognitive_pipeline,
    run_cognitive_pipeline_adaptive,
)
from firestore_sync import (
    create_question_sync,
    delete_question_sync,
    get_status as firestore_get_status,
    sync_all_questions,
    update_question_sync,
)
from item_contract import (
    SCHEMA_VERSION,
    index_fields as _index_fields,
    normalize_item,
    validate as validate_item,
)
from ontology_seed import DEFAULT_ONTOLOGY
from ontology_validator import OntologyRegistry
import settings
from storage import APP_NAME, build_path, delete_prefix, get_object, init_storage, put_object

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings.exigir_config_valida()

client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
db = client[settings.DB_NAME]

PIPELINE_API_KEY = settings.PIPELINE_API_KEY


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not PIPELINE_API_KEY:
        raise HTTPException(status_code=503, detail="PIPELINE_API_KEY not configured on server")
    # Comparação em tempo constante: `!=` sobre strings sai no primeiro byte
    # divergente, o que transforma a chave num alvo de ataque por temporização.
    if not x_api_key or not hmac.compare_digest(x_api_key, PIPELINE_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


app = FastAPI(
    title="Sapiens Cognitive Annotator",
    # A documentação interativa expõe todo o inventário de rotas e schemas.
    # Útil em desenvolvimento; em produção é superfície gratuita para um
    # atacante mapear o serviço antes mesmo de tentar autenticar.
    docs_url=None if settings.IS_PRODUCTION else "/docs",
    redoc_url=None if settings.IS_PRODUCTION else "/redoc",
    openapi_url=None if settings.IS_PRODUCTION else "/openapi.json",
)
api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


# ----------------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_id(obj: dict) -> dict:
    obj.pop("_id", None)
    return obj


ALLOWED_ONTOLOGY_EXTS = {".json", ".yaml", ".yml", ".md", ".markdown", ".txt", ".docx", ".pdf"}
ALLOWED_QUESTION_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".json": "application/json",
}


ONTOLOGY_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


async def _ler_upload(f: UploadFile, exts_permitidas: set[str]) -> tuple[str, bytes, str]:
    """Lê um upload aplicando limite de extensão e de tamanho.

    O limite de tamanho não é decorativo: sem ele, `await f.read()` carrega o
    corpo inteiro na memória do processo, e um único POST grande derruba a
    instância — que num PaaS de plano gratuito tem poucas centenas de MB.
    """
    nome = f.filename or "arquivo"
    ext = os.path.splitext(nome)[1].lower()
    if ext not in exts_permitidas:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão '{ext}' não suportada. Use: {sorted(exts_permitidas)}",
        )
    data = await f.read()
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"'{nome}' tem {len(data) / 1_048_576:.1f} MB; o limite é "
                f"{settings.MAX_UPLOAD_MB} MB (MAX_UPLOAD_MB)."
            ),
        )
    if not data:
        raise HTTPException(status_code=400, detail=f"'{nome}' está vazio.")
    return nome, data, MIME_BY_EXT.get(ext, "application/octet-stream")


def _limitar_quantidade(files: list[UploadFile]) -> None:
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")
    if len(files) > settings.MAX_FILES_POR_REQUISICAO:
        raise HTTPException(
            status_code=413,
            detail=(
                f"{len(files)} arquivos; o limite por requisição é "
                f"{settings.MAX_FILES_POR_REQUISICAO} (MAX_FILES_POR_REQUISICAO)."
            ),
        )


async def parse_ontology_file(filename: str, data: bytes) -> dict[str, Any]:
    """Parse an ontology file.

    - JSON / YAML: parseados diretamente.
    - PDF / DOCX / MD / TXT: passados para o Gemini que devolve a ontologia
      no schema canônico.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".json":
        parsed = json.loads(data.decode("utf-8", errors="replace"))
    elif ext in (".yaml", ".yml"):
        parsed = yaml.safe_load(data.decode("utf-8", errors="replace"))
    elif ext in ONTOLOGY_MIME:
        mime = ONTOLOGY_MIME[ext]
        parsed = await parse_ontology_with_gemini(filename, data, mime)
    else:
        raise ValueError(f"Extensão '{ext}' não suportada para ontologia.")

    if not isinstance(parsed, dict):
        raise ValueError("Ontologia deve ser um objeto no topo do documento.")

    parsed.setdefault("version", f"custom-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    for key in (
        "dominios",
        "competencias",
        "processos_cognitivos",
        "habilidades_observaveis",
        "tipos_erro",
        "intervencoes_pedagogicas",
    ):
        parsed.setdefault(key, [])
    return parsed


async def get_active_ontology() -> dict[str, Any]:
    doc = await db.ontologies.find_one({"is_active": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=400, detail="Nenhuma ontologia ativa carregada.")
    return doc


async def get_active_schema() -> dict[str, Any]:
    """Return the currently active pipeline schema (JSON estrutura da anotação).

    Falls back to DEFAULT_PIPELINE_SCHEMA if no active schema was ever imported.
    """
    doc = await db.pipeline_schemas.find_one({"is_active": True}, {"_id": 0})
    if doc:
        return doc.get("schema") or DEFAULT_PIPELINE_SCHEMA
    return DEFAULT_PIPELINE_SCHEMA


def _schema_summary(doc: dict[str, Any] | None) -> dict[str, Any]:
    if not doc:
        return {
            "version": SCHEMA_VERSION,
            "name": "Schema Sapiens 2.2 (contrato canônico)",
            "imported_at": None,
            "source_filename": "pipeline/docs/Schema anotador de questoes/06 Schema Sapiens 2.1.json.md",
            "is_default": True,
        }
    return {
        "id": doc.get("id"),
        "version": doc.get("version"),
        "name": doc.get("name"),
        "imported_at": doc.get("imported_at"),
        "source_filename": doc.get("source_filename"),
        "is_default": False,
        "is_active": doc.get("is_active", False),
    }


def _summary(ontology: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": ontology.get("version"),
        "name": ontology.get("name"),
        "description": ontology.get("description"),
        "imported_at": ontology.get("imported_at"),
        "source_filename": ontology.get("source_filename"),
        "counts": {
            "dominios": len(ontology.get("dominios", [])),
            "competencias": len(ontology.get("competencias", [])),
            "processos_cognitivos": len(ontology.get("processos_cognitivos", [])),
            "habilidades_observaveis": len(ontology.get("habilidades_observaveis", [])),
            "tipos_erro": len(ontology.get("tipos_erro", [])),
            "intervencoes_pedagogicas": len(ontology.get("intervencoes_pedagogicas", [])),
        },
    }


# ----------------------------------------------------------------------------
# Startup: init storage + seed default ontology if empty
# ----------------------------------------------------------------------------
@app.on_event("startup")
async def _startup() -> None:
    try:
        init_storage()
    except Exception as exc:  # pragma: no cover — logs but keeps server up
        logger.error("Falha ao iniciar object storage: %s", exc)

    existing = await db.ontologies.find_one({"is_active": True})
    if existing:
        # Migration: a previously auto-seeded ontology (source_filename ==
        # "seed_default.json") whose version no longer matches the canonical
        # docs/ontology JSON is stale — archive it (never delete) and activate
        # the canonical version. A real imported ontology (any other
        # source_filename) is left untouched.
        if (
            existing.get("source_filename") == "seed_default.json"
            and existing.get("version") != DEFAULT_ONTOLOGY["version"]
        ):
            await db.ontologies.update_one({"id": existing["id"]}, {"$set": {"is_active": False}})
            canonical = {
                **DEFAULT_ONTOLOGY,
                "id": str(uuid.uuid4()),
                "imported_at": _now_iso(),
                "source_filename": "seed_default.json",
                "is_active": True,
            }
            await db.ontologies.insert_one(canonical)
            logger.info(
                "Ontologia semente desatualizada (%s) arquivada; canônica %s ativada.",
                existing.get("version"), canonical["version"],
            )
            return
        logger.info("Ontologia ativa: %s", existing.get("version"))
        return

    seed = {
        **DEFAULT_ONTOLOGY,
        "id": str(uuid.uuid4()),
        "imported_at": _now_iso(),
        "source_filename": "seed_default.json",
        "is_active": True,
    }
    await db.ontologies.insert_one(seed)
    logger.info("Ontologia semente inserida (versão %s)", seed["version"])


@app.on_event("shutdown")
async def _shutdown() -> None:
    client.close()


# ----------------------------------------------------------------------------
# Ontology endpoints
# ----------------------------------------------------------------------------
@api_router.get("/ontology")
async def get_ontology() -> dict:
    ontology = await get_active_ontology()
    return ontology


@api_router.get("/ontology/summary")
async def ontology_summary() -> dict:
    ontology = await get_active_ontology()
    return _summary(ontology)


@api_router.get("/ontology/versions")
async def ontology_versions() -> list[dict]:
    versions = await db.ontologies.find(
        {}, {"_id": 0, "version": 1, "imported_at": 1, "source_filename": 1, "is_active": 1, "id": 1}
    ).sort("imported_at", -1).to_list(200)
    return versions


@api_router.post("/ontology/import")
async def import_ontology(file: UploadFile = File(...)) -> dict:
    _, data, _ = await _ler_upload(file, ALLOWED_ONTOLOGY_EXTS)
    try:
        parsed = await parse_ontology_file(file.filename or "ontology", data)
    except Exception as exc:
        logger.exception("Falha ao parsear ontologia")
        raise HTTPException(status_code=400, detail=f"Erro ao parsear: {exc}") from exc

    total = sum(len(parsed.get(k, [])) for k in (
        "dominios", "competencias", "processos_cognitivos",
        "habilidades_observaveis", "tipos_erro", "intervencoes_pedagogicas",
    ))
    if total == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Nenhum elemento cognitivo encontrado no arquivo. "
                "Verifique se o documento contém domínios/competências/processos "
                "ou use o botão 'Resetar para versão canônica'."
            ),
        )

    # Deactivate previous active
    await db.ontologies.update_many({"is_active": True}, {"$set": {"is_active": False}})

    doc = {
        **parsed,
        "id": str(uuid.uuid4()),
        "imported_at": _now_iso(),
        "source_filename": file.filename,
        "is_active": True,
    }
    await db.ontologies.insert_one(doc)
    return _summary(doc)


@api_router.post("/ontology/reset")
async def reset_ontology() -> dict:
    """Restaura a ontologia canônica (pipeline/docs/ontology). Se já existir uma
    cópia no banco, ativa-a; caso contrário, reinsere."""
    seed = await db.ontologies.find_one({"version": DEFAULT_ONTOLOGY["version"]})
    await db.ontologies.update_many({"is_active": True}, {"$set": {"is_active": False}})
    if seed:
        await db.ontologies.update_one({"id": seed["id"]}, {"$set": {"is_active": True}})
        activated = await db.ontologies.find_one({"id": seed["id"]}, {"_id": 0})
    else:
        activated = {
            **DEFAULT_ONTOLOGY,
            "id": str(uuid.uuid4()),
            "imported_at": _now_iso(),
            "source_filename": "seed_default.json",
            "is_active": True,
        }
        await db.ontologies.insert_one(activated)
        activated = await db.ontologies.find_one({"id": activated["id"]}, {"_id": 0})
    return _summary(activated)


@api_router.post("/ontology/activate/{ontology_id}")
async def activate_ontology(ontology_id: str) -> dict:
    target = await db.ontologies.find_one({"id": ontology_id})
    if not target:
        raise HTTPException(status_code=404, detail="Ontologia não encontrada.")
    await db.ontologies.update_many({"is_active": True}, {"$set": {"is_active": False}})
    await db.ontologies.update_one({"id": ontology_id}, {"$set": {"is_active": True}})
    activated = await db.ontologies.find_one({"id": ontology_id}, {"_id": 0})
    return _summary(activated)


# ----------------------------------------------------------------------------
# Pipeline schema endpoints (JSON estrutural que descreve como o Gemini deve
# anotar cada questão). Independente da ontologia.
# ----------------------------------------------------------------------------
@api_router.get("/schema")
async def get_schema() -> dict:
    """Return the currently active pipeline schema + metadata."""
    doc = await db.pipeline_schemas.find_one({"is_active": True}, {"_id": 0})
    if not doc:
        return {
            "summary": _schema_summary(None),
            "schema": DEFAULT_PIPELINE_SCHEMA,
        }
    return {
        "summary": _schema_summary(doc),
        "schema": doc.get("schema") or DEFAULT_PIPELINE_SCHEMA,
    }


@api_router.get("/schema/summary")
async def schema_summary() -> dict:
    doc = await db.pipeline_schemas.find_one({"is_active": True}, {"_id": 0})
    return _schema_summary(doc)


@api_router.get("/schema/versions")
async def schema_versions() -> list[dict]:
    docs = await db.pipeline_schemas.find(
        {}, {"_id": 0, "id": 1, "version": 1, "name": 1, "imported_at": 1,
             "source_filename": 1, "is_active": 1}
    ).sort("imported_at", -1).to_list(200)
    return docs


@api_router.post("/schema/import")
async def import_schema(file: UploadFile = File(...)) -> dict:
    """Importa um schema de saída customizado (JSON) para instruir o modelo.

    **Aviso de contrato.** O schema builtin é o **Schema Sapiens 2.2**, contrato
    canônico do item anotado. Um schema importado substitui apenas a *instrução
    de forma* enviada ao modelo — ele NÃO desliga a normalização nem a
    validação: `ontology_version`, `item_id`, `item_hash` e a derivação de
    domínios/competências continuam sendo aplicados pelo servidor, e o resultado
    continua sendo validado contra o Schema 2.2. Um schema que produza forma
    incompatível gera itens marcados como inválidos em `validacao`, não itens
    fora de contrato.
    """
    _, data, _ = await _ler_upload(file, {".json"})
    try:
        parsed = json.loads(data.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"JSON inválido: {exc}") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="O schema deve ser um objeto JSON no topo.")

    # Deactivate previous
    await db.pipeline_schemas.update_many({"is_active": True}, {"$set": {"is_active": False}})

    doc = {
        "id": str(uuid.uuid4()),
        "version": parsed.get("_meta", {}).get("version")
        or parsed.get("version")
        or f"custom-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "name": parsed.get("_meta", {}).get("name") or file.filename,
        "imported_at": _now_iso(),
        "source_filename": file.filename,
        "is_active": True,
        "schema": parsed,
    }
    await db.pipeline_schemas.insert_one(doc)
    return {"summary": _schema_summary(doc), "schema": parsed}


@api_router.post("/schema/reset")
async def reset_schema() -> dict:
    """Deactivate any custom schema; the engine falls back to the builtin default."""
    await db.pipeline_schemas.update_many({"is_active": True}, {"$set": {"is_active": False}})
    return {"summary": _schema_summary(None), "schema": DEFAULT_PIPELINE_SCHEMA}


# ----------------------------------------------------------------------------
# Pipeline endpoints
# ----------------------------------------------------------------------------
class PipelineListItem(BaseModel):
    id: str
    created_at: str
    item_id: str | None = None
    item_hash: str | None = None
    disciplina: str | None = None
    banca: str | None = None
    ano: str | None = None
    tema: str | None = None
    resposta_correta: str | None = None
    ontology_version: str | None = None
    schema_version: str | None = None
    processos: list[str] = Field(default_factory=list)
    competencias: list[str] = Field(default_factory=list)
    dominios: list[str] = Field(default_factory=list)


def _persist_annotation(
    record: dict, item: dict, ontology: dict, registry: OntologyRegistry
) -> None:
    """Grava a anotação normalizada no registro + o resultado da validação.

    A validação é **registrada, nunca bloqueante**, e isso é exigido pelo corpus,
    não escolhido aqui. `EXT-WP1-1.0`, item L13, lista "ler a regra 1 como
    proibição de armazenamento" entre os **riscos de reintrodução indevida**:
    "o item pode ser armazenado; não pode ser exposto ao motor. A distinção é o
    que permite ingestão em massa com enriquecimento posterior."

    O que impede um item de contaminar a camada de crença é
    `qualidade.apto_para_camada_de_crenca` (L13b), que só a revisão humana torna
    verdadeiro — nunca a recusa de ingestão.
    """
    record["item"] = item
    record["schema_version"] = item.get("schema_version")
    record["ontology_version"] = item.get("ontology_version") or ontology.get("version")
    record["validacao"] = validate_item(item, registry)
    record.update(_index_fields(item))


async def _persist_artifacts(
    question_id: str, files: list[tuple[str, bytes, str]], extraction: dict, pipeline_json: dict
) -> dict:
    """Upload the 3 artifacts and return their storage paths."""
    original_paths: list[dict] = []
    for filename, data, content_type in files:
        p = build_path("original", question_id, filename)
        try:
            put_object(p, data, content_type)
        except Exception as exc:
            logger.exception("Falha ao subir artefato original: %s", exc)
            raise HTTPException(status_code=500, detail=f"Falha ao salvar original: {exc}")
        original_paths.append(
            {"filename": filename, "path": p, "content_type": content_type, "size": len(data)}
        )

    extraction_bytes = json.dumps(extraction, ensure_ascii=False, indent=2).encode()
    extraction_path = build_path("extraction", question_id, "extraction.json")
    put_object(extraction_path, extraction_bytes, "application/json")

    pipeline_bytes = json.dumps(pipeline_json, ensure_ascii=False, indent=2).encode()
    pipeline_path = build_path("pipeline", question_id, "pipeline.json")
    put_object(pipeline_path, pipeline_bytes, "application/json")

    return {
        "originals": original_paths,
        "extraction": extraction_path,
        "pipeline": pipeline_path,
    }


def _discard_artifacts(question_id: str) -> None:
    """Remove os binários de um item apagado.

    Enquanto o storage era da Emergent, apagar um item deixava os artefatos
    órfãos numa infraestrutura fora de alcance. Agora o storage é nosso, então
    apagar um item apaga também os arquivos dele. Best-effort: uma falha aqui
    não pode desfazer a remoção do registro, que já ocorreu.
    """
    try:
        removed = delete_prefix(f"{APP_NAME}/questions/{question_id}")
        if removed:
            logger.info("Artefatos removidos para %s: %d", question_id, removed)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao remover artefatos de %s: %s", question_id, exc)


@api_router.post("/pipeline/generate")
async def generate_pipeline(
    files: list[UploadFile] = File(...),
    fonte: str | None = Query(
        None,
        description=(
            "JSON com a procedência já conhecida (banca, ano, prova, numero, "
            "disciplina). Sobrescreve o que o modelo inferir: numa prova de 2023 "
            "ele chegou a devolver ano 2010. Também é o que torna o item_id "
            "determinístico e estável."
        ),
    ),
) -> dict:
    _limitar_quantidade(files)

    ontology = await get_active_ontology()
    schema = await get_active_schema()

    incoming: list[tuple[str, bytes, str]] = [
        await _ler_upload(f, ALLOWED_QUESTION_EXTS) for f in files
    ]

    question_id = str(uuid.uuid4())

    fonte_conhecida = None
    if fonte:
        try:
            fonte_conhecida = json.loads(fonte)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"'fonte' não é JSON válido: {exc}")
        if not isinstance(fonte_conhecida, dict):
            raise HTTPException(status_code=400, detail="'fonte' deve ser um objeto JSON.")

    registry = OntologyRegistry.from_dict(ontology)

    async def _usage_sink(u: dict) -> None:
        await gemini_telemetry.persist(
            db.gemini_usage, u, context="pipeline_generate", item_id=question_id,
        )

    def _judge(raw_candidate: dict) -> bool:
        candidate_item = normalize_item(
            raw_candidate, ontology, arquivo_origem=incoming[0][0] if incoming else None,
            fonte_conhecida=fonte_conhecida, registry=registry,
        )
        return validate_item(candidate_item, registry)["valid"]

    # Cognitive pass
    try:
        raw, _thinking_meta = await run_cognitive_pipeline_adaptive(
            ontology, [(n, d) for n, d, _ in incoming], schema=schema,
            cache_collection=db.gemini_caches, on_usage=_usage_sink, judge=_judge,
        )
    except Exception as exc:
        logger.exception("Falha no pipeline cognitivo")
        raise HTTPException(status_code=502, detail=f"Falha na chamada do modelo: {exc}") from exc

    item = normalize_item(
        raw, ontology, arquivo_origem=incoming[0][0] if incoming else None,
        fonte_conhecida=fonte_conhecida, registry=registry,
    )

    # Artefato de extração = o bloco `questao` do contrato 2.2 (extração
    # estruturada), separado da classificação cognitiva.
    extraction = {"questao": item.get("questao"), "arquivos": [n for n, _, _ in incoming]}

    record = {
        "id": question_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "artifacts": {},
    }
    _persist_annotation(record, item, ontology, registry)
    # Persist the (already paid for) model output before touching object storage,
    # so a storage outage costs the binaries but never the cognitive result.
    await db.pipelines.insert_one(record)

    try:
        artifacts = await _persist_artifacts(question_id, incoming, extraction, item)
    except Exception as exc:
        logger.exception("Artefatos não persistidos para %s: %s", question_id, exc)
        record["artifacts_error"] = str(exc)
        await db.pipelines.update_one(
            {"id": question_id}, {"$set": {"artifacts_error": str(exc)}}
        )
    else:
        record["artifacts"] = artifacts
        await db.pipelines.update_one(
            {"id": question_id}, {"$set": {"artifacts": artifacts, "updated_at": _now_iso()}}
        )

    create_question_sync(question_id, record)
    return _clean_id({**record})


@api_router.get("/pipelines")
async def list_pipelines(
    q: str | None = Query(None, description="Busca por tema/disciplina/enunciado"),
    disciplina: str | None = None,
    banca: str | None = None,
    ano: str | None = None,
    processo: str | None = None,
    competencia: str | None = None,
    dominio: str | None = None,
    limit: int = 100,
) -> list[dict]:
    query: dict[str, Any] = {}
    if disciplina:
        query["disciplina"] = disciplina
    if banca:
        query["banca"] = banca
    if ano:
        query["ano"] = ano
    if processo:
        query["processos"] = processo
    if competencia:
        query["competencias"] = competencia
    if dominio:
        query["dominios"] = dominio
    if q:
        query["$or"] = [
            {"tema": {"$regex": q, "$options": "i"}},
            {"disciplina": {"$regex": q, "$options": "i"}},
            {"item.questao.enunciado": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.pipelines.find(
        query,
        {
            "_id": 0,
            "id": 1,
            "created_at": 1,
            "item_id": 1,
            "item_hash": 1,
            "disciplina": 1,
            "banca": 1,
            "ano": 1,
            "tema": 1,
            "resposta_correta": 1,
            "ontology_version": 1,
            "schema_version": 1,
            "validacao": 1,
            "processos": 1,
            "competencias": 1,
            "dominios": 1,
        },
    ).sort("created_at", -1).to_list(limit)
    return docs


@api_router.get("/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: str) -> dict:
    doc = await db.pipelines.find_one({"id": pipeline_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado.")
    return doc


class BulkIdsRequest(BaseModel):
    ids: list[str]


@api_router.post("/pipelines/bulk_get")
async def bulk_get_pipelines(payload: BulkIdsRequest) -> list[dict]:
    """Retorna os pipelines pedidos preservando a ordem dos ids."""
    docs = await db.pipelines.find({"id": {"$in": payload.ids}}, {"_id": 0}).to_list(500)
    by_id = {d["id"]: d for d in docs}
    return [by_id[i] for i in payload.ids if i in by_id]


@api_router.post("/pipelines/bulk_delete")
async def bulk_delete_pipelines(payload: BulkIdsRequest) -> dict:
    result = await db.pipelines.delete_many({"id": {"$in": payload.ids}})
    for pid in payload.ids:
        delete_question_sync(pid)
        _discard_artifacts(pid)
    return {"deleted": result.deleted_count}


class PipelineUpdate(BaseModel):
    # `item` é o nome canônico (Schema 2.2). `pipeline` é aceito como alias de
    # compatibilidade para clientes ainda não migrados.
    item: dict | None = None
    pipeline: dict | None = None

    def payload(self) -> dict:
        doc = self.item if self.item is not None else self.pipeline
        if doc is None:
            raise HTTPException(status_code=422, detail="Envie o item anotado em 'item'.")
        return doc


@api_router.put("/pipeline/{pipeline_id}")
async def update_pipeline(pipeline_id: str, payload: PipelineUpdate) -> dict:
    existing = await db.pipelines.find_one({"id": pipeline_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado.")

    ontology = await get_active_ontology()
    registry = OntologyRegistry.from_dict(ontology)
    # Preserva o item_id existente: ele é invariável por contrato entre
    # pipeline, Firestore, aluno e professor. Editar o conteúdo muda o
    # `item_hash`, nunca a identidade do item.
    item = normalize_item(
        payload.payload(),
        ontology,
        item_id=existing.get("item_id") or (existing.get("item") or {}).get("item_id"),
        registry=registry,
    )

    update: dict[str, Any] = {"updated_at": _now_iso()}
    _persist_annotation(update, item, ontology, registry)

    # Re-upload pipeline artifact (extraction remains untouched)
    try:
        put_object(
            existing["artifacts"]["pipeline"],
            json.dumps(item, ensure_ascii=False, indent=2).encode(),
            "application/json",
        )
    except Exception as exc:
        logger.exception("Falha ao regravar artefato do pipeline")
        raise HTTPException(status_code=500, detail=f"Falha ao salvar pipeline: {exc}") from exc
    await db.pipelines.update_one({"id": pipeline_id}, {"$set": update})
    doc = await db.pipelines.find_one({"id": pipeline_id}, {"_id": 0})
    update_question_sync(pipeline_id, doc)
    return doc


@api_router.post("/pipeline/{pipeline_id}/regenerate")
async def regenerate_pipeline(pipeline_id: str) -> dict:
    existing = await db.pipelines.find_one({"id": pipeline_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado.")

    ontology = await get_active_ontology()
    schema = await get_active_schema()

    files: list[tuple[str, bytes]] = []
    for orig in existing["artifacts"]["originals"]:
        data, _ = get_object(orig["path"])
        files.append((orig["filename"], data))

    registry = OntologyRegistry.from_dict(ontology)
    existing_item_id = existing.get("item_id") or (existing.get("item") or {}).get("item_id")

    async def _usage_sink(u: dict) -> None:
        await gemini_telemetry.persist(
            db.gemini_usage, u, context="pipeline_regenerate", item_id=pipeline_id,
        )

    def _judge(raw_candidate: dict) -> bool:
        candidate_item = normalize_item(
            raw_candidate, ontology, item_id=existing_item_id,
            arquivo_origem=files[0][0] if files else None, registry=registry,
        )
        return validate_item(candidate_item, registry)["valid"]

    try:
        raw, _thinking_meta = await run_cognitive_pipeline_adaptive(
            ontology, files, schema=schema, cache_collection=db.gemini_caches,
            on_usage=_usage_sink, judge=_judge,
        )
    except Exception as exc:
        logger.exception("Falha na regeneração")
        raise HTTPException(status_code=502, detail=f"Falha na chamada do modelo: {exc}") from exc

    item = normalize_item(
        raw,
        ontology,
        item_id=existing_item_id,
        arquivo_origem=files[0][0] if files else None,
        registry=registry,
    )

    put_object(
        existing["artifacts"]["pipeline"],
        json.dumps(item, ensure_ascii=False, indent=2).encode(),
        "application/json",
    )

    update: dict[str, Any] = {"updated_at": _now_iso()}
    _persist_annotation(update, item, ontology, registry)
    await db.pipelines.update_one({"id": pipeline_id}, {"$set": update})
    doc = await db.pipelines.find_one({"id": pipeline_id}, {"_id": 0})
    update_question_sync(pipeline_id, doc)
    return doc


@api_router.delete("/pipeline/{pipeline_id}")
async def delete_pipeline(pipeline_id: str) -> dict:
    result = await db.pipelines.delete_one({"id": pipeline_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado.")
    delete_question_sync(pipeline_id)
    _discard_artifacts(pipeline_id)
    return {"deleted": True, "id": pipeline_id}


# ----------------------------------------------------------------------------
# Book (caderno) endpoints — split a multi-question PDF into individual pipelines
# ----------------------------------------------------------------------------
@api_router.post("/book/upload")
async def upload_book(
    files: list[UploadFile] = File(...),
    banca: str = Form(..., description="Banca examinadora. Para ENEM, deve ser exatamente 'ENEM'."),
    ano: int = Form(..., description="Ano da prova."),
    prova: str = Form(..., description="Cor/identificador do caderno (ex.: Azul, Amarelo, CAD11)."),
) -> dict:
    """Recebe o PDF do caderno + a procedência fornecida pelo usuário.

    `banca`/`ano`/`prova` são OBRIGATÓRIOS aqui, não opcionais em algum ponto
    posterior: são metadado de procedência, e o Manual §8 proíbe inferi-los do
    conteúdo. O modelo lê o cabeçalho da página e erra — numa prova de 2023 já
    devolveu ano 2010 e 2016. Ficam presos ao caderno inteiro (todas as
    questões dele compartilham a mesma banca/ano/prova) e são carimbados sobre
    o que o modelo produzir em `/book/{id}/process`, nunca aceitos dele.
    """
    banca = banca.strip()
    prova = prova.strip()
    if not banca:
        raise HTTPException(status_code=400, detail="'banca' não pode ser vazia.")
    if not prova:
        raise HTTPException(status_code=400, detail="'prova' (cor do caderno) não pode ser vazia.")
    if banca.upper() == "ENEM" and banca != "ENEM":
        raise HTTPException(status_code=400, detail="Para ENEM, 'banca' deve ser registrada exatamente como 'ENEM'.")
    if not (1998 <= ano <= 2100):
        raise HTTPException(status_code=400, detail=f"'ano'={ano} fora do intervalo plausível (1998–2100).")

    _limitar_quantidade(files)

    book_id = str(uuid.uuid4())
    stored: list[dict] = []
    for f in files:
        filename, data, content_type = await _ler_upload(f, ALLOWED_QUESTION_EXTS)
        path = build_path("book", book_id, filename)
        try:
            put_object(path, data, content_type)
        except Exception as exc:
            logger.exception("Falha ao salvar arquivo do caderno")
            raise HTTPException(status_code=500, detail=f"Falha ao salvar: {exc}") from exc
        stored.append(
            {"filename": filename, "path": path, "content_type": content_type, "size": len(data)}
        )

    doc = {
        "id": book_id,
        "created_at": _now_iso(),
        "files": stored,
        "manifest": None,
        "manifest_generated_at": None,
        "banca": banca,
        "ano": ano,
        "prova": prova,
    }
    await db.books.insert_one(doc)
    return _clean_id({**doc})


async def _load_book_files(book_doc: dict) -> list[tuple[str, bytes, str]]:
    result: list[tuple[str, bytes, str]] = []
    for f in book_doc["files"]:
        data, _ = get_object(f["path"])
        result.append((f["filename"], data, f["content_type"]))
    return result


def _book_fonte_conhecida(book_doc: dict, question_number: str) -> dict:
    """Procedência autoritativa do caderno: fornecida pelo usuário no upload,
    nunca inferida ou substituída pelo modelo (Manual §8).

    `banca`/`ano`/`prova` vêm do caderno inteiro; `numero` é por questão. Os
    quatro juntos são exatamente `_FONTE_PARA_ID` — o que torna `item_id`
    determinístico. Cadernos antigos (anteriores a esta exigência) podem não
    ter `banca`/`ano`/`prova` gravados; nesse caso o valor é omitido em vez de
    forçado a `None`, para não sobrescrever uma inferência do modelo com um
    `null` pior do que ela.
    """
    try:
        numero: Any = int(question_number)
    except (TypeError, ValueError):
        numero = question_number
    fonte: dict[str, Any] = {"numero": numero}
    for campo in ("banca", "ano", "prova"):
        if book_doc.get(campo) is not None:
            fonte[campo] = book_doc[campo]
    return fonte


@api_router.post("/book/{book_id}/manifest")
async def book_manifest(book_id: str) -> dict:
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Caderno não encontrado.")

    incoming = await _load_book_files(book)
    try:
        manifest = await run_book_manifest([(n, d) for n, d, _ in incoming])
    except Exception as exc:
        logger.exception("Falha ao gerar manifesto")
        raise HTTPException(status_code=502, detail=f"Falha no manifesto: {exc}") from exc

    await db.books.update_one(
        {"id": book_id},
        {"$set": {"manifest": manifest, "manifest_generated_at": _now_iso()}},
    )
    return {"book_id": book_id, "manifest": manifest}


class BookProcessRequest(BaseModel):
    question_number: str
    question_title: str | None = None
    # Vale só para este processamento — nunca muda GEMINI_THINKING_LEVEL nem
    # o padrão global (`cognitive_engine.DEFAULT_THINKING_LEVEL`). Ausente
    # usa o padrão do processo, como antes.
    thinking_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None


@api_router.post("/book/{book_id}/process")
async def book_process_question(book_id: str, payload: BookProcessRequest) -> dict:
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Caderno não encontrado.")

    ontology = await get_active_ontology()
    schema = await get_active_schema()
    incoming = await _load_book_files(book)
    files_bytes = [(n, d) for n, d, _ in incoming]

    focus_hint = f"Questão nº {payload.question_number}"
    if payload.question_title:
        focus_hint += f" — {payload.question_title.strip()}"

    question_id = str(uuid.uuid4())
    registry = OntologyRegistry.from_dict(ontology)
    fonte_conhecida = _book_fonte_conhecida(book, payload.question_number)

    async def _usage_sink(u: dict) -> None:
        await gemini_telemetry.persist(
            db.gemini_usage, u, context="book_process",
            book_id=book_id, question_number=payload.question_number, item_id=question_id,
        )

    def _judge(raw_candidate: dict) -> bool:
        candidate_item = normalize_item(
            raw_candidate, ontology, arquivo_origem=incoming[0][0] if incoming else None,
            fonte_conhecida=fonte_conhecida, registry=registry,
        )
        return validate_item(candidate_item, registry)["valid"]

    try:
        raw, _thinking_meta = await run_cognitive_pipeline_adaptive(
            ontology, files_bytes, focus_hint=focus_hint, schema=schema,
            cache_collection=db.gemini_caches, on_usage=_usage_sink,
            thinking_level=payload.thinking_level, judge=_judge,
            # Mesmo book_id em toda questão deste caderno: a 1ª chamada sobe
            # o PDF pro cache, as seguintes só leem — não reenvia o PDF
            # inteiro (32 páginas) em toda questão. Ver
            # `run_cognitive_pipeline` e auditoria/AUDITORIA-OTIMIZACAO-
            # CUSTO-GEMINI-2.md.
            book_cache_key=book_id,
        )
    except Exception as exc:
        logger.exception("Falha no pipeline (caderno)")
        raise HTTPException(status_code=502, detail=f"Falha na chamada do modelo: {exc}") from exc

    item = normalize_item(
        raw, ontology, arquivo_origem=incoming[0][0] if incoming else None,
        fonte_conhecida=fonte_conhecida, registry=registry,
    )

    extraction = {
        "questao": item.get("questao"),
        "arquivos": [n for n, _, _ in incoming],
        "book_id": book_id,
        "question_number": payload.question_number,
    }
    artifacts = await _persist_artifacts(question_id, incoming, extraction, item)

    record = {
        "id": question_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "artifacts": artifacts,
        "book_id": book_id,
        "question_number": payload.question_number,
    }
    _persist_annotation(record, item, ontology, registry)
    await db.pipelines.insert_one(record)
    create_question_sync(question_id, record)
    return _clean_id({**record})


@api_router.get("/book/{book_id}")
async def get_book(book_id: str) -> dict:
    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Caderno não encontrado.")
    return doc


# ----------------------------------------------------------------------------
# Batch endpoints — fila com retry/backoff, para lotes que uma chamada
# síncrona por questão não sobrevive (ex.: 429 de cota diária no meio do
# lote). Ver `batch_queue.py`. Ninguém aqui inicia processamento sozinho:
# `enqueue` só grava; `drain` é quem de fato chama o Gemini, e só quando
# chamado explicitamente.
# ----------------------------------------------------------------------------
@api_router.post("/batch/enqueue")
async def batch_enqueue(
    files: list[UploadFile] = File(...),
    fonte: str | None = Query(None, description="JSON com a procedência já conhecida (mesmo formato de /pipeline/generate)."),
) -> dict:
    _limitar_quantidade(files)
    incoming = [await _ler_upload(f, ALLOWED_QUESTION_EXTS) for f in files]

    fonte_conhecida = None
    if fonte:
        try:
            fonte_conhecida = json.loads(fonte)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"'fonte' não é JSON válido: {exc}")
        if not isinstance(fonte_conhecida, dict):
            raise HTTPException(status_code=400, detail="'fonte' deve ser um objeto JSON.")

    item_id = await batch_queue.enqueue(db, files=incoming, fonte_conhecida=fonte_conhecida)
    return {"queue_item_id": item_id, "status": "pending"}


@api_router.post("/batch/enqueue/book/{book_id}")
async def batch_enqueue_book_question(book_id: str, payload: BookProcessRequest) -> dict:
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Caderno não encontrado.")
    incoming = await _load_book_files(book)

    focus_hint = f"Questão nº {payload.question_number}"
    if payload.question_title:
        focus_hint += f" — {payload.question_title.strip()}"

    item_id = await batch_queue.enqueue(
        db, files=incoming,
        fonte_conhecida=_book_fonte_conhecida(book, payload.question_number),
        focus_hint=focus_hint,
    )
    return {"queue_item_id": item_id, "status": "pending", "book_id": book_id}


@api_router.post("/batch/drain")
async def batch_drain(limit: int = Query(20, ge=1, le=200)) -> dict:
    """Processa até `limit` itens já no prazo. Chamada explícita — não há
    scheduler em background; repita a chamada (manualmente, via cron, etc.)
    para continuar drenando a fila."""
    ontology = await get_active_ontology()
    schema = await get_active_schema()
    return await batch_queue.drain(
        db, ontology=ontology, schema=schema, limit=limit, cache_collection=db.gemini_caches,
    )


@api_router.get("/batch/status")
async def batch_status() -> dict:
    return await batch_queue.status(db)


@api_router.post("/batch/requeue/{item_id}")
async def batch_requeue(item_id: str) -> dict:
    ok = await batch_queue.requeue(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item de fila não encontrado.")
    return {"queue_item_id": item_id, "status": "pending"}


@api_router.get("/pipeline/{pipeline_id}/artifact/{kind}")
async def download_artifact(pipeline_id: str, kind: str, index: int = 0):
    doc = await db.pipelines.find_one({"id": pipeline_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado.")

    artifacts = doc.get("artifacts", {})
    if kind == "original":
        originals = artifacts.get("originals", [])
        if index >= len(originals):
            raise HTTPException(status_code=404, detail="Original inexistente.")
        entry = originals[index]
        data, ct = get_object(entry["path"])
        return Response(
            content=data,
            media_type=entry.get("content_type", ct),
            headers={"Content-Disposition": f'inline; filename="{entry["filename"]}"'},
        )
    if kind == "extraction":
        data, _ = get_object(artifacts["extraction"])
        return Response(content=data, media_type="application/json")
    if kind == "pipeline":
        data, _ = get_object(artifacts["pipeline"])
        return Response(content=data, media_type="application/json")
    raise HTTPException(status_code=400, detail="Tipo inválido. Use original|extraction|pipeline.")


# ----------------------------------------------------------------------------
# LLM diagnostic
# ----------------------------------------------------------------------------
@api_router.get("/llm/status")
async def llm_status() -> dict:
    """Diagnóstico da configuração do Gemini em runtime.

    Retorna prefixo/sufixo mascarados da chave que o processo carregou, o modelo
    ativo, e o resultado de uma chamada de teste ('ping' → 'pong'). Sem custo
    significativo — usa 1 request minúsculo.
    """
    key = os.environ.get("GEMINI_API_KEY") or ""
    model = os.environ.get("GEMINI_MODEL") or "gemini-3-flash-preview"
    if not key:
        return {
            "configured": False,
            "model": model,
            "error": "GEMINI_API_KEY não carregada no processo",
        }

    masked = f"{key[:8]}...{key[-4:]}" if len(key) >= 14 else "***"
    result: dict[str, Any] = {
        "configured": True,
        "key_masked": masked,
        "key_length": len(key),
        "key_source": ".env (backend/.env)",
        "model": model,
    }

    # Live probe — confirms the paid key is actually accepted by Google
    try:
        from google import genai as _genai

        client = _genai.Client(api_key=key)
        resp = client.models.generate_content(model=model, contents=["ping"])
        text = (getattr(resp, "text", "") or "").strip()
        result["live_probe"] = "ok"
        result["live_probe_response"] = text[:80]
    except Exception as exc:  # noqa: BLE001
        result["live_probe"] = "failed"
        result["live_probe_error"] = f"{type(exc).__name__}: {exc}"

    return result


# ----------------------------------------------------------------------------
# Firestore sync endpoints
# ----------------------------------------------------------------------------
@api_router.get("/firestore/status")
async def firestore_status() -> dict:
    """Return current mirror state (count, retry queue, stats)."""
    return firestore_get_status()


@api_router.post("/firestore/sync-all")
async def firestore_sync_all() -> dict:
    """Full reconciliation: upsert every internal question and remove orphans.

    The internal Mongo collection remains the source of truth; this endpoint
    only rewrites the Firestore mirror to match.
    """
    docs = await db.pipelines.find({}, {"_id": 0}).to_list(10000)
    return sync_all_questions(docs)


@api_router.get("/firestore/document/{question_id}")
async def firestore_document(question_id: str) -> dict:
    """Read-only mirror inspection (useful for tests and debugging)."""
    from firestore_sync import peek_document

    doc = peek_document(question_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado no Firestore.")
    return doc


# ----------------------------------------------------------------------------
# Stats
# ----------------------------------------------------------------------------
@api_router.get("/stats")
async def get_stats() -> dict:
    total = await db.pipelines.count_documents({})
    ontology = await db.ontologies.find_one({"is_active": True}, {"_id": 0})
    by_disciplina: list[dict] = []
    async for row in db.pipelines.aggregate([
        {"$group": {"_id": "$disciplina", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]):
        by_disciplina.append({"disciplina": row["_id"] or "—", "count": row["count"]})
    return {
        "total_pipelines": total,
        "ontology": _summary(ontology) if ontology else None,
        "top_disciplinas": by_disciplina,
    }


@api_router.get("/")
async def root() -> dict:
    return {"name": "Sapiens Cognitive Annotator", "status": "ok"}


app.include_router(api_router)


# ----------------------------------------------------------------------------
# Health checks — FORA do api_router, portanto sem exigir X-API-Key.
# O balanceador da plataforma não tem a chave; se o health exigisse auth, o
# serviço seria marcado como morto e reiniciado em laço.
# ----------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    """Liveness: o processo está de pé. Não toca em dependência alguma."""
    return {"status": "ok", "service": "pipeline", "app_env": settings.APP_ENV}


@app.get("/ready")
async def ready() -> JSONResponse:
    """Readiness: as dependências respondem?

    Devolve 503 enquanto alguma estiver fora, para que a plataforma não mande
    tráfego para uma instância que ainda não consegue atender.
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
        onto = await db.ontologies.find_one({"is_active": True}, {"_id": 0, "version": 1})
        checks["ontologia_ativa"] = onto.get("version") if onto else "nenhuma"
        ok = ok and bool(onto)
    except Exception as exc:  # noqa: BLE001
        checks["ontologia_ativa"] = f"falhou: {type(exc).__name__}"
        ok = False

    try:
        checks["storage"] = {"modo": settings.STORAGE_MODE, "destino": init_storage()}
    except Exception as exc:  # noqa: BLE001
        checks["storage"] = f"falhou: {type(exc).__name__}"
        ok = False

    checks["firestore_mode"] = settings.FIRESTORE_MODE
    checks["gemini_configurado"] = bool(settings.GEMINI_API_KEY)
    ok = ok and checks["gemini_configurado"]

    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "degraded", "checks": checks},
    )


# ----------------------------------------------------------------------------
# Erros não tratados
# ----------------------------------------------------------------------------
@app.exception_handler(Exception)
async def _erro_nao_tratado(request: Request, exc: Exception) -> JSONResponse:
    """Registra o traceback no log e devolve um identificador ao cliente.

    O default do Starlette pode devolver detalhe interno na resposta. Em
    produção isso vaza caminho de arquivo e estrutura do código; aqui o cliente
    recebe apenas um id correlacionável com a entrada de log.
    """
    incidente = secrets.token_hex(8)
    logger.exception("[%s] %s %s", incidente, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno.", "incidente": incidente},
    )


if not settings.CORS_ORIGINS:
    # Só alcançável fora de produção — `settings.validar()` recusa o boot em
    # produção sem origens declaradas.
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
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)
