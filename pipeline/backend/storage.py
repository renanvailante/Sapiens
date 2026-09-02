"""Armazenamento de artefatos binários do pipeline (originais, extração, anotação).

Substitui o Object Storage da Emergent, removido da plataforma. Dois backends,
selecionados por ``STORAGE_MODE``:

* ``local`` (padrão) — sistema de arquivos, sob ``STORAGE_ROOT``. Não exige
  nenhuma infraestrutura externa; é o que faz o pipeline rodar numa máquina de
  desenvolvimento sem credencial nenhuma.
* ``firebase`` — Firebase Storage (bucket do GCS), pelo mesmo
  ``firebase_admin`` e pela mesma credencial de serviço que o espelho Firestore
  já usa. Sem novo fornecedor, sem nova chave.

O mesmo par de eixos que ``firestore_sync`` já adota (backend plugável +
variável de ambiente), por consistência com o que existe.

Nenhum caminho de objeto mudou: ``build_path`` produz exatamente a mesma
namespace de antes, então artefatos já gravados continuam localizáveis quando
migrados para o novo backend.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = os.environ.get("APP_NAME", "sapiens-cognitive")
STORAGE_MODE = os.environ.get("STORAGE_MODE", "local").lower()
STORAGE_ROOT = Path(
    os.environ.get("STORAGE_ROOT") or (Path(__file__).resolve().parent / "_storage")
)
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET")

_CONTENT_TYPE_SIDECAR = ".content-type"


# ---------------------------------------------------------------------------
# Backend: sistema de arquivos
# ---------------------------------------------------------------------------
def _local_path(path: str) -> Path:
    """Resolve um caminho lógico para o disco, sem permitir escapar da raiz.

    `path` vem de `build_path`, que compõe nomes de arquivo enviados pelo
    usuário. Um `..` ali escreveria fora da árvore de storage — daí a
    verificação explícita em vez de confiança no formato.
    """
    root = STORAGE_ROOT.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Caminho de objeto fora da raiz de storage: {path!r}")
    return target


def _local_put(path: str, data: bytes, content_type: str) -> dict:
    target = _local_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    # O filesystem não guarda content-type; um sidecar preserva o que o
    # download precisa devolver, sem depender de adivinhação por extensão.
    target.with_suffix(target.suffix + _CONTENT_TYPE_SIDECAR).write_text(
        content_type, encoding="utf-8"
    )
    return {"path": path, "size": len(data), "content_type": content_type}


def _local_get(path: str) -> tuple[bytes, str]:
    target = _local_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"Objeto não encontrado: {path}")
    sidecar = target.with_suffix(target.suffix + _CONTENT_TYPE_SIDECAR)
    content_type = (
        sidecar.read_text(encoding="utf-8").strip()
        if sidecar.is_file()
        else "application/octet-stream"
    )
    return target.read_bytes(), content_type


def _local_delete_prefix(prefix: str) -> int:
    target = _local_path(prefix)
    if not target.exists():
        return 0
    count = sum(1 for p in target.rglob("*") if p.is_file() and not p.name.endswith(_CONTENT_TYPE_SIDECAR))
    shutil.rmtree(target)
    return count


# ---------------------------------------------------------------------------
# Backend: Firebase Storage (GCS)
# ---------------------------------------------------------------------------
def _bucket():
    import firebase_admin
    from firebase_admin import credentials, storage as fb_storage

    try:
        app = firebase_admin.get_app()
    except ValueError:
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get(
            "FIREBASE_SERVICE_ACCOUNT_PATH"
        )
        if not cred_path:
            raise RuntimeError(
                "STORAGE_MODE=firebase exige GOOGLE_APPLICATION_CREDENTIALS "
                "(ou FIREBASE_SERVICE_ACCOUNT_PATH)."
            )
        options = {}
        if FIREBASE_STORAGE_BUCKET:
            options["storageBucket"] = FIREBASE_STORAGE_BUCKET
        app = firebase_admin.initialize_app(credentials.Certificate(cred_path), options)
    return fb_storage.bucket(FIREBASE_STORAGE_BUCKET, app=app)


def _fb_put(path: str, data: bytes, content_type: str) -> dict:
    blob = _bucket().blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return {"path": path, "size": len(data), "content_type": content_type}


def _fb_get(path: str) -> tuple[bytes, str]:
    blob = _bucket().blob(path)
    if not blob.exists():
        raise FileNotFoundError(f"Objeto não encontrado: {path}")
    data = blob.download_as_bytes()
    blob.reload()
    return data, blob.content_type or "application/octet-stream"


def _fb_delete_prefix(prefix: str) -> int:
    bucket = _bucket()
    blobs = list(bucket.list_blobs(prefix=prefix))
    for b in blobs:
        b.delete()
    return len(blobs)


def _fb_exists(path: str) -> bool:
    return _bucket().blob(path).exists()


# ---------------------------------------------------------------------------
# API pública — inalterada
# ---------------------------------------------------------------------------
def init_storage() -> str:
    """Prepara o backend. Chamado uma vez no startup.

    Não faz chamada de rede no modo local; no modo firebase apenas resolve o
    bucket, para que uma credencial ausente falhe no boot em vez de na primeira
    geração de item.
    """
    if STORAGE_MODE == "firebase":
        bucket = _bucket()
        logger.info("Object storage: Firebase Storage · bucket=%s", bucket.name)
        return bucket.name
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    logger.info("Object storage: filesystem · root=%s", STORAGE_ROOT)
    return str(STORAGE_ROOT)


def put_object(path: str, data: bytes, content_type: str) -> dict:
    if STORAGE_MODE == "firebase":
        return _fb_put(path, data, content_type)
    return _local_put(path, data, content_type)


def get_object(path: str) -> tuple[bytes, str]:
    if STORAGE_MODE == "firebase":
        return _fb_get(path)
    return _local_get(path)


def object_exists(path: str) -> bool:
    if STORAGE_MODE == "firebase":
        return _fb_exists(path)
    return _local_path(path).is_file()


def delete_prefix(prefix: str) -> int:
    """Remove todos os objetos sob um prefixo. Devolve quantos foram removidos."""
    if STORAGE_MODE == "firebase":
        return _fb_delete_prefix(prefix)
    return _local_delete_prefix(prefix)


def build_prefix(kind: str, question_id: str) -> str:
    """Prefixo (sem nome de arquivo) do mesmo namespace usado por `build_path`."""
    return f"{APP_NAME}/questions/{question_id}/{kind}"


def build_path(kind: str, question_id: str, filename: str) -> str:
    """Namespace: {app}/questions/{question_id}/{kind}/{filename}."""
    return f"{build_prefix(kind, question_id)}/{filename}"


def build_blob_path(data: bytes, filename: str) -> str:
    """Caminho endereçado por conteúdo (sha256), para artefatos-fonte.

    Usado para os arquivos originais (PDF/imagem) de uma questão: o mesmo
    caderno é recarregado e re-persistido a cada questão extraída dele
    (`/book/{id}/process`), e o mesmo arquivo enfileirado é persistido de novo
    ao sair da fila (`batch_queue` → `annotation_pipeline.persist_artifacts`).
    Endereçar pelo hash do conteúdo, em vez de por `question_id`, faz bytes
    idênticos caírem no mesmo objeto em vez de uma cópia nova a cada vez —
    ver auditoria de custo de imagem, 90 cópias de 3.7MB do mesmo caderno.
    """
    digest = hashlib.sha256(data).hexdigest()
    ext = Path(filename).suffix
    return f"{APP_NAME}/blobs/{digest}{ext}"


def put_object_deduped(data: bytes, content_type: str, filename: str) -> dict:
    """Como `put_object`, mas grava uma única vez por conteúdo distinto.

    Se bytes idênticos já foram gravados (mesmo hash), reaproveita o objeto
    existente em vez de regravar — sem exigir que quem chama saiba disso.
    """
    path = build_blob_path(data, filename)
    if object_exists(path):
        return {"path": path, "size": len(data), "content_type": content_type, "deduped": True}
    result = put_object(path, data, content_type)
    result["deduped"] = False
    return result
