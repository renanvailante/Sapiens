"""Os direitos que os pacotes vendem, além de saldo.

`cursos_inclusos`/`lives_inclusas`/`comunidade_vip` são para sempre.
`mentis_ilimitada` tem prazo desde 2026-09-21 (`sparks_store.
PRAZO_MENTIS_ILIMITADA_DIAS`, decisão do dono que reverte a regra anterior de
"permanente") — ver `TestMentisIlimitadaComPrazo` mais abaixo.

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

import asyncio
import sys
from datetime import datetime, timedelta, timezone
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
                        # `mentis_ilimitada_ate` no futuro — sem isso `True`
                        # sozinho não basta mais (prazo desde 2026-09-21).
                        futuro = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
                        return {"mentis_ilimitada": True, "mentis_ilimitada_ate": futuro}
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


class TestMentisIlimitadaComPrazo:
    """Decisão do dono, 2026-09-21: `mentis_ilimitada` deixou de ser
    permanente e passou a valer `sparks_store.PRAZO_MENTIS_ILIMITADA_DIAS`
    (30) dias — reverte a regra anterior (`Cerebro/regras/inviolaveis.md`
    chegou a travar o oposto: "não afirme que um direito expira"). Os outros
    três direitos do pacote de R$119,90 continuam sem prazo."""

    def test_mentis_ilimitada_valida_exige_ate_no_futuro(self):
        futuro = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        passado = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        assert fs._mentis_ilimitada_valida({"mentis_ilimitada": True, "mentis_ilimitada_ate": futuro}) is True
        assert fs._mentis_ilimitada_valida({"mentis_ilimitada": True, "mentis_ilimitada_ate": passado}) is False

    def test_true_sem_ate_e_tratado_como_expirado_nao_como_permanente(self):
        """Holder de antes da migração (ou falha de escrita): na dúvida,
        cobra — mesma disciplina de falha de leitura inteira."""
        assert fs._mentis_ilimitada_valida({"mentis_ilimitada": True}) is False

    def test_false_nunca_fica_valido_mesmo_com_ate_no_futuro(self):
        futuro = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        assert fs._mentis_ilimitada_valida({"mentis_ilimitada": False, "mentis_ilimitada_ate": futuro}) is False

    def test_data_ilegivel_nao_quebra_e_vira_expirado(self):
        assert fs._mentis_ilimitada_valida({"mentis_ilimitada": True, "mentis_ilimitada_ate": "lixo"}) is False

    def test_ler_direitos_rebaixa_true_expirado_para_false(self, monkeypatch):
        passado = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        class _Doc:
            def get(self):
                class _Snap:
                    @staticmethod
                    def to_dict():
                        return {"mentis_ilimitada": True, "mentis_ilimitada_ate": passado, "comunidade_vip": True}
                return _Snap()

        class _Cliente:
            def collection(self, *_a):
                return self

            def document(self, *_a):
                return _Doc()

        monkeypatch.setattr(fs, "get_firestore", lambda *a, **k: _Cliente())
        direitos = fs.ler_direitos("aluno-1")
        assert direitos["mentis_ilimitada"] is False  # expirado
        assert direitos["comunidade_vip"] is True  # este continua sem prazo

    def test_conceder_direitos_grava_ate_trinta_dias_a_frente(self, monkeypatch):
        gravado: dict = {}

        class _Doc:
            def set(self, campos, merge=True):
                gravado.update(campos)

        class _Cliente:
            def collection(self, *_a):
                return self

            def document(self, *_a):
                return _Doc()

        monkeypatch.setattr(fs, "get_firestore", lambda *a, **k: _Cliente())
        antes = datetime.now(timezone.utc)
        fs.conceder_direitos("aluno-1", ("mentis_ilimitada", "comunidade_vip"))

        assert gravado["mentis_ilimitada"] is True
        assert gravado["comunidade_vip"] is True
        assert "comunidade_vip_ate" not in gravado  # só mentis_ilimitada tem prazo
        ate = datetime.fromisoformat(gravado["mentis_ilimitada_ate"])
        dias = (ate - antes).total_seconds() / 86400
        assert sparks_store.PRAZO_MENTIS_ILIMITADA_DIAS - 0.01 <= dias <= sparks_store.PRAZO_MENTIS_ILIMITADA_DIAS + 0.01

    def test_migracao_da_janela_nova_a_partir_de_hoje_nao_da_compra_original(self, monkeypatch):
        """Decisão explícita do dono: quem já tinha o direito permanente
        ganha 30 dias A PARTIR DE HOJE, não a partir de quando comprou —
        ninguém perde acesso no minuto em que a migração roda."""
        class _Snap:
            def __init__(self, id_, dados):
                self.id = id_
                self._dados = dados
                self.reference = self

            def to_dict(self):
                return self._dados

            def set(self, campos, merge=True):
                self._dados.update(campos)

        antigo = {"mentis_ilimitada": True}  # sem `_ate` — holder de antes da migração
        ja_migrado = {"mentis_ilimitada": True, "mentis_ilimitada_ate": "2020-01-01T00:00:00+00:00"}
        nunca_comprou = {"mentis_ilimitada": False}
        docs = [
            _Snap("holder-antigo", antigo),
            _Snap("ja-migrado", ja_migrado),
            _Snap("sem-direito", nunca_comprou),
        ]

        class _Colecao:
            def stream(self):
                return iter(docs)

        class _Cliente:
            def collection(self, *_a):
                return _Colecao()

        monkeypatch.setattr(fs, "get_firestore", lambda *a, **k: _Cliente())

        dry_run = fs.migrar_mentis_ilimitada_para_prazo(aplicar=False)
        assert dry_run["afetados"] == 1
        assert dry_run["uids"] == ["holder-antigo"]
        assert "mentis_ilimitada_ate" not in antigo  # dry run não escreve

        aplicado = fs.migrar_mentis_ilimitada_para_prazo(aplicar=True)
        assert aplicado["afetados"] == 1
        assert "mentis_ilimitada_ate" in antigo
        assert ja_migrado["mentis_ilimitada_ate"] == "2020-01-01T00:00:00+00:00"  # não mexeu em quem já tinha

        # a validade nova é ~30 dias a partir de AGORA, não de uma data antiga
        ate = datetime.fromisoformat(antigo["mentis_ilimitada_ate"])
        dias = (ate - datetime.now(timezone.utc)).total_seconds() / 86400
        assert sparks_store.PRAZO_MENTIS_ILIMITADA_DIAS - 0.01 <= dias <= sparks_store.PRAZO_MENTIS_ILIMITADA_DIAS + 0.01


class TestQuemNaoPagouNaoRecebeEstorno:
    """O outro lado da ilimitada: quem não foi cobrado não pode ser
    reembolsado. Até 2026-10-01 a falha do modelo devolvia o preço de tabela a
    quem tem a Mentis ilimitada — cada explicação que falhava CREDITAVA Sparks
    a quem não tinha pago nada."""

    @pytest.fixture
    def carteira(self, monkeypatch):
        estado = {"saldo": 500, "debitos": [], "reembolsos": []}

        def _deduct(uid, quantia):
            estado["saldo"] -= quantia
            estado["debitos"].append(quantia)
            return estado["saldo"]

        def _refund(uid, quantia):
            estado["saldo"] += quantia
            estado["reembolsos"].append(quantia)
            return estado["saldo"]

        monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: estado["saldo"])
        monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: estado["saldo"])
        monkeypatch.setattr(fs, "deduct_sparks", _deduct)
        monkeypatch.setattr(fs, "refund_sparks", _refund)
        return estado

    def test_recibo_diz_quanto_foi_cobrado_de_verdade(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: True)
        assert mr._cobrar_com_recibo("aluno-1", mr.EXPLICACAO_COST) == (500, 0)
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)
        assert mr._cobrar_com_recibo("aluno-1", mr.EXPLICACAO_COST) == (500 - mr.EXPLICACAO_COST, mr.EXPLICACAO_COST)

    def test_ilimitada_nao_ganha_sparks_quando_o_modelo_falha(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: True)
        for custo in (mr.SESSAO_COST, mr.MENSAGEM_COST, mr.EXPLICACAO_COST, mr.INTERVENCAO_COST,
                      mr.EXPLICACAO_CONTEUDO_COST, mr.DISSERTATIVA_COST):
            assert mr._safe_reembolso("aluno-1", custo) == 500
        assert carteira["reembolsos"] == []
        assert carteira["saldo"] == 500

    def test_quem_pagou_continua_recebendo_o_estorno(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)
        mr._safe_reembolso("aluno-1", mr.EXPLICACAO_COST)
        assert carteira["reembolsos"] == [mr.EXPLICACAO_COST]

    def test_estorno_de_zero_nao_mexe_no_saldo(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)
        assert mr._safe_reembolso("aluno-1", 0) == 500
        assert carteira["reembolsos"] == []


class TestLeituraDaRodadaEhMentis:
    """"Ler com a Mentis" na devolutiva da rodada é ferramenta da Mentis e
    passa pela cobrança dela — quem comprou a ilimitada não paga, e a falha
    não devolve o que não foi cobrado."""

    def _rodada(self, monkeypatch, resultado=None, explode=False):
        import firestore_routes as fr

        monkeypatch.setattr(fr.annotation_service, "montar_contexto_sessao", lambda respostas: {"n": len(respostas)})

        async def _diagnose(contexto):
            if explode:
                raise RuntimeError("gemini fora do ar")
            return resultado or {"pontos_fortes": ["leitura"], "pontos_de_atencao": [], "padroes_de_erro": []}

        monkeypatch.setattr(fr.ai_service, "diagnose_sessao", _diagnose)
        payload = fr.SessaoDiagnosticoPayload(respostas=[
            {"item_id": f"I{i}", "alternativa_escolhida": "A", "acertou": i % 2 == 0} for i in range(10)
        ])
        from models import User
        return asyncio.run(fr.diagnostico_sessao(payload, user=User(user_id="aluno-1", email="a@b.c", name="A"), _=None))

    @pytest.fixture
    def carteira(self, monkeypatch):
        estado = {"saldo": 500, "debitos": [], "reembolsos": []}
        monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: estado["saldo"])
        monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: estado["saldo"])

        def _deduct(uid, q):
            estado["saldo"] -= q
            estado["debitos"].append(q)
            return estado["saldo"]

        def _refund(uid, q):
            estado["saldo"] += q
            estado["reembolsos"].append(q)
            return estado["saldo"]

        monkeypatch.setattr(fs, "deduct_sparks", _deduct)
        monkeypatch.setattr(fs, "refund_sparks", _refund)
        return estado

    def test_ilimitada_le_a_rodada_sem_pagar(self, carteira, monkeypatch):
        import firestore_routes as fr
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: True)
        saida = self._rodada(monkeypatch)
        assert saida["cobrado"] == 0
        assert carteira["debitos"] == []
        assert fr.RESUMO_SESSAO_COST > 0

    def test_sem_o_direito_cobra_o_preco_da_constante(self, carteira, monkeypatch):
        import firestore_routes as fr
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)
        saida = self._rodada(monkeypatch)
        assert carteira["debitos"] == [fr.RESUMO_SESSAO_COST]
        assert saida["cobrado"] == fr.RESUMO_SESSAO_COST

    def test_falha_da_ilimitada_nao_vira_credito(self, carteira, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: True)
        with pytest.raises(HTTPException) as erro:
            self._rodada(monkeypatch, explode=True)
        assert erro.value.status_code == 503
        assert "Nada foi cobrado" in erro.value.detail
        assert carteira["reembolsos"] == []

    def test_falha_de_quem_pagou_devolve(self, carteira, monkeypatch):
        import firestore_routes as fr
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)
        with pytest.raises(HTTPException):
            self._rodada(monkeypatch, explode=True)
        assert carteira["reembolsos"] == [fr.RESUMO_SESSAO_COST]


class TestPrecosDaMentisSaemDasConstantes:
    def test_endpoint_devolve_as_constantes_que_cobram(self):
        import firestore_routes as fr
        precos = asyncio.run(mr.precos(None))
        assert precos == {
            "explicacao": mr.EXPLICACAO_COST,
            "sessao": mr.SESSAO_COST,
            "mensagem": mr.MENSAGEM_COST,
            "intervencao": mr.INTERVENCAO_COST,
            "explicacao_conteudo": mr.EXPLICACAO_CONTEUDO_COST,
            "dissertativa": mr.DISSERTATIVA_COST,
            "resumo_rodada": fr.RESUMO_SESSAO_COST,
        }


class TestSapiensPlus:
    """O Plus da primeira ofensiva de 5 dias liga, por 48 horas, os direitos
    digitais do pacote de cima — lido pelo MESMO `ler_direitos`, então
    nenhuma porta precisou saber que ele existe."""

    def _doc(self, monkeypatch, dados):
        class _Snap:
            def to_dict(self):
                return dados

        class _Ref:
            def get(self):
                return _Snap()

        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: _Ref())

    def test_plus_vigente_libera_mentis_cursos_e_vip(self, monkeypatch):
        futuro = (datetime.now(timezone.utc) + timedelta(hours=40)).isoformat()
        self._doc(monkeypatch, {"plus_ate": futuro})
        d = fs.ler_direitos("u1")
        assert d["mentis_ilimitada"] and d["cursos_inclusos"] and d["comunidade_vip"]

    def test_plus_nao_inclui_a_live(self, monkeypatch):
        """A live inscreve na leitura de `/cursos` — uma vaga que sobreviveria
        às 48 horas. Fica fora do Plus de propósito."""
        futuro = (datetime.now(timezone.utc) + timedelta(hours=40)).isoformat()
        self._doc(monkeypatch, {"plus_ate": futuro})
        assert fs.ler_direitos("u1")["lives_inclusas"] is False
        assert "lives_inclusas" not in sparks_store.DIREITOS_DO_PLUS

    def test_plus_vencido_volta_a_cobrar(self, monkeypatch):
        passado = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self._doc(monkeypatch, {"plus_ate": passado})
        assert not any(fs.ler_direitos("u1").values())

    def test_plus_nunca_desliga_o_que_foi_comprado(self, monkeypatch):
        passado = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self._doc(monkeypatch, {"plus_ate": passado, "cursos_inclusos": True, "lives_inclusas": True})
        d = fs.ler_direitos("u1")
        assert d["cursos_inclusos"] and d["lives_inclusas"]

    def test_saldo_e_direitos_tambem_enxerga_o_plus(self, monkeypatch):
        futuro = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self._doc(monkeypatch, {"plus_ate": futuro, "sparks_balance": 42})
        saldo, d = fs.ler_saldo_e_direitos("u1")
        assert saldo == 42 and d["cursos_inclusos"] is True

    def test_plus_e_subconjunto_dos_direitos(self):
        assert set(sparks_store.DIREITOS_DO_PLUS) <= set(sparks_store.DIREITOS)
