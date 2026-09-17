"""Os direitos que os pacotes vendem, além de saldo — todos para sempre.

**Um único pacote concede direito hoje** (desde 2026-09-16): o de
**R$119,90 (4.000 Sparks)**, que dá `cursos_inclusos` (os quatro cursos do
catálogo, sem os 500 de cada), `lives_inclusas` (toda quinta, sem os 200 por
edição), `mentis_ilimitada` e `comunidade_vip`.

Os outros pacotes vendem SALDO, e só saldo — inclusive o de R$54,90, que até
2026-09-16 incluía as aulas ao vivo. A aula de quinta voltou a custar 200
Sparks por edição para todo mundo, e a única exceção é o pacote de cima.

A escada continua sendo a regra que segura o catálogo: **pacote mais caro
nunca dá menos direito que um mais barato**. Ela é o que impede o defeito de
alguém pagar R$119,90 e continuar pagando por uma quinta que sai de graça
para quem gastou menos.

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
    def test_o_pacote_de_11990_concede_tudo(self):
        pkg = sparks_store.get_package("spark_4000")
        assert pkg.price_cents == 11990
        assert pkg.sparks_amount == 4000
        assert set(pkg.direitos) == set(sparks_store.DIREITOS)

    def test_so_o_pacote_de_11990_dispensa_os_200_sparks_da_quinta(self):
        """A aula ao vivo custa 200 Sparks por edição, toda quinta, para todo
        mundo — MENOS para quem comprou o pacote de R$119,90.

        É a regra de produto de 2026-09-16, e ela mora inteira no catálogo: se
        um segundo pacote ganhasse `lives_inclusas` por descuido, a aula
        deixaria de ser cobrada de quem o produto decidiu cobrar."""
        donos = [
            p.package_id for p in sparks_store.list_packages()
            if "lives_inclusas" in p.direitos
        ]
        assert donos == ["spark_4000"]

    def test_o_pacote_de_5490_vende_saldo_e_so_saldo(self):
        """R$54,90 deixou de incluir as lives em 2026-09-16. O pacote continua
        existindo e continua sendo o "mais vendido" — o que ele não faz mais é
        conceder direito nenhum."""
        pkg = sparks_store.get_package("spark_1500")
        assert pkg.price_cents == 5490
        assert pkg.direitos == ()
        assert pkg.beneficios == ()

    def test_cada_direito_tem_uma_linha_na_loja(self):
        """Direito concedido e não anunciado é dinheiro na mesa; anunciado e
        não concedido é propaganda enganosa. Um para um, em todo pacote."""
        for pkg in sparks_store.list_packages():
            assert len(pkg.beneficios) == len(pkg.direitos), pkg.package_id
            assert all(texto.strip() for texto in pkg.beneficios), pkg.package_id

    def test_so_o_pacote_de_cima_concede_direito(self):
        outros = [
            p for p in sparks_store.list_packages()
            if p.package_id != "spark_4000"
        ]
        assert outros and all(p.direitos == () for p in outros)

    def test_a_oferta_aponta_para_a_porta_mais_barata_do_direito(self):
        """A tela diz "isto vem no pacote X" perguntando ao catálogo
        (`pacote_com_direito`). Com um direito herdado pelos pacotes de cima,
        a resposta certa é o MAIS BARATO que o concede — anunciar o de
        R$119,90 para quem só quer as lives seria vender caro de propósito."""
        for direito in sparks_store.DIREITOS:
            donos = [
                p.package_id for p in sparks_store.list_packages()
                if not p.oculto and direito in sparks_store.direitos_do_pacote(p.package_id)
            ]
            assert donos, direito
            assert sparks_store.pacote_com_direito(direito).package_id == donos[0], direito

    def test_pacote_mais_caro_nunca_da_menos_direito_que_um_mais_barato(self):
        """A ESCADA. Um direito que existisse só no pacote de baixo faria o
        cliente que gastou mais pagar por algo que o vizinho ganhou — e é o
        tipo de defeito que só aparece na fatura do aluno."""
        visiveis = sorted(
            (p for p in sparks_store.list_packages() if not p.oculto),
            key=lambda p: p.price_cents,
        )
        for barato, caro in zip(visiveis, visiveis[1:]):
            assert set(barato.direitos) <= set(caro.direitos), (
                f"{caro.package_id} (R${caro.price_cents / 100:.2f}) não inclui "
                f"o que {barato.package_id} (R${barato.price_cents / 100:.2f}) já dá"
            )

    def test_todo_direito_da_lista_e_vendido_por_alguem(self):
        """Direito que nenhum pacote concede é uma porta no backend que
        ninguém consegue abrir."""
        vendidos = {
            d for p in sparks_store.list_packages()
            for d in sparks_store.direitos_do_pacote(p.package_id)
        }
        assert vendidos == set(sparks_store.DIREITOS)

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
        assert fs.tem_cursos_inclusos("aluno-1") is False
        assert fs.tem_lives_inclusas("aluno-1") is False

    def test_saldo_e_direitos_saem_de_uma_leitura_so(self, monkeypatch):
        """A aba de Cursos precisa dos dois e eles moram no mesmo documento.
        Duas leituras por abertura de página é exatamente o padrão que
        estourou a cota em 2026-09-04."""
        leituras = {"n": 0}

        class _Doc:
            def get(self):
                leituras["n"] += 1

                class _Snap:
                    @staticmethod
                    def to_dict():
                        return {"sparks_balance": 320, "lives_inclusas": True}
                return _Snap()

        class _Cliente:
            def collection(self, *_a):
                return self

            def document(self, *_a):
                return _Doc()

        monkeypatch.setattr(fs, "get_firestore", lambda *a, **k: _Cliente())
        saldo, direitos = fs.ler_saldo_e_direitos("aluno-1")
        assert leituras["n"] == 1
        assert saldo == 320
        assert direitos["lives_inclusas"] is True
        assert direitos["cursos_inclusos"] is False

    def test_leitura_quebrada_devolve_saldo_nulo_e_nenhum_direito(self, monkeypatch):
        """Saldo `None` deixa a tela mostrar o preço e tentar de novo no
        clique; direito `False` impede o produto caro de virar brinde durante
        um incidente."""
        class _Explode:
            def document(self, *_a, **_k):
                raise RuntimeError("Firestore fora do ar")

        monkeypatch.setattr(fs, "get_firestore", lambda *a, **k: _Explode())
        saldo, direitos = fs.ler_saldo_e_direitos("aluno-1")
        assert saldo is None
        assert direitos == {d: False for d in sparks_store.DIREITOS}

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
        assert direitos["cursos_inclusos"] is False
        assert direitos["lives_inclusas"] is False
