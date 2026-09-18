""""Explicar melhor" um trecho de curso ou de e-book — `mentis_routes.explicar_trecho`.

Mesma família do "Saiba mais" de uma questão (`TestExplicacao` em
`test_mentis.py`), com uma diferença que é o ponto inteiro deste botão: o
texto NUNCA vem do cliente, é resolvido pelo chamador (`cursos_estudo_routes`
ou `cursos_routes`) a partir do conteúdo publicado. O que se testa aqui é a
função compartilhada — cobrança, cache e reembolso — offline, sem Gemini.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_service as fs  # noqa: E402
import mentis_routes as mr  # noqa: E402


class _SparksFalso:
    def __init__(self, saldo=1000):
        self.saldo = saldo
        self.debitos: list[int] = []
        self.reembolsos: list[int] = []

    def instalar(self, monkeypatch):
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: False)
        monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: self.saldo)
        monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: self.saldo)
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


class TestTextoDoBloco:
    def test_texto(self):
        assert mr.texto_do_bloco({"tipo": "texto", "markdown": "Olá mundo."}) == "Olá mundo."

    def test_exemplo_junta_enunciado_e_passos(self):
        bloco = {
            "tipo": "exemplo", "enunciado": "Resolva 2+2.",
            "passos": [{"texto": "Some as parcelas."}, {"texto": "O resultado é 4."}],
        }
        texto = mr.texto_do_bloco(bloco)
        assert "Resolva 2+2." in texto
        assert "Some as parcelas." in texto
        assert "O resultado é 4." in texto

    def test_tabela_junta_colunas_e_linhas(self):
        bloco = {"tipo": "tabela", "colunas": ["Figura", "Área"], "linhas": [["Círculo", "πr²"]]}
        texto = mr.texto_do_bloco(bloco)
        assert "Figura" in texto and "Área" in texto
        assert "Círculo" in texto and "πr²" in texto

    def test_tipo_desconhecido_devolve_vazio(self):
        assert mr.texto_do_bloco({"tipo": "exercicio", "enunciado": "x"}) == ""


class TestExplicarTrecho:
    def test_cobra_10_e_gera_pela_primeira_vez(self, monkeypatch, fake_db):
        mr.set_db(fake_db)
        carteira = _SparksFalso().instalar(monkeypatch)

        async def _resposta(system, prompt, **kwargs):
            assert "Onde está" in prompt and "Trecho de teste" in prompt
            return {"paragrafos": ["um parágrafo", "outro parágrafo", "terceiro parágrafo"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _resposta)
        out = asyncio.run(mr.explicar_trecho(
            "U1", origem="curso", ref_id="curso-x:estacao-1:bloco-1:v1",
            contexto="Curso X, estação 1", texto_fonte="Trecho de teste",
        ))
        assert out["paragrafos"] == ["um parágrafo", "outro parágrafo", "terceiro parágrafo"]
        assert out["cache"] is False
        assert carteira.debitos == [mr.EXPLICACAO_CONTEUDO_COST]

    def test_segundo_pedido_no_mesmo_trecho_le_do_cache_e_cobra_de_novo(self, monkeypatch, fake_db):
        mr.set_db(fake_db)
        carteira = _SparksFalso().instalar(monkeypatch)
        chamadas = []

        async def _resposta(*a, **k):
            chamadas.append(1)
            return {"paragrafos": ["um", "dois", "três"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _resposta)
        primeiro = asyncio.run(mr.explicar_trecho(
            "U1", origem="ebook", ref_id="ebook-x:pagina-1:bloco-1:v1",
            contexto="E-book X", texto_fonte="Texto",
        ))
        segundo = asyncio.run(mr.explicar_trecho(
            "U2", origem="ebook", ref_id="ebook-x:pagina-1:bloco-1:v1",
            contexto="E-book X", texto_fonte="Texto",
        ))
        assert len(chamadas) == 1
        assert primeiro["cache"] is False and segundo["cache"] is True
        # decisão de produto mantida: cache hit ainda cobra, o valor entregue é o mesmo
        assert carteira.debitos == [mr.EXPLICACAO_CONTEUDO_COST, mr.EXPLICACAO_CONTEUDO_COST]

    def test_trecho_diferente_nao_reaproveita_o_cache_do_outro(self, monkeypatch, fake_db):
        mr.set_db(fake_db)
        _SparksFalso().instalar(monkeypatch)
        chamadas = []

        async def _resposta(*a, **k):
            chamadas.append(1)
            return {"paragrafos": ["um", "dois", "três"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _resposta)
        asyncio.run(mr.explicar_trecho(
            "U1", origem="curso", ref_id="curso-x:estacao-1:bloco-1:v1",
            contexto="Curso X", texto_fonte="Texto A",
        ))
        asyncio.run(mr.explicar_trecho(
            "U1", origem="curso", ref_id="curso-x:estacao-1:bloco-2:v1",
            contexto="Curso X", texto_fonte="Texto B",
        ))
        assert len(chamadas) == 2

    def test_falha_do_modelo_devolve_as_sparks(self, monkeypatch, fake_db):
        mr.set_db(fake_db)
        carteira = _SparksFalso().instalar(monkeypatch)

        async def _explode(*a, **k):
            raise RuntimeError("Gemini indisponível")

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _explode)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mr.explicar_trecho(
                "U1", origem="curso", ref_id="curso-x:estacao-1:bloco-1:v1",
                contexto="Curso X", texto_fonte="Texto",
            ))
        assert exc.value.status_code == 503
        assert carteira.reembolsos == [mr.EXPLICACAO_CONTEUDO_COST]

    def test_resposta_curta_demais_nao_e_entregue_e_devolve_as_sparks(self, monkeypatch, fake_db):
        mr.set_db(fake_db)
        carteira = _SparksFalso().instalar(monkeypatch)

        async def _curta(*a, **k):
            return {"paragrafos": ["só um"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _curta)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mr.explicar_trecho(
                "U1", origem="curso", ref_id="curso-x:estacao-1:bloco-1:v1",
                contexto="Curso X", texto_fonte="Texto",
            ))
        assert exc.value.status_code == 503
        assert carteira.reembolsos == [mr.EXPLICACAO_CONTEUDO_COST]

    def test_mentis_ilimitada_nao_debita_nada(self, monkeypatch, fake_db):
        mr.set_db(fake_db)
        _SparksFalso().instalar(monkeypatch)
        monkeypatch.setattr(fs, "tem_mentis_ilimitada", lambda uid: True)
        monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: 4242)

        async def _resposta(*a, **k):
            return {"paragrafos": ["um", "dois", "três"]}

        monkeypatch.setattr(mr.ai_service, "generate_json_resiliente", _resposta)
        out = asyncio.run(mr.explicar_trecho(
            "U1", origem="curso", ref_id="curso-x:estacao-1:bloco-1:v1",
            contexto="Curso X", texto_fonte="Texto",
        ))
        assert out["sparks_balance"] == 4242
