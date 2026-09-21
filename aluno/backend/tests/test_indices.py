"""Criação de índices no startup — nunca aborta, e não mente sobre falha.

O contador de falhas é o que um deploy olha para saber se ficou algo sem
trava. Um conflito de NOME com um índice equivalente (criado antes deste
módulo existir) não é falha; um índice com as mesmas chaves mas sem `unique`
é, porque aí a garantia não existe.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import db_indexes  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class _Colecao:
    """`erro_em` limita a falha ao índice daquele nome — sem isso o dublê
    derrubaria também o TTL da mesma coleção, que não tem equivalente e viraria
    uma falha legítima, mascarando o que o teste quer medir."""

    def __init__(self, existentes=None, erro=None, erro_em=None):
        self.existentes = existentes or {}
        self.erro = erro
        self.erro_em = erro_em

    async def create_index(self, chaves, **kwargs):
        if self.erro and (self.erro_em is None or kwargs.get("name") == self.erro_em):
            raise self.erro
        return kwargs.get("name")

    async def index_information(self):
        return self.existentes


class _DB:
    def __init__(self, colecoes):
        self.colecoes = colecoes

    def __getitem__(self, nome):
        return self.colecoes.get(nome, _Colecao())


class _ColecaoRedefinida:
    """Um índice que já existe com o mesmo NOME e as mesmas chaves, mas com as
    opções antigas: `create_index` conflita até o índice ser derrubado."""

    def __init__(self, nome, info):
        self.nome = nome
        self.info = info
        self.derrubados = []

    async def create_index(self, chaves, **kwargs):
        if kwargs.get("name") == self.nome and self.nome not in self.derrubados:
            raise Exception("IndexOptionsConflict: an existing index has the same name")
        return kwargs.get("name")

    async def drop_index(self, nome):
        self.derrubados.append(nome)

    async def index_information(self):
        if self.nome in self.derrubados:
            return {}
        return {self.nome: self.info}


def test_referral_code_e_unico_so_para_codigo_de_verdade():
    """Regressão do cadastro quebrado (2026-09-21).

    `sparse` pula só o documento em que o campo está AUSENTE — o que está
    presente valendo `null` é indexado como qualquer outro. Como
    `User.model_dump()` grava `referral_code: None` em toda conta nova, o
    primeiro cadastro ficava com o valor nulo e todos os seguintes morriam com
    `DuplicateKeyError` dentro de `auth.signup`, pelos dois caminhos (e-mail e
    Google). A unicidade tem de valer só para o código de verdade.
    """
    kwargs = [kw for col, chaves, kw in db_indexes.INDICES
              if col == "users" and [k for k, _ in chaves] == ["referral_code"]]
    assert len(kwargs) == 1
    assert kwargs[0]["unique"] is True
    assert not kwargs[0].get("sparse")
    assert kwargs[0]["partialFilterExpression"] == {"referral_code": {"$type": "string"}}


def test_indice_redefinido_sob_o_mesmo_nome_e_derrubado_e_recriado():
    """Mudar a definição de um índice aqui não conserta banco nenhum que já
    rodou: o Mongo recusa redefinir um índice existente, e recusaria de novo em
    todo boot seguinte. Foi o que manteve `referral_code_unico` esparso em
    produção com o cadastro quebrado do outro lado."""
    antigo = _ColecaoRedefinida(
        "referral_code_unico",
        {"key": [("referral_code", 1)], "unique": True, "sparse": True},
    )
    resultado = _run(db_indexes.criar_indices(_DB({"users": antigo})))
    assert antigo.derrubados == ["referral_code_unico"]
    assert resultado["falhas"] == 0
    assert resultado["criados"] == len(db_indexes.INDICES)


def test_todos_os_indices_criados_sem_falha():
    resultado = _run(db_indexes.criar_indices(_DB({})))
    assert resultado["falhas"] == 0
    assert resultado["criados"] == len(db_indexes.INDICES)


def test_conflito_de_nome_com_indice_equivalente_nao_conta_falha():
    """Caso real: `webhook_events.dedupe_key` já existia como `dedupe_key_1`,
    único. A trava está de pé — só o nome diverge."""
    conflito = _Colecao(
        existentes={"dedupe_key_1": {"key": [("dedupe_key", 1)], "unique": True}},
        erro=Exception("Index already exists with a different name: dedupe_key_1"),
        erro_em="dedupe_key_unico",
    )
    resultado = _run(db_indexes.criar_indices(_DB({"webhook_events": conflito})))
    assert resultado["falhas"] == 0
    assert resultado["criados"] == len(db_indexes.INDICES)


def test_indice_existente_sem_unique_continua_sendo_falha():
    """A trava de verdade é o `unique`. Se o que existe não é único, o dedupe
    do webhook não existe — e isso NÃO pode ser contado como sucesso."""
    sem_unique = _Colecao(
        existentes={"dedupe_key_1": {"key": [("dedupe_key", 1)], "unique": False}},
        erro=Exception("Index already exists with a different name: dedupe_key_1"),
        erro_em="dedupe_key_unico",
    )
    resultado = _run(db_indexes.criar_indices(_DB({"webhook_events": sem_unique})))
    assert resultado["falhas"] > 0


def test_falha_de_indice_nao_derruba_o_processo():
    """Um índice ausente deixa o app lento ou sem uma trava; subir sem app
    nenhum é pior."""
    quebrada = _Colecao(erro=Exception("dado duplicado viola o índice único"), erro_em="email_unico")
    resultado = _run(db_indexes.criar_indices(_DB({"users": quebrada})))
    assert resultado["falhas"] > 0  # registra, mas não levanta


def test_travas_criticas_estao_declaradas():
    """As três que sustentam garantias de segurança/dinheiro."""
    unicos = {
        (col, tuple(k for k, _ in chaves))
        for col, chaves, kw in db_indexes.INDICES if kw.get("unique")
    }
    assert ("user_sessions", ("session_token",)) in unicos
    assert ("users", ("email",)) in unicos
    assert ("webhook_events", ("dedupe_key",)) in unicos
    assert ("sparks_payments", ("mp_payment_id",)) in unicos
