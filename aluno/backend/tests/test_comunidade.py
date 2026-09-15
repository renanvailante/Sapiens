"""Mural de dúvidas: publicação, respostas, economia e moderação.

O foco não é o caminho feliz (publicar e responder é a parte fácil) — é o que
acontece quando alguém tenta abusar: votar em si mesmo, marcar a própria
resposta como a melhor, fabricar Sparks com contas-fantasma, ou derrubar o
conteúdo de um colega sozinho.
"""
from __future__ import annotations

import asyncio

import pytest

import comunidade
import engajamento_service


def roda(coro):
    return asyncio.run(coro)


@pytest.fixture
def mural(fake_db, monkeypatch):
    comunidade.set_db(fake_db)
    engajamento_service.set_db(fake_db)
    monkeypatch.setattr(engajamento_service, "_hoje", lambda: "2026-09-15")
    monkeypatch.setattr(comunidade.fs, "dia_local", lambda *a, **k: "2026-09-15")
    monkeypatch.setattr(
        comunidade.fs, "grant_sparks_evento",
        lambda uid, *, categoria, chave, amount, meta=None: {"ja_concedido": False, "sparks_ganhos": amount},
    )
    yield fake_db
    comunidade.set_db(None)
    engajamento_service.set_db(None)


def publica(area="Matemática", uid="autor", titulo="Não entendi essa função", corpo="Alguém explica o passo 3?"):
    return roda(comunidade.publicar_duvida(
        student_id=uid, autor_nome="Autor", area=area, titulo=titulo, corpo=corpo
    ))


class TestPublicar:
    def test_perguntar_nunca_custa_sparks(self, mural, monkeypatch):
        """Decisão de produto nº 1: cobrar de quem está travado num exercício
        é cobrar no pior momento possível e mata o mural na primeira semana."""
        def nao_pode_cobrar(*a, **k):
            raise AssertionError("publicar dúvida não pode debitar Sparks")

        monkeypatch.setattr(comunidade.fs, "deduct_sparks", nao_pode_cobrar)
        assert publica()["duvida_id"]

    def test_area_desconhecida_cai_em_outro(self, mural):
        assert publica(area="Astrologia")["area"] == "Outro"

    def test_publicar_da_xp(self, mural):
        publica()
        perfil = roda(mural.engajamento_perfil.find_one({"_id": "autor"}))
        assert perfil["xp_total"] == comunidade.engajamento_service.eng.XP_POR_ACAO["duvida_publicada"]


class TestResponder:
    def test_resposta_entra_na_thread_e_conta(self, mural):
        d = publica()
        r = roda(comunidade.responder(
            duvida_id=d["duvida_id"], student_id="ajudante", autor_nome="Bia", corpo="É a regra da cadeia."
        ))
        assert r["ok"] is True
        atual = roda(mural.comunidade_duvidas.find_one({"duvida_id": d["duvida_id"]}))
        assert atual["respostas"] == 1

    def test_nao_responde_duvida_removida(self, mural):
        d = publica()
        roda(comunidade.moderar(tipo="duvida", alvo_id=d["duvida_id"], acao="remover"))
        r = roda(comunidade.responder(
            duvida_id=d["duvida_id"], student_id="x", autor_nome="X", corpo="oi oi oi"
        ))
        assert r["ok"] is False


class TestVoto:
    def test_nao_vota_no_proprio_conteudo(self, mural):
        d = publica(uid="autor")
        r = roda(comunidade.votar(tipo="duvida", alvo_id=d["duvida_id"], uid="autor"))
        assert r["ok"] is False

    def test_um_voto_por_pessoa(self, mural):
        d = publica(uid="autor")
        primeiro = roda(comunidade.votar(tipo="duvida", alvo_id=d["duvida_id"], uid="outro"))
        segundo = roda(comunidade.votar(tipo="duvida", alvo_id=d["duvida_id"], uid="outro"))
        assert primeiro["ok"] is True
        assert segundo["ok"] is False
        atual = roda(mural.comunidade_duvidas.find_one({"duvida_id": d["duvida_id"]}))
        assert atual["votos"] == 1


class TestMelhorResposta:
    def _com_resposta(self, mural):
        d = publica(uid="autor")
        r = roda(comunidade.responder(
            duvida_id=d["duvida_id"], student_id="ajudante", autor_nome="Bia", corpo="Resposta boa aqui."
        ))
        return d["duvida_id"], r["resposta"]["resposta_id"]

    def test_so_o_autor_marca(self, mural):
        duvida_id, resposta_id = self._com_resposta(mural)
        r = roda(comunidade.marcar_melhor(duvida_id=duvida_id, resposta_id=resposta_id, uid="intruso"))
        assert r["ok"] is False

    def test_nao_marca_a_propria_resposta(self, mural):
        """Sem isto, duas contas do mesmo dono — ou uma só — imprimem Sparks."""
        d = publica(uid="autor")
        r = roda(comunidade.responder(
            duvida_id=d["duvida_id"], student_id="autor", autor_nome="Autor", corpo="me respondendo"
        ))
        saida = roda(comunidade.marcar_melhor(
            duvida_id=d["duvida_id"], resposta_id=r["resposta"]["resposta_id"], uid="autor"
        ))
        assert saida["ok"] is False

    def test_paga_o_autor_da_resposta(self, mural):
        duvida_id, resposta_id = self._com_resposta(mural)
        r = roda(comunidade.marcar_melhor(duvida_id=duvida_id, resposta_id=resposta_id, uid="autor"))
        assert r["ok"] is True
        assert r["sparks_para_o_autor"] == comunidade.SPARKS_MELHOR_RESPOSTA

    def test_marca_uma_vez_so(self, mural):
        duvida_id, resposta_id = self._com_resposta(mural)
        roda(comunidade.marcar_melhor(duvida_id=duvida_id, resposta_id=resposta_id, uid="autor"))
        segunda = roda(comunidade.marcar_melhor(duvida_id=duvida_id, resposta_id=resposta_id, uid="autor"))
        assert segunda["ok"] is False

    def test_teto_diario_de_sparks(self, mural):
        """Passado o teto, o XP continua (ajudar muita gente no mesmo dia não
        é abuso) mas o Spark para — é o que torna a fazenda de contas-fantasma
        mais trabalhosa do que estudar."""
        for i in range(comunidade.MAX_SPARKS_DIA + 1):
            d = publica(uid=f"autor{i}", titulo=f"Dúvida número {i} aqui")
            r = roda(comunidade.responder(
                duvida_id=d["duvida_id"], student_id="farm", autor_nome="Farm", corpo="resposta padrão"
            ))
            saida = roda(comunidade.marcar_melhor(
                duvida_id=d["duvida_id"], resposta_id=r["resposta"]["resposta_id"], uid=f"autor{i}"
            ))
            if i < comunidade.MAX_SPARKS_DIA:
                assert saida["sparks_para_o_autor"] == comunidade.SPARKS_MELHOR_RESPOSTA
            else:
                assert saida["sparks_para_o_autor"] == 0
                assert saida["limite_diario_atingido"] is True

        perfil = roda(mural.engajamento_perfil.find_one({"_id": "farm"}))
        assert perfil["respostas_uteis"] == comunidade.MAX_SPARKS_DIA + 1


class TestDestaque:
    def test_cobra_e_marca_o_prazo(self, mural, monkeypatch):
        monkeypatch.setattr(comunidade.fs, "deduct_sparks", lambda uid, amount: 200)
        d = publica(uid="autor")
        r = roda(comunidade.destacar(duvida_id=d["duvida_id"], uid="autor"))
        assert r["ok"] is True
        assert r["destacada_ate"] > comunidade._now_iso()

    def test_sem_saldo_diz_quanto_falta(self, mural, monkeypatch):
        def sem_saldo(uid, amount):
            raise comunidade.fs.InsufficientSparksError(5, amount)

        monkeypatch.setattr(comunidade.fs, "deduct_sparks", sem_saldo)
        d = publica(uid="autor")
        r = roda(comunidade.destacar(duvida_id=d["duvida_id"], uid="autor"))
        assert r["faltam"] == comunidade.CUSTO_DESTAQUE - 5

    def test_destaque_vencido_nao_fica_no_topo_para_sempre(self, mural, monkeypatch):
        """O aluno comprou 24h, não a eternidade. A ordenação compara
        `destacada_ate` com o instante de AGORA."""
        monkeypatch.setattr(comunidade.fs, "deduct_sparks", lambda uid, amount: 200)
        antiga = publica(uid="a1", titulo="Dúvida antiga destacada")
        roda(mural.comunidade_duvidas.update_one(
            {"duvida_id": antiga["duvida_id"]}, {"$set": {"destacada_ate": "2020-01-01T00:00:00+00:00"}}
        ))
        nova = publica(uid="a2", titulo="Dúvida nova sem destaque")

        lista = roda(comunidade.listar())
        assert lista["items"][0]["duvida_id"] == nova["duvida_id"]

    def test_destaque_valido_sobe_ao_topo(self, mural, monkeypatch):
        monkeypatch.setattr(comunidade.fs, "deduct_sparks", lambda uid, amount: 200)
        velha = publica(uid="a1", titulo="Primeira dúvida publicada")
        nova = publica(uid="a2", titulo="Segunda dúvida publicada")
        roda(comunidade.destacar(duvida_id=velha["duvida_id"], uid="a1"))

        lista = roda(comunidade.listar())
        assert lista["items"][0]["duvida_id"] == velha["duvida_id"]
        assert lista["items"][1]["duvida_id"] == nova["duvida_id"]


class TestModeracao:
    def test_uma_pessoa_sozinha_nao_derruba_conteudo(self, mural):
        """`$addToSet` conta gente DIFERENTE: cinco cliques da mesma pessoa
        são um reporte só."""
        d = publica(uid="autor")
        for _ in range(5):
            roda(comunidade.reportar(tipo="duvida", alvo_id=d["duvida_id"], uid="perseguidor", motivo="não gosto"))
        atual = roda(mural.comunidade_duvidas.find_one({"duvida_id": d["duvida_id"]}))
        assert atual["status"] == "publicada"

    def test_reportes_distintos_ocultam_ate_um_admin_olhar(self, mural):
        d = publica(uid="autor")
        for i in range(comunidade.REPORTES_PARA_OCULTAR):
            roda(comunidade.reportar(tipo="duvida", alvo_id=d["duvida_id"], uid=f"pessoa{i}", motivo="ofensivo"))
        atual = roda(mural.comunidade_duvidas.find_one({"duvida_id": d["duvida_id"]}))
        assert atual["status"] == "em_revisao"
        assert roda(comunidade.listar())["items"] == []

    def test_autor_continua_vendo_a_propria_duvida_em_revisao(self, mural):
        """Sumir sem explicação é o que faz a pessoa achar que o produto
        engoliu o texto dela."""
        d = publica(uid="autor")
        for i in range(comunidade.REPORTES_PARA_OCULTAR):
            roda(comunidade.reportar(tipo="duvida", alvo_id=d["duvida_id"], uid=f"p{i}", motivo="x"))
        minhas = roda(comunidade.listar(filtro="minhas", uid="autor"))
        assert [i["duvida_id"] for i in minhas["items"]] == [d["duvida_id"]]

    def test_restaurar_zera_os_reportes(self, mural):
        """Sem zerar, o próximo reporte sozinho derrubaria de novo o que o
        admin acabou de aprovar."""
        d = publica(uid="autor")
        for i in range(comunidade.REPORTES_PARA_OCULTAR):
            roda(comunidade.reportar(tipo="duvida", alvo_id=d["duvida_id"], uid=f"p{i}", motivo="x"))
        roda(comunidade.moderar(tipo="duvida", alvo_id=d["duvida_id"], acao="restaurar"))
        atual = roda(mural.comunidade_duvidas.find_one({"duvida_id": d["duvida_id"]}))
        assert atual["status"] == "publicada"
        assert atual["reportada_por"] == []

    def test_remover_guarda_o_documento(self, mural):
        """Apagar destruiria a prova de por que a decisão foi tomada."""
        d = publica(uid="autor")
        roda(comunidade.moderar(tipo="duvida", alvo_id=d["duvida_id"], acao="remover"))
        assert roda(mural.comunidade_duvidas.find_one({"duvida_id": d["duvida_id"]})) is not None
        assert roda(comunidade.listar())["items"] == []

    def test_fila_mostra_o_que_foi_reportado(self, mural):
        d = publica(uid="autor")
        roda(comunidade.reportar(tipo="duvida", alvo_id=d["duvida_id"], uid="p1", motivo="spam"))
        fila = roda(comunidade.fila_de_moderacao())
        assert len(fila["duvidas"]) == 1


class TestListagem:
    def test_filtro_sem_resposta(self, mural):
        sem = publica(uid="a1", titulo="Essa aqui ninguém respondeu")
        com = publica(uid="a2", titulo="Essa aqui alguém respondeu")
        roda(comunidade.responder(
            duvida_id=com["duvida_id"], student_id="b", autor_nome="B", corpo="resposta"
        ))
        lista = roda(comunidade.listar(filtro="sem_resposta"))
        assert [i["duvida_id"] for i in lista["items"]] == [sem["duvida_id"]]

    def test_filtro_por_area(self, mural):
        publica(area="Matemática", uid="a1", titulo="Dúvida de matemática aqui")
        publica(area="Redação", uid="a2", titulo="Dúvida de redação aqui")
        lista = roda(comunidade.listar(area="Redação"))
        assert len(lista["items"]) == 1
        assert lista["items"][0]["area"] == "Redação"

    def test_paginacao_existe_desde_o_primeiro_dia(self, mural):
        for i in range(5):
            publica(uid=f"a{i}", titulo=f"Dúvida de número {i} publicada")
        pagina = roda(comunidade.listar(limite=2, pular=2))
        assert len(pagina["items"]) == 2
        assert pagina["total"] == 5

    def test_nunca_vaza_quem_reportou(self, mural):
        d = publica(uid="autor")
        roda(comunidade.reportar(tipo="duvida", alvo_id=d["duvida_id"], uid="p1", motivo="x"))
        lista = roda(comunidade.listar())
        assert "reportada_por" not in lista["items"][0]
        detalhe = roda(comunidade.ler_duvida(d["duvida_id"], uid="qualquer"))
        assert "reportada_por" not in detalhe["duvida"]
