"""Decomposição local do tema (`redacao/tema_local.py`) e o efeito dela na
nota: os três itens que dependiam de `tema_elementos_obrigatorios` deixam de
ser indeterminados sem nenhuma chamada de rede."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from redacao import service, tema_local  # noqa: E402
from redacao.tipos import RedacaoEntrada  # noqa: E402

TEMA = "Desafios para a valorização de comunidades e povos tradicionais no Brasil"

NO_TEMA = (
    "A valorização das comunidades tradicionais é um desafio persistente. Embora a "
    "Constituição assegure direitos territoriais aos povos indígenas e quilombolas, a "
    "efetivação dessas garantias esbarra em entraves históricos.\n\n"
    "Em primeiro lugar, a invisibilidade cultural dos povos tradicionais perpetua "
    "estereótipos. Dessa forma, a ausência de representação nas comunidades midiáticas "
    "contribui para que demandas legítimas sejam tratadas como assunto secundário.\n\n"
    "Além disso, a morosidade na demarcação de terras agrava o quadro. Consequentemente, "
    "famílias tradicionais vivem sob ameaça de despejo, o que compromete a transmissão de "
    "saberes ancestrais.\n\n"
    "Portanto, cabe ao poder público ampliar a demarcação de territórios das comunidades, "
    "por meio de editais permanentes, a fim de garantir a valorização desses povos."
)

FORA_DO_TEMA = (
    "A tecnologia mudou a forma como as pessoas se relacionam. Os aplicativos de mensagem "
    "substituíram a carta e o telefone fixo, e hoje qualquer pessoa fala com outra do outro "
    "lado do planeta em segundos.\n\n"
    "Por outro lado, essa facilidade trouxe problemas. O excesso de notificações prejudica a "
    "concentração e muita gente relata ansiedade por não conseguir se desconectar.\n\n"
    "Portanto, é necessário que as escolas promovam campanhas de educação digital, por meio "
    "de oficinas periódicas, a fim de ensinar os jovens a usar a tecnologia com equilíbrio."
)


def _corrigir(texto: str, tema: str | None):
    return asyncio.run(
        service.corrigir_redacao(RedacaoEntrada(texto=texto, tema_frase=tema), db=None, redacao_id="r")
    )


def _comp(resultado, comp_id: str) -> dict:
    return next(c for c in resultado["competencias"] if c["id"] == comp_id)


# ---------------------------------------------------------------- extração


def test_extrai_as_palavras_de_conteudo_do_tema():
    elementos = tema_local.elementos_do_tema(TEMA)
    assert elementos
    assert all(len(e) >= 5 for e in elementos)
    # "Brasil", "desafios", "para", "de", "no" são vazias para efeito de tema:
    # casariam com qualquer redação em português, inclusive uma fuga total.
    assert not any(e.startswith("brasil") or e.startswith("desafi") for e in elementos)


def test_frase_sem_palavra_de_conteudo_nao_inventa_elemento():
    assert tema_local.elementos_do_tema("a de os no") == []
    assert tema_local.elementos_do_tema("") == []
    assert tema_local.elementos_do_tema(None) == []


def test_radical_tolera_flexao():
    """"comunidades" no tema precisa casar com "comunidade" no texto do aluno."""
    elementos = tema_local.elementos_do_tema("Valorização das comunidades tradicionais")
    assert any("comunidad" in e for e in elementos)
    assert all(e in "valorizacao das comunidade tradicional" for e in elementos)


# -------------------------------------------------------- efeito na correção


def test_com_tema_a_competencia_ii_deixa_de_ficar_sem_nota():
    """Antes disto `COMP-II` saía `INSUFICIENTE` em toda correção — o campo de
    elementos nunca era preenchido por ninguém — e somava zero na nota."""
    resultado = _corrigir(NO_TEMA, TEMA)
    assert resultado["tema_elementos_usados"]
    assert _comp(resultado, "COMP-II")["nivel_pontos"] > 0


def test_texto_fora_do_tema_perde_na_competencia_ii():
    dentro = _comp(_corrigir(NO_TEMA, TEMA), "COMP-II")["nivel_pontos"]
    fora = _comp(_corrigir(FORA_DO_TEMA, TEMA), "COMP-II")["nivel_pontos"]
    assert fora < dentro


def test_correcao_nunca_escalona_para_o_llm_por_padrao():
    """O escalonamento é opt-in (`REDACAO_ESCALONAR_LLM`). Sem ele, a nota que o
    aluno paga não dispara nenhuma chamada de API."""
    for texto, tema in [(NO_TEMA, TEMA), (FORA_DO_TEMA, TEMA), (NO_TEMA, None)]:
        assert _corrigir(texto, tema)["itens_escalonados_llm"] == []


def test_escalonamento_ligado_por_env(monkeypatch):
    monkeypatch.setenv("REDACAO_ESCALONAR_LLM", "1")
    assert service._escalonamento_ligado() is True
    monkeypatch.setenv("REDACAO_ESCALONAR_LLM", "0")
    assert service._escalonamento_ligado() is False
    monkeypatch.delenv("REDACAO_ESCALONAR_LLM")
    assert service._escalonamento_ligado() is False


def test_decomposicao_explicita_do_chamador_tem_prioridade():
    """Se alguém (uma tela futura, um import de prova real) mandar a
    decomposição oficial do tema, ela não é sobrescrita pela heurística."""
    entrada = RedacaoEntrada(texto=NO_TEMA, tema_frase=TEMA, tema_elementos_obrigatorios=["quilombola"])
    assert service._com_tema_decomposto(entrada).tema_elementos_obrigatorios == ["quilombola"]
