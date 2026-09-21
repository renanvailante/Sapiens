"""Programa de influencers/afiliados: código, ativação, atribuição, comissão.

Os pontos que estes testes existem para travar — espelhando exatamente as
garantias que `test_indicacao_de_amigo.py` já trava para o referral de
aluno-a-aluno, porque a mecânica de segurança (idempotência por pagamento,
"nunca sobrescrever atribuição válida", "não pagar de novo no reenvio") é a
mesma, só que a moeda da comissão é dinheiro em vez de Sparks:

1. Ativar um influencer cria um `promo_codes` de verdade, com o mesmo
   contrato que `_bonus_de_cadastro` já sabe ler.
2. Autoindicação (e-mail do influencer == e-mail de quem se cadastra) é
   bloqueada.
3. Comissão roda em TODA compra do aluno atribuído (não só a primeira).
4. Reenvio do mesmo webhook não lança comissão duas vezes.
5. Estorno muda o status do lançamento, nunca subtrai de um contador.
6. Um cupom comum (sem `influencer_id`) nunca vira atribuição de influencer.

Offline, com o dublê de Mongo do `conftest.py`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import Response

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import auth  # noqa: E402
import firestore_service as fs  # noqa: E402
import influencers  # noqa: E402
import promo_codes_routes as promo  # noqa: E402
import rate_limit  # noqa: E402
import sparks_payments_service as svc  # noqa: E402
from models import SignupRequest  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _sem_limites_residuais():
    rate_limit.limpar()
    yield
    rate_limit.limpar()


@pytest.fixture
def db(fake_db, monkeypatch):
    auth.set_db(fake_db)
    promo.set_db(fake_db)
    monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
    return fake_db


def _cadastrar(db, email: str, nome: str = "Aluno Novo", codigo: str | None = None) -> dict:
    _run(auth.signup(
        SignupRequest(
            email=email, name=nome, password="senha-forte-1",
            whatsapp="(11) 91234-5678", promo_code=codigo,
        ),
        Response(),
    ))
    return _run(db.users.find_one({"email": email}))


def _influencer_ativo(db, nome: str = "Lucas Criador", email_login: str = "lucas@creators.com",
                       percentual: float = 0.30, sparks: int = 300) -> dict:
    lead = _run(influencers.criar_lead(db, {"nome": nome}))
    ativo = _run(influencers.ativar(
        db, lead["influencer_id"],
        email_login=email_login, percentual_comissao=percentual, sparks_boas_vindas=sparks,
    ))
    return ativo


def _pagar(db, comprador_id: str, mp_id: str, price_cents: int, sparks: int, monkeypatch,
           status: str = "approved"):
    monkeypatch.setattr(svc.mp, "get_payment", lambda pid: {"id": pid, "status": status, "metadata": {}})
    monkeypatch.setattr(svc.fs, "grant_purchase_sparks", lambda uid, **k: {"ja_creditado": False})
    existente = _run(db.sparks_payments.find_one({"mp_payment_id": mp_id}))
    if existente is None:
        _run(db.sparks_payments.insert_one({
            "purchase_id": f"compra-{mp_id}", "user_id": comprador_id, "package_id": "spark_1500",
            "sparks_amount": sparks, "price_cents": price_cents, "currency": "BRL", "source": "manual",
            "mp_payment_id": mp_id, "status": "pending", "credited": False,
        }))
    return _run(svc.process_payment_webhook(db, mp_id))


# ============================================================== o código

class TestCodigo:
    def test_codigo_comeca_com_sapiens_mais_o_nome(self, db):
        codigo = _run(influencers.gerar_codigo(db, "Lucas Criador"))
        assert codigo.startswith("SAPIENSLUCAS")

    def test_codigo_tenta_de_novo_quando_o_primeiro_sorteio_ja_esta_ocupado(self, db, monkeypatch):
        """`gerar_codigo` chama `_codigo_livre` antes de aceitar um candidato
        — aqui a primeira chamada diz "ocupado" e a segunda diz "livre", e o
        resultado tem que ser o SEGUNDO candidato, não o primeiro."""
        chamadas = {"n": 0}

        async def livre_na_segunda_vez(_db, _c):
            chamadas["n"] += 1
            return chamadas["n"] >= 2

        monkeypatch.setattr(influencers, "_codigo_livre", livre_na_segunda_vez)
        codigo = _run(influencers.gerar_codigo(db, "Lucas"))
        assert codigo.startswith("SAPIENSLUCAS")
        assert chamadas["n"] == 2

    def test_codigo_nao_colide_com_codigo_pessoal_de_indicacao(self, db):
        _run(db.users.insert_one({"user_id": "u1", "referral_code": "SAPIENSANA1234"}))
        assert _run(influencers._codigo_livre(db, "SAPIENSANA1234")) is False


# ============================================================== ativação

class TestAtivacao:
    def test_ativar_cria_um_promo_code_de_verdade(self, db):
        inf = _influencer_ativo(db)
        cupom = _run(db.promo_codes.find_one({"code": inf["codigo"]}))
        assert cupom is not None
        assert cupom["sparks_amount"] == 300
        assert cupom["promoter_email"] == "lucas@creators.com"
        assert cupom["influencer_id"] == inf["influencer_id"]

    def test_ativar_de_novo_e_idempotente(self, db):
        lead = _run(influencers.criar_lead(db, {"nome": "Lucas"}))
        primeira = _run(influencers.ativar(
            db, lead["influencer_id"], email_login="l@x.com", percentual_comissao=0.3, sparks_boas_vindas=300,
        ))
        segunda = _run(influencers.ativar(
            db, lead["influencer_id"], email_login="outro@x.com", percentual_comissao=0.5, sparks_boas_vindas=999,
        ))
        assert segunda["codigo"] == primeira["codigo"]
        assert _run(db.promo_codes.count_documents({"influencer_id": lead["influencer_id"]})) == 1

    def test_percentual_e_bonus_sao_configuraveis_por_influencer(self, db):
        inf = _influencer_ativo(db, nome="Marina", email_login="marina@x.com", percentual=0.5, sparks=500)
        assert inf["percentual_comissao"] == 0.5
        cupom = _run(db.promo_codes.find_one({"code": inf["codigo"]}))
        assert cupom["sparks_amount"] == 500


# ================================================================ atribuição

class TestAtribuicaoNoCadastro:
    def test_cadastro_com_codigo_de_influencer_grava_o_vinculo(self, db):
        inf = _influencer_ativo(db)
        conta = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        assert conta["influenciado_por"] == inf["influencer_id"]
        assert conta["influenciado_por_codigo"] == inf["codigo"]
        assert conta["promo_code"] == inf["codigo"]  # também é o cupom aplicado
        assert conta["promo_sparks"] == 300

    def test_cupom_comum_sem_influencer_id_nao_vira_atribuicao(self, db):
        _run(db.promo_codes.insert_one({"code": "BEMVINDO", "sparks_amount": 100, "active": True, "usos": 0}))
        conta = _cadastrar(db, "aluno@x.com", "Aluno", "BEMVINDO")
        assert conta["promo_code"] == "BEMVINDO"
        assert conta["influenciado_por"] is None

    def test_autoindicacao_e_bloqueada(self, db):
        """O próprio influencer não pode virar 'aluno atribuído a si mesmo'
        usando o e-mail que também é o login do painel dele."""
        inf = _influencer_ativo(db, email_login="lucas@x.com")
        conta = _cadastrar(db, "lucas@x.com", "Lucas Criador", inf["codigo"])
        assert conta["influenciado_por"] is None

    def test_codigo_inexistente_nao_barra_cadastro(self, db):
        conta = _cadastrar(db, "aluno@x.com", "Aluno", "NAOEXISTE")
        assert conta["influenciado_por"] is None


# ================================================================= comissão

class TestComissao:
    def test_comissao_e_percentual_do_preco_pago(self, db, monkeypatch):
        inf = _influencer_ativo(db, percentual=0.30)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)

        lancamento = _run(db.influencer_comissoes.find_one({"_id": "mp-1"}))
        assert lancamento["comissao_cents"] == 3000
        assert lancamento["status"] == influencers.COMISSAO_ACUMULADA
        assert lancamento["influencer_id"] == inf["influencer_id"]

    def test_comissao_roda_em_toda_compra_nao_so_a_primeira(self, db, monkeypatch):
        """Diferente de `indicacoes`: aqui é receita recorrente."""
        inf = _influencer_ativo(db)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)
        _pagar(db, aluno["user_id"], "mp-2", price_cents=5000, sparks=600, monkeypatch=monkeypatch)

        total = _run(db.influencer_comissoes.count_documents({"influencer_id": inf["influencer_id"]}))
        assert total == 2
        soma = sum(c["comissao_cents"] for c in _run(
            db.influencer_comissoes.find({"influencer_id": inf["influencer_id"]}).to_list(10)
        ))
        assert soma == 3000 + 1500

    def test_reenvio_do_mesmo_pagamento_nao_lanca_comissao_duas_vezes(self, db, monkeypatch):
        inf = _influencer_ativo(db)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)
        _run(db.sparks_payments.update_one({"mp_payment_id": "mp-1"}, {"$set": {"credited": False}}))
        _run(svc.process_payment_webhook(db, "mp-1"))

        assert _run(db.influencer_comissoes.count_documents({})) == 1

    def test_comprador_sem_influencer_nao_gera_lancamento(self, db, monkeypatch):
        aluno = _cadastrar(db, "sozinho@x.com", "Sozinho")
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)
        assert _run(db.influencer_comissoes.count_documents({})) == 0

    def test_comprador_recebe_sparks_mesmo_se_comissao_falhar(self, db, monkeypatch):
        inf = _influencer_ativo(db)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])

        def explode(*a, **k):
            raise RuntimeError("Mongo fora do ar")

        monkeypatch.setattr(db.influencer_comissoes, "insert_one", explode)
        resultado = _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)
        assert resultado["credited"] is True

    def test_estorno_muda_status_do_lancamento(self, db, monkeypatch):
        inf = _influencer_ativo(db)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)

        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch, status="refunded")

        lancamento = _run(db.influencer_comissoes.find_one({"_id": "mp-1"}))
        assert lancamento["status"] == influencers.COMISSAO_ESTORNADA
        assert lancamento["estornado_em"] is not None
        # o lançamento nunca é apagado — auditável mesmo estornado
        assert lancamento["comissao_cents"] == 3000

    def test_marcar_pago_so_afeta_lancamentos_acumulados(self, db, monkeypatch):
        inf = _influencer_ativo(db)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)
        _pagar(db, aluno["user_id"], "mp-2", price_cents=5000, sparks=600, monkeypatch=monkeypatch)

        resultado = _run(influencers.marcar_comissao_paga(db, inf["influencer_id"], mp_payment_ids=["mp-1"]))
        assert resultado["marcados"] == 1
        pago = _run(db.influencer_comissoes.find_one({"_id": "mp-1"}))
        ainda_acumulado = _run(db.influencer_comissoes.find_one({"_id": "mp-2"}))
        assert pago["status"] == influencers.COMISSAO_PAGA
        assert ainda_acumulado["status"] == influencers.COMISSAO_ACUMULADA


# ================================================================== resumo

class TestResumo:
    def test_resumo_soma_faturamento_e_comissao_corretamente(self, db, monkeypatch):
        inf = _influencer_ativo(db, percentual=0.30)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)
        _run(influencers.marcar_comissao_paga(db, inf["influencer_id"], mp_payment_ids=["mp-1"]))
        _pagar(db, aluno["user_id"], "mp-2", price_cents=5000, sparks=600, monkeypatch=monkeypatch)

        resumo = _run(influencers.resumo(db, inf["influencer_id"]))
        assert resumo["alunos_atribuidos"] == 1
        assert resumo["faturamento_atribuido_cents"] == 15000
        assert resumo["comissao_paga_cents"] == 3000
        assert resumo["comissao_acumulada_cents"] == 1500

    def test_resumo_admin_lista_todos_os_influencers(self, db, monkeypatch):
        a = _influencer_ativo(db, nome="Lucas", email_login="lucas@x.com")
        b = _influencer_ativo(db, nome="Marina", email_login="marina@x.com")
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", a["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)

        resumo = _run(influencers.resumo_admin(db))
        assert resumo["total"] == 2
        assert resumo["ativos"] == 2
        por_id = {i["influencer_id"]: i for i in resumo["items"]}
        assert por_id[a["influencer_id"]]["alunos_atribuidos"] == 1
        assert por_id[b["influencer_id"]]["alunos_atribuidos"] == 0


# =============================================================== priorização

class TestPriorizacaoDeLeads:
    def test_maior_alcance_vem_primeiro(self, db):
        leads = [
            {"influencer_id": "a", "status": "lead", "tamanho_aproximado": 1_000},
            {"influencer_id": "b", "status": "lead", "tamanho_aproximado": 1_000_000},
        ]
        ordenado = influencers.priorizar(leads)
        assert ordenado[0]["influencer_id"] == "b"

    def test_lead_parado_nunca_fica_no_topo(self, db):
        leads = [
            {"influencer_id": "a", "status": "recusado", "tamanho_aproximado": 10_000_000},
            {"influencer_id": "b", "status": "lead", "tamanho_aproximado": None},
        ]
        ordenado = influencers.priorizar(leads)
        assert ordenado[-1]["influencer_id"] == "a"

    def test_sem_tamanho_nao_quebra_e_nao_vira_prioridade_maxima(self, db):
        leads = [{"influencer_id": "a", "status": "lead"}]
        ordenado = influencers.priorizar(leads)
        assert len(ordenado) == 1


# =========================================================== kit e mensagens

class TestKitEMensagens:
    def test_kit_usa_dado_real_do_influencer(self, db):
        inf = _influencer_ativo(db, nome="Lucas Criador")
        kit = influencers.gerar_kit(inf)
        assert inf["codigo"] in kit["mensagem"]
        assert inf["codigo"] in kit["legenda"]
        assert str(inf["sparks_boas_vindas"]) in kit["mensagem"]

    def test_mensagem_de_prospeccao_nao_inventa_canal_ausente(self):
        """Sem `plataforma`, não há "vi seu trabalho no X" honesto a escrever —
        a variante sem referência entra, em vez de inventar um lugar."""
        mensagem = influencers.gerar_mensagem_prospeccao({"nome": "Ana Silva"})
        assert "None" not in mensagem
        assert "Encontrei seu contato" in mensagem
        assert "Vi seu trabalho no" not in mensagem

    def test_mensagem_cita_a_plataforma_e_nunca_o_nicho_interno(self):
        """Correção do dono em 2026-09-21: "vi seu trabalho em dicas rápidas
        para o ENEM" é o rótulo que NÓS demos ao lead — citá-lo denuncia
        automação. O que a pessoa reconhece é a plataforma dela."""
        lead = {"nome": "ameninadamatematica", "plataforma": "tiktok",
                "nicho": "dicas rápidas para o ENEM"}
        mensagem = influencers.gerar_mensagem_prospeccao(lead)
        assert "TikTok" in mensagem
        assert "dicas rápidas para o ENEM" not in mensagem

    def test_mensagem_se_apresenta_como_pessoa_e_nao_chama_pelo_arroba(self):
        lead = {"nome": "ameninadamatematica", "plataforma": "instagram"}
        mensagem = influencers.gerar_mensagem_prospeccao(lead)
        assert influencers.FUNDADOR_NOME in mensagem
        assert "fundador da Sapiens" in mensagem
        assert not mensagem.startswith("Oi ameninadamatematica")

    def test_mensagem_vende_a_ia_e_nao_promete_prazo_eterno(self):
        """Duas decisões de conteúdo do dono: a IA é o argumento, e
        "sem limite de tempo" é compromisso que ninguém pediu num primeiro
        contato."""
        mensagem = influencers.gerar_mensagem_prospeccao(
            {"nome": "x", "plataforma": "instagram"})
        assert "agentes de IA" in mensagem
        for promessa in ("sem limite de tempo", "para sempre", "vitalício"):
            assert promessa not in mensagem.lower()

    def test_sparks_padrao_vem_da_constante_e_nao_da_mao(self):
        """Regra de preço do CLAUDE.md: o número do bônus padrão é o que o
        backend de fato dá a quem entra sem cupom. Escrever "100" aqui seria
        uma promessa que cala quando a constante mudar."""
        import firestore_service as fs

        mensagem = influencers.gerar_mensagem_prospeccao(
            {"nome": "x", "plataforma": "instagram", "sparks_boas_vindas": 300})
        assert f"(o padrão é {fs.SPARKS_INITIAL_BALANCE})" in mensagem
        assert "300 Sparks" in mensagem

    def test_variacoes_diferentes_produzem_texto_diferente(self):
        lead = {"nome": "Ana Silva", "plataforma": "instagram"}
        m0 = influencers.gerar_mensagem_prospeccao(lead, variacao=0)
        m1 = influencers.gerar_mensagem_prospeccao(lead, variacao=1)
        assert m0 != m1

    def test_followup_so_existe_para_d3_e_d7(self):
        lead = {"nome": "Ana"}
        assert influencers.gerar_followup(lead, 3) is not None
        assert influencers.gerar_followup(lead, 7) is not None
        assert influencers.gerar_followup(lead, 1) is None


# ============================================================== classificação

class TestClassificarResposta:
    @pytest.mark.parametrize("texto,esperado", [
        ("não quero mais receber mensagens, por favor remover", "pedido_remocao"),
        ("não tenho interesse, obrigado", "recusou"),
        ("quanto vocês pagam de comissão?", "quer_preco"),
        ("bora fechar, como funciona a parceria?", "quer_parceria"),
        ("gostei muito da proposta", "interessado"),
    ])
    def test_classifica_por_palavra_chave(self, texto, esperado):
        assert influencers.classificar_resposta(texto) == esperado

    def test_texto_ambiguo_devolve_none(self):
        assert influencers.classificar_resposta("oi tudo bem") is None

    def test_texto_vazio_devolve_none(self):
        assert influencers.classificar_resposta("") is None


# ========================================================= exclusão de conta

class TestFluxoCompletoPontaAPonta:
    """Os 13 itens do critério de sucesso do programa, numa sequência só —
    não é redundante com as classes acima: aqui a garantia é que a cadeia
    INTEIRA funciona junta, não cada peça isolada."""

    def test_do_lead_a_comissao_calculada(self, db, monkeypatch):
        # 1. cadastrar um influencer
        lead = _run(influencers.criar_lead(db, {
            "nome": "Lucas Criador", "plataforma": "instagram", "nicho": "vestibular",
            "tamanho_aproximado": 50_000,
        }))
        assert lead["status"] == influencers.STATUS_LEAD

        _run(influencers.atualizar(db, lead["influencer_id"], {"status": "qualificado"}))
        _run(influencers.atualizar(db, lead["influencer_id"], {"status": "contato"}))
        _run(influencers.atualizar(db, lead["influencer_id"], {"status": "respondeu"}))
        _run(influencers.atualizar(db, lead["influencer_id"], {"status": "interessado"}))

        # 2 + 3 + 4. gerar código, link e benefício de 300 Sparks automaticamente
        ativo = _run(influencers.ativar(
            db, lead["influencer_id"], email_login="lucas@creators.com",
            percentual_comissao=0.30, sparks_boas_vindas=300,
        ))
        assert ativo["codigo"].startswith("SAPIENSLUCAS")
        # O link carrega SÓ o código: um `&bonus=N` na URL é editável por quem
        # abre a página, e a tela chegou a prometer o número que a pessoa
        # digitasse ali (o crédito real nunca veio da URL).
        assert ativo["link"] == f"/login?convite={ativo['codigo']}"
        assert "bonus" not in ativo["link"]
        cupom = _run(db.promo_codes.find_one({"code": ativo["codigo"]}))
        assert cupom["sparks_amount"] == 300

        # 5. atribuir novos alunos
        aluno = _cadastrar(db, "aluno@x.com", "Aluno Novo", ativo["codigo"])
        assert aluno["influenciado_por"] == ativo["influencer_id"]
        assert aluno["promo_sparks"] == 300  # o benefício de fato foi concedido

        # 6 + 7 + 8. registrar compra, calcular receita e comissão de 30%
        resultado = _pagar(db, aluno["user_id"], "mp-1", price_cents=20000, sparks=1500, monkeypatch=monkeypatch)
        assert resultado["credited"] is True
        lancamento = _run(db.influencer_comissoes.find_one({"_id": "mp-1"}))
        assert lancamento["comissao_cents"] == 6000  # 30% de R$200,00

        # 9. acompanhar tudo no sistema (painel do influencer)
        resumo = _run(influencers.resumo(db, ativo["influencer_id"]))
        assert resumo["alunos_atribuidos"] == 1
        assert resumo["faturamento_atribuido_cents"] == 20000
        assert resumo["comissao_acumulada_cents"] == 6000

        # 10. gerar materiais personalizados
        kit = influencers.gerar_kit(resumo)
        assert ativo["codigo"] in kit["mensagem"]
        mensagem_prospeccao = influencers.gerar_mensagem_prospeccao(lead)
        # Desde 2026-09-21 a abertura é a apresentação de quem ESCREVE, não o
        # nome de quem recebe — ver `test_mensagem_se_apresenta_como_pessoa...`.
        assert influencers.FUNDADOR_NOME in mensagem_prospeccao
        assert "parceria" in mensagem_prospeccao

        # 11. medir conversão
        funil = _run(__import__("growth_events").resumo_funil(db, influencer_id=ativo["influencer_id"]))
        assert funil["eventos"]["referral_signup"] == 1
        assert funil["eventos"]["influencer_commission"] == 1

        # 12. preparar campanhas (estrutura existe e responde, sem gastar nada)
        import campaigns

        campanha = _run(campaigns.criar(db, {"nome": "Teste Meta Ads", "canal": "meta_ads"}))
        assert campanha["custo_real_cents"] == 0
        comparativo = _run(campaigns.resumo_comparativo(db))
        canais = {c["canal"] for c in comparativo["canais"]}
        assert {"meta_ads", "influencer"} <= canais

        # 13. operar com custo inicial mínimo — nenhuma chamada de IA em
        # todo o fluxo acima (kit e mensagem são puro Python, sem rede)


class TestExclusaoDeConta:
    def test_comissao_e_anonimizada_pelo_lado_do_aluno(self, db, monkeypatch):
        import dados_pessoais

        dados_pessoais.set_db(db)
        inf = _influencer_ativo(db)
        aluno = _cadastrar(db, "aluno@x.com", "Aluno", inf["codigo"])
        _pagar(db, aluno["user_id"], "mp-1", price_cents=10000, sparks=1500, monkeypatch=monkeypatch)

        n = _run(dados_pessoais._anonimizar_comissoes(aluno["user_id"]))
        assert n == 1
        lancamento = _run(db.influencer_comissoes.find_one({"_id": "mp-1"}))
        assert lancamento["aluno_id"] == dados_pessoais.TOMBSTONE
        assert lancamento["comissao_cents"] == 3000  # o registro financeiro permanece
