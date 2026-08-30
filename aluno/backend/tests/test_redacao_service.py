"""`service.corrigir_redacao` — orquestração ponta a ponta, Gemini mockado.
Foco no efeito de custo mais importante da arquitetura: um texto claramente
anulado pela Etapa 0 mecânica nunca soma nenhuma chamada de LLM, mesmo que
outros itens (competências, coesão etc.) ficassem pendentes se avaliados
isoladamente — o curto-circuito acontece ANTES do escalonamento."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import ai_service  # noqa: E402
from redacao import service  # noqa: E402
from redacao.tipos import RedacaoEntrada  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def test_texto_em_branco_nunca_chama_llm(fake_db, monkeypatch):
    chamadas = {"n": 0}

    async def fake_generate_json(*a, **kw):
        chamadas["n"] += 1
        return {"itens": []}

    monkeypatch.setattr(ai_service, "generate_json", fake_generate_json)
    resultado = _run(service.corrigir_redacao(RedacaoEntrada(texto=""), db=fake_db, redacao_id="r-blank"))
    assert resultado["estado_geral"] == "ANULADA"
    assert resultado["nota_total"] == 0
    assert resultado["itens_escalonados_llm"] == []
    assert chamadas["n"] == 0


def test_texto_limpo_e_completo_chama_llm_no_maximo_para_poucos_itens(fake_db, monkeypatch):
    import re

    chamadas = {"n": 0}

    async def fake_generate_json(system, prompt, model=None, thinking_level=None):
        chamadas["n"] += 1
        itens = []
        for item_id in re.findall(r"### Item (\S+)", prompt):
            if item_id.startswith("COMP-"):
                itens.append({"criterio_id": item_id, "nivel_pontos": 160, "trecho_citado": "t",
                              "evidencias_encontradas": [], "evidencias_ausentes": []})
            else:
                itens.append({"criterio_id": item_id, "disparado": False, "trecho_citado": "t",
                              "evidencias_encontradas": [], "evidencias_ausentes": []})
        return {"itens": itens}

    monkeypatch.setattr(ai_service, "generate_json", fake_generate_json)
    texto = """A valorização da herança africana no Brasil enfrenta desafios estruturais que precisam ser enfrentados com urgência.

Em primeiro lugar, é preciso reconhecer que o racismo estrutural, herdado do período escravocrata, ainda molda as oportunidades de acesso à educação e ao mercado de trabalho no Brasil. Dessa forma, a valorização da herança africana esbarra em desigualdades concretas.

Ademais, a escola brasileira historicamente relegou a história e a cultura africana a um papel secundário nos currículos, o que perpetua o desconhecimento sobre a contribuição africana para a formação do Brasil. Portanto, a ausência desse conteúdo nas salas de aula compromete a valorização plena dessa herança.

Diante disso, é fundamental que o Estado, por meio do Ministério da Educação, implemente políticas de valorização da herança africana no Brasil, a fim de garantir que as futuras gerações reconheçam essa contribuição histórica, com a criação de materiais didáticos específicos e formação continuada de professores."""
    entrada = RedacaoEntrada(
        texto=texto, titulo="Desafios para a valorização da herança africana no Brasil",
        tema_frase="Desafios para a valorização da herança africana no Brasil",
        tema_elementos_obrigatorios=["Desafios", "Valorização", "Herança africana", "Brasil"],
    )
    resultado = _run(service.corrigir_redacao(entrada, db=fake_db, redacao_id="r-limpa"))
    assert resultado["estado_geral"] == "AVALIAVEL"
    assert len(resultado["itens_escalonados_llm"]) <= 5
    assert chamadas["n"] <= 1  # 1 chamada LOW cobre todos os itens pendentes de uma vez (sem malformação no mock)
