"""O contrato de conteúdo dos cursos: o que a carga aceita e o que ela recusa.

Estes testes existem porque o conteúdo NÃO é escrito aqui. Ele é produzido
fora (uma IA escreve, outra revisa, outra gera volume de exercícios) e entra
por commit — em lote, e em volume que ninguém revisa linha a linha. O
validador é o revisor que não cansa, e este arquivo é o que garante que ele
continua recusando o que precisa recusar.

O que doeria, na ordem:

1. **Um arquivo de conteúdo declarando preço.** Preço é decisão de produto e
   mora em `cursos.py`; um `"custo_sparks": 50` vindo de um lote gerado seria
   promessa de preço publicada sem ninguém ter decidido nada.
2. **Gabarito vazando para a tela.** O aluno receberia a resposta junto com a
   pergunta, e o exercício deixaria de medir qualquer coisa.
3. **Progressão que retrocede.** "Do simples ao avançado" vira intenção do
   autor, e a estação em que ela se perde é indistinguível das outras até um
   aluno travar.
4. **Trilha com buraco.** Estação citada sem arquivo, arquivo sem trilha,
   pré-requisito que não existe ou que faz ciclo — todos deixam o aluno preso
   numa porta que nunca abre, em silêncio.

Tudo offline: os cursos de exemplo são escritos em `tmp_path` pelo próprio
teste. O último teste, e só ele, valida a pasta REAL de conteúdo do produto.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import cursos  # noqa: E402
import cursos_conteudo as cc  # noqa: E402

CATALOGO = ["curso-de-teste"]


# ---------------------------------------------------------------------------
# Fábrica de conteúdo de exemplo (fixture de teste, não conteúdo do produto)
# ---------------------------------------------------------------------------


def _exercicio(bloco_id: str, nivel: int = 1, **extra) -> dict:
    base = {
        "tipo": "exercicio",
        "bloco_id": bloco_id,
        "nivel": nivel,
        "formato": "multipla_escolha",
        "enunciado": "Enunciado de teste.",
        "alternativas": [
            {"id": "a", "texto": "Certa"},
            {"id": "b", "texto": "Errada"},
        ],
        "gabarito": "a",
        "dica": "Dica de teste.",
        "feedback": {"a": "Isso.", "b": "Aqui está o engano."},
        "solucao": "Resolução de teste.",
    }
    base.update(extra)
    return base


def _estacao(estacao_id: str, **extra) -> dict:
    base = {
        "schema_version": "1.0",
        "estacao_id": estacao_id,
        "titulo": "Estação de teste",
        "objetivo": "Ao fim desta estação você consegue testar.",
        "versao": "2026-09-16",
        "blocos": [
            {"tipo": "texto", "bloco_id": "t1", "markdown": "Texto de teste."},
            _exercicio("x1", 1),
            _exercicio("x2", 2),
        ],
    }
    base.update(extra)
    return base


def _escrever(raiz: Path, curso_id: str, manifesto: dict, estacoes: dict[str, dict]) -> Path:
    pasta = raiz / curso_id
    (pasta / "estacoes").mkdir(parents=True, exist_ok=True)
    (pasta / "curso.json").write_text(json.dumps(manifesto), encoding="utf-8")
    for nome, dados in estacoes.items():
        (pasta / "estacoes" / f"{nome}.json").write_text(json.dumps(dados), encoding="utf-8")
    return pasta


def _manifesto(estacoes: list[str], curso_id: str = "curso-de-teste") -> dict:
    return {
        "schema_version": "1.0",
        "curso_id": curso_id,
        "versao": "2026-09-16",
        "trilhas": [{"trilha_id": "t", "titulo": "Trilha", "estacoes": estacoes}],
    }


def _carregar(tmp_path: Path, manifesto: dict, estacoes: dict[str, dict], curso_id="curso-de-teste"):
    _escrever(tmp_path, curso_id, manifesto, estacoes)
    return cc.carregar(tmp_path, catalogo=CATALOGO)


# ---------------------------------------------------------------------------
# O caminho feliz
# ---------------------------------------------------------------------------


def test_curso_valido_e_servido_com_trilhas_e_estacoes(tmp_path):
    bib = _carregar(tmp_path, _manifesto(["e1", "e2"]), {"e1": _estacao("e1"), "e2": _estacao("e2")})

    assert bib.problemas == ()
    curso = bib.curso("curso-de-teste")
    assert curso is not None
    assert [t.trilha_id for t in curso.trilhas] == ["t"]
    assert curso.ordem_das_estacoes == ("e1", "e2")
    assert curso.estacoes["e1"].trilha_id == "t"
    assert curso.estacoes["e2"].ordem == 1


def test_pasta_ausente_nao_e_erro():
    """O estado normal antes de o conteúdo existir: a aba de Cursos continua
    sendo a pré-venda, e nada quebra."""
    bib = cc.carregar(Path("/tmp/sapiens-conteudo-que-nao-existe"), catalogo=CATALOGO)
    assert bib.cursos == {}
    assert bib.problemas == ()


def test_exercicio_opcional_e_desafio_nao_contam_para_concluir(tmp_path):
    estacao = _estacao("e1", blocos=[
        _exercicio("x1", 1),
        _exercicio("x2", 2, opcional=True),
        _exercicio("d1", 3, tipo="desafio"),
    ])
    bib = _carregar(tmp_path, _manifesto(["e1"]), {"e1": estacao})

    e = bib.estacao("curso-de-teste", "e1")
    assert [b["bloco_id"] for b in e.exercicios] == ["x1"]
    assert e.acertos_para_concluir == 1
    # Mas os três continuam respondíveis.
    assert len(e.avaliaveis) == 3


def test_minimo_de_acertos_e_respeitado(tmp_path):
    estacao = _estacao("e1", conclusao={"tipo": "minimo_de_acertos", "minimo": 1})
    bib = _carregar(tmp_path, _manifesto(["e1"]), {"e1": estacao})
    assert bib.estacao("curso-de-teste", "e1").acertos_para_concluir == 1


# ---------------------------------------------------------------------------
# Regra 1 — preço não mora em conteúdo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chave", ["custo_sparks", "preco", "sparks", "desconto"])
def test_arquivo_de_conteudo_nao_pode_declarar_preco(chave):
    problemas = cc.validar_estacao(_estacao("e1", **{chave: 10}))
    assert any("preço" in p.lower() for p in problemas), problemas


def test_preco_e_recusado_tambem_no_fundo_da_estrutura():
    """A varredura é recursiva de propósito: o risco real não é alguém pôr
    `custo` no topo do arquivo, é um bloco gerado em lote trazer o campo
    escondido dentro de uma alternativa."""
    estacao = _estacao("e1")
    estacao["blocos"][1]["alternativas"][0]["custo"] = 5
    problemas = cc.validar_estacao(estacao)
    assert any("blocos[1].alternativas[0].custo" in p for p in problemas), problemas


def test_enunciado_pode_falar_de_preco():
    """É Matemática Básica: metade dos enunciados fala de preço e desconto. O
    que a regra proíbe é o ARQUIVO declarar um, não o texto citar."""
    estacao = _estacao("e1")
    estacao["blocos"][1]["enunciado"] = "Uma blusa custa R$ 80 e teve 25% de desconto. Qual o preço final?"
    assert cc.validar_estacao(estacao) == []


# ---------------------------------------------------------------------------
# Regra 2 — a progressão não retrocede
# ---------------------------------------------------------------------------


def test_nivel_que_retrocede_e_recusado():
    estacao = _estacao("e1", blocos=[_exercicio("x1", 3), _exercicio("x2", 1)])
    problemas = cc.validar_estacao(estacao)
    assert any("retrocede" in p for p in problemas), problemas


def test_nivel_repetido_e_permitido():
    """Três exercícios de nível 2 seguidos são prática, não regressão."""
    estacao = _estacao("e1", blocos=[_exercicio("x1", 2), _exercicio("x2", 2), _exercicio("x3", 3)])
    assert cc.validar_estacao(estacao) == []


def test_desafio_nao_pode_ser_mais_facil_que_o_ultimo_exercicio():
    estacao = _estacao("e1", blocos=[
        _exercicio("x1", 1), _exercicio("x2", 4), _exercicio("d1", 2, tipo="desafio"),
    ])
    problemas = cc.validar_estacao(estacao)
    assert any("desafio" in p and "teto" in p for p in problemas), problemas


# ---------------------------------------------------------------------------
# Regra 3 — gabarito existe e resolve
# ---------------------------------------------------------------------------


def test_gabarito_precisa_apontar_uma_alternativa_existente():
    estacao = _estacao("e1", blocos=[_exercicio("x1", 1, gabarito="z")])
    assert any("gabarito" in p for p in cc.validar_estacao(estacao))


def test_feedback_nao_pode_citar_alternativa_inexistente():
    estacao = _estacao("e1", blocos=[_exercicio("x1", 1, feedback={"a": "ok", "z": "?"})])
    assert any("não é alternativa" in p for p in cc.validar_estacao(estacao))


def test_numerico_exige_valor_e_tolerancia_nao_negativa():
    ruim = _estacao("e1", blocos=[_exercicio(
        "x1", 1, formato="numerico", gabarito={"valor": 1, "tolerancia": -1},
        alternativas=None, feedback={"correto": "ok"},
    )])
    assert any("tolerancia" in p for p in cc.validar_estacao(ruim))


def test_texto_curto_exige_ao_menos_uma_resposta_aceita():
    ruim = _estacao("e1", blocos=[_exercicio(
        "x1", 1, formato="texto_curto", gabarito={"aceitos": []}, feedback={"correto": "ok"},
    )])
    assert any("aceitos" in p for p in cc.validar_estacao(ruim))


def test_formato_desconhecido_e_recusado():
    estacao = _estacao("e1", blocos=[_exercicio("x1", 1, formato="dissertativo")])
    assert any("formato" in p for p in cc.validar_estacao(estacao))


# ---------------------------------------------------------------------------
# Regras 4 a 7 — a trilha não pode ter buraco
# ---------------------------------------------------------------------------


def test_estacao_citada_sem_arquivo_derruba_o_curso(tmp_path):
    bib = _carregar(tmp_path, _manifesto(["e1", "e2"]), {"e1": _estacao("e1")})
    assert bib.curso("curso-de-teste") is None
    assert any("não existe `estacoes/e2.json`" in p.mensagem for p in bib.problemas)


def test_estacao_orfa_derruba_o_curso(tmp_path):
    bib = _carregar(tmp_path, _manifesto(["e1"]), {"e1": _estacao("e1"), "e9": _estacao("e9")})
    assert bib.curso("curso-de-teste") is None
    assert any("órfã" in p.mensagem for p in bib.problemas)


def test_pre_requisito_inexistente_derruba_o_curso(tmp_path):
    bib = _carregar(
        tmp_path, _manifesto(["e1"]), {"e1": _estacao("e1", pre_requisitos=["fantasma"])},
    )
    assert bib.curso("curso-de-teste") is None
    assert any("fantasma" in p.mensagem for p in bib.problemas)


def test_ciclo_de_pre_requisitos_derruba_o_curso(tmp_path):
    bib = _carregar(tmp_path, _manifesto(["e1", "e2"]), {
        "e1": _estacao("e1", pre_requisitos=["e2"]),
        "e2": _estacao("e2", pre_requisitos=["e1"]),
    })
    assert bib.curso("curso-de-teste") is None
    assert any("ciclo" in p.mensagem for p in bib.problemas)


def test_bloco_id_repetido_e_recusado():
    estacao = _estacao("e1", blocos=[_exercicio("x1", 1), _exercicio("x1", 2)])
    assert any("repetido" in p for p in cc.validar_estacao(estacao))


def test_mesma_estacao_em_duas_trilhas_e_recusada():
    manifesto = {
        "schema_version": "1.0", "curso_id": "curso-de-teste", "versao": "1",
        "trilhas": [
            {"trilha_id": "a", "titulo": "A", "estacoes": ["e1"]},
            {"trilha_id": "b", "titulo": "B", "estacoes": ["e1"]},
        ],
    }
    assert any("mais de um lugar" in p for p in cc.validar_manifesto(manifesto))


def test_estacao_sem_exercicio_que_conte_e_recusada():
    """Com `todos_os_exercicios`, ela seria concluída sem o aluno responder
    nada — e liberaria a seguinte de graça."""
    estacao = _estacao("e1", blocos=[{"tipo": "texto", "bloco_id": "t1", "markdown": "só texto"}])
    assert any("sem nenhum exercício" in p for p in cc.validar_estacao(estacao))


def test_minimo_maior_que_o_numero_de_exercicios_e_recusado():
    estacao = _estacao("e1", conclusao={"tipo": "minimo_de_acertos", "minimo": 99})
    assert any("nunca poderia ser concluída" in p for p in cc.validar_estacao(estacao))


def test_curso_fora_do_catalogo_nao_e_servido(tmp_path):
    bib = _carregar(
        tmp_path, _manifesto(["e1"], curso_id="curso-inexistente"), {"e1": _estacao("e1")},
        curso_id="curso-inexistente",
    )
    assert bib.cursos == {}
    assert any("cursos.CURSOS" in p.mensagem for p in bib.problemas)


def test_nome_do_arquivo_e_o_id_precisam_concordar(tmp_path):
    bib = _carregar(tmp_path, _manifesto(["e1"]), {"e1": _estacao("outro-id")})
    assert bib.curso("curso-de-teste") is None
    assert any("diferente do nome do arquivo" in p.mensagem for p in bib.problemas)


def test_schema_version_maior_diferente_e_recusada():
    assert any("incompatível" in p for p in cc.validar_estacao(_estacao("e1", schema_version="2.0")))


def test_json_quebrado_nao_derruba_a_carga(tmp_path):
    pasta = _escrever(tmp_path, "curso-de-teste", _manifesto(["e1"]), {"e1": _estacao("e1")})
    (pasta / "estacoes" / "e1.json").write_text("{ isto não é json", encoding="utf-8")
    bib = cc.carregar(tmp_path, catalogo=CATALOGO)
    assert bib.cursos == {}
    assert any("JSON inválido" in p.mensagem for p in bib.problemas)


def test_um_curso_quebrado_nao_leva_os_outros_junto(tmp_path):
    _escrever(tmp_path, "curso-de-teste", _manifesto(["e1"]), {"e1": _estacao("e1")})
    _escrever(tmp_path, "outro-curso", _manifesto(["e1"], curso_id="outro-curso"), {"e1": _estacao("e1", titulo="")})
    bib = cc.carregar(tmp_path, catalogo=["curso-de-teste", "outro-curso"])
    assert "curso-de-teste" in bib.cursos
    assert "outro-curso" not in bib.cursos


# ---------------------------------------------------------------------------
# Vídeo: opcional sempre, pendência declarada
# ---------------------------------------------------------------------------


def test_video_sem_ref_e_pendencia_valida_e_aparece_no_inventario(tmp_path):
    estacao = _estacao("e1", blocos=[
        {"tipo": "video", "bloco_id": "v1", "titulo": "A gravar", "provedor": "youtube", "ref": None},
        _exercicio("x1", 1),
    ])
    bib = _carregar(tmp_path, _manifesto(["e1"]), {"e1": estacao})

    assert bib.curso("curso-de-teste") is not None
    inv = cc.inventario(bib, catalogo=CATALOGO)
    curso = inv["cursos"][0]
    assert curso["videos"] == 1 and curso["videos_pendentes"] == 1


def test_video_com_ref_vazia_e_erro():
    """`null` é pendência declarada; string vazia é um id que se perdeu."""
    estacao = _estacao("e1", blocos=[
        {"tipo": "video", "bloco_id": "v1", "titulo": "X", "provedor": "youtube", "ref": "  "},
        _exercicio("x1", 1),
    ])
    assert any("ref" in p for p in cc.validar_estacao(estacao))


# ---------------------------------------------------------------------------
# O gabarito não vai para o navegador
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("campo", ["gabarito", "feedback", "dica", "solucao"])
def test_sanitizar_bloco_nao_vaza_resposta(campo):
    limpo = cc.sanitizar_bloco(_exercicio("x1", 1))
    assert campo not in limpo
    assert json.dumps(limpo, ensure_ascii=False).count("Resolução de teste") == 0


def test_sanitizar_mantem_o_que_a_tela_precisa():
    limpo = cc.sanitizar_bloco(_exercicio("x1", 1))
    assert limpo["enunciado"] and limpo["nivel"] == 1
    assert [a["id"] for a in limpo["alternativas"]] == ["a", "b"]
    # A tela precisa saber que existe dica — não qual é.
    assert limpo["tem_dica"] is True


def test_sanitizar_nao_mexe_em_texto():
    bloco = {"tipo": "texto", "bloco_id": "t1", "markdown": "oi"}
    assert cc.sanitizar_bloco(bloco) == bloco


# ---------------------------------------------------------------------------
# Correção
# ---------------------------------------------------------------------------


def test_corrige_multipla_escolha_e_devolve_a_alternativa_escolhida():
    bloco = _exercicio("x1", 1)
    assert cc.corrigir(bloco, "a") == (True, "a")
    assert cc.corrigir(bloco, "b") == (False, "b")
    assert cc.corrigir(bloco, None)[0] is False


def test_corrige_numerico_com_tolerancia_e_virgula():
    bloco = _exercicio(
        "x1", 1, formato="numerico", gabarito={"valor": 12.5, "tolerancia": 0.1},
        alternativas=None, feedback={"correto": "ok", "incorreto": "não"},
    )
    assert cc.corrigir(bloco, "12,45")[0] is True      # vírgula decimal, como se digita em pt-BR
    assert cc.corrigir(bloco, 12.5)[0] is True
    assert cc.corrigir(bloco, "13")[0] is False
    assert cc.corrigir(bloco, "não é número") == (False, "incorreto")


def test_corrige_texto_curto_ignorando_acento_e_caixa():
    bloco = _exercicio(
        "x1", 1, formato="texto_curto", gabarito={"aceitos": ["proporção"]},
        alternativas=None, feedback={"correto": "ok"},
    )
    assert cc.corrigir(bloco, "  PROPORCAO ")[0] is True
    assert cc.corrigir(bloco, "proporções")[0] is False


def test_formato_sem_correcao_nunca_da_acerto():
    """Se um formato escapar do validador, o pior resultado possível seria
    concluir a estação sem o aluno acertar nada."""
    assert cc.corrigir({"formato": "inventado"}, "qualquer coisa") == (False, "incorreto")


# ---------------------------------------------------------------------------
# A escada didática
# ---------------------------------------------------------------------------


def test_primeiro_erro_da_dica_e_nada_mais():
    r = cc.feedback_da_tentativa(_exercicio("x1", 1), "b", acertou=False, tentativa=1)
    assert r["dica"] == "Dica de teste."
    assert "solucao" not in r and "comentario" not in r


def test_segundo_erro_explica_a_alternativa_escolhida_sem_entregar_a_solucao():
    r = cc.feedback_da_tentativa(_exercicio("x1", 1), "b", acertou=False, tentativa=2)
    assert r["comentario"] == "Aqui está o engano."
    assert "solucao" not in r


def test_terceiro_erro_abre_a_solucao():
    r = cc.feedback_da_tentativa(_exercicio("x1", 1), "b", acertou=False, tentativa=3)
    assert r["solucao"] == "Resolução de teste."


def test_acerto_traz_comentario_e_solucao_de_uma_vez():
    r = cc.feedback_da_tentativa(_exercicio("x1", 1), "a", acertou=True, tentativa=1)
    assert r["acertou"] is True
    assert r["comentario"] == "Isso." and r["solucao"] == "Resolução de teste."


def test_exercicio_sem_dica_cai_no_comentario_no_primeiro_erro():
    bloco = _exercicio("x1", 1)
    bloco.pop("dica")
    r = cc.feedback_da_tentativa(bloco, "b", acertou=False, tentativa=1)
    assert r["comentario"] == "Aqui está o engano."


# ---------------------------------------------------------------------------
# Inventário
# ---------------------------------------------------------------------------


def test_inventario_mostra_curso_sem_conteudo_e_distribuicao_de_niveis(tmp_path):
    bib = _carregar(tmp_path, _manifesto(["e1"]), {"e1": _estacao("e1")})
    inv = cc.inventario(bib, catalogo=["curso-de-teste", "curso-vazio"])

    publicado = next(c for c in inv["cursos"] if c["curso_id"] == "curso-de-teste")
    assert publicado["publicado"] is True
    assert publicado["estacoes"] == 1 and publicado["exercicios"] == 2
    assert publicado["exercicios_por_nivel"]["1"] == 1
    assert publicado["exercicios_por_nivel"]["2"] == 1

    vazio = next(c for c in inv["cursos"] if c["curso_id"] == "curso-vazio")
    assert vazio["publicado"] is False and vazio["estacoes"] == 0


def test_inventario_lista_os_problemas_do_curso_fora_do_ar(tmp_path):
    bib = _carregar(tmp_path, _manifesto(["e1", "e2"]), {"e1": _estacao("e1")})
    inv = cc.inventario(bib, catalogo=CATALOGO)
    curso = inv["cursos"][0]
    assert curso["publicado"] is False
    assert curso["problemas"], "o painel precisa dizer O QUE quebrou, não só que quebrou"


# ---------------------------------------------------------------------------
# A pasta de verdade
# ---------------------------------------------------------------------------


def test_o_conteudo_publicado_no_repo_e_valido():
    """Este é o teste que impede conteúdo quebrado de chegar a produção.

    Ele valida a pasta REAL (`conteudo/cursos/`) contra o catálogo REAL. Com a
    pasta vazia ele passa trivialmente — e é exatamente assim que o produto
    está enquanto o conteúdo não é escrito. A partir da primeira estação
    publicada, é ele que derruba o build quando um lote gerado vem torto.
    """
    bib = cc.carregar()
    assert bib.problemas == (), "\n".join(str(p) for p in bib.problemas)


def test_todo_curso_com_conteudo_existe_no_catalogo_do_produto():
    bib = cc.carregar()
    catalogo = {c.curso_id for c in cursos.CURSOS}
    assert set(bib.cursos) <= catalogo
