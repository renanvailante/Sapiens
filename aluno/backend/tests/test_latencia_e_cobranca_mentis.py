"""A espera do aluno e a cobrança das ferramentas da Mentis.

Dois invariantes que se perderam em produção ao mesmo tempo (17/09) e que
este arquivo existe para travar:

1. **Nenhuma ferramenta da Mentis sai de graça.** Toda rota que chama o
   Gemini em nome de um aluno debita Sparks antes da chamada e devolve se a
   chamada não entregar. Havia três exceções silenciosas — o resumo de
   rodada, o OCR do cartão-resposta e o diagnóstico do simulado.

2. **O `timeout` que um chamador escreve é a espera TOTAL do aluno.** Antes
   era o teto de CADA tentativa, e como `generate_json_resiliente` tenta um
   modelo reserva, o pior caso era o dobro do número escrito.
"""
from __future__ import annotations

import asyncio

import pytest

import ai_service


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestOrcamentoTotal:
    def test_primeira_tentativa_recebe_so_uma_fatia_do_orcamento(self, monkeypatch):
        vistos: list[float | None] = []

        async def _falso(system, user_text, **kw):
            vistos.append(kw.get("timeout"))
            return {"ok": True}

        monkeypatch.setattr(ai_service, "_generate_json", _falso)
        _run(ai_service.generate_json_resiliente("s", "u", timeout=10.0))
        assert vistos == [pytest.approx(10.0 * ai_service._FATIA_PRIMARIA)]

    def test_retry_herda_so_o_que_sobrou_do_orcamento(self, monkeypatch):
        vistos: list[float | None] = []

        async def _falso(system, user_text, **kw):
            vistos.append(kw.get("timeout"))
            if len(vistos) == 1:
                raise ai_service.GeminiIndisponivelError("primário fora do ar")
            return {"ok": True}

        monkeypatch.setattr(ai_service, "_generate_json", _falso)
        _run(ai_service.generate_json_resiliente("s", "u", timeout=10.0))
        assert len(vistos) == 2
        # A soma das duas tentativas é o orçamento, não o dobro dele: é essa
        # a diferença entre esperar 10 s e esperar 20 s no pior caso.
        assert sum(vistos) <= 10.0 + 0.5

    def test_sem_orcamento_restante_desiste_em_vez_de_esticar_a_espera(self, monkeypatch):
        chamadas = 0

        async def _lento(system, user_text, **kw):
            nonlocal chamadas
            chamadas += 1
            # Gasta o orçamento inteiro antes de falhar, como um primário
            # pendurado até o próprio teto faria.
            await asyncio.sleep(kw.get("timeout") or 0)
            raise ai_service.GeminiIndisponivelError("pendurado")

        monkeypatch.setattr(ai_service, "_generate_json", _lento)
        with pytest.raises(ai_service.GeminiIndisponivelError):
            _run(ai_service.generate_json_resiliente("s", "u", timeout=2.5))
        # Só o primário: sobraram menos de 2 s, e disparar a reserva aí seria
        # condená-la a estourar depois de fazer o aluno esperar mais.
        assert chamadas == 1


class TestNenhumaChamadaInterativaSemTeto:
    """Varredura: todo chamador de `generate_json_resiliente` passa teto de
    saída. Sem `max_output_tokens` o modelo escreve até cansar, e o tempo de
    parede vai junto — foi assim que uma resposta virou quase um minuto."""

    ARQUIVOS = [
        "mentis_routes.py",
        "treino_routes.py",
        "cronograma_routes.py",
        "redacao_routes.py",
    ]

    def test_todo_chamador_passa_max_output_tokens(self):
        import pathlib
        import re

        raiz = pathlib.Path(__file__).resolve().parent.parent
        for nome in self.ARQUIVOS:
            texto = (raiz / nome).read_text(encoding="utf-8")
            for bloco in re.findall(
                r"generate_json_resiliente\((.*?)\n\s*\)", texto, re.DOTALL
            ):
                assert "max_output_tokens" in bloco, (
                    f"{nome}: chamada sem teto de tokens de saída -> {bloco[:80]}"
                )


class TestRotasPagasNaoSaemDeGraca:
    def test_resumo_de_rodada_tem_preco(self):
        import firestore_routes

        assert firestore_routes.RESUMO_SESSAO_COST > 0

    def test_ocr_do_cartao_tem_preco(self):
        import exam_routes

        assert exam_routes.OCR_CARTAO_COST > 0

    def test_diagnostico_do_simulado_tem_preco(self):
        import exam_routes

        assert exam_routes.DIAGNOSTICO_SIMULADO_COST > 0
