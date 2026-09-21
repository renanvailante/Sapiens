"""As rotas do app, dos dois lados.

O backend emite endereços de tela como dado (o bloco do cronograma, a missão
do dia, o destino que a Mentis escolhe, a ação sugerida no painel do perfil), e
o frontend constrói o roteador a partir da própria tabela. São dois arquivos
com a mesma informação, e por isso podem divergir.

Já divergiram: `mentis_routes.DESTINOS` apontou para `/cognitive-profile` e
`/cursos#live` durante meses depois de as telas terem sido renomeadas, e
ninguém percebeu porque um redirect calado no frontend mantinha tudo
funcionando. Este arquivo existe para que a próxima divergência apareça como
teste vermelho em vez de como redirect invisível.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import rotas_do_app as rotas

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "rotas.js"


def _rotas_do_frontend() -> dict[str, str]:
    """Lê `ROTAS` do `lib/rotas.js`.

    Por regex e não por um parser de JS: o arquivo é uma tabela de literais, o
    formato é estável, e trazer um interpretador de JavaScript para a suíte de
    testes do backend custaria mais do que o problema vale.
    """
    fonte = _FRONTEND.read_text(encoding="utf-8")
    bloco = re.search(r"export const ROTAS = \{(.*?)\n\};", fonte, re.S)
    assert bloco, "não achei `export const ROTAS` em lib/rotas.js"
    return dict(re.findall(r'^\s*([A-Z_]+):\s*"([^"]+)"', bloco.group(1), re.M))


def _legado_do_frontend() -> set[str]:
    fonte = _FRONTEND.read_text(encoding="utf-8")
    bloco = re.search(r"export const LEGADO = \{(.*?)\n\};", fonte, re.S)
    assert bloco, "não achei `export const LEGADO` em lib/rotas.js"
    return set(re.findall(r'^\s*"([^"]+)":', bloco.group(1), re.M))


# --- Os dois arquivos dizem a mesma coisa ----------------------------------

@pytest.mark.parametrize(
    "chave_js, valor_py",
    [
        ("HOJE", rotas.HOJE),
        ("ESTUDAR", rotas.ESTUDAR),
        ("PROVAS", rotas.PROVAS),
        ("CURSOS", rotas.CURSOS),
        ("REDACAO", rotas.REDACAO),
        ("TREINO", rotas.TREINO),
        ("FOLHEAR", rotas.FOLHEAR),
        ("AGENDA", rotas.AGENDA),
        ("PROGRESSO", rotas.PROGRESSO),
        ("COMUNIDADE", rotas.COMUNIDADE),
        ("MENTIS", rotas.MENTIS),
        ("SPARKS", rotas.SPARKS),
        ("SUGESTOES", rotas.SUGESTOES),
        ("AULA_AO_VIVO", rotas.AULA_AO_VIVO),
        ("MENTORIA", rotas.MENTORIA),
    ],
)
def test_backend_e_frontend_concordam(chave_js: str, valor_py: str):
    assert _rotas_do_frontend()[chave_js] == valor_py


def test_todo_endereco_antigo_do_backend_existe_no_frontend():
    """O frontend é quem tem o `<Route>` que redireciona.

    Um endereço antigo que o backend sabe traduzir mas o roteador não conhece
    devolve "página não encontrada" para um link que ainda circula.
    """
    faltando = set(rotas.LEGADO) - _legado_do_frontend()
    assert not faltando, f"sem redirect no frontend: {sorted(faltando)}"


# --- A tradução ------------------------------------------------------------

def test_normalizar_traduz_o_endereco_antigo():
    assert rotas.normalizar("/redacao") == rotas.REDACAO
    assert rotas.normalizar("/exams") == rotas.PROVAS
    assert rotas.normalizar("/cronograma") == rotas.AGENDA
    assert rotas.normalizar("/desempenho") == rotas.PROGRESSO


def test_normalizar_e_idempotente():
    """Rodar duas vezes não pode mudar o resultado: a chave dos lembretes
    depende disso para ser estável ao longo do tempo."""
    for rota in (rotas.REDACAO, rotas.PROVAS, rotas.AGENDA, rotas.PROGRESSO):
        assert rotas.normalizar(rota) == rota
        assert rotas.normalizar(rotas.normalizar(rota)) == rota


def test_normalizar_preserva_a_query():
    """Perder a query aqui não quebra nada visivelmente — entrega um caderno
    genérico onde o aluno pediu a questão que errou."""
    assert rotas.normalizar("/exams?area=Matemática") == f"{rotas.PROVAS}?area=Matemática"
    assert rotas.normalizar("/treino?hab=HAB-12") == f"{rotas.TREINO}?hab=HAB-12"
    assert rotas.normalizar("/exams?item_ids=a,b") == f"{rotas.PROVAS}?item_ids=a,b"


def test_caminho_desconhecido_volta_como_veio():
    assert rotas.normalizar("/uma-rota-que-nao-existe") == "/uma-rota-que-nao-existe"
    assert rotas.normalizar("") == ""
    assert rotas.normalizar(None) == ""


# --- O que a renomeação poderia ter quebrado -------------------------------

def test_lembrete_nao_e_cobrado_duas_vezes_apos_a_renomeacao():
    """A REGRA QUE PROTEGE DINHEIRO.

    A chave de idempotência do lembrete é `sha256(texto + rota)`. Sem
    normalizar a rota, o aluno que guardou um trecho em `/redacao` antes de
    2026-09-18 pagaria os 10 Sparks de novo pelo MESMO trecho em
    `/estudar/redacao`, e a lista mostraria a frase duplicada.
    """
    from lembretes_routes import chave_do_lembrete

    texto = "A competência III avalia a seleção e organização de argumentos."
    antiga = chave_do_lembrete("u1", texto, "/redacao")
    nova = chave_do_lembrete("u1", texto, rotas.REDACAO)
    assert antiga == nova

    # E o que era para ser diferente continua diferente: a MESMA frase marcada
    # em dois lugares são duas lembranças, e apagar uma não apaga a outra.
    outra_tela = chave_do_lembrete("u1", texto, rotas.CURSOS)
    assert outra_tela != nova


def test_destinos_da_mentis_apontam_para_rotas_vivas():
    """O modelo escolhe uma CHAVE, nunca uma URL — mas a chave precisa levar a
    algum lugar que exista."""
    from mentis_routes import DESTINOS

    canonicas = {
        v for k, v in vars(rotas).items()
        if k.isupper() and isinstance(v, str) and v.startswith("/")
    }
    for chave, destino in DESTINOS.items():
        base = destino["rota"].split("?")[0]
        assert base in canonicas, f"destino '{chave}' aponta para {destino['rota']}"
        # E nunca para um endereço antigo: foi assim que `/cognitive-profile`
        # sobreviveu meses dentro desta tabela.
        assert destino["rota"].split("#")[0].split("?")[0] not in rotas.LEGADO


def test_missoes_e_prioridades_apontam_para_rotas_vivas():
    from engajamento import CATALOGO_MISSOES
    from prioridade_enem import DISCIPLINAS

    for missao in CATALOGO_MISSOES:
        base = missao.rota.split("#")[0].split("?")[0]
        assert base not in rotas.LEGADO, f"missão '{missao.id}' usa rota antiga"

    for disciplina in DISCIPLINAS:
        base = disciplina["rota"].split("?")[0]
        assert base not in rotas.LEGADO, f"frente '{disciplina['chave']}' usa rota antiga"
