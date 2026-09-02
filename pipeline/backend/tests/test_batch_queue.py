"""Testes da fila de lote (`batch_queue.py`) contra um Mongo local real.

Segue o padrão de `test_bulk_pipelines.py`/`test_firestore_sync.py`: Mongo de
verdade (precisa estar rodando em `MONGO_URL`), banco isolado e limpo antes/
depois de cada teste. O Gemini nunca é chamado de verdade —
`annotation_pipeline.run_cognitive_pipeline` é substituído por um dublê, e o
storage de artefatos aponta para um diretório temporário.

O espelho Firestore é sempre stubado (ver `_no_real_firestore` abaixo):
o `.env` deste projeto roda com `FIRESTORE_MODE=admin` mesmo em
desenvolvimento (aponta para o projeto real), então depender do valor do
`.env` para "ficar em mock" seria falso neste ambiente e escreveria
documentos de teste no Firestore de verdade.

Nota (auditoria de custo, 2ª rodada): `annotation_pipeline.generate_and_persist`
chama `run_cognitive_pipeline_adaptive` (não mais `run_cognitive_pipeline`
diretamente) — os dublês abaixo substituem esse nome e devolvem a tupla
`(raw, meta)` que a função adaptativa devolve.
"""
from __future__ import annotations

import asyncio
import copy
import os
import sys
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017")
TEST_DB_NAME = "sapiens_pipeline_test_batch_queue"

import annotation_pipeline  # noqa: E402
import batch_queue  # noqa: E402
import storage  # noqa: E402
from cognitive_engine import DEFAULT_PIPELINE_SCHEMA, GeminiQuotaExhaustedError  # noqa: E402
from ontology_seed import DEFAULT_ONTOLOGY  # noqa: E402


@pytest.fixture(autouse=True)
def _no_real_firestore(monkeypatch):
    """Nunca chamar o Firestore de verdade a partir destes testes.

    O `.env` deste projeto roda com `FIRESTORE_MODE=admin` (espelho real,
    mesmo em desenvolvimento) — sem este stub, todo teste que chega ao
    caminho de sucesso escreveria um documento de teste na coleção `itens`
    real. `annotation_pipeline.create_question_sync` é o nome importado que
    o código de produção chama; substituí-lo aqui é suficiente e não exige
    tocar `firestore_sync.py`.
    """
    monkeypatch.setattr(annotation_pipeline, "create_question_sync", lambda *a, **k: True)


def _raw_item_valido() -> dict:
    """Exemplo 3 do Manual §9 (mesmo usado em test_contratos_canonicos.py) —
    já comprovado válido contra `normalize_item`/`validate_item_annotation`."""
    return {
        "fonte": {"banca": "INEP", "ano": 2024, "prova": "ENEM-CAD01", "numero": 23,
                  "disciplina": "Química", "tema": "Cinética química"},
        "questao": {
            "enunciado": "O gráfico mostra a concentração do reagente ao longo do tempo.",
            "alternativas": [
                {"letra": "A", "texto": "0,5 mol", "correta": False},
                {"letra": "B", "texto": "1,0 mol", "correta": True},
                {"letra": "C", "texto": "2,0 mol", "correta": False},
            ],
            "recursos": {"graficos": [{"id": "GRA-01", "descricao": "concentração x tempo"}]},
        },
        "estrutura_cognitiva": {
            "processos": [
                {
                    "id": "PROC-QUANT-02", "papel": "nuclear", "peso_no_item": 0.7,
                    "confianca": "alta",
                    "habilidades": [{"id": "HAB-03", "peso_no_processo": 1.0,
                                     "confianca": "alta", "aproximado": False}],
                    "evidencias": {"trechos": ["quantidade de produto formado"],
                                   "figuras": ["GRA-01"]},
                    "justificativa": "A resposta exige aplicar relação proporcional "
                                     "sobre o valor lido no gráfico.",
                },
            ]
        },
        "distratores": [],
        "intervencoes": [],
    }


def _loop() -> asyncio.AbstractEventLoop:
    """Um loop por thread, reaproveitado entre chamadas.

    Não usa `asyncio.run()`: ele fecha o loop ao final de CADA chamada, e o
    `AsyncIOMotorClient` criado no setup do fixture precisa do MESMO loop
    vivo durante todo o teste (é a ele que sua pool de conexões fica presa).
    `get_event_loop()` também não serve sozinho — no Python 3.12, sem loop
    corrente ele levanta `RuntimeError` em vez de criar um; daí o fallback.
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


@pytest.fixture
def db(monkeypatch, tmp_path):
    """Banco Mongo privado por teste (nome com uuid), nunca compartilhado.

    `pytest.ini` roda com `-n 2 --dist loadscope`, que agrupa por CLASSE, não
    por módulo — duas classes deste arquivo podem rodar em workers diferentes
    ao mesmo tempo. Um nome de banco fixo + `delete_many({})` no setup fazia
    um worker apagar o item que o outro tinha acabado de inserir. Um banco
    novo por teste elimina a corrida por construção, em vez de torcer para
    que a ordem de execução salve o resultado.
    """
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path / "_storage")
    db_name = f"{TEST_DB_NAME}_{uuid.uuid4().hex[:12]}"

    async def _fresh():
        cli = AsyncIOMotorClient(MONGO_URL)
        return cli, cli[db_name]

    cli, database = _loop().run_until_complete(_fresh())
    yield database

    async def _cleanup():
        await cli.drop_database(db_name)
        cli.close()

    _loop().run_until_complete(_cleanup())


def _run(coro):
    return _loop().run_until_complete(coro)


def _some_file() -> list[tuple[str, bytes, str]]:
    return [("questao23.png", b"fake-png-bytes", "image/png")]


class TestEnqueue:
    def test_enqueue_grava_item_pendente_com_arquivos_no_storage(self, db):
        item_id = _run(batch_queue.enqueue(db, files=_some_file()))

        doc = _run(db.pipeline_queue.find_one({"id": item_id}))
        assert doc["status"] == "pending"
        assert doc["attempts"] == 0
        assert len(doc["files"]) == 1

        data, content_type = storage.get_object(doc["files"][0]["path"])
        assert data == b"fake-png-bytes"
        assert content_type == "image/png"


class TestDrainSucesso:
    def test_drain_processa_item_e_marca_succeeded(self, db, monkeypatch):
        async def _fake_run_cognitive_pipeline_adaptive(*args, **kwargs):
            return copy.deepcopy(_raw_item_valido()), {"attempts": ["LOW"], "escalated": False}

        monkeypatch.setattr(
            annotation_pipeline, "run_cognitive_pipeline_adaptive", _fake_run_cognitive_pipeline_adaptive
        )

        item_id = _run(batch_queue.enqueue(db, files=_some_file()))
        summary = _run(batch_queue.drain(
            db, ontology=DEFAULT_ONTOLOGY, schema=DEFAULT_PIPELINE_SCHEMA, limit=10,
        ))

        assert summary == {
            "processed": 1, "succeeded": 1, "requeued": 0, "dead_letter": 0,
            "quota_exhausted": False, "quota_id": None, "retry_delay_seconds": None,
        }
        doc = _run(db.pipeline_queue.find_one({"id": item_id}))
        assert doc["status"] == "succeeded"
        assert doc["result_pipeline_id"]

        pipeline_doc = _run(db.pipelines.find_one({"id": doc["result_pipeline_id"]}))
        assert pipeline_doc["schema_version"] == "2.2"

        # O staging da fila (queue/{item_id}) não serve mais a nada depois do
        # sucesso — o conteúdo já foi persistido (deduplicado) no artefato
        # final — e não deve ficar órfão para sempre.
        assert not storage.object_exists(doc["files"][0]["path"])

    def test_drain_sem_itens_devidos_nao_faz_nada(self, db):
        summary = _run(batch_queue.drain(
            db, ontology=DEFAULT_ONTOLOGY, schema=DEFAULT_PIPELINE_SCHEMA, limit=10,
        ))
        assert summary["processed"] == 0


class TestDrainFalhaTransiente:
    def test_falha_reagenda_ate_esgotar_tentativas_depois_dead_letter(self, db, monkeypatch):
        async def _fake_falha(*args, **kwargs):
            raise RuntimeError("503 simulado")

        monkeypatch.setattr(annotation_pipeline, "run_cognitive_pipeline_adaptive", _fake_falha)

        item_id = _run(batch_queue.enqueue(db, files=_some_file(), max_attempts=2))

        # Tentativa 1: falha, deveria reagendar (não é a última tentativa).
        summary1 = _run(batch_queue.drain(
            db, ontology=DEFAULT_ONTOLOGY, schema=DEFAULT_PIPELINE_SCHEMA, limit=10,
        ))
        assert summary1["requeued"] == 1
        doc = _run(db.pipeline_queue.find_one({"id": item_id}))
        assert doc["status"] == "pending"
        assert doc["attempts"] == 1
        # Força o item a já estar no prazo, sem esperar o backoff real.
        _run(db.pipeline_queue.update_one({"id": item_id}, {"$set": {"next_attempt_at": doc["updated_at"]}}))

        # Tentativa 2 (última, max_attempts=2): dead_letter.
        summary2 = _run(batch_queue.drain(
            db, ontology=DEFAULT_ONTOLOGY, schema=DEFAULT_PIPELINE_SCHEMA, limit=10,
        ))
        assert summary2["dead_letter"] == 1
        doc = _run(db.pipeline_queue.find_one({"id": item_id}))
        assert doc["status"] == "dead_letter"
        assert doc["attempts"] == 2
        assert "503 simulado" in doc["last_error"]


class TestDrainCotaDiariaEsgotada:
    def test_para_o_dreno_sem_consumir_tentativa_do_item(self, db, monkeypatch):
        async def _fake_quota(*args, **kwargs):
            raise GeminiQuotaExhaustedError(
                "GenerateRequestsPerDayPerProjectPerModel-FreeTier", 120.0, RuntimeError("429"),
            )

        monkeypatch.setattr(annotation_pipeline, "run_cognitive_pipeline_adaptive", _fake_quota)

        item_a = _run(batch_queue.enqueue(db, files=_some_file()))
        item_b = _run(batch_queue.enqueue(db, files=_some_file()))

        summary = _run(batch_queue.drain(
            db, ontology=DEFAULT_ONTOLOGY, schema=DEFAULT_PIPELINE_SCHEMA, limit=10,
        ))

        assert summary["processed"] == 1
        assert summary["quota_exhausted"] is True
        assert summary["quota_id"] == "GenerateRequestsPerDayPerProjectPerModel-FreeTier"

        doc_a = _run(db.pipeline_queue.find_one({"id": item_a}))
        assert doc_a["status"] == "pending"
        assert doc_a["attempts"] == 0  # não consumiu tentativa — a culpa é da cota, não do item

        # O segundo item nem chegou a ser reivindicado.
        doc_b = _run(db.pipeline_queue.find_one({"id": item_b}))
        assert doc_b["status"] == "pending"


class TestStatusERequeue:
    def test_status_agrega_por_situacao(self, db):
        _run(batch_queue.enqueue(db, files=_some_file()))
        result = _run(batch_queue.status(db))
        assert result["counts"] == {"pending": 1}

    def test_requeue_devolve_item_dead_letter_para_pending(self, db):
        item_id = _run(batch_queue.enqueue(db, files=_some_file()))
        _run(db.pipeline_queue.update_one(
            {"id": item_id}, {"$set": {"status": "dead_letter", "attempts": 5, "last_error": "x"}},
        ))

        ok = _run(batch_queue.requeue(db, item_id))
        assert ok is True

        doc = _run(db.pipeline_queue.find_one({"id": item_id}))
        assert doc["status"] == "pending"
        assert doc["attempts"] == 0
        assert doc["last_error"] is None

    def test_requeue_item_inexistente_devolve_false(self, db):
        assert _run(batch_queue.requeue(db, "nao-existe")) is False
