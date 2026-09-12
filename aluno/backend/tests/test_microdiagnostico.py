"""Microdiagnóstico (Fase 3) — a evidência que o aluno declara.

A regra que estes testes existem para travar é UMA, e é a mais fácil de perder
numa refatoração bem-intencionada:

    **o autorrelato não entra na escala de confiança do Error Trace.**

O traço tem `produtor: "regra"` e vem do catálogo. O autorrelato tem produtor
próprio e outra epistemologia — o aluno pós-racionaliza, e frequentemente não
sabe por que errou. Fundi-lo ao `peso_raiz` seria inventar vínculo Erro→Processo
fora do catálogo (R-1) e determinizar causa (R-3) de uma vez só.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service  # noqa: E402
import microdiagnostico as micro  # noqa: E402
import motor_cognitivo as motor  # noqa: E402
import portao_crenca  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _limpo():
    micro.esquecer()
    micro.set_db(None)
    motor.esquecer_historico()
    yield
    micro.esquecer()
    micro.set_db(None)
    motor.esquecer_historico()


CADEIA = [
    {"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": 0.7, "mecanismo": "MEC-02"},
    {"ordem": 2, "erro": "ERR-04", "processo_afetado": "PROC-QUANT-04", "confianca": 0.4},
]


def _item():
    return {
        "item_id": "I-1",
        "item_hash": "h-1",
        "ontology_version": "1.4.1",
        "fonte": {"banca": "ENEM", "ano": 2023, "prova": "AMARELO", "numero": 93},
        "estrutura_cognitiva": {"processos": [{"id": "PROC-SIMB-01"}]},
        "qualidade": {"apto_para_camada_de_crenca": {"valor": True}, "revisado": True},
        "distratores": [{"alternativa": "B", "erros_esperados": CADEIA}],
    }


def _evento(n=1, autorrelato=None):
    ev = {
        "event_id": f"e{n}",
        "item_id": "I-1",
        "ontology_version": "1.4.1",
        "status": "respondida",
        "timestamp": f"2026-09-0{n}T10:00:00+00:00",
        "resposta": {"alternativa_escolhida": "B", "acertou": False},
    }
    if autorrelato:
        ev["autorrelato"] = {"opcao": autorrelato, "produtor": micro.PRODUTOR, "par": "ERR-03|PROC-SIMB-01"}
    return ev


# ============================================ a fronteira


class TestNaoAlteraOTraco:
    """O critério de aceite da Fase 3, item por item."""

    def _perfil(self, autorrelatos):
        eventos = [_evento(i + 1, autorrelato=a) for i, a in enumerate(autorrelatos)]
        hist = {
            "tracos": [t for t in (motor.produzir_traco("U1", ev, _item()) for ev in eventos) if t],
            "processo_stats": {"PROC-SIMB-01": {"respondidas": len(eventos), "acertos": 0}},
            "itens_respondidos": {"I-1"},
            "eventos": len(eventos),
            "respondidos": len(eventos),
            "eventos_com_item": len(eventos),
            "erros": len(eventos),
            "falha_de_leitura": False,
        }
        return hist

    def test_autorrelato_nao_altera_peso_raiz_nem_ocorrencias(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)
        sem = self._perfil([None, None, None])
        com = self._perfil(["chute", "nao_sabia", "errei_o_passo"])

        fila_sem = motor._priorizar(sem["tracos"], sem["processo_stats"])
        fila_com = motor._priorizar(com["tracos"], com["processo_stats"])
        assert fila_sem == fila_com, "o autorrelato mexeu na priorização"
        assert fila_com[0]["peso_raiz"] == pytest.approx(2.1)
        assert fila_com[0]["ocorrencias_raiz"] == 3

    def test_autorrelato_nao_altera_mapa_de_erros(self):
        sem = self._perfil([None, None])
        com = self._perfil(["chute", "chute"])
        assert motor._agregar_erros(sem["tracos"]) == motor._agregar_erros(com["tracos"])

    def test_autorrelato_nao_vira_elo_da_cadeia(self):
        t = motor.produzir_traco("U1", _evento(1, autorrelato="chute"), _item())
        assert [e["erro"] for e in t["cadeia"]] == ["ERR-03", "ERR-04"]
        assert t["produtor"] == "regra"
        assert "autorrelato" not in t

    def test_o_motor_nao_le_o_campo_em_lugar_nenhum(self):
        """Se um dia alguém ligar os dois, este teste é o primeiro a cair."""
        fonte = (BACKEND / "motor_cognitivo.py").read_text(encoding="utf-8")
        assert "autorrelato" not in fonte

    def test_produtor_e_declaradamente_outro(self):
        assert micro.PRODUTOR != motor.PRODUTOR
        assert micro.PRODUTOR.startswith("proposta")


class TestAlternativasFechadas:
    def test_texto_livre_nao_e_aceito(self):
        with pytest.raises(ValueError):
            _run(micro.registrar(uid="U1", event_id="e1", opcao="porque sim", chave_par="ERR-03|PROC-SIMB-01"))

    def test_as_cinco_opcoes_sao_estaveis(self):
        assert micro.IDS_VALIDOS == {
            "nao_sabia", "outra_leitura", "errei_o_passo", "entre_duas", "chute",
        }

    def test_so_o_chute_contradiz_qualquer_cadeia(self):
        contradizem = {o["id"] for o in micro.OPCOES if o["contradiz"]}
        assert contradizem == {"chute"}


# ============================================ quando perguntar


class TestQuandoPerguntar:
    def test_acerto_nunca_pergunta(self):
        assert _run(micro.perguntar_por(causa_raiz={"erro_id": "E", "processo_id": "P"}, acertou=True, event_id="e1")) is None

    def test_erro_sem_cadeia_anotada_nao_pergunta(self):
        assert _run(micro.perguntar_por(causa_raiz=None, acertou=False, event_id="e1")) is None

    def test_erro_com_cadeia_pergunta(self):
        p = _run(micro.perguntar_por(causa_raiz={"erro_id": "ERR-03", "processo_id": "PROC-SIMB-01"}, acertou=False, event_id="e1"))
        assert p["par"] == "ERR-03|PROC-SIMB-01"
        assert [o["id"] for o in p["opcoes"]] == [o["id"] for o in micro.OPCOES]

    def test_par_ja_caracterizado_para_de_perguntar(self, fake_db):
        """Onde o valor diagnóstico é alto e a amostra é baixa — passando do
        teto, continuar perguntando só gasta a paciência do aluno."""
        micro.set_db(fake_db)
        _run(fake_db.autorrelato_pares.insert_one(
            {"_id": "ERR-03|PROC-SIMB-01", "total": micro.TETO_AMOSTRA_POR_PAR}
        ))
        assert _run(micro.perguntar_por(
            causa_raiz={"erro_id": "ERR-03", "processo_id": "PROC-SIMB-01"}, acertou=False, event_id="e1"
        )) is None


# ============================================ gravação


class TestGravacao:
    def test_grava_no_evento_em_campo_proprio(self, monkeypatch, fake_db):
        import firestore_service as fs

        micro.set_db(fake_db)
        escrito = {}
        monkeypatch.setattr(fs, "marcar_autorrelato", lambda uid, eid, dados: escrito.update({eid: dados}))
        _run(micro.registrar(uid="U1", event_id="e1", opcao="chute", chave_par="ERR-03|PROC-SIMB-01"))
        assert escrito["e1"]["opcao"] == "chute"
        assert escrito["e1"]["produtor"] == micro.PRODUTOR
        # Nada do contrato 1.1 de behavior é tocado.
        assert set(escrito["e1"]) == {"opcao", "produtor", "par", "em"}

    def test_contador_do_par_sobe(self, monkeypatch, fake_db):
        import firestore_service as fs

        micro.set_db(fake_db)
        monkeypatch.setattr(fs, "marcar_autorrelato", lambda *a, **k: None)
        for _ in range(3):
            _run(micro.registrar(uid="U1", event_id="e1", opcao="chute", chave_par="ERR-03|PROC-SIMB-01"))
        doc = _run(fake_db.autorrelato_pares.find_one({"_id": "ERR-03|PROC-SIMB-01"}))
        assert doc["total"] == 3
        assert doc["por_opcao"]["chute"] == 3

    def test_falha_do_contador_nao_perde_o_relato(self, monkeypatch, fake_db):
        import firestore_service as fs

        class _Quebrado:
            async def update_one(self, *a, **k):
                raise RuntimeError("mongo fora do ar")

            async def find_one(self, *a, **k):
                return None

        class _DB:
            autorrelato_pares = _Quebrado()

        micro.set_db(_DB())
        escrito = {}
        monkeypatch.setattr(fs, "marcar_autorrelato", lambda uid, eid, dados: escrito.update({eid: dados}))
        assert _run(micro.registrar(uid="U1", event_id="e1", opcao="chute", chave_par="P"))["ok"] is True
        assert escrito["e1"]["opcao"] == "chute"


# ============================================ o relatório interno


class TestConcordancia:
    def _pares(self, fake_db, total, chutes):
        micro.set_db(fake_db)
        _run(fake_db.autorrelato_pares.insert_one({
            "_id": "ERR-03|PROC-SIMB-01",
            "total": total,
            "por_opcao": {"chute": chutes, "nao_sabia": total - chutes},
        }))
        return _run(micro.concordancia())["pares"][0]

    def test_amostra_pequena_nunca_vira_suspeita(self, fake_db):
        linha = self._pares(fake_db, total=4, chutes=4)
        assert linha["fracao_contradicao"] == 1.0
        assert linha["suspeita_de_anotacao"] is False
        assert linha["amostra_suficiente"] is False

    def test_contradicao_sistematica_com_amostra_vira_suspeita(self, fake_db):
        linha = self._pares(fake_db, total=12, chutes=9)
        assert linha["suspeita_de_anotacao"] is True
        assert linha["erro_id"] == "ERR-03" and linha["processo_id"] == "PROC-SIMB-01"

    def test_relato_compativel_nao_acusa_a_anotacao(self, fake_db):
        linha = self._pares(fake_db, total=12, chutes=1)
        assert linha["suspeita_de_anotacao"] is False

    def test_sem_mongo_o_relatorio_declara_indisponivel(self):
        micro.set_db(None)
        assert _run(micro.concordancia())["indisponivel"] is True
