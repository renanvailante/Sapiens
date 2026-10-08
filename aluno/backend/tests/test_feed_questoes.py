"""O feed infinito do Folhear: padrão de erro primeiro, nunca acaba, nunca
mostra gabarito, e custa uma leitura do Firestore por lote."""
from __future__ import annotations

import asyncio

import pytest

import feed_questoes as fq


def _item(iid, procs=(), disciplina="Matemática"):
    return {"item_id": iid, "estrutura_cognitiva": {"processos": [{"id": p} for p in procs]}, "fonte": {"disciplina": disciplina}}


INDEX = {
    "m1": _item("m1", ["PROC-QUANT-02"]),
    "m2": _item("m2", ["PROC-QUANT-02"]),
    "m3": _item("m3", ["PROC-QUANT-02"]),
    "t1": _item("t1", ["PROC-TEXT-01"], "Português"),
    "t2": _item("t2", ["PROC-TEXT-01"], "Português"),
}
ACERVO = [
    {"item_id": "m1", "fonte": {"disciplina": "Matemática"}},
    {"item_id": "m2", "fonte": {"disciplina": "Matemática"}},
    {"item_id": "m3", "fonte": {"disciplina": "Matemática"}},
    {"item_id": "t1", "fonte": {"disciplina": "Português"}},
    {"item_id": "t2", "fonte": {"disciplina": "Português"}},
    {"item_id": "h1", "fonte": {"disciplina": "História"}},
    {"item_id": "x1", "fonte": {"disciplina": "Matemática"}},
]


def _escolher(**kw):
    base = dict(index=INDEX, acervo=ACERVO, respondidos=set(), excluir=set(), processos=[], limite=8, semente="s")
    base.update(kw)
    return fq.escolher(**base)


class TestOrdem:
    def test_padrao_de_erro_vem_primeiro_e_intercalado(self):
        lote = _escolher(processos=["PROC-QUANT-02", "PROC-TEXT-01"], limite=4)
        assert [e["motivo"] for e in lote] == ["padrao"] * 4
        assert [e["processo_id"] for e in lote] == ["PROC-QUANT-02", "PROC-TEXT-01"] * 2

    def test_depois_o_acervo_pelo_peso_da_frente(self):
        lote = _escolher(processos=["PROC-TEXT-01"])
        acervo = [e for e in lote if e["motivo"] == "acervo"]
        # Matemática (peso 1.0) antes de História (0.5).
        assert acervo[0]["item_id"] in {"m1", "m2", "m3", "x1"}
        assert acervo[-1]["item_id"] == "h1"

    def test_ja_respondida_nao_volta_enquanto_houver_inedita(self):
        lote = _escolher(respondidos={"m1", "t1"}, limite=5)
        assert "m1" not in [e["item_id"] for e in lote]

    def test_sem_inedita_o_feed_continua_revendo(self):
        """É o que faz o feed não ter fim."""
        todas = {a["item_id"] for a in ACERVO}
        lote = _escolher(respondidos=todas, processos=["PROC-QUANT-02"], limite=3)
        assert len(lote) == 3 and all(e["motivo"] == "rever" for e in lote)
        assert lote[0]["processo_id"] == "PROC-QUANT-02"

    def test_nunca_repete_o_que_a_tela_ja_mostrou(self):
        lote = _escolher(excluir={"m1", "m2", "m3", "t1", "t2", "h1"})
        assert [e["item_id"] for e in lote] == ["x1"]

    def test_tudo_mostrado_devolve_vazio(self):
        assert _escolher(excluir={a["item_id"] for a in ACERVO}) == []

    def test_teto_do_lote(self):
        assert len(_escolher(limite=50)) <= fq.LOTE_MAX


class TestEntrada:
    def test_processos_so_no_formato_do_catalogo(self):
        assert fq.processos_validos("PROC-QUANT-02, lixo,PROC-TEXT-01,PROC-QUANT-02") == ["PROC-QUANT-02", "PROC-TEXT-01"]

    def test_ids_com_teto(self):
        bruto = ",".join(f"i{n}" for n in range(fq.MAX_EXCLUIR + 50))
        assert len(fq.ids_validos(bruto)) == fq.MAX_EXCLUIR


class TestRota:
    @pytest.fixture
    def rota(self, fake_db, monkeypatch):
        import annotation_service
        import feed_routes
        import firestore_service as fs

        leituras = {"n": 0}

        def _agregado(uid):
            leituras["n"] += 1
            return {"item_ids_respondidos": ["m1"]}

        monkeypatch.setattr(fs, "ler_agregado", _agregado)
        monkeypatch.setattr(annotation_service, "_build_item_index", lambda *a, **k: INDEX)
        feed_routes.set_db(fake_db)
        for a in ACERVO:
            asyncio.run(fake_db.questoes_public.insert_one({
                **a, "master_id": "segredo",
                "questao": {"enunciado": "E", "alternativas": [{"letra": "A", "texto": "a", "correta": True}]},
            }))
        yield feed_routes, leituras
        feed_routes.set_db(None)

    def test_lote_sem_gabarito_e_com_rotulo_de_produto(self, rota, monkeypatch):
        feed_routes, leituras = rota
        from models import User

        import rate_limit
        rate_limit.limpar()
        out = asyncio.run(feed_routes.feed_de_questoes(
            limite=3, excluir=None, processos="PROC-QUANT-02",
            user=User(user_id="a1", email="a@x.com", name="A"), _limite=None,
        ))
        assert leituras["n"] == 1, "uma leitura do Firestore por lote, não por questão"
        ids = [i["item_id"] for i in out["itens"]]
        assert "m1" not in ids  # já respondida
        assert out["itens"][0]["motivo"] == "padrao" and out["itens"][0]["ponto"] == "Proporção"
        for i in out["itens"]:
            assert "master_id" not in i
            assert all("correta" not in alt for alt in i["questao"]["alternativas"])
