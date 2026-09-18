"""Estudar um curso: quem entra, o que a tela recebe e como se avança.

O que estes testes protegem, na ordem em que doeria:

1. **O gabarito não chega ao navegador.** Nem a dica, nem o feedback, nem a
   resolução — cada um chega na tentativa em que ensina alguma coisa. Um
   exercício cujo gabarito viaja junto com a pergunta não mede nada.
2. **Quem não comprou não estuda, e quem comprou estuda inteiro.** O acesso é
   binário e vem de fora (compra avulsa ou direito do pacote de 4.000). Aqui
   dentro não existe preço: cobrar por estação transformaria a aula num caixa.
3. **A trilha não trava e não se abre sozinha.** A estação seguinte abre com a
   anterior concluída, e a conclusão acontece sozinha na resposta que cumpre o
   critério — botão que o aluno não vê é trava que ninguém reporta.
4. **Nada no caminho do aluno lê o histórico.** `cursos_eventos` cresce com o
   uso e é só escrita; lê-la numa tela repetiria o incidente de cota de
   2026-09-04.
5. **XP uma vez por estação.** Refazer não fabrica XP.

Offline, com o dublê de Mongo do `conftest.py`, um Firestore de mentira e
conteúdo de teste escrito em `tmp_path` — nenhuma linha de conteúdo do produto
é usada aqui.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import cursos_comportamento as cb  # noqa: E402
import cursos_conteudo as cc  # noqa: E402
import engajamento as eng  # noqa: E402
import cursos_estudo_routes as routes  # noqa: E402
import cursos_progresso as cp  # noqa: E402
import firestore_service as fs  # noqa: E402
import rate_limit  # noqa: E402
from models import User  # noqa: E402

CURSO = "matematica-basica"   # existe no catálogo de produto (`cursos.CURSOS`)


def _run(coro):
    return asyncio.run(coro)


def _user(uid="aluno-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno Teste")


def _admin() -> User:
    return User(user_id="admin-1", email="admin@exemplo.com", name="Admin", is_admin=True)


# ---------------------------------------------------------------------------
# Conteúdo de teste
# ---------------------------------------------------------------------------


def _exercicio(bloco_id: str, nivel: int, **extra) -> dict:
    base = {
        "tipo": "exercicio", "bloco_id": bloco_id, "nivel": nivel,
        "formato": "multipla_escolha",
        "enunciado": f"Enunciado {bloco_id}.",
        "alternativas": [{"id": "a", "texto": "Certa"}, {"id": "b", "texto": "Errada"}],
        "gabarito": "a",
        "dica": "DICA-SECRETA",
        "feedback": {"a": "Isso.", "b": "COMENTARIO-DO-ERRO"},
        "solucao": "SOLUCAO-SECRETA",
    }
    base.update(extra)
    return base


def _estacao(estacao_id: str, blocos=None, **extra) -> dict:
    base = {
        "schema_version": "1.0", "estacao_id": estacao_id,
        "titulo": f"Estação {estacao_id}",
        "objetivo": "Ao fim desta estação você consegue testar.",
        "versao": "v1",
        "blocos": blocos or [
            {"tipo": "texto", "bloco_id": "t1", "markdown": "Texto."},
            _exercicio("x1", 1),
            _exercicio("x2", 2),
        ],
    }
    base.update(extra)
    return base


def _publicar(raiz: Path, estacoes: dict[str, dict], trilhas=None) -> None:
    pasta = raiz / CURSO
    (pasta / "estacoes").mkdir(parents=True, exist_ok=True)
    (pasta / "curso.json").write_text(json.dumps({
        "schema_version": "1.0", "curso_id": CURSO, "versao": "v1",
        "trilhas": trilhas or [
            {"trilha_id": "t", "titulo": "Trilha", "estacoes": list(estacoes)}
        ],
    }), encoding="utf-8")
    for nome, dados in estacoes.items():
        (pasta / "estacoes" / f"{nome}.json").write_text(json.dumps(dados), encoding="utf-8")
    bib = cc.recarregar(raiz)
    assert bib.problemas == (), "\n".join(str(p) for p in bib.problemas)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _sem_limites_residuais():
    rate_limit.limpar()
    yield
    rate_limit.limpar()


@pytest.fixture
def db(fake_db):
    routes.set_db(fake_db)
    return fake_db


@pytest.fixture
def sem_direitos(monkeypatch):
    """O padrão: ninguém tem direito de pacote nenhum."""
    monkeypatch.setattr(fs, "tem_cursos_inclusos", lambda uid: False)
    monkeypatch.setattr(fs, "dia_local", lambda *a, **k: "2026-09-16")


@pytest.fixture
def xp(monkeypatch):
    """Registra as chamadas ao motor de engajamento, sem executá-lo.

    O dublê HONRA `chave_unica`, como o motor de verdade: sem isso, um teste
    de "não paga duas vezes" passaria com uma implementação que paga sempre.
    """
    chamadas: list[dict] = []
    pagas: set[str] = set()

    async def _fake(uid, acoes, **kwargs):
        chamadas.append({"uid": uid, "acoes": acoes, **kwargs})
        chave = kwargs.get("chave_unica")
        if chave:
            if chave in pagas:
                return {"xp": 0, "ja_premiado": True}
            pagas.add(chave)
        return {"xp": sum(eng.XP_POR_ACAO.get(a, 0) for a in acoes)}

    import engajamento_service
    monkeypatch.setattr(engajamento_service, "registrar_acao", _fake)
    return chamadas


@pytest.fixture(autouse=True)
def firestore_de_mentira(monkeypatch):
    """Spark e evento de behavior sem tocar o Firestore.

    `autouse` porque responder um exercício passou a creditar Spark e a
    gravar comportamento: sem o dublê, QUALQUER teste de resposta iria ao
    Firestore de produção — o que o `conftest` corretamente proíbe.

    O dublê guarda o que foi pedido, e é sobre ele que os testes de economia
    e de contrato de behavior fazem suas afirmações.
    """
    creditos: dict[str, int] = {}
    eventos: list[dict] = []

    def _grant(uid, item_id, amount=1):
        chave = f"{uid}:{item_id}"
        if chave in creditos:
            return {"ja_concedido": True, "sparks_ganhos": 0}
        creditos[chave] = amount
        return {"ja_concedido": False, "sparks_ganhos": amount, "item_id": item_id}

    def _behavior(uid, **kwargs):
        if not kwargs.get("ontology_version"):
            raise ValueError("ontology_version é obrigatório no contrato de behavior 1.1")
        eventos.append({"uid": uid, **kwargs})
        return {"event_id": f"ev-{len(eventos)}"}

    monkeypatch.setattr(fs, "grant_question_sparks", _grant)
    monkeypatch.setattr(fs, "write_behavior_event", _behavior)
    return {"creditos": creditos, "eventos": eventos}


@pytest.fixture
def comprado(db):
    """O aluno pagou o preço de tabela pelo curso (documento de `cursos_routes`)."""
    _run(db.cursos_acessos.insert_one({
        "_id": f"aluno-1:{CURSO}", "user_id": "aluno-1", "curso_id": CURSO,
    }))
    return db


@pytest.fixture
def curso_de_duas_estacoes(tmp_path, db, sem_direitos):
    _publicar(tmp_path, {"e1": _estacao("e1"), "e2": _estacao("e2")})
    return tmp_path


# ============================================================ acesso


class TestAcesso:
    def test_curso_sem_conteudo_publicado_e_404(self, db, sem_direitos, tmp_path, comprado):
        cc.recarregar(tmp_path)  # pasta vazia: nenhum curso publicado
        with pytest.raises(HTTPException) as exc:
            _run(routes.ver_trilha(CURSO, user=_user()))
        assert exc.value.status_code == 404

    def test_curso_fora_do_catalogo_e_404(self, curso_de_duas_estacoes, comprado):
        with pytest.raises(HTTPException) as exc:
            _run(routes.ver_trilha("curso-que-nao-existe", user=_user()))
        assert exc.value.status_code == 404

    def test_quem_nao_comprou_leva_403_e_nao_404(self, curso_de_duas_estacoes, db):
        """403 e não 404: dizer "não existe" a quem pode comprar esconde
        justamente o que está à venda."""
        with pytest.raises(HTTPException) as exc:
            _run(routes.ver_trilha(CURSO, user=_user()))
        assert exc.value.status_code == 403

    def test_quem_comprou_entra(self, curso_de_duas_estacoes, comprado):
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        assert dados["curso"]["curso_id"] == CURSO

    def test_o_direito_do_pacote_entra_sem_documento_de_compra(
        self, curso_de_duas_estacoes, db, monkeypatch,
    ):
        """O pacote de 4.000 Sparks inclui o catálogo e NÃO cria documento de
        compra (ver `cursos_routes.comprar_curso`) — o direito é o registro."""
        monkeypatch.setattr(fs, "tem_cursos_inclusos", lambda uid: True)
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        assert dados["curso"]["curso_id"] == CURSO
        assert _run(db.cursos_acessos.count_documents({})) == 0

    def test_admin_entra_sem_comprar_e_sem_tocar_o_firestore(
        self, curso_de_duas_estacoes, db, monkeypatch,
    ):
        """É assim que se valida uma estação recém-escrita em produção antes
        de abrir o curso para alguém."""
        def _explode(uid):
            raise AssertionError("admin não pode custar leitura do Firestore")

        monkeypatch.setattr(fs, "tem_cursos_inclusos", _explode)
        dados = _run(routes.ver_trilha(CURSO, user=_admin()))
        assert dados["curso"]["curso_id"] == CURSO

    def test_quem_comprou_nao_paga_leitura_do_firestore(
        self, curso_de_duas_estacoes, comprado, monkeypatch,
    ):
        """A ordem das checagens é custo: o documento de compra resolve o caso
        no Mongo, e só quem não o tem paga a leitura do Firestore."""
        def _explode(uid):
            raise AssertionError("compra avulsa não pode custar leitura do Firestore")

        monkeypatch.setattr(fs, "tem_cursos_inclusos", _explode)
        _run(routes.ver_trilha(CURSO, user=_user()))


# ============================================================ o mapa


class TestTrilha:
    def test_a_primeira_estacao_abre_e_a_segunda_fica_trancada(
        self, curso_de_duas_estacoes, comprado,
    ):
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        estacoes = dados["trilhas"][0]["estacoes"]
        assert estacoes[0]["estado"] == cp.DISPONIVEL
        assert estacoes[1]["estado"] == cp.BLOQUEADA

    def test_a_proxima_e_a_primeira_liberada(self, curso_de_duas_estacoes, comprado):
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        assert dados["proxima"]["estacao_id"] == "e1"

    def test_o_percentual_conta_estacoes_concluidas(self, curso_de_duas_estacoes, comprado):
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        progresso = dados["progresso"]
        assert progresso["estacoes"] == 2
        assert progresso["concluidas"] == 0
        assert progresso["percentual"] == 0

    def test_a_trilha_anuncia_o_teto_de_xp_e_de_sparks(self, curso_de_duas_estacoes, comprado):
        """O número que a tela mostra sai da MESMA tabela que paga — nunca de
        uma constante escrita no React."""
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        progresso = dados["progresso"]
        # Duas estações de dois exercícios cada: um Spark por exercício.
        assert progresso["sparks_possiveis"] == 4
        assert progresso["xp_possivel"] == sum(
            e["xp_possivel"] for tr in dados["trilhas"] for e in tr["estacoes"]
        )
        assert progresso["xp_possivel"] > 0

    def test_o_cadeado_diz_o_nome_do_que_falta(self, tmp_path, db, sem_direitos, comprado):
        _publicar(tmp_path, {
            "e1": _estacao("e1"),
            "e2": _estacao("e2", pre_requisitos=["e1"]),
        })
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        faltando = dados["trilhas"][0]["estacoes"][1]["pre_requisitos_faltando"]
        assert faltando == [{"estacao_id": "e1", "titulo": "Estação e1"}]

    def test_trilhas_diferentes_comecam_abertas_em_paralelo(self, tmp_path, db, sem_direitos, comprado):
        """Quem quer começar por Frações e quem quer começar por Porcentagem
        estão os dois estudando."""
        _publicar(
            tmp_path,
            {"a1": _estacao("a1"), "b1": _estacao("b1")},
            trilhas=[
                {"trilha_id": "a", "titulo": "A", "estacoes": ["a1"]},
                {"trilha_id": "b", "titulo": "B", "estacoes": ["b1"]},
            ],
        )
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        assert [t["estacoes"][0]["estado"] for t in dados["trilhas"]] == [
            cp.DISPONIVEL, cp.DISPONIVEL,
        ]


# ============================================================ a estação


class TestAbrirEstacao:
    def test_o_gabarito_nao_vai_para_o_navegador(self, curso_de_duas_estacoes, comprado):
        dados = _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        bruto = json.dumps(dados, ensure_ascii=False)
        for segredo in ("DICA-SECRETA", "SOLUCAO-SECRETA", "COMENTARIO-DO-ERRO", '"gabarito"'):
            assert segredo not in bruto, f"{segredo} vazou para a tela"

    def test_a_tela_sabe_que_existe_dica_sem_saber_qual_e(self, curso_de_duas_estacoes, comprado):
        dados = _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        exercicio = next(b for b in dados["estacao"]["blocos"] if b["bloco_id"] == "x1")
        assert exercicio["tem_dica"] is True

    def test_estacao_trancada_responde_423(self, curso_de_duas_estacoes, comprado):
        with pytest.raises(HTTPException) as exc:
            _run(routes.abrir_estacao(CURSO, "e2", user=_user()))
        assert exc.value.status_code == 423

    def test_estacao_inexistente_e_404(self, curso_de_duas_estacoes, comprado):
        with pytest.raises(HTTPException) as exc:
            _run(routes.abrir_estacao(CURSO, "nao-existe", user=_user()))
        assert exc.value.status_code == 404

    def test_video_pendente_nao_vira_player_quebrado(self, tmp_path, db, sem_direitos, comprado):
        _publicar(tmp_path, {"e1": _estacao("e1", blocos=[
            {"tipo": "video", "bloco_id": "v1", "titulo": "A gravar",
             "provedor": "youtube", "ref": None},
            {"tipo": "video", "bloco_id": "v2", "titulo": "Pronto",
             "provedor": "youtube", "ref": "abc123"},
            _exercicio("x1", 1),
        ])})
        dados = _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        ids = [b["bloco_id"] for b in dados["estacao"]["blocos"]]
        assert "v1" not in ids and "v2" in ids

    def test_abrir_marca_o_inicio_uma_vez_so(self, curso_de_duas_estacoes, comprado, db):
        _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        primeiro = _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))["iniciada_em"]
        _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        assert _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))["iniciada_em"] == primeiro
        # E um único evento de início — senão a taxa de início infla com
        # recarregamento de página.
        eventos = _run(db.cursos_eventos.find({"evento": "estacao_iniciada"}).to_list(10))
        assert len(eventos) == 1

    def test_a_versao_do_conteudo_estudado_fica_gravada(self, curso_de_duas_estacoes, comprado):
        _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        doc = _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))
        assert doc["versao_conteudo"] == "v1"

    def test_a_navegacao_nao_atravessa_para_a_trilha_do_lado(
        self, tmp_path, db, sem_direitos, comprado,
    ):
        _publicar(
            tmp_path,
            {"a1": _estacao("a1"), "b1": _estacao("b1")},
            trilhas=[
                {"trilha_id": "a", "titulo": "A", "estacoes": ["a1"]},
                {"trilha_id": "b", "titulo": "B", "estacoes": ["b1"]},
            ],
        )
        dados = _run(routes.abrir_estacao(CURSO, "a1", user=_user()))
        assert dados["navegacao"] == {"anterior": None, "seguinte": None}


# ============================================================ responder


def _responder(bloco_id: str, resposta: str, uid="aluno-1", estacao="e1"):
    return _run(routes.responder(
        CURSO, estacao, bloco_id,
        payload=routes.RespostaRequest(resposta=resposta),
        user=_user(uid), _=None,
    ))


class TestResponder:
    def test_a_escada_didatica_revela_um_degrau_por_vez(self, curso_de_duas_estacoes, comprado):
        primeira = _responder("x1", "b")
        assert primeira["dica"] == "DICA-SECRETA"
        assert "solucao" not in primeira and "comentario" not in primeira

        segunda = _responder("x1", "b")
        assert segunda["comentario"] == "COMENTARIO-DO-ERRO"
        assert "solucao" not in segunda

        terceira = _responder("x1", "b")
        assert terceira["solucao"] == "SOLUCAO-SECRETA"

    def test_errar_nao_entrega_o_gabarito(self, curso_de_duas_estacoes, comprado):
        assert _responder("x1", "b")["gabarito"] is None

    def test_acertar_devolve_a_alternativa_certa_para_a_tela_pintar(
        self, curso_de_duas_estacoes, comprado,
    ):
        certa = _responder("x1", "a")
        assert certa["acertou"] is True and certa["gabarito"] == "a"

    def test_acerto_conta_uma_vez_so_por_exercicio(self, curso_de_duas_estacoes, comprado):
        _responder("x1", "a")
        assert _responder("x1", "a")["acertos"] == 1

    def test_errar_depois_de_acertar_nao_desfaz_o_acerto(self, curso_de_duas_estacoes, comprado):
        _responder("x1", "a")
        assert _responder("x1", "b")["acertos"] == 1

    def test_acerto_de_primeira_e_registrado_uma_vez(self, curso_de_duas_estacoes, comprado):
        _responder("x1", "b")
        _responder("x1", "a")
        doc = _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))
        assert doc["respostas"]["x1"]["acertou_de_primeira"] is False
        assert doc["respostas"]["x1"]["tentativas"] == 2

    def test_bloco_de_texto_nao_e_exercicio(self, curso_de_duas_estacoes, comprado):
        with pytest.raises(HTTPException) as exc:
            _responder("t1", "a")
        assert exc.value.status_code == 404

    def test_estacao_trancada_nao_aceita_resposta(self, curso_de_duas_estacoes, comprado):
        with pytest.raises(HTTPException) as exc:
            _responder("x1", "a", estacao="e2")
        assert exc.value.status_code == 423


# ============================================================ concluir


class TestConclusao:
    def test_acertar_o_que_conta_conclui_a_estacao_sozinho(
        self, curso_de_duas_estacoes, comprado, xp,
    ):
        assert _responder("x1", "a")["estacao_concluida"] is False
        ultima = _responder("x2", "a")
        assert ultima["estacao_concluida"] is True
        assert ultima["concluiu_agora"] is True

    def test_concluir_libera_a_estacao_seguinte(self, curso_de_duas_estacoes, comprado, xp):
        _responder("x1", "a")
        _responder("x2", "a")
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        estados = [e["estado"] for e in dados["trilhas"][0]["estacoes"]]
        # Acertou os dois de primeira: a estação não só concluiu, ela foi
        # DOMINADA — e a seguinte abre igual.
        assert estados == [cp.DOMINADA, cp.DISPONIVEL]

    def test_quem_erra_antes_de_acertar_conclui_sem_dominar(
        self, curso_de_duas_estacoes, comprado, xp,
    ):
        """A diferença entre concluída e dominada é dado, não enfeite: sai de
        `acertou_de_primeira`, que o documento já guardava."""
        _responder("x1", "b")   # erra
        _responder("x1", "a")
        _responder("x2", "a")
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        primeira = dados["trilhas"][0]["estacoes"][0]
        assert primeira["estado"] == cp.CONCLUIDA
        assert primeira["acertos_de_primeira"] == 1

    def test_desafio_nao_e_necessario_para_concluir(self, tmp_path, db, sem_direitos, comprado, xp):
        _publicar(tmp_path, {"e1": _estacao("e1", blocos=[
            _exercicio("x1", 1),
            _exercicio("d1", 3, tipo="desafio"),
        ])})
        assert _responder("x1", "a")["estacao_concluida"] is True

    def test_exercicio_opcional_nao_e_necessario_para_concluir(
        self, tmp_path, db, sem_direitos, comprado, xp,
    ):
        _publicar(tmp_path, {"e1": _estacao("e1", blocos=[
            _exercicio("x1", 1),
            _exercicio("x2", 2, opcional=True),
        ])})
        assert _responder("x1", "a")["estacao_concluida"] is True

    def test_minimo_de_acertos_conclui_antes_do_fim(self, tmp_path, db, sem_direitos, comprado, xp):
        _publicar(tmp_path, {"e1": _estacao(
            "e1",
            blocos=[_exercicio("x1", 1), _exercicio("x2", 2), _exercicio("x3", 3)],
            conclusao={"tipo": "minimo_de_acertos", "minimo": 2},
        )})
        _responder("x1", "a")
        assert _responder("x2", "a")["estacao_concluida"] is True

    def test_xp_uma_vez_por_estacao(self, curso_de_duas_estacoes, comprado, xp):
        _responder("x1", "a")
        _responder("x2", "a")
        # Responder de novo depois de concluída não paga XP de novo.
        _responder("x1", "a")
        _responder("x2", "a")
        conclusoes = [c for c in xp if c["acoes"] == ["estacao_concluida"]]
        assert len(conclusoes) == 1
        assert conclusoes[0]["chave_unica"] == f"estacao:{CURSO}:e1"

    def test_todo_xp_de_exercicio_tem_guarda_de_unicidade(
        self, curso_de_duas_estacoes, comprado, xp,
    ):
        """Exercício de curso pode ser refeito à vontade. Sem `chave_unica` em
        TODA chamada, um laço de respostas erradas fabricaria XP e o ranking
        da liga deixaria de significar alguma coisa."""
        _responder("x1", "b")
        _responder("x1", "a")
        _responder("x1", "a")
        assert all(c.get("chave_unica") for c in xp)
        assert set(c["chave_unica"] for c in xp) == {
            f"tentou:CURSO:{CURSO}:e1:x1", f"acertou:CURSO:{CURSO}:e1:x1",
        }

    def test_conclusao_e_atomica(self, curso_de_duas_estacoes, comprado, db, xp):
        """Duas conclusões simultâneas concluem UMA vez — a condição está no
        filtro do update, não num `if` antes dele."""
        estacao = cc.biblioteca().estacao(CURSO, "e1")
        for bloco_id in ("x1", "x2"):
            _run(cp.registrar_resposta(
                "aluno-1", estacao, estacao.bloco(bloco_id), acertou=True, chave="a",
            ))
        progresso = _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))

        async def _as_duas():
            return await asyncio.gather(
                cp.talvez_concluir("aluno-1", estacao, progresso),
                cp.talvez_concluir("aluno-1", estacao, progresso),
            )

        _run(_as_duas())
        eventos = _run(db.cursos_eventos.find({"evento": "estacao_concluida"}).to_list(10))
        assert len(eventos) == 1
        assert len(xp) == 1

    def test_falha_do_motor_de_xp_nao_derruba_a_conclusao(
        self, curso_de_duas_estacoes, comprado, monkeypatch,
    ):
        """Perder o XP é aborrecimento; perder a conclusão é perder o estudo."""
        async def _explode(*a, **k):
            raise RuntimeError("motor fora do ar")

        import engajamento_service
        monkeypatch.setattr(engajamento_service, "registrar_acao", _explode)
        _responder("x1", "a")
        assert _responder("x2", "a")["estacao_concluida"] is True


# ============================================================ analytics


class TestHistorico:
    def test_cada_interacao_vira_uma_linha_de_historico(self, curso_de_duas_estacoes, comprado, db, xp):
        _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        _run(routes.marcar_visto(CURSO, "e1", "t1", user=_user()))
        _responder("x1", "b")
        _responder("x1", "a")
        _responder("x2", "a")

        eventos = _run(db.cursos_eventos.find({}).to_list(100))
        por_tipo = {}
        for e in eventos:
            por_tipo[e["evento"]] = por_tipo.get(e["evento"], 0) + 1
        assert por_tipo == {
            "estacao_iniciada": 1, "bloco_visto": 1,
            "exercicio_respondido": 3, "estacao_concluida": 1,
        }

    def test_o_evento_carrega_o_que_a_analise_precisa(self, curso_de_duas_estacoes, comprado, db):
        _responder("x1", "b")
        evento = _run(db.cursos_eventos.find({"evento": "exercicio_respondido"}).to_list(1))[0]
        assert evento["curso_id"] == CURSO and evento["estacao_id"] == "e1"
        assert evento["versao_conteudo"] == "v1"
        assert evento["nivel"] == 1 and evento["chave"] == "b"
        assert evento["acertou"] is False and evento["tentativa"] == 1

    def test_ver_o_mesmo_bloco_duas_vezes_nao_duplica_o_evento(
        self, curso_de_duas_estacoes, comprado, db,
    ):
        _run(routes.marcar_visto(CURSO, "e1", "t1", user=_user()))
        _run(routes.marcar_visto(CURSO, "e1", "t1", user=_user()))
        assert len(_run(db.cursos_eventos.find({"evento": "bloco_visto"}).to_list(10))) == 1

    def test_o_caminho_do_aluno_nunca_le_o_historico(self, curso_de_duas_estacoes, comprado, db, xp):
        """A regra que vale para o app inteiro desde o incidente de cota:
        nenhuma tela pode custar O(eventos)."""
        _responder("x1", "a")
        _responder("x2", "a")

        colecao = db.cursos_eventos
        original = colecao.find

        def _proibido(*a, **k):
            raise AssertionError("tela de aluno não pode ler `cursos_eventos`")

        colecao.find = _proibido
        try:
            _run(routes.ver_trilha(CURSO, user=_user()))
            _run(routes.abrir_estacao(CURSO, "e2", user=_user()))
            _responder("x1", "a", estacao="e2")
        finally:
            colecao.find = original

    def test_tempo_absurdo_do_cliente_e_aparado(self, curso_de_duas_estacoes, comprado, db):
        """A aba esquecida aberta a noite toda envenenaria a média de tempo do
        curso inteiro."""
        _run(routes.responder(
            CURSO, "e1", "x1",
            payload=routes.RespostaRequest(resposta="b", tempo_segundos=99999),
            user=_user(), _=None,
        ))
        evento = _run(db.cursos_eventos.find({"evento": "exercicio_respondido"}).to_list(1))[0]
        assert evento["tempo_segundos"] == cp.TEMPO_MAXIMO_SEGUNDOS


# ============================================================ admin


class TestPainelDoAdmin:
    def test_inventario_mostra_o_que_esta_publicado(self, curso_de_duas_estacoes, db):
        inv = _run(routes.inventario(admin=_admin()))
        curso = next(c for c in inv["cursos"] if c["curso_id"] == CURSO)
        assert curso["publicado"] is True and curso["estacoes"] == 2

    def test_a_analise_responde_onde_a_turma_trava(self, curso_de_duas_estacoes, comprado, db, xp):
        _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        _responder("x1", "b")          # erra
        _responder("x1", "b")          # erra de novo
        _responder("x1", "a")          # acerta na terceira
        _responder("x2", "a")          # acerta de primeira

        analise = _run(routes.analise(CURSO, admin=_admin()))
        e1 = next(e for e in analise["estacoes"] if e["estacao_id"] == "e1")
        assert e1["iniciaram"] == 1 and e1["concluiram"] == 1

        x1 = next(x for x in e1["exercicios"] if x["bloco_id"] == "x1")
        assert x1["tentativas"] == 3
        assert x1["acerto_de_primeira"] == 0
        # A alternativa errada mais escolhida é o mapa do equívoco da turma.
        assert x1["escolhas"][0] == {"chave": "b", "vezes": 2}

        x2 = next(x for x in e1["exercicios"] if x["bloco_id"] == "x2")
        assert x2["acerto_de_primeira"] == 100

    def test_analise_de_curso_sem_conteudo_e_404(self, tmp_path, db):
        cc.recarregar(tmp_path)
        with pytest.raises(HTTPException) as exc:
            _run(routes.analise(CURSO, admin=_admin()))
        assert exc.value.status_code == 404


# ============================================================ economia e behavior


def _sondar(uid="aluno-1", estacao="e1"):
    return _run(routes.abrir_sondagem(CURSO, estacao, user=_user(uid), _=None))


def _responder_sondagem(bloco_id: str, resposta: str, uid="aluno-1", estacao="e1"):
    return _run(routes.responder_sondagem(
        CURSO, estacao,
        payload=routes.RespostaDeSondagem(bloco_id=bloco_id, resposta=resposta),
        user=_user(uid), _=None,
    ))


class TestRecompensa:
    """+1 Spark por acerto, XP por esforço — e nenhum dos dois duas vezes.

    O que está sendo protegido aqui não é o número: é a promessa da tela. A
    devolutiva anuncia o que ENTROU nesta resposta, e anunciar um Spark que
    não foi creditado é o jeito mais rápido de fazer o aluno desconfiar do
    saldo inteiro.
    """

    def test_acertar_credita_um_spark(self, curso_de_duas_estacoes, comprado, xp, firestore_de_mentira):
        r = _responder("x1", "a")
        assert r["recompensa"]["sparks"] == 1
        assert f"aluno-1:CURSO:{CURSO}:e1:x1" in firestore_de_mentira["creditos"]

    def test_errar_nao_credita_spark(self, curso_de_duas_estacoes, comprado, xp):
        r = _responder("x1", "b")
        assert r["recompensa"]["sparks"] == 0
        # Mas o esforço vale XP: é o que separa Spark (dinheiro) de XP (mérito).
        assert r["recompensa"]["xp"] > 0

    def test_refazer_exercicio_nao_credita_de_novo(self, curso_de_duas_estacoes, comprado, xp):
        primeira = _responder("x1", "a")
        segunda = _responder("x1", "a")
        assert primeira["recompensa"] == {"sparks": 1, "xp": primeira["recompensa"]["xp"]}
        assert segunda["recompensa"] == {"sparks": 0, "xp": 0}

    def test_exercicio_dificil_vale_mais_xp(self, tmp_path, db, sem_direitos, comprado, xp):
        """O XP por dificuldade é configuração (`engajamento.XP_POR_ACAO`), e a
        tela não participa da conta."""
        _publicar(tmp_path, {"e1": _estacao("e1", blocos=[
            _exercicio("facil", 1), _exercicio("dificil", 4),
        ])})
        facil = _responder("facil", "a")["recompensa"]["xp"]
        dificil = _responder("dificil", "a")["recompensa"]["xp"]
        assert dificil > facil

    def test_a_falha_do_firestore_nao_derruba_a_resposta(
        self, curso_de_duas_estacoes, comprado, xp, monkeypatch,
    ):
        """Perder um Spark é aborrecimento; perder a resposta é perder o estudo."""
        def _explode(*a, **k):
            raise RuntimeError("Firestore fora do ar")

        monkeypatch.setattr(fs, "grant_question_sparks", _explode)
        monkeypatch.setattr(fs, "write_behavior_event", _explode)
        r = _responder("x1", "a")
        assert r["acertou"] is True
        assert r["recompensa"]["sparks"] == 0
        assert _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))["respostas"]["x1"]["acertou"]


class TestBehavior:
    """Curso e ENEM escrevem no MESMO contrato de behavior.

    É a condição para a pergunta que justifica o ecossistema: *este aluno erra
    o mesmo tipo de coisa na prova e na aula?* Dois formatos "parecidos" não
    se cruzam; o mesmo formato se cruza com um `where`.
    """

    def test_responder_grava_o_evento_canonico(
        self, curso_de_duas_estacoes, comprado, xp, firestore_de_mentira,
    ):
        _responder("x1", "b")
        assert len(firestore_de_mentira["eventos"]) == 1
        ev = firestore_de_mentira["eventos"][0]
        assert ev["uid"] == "aluno-1"
        assert ev["item_id"] == f"CURSO:{CURSO}:e1:x1"
        assert ev["acertou"] is False
        assert ev["alternativa_escolhida"] == "b"
        assert ev["contexto_tipo"] == "curso"
        # A estação é a atividade a que o item pertence — é o campo do
        # contrato que responde "de onde veio esta resposta".
        assert ev["prova_id"] == f"{CURSO}:e1"
        assert ev["origem"] == "curso_local"
        assert ev["numero_tentativas"] == 1

    def test_o_evento_declara_a_versao_do_conteudo(
        self, curso_de_duas_estacoes, comprado, xp, firestore_de_mentira,
    ):
        """`ontology_version` é obrigatório desde a 1.1 e precisa dizer a
        verdade sobre a origem do item; `item_schema_version` é a versão DA
        ESTAÇÃO, que muda quando o texto é reescrito."""
        _responder("x1", "a")
        ev = firestore_de_mentira["eventos"][0]
        assert ev["ontology_version"] == cb.ONTOLOGY_VERSION_CURSOS
        assert ev["item_schema_version"] == "v1"

    def test_o_hash_do_item_nao_carrega_gabarito(
        self, curso_de_duas_estacoes, comprado, xp, firestore_de_mentira,
    ):
        """O hash cobre o que o aluno VIU. Corrigir uma vírgula no feedback
        não pode mudar a identidade do item que ele respondeu."""
        _responder("x1", "a")
        conteudo = firestore_de_mentira["eventos"][0]["item_content"]
        assert "gabarito" not in conteudo
        assert "solucao" not in conteudo
        assert "dica" not in conteudo

    def test_numerico_nao_inventa_alternativa_escolhida(
        self, tmp_path, db, sem_direitos, comprado, xp, firestore_de_mentira,
    ):
        _publicar(tmp_path, {"e1": _estacao("e1", blocos=[{
            "tipo": "exercicio", "bloco_id": "n1", "nivel": 1, "formato": "numerico",
            "enunciado": "Quanto é 2+2?", "gabarito": {"valor": 4, "tolerancia": 0},
            "feedback": {"correto": "Isso.", "incorreto": "Não."},
        }])})
        _run(routes.responder(
            CURSO, "e1", "n1",
            payload=routes.RespostaRequest(resposta="4"), user=_user(), _=None,
        ))
        ev = firestore_de_mentira["eventos"][0]
        assert ev["alternativa_escolhida"] is None
        assert ev["acertou"] is True

    def test_a_sondagem_tem_contexto_proprio(
        self, curso_de_duas_estacoes, comprado, xp, firestore_de_mentira,
    ):
        """Tentar pular é comportamento, e é comportamento DIFERENTE de
        estudar — senão não dá para perguntar depois como vai quem tenta."""
        _sondar()
        _responder_sondagem("x2", "a")
        assert firestore_de_mentira["eventos"][-1]["contexto_tipo"] == "curso_dominio"


class TestDominio:
    """"Já domino isto": provar, e não pular por vontade própria."""

    @pytest.fixture
    def estacao_com_cinco(self, tmp_path, db, sem_direitos):
        _publicar(tmp_path, {"e1": _estacao("e1", blocos=[
            _exercicio("x1", 1), _exercicio("x2", 2), _exercicio("x3", 3),
            _exercicio("x4", 4), _exercicio("x5", 5),
        ]), "e2": _estacao("e2")})
        return tmp_path

    def test_a_sondagem_pergunta_os_mais_dificeis(self, estacao_com_cinco, comprado, xp):
        sondagem = _sondar()
        assert [b["bloco_id"] for b in sondagem["blocos"]] == ["x5", "x4", "x3"]
        assert sondagem["regra"] == {"questoes": 3, "acertos_necessarios": 3, "de_primeira": True}

    def test_a_sondagem_nao_entrega_gabarito(self, estacao_com_cinco, comprado, xp):
        bruto = json.dumps(_sondar(), ensure_ascii=False)
        assert "DICA-SECRETA" not in bruto
        assert "SOLUCAO-SECRETA" not in bruto
        assert '"gabarito"' not in bruto

    def test_acertar_tudo_de_primeira_pula_a_estacao(self, estacao_com_cinco, comprado, xp):
        _sondar()
        _responder_sondagem("x5", "a")
        _responder_sondagem("x4", "a")
        r = _responder_sondagem("x3", "a")
        assert r["estacao_pulada"] is True
        assert r["pulou_agora"] is True

        progresso = _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))
        # PULADA não é CONCLUÍDA. O produto (e a Mentis) não podem afirmar que
        # este aluno estudou esta estação.
        assert progresso["pulada_em"]
        assert "concluida_em" not in progresso
        # E a evidência fica registrada: o que foi perguntado e como ele foi.
        assert progresso["dominio"]["blocos"] == ["x5", "x4", "x3"]
        assert progresso["dominio"]["acertos_de_primeira"] == 3

    def test_pular_libera_a_estacao_seguinte(self, estacao_com_cinco, comprado, xp):
        _sondar()
        for bloco in ("x5", "x4", "x3"):
            _responder_sondagem(bloco, "a")
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        estados = [e["estado"] for e in dados["trilhas"][0]["estacoes"]]
        assert estados == [cp.PULADA, cp.DISPONIVEL]
        assert dados["progresso"]["puladas"] == 1
        assert dados["progresso"]["estudadas"] == 0
        # Andou uma estação: a barra não pode dizer 0%.
        assert dados["progresso"]["percentual"] == 50

    def test_errar_um_nao_pula(self, estacao_com_cinco, comprado, xp):
        _sondar()
        _responder_sondagem("x5", "a")
        _responder_sondagem("x4", "b")   # erra
        r = _responder_sondagem("x3", "a")
        assert r["estacao_pulada"] is False
        assert r["reprovado"] is True

    def test_acertar_na_segunda_tentativa_nao_e_dominio(self, estacao_com_cinco, comprado, xp):
        """Acerto na segunda mede persistência, não domínio prévio."""
        _sondar()
        _responder_sondagem("x5", "b")
        _responder_sondagem("x5", "a")
        _responder_sondagem("x4", "a")
        r = _responder_sondagem("x3", "a")
        assert r["estacao_pulada"] is False

    def test_as_respostas_da_sondagem_contam_para_a_estacao(self, estacao_com_cinco, comprado, xp):
        """Eram exercícios de verdade. Quem não passou não perdeu o que fez."""
        _sondar()
        _responder_sondagem("x5", "a")
        _responder_sondagem("x4", "b")
        r = _responder_sondagem("x3", "a")
        assert r["acertos"] == 2

    def test_a_porta_da_estacao_sabe_que_a_sondagem_foi_usada(
        self, estacao_com_cinco, comprado, xp,
    ):
        """Sem este campo, a sala de aula ofereceria "já domino isto" a quem
        acabou de usar a chance — e o servidor recusaria o clique."""
        antes = _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        assert antes["progresso"]["sondagem_usada"] is False
        _sondar()
        depois = _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        assert depois["progresso"]["sondagem_usada"] is True

    def test_a_porta_da_estacao_sabe_que_ela_foi_pulada(self, estacao_com_cinco, comprado, xp):
        _sondar()
        for bloco in ("x5", "x4", "x3"):
            _responder_sondagem(bloco, "a")
        dados = _run(routes.abrir_estacao(CURSO, "e1", user=_user()))
        assert dados["progresso"]["pulada_em"]
        assert dados["progresso"]["concluida_em"] is None

    def test_a_sondagem_vale_uma_vez(self, estacao_com_cinco, comprado, xp):
        _sondar()
        _responder_sondagem("x5", "b")
        _responder_sondagem("x4", "b")
        _responder_sondagem("x3", "b")
        with pytest.raises(HTTPException) as exc:
            _sondar()
        assert exc.value.status_code == 409

    def test_nao_da_para_sondar_exercicio_facil(self, estacao_com_cinco, comprado, xp):
        """O cliente não escolhe o que a sondagem pergunta — senão "provar
        domínio" viraria acertar o exercício mais fácil da estação."""
        _sondar()
        with pytest.raises(HTTPException) as exc:
            _responder_sondagem("x1", "a")
        assert exc.value.status_code == 404

    def test_estacao_bloqueada_nao_pode_ser_sondada(self, tmp_path, db, sem_direitos, comprado, xp):
        _publicar(tmp_path, {"e1": _estacao("e1"), "e2": _estacao("e2")})
        with pytest.raises(HTTPException) as exc:
            _sondar(estacao="e2")
        assert exc.value.status_code == 423

    def test_estacao_ja_concluida_nao_tem_o_que_pular(self, curso_de_duas_estacoes, comprado, xp):
        _responder("x1", "a")
        _responder("x2", "a")
        with pytest.raises(HTTPException) as exc:
            _sondar()
        assert exc.value.status_code == 409

    def test_pular_paga_xp_uma_vez_e_menos_que_concluir(self, estacao_com_cinco, comprado, xp):
        """Provar domínio é trabalho, e vale menos que atravessar a estação.
        As duas ações dividem a `chave_unica`: a estação paga XP UMA vez."""
        _sondar()
        for bloco in ("x5", "x4", "x3"):
            _responder_sondagem(bloco, "a")
        estacao = [c for c in xp if c["chave_unica"] == f"estacao:{CURSO}:e1"]
        assert [c["acoes"] for c in estacao] == [["estacao_dominada"]]
        assert eng.XP_POR_ACAO["estacao_dominada"] < eng.XP_POR_ACAO["estacao_concluida"]


# ============================================================ pular até aqui


def _abrir_salto(estacao: str, uid="aluno-1"):
    return _run(routes.abrir_salto(CURSO, estacao, user=_user(uid), _=None))


def _responder_salto(bloco_id: str, resposta: str, estacao: str, uid="aluno-1"):
    return _run(routes.responder_salto(
        CURSO, estacao,
        payload=routes.RespostaDoSalto(bloco_id=bloco_id, resposta=resposta),
        user=_user(uid), _=None,
    ))


def _curso_longo(raiz, quantas=6, exercicios=4):
    """Um curso com estações suficientes para o salto ter o que sortear."""
    estacoes = {}
    for i in range(1, quantas + 1):
        blocos = [_exercicio(f"e{i}x{j}", min(5, j)) for j in range(1, exercicios + 1)]
        estacoes[f"e{i}"] = _estacao(f"e{i}", blocos=blocos)
    _publicar(raiz, estacoes)
    return estacoes


class TestSparkDePrimeira:
    """Spark só no acerto de PRIMEIRA — e a regra não é anunciada na tela.

    Com quatro alternativas e tentativa livre, todo exercício acaba certo: o
    Spark por "acerto eventual" pagaria persistência de clique, não domínio.
    """

    def test_acerto_depois_de_errar_nao_paga_spark(self, curso_de_duas_estacoes, comprado, xp):
        assert _responder("x1", "b")["recompensa"]["sparks"] == 0
        certa = _responder("x1", "a")
        assert certa["acertou"] is True
        assert certa["recompensa"]["sparks"] == 0
        # Mas o acerto continua contando para concluir a estação.
        assert certa["acertos"] == 1

    def test_acerto_de_primeira_paga(self, curso_de_duas_estacoes, comprado, xp):
        assert _responder("x1", "a")["recompensa"]["sparks"] == 1


class TestSalto:
    """"Pular até aqui": provar tudo que vem antes, de uma vez."""

    @pytest.fixture
    def curso_longo(self, tmp_path, db, sem_direitos):
        _curso_longo(tmp_path)
        return tmp_path

    def test_a_prova_sorteia_de_todas_as_estacoes_anteriores(self, curso_longo, comprado, xp):
        salto = _abrir_salto("e5")
        origens = {b["estacao_id"] for b in salto["blocos"]}
        assert origens == {"e1", "e2", "e3", "e4"}
        # Nenhuma questão do destino nem do que vem depois dele.
        assert "e5" not in origens and "e6" not in origens

    def test_a_prova_nao_entrega_gabarito(self, curso_longo, comprado, xp):
        bruto = json.dumps(_abrir_salto("e5"), ensure_ascii=False)
        assert '"gabarito"' not in bruto
        assert "SOLUCAO-SECRETA" not in bruto

    def test_reabrir_devolve_a_mesma_prova(self, curso_longo, comprado, xp):
        """F5 não pode ser um sorteio novo até sair uma prova fácil."""
        primeira = [b["bloco_id"] for b in _abrir_salto("e5")["blocos"]]
        segunda = [b["bloco_id"] for b in _abrir_salto("e5")["blocos"]]
        assert primeira == segunda

    def test_acertar_o_bastante_pula_tudo_que_vem_antes(self, curso_longo, comprado, xp):
        salto = _abrir_salto("e5")
        ultimo = None
        for b in salto["blocos"]:
            ultimo = _responder_salto(b["bloco_id"], "a", "e5")
        assert ultimo["aprovado"] is True
        assert set(ultimo["puladas"]) == {"e1", "e2", "e3", "e4"}

        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        por_id = {e["estacao_id"]: e for tr in dados["trilhas"] for e in tr["estacoes"]}
        assert [por_id[f"e{i}"]["estado"] for i in range(1, 5)] == [cp.PULADA] * 4
        # E o destino abre.
        assert por_id["e5"]["estado"] == cp.DISPONIVEL

    def test_pular_nao_paga_spark(self, curso_longo, comprado, xp, firestore_de_mentira):
        for b in _abrir_salto("e5")["blocos"]:
            r = _responder_salto(b["bloco_id"], "a", "e5")
            assert "recompensa" not in r
        assert firestore_de_mentira["creditos"] == {}

    def test_a_prova_nao_marca_progresso_nas_estacoes_de_origem(self, curso_longo, comprado, xp):
        """Foi prova, não aula: a estação de origem não pode ganhar um acerto
        que o aluno não conquistou estudando."""
        for b in _abrir_salto("e5")["blocos"][:2]:
            _responder_salto(b["bloco_id"], "a", "e5")
        origem = _run(cp.progresso_da_estacao("aluno-1", CURSO, "e1"))
        assert not origem.get("respostas")

    def test_errar_demais_reprova_e_nao_pula(self, curso_longo, comprado, xp):
        salto = _abrir_salto("e5")
        ultimo = None
        for i, b in enumerate(salto["blocos"]):
            ultimo = _responder_salto(b["bloco_id"], "a" if i < 2 else "b", "e5")
        assert ultimo["reprovado"] is True
        assert ultimo["puladas"] == []
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        por_id = {e["estacao_id"]: e for tr in dados["trilhas"] for e in tr["estacoes"]}
        assert por_id["e2"]["estado"] == cp.BLOQUEADA

    def test_a_prova_vale_uma_vez_por_destino(self, curso_longo, comprado, xp):
        for b in _abrir_salto("e5")["blocos"]:
            _responder_salto(b["bloco_id"], "b", "e5")
        with pytest.raises(HTTPException) as exc:
            _abrir_salto("e5")
        assert exc.value.status_code == 409

    def test_quem_reprovou_pode_provar_um_salto_mais_curto(self, curso_longo, comprado, xp):
        """A saída de quem não passou não é estudar tudo: é provar menos."""
        for b in _abrir_salto("e5")["blocos"]:
            _responder_salto(b["bloco_id"], "b", "e5")
        assert _abrir_salto("e3")["blocos"]

    def test_o_cliente_nao_escolhe_a_questao(self, curso_longo, comprado, xp):
        salto = _abrir_salto("e5")
        sorteadas = {b["bloco_id"] for b in salto["blocos"]}
        # De uma estação DEPOIS do destino: nunca entra numa prova de salto.
        assert "e6x1" not in sorteadas
        with pytest.raises(HTTPException) as exc:
            _responder_salto("e6x1", "a", "e5")
        assert exc.value.status_code == 404

    def test_nao_da_para_responder_duas_vezes(self, curso_longo, comprado, xp):
        b = _abrir_salto("e5")["blocos"][0]["bloco_id"]
        _responder_salto(b, "b", "e5")
        with pytest.raises(HTTPException) as exc:
            _responder_salto(b, "a", "e5")
        assert exc.value.status_code == 409

    def test_nao_ha_o_que_pular_na_primeira_estacao(self, curso_longo, comprado, xp):
        with pytest.raises(HTTPException) as exc:
            _abrir_salto("e1")
        assert exc.value.status_code == 409

    def test_a_trilha_diz_onde_o_salto_existe(self, curso_longo, comprado, xp):
        dados = _run(routes.ver_trilha(CURSO, user=_user()))
        por_id = {e["estacao_id"]: e for tr in dados["trilhas"] for e in tr["estacoes"]}
        assert por_id["e1"]["pode_saltar"] is False
        assert por_id["e4"]["pode_saltar"] is True
        assert por_id["e4"]["estacoes_a_pular"] == 3

    def test_o_comportamento_do_salto_entra_no_historico(
        self, curso_longo, comprado, xp, firestore_de_mentira,
    ):
        """Tentar pular é comportamento, e é dado que a Mentis vai querer."""
        b = _abrir_salto("e5")["blocos"][0]
        _responder_salto(b["bloco_id"], "a", "e5")
        ev = firestore_de_mentira["eventos"][-1]
        assert ev["item_id"].endswith(b["bloco_id"])
        # O item pertence à estação de ORIGEM, não ao destino do salto.
        assert b["estacao_id"] in ev["prova_id"]


# ---------------------------------------------------------------------------
# "Explicar melhor" um trecho de leitura — mentis_routes.explicar_trecho
# ---------------------------------------------------------------------------


class TestExplicarBloco:
    """O texto que vai para a Mentis é resolvido AQUI, do conteúdo publicado —
    nunca aceito do cliente. `mentis_routes.explicar_trecho` em si já tem
    cobertura própria (`test_mentis_explicacao_conteudo.py`); o que se testa
    aqui é a ponte: acesso, resolução do bloco certo e os tipos que o botão
    aceita."""

    def test_sem_acesso_e_403(self, curso_de_duas_estacoes, db, xp):
        with pytest.raises(HTTPException) as exc:
            _run(routes.explicar_bloco(CURSO, "e1", "t1", user=_user(), _=None))
        assert exc.value.status_code == 403

    def test_bloco_de_exercicio_nao_pode_ser_explicado(self, curso_de_duas_estacoes, comprado, xp):
        with pytest.raises(HTTPException) as exc:
            _run(routes.explicar_bloco(CURSO, "e1", "x1", user=_user(), _=None))
        assert exc.value.status_code == 404

    def test_bloco_inexistente_e_404(self, curso_de_duas_estacoes, comprado, xp):
        with pytest.raises(HTTPException) as exc:
            _run(routes.explicar_bloco(CURSO, "e1", "fantasma", user=_user(), _=None))
        assert exc.value.status_code == 404

    def test_encaminha_o_texto_do_bloco_e_o_contexto_certos(
        self, monkeypatch, curso_de_duas_estacoes, comprado, xp,
    ):
        visto = {}

        async def _fake(uid, *, origem, ref_id, contexto, texto_fonte):
            visto.update(uid=uid, origem=origem, ref_id=ref_id, contexto=contexto, texto_fonte=texto_fonte)
            return {"paragrafos": ["um", "dois", "três"], "sparks_balance": 990, "cache": False}

        monkeypatch.setattr(routes.mentis_routes, "explicar_trecho", _fake)
        out = _run(routes.explicar_bloco(CURSO, "e1", "t1", user=_user(), _=None))
        assert out["paragrafos"] == ["um", "dois", "três"]
        assert visto["origem"] == "curso"
        assert visto["ref_id"] == f"{CURSO}:e1:t1:v1"
        assert visto["texto_fonte"] == "Texto."
        assert "Estação e1" in visto["contexto"]
