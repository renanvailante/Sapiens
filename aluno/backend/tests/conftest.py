"""Dublês mínimos de Mongo (Motor) para testes offline do corretor de
redação — sem banco real, síncronos por baixo mas com a mesma interface
`async def` que o código de produção espera."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


class FakeCollection:
    """Suporte mínimo: find_one/update_one(upsert)/insert_one/find. Consultas
    são casamento exato de campo — suficiente para os testes deste módulo,
    que nunca fazem filtro composto complexo."""

    def __init__(self):
        self.docs: list[dict] = []

    def _bate(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if isinstance(v, dict) and "$in" in v:
                if doc.get(k) not in v["$in"]:
                    return False
            elif doc.get(k) != v:
                return False
        return True

    async def find_one(self, query: dict, projection: dict | None = None):
        for doc in self.docs:
            if self._bate(doc, query):
                return dict(doc)
        return None

    async def insert_one(self, doc: dict):
        self.docs.append(dict(doc))

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        for doc in self.docs:
            if self._bate(doc, query):
                doc.update(update.get("$set", {}))
                return FakeUpdateResult(matched_count=1)
        if upsert:
            novo = dict(query)
            novo.update(update.get("$set", {}))
            self.docs.append(novo)
            return FakeUpdateResult(matched_count=0)
        return FakeUpdateResult(matched_count=0)

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
