"""Os direitos que o pacote de R$119,90 vende: Mentis ILIMITADA (por um mês,
desde 2026-09-16) e Comunidade VIP (para sempre).

O prazo da Mentis é testado em `test_validade_dos_direitos.py`; aqui se testa
o que não depende de data — o catálogo ser a fonte única, e quem tem o direito
VIGENTE não pagar.

Isto é publicidade que vira contrato. A loja anuncia "Mentis ilimitada" no
card de 4.000 Sparks; se o servidor continuasse cobrando os 70 da sessão e os
10 por mensagem, o produto estaria cobrando duas vezes pela mesma coisa e a
tela de pagamento estaria mentindo. Os testes abaixo fecham exatamente esse
buraco, dos dois lados:

* **quem comprou não paga** nenhuma das quatro cobranças da Mentis;
* **quem não comprou continua pagando** — e o direito não escapa por falha de
  leitura do Firestore, que é o caminho pelo qual um "ilimitado" grátis
  vazaria para a base inteira.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
import mentis_routes as mr  # noqa: E402
import sparks_store  # noqa: E402


class TestOCatalogoEAFonteUnica:
    def test_o_pacote_de_11990_concede_os_dois_direitos(self):
        pkg = sparks_store.get_package("spark_4000")
        assert pkg.price_cents == 11990
        assert pkg.sparks_amount == 4000
        assert set(pkg.direitos) == {"mentis_ilimitada", "comunidade_vip"}

    def test_cada_direito_tem_uma_linha_na_loja(self):
        """Direito concedido e não anunciado é dinheiro na mesa; anunciado e
        não concedido é propaganda enganosa. Um para um."""
        pkg = sparks_store.get_package("spark_4000")
        assert len(pkg.beneficios) == len(pkg.direitos)
        assert all(texto.strip() for texto in pkg.beneficios)

    def test_nenhum_outro_pacote_concede_direito(self):
        outros = [p for p in sparks_store.list_packages() if p.package_id != "spark_4000"]
        assert outros and all(p.direitos == () for p in outros)

    def test_conceder_e_anunciar_leem_a_mesma_coisa(self):
        """Se estas duas respostas divergissem, a loja prometeria o que o
        webhook não concede — ou o contrário."""
        for p in sparks_store.list_packages():
            assert sparks_store.direitos_do_pacote(p.package_id) == p.direitos

    def test_pacote_nao_pode_inventar_direito_fora_da_lista(self):
        """`DIREITOS` é a lista fechada: cada item é uma porta que existe no
        backend. Um pacote com um direito inventado concederia uma flag que
        ninguém lê."""
        for p in sparks_store.list_packages():
            assert set(p.direitos) <= set(sparks_store.DIREITOS)

    def test_pacote_inexistente_nao_concede_nada(self):
        assert sparks_store.direitos_do_pacote("spark_inventado") == ()
        assert sparks_store.concede_mentis_ilimitada("spark_inventado") is False


class TestQuemComprouNaoPaga:
    @pytest.fixture
    def carteira(self, monkeypatch):
        estado = {"saldo": 500, "debitos": []}

        def _deduct(uid, quantia):
            estado["saldo"] -= quantia
            estado["debitos"].append(quantia)
            return estado["saldo"]

        monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: estado["saldo"])
        monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: estado["saldo"])
        monkeypatch.setattr(fs, "deduct_sparks", _deduct)
        return estado

    def test_com_o_direito_o_saldo_nem_e_tocado(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: True)
        for custo in (mr.SESSAO_COST, mr.MENSAGEM_COST, mr.EXPLICACAO_COST, mr.INTERVENCAO_COST):
            assert mr._cobrar("aluno-1", custo) == 500
        assert carteira["debitos"] == []

    def test_sem_o_direito_cada_acao_cobra(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)
        mr._cobrar("aluno-1", mr.SESSAO_COST)
        mr._cobrar("aluno-1", mr.MENSAGEM_COST)
        assert carteira["debitos"] == [mr.SESSAO_COST, mr.MENSAGEM_COST]

    def test_saldo_insuficiente_continua_402_para_quem_nao_comprou(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)

        def _sem_saldo(uid, quantia):
            raise fs.InsufficientSparksError(balance=5, needed=quantia)

        monkeypatch.setattr(fs, "deduct_sparks", _sem_saldo)
        with pytest.raises(HTTPException) as exc:
            mr._cobrar("aluno-1", mr.SESSAO_COST)
        assert exc.value.status_code == 402

    def test_ilimitada_nao_e_afetada_por_saldo_zero(self, carteira, monkeypatch):
        """O ponto de "ilimitada": o saldo pode estar em zero e a Mentis
        continua respondendo."""
        carteira["saldo"] = 0
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: True)
        assert mr._cobrar("aluno-1", mr.SESSAO_COST) == 0
        assert carteira["debitos"] == []


class TestOhDireitoNaoVazaPorFalha:
    def test_firestore_indisponivel_nao_libera_nada_de_graca(self, monkeypatch):
        """Na dúvida, cobra. Liberar o produto mais caro do catálogo por
        instabilidade de leitura seria dá-lo de presente à base inteira
        durante o incidente."""
        class _Explode:
            def document(self, *_a, **_k):
                raise RuntimeError("Firestore fora do ar")

        monkeypatch.setattr(fs, "get_firestore", lambda *a, **k: _Explode())
        assert fs.ler_direitos("aluno-1") == {d: False for d in sparks_store.DIREITOS}
        assert fs.tem_mentis_ilimitada("aluno-1") is False
        assert fs.tem_comunidade_vip("aluno-1") is False

    def test_ler_direitos_devolve_a_lista_inteira_sempre(self, monkeypatch):
        """Mesmo para o aluno que não comprou nada: a tela distingue `False`
        de "campo que não veio" e um dicionário incompleto viraria
        `undefined` no JavaScript."""
        class _Doc:
            def get(self):
                class _Snap:
                    @staticmethod
                    def to_dict():
                        return {"mentis_ilimitada": True}
                return _Snap()

        class _Cliente:
            def collection(self, *_a):
                return self

            def document(self, *_a):
                return _Doc()

        monkeypatch.setattr(fs, "get_firestore", lambda *a, **k: _Cliente())
        direitos = fs.ler_direitos("aluno-1")
        assert set(direitos) == set(sparks_store.DIREITOS)
        assert direitos["mentis_ilimitada"] is True
        assert direitos["comunidade_vip"] is False
