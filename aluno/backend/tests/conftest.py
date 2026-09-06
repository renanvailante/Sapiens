"""Dublês mínimos de Mongo (Motor) para testes offline do corretor de
redação — sem banco real, síncronos por baixo mas com a mesma interface
`async def` que o código de produção espera."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pymongo.errors import DuplicateKeyError

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


class FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs
        self._i = 0

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return list(self._docs)

    def __aiter__(self):
        self._i = 0
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._i]
        self._i += 1
        return doc


class FakeUpdateResult:
    def __init__(self, matched_count: int):
        self.matched_count = matched_count


class FakeDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class FakeCollection:
    """Suporte mínimo: find_one/update_one(upsert)/insert_one/find. Consultas
    são casamento exato de campo — suficiente para os testes deste módulo,
    que nunca fazem filtro composto complexo."""

    def __init__(self):
        self.docs: list[dict] = []

    _OPS = {
        "$in": lambda atual, alvo: atual in alvo,
        "$gt": lambda atual, alvo: atual is not None and atual > alvo,
        "$gte": lambda atual, alvo: atual is not None and atual >= alvo,
        "$lt": lambda atual, alvo: atual is not None and atual < alvo,
        "$lte": lambda atual, alvo: atual is not None and atual <= alvo,
        "$ne": lambda atual, alvo: atual != alvo,
    }

    def _bate(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if isinstance(v, dict) and any(op in v for op in self._OPS):
                for op, esperado in v.items():
                    if not self._OPS[op](doc.get(k), esperado):
                        return False
            elif doc.get(k) != v:
                return False
        return True

    async def find_one(self, query: dict, projection: dict | None = None, sort=None):
        candidatos = [d for d in self.docs if self._bate(d, query)]
        if sort:
            for campo, direcao in reversed(list(sort)):
                candidatos.sort(key=lambda d: d.get(campo) or "", reverse=direcao < 0)
        return dict(candidatos[0]) if candidatos else None

    async def insert_one(self, doc: dict):
        """Aplica a unicidade de `_id` do Mongo real. Sem isto, o dublê
        aceitaria duas reivindicações com a mesma chave e os testes de
        idempotência de `redacao_routes` passariam sem provar nada — a
        garantia inteira depende de `DuplicateKeyError` acontecer."""
        _id = doc.get("_id")
        if _id is not None and any(d.get("_id") == _id for d in self.docs):
            raise DuplicateKeyError(f"E11000 duplicate key error: _id {_id!r}")
        self.docs.append(dict(doc))

    async def find_one_and_update(self, query: dict, update: dict, return_document=True, **kwargs):
        for doc in self.docs:
            if self._bate(doc, query):
                doc.update(update.get("$set", {}))
                return dict(doc)
        return None

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        for doc in self.docs:
            if self._bate(doc, query):
                doc.update(update.get("$set", {}))
                for campo, valor in (update.get("$push") or {}).items():
                    lista = doc.setdefault(campo, [])
                    lista.extend(valor["$each"] if isinstance(valor, dict) and "$each" in valor else [valor])
                return FakeUpdateResult(matched_count=1)
        if upsert:
            novo = dict(query)
            novo.update(update.get("$set", {}))
            self.docs.append(novo)
            return FakeUpdateResult(matched_count=0)
        return FakeUpdateResult(matched_count=0)

    async def delete_many(self, query: dict):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not self._bate(d, query)]
        return FakeDeleteResult(antes - len(self.docs))

    async def delete_one(self, query: dict):
        for i, d in enumerate(self.docs):
            if self._bate(d, query):
                del self.docs[i]
                return FakeDeleteResult(1)
        return FakeDeleteResult(0)

    def find(self, query: dict | None = None, projection: dict | None = None):
        query = query or {}
        return FakeCursor([d for d in self.docs if self._bate(d, query)])


class FakeDB:
    def __init__(self):
        self._colecoes: dict[str, FakeCollection] = {}

    def __getattr__(self, nome: str) -> FakeCollection:
        return self._colecoes.setdefault(nome, FakeCollection())


@pytest.fixture
def fake_db() -> FakeDB:
    return FakeDB()
