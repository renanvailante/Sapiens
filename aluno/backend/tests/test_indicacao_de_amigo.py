"""Indicação de amigo: o código pessoal, o vínculo no cadastro e o prêmio da
primeira compra.

A regra do produto, inteira: cada aluno tem um código; quem se cadastra com
ele fica ligado a quem indicou; na PRIMEIRA compra do indicado, o indicador
recebe metade dos Sparks daquela compra — uma vez, nunca mais.

Os quatro pontos que estes testes existem para travar:

1. **"Metade" sai do pacote do servidor**, não de nada que o cliente mande.
2. **"Primeira" é primeira mesmo.** A segunda compra do mesmo indicado não
   paga de novo, nem que o webhook chegue de outro jeito.
3. **Reenvio do MESMO webhook não paga duas vezes** — e também não pode
   TRAVAR o prêmio se o processo tiver morrido no meio do caminho anterior.
4. **Código de indicação não invade o território do cupom.** Um cupom ativo
   com o mesmo texto continua sendo cupom, e o vínculo não acontece.

Offline, com o dublê de Mongo do `conftest.py`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import Response

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import auth  # noqa: E402
import firestore_service as fs  # noqa: E402
import indicacoes  # noqa: E402
import indicacoes_routes  # noqa: E402
import promo_codes_routes as promo  # noqa: E402
import rate_limit  # noqa: E402
import sparks_payments_service as svc  # noqa: E402
from models import SignupRequest, User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _sem_limites_residuais():
    rate_limit.limpar()
    yield
    rate_limit.limpar()


@pytest.fixture
def db(fake_db, monkeypatch):
    auth.set_db(fake_db)
    promo.set_db(fake_db)
    indicacoes_routes.set_db(fake_db)
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
    return fake_db


@pytest.fixture
def creditos(monkeypatch):
    """Espião do único caminho que move Spark: `grant_sparks_evento`.

    Guarda `(uid, chave, valor)` e devolve `ja_concedido` para a MESMA chave,
    que é a garantia real do Firestore em produção (`_conceder_sparks_atomico`)
    — sem reproduzi-la aqui, o teste de reenvio passaria sem provar nada.
    """
    registros: list[tuple[str, str, int]] = []
    concedidas: set[tuple[str, str]] = set()

    def falso(uid, *, categoria, chave, amount, meta=None):
        if (uid, chave) in concedidas:
            return {"ja_concedido": True, "sparks_ganhos": 0}
        concedidas.add((uid, chave))
        registros.append((uid, chave, amount))
        return {"ja_concedido": False, "sparks_ganhos": amount}

    monkeypatch.setattr(fs, "grant_sparks_evento", falso)
    return registros


def _cadastrar(db, email: str, nome: str = "Amigo Novo", codigo: str | None = None) -> dict:
    _run(auth.signup(
        SignupRequest(
            email=email, name=nome, password="senha-forte-1",
            whatsapp="(11) 91234-5678", promo_code=codigo,
        ),
        Response(),
    ))
    return _run(db.users.find_one({"email": email}))


def _indicador(db, nome: str = "Renan Vailante") -> tuple[str, str]:
    """Cria a conta de quem indica e devolve `(user_id, codigo)`."""
    conta = _cadastrar(db, "indicador@x.com", nome)
    codigo = _run(indicacoes.garantir_codigo(db, conta["user_id"], nome))
    return conta["user_id"], codigo


def _pagar(db, comprador_id: str, mp_id: str, package_id: str, sparks: int, monkeypatch):
    monkeypatch.setattr(
        svc.mp, "get_payment",
        lambda pid: {"id": pid, "status": "approved", "metadata": {}},
    )
    monkeypatch.setattr(
        svc.fs, "grant_purchase_sparks",
        lambda uid, **k: {"ja_creditado": False},
    )
    _run(db.sparks_payments.insert_one({
        "purchase_id": f"compra-{mp_id}", "user_id": comprador_id, "package_id": package_id,
        "sparks_amount": sparks, "price_cents": 0, "currency": "BRL", "source": "manual",
        "mp_payment_id": mp_id, "status": "pending", "credited": False,
    }))
    return _run(svc.process_payment_webhook(db, mp_id))


# ============================================================ o código

class TestCodigoPessoal:
    def _conta(self, db, user_id: str = "u1", nome: str = "Ana") -> str:
        _run(db.users.insert_one({"user_id": user_id, "name": nome, "email": f"{user_id}@x.com"}))
        return user_id

    def test_o_codigo_comeca_pelo_primeiro_nome(self, db):
        self._conta(db, "u1", "Renan Vailante")
        codigo = _run(indicacoes.garantir_codigo(db, "u1", "Renan Vailante"))
        assert codigo.startswith("RENAN")
        assert len(codigo) == len("RENAN") + 4

    def test_o_codigo_nao_usa_caracteres_ambiguos(self, db):
        """Ele é lido em voz alta e digitado a partir de um print: I/O/0/1 não
        podem existir no sufixo sorteado."""
        for i in range(60):
            self._conta(db, f"u{i}")
            codigo = _run(indicacoes.garantir_codigo(db, f"u{i}", "Ana"))
            assert not (set(codigo[len("ANA"):]) & set("IO01"))

    def test_perguntar_duas_vezes_devolve_o_mesmo_codigo(self, db):
        self._conta(db)
        primeiro = _run(indicacoes.garantir_codigo(db, "u1", "Ana"))
        segundo = _run(indicacoes.garantir_codigo(db, "u1", "Ana"))
        assert primeiro == segundo

    def test_nome_sem_letra_nenhuma_nao_gera_codigo_vazio(self, db):
        self._conta(db, "u1", "🙂 123")
        codigo = _run(indicacoes.garantir_codigo(db, "u1", "🙂 123"))
        assert codigo.startswith("AMIGO")

    def test_conta_inexistente_falha_alto_em_vez_de_inventar_codigo(self, db):
        """Um código não gravado é pior que um erro: o amigo se cadastraria com
        ele, `resolver_indicador` não acharia dono nenhum, e o prêmio sumiria
        em silêncio."""
        with pytest.raises(indicacoes.ContaSemCadastro):
            _run(indicacoes.garantir_codigo(db, "fantasma", "Ana"))

    def test_codigo_nunca_nasce_igual_a_um_cupom_do_catalogo(self, db, monkeypatch):
        """Os dois moram no MESMO campo do cadastro e o cupom tem precedência.
        Um código de indicação que repetisse um cupom ativo seria sempre lido
        como cupom, e o indicador nunca receberia nada."""
        self._conta(db)
        _run(db.promo_codes.insert_one({"code": "ANAXXXX", "sparks_amount": 500, "active": True}))
        sorteios = iter(["ANAXXXX", "ANAYYYY"])
        monkeypatch.setattr(indicacoes, "_sortear", lambda nome, tamanho=4: next(sorteios))
        assert _run(indicacoes.garantir_codigo(db, "u1", "Ana")) == "ANAYYYY"


# ======================================================= vínculo no cadastro

class TestVinculoNoCadastro:
    def test_cadastro_com_codigo_de_amigo_grava_o_vinculo(self, db):
        indicador_id, codigo = _indicador(db)
        conta = _cadastrar(db, "amigo@x.com", "Amigo Novo", codigo)

        assert conta["indicado_por"] == indicador_id
        vinculo = _run(db.indicacoes.find_one({"indicado_id": conta["user_id"]}))
        assert vinculo["indicador_id"] == indicador_id
        assert vinculo["premio_em"] is None

    def test_o_codigo_pode_ser_digitado_em_minusculas(self, db):
        indicador_id, codigo = _indicador(db)
        conta = _cadastrar(db, "amigo@x.com", "Amigo", f"  {codigo.lower()} ")
        assert conta["indicado_por"] == indicador_id

    def test_codigo_inexistente_nao_barra_o_cadastro(self, db):
        conta = _cadastrar(db, "amigo@x.com", "Amigo", "NAOEXISTE")
        assert conta["indicado_por"] is None
        assert conta["promo_code"] is None

    def test_cupom_do_catalogo_tem_precedencia_e_nao_vira_indicacao(self, db):
        """Mesmo campo, duas leituras. Se um cupom ativo casou, o texto era
        cupom — e nenhum vínculo de indicação pode nascer dali."""
        _run(db.promo_codes.insert_one(
            {"code": "BEMVINDO", "sparks_amount": 500, "active": True, "usos": 0}
        ))
        _run(db.users.update_one({"email": "indicador@x.com"}, {"$set": {}}))
        _indicador(db)
        _run(db.users.update_one(
            {"email": "indicador@x.com"}, {"$set": {"referral_code": "BEMVINDO"}}
        ))

        conta = _cadastrar(db, "amigo@x.com", "Amigo", "BEMVINDO")
        assert conta["promo_code"] == "BEMVINDO"
        assert conta["indicado_por"] is None

    def test_cadastro_sem_codigo_nao_cria_vinculo(self, db):
        conta = _cadastrar(db, "sozinho@x.com", "Sozinho")
        assert conta["indicado_por"] is None
        assert _run(db.indicacoes.count_documents({})) == 0


# =========================================================== o prêmio

class TestPremioDaPrimeiraCompra:
    def test_indicador_recebe_metade_dos_sparks_da_compra(self, db, creditos, monkeypatch):
        indicador_id, codigo = _indicador(db)
        amigo = _cadastrar(db, "amigo@x.com", "Amigo", codigo)

        _pagar(db, amigo["user_id"], "mp-1", "spark_1500", 1500, monkeypatch)

        assert creditos == [(indicador_id, "mp-1", 750)]
        vinculo = _run(db.indicacoes.find_one({"indicado_id": amigo["user_id"]}))
        assert vinculo["premio_sparks"] == 750
        assert vinculo["premio_em"] is not None

    def test_so_a_primeira_compra_paga(self, db, creditos, monkeypatch):
        """A segunda compra do MESMO amigo não rende mais nada — é a regra
        inteira do produto, e é o que o carimbo no vínculo protege."""
        indicador_id, codigo = _indicador(db)
        amigo = _cadastrar(db, "amigo@x.com", "Amigo", codigo)

        _pagar(db, amigo["user_id"], "mp-1", "spark_200", 200, monkeypatch)
        _pagar(db, amigo["user_id"], "mp-2", "spark_4000", 4000, monkeypatch)

        assert creditos == [(indicador_id, "mp-1", 100)]

    def test_reenvio_do_mesmo_pagamento_nao_paga_duas_vezes(self, db, creditos, monkeypatch):
        """Cenário real: o processo morre entre o crédito e o `credited: True`,
        e o Mercado Pago reenvia. O caminho tem de ser refeito INTEIRO sem
        pagar de novo — nem travar, achando que outra compra já ganhou."""
        indicador_id, codigo = _indicador(db)
        amigo = _cadastrar(db, "amigo@x.com", "Amigo", codigo)

        _pagar(db, amigo["user_id"], "mp-1", "spark_600", 600, monkeypatch)
        # Desfaz só o carimbo do Mongo, como se o processo tivesse morrido logo
        # depois de creditar: o webhook volta a entrar no ramo do crédito.
        _run(db.sparks_payments.update_one({"mp_payment_id": "mp-1"}, {"$set": {"credited": False}}))
        _run(svc.process_payment_webhook(db, "mp-1"))

        assert creditos == [(indicador_id, "mp-1", 300)]
        vinculo = _run(db.indicacoes.find_one({"indicado_id": amigo["user_id"]}))
        assert vinculo["premio_sparks"] == 300

    def test_comprador_sem_indicador_nao_paga_ninguem(self, db, creditos, monkeypatch):
        conta = _cadastrar(db, "sozinho@x.com", "Sozinho")
        _pagar(db, conta["user_id"], "mp-1", "spark_600", 600, monkeypatch)
        assert creditos == []

    def test_o_comprador_recebe_o_dele_mesmo_se_o_premio_falhar(self, db, monkeypatch):
        """O prêmio é acessório; o crédito de quem PAGOU é o contrato. Uma
        falha no bônus não pode derrubar a compra."""
        _, codigo = _indicador(db)
        amigo = _cadastrar(db, "amigo@x.com", "Amigo", codigo)

        def explode(*a, **k):
            raise RuntimeError("Firestore fora do ar")

        monkeypatch.setattr(fs, "grant_sparks_evento", explode)
        resultado = _pagar(db, amigo["user_id"], "mp-1", "spark_600", 600, monkeypatch)
        assert resultado["credited"] is True

    def test_pacote_pequeno_demais_nao_gera_premio_de_zero(self, db, creditos, monkeypatch):
        """O pacote de teste tem 15 Sparks; metade arredondada para baixo é 7.
        Zero seria um registro de prêmio que não pagou nada — 1 Spark ainda é
        prêmio, 0 não é."""
        indicador_id, codigo = _indicador(db)
        amigo = _cadastrar(db, "amigo@x.com", "Amigo", codigo)
        _pagar(db, amigo["user_id"], "mp-1", "spark_test_15", 15, monkeypatch)
        assert creditos == [(indicador_id, "mp-1", 7)]


# ============================================================ a tela

class TestResumoDoAluno:
    def test_lista_os_amigos_e_separa_quem_ja_comprou(self, db, creditos, monkeypatch):
        indicador_id, codigo = _indicador(db)
        comprou = _cadastrar(db, "comprou@x.com", "Beatriz", codigo)
        _cadastrar(db, "ainda-nao@x.com", "Carlos", codigo)
        _pagar(db, comprou["user_id"], "mp-1", "spark_600", 600, monkeypatch)

        resumo = _run(indicacoes.resumo(db, indicador_id, "Renan Vailante"))
        assert resumo["codigo"] == codigo
        assert resumo["total_amigos"] == 2
        assert resumo["aguardando_primeira_compra"] == 1
        assert resumo["total_sparks"] == 300
        por_nome = {a["nome"]: a for a in resumo["amigos"]}
        assert por_nome["Beatriz"]["ja_comprou"] is True
        assert por_nome["Carlos"]["ja_comprou"] is False

    def test_quem_nunca_indicou_ve_o_proprio_codigo_e_lista_vazia(self, db):
        conta = _cadastrar(db, "novo@x.com", "Ana")
        resumo = _run(indicacoes.resumo(db, conta["user_id"], "Ana"))
        assert resumo["codigo"].startswith("ANA")
        assert resumo["amigos"] == []
        assert resumo["total_sparks"] == 0

    def test_a_tela_nunca_devolve_email_de_quem_foi_indicado(self, db):
        """A lista é do indicador, mas os dados são de TERCEIROS. Nome e data
        bastam para ele reconhecer quem entrou; e-mail é dado de outra pessoa
        e não tem por que atravessar a API."""
        indicador_id, codigo = _indicador(db)
        _cadastrar(db, "amigo@x.com", "Amigo", codigo)
        resumo = _run(indicacoes.resumo(db, indicador_id, "Renan"))
        assert "email" not in resumo["amigos"][0]
        assert "user_id" not in resumo["amigos"][0]


# ======================================================= exclusão de conta

class TestExclusaoDeConta:
    def test_quem_indicou_vira_lapide_sem_apagar_a_origem_do_outro(self, db, monkeypatch):
        import dados_pessoais

        dados_pessoais.set_db(db)
        indicador_id, codigo = _indicador(db)
        amigo = _cadastrar(db, "amigo@x.com", "Amigo", codigo)

        n = _run(dados_pessoais._desvincular_indicacoes(indicador_id))

        vinculo = _run(db.indicacoes.find_one({"indicado_id": amigo["user_id"]}))
        assert n == 1
        assert vinculo is not None                       # a conta do amigo continua tendo origem
        assert vinculo["indicador_id"] == dados_pessoais.TOMBSTONE
        assert indicador_id not in str(vinculo)          # nenhum resto do id (que carrega o nome)
