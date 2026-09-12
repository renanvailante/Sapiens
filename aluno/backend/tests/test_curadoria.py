"""Fase 0 — destravar a evidência, e a Fase 5 que a alimenta.

A Fase 0 não é funcionalidade: é o pré-requisito das outras. Os três critérios
de aceite dela estão aqui, um por classe:

1. **Revisar um item religa o portão para ele** — e `portao.tracos_no_perfil`
   sobe com `PORTAO_CRENCA_MODO=crenca`. É a única forma legítima de sair do
   perfil provisório em que produção roda desde 2026-09-04.
2. **O relatório de oferta existe e reprova** — processo com acervo raso não
   sustenta reteste, e reteste sobre acervo raso mede memória do item, não
   estabilização da habilidade.
3. **O Lab propõe e nunca altera a ontologia** (R-7).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import annotation_service  # noqa: E402
import curadoria  # noqa: E402
import firestore_service as fs  # noqa: E402
import microdiagnostico  # noqa: E402
import motor_cognitivo as motor  # noqa: E402
import portao_crenca  # noqa: E402
import sapiens_lab  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


CADEIA = [{"ordem": 1, "erro": "ERR-03", "processo_afetado": "PROC-SIMB-01", "confianca": 0.7}]


def _item(item_id="I-1", *, apto=False, revisado=False, dominio="DOM-01", disciplina="Física",
          com_cadeia=True, com_intervencao=True):
    return {
        "item_id": item_id,
        "item_hash": f"h-{item_id}",
        "ontology_version": "1.4.1",
        "fonte": {"banca": "ENEM", "ano": 2023, "prova": "AMARELO", "numero": 93, "disciplina": disciplina},
        "questao": {"enunciado": "Enunciado."},
        "estrutura_cognitiva": {"dominios": [{"id": dominio}], "processos": [{"id": "PROC-SIMB-01"}]},
        "qualidade": {"apto_para_camada_de_crenca": {"valor": apto}, "revisado": revisado},
        "distratores": (
            [{"alternativa": "B", "erros_esperados": CADEIA, "explicacao": "Confunde área com raio."}]
            if com_cadeia
            else []
        ),
        "intervencoes": (
            [{"id": "INT-02", "gatilho": {"processo": "PROC-SIMB-01", "erro": "ERR-03"}, "acao": "Diagrama."}]
            if com_intervencao
            else []
        ),
    }


def _indice(itens):
    mapa = {}
    for it in itens:
        mapa[it["item_id"]] = it
        mapa[it["item_hash"]] = it
    return mapa


class _Doc:
    def __init__(self, doc_id, dados, escritas):
        self.id = doc_id
        self._d = dados
        self._escritas = escritas

    def to_dict(self):
        return self._d

    def set(self, payload, merge=False):
        self._escritas.append((self.id, payload, merge))
        qual = ((payload.get("item") or {}).get("qualidade")) or {}
        self._d.setdefault("item", {}).setdefault("qualidade", {}).update(qual)


class _Colecao:
    def __init__(self, docs, escritas):
        self._docs = docs
        self._escritas = escritas

    def stream(self):
        return iter(self._docs)

    def limit(self, n):
        return self

    def document(self, doc_id):
        for d in self._docs:
            if d.id == doc_id:
                return d
        novo = _Doc(doc_id, {}, self._escritas)
        self._docs.append(novo)
        return novo


class _Cliente:
    def __init__(self, docs, escritas):
        self._docs = docs
        self._escritas = escritas

    def collection(self, nome):
        return _Colecao(self._docs, self._escritas)


@pytest.fixture(autouse=True)
def _limpo():
    curadoria.esquecer()
    motor.esquecer_historico()
    microdiagnostico.set_db(None)
    yield
    curadoria.esquecer()
    motor.esquecer_historico()
    microdiagnostico.set_db(None)


def _instalar(monkeypatch, itens):
    escritas = []
    docs = [_Doc(f"doc-{it['item_id']}", {"item": it}, escritas) for it in itens]
    monkeypatch.setattr(fs, "get_firestore", lambda: _Cliente(docs, escritas))
    monkeypatch.setattr(annotation_service, "_build_item_index", lambda force=False: _indice(itens))
    return escritas, docs


# ============================================ relatório de oferta


class TestRelatorioDeOferta:
    def _linha(self, relatorio, pid="PROC-SIMB-01"):
        return next(l for l in relatorio["processos"] if l["processo_id"] == pid)

    def test_acervo_raso_e_reprovado(self, monkeypatch):
        _instalar(monkeypatch, [_item("I-1")])
        linha = self._linha(curadoria.relatorio_de_oferta())
        assert linha["apto_para_fase_1"] is False
        assert any("item(ns) no acervo" in m for m in linha["motivos"])

    def test_um_contexto_so_nao_sustenta_transferencia(self, monkeypatch):
        itens = [_item(f"I-{i}", disciplina="Física") for i in range(1, 6)]
        _instalar(monkeypatch, itens)
        linha = self._linha(curadoria.relatorio_de_oferta())
        assert linha["apto_para_fase_1"] is False
        assert any("contexto" in m for m in linha["motivos"])

    def test_acervo_suficiente_em_dois_contextos_e_aprovado(self, monkeypatch):
        itens = [_item(f"I-{i}", disciplina="Física" if i < 3 else "Biologia") for i in range(1, 6)]
        _instalar(monkeypatch, itens)
        relatorio = curadoria.relatorio_de_oferta()
        linha = self._linha(relatorio)
        assert linha["apto_para_fase_1"] is True
        assert linha["contextos_distintos"] == 2
        assert "PROC-SIMB-01" in relatorio["aprovados"]

    def test_item_sem_cadeia_anotada_conta_como_acervo_mas_nao_como_evidencia(self, monkeypatch):
        itens = [_item(f"I-{i}", disciplina="Física" if i < 3 else "Biologia", com_cadeia=False) for i in range(1, 6)]
        _instalar(monkeypatch, itens)
        linha = self._linha(curadoria.relatorio_de_oferta())
        assert linha["itens"] == 5
        assert linha["com_cadeia_raiz"] == 0
        assert linha["apto_para_fase_1"] is False

    def test_nao_conta_o_mesmo_item_duas_vezes(self, monkeypatch):
        """O índice mapeia `item_id` E `item_hash` para o mesmo item."""
        _instalar(monkeypatch, [_item("I-1")])
        assert curadoria.relatorio_de_oferta()["acervo"]["itens"] == 1

    def test_relatorio_conta_o_que_ja_passou_por_revisao(self, monkeypatch):
        _instalar(monkeypatch, [_item("I-1", revisado=True, apto=True), _item("I-2")])
        acervo = curadoria.relatorio_de_oferta()["acervo"]
        assert acervo["revisados"] == 1 and acervo["aptos_para_crenca"] == 1


# ============================================ fila e revisão humana


class TestRevisaoHumana:
    def test_fila_agrupa_por_par_e_mostra_a_cadeia(self, monkeypatch):
        _instalar(monkeypatch, [_item("I-1"), _item("I-2")])
        fila = curadoria.fila_de_revisao()
        grupo = fila["pares"][0]
        assert grupo["par"] == "ERR-03|PROC-SIMB-01"
        assert len(grupo["itens"]) == 2
        assert grupo["itens"][0]["cadeia"][0]["papel"] == "raiz"
        assert grupo["itens"][0]["alternativa"] == "B"

    def test_item_ja_revisado_sai_da_fila_de_pendentes(self, monkeypatch):
        _instalar(monkeypatch, [_item("I-1", revisado=True, apto=True), _item("I-2")])
        fila = curadoria.fila_de_revisao(apenas_pendentes=True)
        assert [i["item_id"] for i in fila["pares"][0]["itens"]] == ["I-2"]

    def test_revisar_grava_o_portao_no_item(self, monkeypatch):
        escritas, _ = _instalar(monkeypatch, [_item("I-1")])
        curadoria.revisar_item("I-1", aprovado=True, revisor="ana@x.com")
        doc_id, payload, merge = escritas[-1]
        qual = payload["item"]["qualidade"]
        assert doc_id == "doc-I-1" and merge is True
        assert qual["apto_para_camada_de_crenca"]["valor"] is True
        assert qual["revisado"] is True and qual["revisor"] == "ana@x.com"

    def test_rejeitar_registra_a_revisao_sem_abrir_o_portao(self, monkeypatch):
        escritas, _ = _instalar(monkeypatch, [_item("I-1")])
        curadoria.revisar_item("I-1", aprovado=False, revisor="ana@x.com")
        qual = escritas[-1][1]["item"]["qualidade"]
        assert qual["revisado"] is True
        assert qual["apto_para_camada_de_crenca"]["valor"] is False

    def test_item_inexistente_e_erro_e_nao_silencio(self, monkeypatch):
        _instalar(monkeypatch, [_item("I-1")])
        with pytest.raises(KeyError):
            curadoria.revisar_item("I-404", aprovado=True, revisor="ana@x.com")

    def test_lote_nao_derruba_os_outros_quando_um_falha(self, monkeypatch):
        _instalar(monkeypatch, [_item("I-1")])
        r = curadoria.revisar_em_lote(["I-1", "I-404"], aprovado=True, revisor="ana@x.com")
        assert r["revisados"] == ["I-1"]
        assert r["falhas"][0]["item_id"] == "I-404"


class TestPortaoSobeDepoisDaRevisao:
    """O critério de aceite número 1 da Fase 0, ponta a ponta."""

    def _historico(self, item):
        evento = {
            "event_id": "e1",
            "item_id": "I-1",
            "ontology_version": "1.4.1",
            "status": "respondida",
            "timestamp": "2026-09-01T10:00:00+00:00",
            "resposta": {"alternativa_escolhida": "B", "acertou": False},
        }
        traco = motor.produzir_traco("U1", evento, item)
        return {
            "tracos": [traco], "processo_stats": {}, "itens_respondidos": {"I-1"},
            "eventos": 1, "respondidos": 1, "eventos_com_item": 1, "erros": 1,
            "falha_de_leitura": False,
        }

    def test_antes_da_revisao_o_traco_e_barrado(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)
        monkeypatch.setattr(motor, "_ler_historico", lambda uid: self._historico(_item("I-1", apto=False)))
        p = motor.perfil("U1")
        assert p["portao"]["tracos_no_perfil"] == 0
        assert p["portao"]["tracos_barrados"] == 1
        assert p["habilidades_prioritarias"] == []

    def test_depois_da_revisao_o_traco_entra_no_perfil(self, monkeypatch):
        monkeypatch.setattr(portao_crenca, "_cache", portao_crenca.MODO_CRENCA, raising=False)
        revisado = _item("I-1", apto=True, revisado=True)
        monkeypatch.setattr(motor, "_ler_historico", lambda uid: self._historico(revisado))
        p = motor.perfil("U1")
        assert p["portao"]["tracos_no_perfil"] == 1
        assert p["portao"]["tracos_barrados"] == 0
        assert p["provisorio"] is False
        assert p["aviso"] is None

    def test_revisar_invalida_o_indice_de_itens(self, monkeypatch):
        """Sem isto a revisão acontece e não tem efeito até o próximo deploy:
        o índice é cache de processo e alimenta motor e intervenções."""
        _instalar(monkeypatch, [_item("I-1")])
        chamadas = {"force": 0}
        original = annotation_service._build_item_index

        def _espiao(force=False):
            if force:
                chamadas["force"] += 1
            return original(force=force)

        monkeypatch.setattr(annotation_service, "_build_item_index", _espiao)
        curadoria.revisar_item("I-1", aprovado=True, revisor="ana@x.com")
        assert chamadas["force"] == 1


# ============================================ Fase 5 — Sapiens Lab


class TestSapiensLab:
    def _bloco(self, *, dispensas=0, retestes=(0, 0), raizes=2):
        import revisao_espacada as rev

        b = None
        for i in range(raizes):
            b = rev.registrar(
                b,
                processos=["PROC-SIMB-01"],
                acertou=False,
                dia=f"2026-09-{i + 1:02d}",
                quando=f"2026-09-{i + 1:02d}T10:00:00+00:00",
                raiz={"erro": "ERR-03", "processo": "PROC-SIMB-01", "confianca": 0.7},
            )
        e = b["processos"]["PROC-SIMB-01"]
        e["dispensas"] = dispensas
        e["retestes"] = {"total": retestes[0], "acertos": retestes[1]}
        e["marcos"] = [{"tipo": rev.MARCO_INTERVENCAO, "ts": "2026-09-02T10:00:00+00:00", "erro": "ERR-03"}] * 10
        return b

    def test_alvo_e_o_par_e_nunca_o_aluno(self, monkeypatch):
        monkeypatch.setattr(fs, "varrer_revisoes", lambda limite=500: [{"uid": "U1", "revisao": self._bloco()}])
        r = _run(sapiens_lab.hipoteses())
        assert r["pares"][0]["par"] == "ERR-03|PROC-SIMB-01"
        assert "uid" not in r["pares"][0] and "aluno_id" not in r["pares"][0]
        assert r["nao_altera_ontologia"] is True

    def test_dispensa_sistematica_vira_sinal(self, monkeypatch):
        blocos = [
            {"uid": f"U{i}", "revisao": self._bloco(dispensas=8)} for i in range(4)
        ]
        monkeypatch.setattr(fs, "varrer_revisoes", lambda limite=500: blocos)
        linha = _run(sapiens_lab.hipoteses())["pares"][0]
        assert any(s["tipo"] == "intervencao_dispensada" for s in linha["sinais"])
        assert linha["acao"] == "revisar_anotacao"

    def test_amostra_pequena_nao_entra_na_fila_de_revisao(self, monkeypatch):
        monkeypatch.setattr(fs, "varrer_revisoes", lambda limite=500: [{"uid": "U1", "revisao": self._bloco(dispensas=8)}])
        r = _run(sapiens_lab.hipoteses())
        assert r["para_revisao_humana"] == []
        assert r["pares"][0]["amostra_suficiente"] is False

    def test_reteste_que_nao_melhora_vira_sinal(self, monkeypatch):
        blocos = [{"uid": f"U{i}", "revisao": self._bloco(retestes=(10, 2))} for i in range(4)]
        monkeypatch.setattr(fs, "varrer_revisoes", lambda limite=500: blocos)
        linha = _run(sapiens_lab.hipoteses())["pares"][0]
        assert any(s["tipo"] == "reteste_nao_melhora" for s in linha["sinais"])

    def test_autorrelato_entra_como_terceira_evidencia(self, monkeypatch, fake_db):
        microdiagnostico.set_db(fake_db)
        _run(fake_db.autorrelato_pares.insert_one({
            "_id": "ERR-03|PROC-SIMB-01", "total": 12, "por_opcao": {"chute": 10, "nao_sabia": 2},
        }))
        blocos = [{"uid": f"U{i}", "revisao": self._bloco()} for i in range(4)]
        monkeypatch.setattr(fs, "varrer_revisoes", lambda limite=500: blocos)
        linha = _run(sapiens_lab.hipoteses())["pares"][0]
        assert any(s["tipo"] == "autorrelato_contradiz" for s in linha["sinais"])
        assert "ERR-03|PROC-SIMB-01" in _run(sapiens_lab.hipoteses())["para_revisao_humana"]

    def test_o_lab_nunca_escreve_nada(self):
        """R-7 lido no CÓDIGO, não na docstring: o Lab propõe revisão e nada
        mais. Nem catálogo, nem item, nem estado de aluno."""
        import ast

        arvore = ast.parse((BACKEND / "sapiens_lab.py").read_text(encoding="utf-8"))
        importados = {
            (no.module or "").split(".")[0]
            for no in ast.walk(arvore)
            if isinstance(no, ast.ImportFrom)
        } | {
            alias.name.split(".")[0]
            for no in ast.walk(arvore)
            if isinstance(no, ast.Import)
            for alias in no.names
        }
        assert "curadoria" not in importados, "o Lab importou o módulo que escreve revisão"
        assert "canonical_ontology" not in importados, "o Lab alcançou o catálogo"

        chamadas = {
            no.func.attr
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        }
        for proibida in ("set", "update", "update_one", "revisar_item", "escrever_revisao", "write"):
            assert proibida not in chamadas, f"sapiens_lab chama {proibida}()"


# ============================================ a chave de contexto


class TestChaveDeContexto:
    """O relatório de oferta só significa alguma coisa se "outro contexto"
    discriminar de verdade. A primeira versão usava o DOMÍNIO, que a
    Constituição §4.4 define como DERIVADO do processo — logo, quase constante
    dentro de um processo. Medido no acervo real, sete processos apareciam como
    "sem transferência possível" cobrindo meia dúzia de disciplinas cada."""

    def test_dominio_igual_mas_disciplina_diferente_conta_como_outro_contexto(self, monkeypatch):
        itens = [
            _item(f"I-{i}", dominio="DOM-01", disciplina="Física" if i < 3 else "Biologia")
            for i in range(1, 6)
        ]
        _instalar(monkeypatch, itens)
        linha = next(
            l for l in curadoria.relatorio_de_oferta()["processos"] if l["processo_id"] == "PROC-SIMB-01"
        )
        assert linha["contextos_distintos"] == 2, "o domínio comum apagou a variedade de disciplina"
        assert linha["apto_para_fase_1"] is True

    def test_disciplina_igual_nao_vira_contexto_novo_por_causa_do_dominio(self, monkeypatch):
        """O inverso também tem de valer: variar só o domínio, com a mesma
        disciplina, NÃO é transferência."""
        itens = [
            _item(f"I-{i}", dominio="DOM-01" if i < 3 else "DOM-07", disciplina="Física")
            for i in range(1, 6)
        ]
        _instalar(monkeypatch, itens)
        linha = next(
            l for l in curadoria.relatorio_de_oferta()["processos"] if l["processo_id"] == "PROC-SIMB-01"
        )
        assert linha["contextos_distintos"] == 1
        assert linha["apto_para_fase_1"] is False

    def test_tema_nao_e_chave_primaria(self, monkeypatch):
        """Com dezenas de temas por processo, tema como chave faria quase toda
        questão contar como transferência — e o sinal deixaria de significar
        alguma coisa."""
        import revisao_service

        item = _item("I-1", disciplina="Física")
        item["fonte"]["tema"] = "Ondulatória"
        outro = _item("I-2", disciplina="Física")
        outro["fonte"]["tema"] = "Termodinâmica"
        assert revisao_service.contexto_do_item(item) == revisao_service.contexto_do_item(outro)


class TestFilaNaoTruncaEmSilencio:
    """Uma fila de revisão que corta sem avisar é pior que uma fila vazia: o
    revisor termina a tela achando que acabou, e o que sobrou não volta a
    aparecer para ninguém. Medido no acervo real, o par maior tem 89 linhas
    contra um limite de tela de 50."""

    def test_o_par_declara_quantas_linhas_tem_de_verdade(self, monkeypatch):
        _instalar(monkeypatch, [_item(f"I-{i}") for i in range(1, 8)])
        fila = curadoria.fila_de_revisao(limite=3)
        g = fila["pares"][0]
        assert len(g["itens"]) == 3
        assert g["total_no_par"] == 7
        assert g["par"] in fila["pares_truncados"]

    def test_sem_truncamento_a_lista_de_avisos_fica_vazia(self, monkeypatch):
        _instalar(monkeypatch, [_item(f"I-{i}") for i in range(1, 4)])
        fila = curadoria.fila_de_revisao(limite=50)
        assert fila["pares_truncados"] == []
        assert fila["pares"][0]["total_no_par"] == 3

    def test_pendentes_conta_o_que_ficou_de_fora(self, monkeypatch):
        """O contador do topo é o tamanho do TRABALHO, não o da tela."""
        _instalar(monkeypatch, [_item(f"I-{i}") for i in range(1, 8)])
        assert curadoria.fila_de_revisao(limite=2)["itens_pendentes"] == 7


# ============================================ piso de confiança


class TestPisoDeConfianca:
    """O piso é o substituto PROVISÓRIO da revisão humana, para um corpus que
    ninguém tem tempo de revisar item a item.

    A linha que ele não cruza: nunca grava `revisado` nem
    `apto_para_camada_de_crenca`. Transformar a confiança que a IA declarou em
    "revisado por humano" seria falsificar exatamente o dado que EXT-WP1-1.0
    L13b existe para proteger — e o perfil continuaria, com razão, provisório.
    """

    def _traco(self, confianca, revisado=False):
        return {"apto_para_camada_de_crenca": revisado, "confianca_global": confianca}

    def _com_piso(self, monkeypatch, piso, modo=portao_crenca.MODO_DESLIGADO):
        monkeypatch.setattr(portao_crenca, "_cache", modo, raising=False)
        monkeypatch.setattr(portao_crenca, "_cache_piso", piso, raising=False)

    def test_sem_piso_o_comportamento_e_o_de_antes(self, monkeypatch):
        self._com_piso(monkeypatch, 0.0)
        tracos = [self._traco(0.15), self._traco(0.4), self._traco(0.7)]
        aptos, barrados = motor._particionar_pelo_portao(tracos)
        assert len(aptos) == 3 and barrados == []

    def test_piso_barra_a_raiz_fraca_mesmo_com_o_portao_desligado(self, monkeypatch):
        self._com_piso(monkeypatch, 0.4)
        aptos, barrados = motor._particionar_pelo_portao(
            [self._traco(0.15), self._traco(0.4), self._traco(0.7)]
        )
        assert [t["confianca_global"] for t in aptos] == [0.4, 0.7]
        assert [t["confianca_global"] for t in barrados] == [0.15]

    def test_revisao_humana_supersede_o_piso(self, monkeypatch):
        """O piso substitui a revisão; não é um requisito somado a ela."""
        self._com_piso(monkeypatch, 0.7)
        aptos, barrados = motor._particionar_pelo_portao([self._traco(0.15, revisado=True)])
        assert len(aptos) == 1 and barrados == []

    def test_com_o_portao_em_crenca_o_piso_nao_abre_excecao(self, monkeypatch):
        """`crenca` exige revisão humana. Confiança alta não é revisão."""
        self._com_piso(monkeypatch, 0.4, modo=portao_crenca.MODO_CRENCA)
        aptos, barrados = motor._particionar_pelo_portao([self._traco(0.7)])
        assert aptos == [] and len(barrados) == 1

    def test_o_piso_nunca_marca_o_item_como_revisado(self, monkeypatch):
        """A garantia central. Se um dia alguém fizer o piso gravar no item,
        este teste cai — e é para cair."""
        self._com_piso(monkeypatch, 0.4)
        traco = self._traco(0.7)
        motor._particionar_pelo_portao([traco])
        assert traco["apto_para_camada_de_crenca"] is False

    def test_valor_invalido_degrada_para_sem_piso(self, monkeypatch):
        for bruto in ("abacaxi", "-1", "2.5"):
            monkeypatch.setenv("PORTAO_CONFIANCA_MINIMA", bruto)
            monkeypatch.setattr(portao_crenca, "_cache_piso", None, raising=False)
            assert portao_crenca.confianca_minima() == 0.0

    def test_o_piso_vale_tambem_para_agendar_reteste(self, monkeypatch):
        """Agendar um reteste É mover o estado do aluno — a mesma regra do
        perfil tem de valer aqui, senão o piso teria um buraco."""
        import revisao_service

        self._com_piso(monkeypatch, 0.7)
        item = _item("I-1")
        evento = {
            "event_id": "e1", "item_id": "I-1", "ontology_version": "1.4.1",
            "status": "respondida", "timestamp": "2026-09-01T10:00:00+00:00",
            "resposta": {"alternativa_escolhida": "B", "acertou": False},
        }
        # A cadeia do dublê tem raiz com confiança 0.7 — passa no piso de 0.7.
        assert revisao_service.raiz_do_evento("U1", evento, item) is not None
        self._com_piso(monkeypatch, 0.71)
        assert revisao_service.raiz_do_evento("U1", evento, item) is None
