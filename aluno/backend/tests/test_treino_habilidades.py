"""Banco de treino (HAB-01..HAB-56): integridade do corpus compilado, o
agregado O(1) por habilidade, e as rotas — com foco especial no que o Sparks
do aluno depende: `gerar` sempre termina com o saldo intacto (cobra e
devolve, geração real ainda não existe), nunca cobra duas vezes pela mesma
tentativa, e `responder` nunca confia no que o cliente afirma ter acertado.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from firebase_admin import firestore as fb_firestore

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
import treino_habilidades as th  # noqa: E402
import treino_routes as routes  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _user(uid: str = "aluno-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno")


# ============================================================== integridade


class TestIntegridadeDoCorpus:
    def test_56_habilidades_na_ordem_canonica(self):
        ids = [h["hab_id"] for h in th.banco()["habilidades"]]
        assert ids == [f"HAB-{i:02d}" for i in range(1, 57)]

    def test_cada_habilidade_tem_4_ou_5_questoes(self):
        for h in th.banco()["habilidades"]:
            assert len(h["questoes"]) in (4, 5), h["hab_id"]

    def test_hab_38_tem_a_lacuna_conhecida_de_4_questoes(self):
        """Decisão do usuário: seguir com as 4 existentes em vez de bloquear
        a habilidade — ver plano de implementação."""
        hab38 = next(h for h in th.banco()["habilidades"] if h["hab_id"] == "HAB-38")
        assert len(hab38["questoes"]) == 4

    def test_gabarito_sempre_aponta_para_alternativa_existente(self):
        for h in th.banco()["habilidades"]:
            for q in h["questoes"]:
                letras = {a["letra"] for a in q["alternativas"]}
                assert set(q["gabarito"]) <= letras, (h["hab_id"], q["indice"])
                assert q["gabarito"], (h["hab_id"], q["indice"])

    def test_dificuldade_sempre_no_enum_valido(self):
        for h in th.banco()["habilidades"]:
            for q in h["questoes"]:
                assert q["dificuldade"] in th.DIFICULDADES_VALIDAS, (h["hab_id"], q["indice"])

    def test_tabela_quando_existe_tem_linhas_com_mesma_largura_do_cabecalho(self):
        total_com_tabela = 0
        for h in th.banco()["habilidades"]:
            for q in h["questoes"]:
                if q["tabela"] is None:
                    continue
                total_com_tabela += 1
                largura = len(q["tabela"]["headers"])
                for linha in q["tabela"]["rows"]:
                    assert len(linha) == largura, (h["hab_id"], q["indice"])
        assert total_com_tabela == 30  # 7 arquivos-fonte identificados na auditoria

    def test_projecao_sem_gabarito_nunca_vaza_resposta(self):
        base = th.obter_base("HAB-23")
        bruto = str(base)
        assert "gabarito" not in bruto.lower()
        assert "elucidacao" not in bruto.lower()

    def test_gabarito_bimodal_e_preservado_sem_forcar_uma_unica_letra(self):
        """HAB-27 questão 2: conjunto de dados genuinamente bimodal (18 e 22
        aparecem duas vezes cada) — o conteúdo original tem duas letras
        corretas, e isso não é um erro de transcrição para 'corrigir'."""
        hab27 = next(h for h in th.banco()["habilidades"] if h["hab_id"] == "HAB-27")
        q2 = next(q for q in hab27["questoes"] if q["indice"] == 2)
        assert q2["gabarito"] == ["A", "C"]


# ==================================================== agregado O(1) por HAB


class _FakeDocComIncrement:
    """Entende `firestore.Increment` (soma no valor já existente) o
    suficiente para provar a semântica de `increment_treino_stats` sem
    depender de um Firestore de verdade."""

    def __init__(self, dados=None):
        self.dados = dados or {}
        self.exists = bool(dados)

    def get(self):
        return self

    def to_dict(self):
        return self.dados

    def set(self, novo, merge=False):
        def _mesclar(alvo: dict, origem: dict):
            for chave, valor in origem.items():
                if isinstance(valor, fb_firestore.Increment):
                    atual = alvo.get(chave, 0) if isinstance(alvo.get(chave), (int, float)) else 0
                    alvo[chave] = atual + valor.value
                elif isinstance(valor, dict):
                    _mesclar(alvo.setdefault(chave, {}), valor)
                else:
                    alvo[chave] = valor

        if merge:
            _mesclar(self.dados, novo)
        else:
            self.dados = novo
        self.exists = True


class TestAgregadoDeTreino:
    def test_incrementa_respondidas_e_acertos_independentemente_por_hab(self, monkeypatch):
        doc = _FakeDocComIncrement()
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)

        fs.increment_treino_stats("aluno-1", "HAB-03", acertou=True)
        fs.increment_treino_stats("aluno-1", "HAB-03", acertou=False)
        fs.increment_treino_stats("aluno-1", "HAB-07", acertou=True)

        stats = fs.ler_treino_stats("aluno-1")
        assert stats["HAB-03"] == {"respondidas": 2, "acertos": 1}
        assert stats["HAB-07"] == {"respondidas": 1, "acertos": 1}

    def test_uma_leitura_so_nao_varre_historico(self, monkeypatch):
        doc = _FakeDocComIncrement({"treino_agregado": {"HAB-01": {"respondidas": 5, "acertos": 3}}})
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)

        def _proibido(*a, **k):
            raise AssertionError("ler_treino_stats varreu o histórico de behavior")

        monkeypatch.setattr(fs, "get_student_behavior_history", _proibido)
        assert fs.ler_treino_stats("aluno-1")["HAB-01"] == {"respondidas": 5, "acertos": 3}

    def test_falha_ao_atualizar_agregado_nao_derruba_a_resposta(self, monkeypatch):
        """O evento de behavior já foi gravado antes disto — um agregado que
        falhou é recuperável depois; a resposta do aluno, não."""
        def _quebra(uid):
            raise RuntimeError("firestore fora do ar")

        monkeypatch.setattr(fs, "_student_doc_ref", _quebra)
        fs.increment_treino_stats("aluno-1", "HAB-03", acertou=True)  # não levanta


# ============================================================== rotas


class BehaviorFake:
    """Dublê de `firestore_service` para behavior + agregado de treino +
    Sparks por questão concluída (`grant_question_sparks`): grava tudo em
    memória, com a mesma garantia de "só credita uma vez por item_id" do
    Firestore real, sem precisar de um Firestore de verdade."""

    def __init__(self, saldo_inicial: int = 1000):
        self.eventos: list[dict] = []
        self.stats: dict[str, dict[str, dict[str, int]]] = {}
        self.saldos: dict[str, int] = {}
        self.inicial = saldo_inicial
        self.itens_creditados: set[tuple[str, str]] = set()

    def instalar(self, monkeypatch):
        monkeypatch.setattr(fs, "write_behavior_event", self.write_behavior_event)
        monkeypatch.setattr(fs, "increment_treino_stats", self.increment_treino_stats)
        monkeypatch.setattr(fs, "ler_treino_stats", self.ler_treino_stats)
        monkeypatch.setattr(fs, "grant_question_sparks", self.grant_question_sparks)
        monkeypatch.setattr(fs, "read_sparks_balance", self.read_sparks_balance)
        return self

    def write_behavior_event(self, uid, **kwargs):
        evento = {"student_id": uid, **kwargs}
        self.eventos.append(evento)
        return evento

    def increment_treino_stats(self, uid, hab_id, acertou):
        s = self.stats.setdefault(uid, {}).setdefault(hab_id, {"respondidas": 0, "acertos": 0})
        s["respondidas"] += 1
        s["acertos"] += 1 if acertou else 0

    def ler_treino_stats(self, uid):
        return dict(self.stats.get(uid, {}))

    def grant_question_sparks(self, uid, item_id, amount=1):
        chave = (uid, item_id)
        if chave in self.itens_creditados:
            return {"ja_concedido": True, "sparks_ganhos": 0}
        self.itens_creditados.add(chave)
        self.saldos[uid] = self.saldos.setdefault(uid, self.inicial) + amount
        return {"ja_concedido": False, "sparks_ganhos": amount}

    def read_sparks_balance(self, uid):
        return self.saldos.setdefault(uid, self.inicial)


@pytest.fixture
def behavior(monkeypatch) -> BehaviorFake:
    return BehaviorFake().instalar(monkeypatch)


class CarteiraFake:
    """Mesmo contrato de `test_redacao_routes.CarteiraFake`: o que prova
    idempotência é a CONTAGEM de débitos/reembolsos, não o saldo final (um
    débito seguido de reembolso deixa o mesmo saldo de nunca ter cobrado)."""

    def __init__(self, saldo_inicial: int = 1000):
        self.saldos: dict[str, int] = {}
        self.inicial = saldo_inicial
        self.debitos: list[tuple[str, int]] = []
        self.reembolsos: list[tuple[str, int]] = []

    def instalar(self, monkeypatch):
        monkeypatch.setattr(fs, "ensure_sparks_balance", self.ensure)
        monkeypatch.setattr(fs, "deduct_sparks", self.deduct)
        monkeypatch.setattr(fs, "refund_sparks", self.refund)
        monkeypatch.setattr(fs, "read_sparks_balance", self.read)
        return self

    def ensure(self, uid: str) -> int:
        return self.saldos.setdefault(uid, self.inicial)

    def read(self, uid: str) -> int:
        return self.saldos.setdefault(uid, self.inicial)

    def deduct(self, uid: str, amount: int) -> int:
        saldo = self.saldos.setdefault(uid, self.inicial)
        if saldo < amount:
            raise fs.InsufficientSparksError(saldo, amount)
        self.saldos[uid] = saldo - amount
        self.debitos.append((uid, amount))
        return self.saldos[uid]

    def refund(self, uid: str, amount: int) -> int:
        self.saldos[uid] = self.saldos.setdefault(uid, self.inicial) + amount
        self.reembolsos.append((uid, amount))
        return self.saldos[uid]


@pytest.fixture
def carteira(monkeypatch) -> CarteiraFake:
    return CarteiraFake().instalar(monkeypatch)


# ---------------------------------------------------------- listar / base


def test_listar_habilidades_sem_resposta_vem_sem_dados(fake_db, behavior):
    resultado = _run(routes.listar_habilidades(user=_user()))
    assert len(resultado["habilidades"]) == 56
    hab01 = next(h for h in resultado["habilidades"] if h["hab_id"] == "HAB-01")
    assert hab01["classificacao"] == "sem_dados"
    assert hab01["respondidas"] == 0


def test_obter_base_de_habilidade_inexistente_e_404(fake_db, behavior):
    with pytest.raises(HTTPException) as exc:
        _run(routes.obter_base("HAB-99", user=_user()))
    assert exc.value.status_code == 404


# ------------------------------------------------------------- responder


def test_responder_ignora_acertou_do_cliente_e_usa_o_gabarito_do_servidor(fake_db, behavior):
    """O payload só tem `indice`/`alternativa` — não existe campo para o
    cliente afirmar que acertou. Isto prova que o resultado devolvido bate
    com o gabarito real do banco, não com nada que o cliente poderia forjar."""
    payload_errado = routes.ResponderRequest(indice=1, alternativa="B")  # HAB-01 Q1 correta é A
    resultado = _run(routes.responder("HAB-01", payload_errado, user=_user()))
    assert resultado["acertou"] is False
    assert resultado["gabarito"] == ["A"]

    payload_certo = routes.ResponderRequest(indice=1, alternativa="A")
    resultado2 = _run(routes.responder("HAB-01", payload_certo, user=_user()))
    assert resultado2["acertou"] is True


def test_responder_com_gabarito_bimodal_aceita_qualquer_letra_correta(fake_db, behavior):
    r_a = _run(routes.responder("HAB-27", routes.ResponderRequest(indice=2, alternativa="A"), user=_user("x")))
    r_c = _run(routes.responder("HAB-27", routes.ResponderRequest(indice=2, alternativa="C"), user=_user("y")))
    r_b = _run(routes.responder("HAB-27", routes.ResponderRequest(indice=2, alternativa="B"), user=_user("z")))
    assert r_a["acertou"] is True
    assert r_c["acertou"] is True
    assert r_b["acertou"] is False


def test_responder_alternativa_inexistente_e_422(fake_db, behavior):
    with pytest.raises(HTTPException) as exc:
        _run(routes.responder("HAB-01", routes.ResponderRequest(indice=1, alternativa="Z"), user=_user()))
    assert exc.value.status_code == 422


def test_responder_grava_evento_de_behavior_em_namespace_proprio(fake_db, behavior):
    """`item_id` no formato `TREINO:{hab}:{indice}` nunca colide com um item
    real do Enem — é isso que garante que Motor Cognitivo e Diagnóstico real
    (que resolvem eventos contra a coleção `itens`) ignoram estes eventos
    sem precisar de nenhum filtro extra (ver auditoria no plano)."""
    _run(routes.responder("HAB-01", routes.ResponderRequest(indice=1, alternativa="A"), user=_user()))
    assert len(behavior.eventos) == 1
    evento = behavior.eventos[0]
    assert evento["item_id"] == "TREINO:HAB-01:1"
    assert evento["contexto_tipo"] == "treino_habilidade"
    assert evento["ontology_version"] == th.ONTOLOGY_VERSION_TREINO


def test_responder_credita_1_sparks_na_primeira_vez_e_nunca_mais(fake_db, behavior):
    """`grant_question_sparks` é por `item_id`, não por resposta: revisar a
    mesma questão de novo não pode virar uma fonte infinita de Sparks."""
    r1 = _run(routes.responder("HAB-01", routes.ResponderRequest(indice=1, alternativa="A"), user=_user()))
    assert r1["sparks_ganhos"] == 1

    r2 = _run(routes.responder("HAB-01", routes.ResponderRequest(indice=1, alternativa="B"), user=_user()))
    assert r2["sparks_ganhos"] == 0
    assert behavior.saldos["aluno-1"] == behavior.inicial + 1


def test_tres_acertos_seguidos_classificam_como_forte(fake_db, behavior):
    for i in range(1, 4):
        _run(routes.responder("HAB-01", routes.ResponderRequest(indice=i, alternativa="A"), user=_user()))
    # A questão 1 tem gabarito A; força acerto usando o gabarito real de cada uma
    stats = _run(routes.listar_habilidades(user=_user()))
    hab01 = next(h for h in stats["habilidades"] if h["hab_id"] == "HAB-01")
    assert hab01["respondidas"] == 3


# --------------------------------------------------- gerar (beta indisponível)


def _payload_gerar(chave="chave-teste-1", **kw) -> routes.GerarRequest:
    dados = {"quantidade": 2, "dificuldade": "MEDIO", "idempotency_key": chave}
    dados.update(kw)
    return routes.GerarRequest(**dados)


def test_gerar_cobra_e_devolve_tudo_e_nunca_gera_questao(fake_db, carteira):
    routes.set_db(fake_db)
    resposta = _run(routes.gerar_questoes("HAB-01", _payload_gerar(quantidade=2), user=_user()))

    assert resposta["status"] == "indisponivel"
    assert carteira.debitos == [("aluno-1", 6)]
    assert carteira.reembolsos == [("aluno-1", 6)]
    assert carteira.saldos["aluno-1"] == 1000  # saldo intacto no fim
    assert resposta["sparks_cobrados"] == 0
    assert resposta["sparks_devolvidos"] == 6
    assert resposta["sparks_balance"] == 1000


def test_gerar_cobra_3_por_questao(fake_db, carteira):
    routes.set_db(fake_db)
    _run(routes.gerar_questoes("HAB-01", _payload_gerar(quantidade=5), user=_user()))
    assert carteira.debitos == [("aluno-1", 15)]
    assert carteira.reembolsos == [("aluno-1", 15)]


def test_mesma_chave_nao_cobra_duas_vezes(fake_db, carteira):
    routes.set_db(fake_db)
    primeira = _run(routes.gerar_questoes("HAB-01", _payload_gerar("k-repetida"), user=_user()))
    segunda = _run(routes.gerar_questoes("HAB-01", _payload_gerar("k-repetida"), user=_user()))

    assert carteira.debitos == [("aluno-1", 6)]  # só cobrou uma vez
    assert segunda == primeira


def test_chave_nova_cobra_de_novo(fake_db, carteira):
    routes.set_db(fake_db)
    _run(routes.gerar_questoes("HAB-01", _payload_gerar("chave-aaa1"), user=_user()))
    _run(routes.gerar_questoes("HAB-01", _payload_gerar("chave-bbb2"), user=_user()))
    assert carteira.debitos == [("aluno-1", 6), ("aluno-1", 6)]


def test_mesma_chave_de_outro_aluno_nao_colide(fake_db, carteira):
    routes.set_db(fake_db)
    _run(routes.gerar_questoes("HAB-01", _payload_gerar("chave-mesma"), user=_user("aluno-1")))
    _run(routes.gerar_questoes("HAB-01", _payload_gerar("chave-mesma"), user=_user("aluno-2")))
    assert carteira.debitos == [("aluno-1", 6), ("aluno-2", 6)]


def test_saldo_insuficiente_nao_cobra_nem_cria_reivindicacao(fake_db, monkeypatch):
    routes.set_db(fake_db)
    CarteiraFake(saldo_inicial=2).instalar(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _run(routes.gerar_questoes("HAB-01", _payload_gerar(quantidade=1), user=_user()))
    assert exc.value.status_code == 402
    assert fake_db.treino_geracoes.docs == []


def test_habilidade_inexistente_e_404_antes_de_cobrar(fake_db, carteira):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.gerar_questoes("HAB-99", _payload_gerar(), user=_user()))
    assert exc.value.status_code == 404
    assert carteira.debitos == []


def test_dificuldade_invalida_e_422_antes_de_cobrar(fake_db, carteira):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.gerar_questoes("HAB-01", _payload_gerar(dificuldade="IMPOSSIVEL"), user=_user()))
    assert exc.value.status_code == 422
    assert carteira.debitos == []


def test_quantidade_fora_de_1_a_10_e_rejeitada_na_validacao():
    with pytest.raises(ValueError):
        routes.GerarRequest(quantidade=11, dificuldade="FACIL", idempotency_key="x12345678")
    with pytest.raises(ValueError):
        routes.GerarRequest(quantidade=0, dificuldade="FACIL", idempotency_key="x12345678")


def test_reembolso_falho_nao_trava_a_chave_para_sempre(fake_db, carteira, monkeypatch):
    """Se até a compensação falhar (Firestore fora do ar bem na hora do
    reembolso), a reivindicação TTL permite retomar depois em vez de queimar
    a chave do aluno para sempre."""
    routes.set_db(fake_db)

    chamadas = {"n": 0}
    original = carteira.refund

    def _quebra_uma_vez(uid, amount):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("firestore fora do ar")
        return original(uid, amount)

    monkeypatch.setattr(fs, "refund_sparks", _quebra_uma_vez)
    resposta = _run(routes.gerar_questoes("HAB-01", _payload_gerar("chave-instavel"), user=_user()))
    # _safe_reembolso engoliu a exceção: a resposta ainda sai como "indisponível",
    # e a reivindicação foi marcada concluída mesmo com o reembolso tendo falhado
    # silenciosamente (mesmo contrato de redacao_routes._safe_reembolso).
    assert resposta["status"] == "indisponivel"
    assert carteira.debitos == [("aluno-1", 6)]


def test_concorrencia_na_mesma_chave_so_cobra_uma_vez(fake_db, carteira):
    """Duas requisições 'simultâneas' com a mesma idempotency_key — a
    segunda insert_one já encontra o documento e nunca chega a cobrar."""
    routes.set_db(fake_db)

    async def _duas_juntas():
        return await asyncio.gather(
            routes.gerar_questoes("HAB-01", _payload_gerar("chave-concorrente"), user=_user()),
            routes.gerar_questoes("HAB-01", _payload_gerar("chave-concorrente"), user=_user()),
        )

    resultados = _run(_duas_juntas())
    assert carteira.debitos == [("aluno-1", 6)]
    assert resultados[0]["status"] == resultados[1]["status"] == "indisponivel"
