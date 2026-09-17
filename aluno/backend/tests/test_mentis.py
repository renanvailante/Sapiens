"""Testes da Mentis — explicação de questão e chat com o dossiê do aluno.

Offline: Firestore, Mongo e Gemini são dublês. O que estes testes protegem,
em ordem de importância:

* **O botão "Saiba mais" não pode voltar a quebrar.** Ele passou a produção
  inteira devolvendo 503 porque pedia `thinking_level="MEDIUM"` com um teto de
  30s — combinação que o modelo nunca cumpre numa questão real. Há um teste
  que trava o nível de raciocínio e o teto de tempo em valores que a medição
  de 2026-09-03 mostrou funcionar.
* **Sparks cobrados por falha da nossa infra têm de voltar.**
* **O custo de uma mensagem do chat não pode crescer com a conversa** — o
  corte do histórico é o que mantém a feature dentro do orçamento.
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
from models import User  # noqa: E402


_ALUNO = User(user_id="U1", email="aluno@exemplo.com", name="Ana Beatriz Souza")


def _diagnostico(fracos=None, padroes=None):
    fracos = fracos if fracos is not None else [
        {"id": f"PROC-{i}", "nome": f"Processo {i}", "acertos": 1, "respondidas": 6, "percentual_acerto": 16.7}
        for i in range(1, 9)
    ]
    return {
        "por_dominio": {"fracos": [{"id": "DOM-1", "nome": "Domínio 1", "acertos": 2, "respondidas": 8, "percentual_acerto": 25.0}], "fortes": []},
        "por_competencia": {"fracos": [], "fortes": []},
        "por_processo": {
            "fracos": fracos,
            "fortes": [{"id": "PROC-9", "nome": "Processo 9", "acertos": 9, "respondidas": 10, "percentual_acerto": 90.0}],
        },
        "padroes_associados": padroes if padroes is not None else [
            {"processo_nome": "Processo 1", "erro_nome": "Troca de referencial",
             "erro_evidencia_observavel": "E" * 400, "intervencao_nome": "Releitura guiada"}
        ],
        "amostra_minima": 3,
        "coverage": 88.0,
    }


class _SparksFalso:
    """Carteira em memória com a mesma interface que `mentis_routes` usa."""

    def __init__(self, saldo=1000):
        self.saldo = saldo
        self.debitos: list[int] = []
        self.reembolsos: list[int] = []

    def instalar(self, monkeypatch):
        monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: self.saldo)
        monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: self.saldo)
        monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
        monkeypatch.setattr(fs, "deduct_sparks", self._debitar)
        monkeypatch.setattr(fs, "refund_sparks", self._reembolsar)
        return self

    def _debitar(self, uid, quanto):
        if self.saldo < quanto:
            raise fs.InsufficientSparksError(balance=self.saldo, needed=quanto)
        self.saldo -= quanto
        self.debitos.append(quanto)
        return self.saldo

    def _reembolsar(self, uid, quanto):
        self.saldo += quanto
        self.reembolsos.append(quanto)
        return self.saldo


# ===================================================== dossiê (sem IA nenhuma)

class TestDossie:
    def test_limita_o_tamanho_do_contexto(self):
        """Aluno com histórico enorme manda o mesmo tamanho de contexto que um
        aluno de duas semanas — é isso que torna o custo por mensagem previsível."""
        dossie = mr._montar_dossie("Ana", _diagnostico(), {"total_respostas": 900, "dias_ativos": ["d"] * 120})
        resumo = dossie["resumo_ui"]
        assert len(resumo["fracos"]) == mr._DOSSIE_MAX_FRACOS
        assert len(resumo["fortes"]) <= mr._DOSSIE_MAX_FORTES
        assert len(resumo["padroes"]) <= mr._DOSSIE_MAX_PADROES
        # a evidência longa entra truncada, não inteira
        assert "E" * mr._EVIDENCIA_MAX_CHARS in dossie["texto"]
        assert "E" * (mr._EVIDENCIA_MAX_CHARS + 1) not in dossie["texto"]

    def test_texto_traz_amostra_junto_de_cada_ponto(self):
        """Percentual sem amostra vira veredito; com amostra continua medida."""
        texto = mr._montar_dossie("Ana", _diagnostico(), {"total_respostas": 40, "dias_ativos": []})["texto"]
        assert "Processo 1 16.7% (1/6)" in texto
        assert "Questões respondidas no total: 40" in texto

    def test_sem_medicao_o_dossie_manda_o_modelo_admitir_isso(self):
        vazio = _diagnostico(fracos=[], padroes=[])
        vazio["por_dominio"] = {"fracos": [], "fortes": []}
        texto = mr._montar_dossie("Ana", vazio, {"total_respostas": 2, "dias_ativos": ["d"]})["texto"]
        assert "AINDA NÃO HÁ MEDIÇÃO SUFICIENTE" in texto
        assert "sem inventar diagnóstico" in texto


class TestAberturaSemIA:
    def test_abertura_cita_o_ponto_fraco_real(self):
        resumo = mr._montar_dossie("Ana", _diagnostico(), {"total_respostas": 40, "dias_ativos": []})["resumo_ui"]
        texto = mr._texto_de_abertura("Ana", resumo)
        assert "Processo 1" in texto and "40" in texto and "(16.7%)" in texto

    def test_abertura_sem_dados_nao_inventa_ponto_fraco(self):
        vazio = _diagnostico(fracos=[], padroes=[])
        resumo = mr._montar_dossie("Ana", vazio, {"total_respostas": 1, "dias_ativos": []})["resumo_ui"]
        texto = mr._texto_de_abertura("Ana", resumo)
        assert "1 questão respondida" in texto
        assert "Ainda é pouco" in texto


class TestCorteDoHistorico:
    def test_so_as_ultimas_trocas_acompanham_a_pergunta(self):
        mensagens = [{"papel": "aluno" if i % 2 else "mentis", "texto": f"m{i}"} for i in range(20)]
        prompt = mr._montar_prompt_chat("DOSSIE", mensagens, "pergunta nova")
        assert "m19" in prompt and "m14" in prompt
        assert "m13" not in prompt  # 3 trocas = 6 mensagens
        assert "DOSSIE" in prompt and "pergunta nova" in prompt


# ===================================================== chat: sessão e cobrança

def _abrir(monkeypatch, fake_db, carteira):
    mr.set_db(fake_db)
    monkeypatch.setattr(fs, "ler_agregado", lambda uid: {"total_respostas": 40, "dias_ativos": ["a", "b"]})

    async def _diag(uid):
        return _diagnostico()

    monkeypatch.setattr(mr.annotation_service, "compute_diagnostico_real", _diag)
    return asyncio.run(mr.abrir_sessao(user=_ALUNO))


class TestSessao:
    def test_abrir_cobra_70_e_nao_chama_o_modelo(self, monkeypatch, fake_db):
        """A abertura é determinística de propósito: as 70 Sparks compram
        acesso, não uma chamada de IA que não acrescentaria nada ao dado."""
        carteira = _SparksFalso().instalar(monkeypatch)

        async def _explode(*a, **k):
            raise AssertionError("a abertura não pode chamar o Gemini")

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _explode)

        out = _abrir(monkeypatch, fake_db, carteira)
        assert carteira.debitos == [mr.SESSAO_COST] == [70]
        assert out["nova"] is True
        assert len(out["mensagens"]) == 1 and out["mensagens"][0]["papel"] == "mentis"
        assert "Processo 1" in out["mensagens"][0]["texto"]

    def test_reabrir_dentro_da_janela_nao_cobra_de_novo(self, monkeypatch, fake_db):
        """Recarregar a página não pode custar 70 Sparks."""
        carteira = _SparksFalso().instalar(monkeypatch)
        _abrir(monkeypatch, fake_db, carteira)
        de_novo = asyncio.run(mr.abrir_sessao(user=_ALUNO))
        assert carteira.debitos == [70]
        assert de_novo["nova"] is False

    def test_sessao_vencida_nao_e_retomada(self, monkeypatch, fake_db):
        carteira = _SparksFalso().instalar(monkeypatch)
        _abrir(monkeypatch, fake_db, carteira)
        vencida = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        fake_db.mentis_sessoes.docs[0]["expira_em"] = vencida
        assert asyncio.run(mr.ler_sessao(user=_ALUNO))["ativa"] is False

    def test_saldo_insuficiente_devolve_402(self, monkeypatch, fake_db):
        _SparksFalso(saldo=10).instalar(monkeypatch)
        mr.set_db(fake_db)
        with pytest.raises(HTTPException) as exc:
            _abrir(monkeypatch, fake_db, None)
        assert exc.value.status_code == 402

    def test_falha_ao_montar_o_dossie_devolve_as_sparks(self, monkeypatch, fake_db):
        carteira = _SparksFalso().instalar(monkeypatch)
        mr.set_db(fake_db)
        monkeypatch.setattr(fs, "ler_agregado", lambda uid: {})

        async def _falha(uid):
            raise RuntimeError("Firestore fora do ar")

        monkeypatch.setattr(mr.annotation_service, "compute_diagnostico_real", _falha)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mr.abrir_sessao(user=_ALUNO))
        assert exc.value.status_code == 503
        assert carteira.reembolsos == [70] and carteira.saldo == 1000


class TestMensagem:
    def _preparar(self, monkeypatch, fake_db):
        carteira = _SparksFalso().instalar(monkeypatch)
        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", lambda *a, **k: None)
        _abrir(monkeypatch, fake_db, carteira)
        return carteira

    def test_cobra_10_e_grava_as_duas_falas(self, monkeypatch, fake_db):
        carteira = self._preparar(monkeypatch, fake_db)

        async def _resposta(system, prompt, **kwargs):
            assert kwargs["thinking_level"] == "MINIMAL"
            return {"resposta": "Você troca o referencial no meio da conta."}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _resposta)
        out = asyncio.run(mr.enviar_mensagem(mr.MensagemPayload(texto="Por que eu erro tanto?"), user=_ALUNO))
        assert carteira.debitos == [70, 10]
        assert [m["papel"] for m in out["mensagens"]] == ["aluno", "mentis"]
        assert len(fake_db.mentis_sessoes.docs[0]["mensagens"]) == 3

    def test_o_dossie_vai_no_prompt_de_toda_mensagem(self, monkeypatch, fake_db):
        """Sem isso o chat responderia genérico — o valor das 70 Sparks é
        justamente o modelo já saber quem está do outro lado."""
        self._preparar(monkeypatch, fake_db)
        visto = {}

        async def _captura(system, prompt, **kwargs):
            visto["prompt"] = prompt
            return {"resposta": "ok"}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _captura)
        asyncio.run(mr.enviar_mensagem(mr.MensagemPayload(texto="e agora?"), user=_ALUNO))
        assert "Processo 1 16.7% (1/6)" in visto["prompt"]

    def test_falha_do_modelo_devolve_as_sparks(self, monkeypatch, fake_db):
        carteira = self._preparar(monkeypatch, fake_db)

        async def _falha(*a, **k):
            raise mr.ai_service.GeminiIndisponivelError("fora do ar")

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _falha)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mr.enviar_mensagem(mr.MensagemPayload(texto="oi"), user=_ALUNO))
        assert exc.value.status_code == 503
        assert carteira.reembolsos == [10]

    def test_resposta_vazia_do_modelo_tambem_devolve(self, monkeypatch, fake_db):
        carteira = self._preparar(monkeypatch, fake_db)

        async def _vazia(*a, **k):
            return {"resposta": "   "}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _vazia)
        with pytest.raises(HTTPException):
            asyncio.run(mr.enviar_mensagem(mr.MensagemPayload(texto="oi"), user=_ALUNO))
        assert carteira.reembolsos == [10]

    def test_sem_sessao_ativa_nao_cobra_nada(self, monkeypatch, fake_db):
        carteira = _SparksFalso().instalar(monkeypatch)
        mr.set_db(fake_db)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mr.enviar_mensagem(mr.MensagemPayload(texto="oi"), user=_ALUNO))
        assert exc.value.status_code == 409
        assert carteira.debitos == []

    def test_mensagem_longa_e_recusada_antes_de_chegar_ao_modelo(self):
        with pytest.raises(Exception):
            mr.MensagemPayload(texto="x" * (mr._MENSAGEM_MAX_CHARS + 1))


# ===================================== explicação: a regressão que quebrou o botão

class TestExplicacao:
    _ITEM = {
        "item_id": "IT-1",
        "item_hash": "h1",
        "questao": {
            "enunciado": "Um pescador tem custo fixo diário de R$ 900,00...",
            "alternativas": [{"letra": "A", "texto": "1"}, {"letra": "C", "texto": "3", "correta": True}],
        },
        "fonte": {"disciplina": "Matemática"},
    }

    def _com_item(self, fake_db):
        mr.set_db(fake_db)
        fake_db.questoes_public.docs.append(dict(self._ITEM))

    def test_usa_raciocinio_minimo_e_orcamento_curto_com_teto_de_saida(self, monkeypatch, fake_db):
        """Duas regressões, uma em cima da outra.

        A de 03/09: com `thinking=MEDIUM` sob o teto global de 30 s o modelo
        NUNCA respondia a tempo. Medição no mesmo item: MINIMAL 4,3 s /
        LOW 83,4 s / MEDIUM 503 aos 37 s. A correção de então foi MINIMAL
        mais um teto de tempo PRÓPRIO e generoso (60 s).

        A de 17/09: aquele teto generoso era por TENTATIVA, e
        `generate_json_resiliente` faz duas — o pior caso virou 120 s de tela
        parada, que é a "Mentis demorando quase 1 minuto". A correção agora é
        pelo outro lado: `timeout` passa a ser o orçamento TOTAL e curto, e o
        que o torna realista é `max_output_tokens`, porque numa resposta em
        streaming o tempo acompanha o que o modelo escreve.

        Por isso o teto de tempo agora é asseverado para BAIXO, não para
        cima: subir este número de novo é reintroduzir a espera."""
        self._com_item(fake_db)
        _SparksFalso().instalar(monkeypatch)
        visto = {}

        async def _resposta(system, prompt, **kwargs):
            visto.update(kwargs)
            return {"paragrafos": ["um", "dois", "três"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _resposta)
        out = asyncio.run(mr.gerar_explicacao(mr.ExplicacaoPayload(item_id="IT-1"), user=_ALUNO))
        assert visto["thinking_level"] == "MINIMAL"
        assert visto["timeout"] <= 15  # orçamento TOTAL do aluno, não por tentativa
        assert visto["max_output_tokens"] > 0  # sem teto de saída, não há teto de espera
        assert out["paragrafos"] == ["um", "dois", "três"] and out["cache"] is False

    def test_segundo_aluno_le_do_cache_sem_nova_chamada(self, monkeypatch, fake_db):
        self._com_item(fake_db)
        carteira = _SparksFalso().instalar(monkeypatch)
        chamadas = []

        async def _resposta(*a, **k):
            chamadas.append(1)
            return {"paragrafos": ["um", "dois", "três"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _resposta)
        asyncio.run(mr.gerar_explicacao(mr.ExplicacaoPayload(item_id="IT-1"), user=_ALUNO))
        segundo = asyncio.run(mr.gerar_explicacao(mr.ExplicacaoPayload(item_id="IT-1"), user=_ALUNO))
        assert len(chamadas) == 1
        assert segundo["cache"] is True
        # decisão de produto mantida: cache hit ainda cobra, o valor entregue é o mesmo
        assert carteira.debitos == [7, 7]

    def test_resposta_curta_demais_nao_e_entregue_e_devolve_as_sparks(self, monkeypatch, fake_db):
        self._com_item(fake_db)
        carteira = _SparksFalso().instalar(monkeypatch)

        async def _curta(*a, **k):
            return {"paragrafos": ["só um"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _curta)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mr.gerar_explicacao(mr.ExplicacaoPayload(item_id="IT-1"), user=_ALUNO))
        assert exc.value.status_code == 503
        assert carteira.reembolsos == [7]

    def test_item_sem_gabarito_nao_cobra(self, monkeypatch, fake_db):
        mr.set_db(fake_db)
        carteira = _SparksFalso().instalar(monkeypatch)
        fake_db.questoes_public.docs.append(
            {"item_id": "IT-2", "questao": {"enunciado": "x", "alternativas": [{"letra": "A", "texto": "1"}]}}
        )
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mr.gerar_explicacao(mr.ExplicacaoPayload(item_id="IT-2"), user=_ALUNO))
        assert exc.value.status_code == 409
        assert carteira.debitos == []


class TestAcaoDeNavegacao:
    """A Mentis como camada de navegação: ela pode LEVAR o aluno a uma tela.

    O que estes testes travam é o que impede um botão quebrado de chegar ao
    aluno: o modelo escolhe uma CHAVE de uma lista fechada, nunca uma URL.
    """

    def test_destino_do_catalogo_vira_rota_e_rotulo(self):
        acao = mr._validar_acao({"tipo": "ir", "destino": "mapa_treino"})
        assert acao == {
            "tipo": "ir",
            "destino": "mapa_treino",
            "rota": "/treino",
            "rotulo": "Abrir o Mapa de Treino",
        }

    def test_destino_inventado_e_descartado(self):
        assert mr._validar_acao({"tipo": "ir", "destino": "tela_que_nao_existe"}) is None

    def test_url_no_lugar_da_chave_e_descartada(self):
        """O modelo não escreve rota. Se tentar, a ação morre aqui — nunca
        vira um botão que leva o aluno para fora do produto."""
        assert mr._validar_acao({"tipo": "ir", "destino": "https://exemplo.com"}) is None
        assert mr._validar_acao({"tipo": "ir", "destino": "/admin/users"}) is None

    def test_todo_destino_do_catalogo_e_uma_rota_interna(self):
        for chave, alvo in mr.DESTINOS.items():
            assert alvo["rota"].startswith("/"), chave
            assert not alvo["rota"].startswith("//"), chave
            assert alvo["rotulo"], chave
