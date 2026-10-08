"""Notificação no celular — a escolha da mensagem, o teto de 1/dia e a janela.

Offline: `fake_db` no lugar do Mongo, um dublê de `ler_estado_do_aluno` no
lugar do Firestore e um transporte falso no lugar do serviço de push.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

import firestore_service as fs
import push
import push_service

HOJE = "2026-10-06"
ONTEM = "2026-10-05"
ANTEONTEM = "2026-10-04"


def _run(coro):
    return asyncio.run(coro)


def _as(hora: int, minuto: int = 0, dia: str = HOJE) -> datetime:
    a, m, d = (int(x) for x in dia.split("-"))
    return datetime(a, m, d, hora, minuto, tzinfo=fs.ZONA_BRASIL)


# =============================================================== a mensagem

def _sinais(**kw):
    base = {
        "ofensiva": {"dias": 0, "estudou_hoje": False, "em_risco": False},
        "trechos_hoje": 0,
        "revisoes_hoje": 0,
        "padrao": None,
        "missao": None,
    }
    base.update(kw)
    return base


SEQUENCIA_EM_RISCO = {"dias": 12, "estudou_hoje": False, "em_risco": True}
MISSAO = {"titulo": "Responda 5 questões", "progresso": 2, "alvo": 5, "sparks": 5, "concluida": False}


class TestEscolhaDaMensagem:
    def test_sequencia_em_risco_vence_tudo(self):
        m = push.escolher_mensagem(_sinais(
            ofensiva=SEQUENCIA_EM_RISCO, trechos_hoje=3, revisoes_hoje=2,
            padrao={"questoes_novas": 7}, missao=MISSAO,
        ))
        assert m["tipo"] == "sequencia"
        assert "12 dias" in m["titulo"] and "meia-noite" in m["titulo"]

    def test_trechos_e_revisoes_vencem_padrao_e_missao(self):
        m = push.escolher_mensagem(_sinais(trechos_hoje=2, revisoes_hoje=1, padrao={"questoes_novas": 7}, missao=MISSAO))
        assert m["tipo"] == "revisao"
        assert m["titulo"] == "2 trechos que você guardou e 1 revisão voltaram hoje"

    def test_so_trechos_leva_a_lista_de_trechos(self):
        m = push.escolher_mensagem(_sinais(trechos_hoje=1))
        assert m["titulo"] == "1 trecho que você guardou voltou hoje"
        assert m["rota"].endswith("#lembretes")

    def test_padrao_vence_missao(self):
        m = push.escolher_mensagem(_sinais(padrao={"questoes_novas": 4}, missao=MISSAO))
        assert m["tipo"] == "padrao"
        assert m["titulo"].startswith("4 questões novas")

    def test_missao_com_numero_real(self):
        m = push.escolher_mensagem(_sinais(missao=MISSAO))
        assert m["tipo"] == "missao"
        assert "Responda 5 questões" in m["titulo"]
        assert "2/5" in m["corpo"] and "+5 Sparks" in m["corpo"]

    def test_sem_sinal_nenhum_nao_manda_nada(self):
        assert push.escolher_mensagem(_sinais()) is None
        assert push.escolher_mensagem(None) is None

    def test_quem_ja_estudou_hoje_nao_recebe_aviso_de_sequencia(self):
        m = push.escolher_mensagem(_sinais(ofensiva={"dias": 12, "estudou_hoje": True, "em_risco": False}))
        assert m is None

    def test_missao_cumprida_nao_vira_mensagem(self):
        assert push.escolher_mensagem(_sinais(missao={**MISSAO, "concluida": True})) is None

    def test_nenhum_nome_de_ponto_fraco_na_mensagem(self):
        """Os nomes reais da ontologia nunca chegam ao aluno — e a bandeja do
        celular é lida por cima do ombro."""
        m = push.escolher_mensagem(_sinais(padrao={"questoes_novas": 3, "processo_nome": "PROC-07 Interpretar"}))
        assert "PROC" not in m["titulo"] + m["corpo"]
        assert "Interpretar" not in m["titulo"] + m["corpo"]


# =============================================================== a janela

class TestJanela:
    @pytest.mark.parametrize("hora,ok", [(7, False), (8, True), (12, True), (20, True), (21, False), (23, False), (0, False)])
    def test_so_entre_8h_e_21h(self, hora, ok):
        assert push.dentro_da_janela(_as(hora, 59 if hora == 20 else 0)) is ok

    def test_avaliacao_comeca_na_hora_configurada(self):
        assert not push.hora_de_avaliar(_as(18, 59), 19)
        assert push.hora_de_avaliar(_as(19), 19)
        assert not push.hora_de_avaliar(_as(21), 19)

    @pytest.mark.parametrize("bruto", ["5", "21", "lixo", None, "-1"])
    def test_hora_fora_da_janela_volta_ao_padrao(self, bruto):
        assert push.hora_da_avaliacao(bruto) == push.HORA_DA_AVALIACAO_PADRAO

    def test_hora_dentro_da_janela_e_respeitada(self):
        assert push.hora_da_avaliacao("10") == 10


# =============================================================== o endpoint

class TestEndpoint:
    @pytest.mark.parametrize("url", [
        "https://fcm.googleapis.com/fcm/send/abc",
        "https://updates.push.services.mozilla.com/wpush/v2/abc",
        "https://web.push.apple.com/QABC",
        "https://wns2-par02p.notify.windows.com/w/?token=abc",
    ])
    def test_servicos_de_push_reais(self, url):
        assert push.endpoint_valido(url)

    @pytest.mark.parametrize("url", [
        "http://fcm.googleapis.com/fcm/send/abc",           # sem TLS
        "https://169.254.169.254/latest/meta-data",         # SSRF
        "https://fcm.googleapis.com.evil.com/x",            # sufixo falso
        "https://evilfcm.googleapis.com.attacker.io/x",
        "https://fcm.googleapis.com:8443/x",                # porta estranha
        "", None, 42, "https://" + "a" * 3000,
    ])
    def test_qualquer_outro_endereco_e_recusado(self, url):
        assert not push.endpoint_valido(url)


# =============================================================== o laço

class _Transporte:
    def __init__(self, falhar_com: int | None = None):
        self.chamadas: list[tuple[str, str]] = []
        self.falhar_com = falhar_com

    def __call__(self, inscricao, corpo):
        self.chamadas.append((inscricao["endpoint"], corpo))
        if self.falhar_com:
            class _Resp:
                status_code = self.falhar_com

            erro = RuntimeError("push recusado")
            erro.response = _Resp()
            raise erro


@pytest.fixture
def servico(fake_db, monkeypatch):
    push_service.set_db(fake_db)
    estados = {}

    def _ler_estado(uid):
        if estados.get(uid) == "falha":
            raise RuntimeError("cota")
        return estados.get(uid) or {"agregado": {}, "revisao": {}}

    monkeypatch.setattr(fs, "ler_estado_do_aluno", _ler_estado)
    monkeypatch.setattr(push_service, "PUSH_HORA_AVALIACAO", 19)
    yield fake_db, estados
    push_service.set_db(None)


def _inscrever(uid, n=1):
    for i in range(n):
        _run(push_service.inscrever(
            uid, f"https://fcm.googleapis.com/fcm/send/{uid}-{i}", "p" * 87, "a" * 22,
        ))


class TestLaco:
    def test_sequencia_em_risco_sai_uma_vez_so_no_dia(self, servico):
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [ONTEM, ANTEONTEM]}, "revisao": {}}
        _inscrever("aluno-1")
        t = _Transporte()

        r1 = _run(push_service.ciclo(_as(19, 5), transporte=t))
        r2 = _run(push_service.ciclo(_as(19, 20), transporte=t))
        r3 = _run(push_service.ciclo(_as(20, 50), transporte=t))

        assert r1["enviados"] == 1
        assert r2["enviados"] == 0 and r3["enviados"] == 0
        assert len(t.chamadas) == 1
        assert '"tipo": "sequencia"' in t.chamadas[0][1]
        assert "2 dias" in t.chamadas[0][1]

    def test_no_dia_seguinte_volta_a_avaliar(self, servico):
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [ONTEM]}, "revisao": {}}
        _inscrever("aluno-1")
        t = _Transporte()
        _run(push_service.ciclo(_as(19), transporte=t))
        estados["aluno-1"] = {"agregado": {"dias_ativos": [HOJE, ONTEM]}, "revisao": {}}
        _run(push_service.ciclo(_as(19, dia="2026-10-07"), transporte=t))
        assert len(t.chamadas) == 2

    def test_um_por_dia_mesmo_com_varios_aparelhos(self, servico):
        """O teto é por ALUNO: dois aparelhos recebem a mesma notificação, uma
        vez cada, e o dia está gasto."""
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [ONTEM]}, "revisao": {}}
        _inscrever("aluno-1", n=2)
        t = _Transporte()
        _run(push_service.ciclo(_as(19), transporte=t))
        _run(push_service.ciclo(_as(19, 30), transporte=t))
        assert len(t.chamadas) == 2
        assert len({c[0] for c in t.chamadas}) == 2

    def test_duas_maquinas_nao_mandam_em_dobro(self, servico):
        """A reivindicação é o `_id` do dia: a segunda máquina esbarra nela."""
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [ONTEM]}, "revisao": {}}
        _inscrever("aluno-1")
        _run(db.push_envios.insert_one({"_id": push.chave_do_dia("aluno-1", HOJE), "user_id": "aluno-1", "dia": "outro"}))
        t = _Transporte()
        _run(push_service.ciclo(_as(19), transporte=t))
        assert t.chamadas == []

    def test_fora_do_horario_nao_toca_em_nada(self, servico):
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [ONTEM]}, "revisao": {}}
        _inscrever("aluno-1")
        t = _Transporte()
        for hora in (7, 12, 18, 21, 23):
            r = _run(push_service.ciclo(_as(hora), transporte=t))
            assert r["motivo"] == "fora_do_horario"
        assert t.chamadas == []
        assert _run(db.push_envios.count_documents({})) == 0

    def test_leitura_que_falhou_nao_vira_aviso(self, servico):
        db, estados = servico
        estados["aluno-1"] = "falha"
        _inscrever("aluno-1")
        t = _Transporte()
        r = _run(push_service.ciclo(_as(19), transporte=t))
        assert r["indisponiveis"] == 1 and t.chamadas == []

    def test_aluno_sem_sinal_nao_recebe_nada(self, servico, monkeypatch):
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [HOJE]}, "revisao": {}}
        _inscrever("aluno-1")
        # Todas as missões do dia cumpridas.
        _run(db.engajamento_dia.insert_one({
            "_id": f"aluno-1:{HOJE}",
            "contadores": {"questoes": 50, "acertos": 50, "revisoes": 5, "blocos": 5, "treino": 50, "respostas_comunidade": 5},
        }))
        t = _Transporte()
        r = _run(push_service.ciclo(_as(19), transporte=t))
        assert r["sem_mensagem"] == 1 and t.chamadas == []

    def test_trecho_que_voltou_hoje_vira_aviso(self, servico):
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [HOJE]}, "revisao": {}}
        _inscrever("aluno-1")
        _run(db.lembretes_revisao.insert_one({
            "_id": "aluno-1:x", "user_id": "aluno-1", "status": "aberto",
            "agendamento": {"estado": "agendado", "revisar_em": HOJE},
        }))
        _run(db.lembretes_revisao.insert_one({
            "_id": "aluno-1:y", "user_id": "aluno-1", "status": "aberto",
            "agendamento": {"estado": "agendado", "revisar_em": "2026-10-09"},
        }))
        t = _Transporte()
        _run(push_service.ciclo(_as(19), transporte=t))
        assert len(t.chamadas) == 1
        assert "1 trecho que você guardou voltou hoje" in t.chamadas[0][1]

    def test_inscricao_morta_e_apagada(self, servico):
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [ONTEM]}, "revisao": {}}
        _inscrever("aluno-1")
        _run(push_service.ciclo(_as(19), transporte=_Transporte(falhar_com=410)))
        assert _run(db.push_inscricoes.count_documents({"user_id": "aluno-1"})) == 0

    def test_falha_temporaria_nao_apaga_a_inscricao(self, servico):
        db, estados = servico
        estados["aluno-1"] = {"agregado": {"dias_ativos": [ONTEM]}, "revisao": {}}
        _inscrever("aluno-1")
        _run(push_service.ciclo(_as(19), transporte=_Transporte(falhar_com=500)))
        assert _run(db.push_inscricoes.count_documents({"user_id": "aluno-1"})) == 1


class TestInscricao:
    def test_mesmo_aparelho_e_a_mesma_linha_e_troca_de_dono(self, servico):
        db, _ = servico
        ep = "https://fcm.googleapis.com/fcm/send/aparelho"
        _run(push_service.inscrever("aluno-1", ep, "p" * 87, "a" * 22))
        _run(push_service.inscrever("aluno-2", ep, "p" * 87, "a" * 22))
        docs = _run(db.push_inscricoes.find({}).to_list(None))
        assert len(docs) == 1 and docs[0]["user_id"] == "aluno-2"

    def test_teto_de_aparelhos(self, servico):
        db, _ = servico
        _inscrever("aluno-1", n=push_service.MAX_INSCRICOES_POR_ALUNO + 2)
        assert _run(db.push_inscricoes.count_documents({"user_id": "aluno-1"})) == push_service.MAX_INSCRICOES_POR_ALUNO

    def test_desinscrever_so_apaga_o_proprio(self, servico):
        db, _ = servico
        ep = "https://fcm.googleapis.com/fcm/send/aparelho"
        _run(push_service.inscrever("aluno-1", ep, "p" * 87, "a" * 22))
        assert _run(push_service.desinscrever("aluno-2", ep))["removida"] is False
        assert _run(push_service.desinscrever("aluno-1", ep))["removida"] is True


class TestVapid:
    def test_chave_publica_derivada_do_secret(self, monkeypatch):
        from py_vapid import Vapid01

        v = Vapid01()
        v.generate_keys()
        import base64

        numero = v.private_key.private_numbers().private_value.to_bytes(32, "big")
        monkeypatch.setenv("VAPID_PRIVATE_KEY", base64.urlsafe_b64encode(numero).decode().rstrip("="))
        chave = push_service.chave_publica()
        assert chave and len(base64.urlsafe_b64decode(chave + "==")) == 65

    def test_sem_secret_nao_ha_push(self, monkeypatch):
        monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
        assert push_service.chave_publica() is None
