"""Sapiens Cognitive Annotator — FastAPI backend."""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env BEFORE local imports so modules that read env at import time
# (e.g. firestore_sync.COLLECTION_NAME) get the correct values.
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import APIRouter, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from cognitive_engine import (
    DEFAULT_PIPELINE_SCHEMA,
    parse_ontology_with_gemini,
    run_book_manifest,
    run_cognitive_pipeline,
)
from firestore_sync import (
    create_question_sync,
    delete_question_sync,
    get_status as firestore_get_status,
    sync_all_questions,
    update_question_sync,
)
from ontology_seed import DEFAULT_ONTOLOGY
from storage import build_path, get_object, init_storage, put_object

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Sapiens Cognitive Annotator")
api_router = APIRouter(prefix="/api")


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
            "version": "default-builtin",
            "name": "Schema padrão (builtin)",
            "imported_at": None,
            "source_filename": None,
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
        logger.info("Ontologia ativa: %s", existing.get("version"))
        # Backfill habilidades_observaveis on-the-fly if the active ontology was
        # imported before the field was supported and a reference JSON exists.
        try:
            await _maybe_backfill_habilidades(existing)
        except Exception as exc:  # pragma: no cover
            logger.warning("Não foi possível fazer backfill de habilidades: %s", exc)
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


async def _maybe_backfill_habilidades(active: dict[str, Any]) -> None:
    """One-shot migration for pre-existing ontologies that were imported before
    ``habilidades_observaveis`` was supported by the parser.

    If the active ontology has 0 habilidades AND a reference JSON matching its
    version exists at ``docs/ontology/ontology_v<version>.json``, copy the
    ``habilidades_observaveis`` array from that reference into the DB.
    """
    if active.get("habilidades_observaveis"):
        return
    version = str(active.get("version") or "").strip()
    if not version:
        return
    ref_paths = [
        ROOT_DIR.parent / f"docs/ontology/ontology_v{version}.json",
        ROOT_DIR.parent / "docs/ontology/ontology_v1.4.json",
    ]
    ref_path = next((p for p in ref_paths if p.exists()), None)
    if not ref_path:
        return
    try:
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Falha ao ler referência de habilidades %s: %s", ref_path, exc)
        return
    habs = ref.get("habilidades_observaveis") or []
    if not habs:
        return
    await db.ontologies.update_one(
        {"id": active["id"]},
        {"$set": {"habilidades_observaveis": habs}},
    )
    logger.info(
        "Backfill de habilidades_observaveis (%d itens) aplicado à ontologia %s",
        len(habs),
        version,
    )


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
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_ONTOLOGY_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão não suportada. Use: {sorted(ALLOWED_ONTOLOGY_EXTS)}",
        )

    data = await file.read()
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
                "ou use o botão 'Resetar para versão 1.0'."
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
    """Restaura a ontologia semente (versão 1.0.0-seed). Se já existir uma cópia
    no banco, ativa-a; caso contrário, reinsere."""
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
    """Import a custom pipeline schema from a JSON file.

    O arquivo DEVE ser um objeto JSON com pelo menos as chaves ``questao``,
    ``classificacao`` e ``meta`` (a estrutura completa que o motor cognitivo
    espera). Não valida os IDs — a ontologia continua sendo a fonte de IDs.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".json":
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos .json são aceitos para o schema.",
        )

    data = await file.read()
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
    disciplina: str | None = None
    banca: str | None = None
    ano: str | None = None
    tema: str | None = None
    resposta_correta: str | None = None
    ontology_version: str | None = None
    processos: list[str] = Field(default_factory=list)
    competencias: list[str] = Field(default_factory=list)
    dominios: list[str] = Field(default_factory=list)


def _index_fields(pipeline_json: dict) -> dict:
    """Compute indexed columns used for filtering the list view."""
    q = pipeline_json.get("questao", {}) or {}
    c = pipeline_json.get("classificacao", {}) or {}
    return {
        "disciplina": q.get("disciplina"),
        "banca": q.get("banca"),
        "ano": q.get("ano"),
        "tema": q.get("tema"),
        "resposta_correta": q.get("resposta_correta"),
        "processos": [p.get("id") for p in c.get("processos_cognitivos", []) if p.get("id")],
        "competencias": list(c.get("competencias", [])),
        "dominios": list(c.get("dominios", [])),
    }


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


@api_router.post("/pipeline/generate")
async def generate_pipeline(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    ontology = await get_active_ontology()
    schema = await get_active_schema()

    incoming: list[tuple[str, bytes, str]] = []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOWED_QUESTION_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Extensão '{ext}' não suportada. Use PDF, PNG, JPG, JPEG.",
            )
        data = await f.read()
        incoming.append((f.filename or f"file{ext}", data, MIME_BY_EXT.get(ext, "application/octet-stream")))

    # Cognitive pass
    try:
        pipeline_json = await run_cognitive_pipeline(
            ontology, [(n, d) for n, d, _ in incoming], schema=schema
        )
    except Exception as exc:
        logger.exception("Falha no pipeline cognitivo")
        raise HTTPException(status_code=502, detail=f"Falha na chamada do modelo: {exc}") from exc

    # Extraction artifact = question section of pipeline (structured extraction)
    extraction = {"questao": pipeline_json.get("questao"), "arquivos": [n for n, _, _ in incoming]}

    question_id = str(uuid.uuid4())
    artifacts = await _persist_artifacts(question_id, incoming, extraction, pipeline_json)

    indexed = _index_fields(pipeline_json)
    record = {
        "id": question_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "ontology_version": ontology.get("version"),
        "artifacts": artifacts,
        "pipeline": pipeline_json,
        **indexed,
    }
    await db.pipelines.insert_one(record)
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
            {"pipeline.questao.enunciado": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.pipelines.find(
        query,
        {
            "_id": 0,
            "id": 1,
            "created_at": 1,
            "disciplina": 1,
            "banca": 1,
            "ano": 1,
            "tema": 1,
            "resposta_correta": 1,
            "ontology_version": 1,
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
    return {"deleted": result.deleted_count}


class PipelineUpdate(BaseModel):
    pipeline: dict


@api_router.put("/pipeline/{pipeline_id}")
async def update_pipeline(pipeline_id: str, payload: PipelineUpdate) -> dict:
    existing = await db.pipelines.find_one({"id": pipeline_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado.")

    pipeline_json = payload.pipeline
    indexed = _index_fields(pipeline_json)
    update = {
        "pipeline": pipeline_json,
        "updated_at": _now_iso(),
        **indexed,
    }
    # Re-upload pipeline artifact (extraction remains untouched)
    try:
        put_object(
            existing["artifacts"]["pipeline"],
            json.dumps(pipeline_json, ensure_ascii=False, indent=2).encode(),
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

    try:
        pipeline_json = await run_cognitive_pipeline(ontology, files, schema=schema)
    except Exception as exc:
        logger.exception("Falha na regeneração")
        raise HTTPException(status_code=502, detail=f"Falha na chamada do modelo: {exc}") from exc

    put_object(
        existing["artifacts"]["pipeline"],
        json.dumps(pipeline_json, ensure_ascii=False, indent=2).encode(),
        "application/json",
    )

    indexed = _index_fields(pipeline_json)
    update = {
        "pipeline": pipeline_json,
        "updated_at": _now_iso(),
        "ontology_version": ontology.get("version"),
        **indexed,
    }
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
    return {"deleted": True, "id": pipeline_id}


# ----------------------------------------------------------------------------
# Book (caderno) endpoints — split a multi-question PDF into individual pipelines
# ----------------------------------------------------------------------------
@api_router.post("/book/upload")
async def upload_book(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    book_id = str(uuid.uuid4())
    stored: list[dict] = []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOWED_QUESTION_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Extensão '{ext}' não suportada. Use PDF, PNG, JPG, JPEG.",
            )
        data = await f.read()
        filename = f.filename or f"file{ext}"
        content_type = MIME_BY_EXT.get(ext, "application/octet-stream")
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
    }
    await db.books.insert_one(doc)
    return _clean_id({**doc})


async def _load_book_files(book_doc: dict) -> list[tuple[str, bytes, str]]:
    result: list[tuple[str, bytes, str]] = []
    for f in book_doc["files"]:
        data, _ = get_object(f["path"])
        result.append((f["filename"], data, f["content_type"]))
    return result


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

    try:
        pipeline_json = await run_cognitive_pipeline(
            ontology, files_bytes, focus_hint=focus_hint, schema=schema
        )
    except Exception as exc:
        logger.exception("Falha no pipeline (caderno)")
        raise HTTPException(status_code=502, detail=f"Falha na chamada do modelo: {exc}") from exc

    question_id = str(uuid.uuid4())
    extraction = {
        "questao": pipeline_json.get("questao"),
        "arquivos": [n for n, _, _ in incoming],
        "book_id": book_id,
        "question_number": payload.question_number,
    }
    artifacts = await _persist_artifacts(question_id, incoming, extraction, pipeline_json)

    indexed = _index_fields(pipeline_json)
    record = {
        "id": question_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "ontology_version": ontology.get("version"),
        "artifacts": artifacts,
        "pipeline": pipeline_json,
        "book_id": book_id,
        "question_number": payload.question_number,
        **indexed,
    }
    await db.pipelines.insert_one(record)
    create_question_sync(question_id, record)
    return _clean_id({**record})


@api_router.get("/book/{book_id}")
async def get_book(book_id: str) -> dict:
    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Caderno não encontrado.")
    return doc


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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
