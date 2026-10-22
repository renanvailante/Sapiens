"""O diagnóstico do primeiro acesso: as 10 questões que o cadastro abre.

O que estes testes travam é o que o aluno sente na primeira sessão — a
primeira questão é só texto, curta, em português, e a sequência não abre pela
área em que mais se erra. Ver o cabeçalho de `diagnostico_inicial.py`.
"""
from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import diagnostico_inicial as di  # noqa: E402
import server  # noqa: E402
from server import _area_enem  # noqa: E402

_DISCIPLINA = {
    di.LINGUAGENS: "Linguagens, Códigos e suas Tecnologias",
    di.HUMANAS: "Ciências Humanas e suas Tecnologias",
    di.NATUREZA: "Ciências da Natureza e suas Tecnologias",
    di.MATEMATICA: "Matemática e suas Tecnologias",
}


def _q(item_id, area=di.HUMANAS, tamanho=200, *, numero=60, ano=2023, enunciado=None, disciplina=None, **questao):
    texto = enunciado if enunciado is not None else f"{item_id} " + "palavra " * (tamanho // 8)
    return {
        "item_id": item_id,
        "fonte": {"disciplina": disciplina or _DISCIPLINA[area], "numero": numero, "ano": ano, "banca": "ENEM"},
        "questao": {
            "enunciado": texto,
            "alternativas": [{"letra": l, "texto": f"opção {l}", "correta": l == "A"} for l in "ABCDE"],
            **questao,
        },
    }


_SIGLA = {di.LINGUAGENS: "Lin", di.HUMANAS: "Hum", di.NATUREZA: "Nat", di.MATEMATICA: "Mat"}


def _acervo(por_area=5):
    itens = []
    for area, numero in ((di.LINGUAGENS, 20), (di.HUMANAS, 60), (di.NATUREZA, 100), (di.MATEMATICA, 150)):
        for i in range(por_area):
            itens.append(_q(f"{_SIGLA[area]}-{i}", area, 200 + 40 * i, numero=numero + i))
    return itens


def _area_do(item_id, acervo):
    item = next(it for it in acervo if it["item_id"] == item_id)
    return di.area(item["fonte"]["disciplina"], _area_enem)


class TestOrdem:
    def test_dez_questoes_intercaladas_sem_abrir_por_matematica(self):
        acervo = _acervo()
        escolhidos = di.escolher(acervo, _area_enem)
        assert len(escolhidos) == di.TOTAL
        assert [_area_do(i, acervo) for i in escolhidos] == list(di.ORDEM)
        assert _area_do(escolhidos[0], acervo) != di.MATEMATICA

    def test_dentro_da_area_a_mais_curta_vem_primeiro(self):
        acervo = _acervo()
        escolhidos = di.escolher(acervo, _area_enem)
        linguagens = [i for i in escolhidos if _area_do(i, acervo) == di.LINGUAGENS]
        assert linguagens == ["Lin-0", "Lin-1", "Lin-2"]

    def test_mesma_entrada_em_outra_ordem_da_a_mesma_lista(self):
        """Lista estável é o que deixa retomar no meio: o runner começa na
        primeira questão ainda não respondida DESTA lista."""
        acervo = _acervo()
        embaralhado = acervo[:]
        random.Random(7).shuffle(embaralhado)
        assert di.escolher(embaralhado, _area_enem) == di.escolher(acervo, _area_enem)

    def test_empate_de_tamanho_prefere_a_edicao_mais_recente(self):
        acervo = _acervo()
        # Mesmo tamanho de id, mesma carga: só a edição desempata.
        acervo.append(_q("Lin-N", di.LINGUAGENS, 200, numero=30, ano=2024))
        acervo[0]["fonte"]["ano"] = 2015
        escolhidos = di.escolher(acervo, _area_enem)
        assert escolhidos[0] == "Lin-N"


class TestQueNaoEntra:
    def _so_ela_e_curta(self, intrusa):
        """Uma questão bem mais curta que todas: se a regra a aceitasse, ela
        seria a primeira do diagnóstico."""
        acervo = _acervo()
        acervo.append(intrusa)
        return di.escolher(acervo, _area_enem)

    def test_figura_no_enunciado(self):
        assert "X" not in self._so_ela_e_curta(
            _q("X", di.LINGUAGENS, 130, visual_assets=[{"asset_id": "a1"}]))

    def test_imagem_em_recursos(self):
        assert "X" not in self._so_ela_e_curta(
            _q("X", di.LINGUAGENS, 130, recursos={"imagens": [{"arquivo": "q.png"}]}))

    def test_recursos_sem_arquivo_nao_e_figura(self):
        assert self._so_ela_e_curta(
            _q("X", di.LINGUAGENS, 130, recursos={"imagens": [{"arquivo": ""}]}))[0] == "X"

    @pytest.mark.parametrize("numero", [1, 5, 91, 95])
    def test_lingua_estrangeira_pela_numeracao(self, numero):
        assert "X" not in self._so_ela_e_curta(_q("X", di.LINGUAGENS, 130, numero=numero))

    @pytest.mark.parametrize("disciplina", ["Inglês", "Língua Estrangeira - Espanhol", "Linguagens - Inglês"])
    def test_lingua_estrangeira_pela_disciplina(self, disciplina):
        assert "X" not in self._so_ela_e_curta(_q("X", di.LINGUAGENS, 130, disciplina=disciplina))

    def test_texto_em_ingles_sem_rotulo(self):
        texto = "Read the text. The city and the people of this town are proud of the river " * 3
        assert "X" not in self._so_ela_e_curta(_q("X", di.LINGUAGENS, enunciado=texto, numero=30))

    def test_matematica_com_y_nao_e_lingua_estrangeira(self):
        texto = ("Na função dada, y = 2x + 3, e y cresce quando x cresce. Para y igual a 7, "
                 "qual é o valor de x? Considere y positivo e x inteiro em todos os casos.")
        assert not di.lingua_estrangeira(_q("M", di.MATEMATICA, enunciado=texto, numero=150), di.MATEMATICA)

    def test_enunciado_curto_demais_e_extracao_quebrada(self):
        assert "X" not in self._so_ela_e_curta(_q("X", di.LINGUAGENS, enunciado="Assinale a correta."))

    def test_alternativa_sem_texto(self):
        intrusa = _q("X", di.LINGUAGENS, 130)
        intrusa["questao"]["alternativas"][2]["texto"] = ""
        assert "X" not in self._so_ela_e_curta(intrusa)

    def test_enunciado_que_cita_figura_que_nao_veio(self):
        texto = "Observe o gráfico abaixo, que mostra a variação da população ao longo do século passado no país."
        assert "X" not in self._so_ela_e_curta(_q("X", di.HUMANAS, enunciado=texto))

    def test_mesmo_texto_base_nao_entra_duas_vezes(self):
        acervo = _acervo()
        base = "Texto-base comum aos dois itens do par. " * 4
        acervo.append(_q("Par-1", di.LINGUAGENS, enunciado=base + "Primeira pergunta.", numero=10))
        acervo.append(_q("Par-2", di.LINGUAGENS, enunciado=base + "Segunda pergunta.", numero=11))
        escolhidos = di.escolher(acervo, _area_enem)
        assert len({"Par-1", "Par-2"} & set(escolhidos)) == 1


class TestQuandoFalta:
    def test_area_vazia_cede_a_vaga_para_as_outras(self):
        acervo = [it for it in _acervo() if _area_do(it["item_id"], _acervo()) != di.NATUREZA]
        escolhidos = di.escolher(acervo, _area_enem)
        assert len(escolhidos) == di.TOTAL
        assert di.NATUREZA not in {_area_do(i, acervo) for i in escolhidos}

    def test_a_reserva_so_entra_quando_a_estrita_nao_fecha_dez(self):
        texto = ("Observe a tabela com os dados de produção agrícola das regiões ao longo de uma "
                 "década inteira e responda considerando apenas as regiões citadas no texto.")
        poucas = _acervo(por_area=1) + [_q("R", di.HUMANAS, enunciado=texto)]
        assert "R" in di.escolher(poucas, _area_enem)
        assert "R" not in di.escolher(_acervo() + [_q("R", di.HUMANAS, enunciado=texto)], _area_enem)

    def test_acervo_vazio_nao_quebra(self):
        assert di.escolher([], _area_enem) == []

    def test_disciplina_fina_cai_na_area_certa(self):
        assert di.area("História", _area_enem) == di.HUMANAS
        assert di.area("Língua Portuguesa", _area_enem) == di.LINGUAGENS
        assert di.area("Inglês", _area_enem) is None


class TestRota:
    @pytest.fixture
    def rota(self, fake_db, monkeypatch):
        monkeypatch.setattr(server, "db", fake_db)
        # O dublê não atravessa projeção de INCLUSÃO por caminho
        # ("questao.enunciado"); a de exclusão devolve o documento inteiro, e a
        # regra lê o que precisa dele.
        monkeypatch.setattr(server, "_PROJECAO_DA_ESCOLHA", {"_id": 0})
        monkeypatch.setitem(server._DIAGNOSTICO_ESCOLHIDO, "ids", [])
        monkeypatch.setitem(server._DIAGNOSTICO_ESCOLHIDO, "em", 0.0)
        return fake_db

    def test_devolve_as_dez_na_ordem_e_sem_gabarito(self, rota):
        for it in _acervo():
            asyncio.run(rota.questoes_public.insert_one(dict(it)))
        resposta = asyncio.run(server.questoes_do_diagnostico(None))
        assert resposta["count"] == di.TOTAL
        assert [it["item_id"] for it in resposta["items"]] == di.escolher(_acervo(), _area_enem)
        for it in resposta["items"]:
            assert all("correta" not in a for a in it["questao"]["alternativas"])

    def test_acervo_vazio_no_meio_do_sync_nao_fica_guardado(self, rota):
        assert asyncio.run(server.questoes_do_diagnostico(None))["count"] == 0
        assert server._DIAGNOSTICO_ESCOLHIDO["ids"] == []
        for it in _acervo():
            asyncio.run(rota.questoes_public.insert_one(dict(it)))
        assert asyncio.run(server.questoes_do_diagnostico(None))["count"] == di.TOTAL
