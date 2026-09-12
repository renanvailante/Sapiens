"""Custo de leitura do Firestore — os testes que guardam a conta.

Escritos depois do incidente de 2026-09-04: a cota diária do projeto (50.000
leituras) foi esgotada por um laço de background, e TODA rota autenticada
passou a responder erro, porque quase todas leem o perfil do aluno.

O que se protege aqui não é comportamento de produto — é a ORDEM DE GRANDEZA
do número de leituras. Cada teste abaixo existe porque a versão anterior do
código lia O(eventos) ou O(5000) onde bastava O(1) ou O(alunos), e nenhuma
dessas regressões produziria erro visível: só uma conta no fim do mês e um
apagão no fim da tarde.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service as asvc  # noqa: E402
import firestore_service as fs  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


# ============================================ cache do agregado derivado


class TestCacheDerivado:
    """`annotation_service._agregado_com_cache`: 1 leitura no lugar de N."""

    def _instalar(self, monkeypatch, fake_db, total_respostas=12):
        leituras = {"firestore": 0, "agregado": 0}

        def _ler_agregado(uid):
            leituras["agregado"] += 1
            return {"total_respostas": total_respostas}

        def _caro(uid):
            leituras["firestore"] += 1
            return {"processo_stats": {"PROC-1": {"respondidas": 9, "acertos": 2}}}

        monkeypatch.setattr(fs, "ler_agregado", _ler_agregado)
        monkeypatch.setattr(asvc, "_db", fake_db)
        return leituras, _caro

    def test_segunda_chamada_nao_toca_no_historico(self, monkeypatch, fake_db):
        leituras, caro = self._instalar(monkeypatch, fake_db)
        a = _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        b = _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        assert a == b
        assert leituras["firestore"] == 1, "o histórico completo foi relido — o cache não pegou"

    def test_resposta_nova_do_aluno_invalida(self, monkeypatch, fake_db):
        """`total_respostas` é a chave: respondeu algo novo, recalcula."""
        leituras, caro = self._instalar(monkeypatch, fake_db, total_respostas=12)
        _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        monkeypatch.setattr(fs, "ler_agregado", lambda uid: {"total_respostas": 13})
        _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        assert leituras["firestore"] == 2

    def test_escopos_diferentes_nao_se_misturam(self, monkeypatch, fake_db):
        leituras, caro = self._instalar(monkeypatch, fake_db)
        _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        _run(asvc._agregado_com_cache("answered", "U1", caro))
        assert leituras["firestore"] == 2

    def test_alunos_diferentes_nao_se_misturam(self, monkeypatch, fake_db):
        leituras, caro = self._instalar(monkeypatch, fake_db)
        a = _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        monkeypatch.setattr(asvc, "_db", fake_db)
        b = _run(asvc._agregado_com_cache("desempenho", "U2", caro))
        assert leituras["firestore"] == 2 and a == b

    def test_cache_expirado_recalcula(self, monkeypatch, fake_db):
        leituras, caro = self._instalar(monkeypatch, fake_db)
        _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        for doc in fake_db.perfil_derivado_cache.docs:
            doc["expira_em"] = "2000-01-01T00:00:00+00:00"
        _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        assert leituras["firestore"] == 2

    def test_sem_mongo_o_cache_some_e_nada_quebra(self, monkeypatch, fake_db):
        """Cache é otimização de custo, nunca dependência para o resultado."""
        leituras, caro = self._instalar(monkeypatch, fake_db)
        monkeypatch.setattr(asvc, "_db", None)
        out = _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        assert out["processo_stats"]["PROC-1"]["respondidas"] == 9
        assert leituras["firestore"] == 1

    def test_agregado_indisponivel_cai_para_leitura_direta(self, monkeypatch, fake_db):
        leituras, caro = self._instalar(monkeypatch, fake_db)

        def _estourou(uid):
            raise RuntimeError("429 Quota exceeded")

        monkeypatch.setattr(fs, "ler_agregado", _estourou)
        out = _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        assert out is not None and leituras["firestore"] == 1

    def test_falha_do_mongo_nao_impede_a_resposta(self, monkeypatch, fake_db):
        leituras, caro = self._instalar(monkeypatch, fake_db)

        class _MongoQuebrado:
            @property
            def perfil_derivado_cache(self):
                raise RuntimeError("mongo fora do ar")

        monkeypatch.setattr(asvc, "_db", _MongoQuebrado())
        out = _run(asvc._agregado_com_cache("desempenho", "U1", caro))
        assert out is not None and leituras["firestore"] == 1


# ============================================ listagem de alunos


class _Snap:
    def __init__(self, sid, dados):
        self.id = sid
        self._d = dados

    def to_dict(self):
        return self._d


class _ColecaoFalsa:
    def __init__(self, snaps, contador):
        self._snaps = snaps
        self._contador = contador

    def stream(self):
        for s in self._snaps:
            self._contador["lidos"] += 1
            yield s


class _ClienteFalso:
    def __init__(self, snaps, contador):
        self._snaps = snaps
        self._contador = contador

    def collection(self, nome):
        assert nome == "students", f"leu a coleção {nome!r} — o caminho barato é 'students'"
        return _ColecaoFalsa(self._snaps, self._contador)


class TestListagemDeAlunos:
    """`list_students_with_behavior` lia `collection_group('behavior').limit(5000)`."""

    def _montar(self, monkeypatch, snaps):
        contador = {"lidos": 0}
        monkeypatch.setattr(fs, "get_firestore", lambda: _ClienteFalso(snaps, contador))
        return contador

    def test_custa_uma_leitura_por_aluno_e_nao_por_evento(self, monkeypatch):
        snaps = [
            _Snap(f"U{i}", {"agregado": {"total_respostas": 300, "atualizado_em": f"2026-09-0{i}"}})
            for i in range(1, 6)
        ]
        contador = self._montar(monkeypatch, snaps)
        linhas = fs.list_students_with_behavior()
        assert len(linhas) == 5
        # 5 alunos x 300 respostas = 1.500 eventos; o custo tem de ser 5, não 1.500
        assert contador["lidos"] == 5

    def test_ordena_do_mais_recente_para_o_mais_antigo(self, monkeypatch):
        snaps = [
            _Snap("antigo", {"agregado": {"total_respostas": 4, "atualizado_em": "2026-01-01"}}),
            _Snap("novo", {"agregado": {"total_respostas": 2, "atualizado_em": "2026-09-01"}}),
        ]
        self._montar(monkeypatch, snaps)
        assert [l["student_id"] for l in fs.list_students_with_behavior()] == ["novo", "antigo"]

    def test_aluno_sem_resposta_fica_de_fora(self, monkeypatch):
        snaps = [
            _Snap("zerado", {"agregado": {"total_respostas": 0}}),
            _Snap("ativo", {"agregado": {"total_respostas": 3, "atualizado_em": "2026-09-01"}}),
        ]
        self._montar(monkeypatch, snaps)
        assert [l["student_id"] for l in fs.list_students_with_behavior()] == ["ativo"]

    def test_aluno_sem_agregado_e_reconstruido_uma_vez(self, monkeypatch):
        """Aluno anterior ao agregado não pode sumir da lista — sumir significa
        parar de receber perfil cognitivo, em silêncio."""
        snaps = [_Snap("legado", {})]
        self._montar(monkeypatch, snaps)
        chamadas = []

        def _reconstruir(uid):
            chamadas.append(uid)
            return {"total_respostas": 7, "atualizado_em": "2026-09-02"}

        monkeypatch.setattr(fs, "reconstruir_agregado", _reconstruir)
        linhas = fs.list_students_with_behavior()
        assert chamadas == ["legado"]
        assert linhas == [{"student_id": "legado", "nome": None, "email": None, "count": 7, "last_at": "2026-09-02"}]

    def test_falha_ao_reconstruir_nao_derruba_a_listagem_inteira(self, monkeypatch):
        snaps = [
            _Snap("quebrado", {}),
            _Snap("ok", {"agregado": {"total_respostas": 5, "atualizado_em": "2026-09-01"}}),
        ]
        self._montar(monkeypatch, snaps)

        def _falha(uid):
            raise RuntimeError("Firestore fora do ar")

        monkeypatch.setattr(fs, "reconstruir_agregado", _falha)
        assert [l["student_id"] for l in fs.list_students_with_behavior()] == ["ok"]

    def test_nao_trunca_em_5000(self, monkeypatch):
        """O `limit(5000)` antigo fazia alunos sumirem em silêncio quando a
        plataforma passasse de 5.000 eventos somados."""
        snaps = [
            _Snap(f"U{i:04d}", {"agregado": {"total_respostas": 9000, "atualizado_em": "2026-09-01"}})
            for i in range(120)
        ]
        self._montar(monkeypatch, snaps)
        assert len(fs.list_students_with_behavior(limit=500)) == 120


# ============================================ provisionamento


class _RefFalsa:
    def __init__(self, existe, contador):
        self._existe = existe
        self._contador = contador

    def get(self):
        self._contador["leituras"] += 1
        ref = self

        class _S:
            exists = ref._existe

            def to_dict(self):
                return {}

        return _S()

    def set(self, *a, **k):
        self._existe = True


class TestProvisionamento:
    """`ensure_student_profile` estava no caminho de quase toda rota
    autenticada e custava 1 leitura por REQUISIÇÃO para responder algo que
    nunca muda: o documento existe."""

    def test_so_le_o_firestore_na_primeira_vez(self, monkeypatch):
        contador = {"leituras": 0}
        fs.esquecer_provisionamento("U1")
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: _RefFalsa(True, contador))
        for _ in range(5):
            fs.ensure_student_profile("U1", "Ana", "a@x.com")
        assert contador["leituras"] == 1

    def test_cria_quando_nao_existe_e_depois_nao_relê(self, monkeypatch):
        contador = {"leituras": 0}
        fs.esquecer_provisionamento("U2")
        ref = _RefFalsa(False, contador)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: ref)
        assert fs.ensure_student_profile("U2", "Ana", "a@x.com") is True
        assert fs.ensure_student_profile("U2", "Ana", "a@x.com") is False
        assert contador["leituras"] == 1

    def test_alunos_diferentes_nao_compartilham_a_memoria(self, monkeypatch):
        contador = {"leituras": 0}
        for uid in ("U3", "U4"):
            fs.esquecer_provisionamento(uid)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: _RefFalsa(True, contador))
        fs.ensure_student_profile("U3")
        fs.ensure_student_profile("U4")
        assert contador["leituras"] == 2

    def test_esquecer_forca_nova_verificacao(self, monkeypatch):
        contador = {"leituras": 0}
        fs.esquecer_provisionamento("U5")
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: _RefFalsa(True, contador))
        fs.ensure_student_profile("U5")
        fs.esquecer_provisionamento("U5")
        fs.ensure_student_profile("U5")
        assert contador["leituras"] == 2


# ============================================ motor cognitivo


class _ColecaoEventos:
    def __init__(self, eventos, contador):
        self._eventos = eventos
        self._contador = contador

    def stream(self):
        for e in self._eventos:
            self._contador["eventos_lidos"] += 1
            yield e


class _DocRef:
    def __init__(self, eventos, contador):
        self._eventos = eventos
        self._contador = contador

    def collection(self, nome):
        return _ColecaoEventos(self._eventos, self._contador)


class _ClienteEventos:
    def __init__(self, eventos, contador):
        self._eventos = eventos
        self._contador = contador

    def collection(self, nome):
        return self

    def document(self, uid):
        return _DocRef(self._eventos, self._contador)


class TestMemoriaDoMotor:
    """`motor_cognitivo._ler_historico` varre o histórico inteiro do aluno.

    Três multiplicadores reais tornavam isso perigoso: `detalhe()` roda logo
    depois de `perfil()` na mesma navegação; `/motor/panorama` chama `perfil()`
    para até 200 alunos numa requisição; e recarregar a página paga tudo de
    novo. Sem memória, o panorama sozinho passava da cota diária inteira.
    """

    def _montar(self, monkeypatch, n_eventos=40, total_respostas=40):
        import annotation_service
        import motor_cognitivo as motor

        motor.esquecer_historico()
        contador = {"eventos_lidos": 0, "agregados_lidos": 0}
        eventos = [_Snap(f"e{i}", {"status": "respondida", "item_id": "X"}) for i in range(n_eventos)]

        def _agregado(uid):
            contador["agregados_lidos"] += 1
            return {"total_respostas": total_respostas}

        monkeypatch.setattr(fs, "ler_agregado", _agregado)
        monkeypatch.setattr(fs, "get_firestore", lambda: _ClienteEventos(eventos, contador))
        monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: {})
        return motor, contador

    def test_segunda_leitura_nao_varre_o_historico_de_novo(self, monkeypatch):
        motor, contador = self._montar(monkeypatch, n_eventos=40)
        motor._ler_historico("U1")
        motor._ler_historico("U1")
        assert contador["eventos_lidos"] == 40, "o histórico foi varrido duas vezes"
        assert contador["agregados_lidos"] == 2, "a chave custa 1 leitura, e só"

    def test_panorama_de_muitos_alunos_nao_multiplica(self, monkeypatch):
        """O caso que estourava a cota num clique."""
        motor, contador = self._montar(monkeypatch, n_eventos=300)
        for _ in range(50):  # 50 visitas ao mesmo aluno, como o panorama repetido
            motor._ler_historico("U1")
        assert contador["eventos_lidos"] == 300  # e não 15.000

    def test_resposta_nova_invalida_a_memoria(self, monkeypatch):
        import annotation_service
        import motor_cognitivo as motor

        motor.esquecer_historico()
        contador = {"eventos_lidos": 0}
        eventos = [_Snap(f"e{i}", {"status": "respondida"}) for i in range(10)]
        contagens = iter([10, 10, 11])
        monkeypatch.setattr(fs, "ler_agregado", lambda uid: {"total_respostas": next(contagens)})
        monkeypatch.setattr(fs, "get_firestore", lambda: _ClienteEventos(eventos, contador))
        monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: {})

        motor._ler_historico("U1")
        motor._ler_historico("U1")   # mesma contagem -> memória
        motor._ler_historico("U1")   # contagem subiu -> relê
        assert contador["eventos_lidos"] == 20

    def test_sem_agregado_nunca_serve_memoria_velha(self, monkeypatch):
        """Sem chave de invalidação confiável, releitura é o comportamento
        correto: caro, porém nunca errado."""
        import annotation_service
        import motor_cognitivo as motor

        motor.esquecer_historico()
        contador = {"eventos_lidos": 0}
        eventos = [_Snap(f"e{i}", {"status": "respondida"}) for i in range(10)]

        def _quebrado(uid):
            raise RuntimeError("429 Quota exceeded")

        monkeypatch.setattr(fs, "ler_agregado", _quebrado)
        monkeypatch.setattr(fs, "get_firestore", lambda: _ClienteEventos(eventos, contador))
        monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: {})

        motor._ler_historico("U1")
        motor._ler_historico("U1")
        assert contador["eventos_lidos"] == 20

    def test_alunos_diferentes_nao_compartilham_historico(self, monkeypatch):
        motor, contador = self._montar(monkeypatch, n_eventos=10)
        a = motor._ler_historico("U1")
        b = motor._ler_historico("U2")
        assert contador["eventos_lidos"] == 20
        assert a is not b

    def test_memoria_tem_teto_e_nao_cresce_sem_fim(self, monkeypatch):
        motor, _ = self._montar(monkeypatch, n_eventos=1)
        for i in range(motor._HISTORICO_MEMO_MAX + 10):
            motor._ler_historico(f"U{i}")
        assert len(motor._HISTORICO_MEMO) <= motor._HISTORICO_MEMO_MAX


# ============================================ revisão espaçada (Fases 1/2/4)


class _DocRevisao:
    """Dublê de `students/{uid}`: conta leituras e escritas separadamente."""

    def __init__(self, contador, dados=None):
        self._c = contador
        self._d = dados or {}

    def get(self):
        self._c["leituras"] += 1
        ref = self

        class _S:
            exists = True

            def to_dict(self):
                return dict(ref._d)

        return _S()

    def set(self, payload, merge=False):
        self._c["escritas"] += 1
        for k, v in payload.items():
            self._d[k] = v


class TestCustoDaRevisao:
    """A Fase 1 acrescenta estado ao aluno; o teto de custo é o que a torna
    aceitável. O incidente de 2026-09-04 foi exatamente uma feature nova lendo
    O(eventos) sem que ninguém percebesse até a cota acabar.
    """

    def _montar(self, monkeypatch, dados=None):
        import revisao_service

        revisao_service.esquecer()
        contador = {"leituras": 0, "escritas": 0}
        ref = _DocRevisao(contador, dados)
        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: ref)
        return revisao_service, contador, ref

    def _item(self):
        return {
            "item_id": "I-1",
            "item_hash": "h-1",
            "fonte": {"banca": "ENEM", "ano": 2023, "prova": "AMARELO", "numero": 93, "disciplina": "Física"},
            "estrutura_cognitiva": {
                "dominios": [{"id": "DOM-01"}],
                "processos": [{"id": "PROC-SIMB-01"}],
            },
            "qualidade": {"apto_para_camada_de_crenca": {"valor": True}, "revisado": True},
            "distratores": [
                {
                    "alternativa": "B",
                    "erros_esperados": [
                        {"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": 0.7}
                    ],
                }
            ],
        }

    def _evento(self, n=1, acertou=False):
        return {
            "event_id": f"e{n}",
            "item_id": "I-1",
            "ontology_version": "1.4.1",
            "status": "respondida",
            "timestamp": f"2026-09-0{(n % 9) + 1}T10:00:00+00:00",
            "resposta": {"alternativa_escolhida": "B", "acertou": acertou},
        }

    def test_uma_resposta_custa_uma_leitura_e_uma_escrita(self, monkeypatch):
        svc, contador, _ = self._montar(monkeypatch)
        svc.registrar_resposta("U1", item=self._item(), evento=self._evento())
        assert contador["leituras"] == 1
        assert contador["escritas"] == 1

    def test_sessao_de_prova_inteira_custa_uma_leitura_so(self, monkeypatch):
        """20 questões seguidas é o caso real. Sem a memória do escritor, seriam
        20 leituras — e cem alunos fazendo isso é a cota diária inteira."""
        svc, contador, _ = self._montar(monkeypatch)
        for i in range(20):
            svc.registrar_resposta("U1", item=self._item(), evento=self._evento(i))
        assert contador["leituras"] == 1, "releu o estado a cada resposta"
        assert contador["escritas"] == 20

    def test_o_gatilho_nao_custa_leitura_adicional(self, monkeypatch):
        """Critério de aceite da Fase 2: avaliar o gatilho custa 0 leituras
        adicionais no caminho de `register_answer`. Ele roda sobre o bloco que
        a atualização acabou de produzir."""
        svc, com, _ = self._montar(monkeypatch)
        for i in range(6):
            svc.registrar_resposta("U1", item=self._item(), evento=self._evento(i), avaliar_gatilho=True)
        leituras_com = com["leituras"]

        svc, sem, _ = self._montar(monkeypatch)
        for i in range(6):
            svc.registrar_resposta("U2", item=self._item(), evento=self._evento(i), avaliar_gatilho=False)
        assert leituras_com == sem["leituras"]

    def test_custo_nao_cresce_com_o_historico_do_aluno(self, monkeypatch):
        """O bloco já cheio custa o mesmo que o bloco vazio: é um documento,
        não uma varredura."""
        import revisao_espacada as rev

        gordo = None
        for i in range(60):
            gordo = rev.registrar(
                gordo,
                processos=["PROC-SIMB-01"],
                acertou=False,
                dia=f"2026-09-{(i % 28) + 1:02d}",
                quando=f"2026-09-{(i % 28) + 1:02d}T10:00:00+00:00",
                raiz={"erro": "ERR-03", "processo": "PROC-SIMB-01", "confianca": 0.7},
            )
        svc, contador, _ = self._montar(monkeypatch, {"revisao": gordo})
        svc.registrar_resposta("U1", item=self._item(), evento=self._evento())
        assert contador["leituras"] == 1

    def test_fila_diaria_custa_uma_leitura(self, monkeypatch):
        """O critério de aceite da Fase 1, literal: montar a fila custa 1
        leitura, independente do número de eventos do aluno."""
        import annotation_service
        import revisao_espacada as rev

        bloco = rev.registrar(
            None,
            processos=["PROC-SIMB-01"],
            acertou=False,
            dia="2026-09-01",
            quando="2026-09-01T10:00:00+00:00",
            raiz={"erro": "ERR-03", "processo": "PROC-SIMB-01", "confianca": 0.7},
            contexto="DOM-01",
        )
        svc, contador, _ = self._montar(
            monkeypatch, {"revisao": bloco, "agregado": {"item_ids_respondidos": ["I-1"]}}
        )
        monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: {})
        resultado = svc.fila("U1")
        assert contador["leituras"] == 1
        assert contador["escritas"] == 0
        assert [i["processo_id"] for i in resultado["itens"]] == ["PROC-SIMB-01"]

    def test_trajetoria_custa_uma_leitura(self, monkeypatch):
        import revisao_espacada as rev

        bloco = rev.registrar(
            None,
            processos=["PROC-SIMB-01"],
            acertou=False,
            dia="2026-09-01",
            quando="2026-09-01T10:00:00+00:00",
            raiz={"erro": "ERR-03", "processo": "PROC-SIMB-01", "confianca": 0.7},
        )
        svc, contador, _ = self._montar(monkeypatch, {"revisao": bloco})
        svc.esquecer()
        assert svc.trajetoria("U1")["habilidades"]
        assert contador["leituras"] == 1

    def test_falha_de_leitura_nao_derruba_a_resposta_do_aluno(self, monkeypatch):
        """O evento de behavior já foi gravado quando chegamos aqui. Um estado
        de revisão que não pôde ser lido atrasa um reteste; nunca perde uma
        resposta."""
        import revisao_service

        revisao_service.esquecer()

        class _Quebrado:
            def get(self):
                raise RuntimeError("429 Quota exceeded")

            def set(self, *a, **k):
                raise RuntimeError("429 Quota exceeded")

        monkeypatch.setattr(fs, "_student_doc_ref", lambda uid: _Quebrado())
        assert revisao_service.registrar_resposta("U1", item=self._item(), evento=self._evento()) == {
            "gatilho": None
        }
