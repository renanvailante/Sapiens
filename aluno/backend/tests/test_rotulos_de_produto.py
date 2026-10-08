"""Os nomes reais da ontologia nunca chegam ao aluno.

Trava quatro coisas: todo processo, erro e intervenção do catálogo tem rótulo;
nenhum rótulo é o nome do catálogo disfarçado; o espelho do frontend é o mesmo
mapa; e as rotas do aluno saem sem nome real nenhum no JSON.
"""
from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from pathlib import Path

import pytest

import motor_cognitivo
import rotulos_de_produto as r

JS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "rotulosDoMotor.js"


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower().strip()


def _catalogo():
    return motor_cognitivo._catalogo()


class TestCobertura:
    def test_todo_processo_do_catalogo_tem_rotulo(self):
        ids = set(_catalogo()["processos"])
        assert len(ids) == 25
        assert ids == set(r.PROCESSOS)

    def test_todo_tipo_de_erro_tem_rotulo(self):
        ids = set(_catalogo()["erros"])
        assert ids <= set(r.ERROS)
        assert motor_cognitivo.SENTINELAS <= set(r.ERROS)

    def test_toda_intervencao_tem_rotulo(self):
        assert set(_catalogo()["intervencoes"]) == set(r.INTERVENCOES)

    def test_nenhum_rotulo_e_o_nome_do_catalogo(self):
        cat = _catalogo()
        nomes = {_norm(x["nome"]) for grupo in ("processos", "erros", "intervencoes") for x in cat[grupo].values()}
        for rotulo in [*r.PROCESSOS.values(), *r.ERROS.values(), *r.INTERVENCOES.values()]:
            assert _norm(rotulo) not in nomes, rotulo

    def test_rotulos_de_processo_nao_se_repetem(self):
        assert len(set(r.PROCESSOS.values())) == len(r.PROCESSOS)


class TestEspelhoDoFrontend:
    def _mapa_js(self, nome: str) -> dict[str, str]:
        texto = JS.read_text(encoding="utf-8")
        bloco = re.search(rf"export const {nome} = \{{(.*?)\n\}};", texto, re.S)
        assert bloco, f"{nome} não encontrado em {JS.name}"
        return dict(re.findall(r'"([^"]+)":\s*"([^"]*)"', bloco.group(1)))

    @pytest.mark.parametrize("nome", ["PROCESSOS", "ERROS", "INTERVENCOES"])
    def test_o_js_e_o_mesmo_mapa(self, nome):
        assert self._mapa_js(nome) == getattr(r, nome)


class TestVestir:
    def test_campos_estruturados(self):
        saida = r.vestir({
            "linhas": [{
                "processo_id": "PROC-QUANT-02",
                "processo_nome": "Inferir e aplicar relacao proporcional entre grandezas",
                "erro_dominante": {"id": "ERR-05", "nome": "Confusao de direcao em relacao proporcional"},
            }],
            "fila": [{"processo_id": "PROC-TEXT-01", "processo_nome": "x", "erro_dominante": "ERR-01", "erro_nome": "y"}],
            "processo": {"id": "PROC-INC-01", "nome": "Interpretar probabilidade condicional"},
        })
        assert saida["linhas"][0]["processo_nome"] == "Proporção"
        assert saida["linhas"][0]["erro_dominante"]["nome"] == "Proporção invertida"
        assert saida["fila"][0]["erro_nome"] == "Dado que passou batido"
        assert saida["processo"]["nome"] == "Chance com condição"

    def test_texto_livre_com_e_sem_acento(self):
        t = r.trocar_no_texto("O padrão é Inferência indevida; antes, inferencia INDEVIDA.")
        assert "nferen" not in t and t.count("Ir além do texto") == 2

    def test_nao_mexe_no_original(self):
        original = {"processo_id": "PROC-QUANT-02", "processo_nome": "nome real"}
        r.vestir(original)
        assert original["processo_nome"] == "nome real"

    def test_id_desconhecido_nunca_devolve_o_nome_que_veio(self):
        assert r.vestir({"processo_id": "PROC-X", "processo_nome": "Segredo"})["processo_nome"] == r.PROCESSO_DESCONHECIDO


def _sem_nome_real(resposta) -> list[str]:
    texto = _norm(json.dumps(resposta, ensure_ascii=False))
    cat = _catalogo()
    return [
        x["nome"] for grupo in ("processos", "erros")
        for x in cat[grupo].values() if _norm(x["nome"]) in texto
    ]


class TestRotasDoAluno:
    """As rotas do aluno passam a resposta por `vestir`. O motor aqui é um
    dublê que devolve o nome REAL do catálogo em todo lugar possível."""

    @pytest.fixture
    def resposta_com_nomes(self):
        cat = _catalogo()
        pid, eid = "PROC-QUANT-02", "ERR-05"
        nome_p, nome_e = cat["processos"][pid]["nome"], cat["erros"][eid]["nome"]
        return {
            "habilidades_prioritarias": [{
                "processo_id": pid, "processo_nome": nome_p,
                "erro_dominante": {"id": eid, "nome": nome_e},
                "porque": f"O ponto {nome_p} tem o erro {nome_e}.",
            }],
            "itens": [{"processo_id": pid, "processo_nome": nome_p, "erro_dominante": eid, "erro_nome": nome_e}],
            "processo": {"id": pid, "nome": nome_p},
        }

    def test_motor_perfil(self, monkeypatch, resposta_com_nomes):
        import firestore_service as fs
        import motor_routes
        from models import User

        monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: None)
        monkeypatch.setattr(motor_cognitivo, "perfil", lambda uid: resposta_com_nomes)
        monkeypatch.setattr(motor_cognitivo, "detalhe", lambda uid, pid: resposta_com_nomes)
        u = User(user_id="a1", email="a@x.com", name="A")
        assert _sem_nome_real(asyncio.run(motor_routes.meu_perfil(user=u))) == []
        assert _sem_nome_real(asyncio.run(motor_routes.minha_habilidade("PROC-QUANT-02", user=u))) == []

    def test_fila_e_trajetoria_de_revisao(self, monkeypatch, resposta_com_nomes):
        import firestore_service as fs
        import revisao_routes
        import revisao_service
        from models import User

        monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: None)
        monkeypatch.setattr(revisao_service, "fila", lambda uid, limite=8: resposta_com_nomes)
        monkeypatch.setattr(revisao_service, "trajetoria", lambda uid: resposta_com_nomes)
        u = User(user_id="a1", email="a@x.com", name="A")
        assert _sem_nome_real(asyncio.run(revisao_routes.minha_fila(limite=8, user=u))) == []
        assert _sem_nome_real(asyncio.run(revisao_routes.minha_trajetoria(user=u))) == []

    def test_diagnostico(self, monkeypatch, resposta_com_nomes):
        import annotation_service
        import diagnostico_routes
        import firestore_service as fs
        from models import User

        async def _diag(uid, **k):
            return resposta_com_nomes

        monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: None)
        monkeypatch.setattr(annotation_service, "compute_diagnostico_real", _diag)
        u = User(user_id="a1", email="a@x.com", name="A")
        assert _sem_nome_real(asyncio.run(diagnostico_routes.get_diagnostico(user=u))) == []
