"""Publicar curso a partir de TEXTO: o que o compilador garante, e o que recusa.

A funcionalidade é simples de descrever e fácil de fazer errado: alguém cola a
aula escrita em texto e ela vira estação no ar. O que estes testes protegem é
justamente o que separa isso de um importador ingênuo:

1. **O gabarito não fica onde o autor o escreveu.** Quem escreve põe a resposta
   certa em A quase sempre; publicado assim, o curso ensina a clicar na
   primeira opção — e o id da alternativa, que viaja para o navegador, seria o
   próprio gabarito.
2. **O comentário do erro vai para o distrator que o aluno escolheu.** É a
   única devolutiva que ensina alguma coisa, e no texto ela vem num parágrafo
   só, misturada com a explicação da conta certa.
3. **Nada entra sem passar pelo mesmo validador do disco.** Inclusive a regra
   de que preço não mora em conteúdo.
4. **O que não dá para corrigir sozinho PARA a publicação**, com uma frase que
   diz o que consertar — em vez de publicar um gabarito adivinhado.
5. **Publicar acrescenta**: o curso que já existe em arquivo não é substituído,
   e despublicar devolve exatamente o que o arquivo dizia.

Os dois testes de regressão no fim são de erros reais que custaram conteúdo no
ar: um exemplo resolvido cujo título tinha parêntese (`**Exemplo 1 (direta).**`)
sumia inteiro, e um enunciado que começava com "Por que" era lido como a linha
de feedback — a questão ia ao ar sem enunciado.

Offline: nenhum banco real, nenhuma linha do conteúdo de produção.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import cursos_conteudo as cc  # noqa: E402
import cursos_ingestao as ci  # noqa: E402
import cursos_publicados as cpub  # noqa: E402

CURSO = "matematica-basica"   # existe no catálogo de produto (`cursos.CURSOS`)


def _run(coro):
    return asyncio.run(coro)


TEXTO = """---
station_id: 07
title: "Potenciação"
skills:
  - potenciacao
---
# Estação 07 — Potenciação

## Objetivo

Ao final desta estação, você saberá resolver potências e usar as propriedades
que aparecem na prova.

## Conteúdo

Potência é multiplicação repetida: `2³ = 2 × 2 × 2 = 8`.

### Expoente zero

Todo número diferente de zero elevado a zero é `1`.

## Exemplos resolvidos

**Exemplo 1.** `2³ × 2²`
- Mesma base, soma dos expoentes: `2⁵`
- `2⁵ = 32`

## Exercícios

### Questão 1
Calcule `3²`.
A) 9
B) 6
C) 5
D) 8
**Resposta:** A
**Feedback:** `3² = 3 × 3 = 9`. A alternativa B multiplica a base pelo expoente. C soma. D chuta.

dificuldade: básico

### Questão 2
Calcule `2³ × 2²`.
A) 32
B) 64
C) 16
D) 12
**Resposta:** A
**Feedback:** Mesma base: somam-se os expoentes, `2⁵ = 32`. B multiplica os expoentes.

dificuldade: intermediário
"""


def _compilar(texto=TEXTO, curso=CURSO):
    return ci.compilar(curso, texto, versao="2026-09-17")


# ---------------------------------------------------------------------------
# O que o compilador produz
# ---------------------------------------------------------------------------


def test_texto_de_autoria_vira_estacao_valida_pelo_contrato():
    compilada = _compilar()
    assert compilada.problemas == []
    (dados,) = compilada.estacoes.values()

    assert dados["estacao_id"] == "mb-07-potenciacao"
    assert dados["numero"] == 7
    assert dados["titulo"] == "Potenciação"
    assert dados["objetivo"].startswith("Ao final desta estação")
    # O validador do disco é o mesmo, e é ele que decide se entra.
    assert cc.validar_estacao(dados) == []

    tipos = [b["tipo"] for b in dados["blocos"]]
    assert tipos.count("exercicio") == 2
    assert "texto" in tipos and "exemplo" in tipos
    # A explicação vem antes do exemplo, e os exercícios no fim: é essa ordem
    # que a divisão em etapas da tela do aluno espera.
    assert tipos.index("texto") < tipos.index("exemplo") < tipos.index("exercicio")


def test_o_subtitulo_vira_bloco_proprio_e_o_exemplo_guarda_os_passos():
    (dados,) = _compilar().estacoes.values()
    textos = [b for b in dados["blocos"] if b["tipo"] == "texto"]
    assert [b.get("titulo") for b in textos] == [None, "Expoente zero"]

    exemplo = next(b for b in dados["blocos"] if b["tipo"] == "exemplo")
    assert exemplo["enunciado"] == "`2³ × 2²`"
    assert [p["texto"] for p in exemplo["passos"]] == [
        "Mesma base, soma dos expoentes: `2⁵`", "`2⁵ = 32`",
    ]


def test_o_gabarito_nao_fica_na_letra_em_que_foi_escrito():
    """As duas questões têm a resposta certa em A; publicadas assim, o curso
    ensinaria a clicar na primeira opção — e o id da alternativa, que vai para
    o navegador, seria o próprio gabarito."""
    (dados,) = _compilar().estacoes.values()
    exercicios = [b for b in dados["blocos"] if b["tipo"] == "exercicio"]

    for bloco in exercicios:
        certa = next(a for a in bloco["alternativas"] if a["id"] == bloco["gabarito"])
        # O conteúdo da resposta certa é preservado; só a posição muda.
        assert certa["texto"] in ("9", "32")
        assert [a["id"] for a in bloco["alternativas"]] == ["a", "b", "c", "d"]
    assert {b["gabarito"] for b in exercicios} != {"a"}


def test_recompilar_o_mesmo_texto_da_exatamente_o_mesmo_conteudo():
    """O embaralhamento é semeado no id do bloco. Sem isto, revisar uma
    vírgula do enunciado mudaria a posição de todas as alternativas e o diff
    de uma revisão seria ilegível."""
    a = json.dumps(list(_compilar().estacoes.values()), ensure_ascii=False, sort_keys=True)
    b = json.dumps(list(_compilar().estacoes.values()), ensure_ascii=False, sort_keys=True)
    assert a == b


def test_o_comentario_do_erro_vai_para_o_distrator_que_o_aluno_escolheu():
    (dados,) = _compilar().estacoes.values()
    q1 = next(b for b in dados["blocos"] if b["bloco_id"] == "mb-07-q01")

    # A explicação da conta certa vira `solucao`; o comentário de cada
    # distrator vira o feedback DAQUELA alternativa.
    assert q1["solucao"].startswith("`3² = 3 × 3 = 9`")
    posicao = {a["texto"]: a["id"] for a in q1["alternativas"]}
    assert q1["feedback"][posicao["6"]] == "Multiplica a base pelo expoente."
    # O gabarito não ganha feedback: quem acerta recebe a `solucao`, e o mesmo
    # texto duas vezes na tela é ruído.
    assert q1["gabarito"] not in q1["feedback"]


def test_a_dificuldade_declarada_vira_nivel_e_a_progressao_nao_retrocede():
    (dados,) = _compilar().estacoes.values()
    niveis = [b["nivel"] for b in dados["blocos"] if b["tipo"] == "exercicio"]
    assert niveis == [1, 2]
    assert niveis == sorted(niveis)


def test_sem_dificuldade_declarada_tudo_entra_no_mesmo_degrau_e_avisa():
    texto = TEXTO.replace("dificuldade: básico", "").replace("dificuldade: intermediário", "")
    compilada = ci.compilar(CURSO, texto, versao="v1")
    (dados,) = compilada.estacoes.values()
    assert [b["nivel"] for b in dados["blocos"] if b["tipo"] == "exercicio"] == [1, 1]
    assert any("dificuldade" in a for a in compilada.avisos)


def test_duas_estacoes_no_mesmo_texto_sao_separadas():
    segunda = TEXTO.replace("station_id: 07", "station_id: 08").replace("Potenciação", "Radiciação")
    compilada = ci.compilar(CURSO, TEXTO + "\n" + segunda, versao="v1")
    assert compilada.problemas == []
    assert compilada.ordem == ["mb-07-potenciacao", "mb-08-radiciacao"]


def test_estacao_sem_numero_declarado_continua_a_numeracao_do_curso():
    texto = TEXTO.split("---\n", 2)[2].replace("# Estação 07 — Potenciação", "# Potenciação")
    compilada = ci.compilar(CURSO, texto, versao="v1", numero_inicial=25)
    (dados,) = compilada.estacoes.values()
    assert dados["numero"] == 25
    assert dados["estacao_id"] == "mb-25-potenciacao"


# ---------------------------------------------------------------------------
# O que o compilador RECUSA
# ---------------------------------------------------------------------------


def test_questao_sem_resposta_sai_da_estacao_e_o_resto_vai_ao_ar():
    """UMA questão quebrada não pode levar a aula inteira junto.

    O `**Resposta:**` esquecido é o erro mais comum de quem cola texto; até
    17/09 ele descartava as outras questões, os blocos de leitura e os
    exemplos — tudo, sem publicar nada."""
    texto = TEXTO.replace("**Resposta:** A\n**Feedback:** `3² = 3 × 3 = 9`.", "")
    compilada = ci.compilar(CURSO, texto, versao="v1")
    (dados,) = compilada.estacoes.values()
    exercicios = [b for b in dados["blocos"] if b["tipo"] == "exercicio"]
    assert len(exercicios) == 1
    assert any("Resposta" in a for a in compilada.avisos)


def test_resposta_que_nao_e_alternativa_nenhuma_tira_so_aquela_questao():
    texto = TEXTO.replace("**Resposta:** A\nFeedback", "**Resposta:** E\nFeedback")
    texto = texto.replace("**Resposta:** A", "**Resposta:** E", 1)
    compilada = ci.compilar(CURSO, texto, versao="v1")
    (dados,) = compilada.estacoes.values()
    assert len([b for b in dados["blocos"] if b["tipo"] == "exercicio"]) == 1
    assert any("não é" in a for a in compilada.avisos)


def test_estacao_em_que_nenhuma_questao_compila_nao_vai_ao_ar():
    """O limite da tolerância: sem exercício nenhum a estação não tem como ser
    concluída, e publicá-la trancaria a estação seguinte para sempre."""
    texto = TEXTO.replace("**Resposta:**", "Resposta")
    compilada = ci.compilar(CURSO, texto, versao="v1")
    assert compilada.estacoes == {}
    assert any("nenhuma" in p.lower() for p in compilada.problemas)


def test_texto_sem_objetivo_publica_com_aviso_e_a_primeira_frase():
    """Sem `## Objetivo` a estação entra assim mesmo. A frase importa, mas
    mandar reescrever o texto inteiro por causa dela é como se desiste de
    publicar."""
    texto = TEXTO.replace("## Objetivo", "## Resumo")
    compilada = ci.compilar(CURSO, texto, versao="v1")
    (dados,) = compilada.estacoes.values()
    assert dados["objetivo"]
    assert any("Objetivo" in a for a in compilada.avisos)


def test_texto_sem_questao_nenhuma_nao_vira_estacao():
    texto = TEXTO.split("## Exercícios")[0]
    compilada = ci.compilar(CURSO, texto, versao="v1")
    assert compilada.estacoes == {}
    assert any("questão" in p.lower() for p in compilada.problemas)


def test_preco_declarado_no_texto_e_recusado_pelo_validador():
    """Regra 1 do contrato de conteúdo: preço é decisão de produto e mora em
    `cursos.py`. Um texto que declarasse custo viraria promessa de preço no ar."""
    (dados,) = _compilar().estacoes.values()
    dados["custo_sparks"] = 50
    problemas = cc.validar_estacao(dados)
    assert any("preço" in p or "preco" in p for p in problemas)


# ---------------------------------------------------------------------------
# Regressões: erros que já custaram conteúdo no ar
# ---------------------------------------------------------------------------


def test_exemplo_com_parenteses_no_titulo_nao_some():
    """`**Exemplo 1 (direta).**` não casava com a regra antiga, e a seção
    inteira de exemplos da estação de regra de três foi publicada vazia — sem
    erro nenhum, porque um exemplo que não casa simplesmente não vira bloco."""
    texto = TEXTO.replace(
        "**Exemplo 1.** `2³ × 2²`",
        "**Exemplo 1 (direta).** 3 kg de arroz custam R$ 15. Quanto custam 5 kg?",
    )
    (dados,) = ci.compilar(CURSO, texto, versao="v1").estacoes.values()
    exemplo = next(b for b in dados["blocos"] if b["tipo"] == "exemplo")
    assert exemplo["enunciado"] == "3 kg de arroz custam R$ 15. Quanto custam 5 kg?"


def test_enunciado_que_comeca_com_por_que_continua_sendo_enunciado():
    """Com os dois-pontos opcionais, "Por que um gráfico que começa em 90
    distorce a leitura?" era lido como a linha de feedback — e a questão ia ao
    ar sem enunciado nenhum."""
    texto = TEXTO.replace(
        "Calcule `3²`.",
        "Por que um gráfico de barras que começa em 90 distorce a leitura?",
    )
    (dados,) = ci.compilar(CURSO, texto, versao="v1").estacoes.values()
    q1 = next(b for b in dados["blocos"] if b["bloco_id"] == "mb-07-q01")
    assert q1["enunciado"] == "Por que um gráfico de barras que começa em 90 distorce a leitura?"


def test_o_compilador_reproduz_a_estacao_que_o_script_publicou():
    """A prova de que existe UM parser: o mesmo texto de autoria, compilado
    aqui, dá o mesmo conteúdo que o script de ingestão escreveu em arquivo."""
    fonte = BACKEND.parent.parent / "cursos" / "matemática básica" / "mat basica 1.md"
    publicado = BACKEND / "conteudo" / "cursos" / "matematica-basica" / "estacoes" / "mb-01-operacoes-fundamentais.json"
    if not fonte.exists() or not publicado.exists():
        pytest.skip("material de autoria não está nesta árvore")

    lida = ci.ler_estacao_de_texto(
        fonte.read_text(encoding="utf-8"),
        prefixo="mb-01",
        exigir_id=True,
        resumo_do_video="Aula conduzida pelo 1º colocado de Medicina da USP.",
    )
    assert lida.blocos == json.loads(publicado.read_text(encoding="utf-8"))["blocos"]


# ---------------------------------------------------------------------------
# Publicar, acrescentar e desfazer
# ---------------------------------------------------------------------------


@pytest.fixture
def curso_em_arquivo(tmp_path):
    """Um curso de mentira em disco, para a publicação ter o que acrescentar."""
    pasta = tmp_path / CURSO
    (pasta / "estacoes").mkdir(parents=True)
    estacao = {
        "schema_version": "1.0", "estacao_id": "mb-01-base", "titulo": "Base",
        "objetivo": "Ao fim desta estação você consegue testar.", "versao": "v1",
        "numero": 1,
        "blocos": [
            {"tipo": "texto", "bloco_id": "t1", "markdown": "Texto."},
            {
                "tipo": "exercicio", "bloco_id": "x1", "nivel": 1,
                "formato": "multipla_escolha", "enunciado": "Quanto é 1 + 1?",
                "alternativas": [{"id": "a", "texto": "2"}, {"id": "b", "texto": "3"}],
                "gabarito": "a",
            },
        ],
    }
    (pasta / "estacoes" / "mb-01-base.json").write_text(json.dumps(estacao), encoding="utf-8")
    (pasta / "curso.json").write_text(json.dumps({
        "schema_version": "1.0", "curso_id": CURSO, "versao": "v1",
        "trilhas": [{"trilha_id": "inicio", "titulo": "Início", "estacoes": ["mb-01-base"]}],
    }), encoding="utf-8")
    bib = cc.recarregar(tmp_path)
    assert bib.problemas == ()
    return tmp_path


@pytest.fixture
def db(fake_db):
    cpub.set_db(fake_db)
    return fake_db


def test_publicar_acrescenta_sem_perder_o_que_veio_do_arquivo(db, curso_em_arquivo):
    compilada = _compilar()
    problemas, resumo = _run(cpub.publicar(
        CURSO, list(compilada.estacoes.values()),
        trilha_id="novas", trilha_titulo="Novas estações", por="admin@exemplo.com",
    ))
    assert problemas == []
    assert [e["estacao_id"] for e in resumo["estacoes"]] == ["mb-07-potenciacao"]

    curso = cc.biblioteca().curso(CURSO)
    # A estação de arquivo continua lá, na trilha dela; a nova entrou na sua.
    assert set(curso.estacoes) == {"mb-01-base", "mb-07-potenciacao"}
    assert [t.trilha_id for t in curso.trilhas] == ["inicio", "novas"]
    assert curso.estacoes["mb-07-potenciacao"].acertos_para_concluir == 1


def test_publicar_de_novo_substitui_a_estacao_em_vez_de_duplicar(db, curso_em_arquivo):
    _run(cpub.publicar(
        CURSO, list(_compilar().estacoes.values()),
        trilha_id="novas", trilha_titulo="Novas estações", por="admin@exemplo.com",
    ))
    corrigido = TEXTO.replace("Calcule `3²`.", "Calcule `3²` sem calculadora.")
    _run(cpub.publicar(
        CURSO, list(ci.compilar(CURSO, corrigido, versao="v2").estacoes.values()),
        trilha_id="novas", trilha_titulo="Novas estações", por="admin@exemplo.com",
    ))

    curso = cc.biblioteca().curso(CURSO)
    assert len(curso.estacoes) == 2
    trilha = next(t for t in curso.trilhas if t.trilha_id == "novas")
    assert trilha.estacoes == ("mb-07-potenciacao",)
    q1 = curso.estacoes["mb-07-potenciacao"].bloco("mb-07-q01")
    assert q1["enunciado"] == "Calcule `3²` sem calculadora."


def test_conteudo_publicado_nunca_entra_quebrado(db, curso_em_arquivo):
    """Uma estação que não passa no contrato não é gravada — e o curso
    continua exatamente como estava."""
    quebrada = list(_compilar().estacoes.values())
    quebrada[0]["blocos"][-1]["gabarito"] = "z"   # alternativa que não existe
    problemas, _ = _run(cpub.publicar(
        CURSO, quebrada, trilha_id="novas", trilha_titulo="Novas", por="admin@exemplo.com",
    ))
    assert problemas and any("gabarito" in p for p in problemas)
    assert set(cc.biblioteca().curso(CURSO).estacoes) == {"mb-01-base"}
    assert _run(db.cursos_publicados.find_one({"_id": CURSO})) is None


def test_despublicar_devolve_o_curso_ao_que_o_arquivo_diz(db, curso_em_arquivo):
    _run(cpub.publicar(
        CURSO, list(_compilar().estacoes.values()),
        trilha_id="novas", trilha_titulo="Novas estações", por="admin@exemplo.com",
    ))
    assert len(cc.biblioteca().curso(CURSO).estacoes) == 2

    _run(cpub.despublicar(CURSO))
    curso = cc.biblioteca().curso(CURSO)
    assert set(curso.estacoes) == {"mb-01-base"}
    assert [t.trilha_id for t in curso.trilhas] == ["inicio"]


def test_a_conferencia_entre_processos_e_limitada_no_tempo(db, curso_em_arquivo, monkeypatch):
    """Nada no caminho do aluno pode custar uma leitura por requisição — foi a
    classe de erro que derrubou o app em 2026-09-04."""
    leituras = {"n": 0}
    original = db.cursos_publicados.find

    def contando(*args, **kwargs):
        leituras["n"] += 1
        return original(*args, **kwargs)

    _run(cpub.recarregar())
    monkeypatch.setattr(db.cursos_publicados, "find", contando)
    for _ in range(50):
        _run(cpub.garantir_atual())
    assert leituras["n"] == 0, "a conferência deveria estar dentro da janela de silêncio"


# ---------------------------------------------------------------------------
# As rotas do painel
# ---------------------------------------------------------------------------


@pytest.fixture
def rotas(db):
    import cursos_estudo_routes as routes
    routes.set_db(db)
    return routes


def _admin():
    from models import User
    return User(user_id="admin-1", email="admin@exemplo.com", name="Admin", is_admin=True)


def _pedido(texto=TEXTO, curso=CURSO, trilha="Álgebra"):
    import cursos_estudo_routes as routes
    return routes.TextoDeCurso(curso_id=curso, texto=texto, trilha_titulo=trilha)


def test_compilar_mostra_a_previa_e_nao_grava_nada(rotas, curso_em_arquivo, db):
    resposta = _run(rotas.compilar_conteudo(_pedido(), _admin()))

    assert resposta["pode_publicar"] is True
    assert resposta["trilha"] == {"trilha_id": "algebra", "titulo": "Álgebra", "resumo": None}
    (estacao,) = resposta["estacoes"]
    assert estacao["problemas"] == []
    # O gabarito APARECE para quem publica: é ele que precisa ser conferido.
    q1 = next(b for b in estacao["blocos"] if b["bloco_id"] == "mb-07-q01")
    assert q1["gabarito"] in ("a", "b", "c", "d")

    assert _run(db.cursos_publicados.find_one({"_id": CURSO})) is None
    assert set(cc.biblioteca().curso(CURSO).estacoes) == {"mb-01-base"}


def test_publicar_pela_rota_poe_no_ar_e_aparece_no_inventario(rotas, curso_em_arquivo):
    resposta = _run(rotas.publicar_conteudo(_pedido(), _admin()))

    assert [e["estacao_id"] for e in resposta["publicado"]["estacoes"]] == ["mb-07-potenciacao"]
    do_inventario = next(
        c for c in resposta["inventario"]["cursos"] if c["curso_id"] == CURSO
    )
    assert do_inventario["estacoes"] == 2
    assert do_inventario["exercicios"] == 3   # 1 do arquivo + 2 do texto

    listadas = _run(rotas.listar_publicados(_admin()))
    assert listadas["cursos"][0]["publicado_por"] == "admin@exemplo.com"


def test_publicar_texto_quebrado_devolve_422_com_a_lista_de_problemas(rotas, curso_em_arquivo):
    from fastapi import HTTPException

    texto = TEXTO.replace("**Resposta:**", "Resposta")
    with pytest.raises(HTTPException) as erro:
        _run(rotas.publicar_conteudo(_pedido(texto=texto), _admin()))
    assert erro.value.status_code == 422
    assert erro.value.detail["problemas"]
    assert set(cc.biblioteca().curso(CURSO).estacoes) == {"mb-01-base"}


def test_nao_se_cria_curso_fora_do_catalogo_por_texto(rotas):
    """Título, preço e status são decisão de produto e moram em `cursos.py`.
    Um texto colado não inventa uma coisa à venda."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as erro:
        _run(rotas.compilar_conteudo(_pedido(curso="curso-que-nao-existe"), _admin()))
    assert erro.value.status_code == 404


# ---------------------------------------------------------------------------
# A questão dissertativa, e o texto que chega torto
# ---------------------------------------------------------------------------

DISSERTATIVA = """# Fotossíntese

## Objetivo
Explicar como a planta transforma luz em alimento.

## Conteúdo
A fotossíntese transforma luz em glicose.

### Questão 1
Explique, em até cinco linhas, por que a planta precisa de luz.
Tipo: dissertativa
**Critérios:**
- Cita a luz como fonte de energia
- Relaciona a luz à produção de glicose
**Resposta esperada:** A luz fornece a energia que alimenta a produção de glicose.
"""


def test_questao_dissertativa_vira_exercicio_com_regua_e_sem_gabarito():
    compilada = ci.compilar(CURSO, DISSERTATIVA, versao="v1")
    assert compilada.problemas == []
    (dados,) = compilada.estacoes.values()
    assert cc.validar_estacao(dados) == []
    (questao,) = [b for b in dados["blocos"] if b["tipo"] == "exercicio"]
    assert questao["formato"] == "dissertativo"
    assert len(questao["criterios"]) == 2
    assert "gabarito" not in questao
    assert questao["referencia"].startswith("A luz fornece")


def test_a_resposta_esperada_nao_viaja_para_o_navegador():
    """`referencia` é a resposta do autor: sai do bloco pelo mesmo motivo que o
    gabarito sai. Os `criterios` ficam — é a régua, e quem sabe o que vai ser
    cobrado escreve melhor."""
    (dados,) = ci.compilar(CURSO, DISSERTATIVA, versao="v1").estacoes.values()
    (questao,) = [b for b in dados["blocos"] if b["tipo"] == "exercicio"]
    limpo = cc.sanitizar_bloco(questao)
    assert "referencia" not in limpo
    assert limpo["criterios"] == questao["criterios"]


def test_dissertativa_sem_criterio_nenhum_fica_de_fora_com_aviso():
    texto = DISSERTATIVA.replace("- Cita a luz como fonte de energia\n", "")
    texto = texto.replace("- Relaciona a luz à produção de glicose\n", "")
    texto = texto.replace("**Resposta esperada:** A luz fornece a energia que alimenta a produção de glicose.\n", "")
    texto += "\n### Questão 2\nQuanto é 2 + 2?\nA) 4\nB) 5\n**Resposta:** A\n"
    compilada = ci.compilar(CURSO, texto, versao="v1")
    (dados,) = compilada.estacoes.values()
    assert [b["formato"] for b in dados["blocos"] if b["tipo"] == "exercicio"] == ["multipla_escolha"]
    assert any("régua" in a for a in compilada.avisos)


def test_o_servidor_nao_corrige_dissertativo_sozinho():
    """Um `acertou` inventado aqui concluiria a estação sem ninguém ler o que o
    aluno escreveu."""
    (dados,) = ci.compilar(CURSO, DISSERTATIVA, versao="v1").estacoes.values()
    (questao,) = [b for b in dados["blocos"] if b["tipo"] == "exercicio"]
    with pytest.raises(ValueError):
        cc.corrigir(questao, "qualquer coisa")


def test_texto_torto_de_gerador_externo_compila_inteiro():
    """O texto como ele chega de um gerador de fora: seção numerada, título de
    questão sem marcação nenhuma, alternativa com marcador de lista e negrito.

    Nenhuma dessas variações é erro de quem escreveu — é só outro jeito de
    escrever a mesma aula."""
    texto = """# Regra de três

## 1. Objetivos
Resolver proporções diretas.

## 2. Conteúdo
Proporção é igualdade entre duas razões.

QUESTÃO 1
Se 2 kg custam R$ 10, quanto custam 5 kg?
- **A)** R$ 25
- **B)** R$ 20
**Resposta correta: A**
**Feedback:** Cada quilo custa R$ 5. A alternativa B multiplica errado.
dificuldade: básico
"""
    compilada = ci.compilar(CURSO, texto, versao="v1")
    assert compilada.problemas == []
    (dados,) = compilada.estacoes.values()
    assert cc.validar_estacao(dados) == []
    assert dados["titulo"] == "Regra de três"
    assert dados["objetivo"].startswith("Resolver")
    (questao,) = [b for b in dados["blocos"] if b["tipo"] == "exercicio"]
    assert len(questao["alternativas"]) == 2
    assert any(a["texto"] == "R$ 25" for a in questao["alternativas"])


def test_duas_secoes_de_exercicios_nao_apagam_uma_a_outra():
    """Título repetido SOMA. Sobrescrever apagaria metade das questões sem
    erro nenhum — que é a falha mais cara que este compilador pode ter."""
    texto = DISSERTATIVA + """
## Exercícios
### Questão 2
Quanto é 2 + 2?
A) 4
B) 5
**Resposta:** A
"""
    (dados,) = ci.compilar(CURSO, texto, versao="v1").estacoes.values()
    assert len([b for b in dados["blocos"] if b["tipo"] == "exercicio"]) == 2
