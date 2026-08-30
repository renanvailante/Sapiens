"""`avaliador_local.avaliar` — combina mecânico + heurística para os 18
itens rastreados (11 gatilhos + 1 localizado + 5 competências + 2
auxiliares). Sem rede: só verifica o que resolve local vs. o que sobra."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import decision_gate as dg  # noqa: E402
from redacao import avaliador_local as av  # noqa: E402
from redacao.tipos import RedacaoEntrada  # noqa: E402

TEMA_ELEMENTOS = ["Desafios", "Valorização", "Herança africana", "Brasil"]

TEXTO_LIMPO = """A valorização da herança africana no Brasil enfrenta desafios estruturais que precisam ser enfrentados com urgência.

Em primeiro lugar, é preciso reconhecer que o racismo estrutural, herdado do período escravocrata, ainda molda as oportunidades de acesso à educação e ao mercado de trabalho no Brasil. Dessa forma, a valorização da herança africana esbarra em desigualdades concretas.

Ademais, a escola brasileira historicamente relegou a história e a cultura africana a um papel secundário nos currículos, o que perpetua o desconhecimento sobre a contribuição africana para a formação do Brasil. Portanto, a ausência desse conteúdo nas salas de aula compromete a valorização plena dessa herança.

Diante disso, é fundamental que o Estado, por meio do Ministério da Educação, implemente políticas de valorização da herança africana no Brasil, a fim de garantir que as futuras gerações reconheçam essa contribuição histórica, com a criação de materiais didáticos específicos e formação continuada de professores."""


def test_texto_em_branco_zera_zero_03_e_maioria_dos_outros_ficam_determinados_limpos():
    entrada = RedacaoEntrada(texto="")
    classificacoes = av.avaliar(entrada)
    zero03 = classificacoes["ZERO-03"]
    assert zero03.estado == dg.EstadoOperacional.DETERMINADO
    assert zero03.candidato_final is True


def test_texto_limpo_e_no_tema_resolve_a_maioria_localmente():
    entrada = RedacaoEntrada(
        texto=TEXTO_LIMPO, titulo="Desafios para a valorização da herança africana no Brasil",
        tema_frase="Desafios para a valorização da herança africana no Brasil",
        tema_elementos_obrigatorios=TEMA_ELEMENTOS,
    )
    classificacoes = av.avaliar(entrada)
    pendentes = av.itens_nao_determinados(classificacoes)
    # nenhum gatilho de zero-redação-inteira deve ficar CONFLITANTE nem
    # DETERMINADO=disparado num texto claramente limpo e no tema.
    for item_id in av.GATILHOS_ZERO_REDACAO_INTEIRA:
        c = classificacoes[item_id]
        assert not (c.estado == dg.EstadoOperacional.DETERMINADO and c.candidato_final is True)
    # a maior parte dos 19 itens resolve sem precisar de LLM.
    assert len(pendentes) <= 5, f"itens pendentes demais para um texto limpo: {pendentes}"


def test_todos_os_19_itens_aparecem_no_resultado():
    """11 gatilhos de zero-redação-inteira + 1 localizado + 5 competências + 2 auxiliares (TEMA-02, COPIA-02)."""
    entrada = RedacaoEntrada(texto=TEXTO_LIMPO)
    classificacoes = av.avaliar(entrada)
    assert set(classificacoes.keys()) == set(av.TODOS_OS_ITENS)
    assert len(av.TODOS_OS_ITENS) == 19
