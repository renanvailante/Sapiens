"""O ciclo fechado, ponta a ponta, pela rota que o aluno de fato usa.

    observar → interpretar → intervir → reter → retestar

`register_answer` é onde as três primeiras fases se encontram: o evento é
gravado (observar), o Error Trace é produzido do item que a rota já tinha na
mão (interpretar), o estado de revisão avança e o gatilho decide se interrompe
(intervir), e a micropergunta da Fase 3 sai junto. Os módulos têm testes
próprios; o que se protege AQUI é a fiação — que é o que quebra calado.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import firestore_routes as fr  # noqa: E402
import firestore_service as fs  # noqa: E402
import microdiagnostico  # noqa: E402
import portao_crenca  # noqa: E402
import revisao_espacada as rev  # noqa: E402
import revisao_service  # noqa: E402
from models import User  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


ALUNO = User(user_id="U1", email="a@x.com", name="Ana")
PROC = "PROC-SIMB-01"
ERRO = "ERR-03"

ITEM_ANOTADO = {
    "item_id": "I-1",
    "item_hash": "h-1",
    "ontology_version": "1.4.1",
    "fonte": {"banca": "ENEM", "ano": 2023, "prova": "AMARELO", "numero": 93, "disciplina": "Física"},
    "estrutura_cognitiva": {"dominios": [{"id": "DOM-01"}], "processos": [{"id": PROC}]},
    "qualidade": {"apto_para_camada_de_crenca": {"valor": True}, "revisado": True},
    "distratores": [
        {
            "alternativa": "B",
            "explicacao": "Confunde área com raio.",
            "erros_esperados": [
                {"ordem": 1, "erro": ERRO, "processo_afetado": PROC, "confianca": 0.7},
                {"ordem": 2, "erro": "ERR-04", "processo_afetado": "PROC-QUANT-04", "confianca": 0.4},
            ],
        }
    ],
    "intervencoes": [{"id": "INT-02", "gatilho": {"processo": PROC, "erro": ERRO}, "acao": "Diagrama."}],
    "pedagogia": {"passos": ["Converter unidades."]},
}


class _DocAluno:
    def __init__(self):
        self.dados = {}
        self.leituras = 0
        self.escritas = 0

    def get(self):
        self.leituras += 1
        ref = self

        class _S:
            exists = True

            def to_dict(self):
                return dict(ref.dados)

        return _S()

    def set(self, payload, merge=False):
        self.escritas += 1
        self.dados.update(payload)


@pytest.fixture
def ambiente(monkeypatch, fake_db):
    revisao_service.esquecer()
    microdiagnostico.esquecer()
    microdiagnostico.set_db(fake_db)
    monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)

    _run(fake_db.questoes_public.insert_one({
        "item_id": "I-1",
        "master_id": "M-1",
        "ontology_version": "1.4.1",
        "item_hash": "h-1",
        "item_schema_version": "2.2",
        "questao": {"alternativas": [{"letra": "A", "correta": True}, {"letra": "B", "correta": False}]},
    }))
    _run(fake_db.questoes_master.insert_one({"id": "M-1", "item": ITEM_ANOTADO}))
    fr.set_db(fake_db)

    doc = _DocAluno()
    monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: doc)
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: False)

    eventos = []

    def _escrever(uid, **kw):
        ev = {
            "event_id": f"e{len(eventos) + 1}",
            "item_id": kw["item_id"],
            "ontology_version": kw["ontology_version"],
            "status": "respondida",
            "timestamp": f"2026-09-{len(eventos) + 1:02d}T10:00:00+00:00",
            "resposta": {"alternativa_escolhida": kw["alternativa_escolhida"], "acertou": kw["acertou"]},
        }
        eventos.append(ev)
        return ev

    monkeypatch.setattr(fs, "write_behavior_event", _escrever)
    return {"doc": doc, "eventos": eventos, "db": fake_db}


def _responder(alternativa="B"):
    return _run(fr.register_answer(fr.AnswerPayload(item_id="I-1", alternativa_escolhida=alternativa), ALUNO))


def _bloco(ambiente):
    return ambiente["doc"].dados.get("revisao") or {}


# ============================================ a fiação


class TestRespostaAlimentaOCiclo:
    def test_erro_registra_raiz_e_agenda_reteste(self, ambiente):
        r = _responder("B")
        assert r["acertou"] is False
        assert r["causa_raiz"] == {"erro_id": ERRO, "processo_id": PROC}
        entrada = _bloco(ambiente)["processos"][PROC]
        assert entrada["proximo_reteste"] is not None
        assert [x["erro"] for x in entrada["raizes_recentes"]] == [ERRO]

    def test_manifestacao_nao_ganha_agendamento(self, ambiente):
        """`PROC-QUANT-04` é a ordem 2 da cadeia. Ele nem sequer entra no
        bloco: não é processo do item, e manifestação não agenda (§1.1)."""
        _responder("B")
        assert "PROC-QUANT-04" not in _bloco(ambiente)["processos"]

    def test_acerto_alimenta_a_janela_sem_criar_raiz(self, ambiente):
        r = _responder("A")
        assert r["acertou"] is True and r["causa_raiz"] is None
        entrada = _bloco(ambiente)["processos"][PROC]
        assert entrada["janela_atual"] == {"respondidas": 1, "acertos": 1, "inicio": entrada["janela_atual"]["inicio"]}
        assert entrada["raizes_recentes"] == []
        assert entrada["proximo_reteste"] is None

    def test_o_evento_e_o_dado_que_importa_e_nunca_se_perde(self, ambiente, monkeypatch):
        """Estado de revisão quebrado atrasa um reteste; nunca derruba a
        resposta do aluno."""
        def _explode(*a, **k):
            raise RuntimeError("429 Quota exceeded")

        monkeypatch.setattr(revisao_service, "registrar_resposta", _explode)
        r = _responder("B")
        assert r["acertou"] is False and r["event_id"] == "e1"
        assert r["professor_invisivel"] is None
        assert len(ambiente["eventos"]) == 1


class TestProfessorInvisivel:
    def test_uma_raiz_nao_interrompe(self, ambiente):
        assert _responder("B")["professor_invisivel"] is None

    def test_recorrencia_em_dias_distintos_interrompe_com_a_intervencao_catalogada(self, ambiente):
        _responder("B")
        r = _responder("B")  # o dublê avança o dia a cada evento
        g = r["professor_invisivel"]
        assert g is not None
        assert g["motivo"] == rev.GATILHO_RECORRENCIA
        assert g["erro_id"] == ERRO and g["processo_id"] == PROC
        # A intervenção vem do CATÁLOGO (ERR-03 -> INT-02), não de semelhança
        # de tema, e o texto é local — nenhuma chamada de modelo.
        assert g["intervencao"]["intervencao_id"] == "INT-02"
        assert g["intervencao"]["como_praticar"]
        assert g["processo_nome"] and g["erro_nome"]

    def test_nao_reinterrompe_no_cooldown(self, ambiente):
        _responder("B")
        assert _responder("B")["professor_invisivel"] is not None
        assert _responder("B")["professor_invisivel"] is None
        assert _responder("B")["professor_invisivel"] is None

    def test_vaga_unica_e_liberada_ao_dispensar(self, ambiente):
        _responder("B")
        _responder("B")
        assert PROC in _bloco(ambiente)["intervencoes_ativas"]
        revisao_service.dispensar_intervencao("U1", processo_id=PROC, dispensada=True)
        assert PROC not in _bloco(ambiente)["intervencoes_ativas"]
        assert _bloco(ambiente)["processos"][PROC]["dispensas"] == 1


class TestMicrodiagnostico:
    def test_erro_com_cadeia_recebe_a_micropergunta(self, ambiente):
        m = _responder("B")["microdiagnostico"]
        assert m["event_id"] == "e1"
        assert m["par"] == f"{ERRO}|{PROC}"
        assert len(m["opcoes"]) == 5

    def test_acerto_nao_recebe(self, ambiente):
        assert _responder("A")["microdiagnostico"] is None

    def test_pular_e_indistinguivel_de_nao_ter_recebido(self, ambiente):
        """A tela simplesmente não chama a rota. Nada é gravado, e o estado do
        aluno é idêntico ao de quem não viu a pergunta."""
        _responder("B")
        antes = dict(_bloco(ambiente))
        assert _run(ambiente["db"].autorrelato_pares.find_one({})) is None
        assert _bloco(ambiente) == antes


class TestPortaoNoCaminhoDaResposta:
    def test_item_nao_revisado_nao_move_o_estado_com_o_portao_ligado(self, ambiente, monkeypatch):
        """§6 / EXT-WP1-1.0 L13b: anotação não revisada não vira crença — e
        agendar um reteste É mover o estado do aluno."""
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)
        _run(ambiente["db"].questoes_master.update_one(
            {"id": "M-1"},
            {"$set": {"item": {**ITEM_ANOTADO, "qualidade": {"apto_para_camada_de_crenca": {"valor": False}}}}},
        ))
        _responder("B")
        entrada = _bloco(ambiente)["processos"][PROC]
        assert entrada["raizes_recentes"] == []
        assert entrada["proximo_reteste"] is None
        # A resposta continua contando como desempenho medido: acerto e erro
        # não dependem de revisão de anotação para serem verdade.
        assert entrada["janela_atual"]["respondidas"] == 1

    def test_portao_desligado_deixa_entrar_marcado_como_provisorio(self, ambiente, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_DESLIGADO, raising=False)
        _run(ambiente["db"].questoes_master.update_one(
            {"id": "M-1"},
            {"$set": {"item": {**ITEM_ANOTADO, "qualidade": {"apto_para_camada_de_crenca": {"valor": False}}}}},
        ))
        _responder("B")
        entrada = _bloco(ambiente)["processos"][PROC]
        assert len(entrada["raizes_recentes"]) == 1
        assert entrada["raizes_recentes"][0]["provisorio"] is True
        assert entrada["provisorio"] is True


class TestFilaDepoisDoCiclo:
    def test_a_fila_do_dia_reflete_o_que_o_aluno_acabou_de_fazer(self, ambiente, monkeypatch):
        import annotation_service

        monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: {})
        _responder("B")
        _responder("B")
        revisao_service.esquecer()
        fila = revisao_service.fila("U1")
        assert fila["itens"][0]["processo_id"] == PROC
        assert fila["itens"][0]["estado"] == rev.ESTADO_RECORRENTE
        assert fila["resumo"]["erros_recorrentes"] == 1
        assert fila["itens"][0]["intervencao"]["intervencao_id"] == "INT-02"

    def test_transferencia_some_quando_o_acervo_nao_tem(self, ambiente, monkeypatch):
        """Nunca degrada para "mais um item igual" — a linha simplesmente não
        aparece."""
        import annotation_service

        monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: {"I-1": ITEM_ANOTADO})
        _responder("B")
        revisao_service.esquecer()
        fila = revisao_service.fila("U1")
        assert fila["itens"][0]["transferencia"] is None
        assert fila["resumo"]["transferencias"] == 0

    def test_transferencia_aparece_quando_ha_item_de_outro_contexto(self, ambiente, monkeypatch):
        import annotation_service

        # Mesmo processo, OUTRA disciplina — que é o que caracteriza
        # transferência. Variar o domínio não bastaria: ele é derivado do
        # processo (Constituição §4.4) e por isso quase não varia dentro dele.
        outro = {
            **ITEM_ANOTADO,
            "item_id": "I-9",
            "item_hash": "h-9",
            "fonte": {**ITEM_ANOTADO["fonte"], "disciplina": "Biologia"},
        }
        monkeypatch.setattr(
            annotation_service, "_build_item_index", lambda force=False: {"I-1": ITEM_ANOTADO, "I-9": outro}
        )
        _responder("B")
        revisao_service.esquecer()
        fila = revisao_service.fila("U1")
        assert fila["itens"][0]["transferencia"]["item_id"] == "I-9"
        assert fila["itens"][0]["transferencia"]["contexto"] == "disciplina:Biologia"


class TestTrajetoriaNaoAlega:
    def test_com_perfil_provisorio_a_tela_nao_afirma_nexo_causal(self, ambiente, monkeypatch):
        """A restrição mais delicada da proposta: descrever, não alegar."""
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_DESLIGADO, raising=False)
        _responder("B")
        revisao_service.esquecer()
        t = revisao_service.trajetoria("U1")
        assert t["nexo_causal"] is False
        assert t["aviso"] and "não afirma que uma coisa causou a outra" in t["aviso"]

    def test_com_o_portao_em_crenca_e_corpus_revisado_o_nexo_e_permitido(self, ambiente):
        _responder("B")
        revisao_service.esquecer()
        t = revisao_service.trajetoria("U1")
        assert t["nexo_causal"] is True
        assert t["aviso"] is None
        assert t["habilidades"][0]["processo_id"] == PROC


# ============================================ os não-objetivos (§9)


class TestNaoObjetivos:
    """A lista do §9 da proposta, virada em teste. Cada item aqui é uma coisa
    que a próxima refatoração pode reintroduzir sem que nada quebre visivelmente
    — que é exatamente por que ela precisa de um teste e não de um comentário.
    """

    MODULOS = (
        "revisao_espacada.py",
        "revisao_service.py",
        "revisao_routes.py",
        "microdiagnostico.py",
        "curadoria.py",
        "sapiens_lab.py",
        "curadoria_routes.py",
    )

    def _fonte(self, nome):
        return (BACKEND / nome).read_text(encoding="utf-8")

    def _codigo(self, nome):
        """A fonte sem docstrings nem comentários — o que de fato executa."""
        import ast

        arvore = ast.parse(self._fonte(nome))
        for no in ast.walk(arvore):
            if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(no)
                if doc and no.body and isinstance(no.body[0], ast.Expr):
                    no.body.pop(0)
        return ast.unparse(arvore)

    @pytest.mark.parametrize("nome", ["revisao_espacada.py", "revisao_service.py", "curadoria.py", "sapiens_lab.py"])
    def test_nenhuma_fase_introduz_llm(self, nome):
        """As Fases 1, 2 e 4 são gratuitas porque não geram conteúdo. Uma fase
        que precise cobrar Spark está gerando onde deveria estar medindo."""
        codigo = self._codigo(nome)
        for proibido in ("ai_service", "gemini", "deduct_sparks", "INTERVENCAO_COST"):
            assert proibido not in codigo, f"{nome} introduziu {proibido}"

    @pytest.mark.parametrize("nome", MODULOS)
    def test_mecanismo_nunca_escolhe_nem_aparece(self, nome):
        """Error Trace §4.2: `MEC-*` não seleciona intervenção e não é exibido.
        Ele existe no traço e para por ali."""
        codigo = self._codigo(nome)
        assert "MEC-" not in codigo, f"{nome} cita um mecanismo do catálogo"
        assert "mecanismo" not in codigo, f"{nome} usa mecanismo em código"

    def test_nada_altera_a_ontologia(self):
        """R-7. O único write legítimo de todo o conjunto é o campo
        `qualidade` de um ITEM, feito por uma pessoa em `curadoria`."""
        import ast

        for nome in self.MODULOS:
            arvore = ast.parse(self._fonte(nome))
            importados = {
                alias.name.split(".")[0]
                for no in ast.walk(arvore)
                if isinstance(no, ast.Import)
                for alias in no.names
            } | {
                (no.module or "").split(".")[0]
                for no in ast.walk(arvore)
                if isinstance(no, ast.ImportFrom)
            }
            if nome != "curadoria.py":
                assert "canonical_ontology" not in importados, f"{nome} alcança o catálogo"

    def test_o_snapshot_antigo_continua_existindo(self):
        """`/plan/:analysisId` está no histórico de todo aluno que já fez uma
        prova. A fila nova não o substitui — convive com ele."""
        app_js = (BACKEND.parent / "frontend" / "src" / "App.js").read_text(encoding="utf-8")
        assert '<Route path="/plan/:analysisId"' in app_js
        assert '<Route path="/revisoes"' in app_js

    def test_o_motor_e_as_intervencoes_nao_foram_reescritos(self):
        """A proposta é explícita: estender, nunca reescrever. Se estes nomes
        sumirem, alguém reimplementou o que já existia."""
        import motor_cognitivo
        import intervencoes
        import portao_crenca

        for alvo, nomes in (
            (motor_cognitivo, ("produzir_traco", "_priorizar", "_validar_cadeia", "perfil", "detalhe")),
            (intervencoes, ("montar", "previa", "sugerir_pratica")),
            (portao_crenca, ("apto", "pode_alimentar_crenca", "modo")),
        ):
            for nome in nomes:
                assert hasattr(alvo, nome), f"{alvo.__name__}.{nome} desapareceu"


# ============================================ §9 — os não-objetivos


# Os sete módulos que o ciclo adaptativo acrescentou. A lista é explícita para
# que um módulo novo tenha de ser adicionado aqui conscientemente — e passe a
# responder pelas mesmas restrições.
MODULOS_NOVOS = (
    "revisao_espacada.py",
    "revisao_service.py",
    "revisao_routes.py",
    "microdiagnostico.py",
    "curadoria.py",
    "curadoria_routes.py",
    "sapiens_lab.py",
)


def _codigo_sem_docstring(nome: str) -> str:
    """O código do módulo com docstrings e comentários fora.

    Necessário porque as docstrings destes módulos CITAM as regras que eles
    prometem não violar ("nunca usa MEC-*", "nunca chama LLM"). Uma varredura
    de texto cru acusaria a própria explicação da regra como se fosse a
    violação dela.
    """
    import ast, io, tokenize

    arvore = ast.parse((BACKEND / nome).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            corpo = getattr(no, "body", None)
            if corpo and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Constant) \
               and isinstance(corpo[0].value.value, str):
                corpo.pop(0)
    sem_docstring = ast.unparse(arvore)
    # `ast.unparse` já descarta comentários; o `tokenize` abaixo é só a prova
    # de que o resultado é código válido e não texto.
    list(tokenize.generate_tokens(io.StringIO(sem_docstring).readline))
    return sem_docstring


class TestNaoObjetivos:
    """§9 da proposta, lido como teste. Cada um destes já foi violado por
    engano em algum produto: a lista existe porque a violação é sempre
    plausível e nunca chamativa."""

    @pytest.mark.parametrize("modulo", MODULOS_NOVOS)
    def test_nenhum_modulo_novo_chama_ia(self, modulo):
        """O motor é gratuito, e continua. Uma fase destas que precisasse de
        LLM estaria gerando conteúdo onde deveria estar medindo."""
        codigo = _codigo_sem_docstring(modulo)
        for proibido in ("ai_service", "genai", "gemini", "GenerativeModel"):
            assert proibido not in codigo, f"{modulo} alcançou IA ({proibido})"

    @pytest.mark.parametrize("modulo", MODULOS_NOVOS)
    def test_nenhum_modulo_novo_cobra_sparks(self, modulo):
        """Medida pedagógica é de graça. O que custa Spark é geração de
        conteúdo (Mentis, mapa cosmético), nunca medir o que o próprio aluno
        produziu respondendo."""
        codigo = _codigo_sem_docstring(modulo)
        for proibido in ("deduct_sparks", "sparks_store", "InsufficientSparks"):
            assert proibido not in codigo, f"{modulo} mexeu em Sparks ({proibido})"

    @pytest.mark.parametrize("modulo", MODULOS_NOVOS)
    def test_mecanismo_nao_escolhe_nem_aparece(self, modulo):
        """Error Trace §4.2: `MEC-*` não seleciona intervenção e não é exibido.
        O mecanismo cognitivo é registro do traço, não critério de decisão."""
        assert "MEC-" not in _codigo_sem_docstring(modulo), f"{modulo} usa MEC-*"

    @pytest.mark.parametrize("modulo", MODULOS_NOVOS)
    def test_nenhum_modulo_novo_escreve_na_ontologia(self, modulo):
        """R-7: padrão observado é insumo para revisão humana sob GOV-1.0
        §11.2, nunca alteração automática do catálogo."""
        import ast

        arvore = ast.parse((BACKEND / modulo).read_text(encoding="utf-8"))
        nomes = {
            no.func.attr for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        } | {
            no.func.id for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
        }
        for proibida in ("write_ontology", "save_ontology", "dump", "open"):
            assert proibida not in nomes, f"{modulo} escreve arquivo ({proibida}())"

    def test_o_motor_e_as_intervencoes_nao_foram_reescritos(self):
        """A proposta é explícita: `motor_cognitivo`, `intervencoes` e
        `portao_crenca` são ESTENDIDOS por fora, nunca reescritos. Se um nome
        público destes sumir, o ciclo passou a depender de uma variante."""
        import intervencoes
        import motor_cognitivo as motor
        import portao_crenca

        for nome in ("produzir_traco", "perfil", "detalhe", "panorama", "_priorizar",
                     "_agregar_erros", "_validar_cadeia", "MIN_TRACOS_RAIZ", "SENTINELAS"):
            assert hasattr(motor, nome), f"motor_cognitivo perdeu {nome}"
        for nome in ("montar", "previa", "sugerir_pratica"):
            assert hasattr(intervencoes, nome), f"intervencoes perdeu {nome}"
        for nome in ("modo", "apto", "pode_alimentar_crenca", "aplicar_a_prova"):
            assert hasattr(portao_crenca, nome), f"portao_crenca perdeu {nome}"

    def test_o_plano_antigo_continua_existindo(self):
        """`/plan/:analysisId` está no histórico de todo aluno que já fez uma
        prova. Histórico não pode quebrar."""
        app_js = (BACKEND.parent / "frontend" / "src" / "App.js").read_text(encoding="utf-8")
        assert '/plan/:analysisId' in app_js
        assert "StudyPlan" in app_js

    def test_a_fila_do_aluno_nao_carrega_id_de_catalogo_no_texto(self):
        """Os IDs viajam como chave (React key, data-testid), nunca como texto
        que o aluno lê. O que ele lê é `processo_nome` e `erro_nome`."""
        import revisao_service

        for campo in ("rotulo", "processo_nome", "erro_nome"):
            assert campo in (BACKEND / "revisao_service.py").read_text(encoding="utf-8")
        rotulos = set(revisao_service._ROTULO_ESTADO.values()) | set(revisao_service._MARCO_TEXTO.values())
        for texto in rotulos:
            assert not any(p in texto for p in ("ERR-", "PROC-", "MEC-", "INT-")), texto
