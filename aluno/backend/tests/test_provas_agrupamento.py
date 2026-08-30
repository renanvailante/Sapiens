"""`/api/provas` (agrupamento por banca/ano/prova) e o filtro de `/api/questoes`.

Não depende de `REACT_APP_BACKEND_URL` nem de servidor no ar — importa
`server` diretamente e chama as funções da rota, como
`pipeline/backend/tests/test_book_fonte_autoritativa.py`. Usa o Mongo local
de verdade (mesmo padrão do resto da suíte offline deste projeto), mas as
asserções não fixam a contagem real de questões — só a forma da resposta e o
comportamento do filtro — para não quebrar quando o corpus mudar de tamanho.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import server  # noqa: E402
from server import _area_enem, _bloco_enem  # noqa: E402


_loop = None


def _run(coro):
    """Reusa UM loop para todos os testes deste arquivo.

    O cliente Motor (`server.client`) é um singleton de módulo, preso ao
    primeiro event loop que o usa. Criar um `asyncio.new_event_loop()` novo a
    cada teste faz o driver colidir ("Future attached to a different loop")
    a partir da 3ª chamada ao banco no mesmo processo — reusar o loop dentro
    deste arquivo evita isso sem tocar a inicialização de `server.py`.
    """
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


class TestAreaEnem:
    def test_variacoes_de_caixa_e_granularidade_caem_na_mesma_area(self):
        for bruto in ("Matemática e suas Tecnologias", "MATEMÁTICA E SUAS TECNOLOGIAS", "Matemática"):
            assert _area_enem(bruto) == "Matemática"

    def test_disciplinas_especificas_de_natureza_convergem(self):
        for bruto in ("Física", "Química", "Biologia", "Ciências da Natureza e suas Tecnologias"):
            assert _area_enem(bruto) == "Ciências da Natureza"

    def test_valor_desconhecido_e_preservado_sem_inventar_categoria(self):
        assert _area_enem("Filosofia") == "Filosofia"

    def test_none_e_vazio_nao_quebram(self):
        assert _area_enem(None) is None
        assert _area_enem("") is None


class TestBlocoEnem:
    def test_os_4_blocos_canonicos(self):
        assert _bloco_enem(1) == (1, 45)
        assert _bloco_enem(45) == (1, 45)
        assert _bloco_enem(46) == (46, 90)
        assert _bloco_enem(90) == (46, 90)
        assert _bloco_enem(91) == (91, 135)
        assert _bloco_enem(135) == (91, 135)
        assert _bloco_enem(136) == (136, 180)
        assert _bloco_enem(180) == (136, 180)

    def test_bloco_e_sempre_canonico_mesmo_com_um_item_faltando(self):
        # 89 de 90 persistidas (1 caiu por timeout, ver auditoria) não pode
        # encolher o bloco nem misturá-lo com o vizinho: 134 é sempre 91-135.
        assert _bloco_enem(134) == (91, 135)

    def test_numero_none_ou_invalido_nao_tem_bloco(self):
        assert _bloco_enem(None) is None
        assert _bloco_enem(0) is None
        assert _bloco_enem(-5) is None


class TestListProvasPublico:
    def test_formato_da_resposta(self):
        r = _run(server.list_provas_publico())
        assert "provas" in r
        assert isinstance(r["provas"], list)
        for p in r["provas"]:
            assert set(p.keys()) == {
                "banca", "ano", "prova", "numero_min", "numero_max", "count", "total_bloco", "disciplinas",
            }
            assert isinstance(p["count"], int) and p["count"] > 0
            assert p["total_bloco"] == 45
            assert p["numero_max"] - p["numero_min"] == 44
            assert p["count"] <= p["total_bloco"]
            assert isinstance(p["disciplinas"], list)

    def test_nenhum_bloco_junta_mais_de_45_questoes(self):
        """A regressão que motivou isto: 2 provas (dias/áreas) diferentes
        sendo mostradas como 1 caderno só de 89/90 questões."""
        r = _run(server.list_provas_publico())
        for p in r["provas"]:
            assert p["count"] <= 45

    def test_disciplina_minoritaria_nao_contamina_o_titulo_do_bloco(self, monkeypatch):
        """Um bloco de 45 é, por estrutura do ENEM, sempre 1 área só — 1-2
        itens com `fonte.disciplina` extraída errado (ruído de anotação
        automática) não podem virar "Ciências da Natureza e Matemática" num
        bloco que é 100% Matemática. A área do bloco é a MODA, não a união.

        Não escreve no Mongo real (`--dist loadscope` só isola por
        classe/módulo — escrever no `questoes_public` compartilhado correria
        contra os testes de `TestListQuestoesPublicoFiltro`, agendados num
        worker separado): injeta os 45 itens sintéticos direto no cursor.
        """
        banca, ano, prova = "TESTE-MODA", 2099, "UNICA"
        extras = [
            {"item_id": f"TESTE-MODA-{i}",
             "fonte": {"banca": banca, "ano": ano, "prova": prova, "numero": i,
                       "disciplina": "Física" if i == 1 else "Matemática"}}
            for i in range(1, 46)
        ]
        real_collection = server.db.questoes_public

        class _CursorComExtras:
            def __init__(self, real_cursor):
                self._real_cursor = real_cursor
                self._extras = iter(extras)

            def __aiter__(self):
                return self

            async def __anext__(self):
                async for doc in self._real_cursor:
                    return doc
                try:
                    return next(self._extras)
                except StopIteration:
                    raise StopAsyncIteration

        class _ColecaoComExtras:
            def find(self, *args, **kwargs):
                return _CursorComExtras(real_collection.find(*args, **kwargs))

        monkeypatch.setattr(server.db, "questoes_public", _ColecaoComExtras())
        r = _run(server.list_provas_publico())
        alvo = next(p for p in r["provas"] if p["banca"] == banca)
        assert alvo["count"] == 45
        assert alvo["disciplinas"] == ["Matemática"]


class TestListQuestoesPublicoFiltro:
    def test_filtro_por_prova_inexistente_devolve_vazio(self):
        r = _run(server.list_questoes_publico(limit=10, banca="ENEM", ano=2023, prova="COR-QUE-NAO-EXISTE"))
        assert r["count"] == 0
        assert r["items"] == []

    def test_sem_filtro_preserva_comportamento_anterior(self):
        # Um único `run_until_complete` para as duas chamadas: o cliente
        # Motor é um singleton do módulo, preso ao primeiro event loop que o
        # usa — dois `_run()` (cada um cria um loop novo) na mesma função
        # colidem ("Future attached to a different loop").
        async def _ambos():
            sem_filtro = await server.list_questoes_publico(limit=500)
            provas = (await server.list_provas_publico())["provas"]
            return sem_filtro, provas

        sem_filtro, provas = _run(_ambos())
        # Cada prova agrupada em /api/provas tem que estar inteiramente
        # contida no resultado sem filtro (nenhum item "sumiu" por causa do
        # parâmetro novo ser opcional).
        total_agrupado = sum(p["count"] for p in provas)
        assert sem_filtro["count"] >= total_agrupado

    def test_filtro_por_bloco_bate_com_a_contagem_do_agrupamento(self):
        # Sem numero_min/numero_max, um filtro por banca+ano+prova devolve o
        # CADERNO inteiro (todos os blocos) — por isso o filtro de bloco
        # (numero_min/numero_max) é obrigatório para isolar 1 prova real.
        async def _ambos():
            provas = (await server.list_provas_publico())["provas"]
            if not provas:
                return None
            alvo = provas[0]
            filtrado = await server.list_questoes_publico(
                limit=500, banca=alvo["banca"], ano=alvo["ano"], prova=alvo["prova"],
                numero_min=alvo["numero_min"], numero_max=alvo["numero_max"],
            )
            return alvo, filtrado

        resultado = _run(_ambos())
        if resultado is None:
            return  # nada sincronizado neste ambiente — nada a comparar
        alvo, filtrado = resultado
        assert filtrado["count"] == alvo["count"]
        for it in filtrado["items"]:
            assert alvo["numero_min"] <= it["fonte"]["numero"] <= alvo["numero_max"]

    def test_dois_blocos_do_mesmo_caderno_nao_se_misturam(self):
        async def _tudo():
            provas = (await server.list_provas_publico())["provas"]
            if len(provas) < 2:
                return None
            a, b = provas[0], provas[1]
            fa = await server.list_questoes_publico(
                limit=500, banca=a["banca"], ano=a["ano"], prova=a["prova"],
                numero_min=a["numero_min"], numero_max=a["numero_max"],
            )
            fb = await server.list_questoes_publico(
                limit=500, banca=b["banca"], ano=b["ano"], prova=b["prova"],
                numero_min=b["numero_min"], numero_max=b["numero_max"],
            )
            return fa, fb

        resultado = _run(_tudo())
        if resultado is None:
            return  # este ambiente só tem 1 bloco sincronizado — nada a comparar
        fa, fb = resultado
        ids_a = {it["item_id"] for it in fa["items"]}
        ids_b = {it["item_id"] for it in fb["items"]}
        assert ids_a.isdisjoint(ids_b)

    def test_itens_vem_ordenados_por_numero(self):
        r = _run(server.list_questoes_publico(limit=500))
        numeros = [it["fonte"]["numero"] for it in r["items"] if it["fonte"].get("numero") is not None]
        assert numeros == sorted(numeros)


class TestMinhasRespondidas:
    def test_formato_da_resposta_para_aluno_sem_historico(self):
        import firestore_routes as fr
        from models import User

        async def _chamar():
            u = User(email="ops@example.com", name="x", user_id="user_offline_teste_sem_historico")
            return await fr.minhas_respondidas(user=u)

        r = _run(_chamar())
        assert r == {"item_ids": []}
