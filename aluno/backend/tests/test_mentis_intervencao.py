"""Intervenção da Mentis (10 Sparks) — reutilização, cobrança e limites.

O que estes testes existem para impedir:

1. **Gerar de novo o que já existe.** A intervenção é indexada pela CAUSA
   (erro × processo), não pelo aluno. Dois alunos com a mesma dificuldade
   precisam custar UMA chamada de IA no total, nunca duas.
2. **Cobrar duas vezes a mesma pessoa.** Refresh, re-render e voltar pelo
   Painel são a mesma compra — o desbloqueio é que decide, não o cache.
3. **Aceitar par inventado.** Um `erro_id`/`processo_id` que o catálogo não
   autoriza (R-1) viraria chave de cache nova e uma geração desperdiçada.
4. **Encostar no "Saiba mais".** São 7 Sparks, outra pergunta, outro cache.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import feedback_templates  # noqa: E402
import intervencoes  # noqa: E402
import mentis_routes as mr  # noqa: E402
import motor_cognitivo as motor  # noqa: E402

CONTEUDO_OK = {
    "o_que_acontece": "Você aceita o primeiro sentido que o texto sugere.",
    "exemplo": {
        "situacao": "Um gráfico mostra duas curvas subindo juntas.",
        "raciocinio_errado": "Se sobem juntas, uma causa a outra.",
        "correcao": "Procure a terceira variável antes de afirmar causa.",
    },
    "treino": ["Marque premissa e conclusão.", "Procure contraexemplo.", "Cheque a ordem no tempo."],
    "sinal_de_alerta": "A resposta parece óbvia rápido demais.",
    "checagem": "O texto sustenta isso, ou fui eu que completei?",
}


class ColecaoFalsa:
    """Dublê de coleção Mongo — assíncrona, como o motor real."""

    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.leituras = 0
        self.escritas = 0

    async def find_one(self, filtro, *args, **kwargs):
        self.leituras += 1
        return self.docs.get(filtro["_id"])

    async def update_one(self, filtro, update, upsert=False):
        self.escritas += 1
        doc = self.docs.setdefault(filtro["_id"], {"_id": filtro["_id"]})
        doc.update(update.get("$set") or {})


class DBFalso:
    def __init__(self):
        self.mentis_intervencoes = ColecaoFalsa()
        self.mentis_intervencoes_abertas = ColecaoFalsa()
        self.mentis_llm_chamadas = ColecaoFalsa()


class Usuario:
    def __init__(self, uid):
        self.user_id = uid
        self.name = "Aluno"
        self.email = f"{uid}@x.com"


@pytest.fixture()
def ambiente(monkeypatch):
    db = DBFalso()
    monkeypatch.setattr(mr, "_db", db)
    chamadas = {"gemini": 0, "cobrancas": [], "reembolsos": []}

    async def _gemini(system, prompt, **kwargs):
        chamadas["gemini"] += 1
        return dict(CONTEUDO_OK)

    monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _gemini)
    monkeypatch.setattr(mr, "_cobrar", lambda uid, custo: chamadas["cobrancas"].append((uid, custo)) or 999)
    monkeypatch.setattr(mr, "_safe_reembolso", lambda uid, custo: chamadas["reembolsos"].append((uid, custo)) or 0)

    async def _telemetria(*a, **k):
        return None

    monkeypatch.setattr(mr.llm_telemetry, "persist", _telemetria)
    return db, chamadas


def _payload(erro="ERR-07", processo="PROC-CAUSAL-01"):
    return mr.IntervencaoPayload(erro_id=erro, processo_id=processo)


class TestCausaRaizVemDeGraca:
    """`register_answer` já carregou o item para o feedback — a causa sai da
    mesma leitura de cadeia, sem tocar no banco de novo."""

    MASTER = {
        "item": {
            "distratores": [{
                "alternativa": "B",
                "erros_esperados": [
                    {"ordem": 1, "erro": "ERR-07", "processo_afetado": "PROC-CAUSAL-01", "confianca": 0.7},
                    {"ordem": 2, "erro": "ERR-08", "processo_afetado": "PROC-INC-03", "confianca": 0.4},
                ],
            }]
        }
    }

    def test_devolve_a_raiz_e_nao_a_manifestacao(self):
        assert feedback_templates.causa_raiz(self.MASTER, "B") == {
            "erro_id": "ERR-07", "processo_id": "PROC-CAUSAL-01",
        }

    def test_alternativa_sem_distrator_nao_tem_causa(self):
        assert feedback_templates.causa_raiz(self.MASTER, "D") is None

    def test_sem_master_nao_inventa(self):
        assert feedback_templates.causa_raiz(None, "B") is None


class TestParContraOCatalogo:
    def test_par_autorizado_passa(self):
        assert motor.par_diagnostico("ERR-07", "PROC-CAUSAL-01")["intervencao_id"] == "INT-08"

    def test_par_inventado_e_recusado(self):
        assert motor.par_diagnostico("ERR-07", "PROC-SIMB-01") is None

    def test_processo_inexistente_e_recusado(self):
        assert motor.par_diagnostico("ERR-07", "PROC-NAO-EXISTE") is None

    def test_sentinela_vale_mas_nao_prescreve(self):
        par = motor.par_diagnostico("erro-nao-catalogado-nesta-versao", "PROC-ESPACO-01")
        assert par["sentinela"] is True and par["intervencao_id"] is None


class TestReutilizacaoEntreAlunos:
    """O cenário que justifica o desenho inteiro."""

    def test_segundo_aluno_com_a_mesma_dificuldade_nao_gera_de_novo(self, ambiente):
        db, ch = ambiente
        a = asyncio.run(mr.abrir_intervencao(_payload(), user=Usuario("aluno-1"), _=None))
        b = asyncio.run(mr.abrir_intervencao(_payload(), user=Usuario("aluno-2"), _=None))

        assert ch["gemini"] == 1, "a mesma causa foi gerada duas vezes"
        assert a["conteudo"] == b["conteudo"]
        assert a["gerada_agora"] is True and b["gerada_agora"] is False
        # Cada aluno paga o seu acesso; o que não se paga duas vezes é a geração.
        assert ch["cobrancas"] == [("aluno-1", 10), ("aluno-2", 10)]

    def test_causas_diferentes_geram_conteudos_diferentes(self, ambiente):
        db, ch = ambiente
        asyncio.run(mr.abrir_intervencao(_payload("ERR-07", "PROC-CAUSAL-01"), user=Usuario("a"), _=None))
        asyncio.run(mr.abrir_intervencao(_payload("ERR-01", "PROC-TEXT-01"), user=Usuario("a"), _=None))
        assert ch["gemini"] == 2
        assert len(db.mentis_intervencoes.docs) == 2


class TestCobrancaUnicaPorAluno:
    def test_reabrir_nao_cobra_de_novo(self, ambiente):
        db, ch = ambiente
        u = Usuario("aluno-1")
        primeiro = asyncio.run(mr.abrir_intervencao(_payload(), user=u, _=None))
        for _ in range(4):  # refresh, voltar pelo Painel, reabrir na questão
            repetido = asyncio.run(mr.abrir_intervencao(_payload(), user=u, _=None))

        assert ch["cobrancas"] == [("aluno-1", 10)], "cobrou mais de uma vez a mesma pessoa"
        assert primeiro["cobrado"] == 10 and repetido["cobrado"] == 0
        assert repetido["conteudo"] == primeiro["conteudo"]
        assert ch["gemini"] == 1

    def test_previa_e_gratuita_e_sem_ia(self):
        """O botão de 10 Sparks não pode ser uma caixa fechada: o objetivo da
        intervenção é texto autoral já existente, servido sem custo nenhum."""
        previa = intervencoes.previa("ERR-07")
        assert previa["intervencao_id"] == "INT-08"
        assert previa["objetivo"] and len(previa["como_praticar"]) >= 3

    def test_previa_de_sentinela_nao_promete_intervencao(self):
        previa = intervencoes.previa("erro-nao-catalogado-nesta-versao")
        assert previa["intervencao_id"] is None and previa["objetivo"]

    def test_leitura_de_desbloqueio_quebrada_nao_cobra_no_escuro(self, ambiente, monkeypatch):
        """Sem saber se já pagou, cobrar de novo é o erro caro e irreversível."""
        db, ch = ambiente

        async def _quebrado(*a, **k):
            raise RuntimeError("mongo fora")

        monkeypatch.setattr(db.mentis_intervencoes_abertas, "find_one", _quebrado)
        asyncio.run(mr.abrir_intervencao(_payload(), user=Usuario("aluno-1"), _=None))
        assert ch["cobrancas"] == []


class TestFalhasEBordas:
    def test_par_invalido_nao_cobra_nem_gera(self, ambiente):
        db, ch = ambiente
        with pytest.raises(mr.HTTPException) as exc:
            asyncio.run(mr.abrir_intervencao(_payload("ERR-07", "PROC-SIMB-01"), user=Usuario("a"), _=None))
        assert exc.value.status_code == 422
        assert ch["cobrancas"] == [] and ch["gemini"] == 0

    def test_saldo_insuficiente_nao_gera_conteudo(self, ambiente, monkeypatch):
        db, ch = ambiente

        def _sem_saldo(uid, custo):
            raise mr.HTTPException(status_code=402, detail="Sparks insuficientes")

        monkeypatch.setattr(mr, "_cobrar", _sem_saldo)
        with pytest.raises(mr.HTTPException) as exc:
            asyncio.run(mr.abrir_intervencao(_payload(), user=Usuario("pobre"), _=None))
        assert exc.value.status_code == 402
        assert ch["gemini"] == 0
        assert db.mentis_intervencoes_abertas.docs == {}

    def test_ia_fora_do_ar_devolve_os_sparks_e_nao_desbloqueia(self, ambiente, monkeypatch):
        db, ch = ambiente

        async def _explode(*a, **k):
            raise RuntimeError("503 UNAVAILABLE")

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _explode)
        with pytest.raises(mr.HTTPException) as exc:
            asyncio.run(mr.abrir_intervencao(_payload(), user=Usuario("aluno-1"), _=None))
        assert exc.value.status_code == 503
        assert ch["reembolsos"] == [("aluno-1", 10)]
        assert db.mentis_intervencoes_abertas.docs == {}, "desbloqueou sem entregar nada"

    def test_resposta_malformada_da_ia_e_recusada(self, ambiente, monkeypatch):
        db, ch = ambiente

        async def _curto(*a, **k):
            return {**CONTEUDO_OK, "treino": ["só um passo"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _curto)
        with pytest.raises(mr.HTTPException):
            asyncio.run(mr.abrir_intervencao(_payload(), user=Usuario("aluno-1"), _=None))
        assert db.mentis_intervencoes.docs == {}, "conteúdo inválido foi para o cache"

    def test_sentinela_tem_intervencao_sem_catalogo(self, ambiente):
        db, ch = ambiente
        r = asyncio.run(mr.abrir_intervencao(
            _payload("erro-nao-catalogado-nesta-versao", "PROC-ESPACO-01"), user=Usuario("a"), _=None
        ))
        assert r["conteudo"]["treino"]
        assert r["causa"]["sentinela"] is True
        assert r["previa"]["intervencao_id"] is None


class TestNaoEncostaNoSaibaMais:
    def test_custos_e_caches_sao_distintos(self):
        assert mr.EXPLICACAO_COST == 7 and mr.INTERVENCAO_COST == 10
        assert mr._CACHE_PREFIXO != mr._CACHE_PREFIXO_INTERVENCAO

    def test_chave_da_intervencao_nao_depende_do_aluno(self):
        par = motor.par_diagnostico("ERR-07", "PROC-CAUSAL-01")
        assert mr._chave_intervencao(par) == mr._chave_intervencao(dict(par))

    def test_chave_muda_com_a_versao_da_ontologia(self):
        par = motor.par_diagnostico("ERR-07", "PROC-CAUSAL-01")
        outra = {**par, "ontology_version": "2.0.0"}
        assert mr._chave_intervencao(par) != mr._chave_intervencao(outra)
