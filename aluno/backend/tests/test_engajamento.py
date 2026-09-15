"""Motor de engajamento: ofensiva, XP, missões, ligas — e a linha ética.

A última classe deste arquivo (`TestLinhaEtica`) não testa comportamento de
software: testa PROMESSAS. Cada teste lá corresponde a uma frase do cabeçalho
de `engajamento.py` sobre o que o produto se recusa a fazer com o aluno. São
justamente as regras que somem primeiro quando alguém precisa de mais
engajamento no fim do trimestre — e é por isso que elas têm teste.
"""
from __future__ import annotations

import asyncio

import pytest

import engajamento as eng
import engajamento_service as servico


def roda(coro):
    """`asyncio.run` por chamada — o padrão da casa (ver `test_cronograma.py`),
    em vez de pytest-asyncio."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Ofensiva
# ---------------------------------------------------------------------------

class TestOfensiva:
    def test_dias_seguidos_contam(self):
        o = eng.calcular_ofensiva(
            ["2026-09-15", "2026-09-14", "2026-09-13"], hoje="2026-09-15"
        )
        assert o.dias == 3
        assert o.estudou_hoje is True
        assert o.em_risco is False

    def test_nao_estudar_hoje_ainda_nao_quebra(self):
        """O dia não acabou. Zerar a sequência de quem vai estudar à noite
        seria o produto mentindo sobre o próprio relógio."""
        o = eng.calcular_ofensiva(["2026-09-14", "2026-09-13"], hoje="2026-09-15")
        assert o.dias == 2
        assert o.em_risco is True

    def test_faltar_um_dia_quebra_sem_congelador(self):
        o = eng.calcular_ofensiva(["2026-09-13", "2026-09-12"], hoje="2026-09-15")
        assert o.dias == 0
        assert o.congelar == ()

    def test_congelador_salva_a_sequencia(self):
        o = eng.calcular_ofensiva(
            ["2026-09-13", "2026-09-12"], hoje="2026-09-15", congeladores=1
        )
        assert o.dias == 2
        assert o.congelar == ("2026-09-14",)
        assert o.congeladores_restantes == 0

    def test_congelador_nao_e_gasto_quando_nao_salva_nada(self):
        """Buraco de seis dias com dois congeladores: a sequência quebra de
        qualquer jeito, e gastar os dois seria cobrar por nada."""
        o = eng.calcular_ofensiva(["2026-09-09"], hoje="2026-09-15", congeladores=2)
        assert o.dias == 0
        assert o.congelar == ()
        assert o.congeladores_restantes == 2

    def test_dia_congelado_liga_a_corrente_mas_nao_conta_como_estudo(self):
        """50 Sparks não podem virar um dia de estudo. O congelador atravessa
        o buraco; quem soma é só o dia em que houve resposta de verdade."""
        o = eng.calcular_ofensiva(
            ["2026-09-12", "2026-09-13", "2026-09-15"],
            hoje="2026-09-15",
            dias_congelados=["2026-09-14"],
        )
        assert o.dias == 3  # 12, 13 e 15 — o 14 ligou, não contou

    def test_recorde_sobrevive_a_quebra(self):
        o = eng.calcular_ofensiva(
            ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-15"],
            hoje="2026-09-15",
        )
        assert o.dias == 1
        assert o.recorde == 4

    def test_aluno_sem_nenhuma_resposta(self):
        o = eng.calcular_ofensiva([], hoje="2026-09-15")
        assert (o.dias, o.recorde, o.em_risco) == (0, 0, False)


# ---------------------------------------------------------------------------
# XP e nível
# ---------------------------------------------------------------------------

class TestNivel:
    def test_curva_e_crescente(self):
        limiares = [eng.xp_acumulado_do_nivel(n) for n in range(1, 30)]
        assert limiares == sorted(limiares)
        assert limiares[0] == 0

    @pytest.mark.parametrize("xp,esperado", [(0, 1), (99, 1), (100, 2), (999, 4), (1000, 5), (4500, 10)])
    def test_nivel_de_xp(self, xp, esperado):
        assert eng.nivel_de_xp(xp)["nivel"] == esperado

    def test_progresso_dentro_do_nivel_fecha_a_conta(self):
        n = eng.nivel_de_xp(150)
        assert n["xp_no_nivel"] + n["xp_para_o_proximo"] == n["xp_do_nivel"]
        assert 0 <= n["percentual"] <= 100

    def test_xp_negativo_ou_ausente_nao_quebra(self):
        assert eng.nivel_de_xp(-5)["nivel"] == 1
        assert eng.nivel_de_xp(None)["nivel"] == 1


# ---------------------------------------------------------------------------
# Missões
# ---------------------------------------------------------------------------

class TestMissoes:
    def test_sempre_tres(self):
        assert len(eng.missoes_do_dia("aluno1", "2026-09-15")) == 3

    def test_estaveis_no_mesmo_dia_para_o_mesmo_aluno(self):
        """Recarregar a página não pode sortear missão nova — senão o aluno
        aprende a recarregar até cair a mais fácil."""
        a = [m["id"] for m in eng.missoes_do_dia("aluno1", "2026-09-15")]
        b = [m["id"] for m in eng.missoes_do_dia("aluno1", "2026-09-15")]
        assert a == b

    def test_estaveis_entre_processos(self):
        """O sorteio usa `hashlib`, não o `hash()` embutido — que é
        aleatorizado por processo e faria as missões trocarem a cada restart
        do servidor e divergirem entre duas instâncias."""
        import hashlib

        semente = int(hashlib.sha256("aluno1:2026-09-15".encode()).hexdigest()[:8], 16)
        assert semente == int(hashlib.sha256("aluno1:2026-09-15".encode()).hexdigest()[:8], 16)
        ids = [m["id"] for m in eng.missoes_do_dia("aluno1", "2026-09-15")]
        assert ids == ["acertar8", "treino", "cronograma"]  # valor fixo, não "o que der"

    def test_nunca_repete_missao_no_mesmo_dia(self):
        """Os trilhos compartilham missões; sem descarte, o aluno via "Acerte
        8 questões" duas vezes e ganhava só duas missões de fato."""
        for uid in ("aluno1", "aluno2", "aluno3", "x", "y", "zzz"):
            ids = [m["id"] for m in eng.missoes_do_dia(uid, "2026-09-15")]
            assert len(set(ids)) == 3, ids

    def test_progresso_vem_dos_contadores(self):
        missoes = eng.missoes_do_dia("aluno1", "2026-09-15", {"questoes": 15, "acertos": 8})
        acertar = next(m for m in missoes if m["id"] == "acertar8")
        assert acertar["progresso"] == 8
        assert acertar["concluida"] is True

    def test_progresso_nunca_passa_do_alvo(self):
        missoes = eng.missoes_do_dia("aluno1", "2026-09-15", {"questoes": 900, "acertos": 900})
        assert all(m["progresso"] <= m["alvo"] for m in missoes)

    def test_toda_missao_do_catalogo_anuncia_o_premio(self):
        assert all(m.sparks > 0 for m in eng.CATALOGO_MISSOES)


# ---------------------------------------------------------------------------
# Ligas
# ---------------------------------------------------------------------------

class TestLigas:
    def test_top_sobe(self):
        assert eng.promover("bronze", posicao=1, total_no_grupo=30) == "prata"

    def test_ultimos_caem_em_grupo_cheio(self):
        assert eng.promover("prata", posicao=30, total_no_grupo=30) == "bronze"

    def test_grupo_pequeno_nao_rebaixa_ninguem(self):
        """Ficar em último entre três pessoas é um fato sobre o tamanho da
        base, não sobre o aluno."""
        assert eng.promover("prata", posicao=3, total_no_grupo=3) == "prata"

    def test_diamante_nao_sobe_mais_e_bronze_nao_desce(self):
        assert eng.promover("diamante", posicao=1, total_no_grupo=30) == "diamante"
        assert eng.promover("bronze", posicao=30, total_no_grupo=30) == "bronze"

    def test_semana_iso_e_o_domingo_de_fechamento(self):
        assert eng.semana_de("2026-09-15") == eng.semana_de("2026-09-20")
        assert eng.fim_da_semana("2026-W38") == "2026-09-20"

    def test_segunda_comeca_semana_nova(self):
        assert eng.semana_de("2026-09-20") != eng.semana_de("2026-09-21")


# ---------------------------------------------------------------------------
# Serviço (Mongo dublê)
# ---------------------------------------------------------------------------

@pytest.fixture
def servico_com_db(fake_db, monkeypatch):
    servico.set_db(fake_db)
    monkeypatch.setattr(servico, "_hoje", lambda: "2026-09-15")
    yield fake_db
    servico.set_db(None)


class TestRegistrarAcao:
    def test_soma_xp_e_contadores(self, servico_com_db):
        roda(servico.registrar_acao(
            "u1", ["questao_respondida", "questao_correta"], contadores={"questoes": 1, "acertos": 1}
        ))
        perfil = roda(servico_com_db.engajamento_perfil.find_one({"_id": "u1"}))
        dia = roda(servico_com_db.engajamento_dia.find_one({"_id": "u1:2026-09-15"}))
        assert perfil["xp_total"] == 15
        assert dia["contadores"]["questoes"] == 1

    def test_alimenta_a_liga_da_semana(self, servico_com_db):
        roda(servico.registrar_acao("u1", ["redacao_corrigida"], nome="Ana"))
        linha = roda(servico_com_db.liga_semana.find_one({"_id": "u1:2026-W38"}))
        assert linha["pontos"] == 120
        assert linha["nome"] == "Ana"

    def test_chave_unica_paga_uma_vez_so(self, servico_com_db):
        """Marcar, desmarcar e marcar de novo um bloco do cronograma não pode
        virar botão de fabricar XP."""
        primeiro = roda(servico.registrar_acao("u1", ["bloco_cronograma"], chave_unica="bloco:x"))
        segundo = roda(servico.registrar_acao("u1", ["bloco_cronograma"], chave_unica="bloco:x"))
        assert primeiro["xp"] == 25
        assert segundo["xp"] == 0
        perfil = roda(servico_com_db.engajamento_perfil.find_one({"_id": "u1"}))
        assert perfil["xp_total"] == 25

    def test_falha_do_mongo_nao_propaga(self, servico_com_db, monkeypatch):
        """Perder XP é aborrecimento; derrubar o registro da resposta é perder
        o estudo do aluno. `registrar_acao` engole as próprias falhas."""

        async def explode(*a, **k):
            raise RuntimeError("mongo caiu")

        monkeypatch.setattr(servico_com_db.engajamento_dia, "update_one", explode)
        assert roda(servico.registrar_acao("u1", ["questao_respondida"], contadores={"questoes": 1})) == {"xp": 0}


class TestEstado:
    def test_ofensiva_vem_do_firestore_nao_do_mongo(self, servico_com_db, monkeypatch):
        """A sequência mede ESTUDO. Ela deriva de `agregado.dias_ativos`, que
        só cresce com resposta real — nunca de um contador que o próprio motor
        de engajamento pudesse incrementar sozinho."""
        monkeypatch.setattr(
            servico.fs, "ler_agregado",
            lambda uid: {"dias_ativos": ["2026-09-15", "2026-09-14"], "total_respostas": 40},
        )
        e = roda(servico.estado("u1"))
        assert e["ofensiva"]["dias"] == 2
        assert e["total_respostas"] == 40

    def test_cota_estourada_nao_zera_a_ofensiva_no_banco(self, servico_com_db, monkeypatch):
        """Firestore fora do ar mostra 0 nesta requisição e volta sozinho na
        próxima — mas NADA é gravado a partir de uma leitura que falhou."""

        def explode(uid):
            raise RuntimeError("cota estourada")

        monkeypatch.setattr(servico.fs, "ler_agregado", explode)
        e = roda(servico.estado("u1"))
        assert e["ofensiva"]["dias"] == 0
        assert roda(servico_com_db.engajamento_perfil.find_one({"_id": "u1"})) is None

    def test_liga_vazia_e_exibida_vazia(self, servico_com_db, monkeypatch):
        """Sem bots. Se ninguém mais está na divisão, o ranking mostra só quem
        está lá de verdade."""
        monkeypatch.setattr(servico.fs, "ler_agregado", lambda uid: {"dias_ativos": [], "total_respostas": 0})
        e = roda(servico.estado("u1"))
        assert e["liga"]["tabela"] == []
        assert e["liga"]["total"] == 0

    def test_ranking_ordena_por_pontos(self, servico_com_db, monkeypatch):
        monkeypatch.setattr(servico.fs, "ler_agregado", lambda uid: {"dias_ativos": [], "total_respostas": 0})
        for uid, pontos, nome in [("u1", 50, "Ana"), ("u2", 300, "Bia"), ("u3", 120, "Caio")]:
            roda(servico_com_db.liga_semana.insert_one(
                {"_id": f"{uid}:2026-W38", "uid": uid, "semana": "2026-W38",
                 "liga_id": "bronze", "pontos": pontos, "nome": nome}
            ))
        e = roda(servico.estado("u1"))
        assert [l["nome"] for l in e["liga"]["tabela"]] == ["Bia", "Caio", "Ana"]
        assert e["liga"]["minha_posicao"] == 3
        assert next(l for l in e["liga"]["tabela"] if l["voce"])["nome"] == "Ana"


class TestResgatarMissao:
    def test_missao_nao_concluida_nao_paga(self, servico_com_db):
        ids = [m["id"] for m in eng.missoes_do_dia("u1", "2026-09-15")]
        r = roda(servico.resgatar_missao("u1", ids[0]))
        assert r["ok"] is False

    def test_paga_uma_vez_so(self, servico_com_db, monkeypatch):
        concessoes: list[str] = []

        def conceder(uid, *, categoria, chave, amount, meta=None):
            if chave in concessoes:
                return {"ja_concedido": True, "sparks_ganhos": 0}
            concessoes.append(chave)
            return {"ja_concedido": False, "sparks_ganhos": amount}

        monkeypatch.setattr(servico.fs, "grant_sparks_evento", conceder)
        monkeypatch.setattr(servico.fs, "read_sparks_balance", lambda uid: 100)

        roda(servico_com_db.engajamento_dia.insert_one(
            {"_id": "u1:2026-09-15", "uid": "u1", "dia": "2026-09-15",
             "contadores": {"questoes": 99, "acertos": 99, "respostas_comunidade": 9}}
        ))
        alvo = eng.missoes_do_dia("u1", "2026-09-15", {"questoes": 99, "acertos": 99})[0]

        primeiro = roda(servico.resgatar_missao("u1", alvo["id"]))
        segundo = roda(servico.resgatar_missao("u1", alvo["id"]))
        assert primeiro["ok"] is True and primeiro["sparks_ganhos"] > 0
        assert segundo["ok"] is False
        assert len(concessoes) == 1


class TestCongelador:
    def test_sem_saldo_devolve_quanto_falta(self, servico_com_db, monkeypatch):
        def sem_saldo(uid, amount):
            raise servico.fs.InsufficientSparksError(10, amount)

        monkeypatch.setattr(servico.fs, "deduct_sparks", sem_saldo)
        r = roda(servico.comprar_congelador("u1"))
        assert r["ok"] is False
        assert r["faltam"] == eng.CUSTO_CONGELADOR - 10

    def test_respeita_o_teto(self, servico_com_db, monkeypatch):
        monkeypatch.setattr(servico.fs, "deduct_sparks", lambda uid, amount: 500)
        roda(servico_com_db.engajamento_perfil.insert_one(
            {"_id": "u1", "uid": "u1", "congeladores": eng.MAX_CONGELADORES}
        ))
        r = roda(servico.comprar_congelador("u1"))
        assert r["ok"] is False
        assert "máximo" in r["motivo"]

    def test_devolve_sparks_se_o_item_nao_for_creditado(self, servico_com_db, monkeypatch):
        devolvido = {}
        monkeypatch.setattr(servico.fs, "deduct_sparks", lambda uid, amount: 450)
        monkeypatch.setattr(
            servico.fs, "refund_sparks",
            lambda uid, amount: devolvido.setdefault("amount", amount) and 500 or 500,
        )

        async def explode(*a, **k):
            raise RuntimeError("mongo caiu")

        monkeypatch.setattr(servico_com_db.engajamento_perfil, "update_one", explode)
        r = roda(servico.comprar_congelador("u1"))
        assert r["ok"] is False
        assert devolvido["amount"] == eng.CUSTO_CONGELADOR


# ---------------------------------------------------------------------------
# A linha ética
# ---------------------------------------------------------------------------

class TestLinhaEtica:
    """Cada teste aqui corresponde a uma recusa declarada no cabeçalho de
    `engajamento.py`. Não são detalhes de implementação: são a diferença entre
    um produto que puxa o aluno de volta e um que o manipula."""

    def test_xp_nao_se_compra(self, servico_com_db, monkeypatch):
        """Sparks compram conveniência (congelador, destaque). Nunca
        progresso: no dia em que nível virar mercadoria, ele para de dizer o
        que o aluno aprendeu.

        Teste de COMPORTAMENTO, não de texto-fonte: gasta Sparks de verdade e
        confere que o XP não se moveu."""
        monkeypatch.setattr(servico.fs, "deduct_sparks", lambda uid, amount: 500)
        roda(servico.registrar_acao("u1", ["questao_respondida"]))
        antes = roda(servico_com_db.engajamento_perfil.find_one({"_id": "u1"}))["xp_total"]

        assert roda(servico.comprar_congelador("u1"))["ok"] is True

        depois = roda(servico_com_db.engajamento_perfil.find_one({"_id": "u1"}))["xp_total"]
        assert depois == antes

    def test_nenhuma_missao_e_cumprida_gastando_sparks(self):
        """Missão é trabalho. Todo contador que mede missão é produzido por
        uma ação de estudo, nunca por um débito."""
        contadores = {m.contador for m in eng.CATALOGO_MISSOES}
        assert contadores <= {"questoes", "acertos", "revisoes", "blocos", "treino", "respostas_comunidade"}

    def test_recompensa_de_missao_e_fixa_e_anunciada(self):
        """Sem razão variável: a recompensa é a mesma toda vez e aparece antes
        de o aluno começar. Razão variável é a mecânica de caça-níquel."""
        for m in eng.missoes_do_dia("u1", "2026-09-15"):
            assert isinstance(m["sparks"], int) and m["sparks"] > 0
            assert isinstance(m["xp"], int) and m["xp"] > 0

    def test_preco_do_congelador_nao_reage_ao_desespero(self, servico_com_db, monkeypatch):
        """O mesmo preço para quem tem 3 dias e para quem tem 300 em risco.
        Preço que sobe com a perda iminente é extorsão com outro nome.

        Também de comportamento: cobra duas vezes com ofensivas MUITO
        diferentes e confere que o valor debitado é idêntico."""
        cobrado: list[int] = []
        monkeypatch.setattr(
            servico.fs, "deduct_sparks", lambda uid, amount: cobrado.append(amount) or 500
        )
        monkeypatch.setattr(
            servico.fs, "ler_agregado",
            lambda uid: {"dias_ativos": ["2026-09-15"], "total_respostas": 1},
        )
        roda(servico.comprar_congelador("novato"))

        longa = [f"2026-{m:02d}-{d:02d}" for m in (8, 9) for d in range(1, 16)]
        monkeypatch.setattr(
            servico.fs, "ler_agregado",
            lambda uid: {"dias_ativos": longa, "total_respostas": 900},
        )
        roda(servico.comprar_congelador("veterano"))

        assert cobrado == [eng.CUSTO_CONGELADOR, eng.CUSTO_CONGELADOR]

    def test_contagem_do_enem_some_quando_nao_ha_prova(self):
        """Nada de urgência inventada: passadas as duas datas, a contagem
        desaparece até o calendário do ano seguinte entrar no código."""
        assert eng.dias_para_o_enem("2027-01-01") is None

    def test_semana_visual_nunca_inventa_atividade(self):
        semana = servico._semana_visual(["2026-09-15"], [], "2026-09-15")
        assert sum(1 for d in semana if d["ativo"]) == 1
        assert len(semana) == 7
        assert semana[-1]["hoje"] is True
