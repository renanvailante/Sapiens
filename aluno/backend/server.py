"""Sapiens FastAPI application."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import auth as auth_module
import exam_routes as exam_module
import feed_routes as feed_module
import annotation_routes as annotation_module
import admin_routes as admin_module
import events_routes as events_module
import firestore_routes as firestore_module
from enem_seed import migrate_and_seed
from feed_seed import seed_feed
from firestore_service import seed_all_students as _firestore_seed_students

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

auth_module.set_db(db)
exam_module.set_db(db)
feed_module.set_db(db)
annotation_module.set_db(db)
admin_module.set_db(db)
events_module.set_db(db)
firestore_module.set_db(db)

app = FastAPI(title="Sapiens")
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "Sapiens", "status": "ok"}


@api_router.get("/questoes")
async def list_questoes_publico(limit: int = 100):
    """Endpoint PUBLICO (sem autenticacao) do ALUNO.
    Le APENAS a colecao filtrada 'questoes_public' do Mongo (versao sem
    metadados internos). NUNCA le do Firestore nem da colecao master.
    """
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 100
    cursor = db.questoes_public.find(
        {}, {"_id": 0, "master_id": 0}
    ).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": items, "count": len(items)}


api_router.include_router(auth_module.router)
api_router.include_router(exam_module.router)
api_router.include_router(feed_module.router)
api_router.include_router(annotation_module.router)
api_router.include_router(admin_module.router)
api_router.include_router(events_module.router)
api_router.include_router(firestore_module.router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sapiens")


@app.on_event("startup")
async def _startup():
    await migrate_and_seed(db)
    await seed_feed(db)
    # Firestore seed is best-effort: run in background with a timeout so a bad
    # Firebase credential can never block startup / freeze the event loop.
    async def _safe_firestore_seed():
        try:
            await asyncio.wait_for(_firestore_seed_students(db), timeout=20)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Firestore student seed skipped: %s", exc)
    asyncio.create_task(_safe_firestore_seed())
    logger.info("Sapiens ready.")


@app.on_event("shutdown")
async def _shutdown():
    client.close()
