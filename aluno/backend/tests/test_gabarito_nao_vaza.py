"""O gabarito nunca sai de `/api/questoes`.

Regressão real (auditoria pré-beta, 2026-09-02): o endpoint era público e
devolvia `correta` em cada alternativa. Um `curl` sem login baixava 268
questões com 267 gabaritos, e o aluno lia a resposta na aba Rede do navegador
ANTES de responder — com Sparks (moeda paga) creditados por acerto.

Estes testes travam as duas metades da correção: a projeção que remove o campo
e o portão de sessão. Rodam offline.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import server  # noqa: E402


def test_projecao_remove_o_gabarito():
    """A projeção usada na leitura precisa excluir `correta` explicitamente."""
    assert server.PROJECAO_SEM_GABARITO["questao.alternativas.correta"] == 0


def test_projecao_e_so_de_exclusao():
    """Mongo recusa projeção que mistura inclusão e exclusão; se alguém
    acrescentar um campo com 1 aqui, a rota quebra em produção, não no teste."""
    assert set(server.PROJECAO_SEM_GABARITO.values()) == {0}


def test_a_leitura_de_questoes_usa_a_projecao_sem_gabarito(monkeypatch):
    """Não basta a constante existir: a rota tem que usá-la. Captura a
    projeção realmente passada ao Mongo."""
    capturado = {}

    class _Cursor:
        def sort(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        async def to_list(self, length=None):
            return []

    class _Colecao:
        def find(self, filtro, projecao):
            capturado["projecao"] = projecao
            return _Cursor()

    class _DB:
        questoes_public = _Colecao()

    monkeypatch.setattr(server, "db", _DB())

    import asyncio

    asyncio.run(server.list_questoes_publico(limit=10, _=None))
    assert capturado["projecao"] == server.PROJECAO_SEM_GABARITO


@pytest.mark.parametrize("rota", ["list_questoes_publico", "list_provas_publico"])
def test_rotas_do_acervo_exigem_sessao(rota):
    """`require_user` precisa estar na assinatura — sem isso o acervo volta a
    ser raspável por qualquer um, mesmo sem o gabarito."""
    import inspect

    from auth import require_user

    parametros = inspect.signature(getattr(server, rota)).parameters
    dependencias = [
        p.default.dependency
        for p in parametros.values()
        if hasattr(p.default, "dependency")
    ]
    assert require_user in dependencias, f"{rota} não exige sessão"
