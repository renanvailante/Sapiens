"""Rotas de `/redacao` — chamadas diretas às funções da rota (sem servidor
HTTP nem TestClient, mesmo estilo offline do resto do repo). Gemini e
Firestore são dublês; Mongo é o dublê de `conftest.py`.

O foco destes testes é a garantia que o dinheiro do aluno depende: **nunca
cobrar sem entregar, nunca cobrar duas vezes pela mesma entrega**.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import ai_service  # noqa: E402
import firestore_service as fs  # noqa: E402
import redacao_routes as routes  # noqa: E402
from models import User  # noqa: E402

TEXTO = (
    "A valorização das comunidades tradicionais no Brasil é um desafio persistente. "
    "Embora a Constituição assegure direitos territoriais e culturais a indígenas e "
    "quilombolas, a efetivação dessas garantias esbarra em entraves históricos.\n\n"
    "Em primeiro lugar, a invisibilidade cultural perpetua estereótipos. Dessa forma, a "
    "ausência de representação qualificada nos meios de comunicação contribui para que "
    "demandas legítimas sejam tratadas como assunto secundário pelo poder público.\n\n"
    "Além disso, a morosidade na demarcação de terras agrava o quadro. Consequentemente, "
    "famílias inteiras vivem sob ameaça de despejo, o que compromete a transmissão de "
    "saberes ancestrais entre gerações.\n\n"
    "Portanto, cabe ao Ministério dos Povos Indígenas ampliar a demarcação de territórios, "
    "por meio de editais permanentes, a fim de garantir segurança jurídica a essas "
    "comunidades tradicionais."
)
TEMA = "Desafios para a valorização de comunidades e povos tradicionais no Brasil"


def _run(coro):
    return asyncio.run(coro)


def _user(uid: str = "user-1") -> User:
    return User(user_id=uid, email=f"{uid}@exemplo.com", name="Aluno")


def _payload(chave: str = "chave-de-teste-1", **kwargs) -> routes.CorrecaoRequest:
    dados = {"texto": TEXTO, "tema_frase": TEMA, "idempotency_key": chave}
    dados.update(kwargs)
    return routes.CorrecaoRequest(**dados)


class CarteiraFake:
    """Dublê de `firestore_service` só para os Sparks: guarda saldo por uid e
    conta quantas vezes cada operação foi chamada — é a contagem que prova a
    idempotência, não o saldo final (um débito seguido de reembolso deixa o
    mesmo saldo de nunca ter cobrado)."""

    def __init__(self, saldo_inicial: int = 1000):
        self.saldos: dict[str, int] = {}
        self.inicial = saldo_inicial
        self.debitos: list[tuple[str, int]] = []
        self.reembolsos: list[tuple[str, int]] = []

    def instalar(self, monkeypatch):
        monkeypatch.setattr(fs, "ensure_sparks_balance", self.ensure)
        monkeypatch.setattr(fs, "deduct_sparks", self.deduct)
        monkeypatch.setattr(fs, "refund_sparks", self.refund)
        monkeypatch.setattr(fs, "read_sparks_balance", self.read)
        return self

    def ensure(self, uid: str) -> int:
        return self.saldos.setdefault(uid, self.inicial)

    def read(self, uid: str) -> int:
        return self.saldos.setdefault(uid, self.inicial)

    def deduct(self, uid: str, amount: int) -> int:
        saldo = self.saldos.setdefault(uid, self.inicial)
        if saldo < amount:
            raise fs.InsufficientSparksError(saldo, amount)
        self.saldos[uid] = saldo - amount
        self.debitos.append((uid, amount))
        return self.saldos[uid]

    def refund(self, uid: str, amount: int) -> int:
        self.saldos[uid] = self.saldos.setdefault(uid, self.inicial) + amount
        self.reembolsos.append((uid, amount))
        return self.saldos[uid]


@pytest.fixture
def carteira(monkeypatch) -> CarteiraFake:
    return CarteiraFake().instalar(monkeypatch)


FEEDBACK_OK = {
    "abertura": "Sua redação alcançou uma nota consistente e o texto se sustenta do começo ao fim.",
    "o_que_ficou_bom": ["A tese aparece já no primeiro parágrafo, o que orienta a leitura."],
    "o_que_ficou_ruim": ["O segundo argumento fica sem dado que o sustente."],
    "onde_melhorar": [{"titulo": "Ancorar o segundo argumento", "texto": "Traga um dado concreto."}],
    "principais_perdas": [{"competencia": "Competência III", "motivo": "Argumento sem sustentação."}],
    "fechamento": "Na próxima, escreva o repertório antes do parágrafo.",
}


# ---------------------------------------------------------------- correção


def test_texto_curto_e_rejeitado_antes_de_cobrar(fake_db, carteira):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.submeter_redacao(_payload(texto="curto demais"), user=_user()))
    assert exc.value.status_code == 422
    assert carteira.debitos == []


def test_sem_tema_e_rejeitado_antes_de_cobrar(fake_db, carteira):
    routes.set_db(fake_db)
    with pytest.raises(HTTPException) as exc:
        _run(routes.submeter_redacao(_payload(tema_frase="   "), user=_user()))
    assert exc.value.status_code == 422
    assert carteira.debitos == []


def test_correcao_cobra_uma_vez_e_devolve_as_cinco_competencias(fake_db, carteira):
    routes.set_db(fake_db)
    resposta = _run(routes.submeter_redacao(_payload(), user=_user()))

    assert carteira.debitos == [("user-1", routes.CORRECAO_COST)]
    assert carteira.reembolsos == []
    assert resposta["custo_cobrado"] == routes.CORRECAO_COST
    assert resposta["sparks_balance"] == 1000 - routes.CORRECAO_COST

    avaliacao = resposta["avaliacao"]
    ids = [c["id"] for c in avaliacao["competencias"]]
    assert ids == ["COMP-I", "COMP-II", "COMP-III", "COMP-IV", "COMP-V"]
    assert all(isinstance(c["nivel_pontos"], int) for c in avaliacao["competencias"])
    assert avaliacao["nota_total"] == sum(c["nivel_pontos"] for c in avaliacao["competencias"])
    assert avaliacao["nota_total"] > 0


def test_correcao_nao_chama_llm_nenhuma(fake_db, carteira, monkeypatch):
    """O caminho da nota é 100% local. Qualquer chamada ao Gemini aqui é
    regressão de custo, não detalhe de implementação."""
    routes.set_db(fake_db)

    async def _explode(*a, **k):
        raise AssertionError("a correção não pode chamar o Gemini")

    monkeypatch.setattr(ai_service, "generate_json", _explode)
    monkeypatch.setattr(ai_service, "generate_json_resiliente", _explode)

    resposta = _run(routes.submeter_redacao(_payload(), user=_user()))
    assert resposta["avaliacao"]["itens_escalonados_llm"] == []


def test_mesma_chave_nao_cobra_duas_vezes(fake_db, carteira):
    """Duplo clique / retry do axios: a segunda chamada devolve o MESMO
    resultado e não encosta no saldo."""
    routes.set_db(fake_db)
    primeira = _run(routes.submeter_redacao(_payload("k-repetida"), user=_user()))
    segunda = _run(routes.submeter_redacao(_payload("k-repetida"), user=_user()))

    assert carteira.debitos == [("user-1", routes.CORRECAO_COST)]
    assert segunda["custo_cobrado"] == 0
    assert segunda["redacao"]["redacao_id"] == primeira["redacao"]["redacao_id"]
    assert segunda["avaliacao"]["nota_total"] == primeira["avaliacao"]["nota_total"]
    assert len(fake_db.redacoes.docs) == 1


def test_chave_nova_cobra_de_novo(fake_db, carteira):
    routes.set_db(fake_db)
    _run(routes.submeter_redacao(_payload("chave-um-1"), user=_user()))
    _run(routes.submeter_redacao(_payload("chave-dois-2"), user=_user()))
    assert carteira.debitos == [("user-1", routes.CORRECAO_COST)] * 2


def test_mesma_chave_de_outro_usuario_nao_colide(fake_db, carteira):
    """A chave é do cliente e pode repetir entre alunos; o dono do documento
    de cobrança é `user:chave`, nunca a chave sozinha."""
    routes.set_db(fake_db)
    _run(routes.submeter_redacao(_payload("chave-mesma"), user=_user("user-1")))
    _run(routes.submeter_redacao(_payload("chave-mesma"), user=_user("user-2")))
    assert carteira.debitos == [("user-1", routes.CORRECAO_COST), ("user-2", routes.CORRECAO_COST)]
    assert len(fake_db.redacoes.docs) == 2


def test_falha_na_correcao_devolve_os_sparks_e_libera_a_chave(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)

    async def _quebra(*a, **k):
        raise RuntimeError("corretor quebrado")

    monkeypatch.setattr(routes.service, "corrigir_redacao", _quebra)
    with pytest.raises(HTTPException) as exc:
        _run(routes.submeter_redacao(_payload("chave-falha"), user=_user()))
    assert exc.value.status_code == 503
    assert carteira.debitos == [("user-1", routes.CORRECAO_COST)]
    assert carteira.reembolsos == [("user-1", routes.CORRECAO_COST)]
    assert carteira.saldos["user-1"] == 1000
    assert fake_db.redacao_cobrancas.docs == []  # chave liberada para nova tentativa


def test_saldo_insuficiente_nao_queima_a_chave(fake_db, monkeypatch):
    routes.set_db(fake_db)
    carteira = CarteiraFake(saldo_inicial=10).instalar(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _run(routes.submeter_redacao(_payload("chave-pobre"), user=_user()))
    assert exc.value.status_code == 402
    assert fake_db.redacao_cobrancas.docs == []

    carteira.saldos["user-1"] = 1000
    resposta = _run(routes.submeter_redacao(_payload("chave-pobre"), user=_user()))
    assert resposta["custo_cobrado"] == routes.CORRECAO_COST


def test_redacao_de_outro_usuario_nao_e_visivel(fake_db, carteira):
    routes.set_db(fake_db)
    resposta = _run(routes.submeter_redacao(_payload(), user=_user("user-1")))
    with pytest.raises(HTTPException) as exc:
        _run(routes.obter_avaliacao(resposta["redacao"]["redacao_id"], user=_user("user-2")))
    assert exc.value.status_code == 404


def test_historico_lista_so_do_proprio_usuario(fake_db, carteira):
    routes.set_db(fake_db)
    _run(routes.submeter_redacao(_payload("chave-aaa"), user=_user("user-1")))
    _run(routes.submeter_redacao(_payload("chave-bbb"), user=_user("user-2")))
    historico = _run(routes.historico_redacoes(user=_user("user-1")))
    assert historico["count"] == 1
    assert historico["items"][0]["redacao"]["user_id"] == "user-1"
    assert historico["items"][0]["tem_feedback"] is False


# ---------------------------------------------------------------- feedback


def _corrigir(fake_db, uid="user-1", chave="chave-feedback") -> str:
    return _run(routes.submeter_redacao(_payload(chave), user=_user(uid)))["redacao"]["redacao_id"]


def _mock_llm(monkeypatch, resultado=FEEDBACK_OK, chamadas=None):
    async def _fake(system, prompt, **kwargs):
        if chamadas is not None:
            chamadas.append(prompt)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    monkeypatch.setattr(ai_service, "generate_json_resiliente", _fake)


def test_feedback_cobra_uma_vez_e_devolve_as_secoes(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    redacao_id = _corrigir(fake_db)
    carteira.debitos.clear()
    _mock_llm(monkeypatch)

    resposta = _run(routes.gerar_feedback(redacao_id, user=_user()))
    assert carteira.debitos == [("user-1", routes.FEEDBACK_COST)]
    assert resposta["custo_cobrado"] == routes.FEEDBACK_COST
    for chave in ("abertura", "o_que_ficou_bom", "o_que_ficou_ruim", "onde_melhorar", "principais_perdas"):
        assert resposta["feedback"][chave]


def test_segundo_feedback_da_mesma_redacao_e_gratis(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    redacao_id = _corrigir(fake_db)
    carteira.debitos.clear()
    chamadas: list[str] = []
    _mock_llm(monkeypatch, chamadas=chamadas)

    primeira = _run(routes.gerar_feedback(redacao_id, user=_user()))
    segunda = _run(routes.gerar_feedback(redacao_id, user=_user()))

    assert carteira.debitos == [("user-1", routes.FEEDBACK_COST)]
    assert len(chamadas) == 1  # o Gemini foi chamado UMA vez
    assert segunda["custo_cobrado"] == 0
    assert segunda["cache"] is True
    assert segunda["feedback"] == primeira["feedback"]


def test_feedback_nao_manda_o_canon_no_prompt(fake_db, carteira, monkeypatch):
    """O prompt leva o texto do aluno, o tema e as notas — não as rubricas
    oficiais, que são dezenas de milhares de caracteres de token pago."""
    routes.set_db(fake_db)
    redacao_id = _corrigir(fake_db)
    chamadas: list[str] = []
    _mock_llm(monkeypatch, chamadas=chamadas)
    _run(routes.gerar_feedback(redacao_id, user=_user()))

    prompt = chamadas[0]
    assert TEMA in prompt
    assert "COMP-I" not in prompt  # competências entram pelo nome, não pelo código
    assert len(prompt) < len(TEXTO) + 4000


def test_feedback_com_resposta_malformada_devolve_os_sparks(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    redacao_id = _corrigir(fake_db)
    carteira.debitos.clear()
    _mock_llm(monkeypatch, resultado={"abertura": "curta"})

    with pytest.raises(HTTPException) as exc:
        _run(routes.gerar_feedback(redacao_id, user=_user()))
    assert exc.value.status_code == 503
    assert carteira.reembolsos == [("user-1", routes.FEEDBACK_COST)]
    assert carteira.saldos["user-1"] == 1000 - routes.CORRECAO_COST
    assert fake_db.redacao_feedbacks.docs == []


def test_feedback_falho_pode_ser_tentado_de_novo(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    redacao_id = _corrigir(fake_db)
    _mock_llm(monkeypatch, resultado=RuntimeError("gemini fora do ar"))
    with pytest.raises(HTTPException):
        _run(routes.gerar_feedback(redacao_id, user=_user()))

    carteira.debitos.clear()
    _mock_llm(monkeypatch)
    resposta = _run(routes.gerar_feedback(redacao_id, user=_user()))
    assert resposta["custo_cobrado"] == routes.FEEDBACK_COST
    assert carteira.debitos == [("user-1", routes.FEEDBACK_COST)]


def test_feedback_de_redacao_alheia_e_404(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    redacao_id = _corrigir(fake_db, uid="user-1")
    _mock_llm(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _run(routes.gerar_feedback(redacao_id, user=_user("user-2")))
    assert exc.value.status_code == 404
    assert carteira.reembolsos == []


def test_get_feedback_nao_cobra(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    redacao_id = _corrigir(fake_db)
    _mock_llm(monkeypatch)
    _run(routes.gerar_feedback(redacao_id, user=_user()))
    carteira.debitos.clear()

    lido = _run(routes.obter_feedback(redacao_id, user=_user()))
    assert lido["feedback"]["abertura"]
    assert carteira.debitos == []


# ------------------------------------------------- a coletânea de temas
#
# O catálogo de temas é constante de módulo: nenhuma ida ao banco, nenhuma ao
# Firestore. O que estes testes travam é o contrato com a tela e a regra que o
# resto do repo já segue — preço não mora em conteúdo.

from redacao import temas as temas_mod  # noqa: E402


def test_a_coletanea_sai_inteira_e_agrupada():
    resposta = _run(routes.listar_temas(_user()))
    ids = [t["tema_id"] for t in resposta["temas"]]
    assert ids == [t.tema_id for t in temas_mod.TEMAS]
    # Todo tema aparece em exatamente um eixo, e nenhum eixo vem vazio.
    dos_eixos = [tid for e in resposta["eixos"] for tid in e["temas"]]
    assert sorted(dos_eixos) == sorted(ids)
    assert all(e["temas"] for e in resposta["eixos"])


def test_todo_tema_tem_proposta_e_textos_motivadores():
    """Um tema sem frase não serve de proposta, e sem motivadores não é
    coletânea — é um título. Os dois são o produto."""
    for t in temas_mod.listar():
        assert t["frase"].strip(), t["tema_id"]
        assert len(t["textos_motivadores"]) >= 2, t["tema_id"]
        for m in t["textos_motivadores"]:
            assert m["rotulo"] and m["fonte"] and len(m["texto"]) > 80


def test_nenhum_tema_fala_de_preco():
    """A mesma regra que o validador de `cursos_conteudo` impõe ao conteúdo
    dos cursos: preço é decisão de produto e mora no código que cobra. Um tema
    que cite Spark viraria promessa de preço no ar."""
    proibidas = ("spark", "r$", "custa", "preço", "preco")
    for t in temas_mod.listar():
        corpo = " ".join(
            [t["titulo"], t["frase"], t["resumo"]]
            + [m["texto"] for m in t["textos_motivadores"]]
        ).lower()
        assert not any(p in corpo for p in proibidas), t["tema_id"]


def test_o_tema_escolhido_nao_atalha_a_correcao(fake_db, carteira):
    """Escrever sobre um tema da coletânea custa exatamente o mesmo, e passa
    pelo mesmo corretor, que um tema digitado à mão."""
    routes.set_db(fake_db)
    tema = temas_mod.listar()[0]
    resposta = _run(routes.submeter_redacao(
        _payload(tema_frase=tema["frase"],
                 textos_motivadores=[m["texto"] for m in tema["textos_motivadores"]]),
        user=_user(),
    ))
    assert carteira.debitos == [("user-1", routes.CORRECAO_COST)]
    assert len(resposta["avaliacao"]["competencias"]) == 5


# ------------------------------------------------- digitalizar a redação
#
# A foto vale Sparks porque é uma chamada de VISÃO ao Gemini. O que precisa ser
# verdade: cobra uma vez por foto, NÃO corrige nada e devolve o dinheiro em
# todo caminho que não entrega texto.

_IMAGEM = "data:image/jpeg;base64," + ("A" * 200)


def _ocr_fake(resultado):
    async def _f(_imagem):
        return resultado
    return _f


def test_digitalizar_devolve_o_texto_e_cobra_uma_vez(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "ocr_redacao", _ocr_fake(
        {"texto": "A juventude brasileira enfrenta.", "linhas": 28, "legivel": True, "observacao": ""},
    ))
    resposta = _run(routes.digitalizar(
        routes.DigitalizarRequest(imagem_base64=_IMAGEM, idempotency_key="foto-aaaa-1"),
        user=_user(),
    ))
    assert resposta["texto"] == "A juventude brasileira enfrenta."
    assert resposta["linhas"] == 28
    assert carteira.debitos == [("user-1", routes.DIGITALIZACAO_COST)]
    assert carteira.reembolsos == []


def test_digitalizar_nao_cria_redacao_nem_avaliacao(fake_db, carteira, monkeypatch):
    """Digitalizar é uma compra; corrigir é outra. Se esta rota gravasse uma
    redação, o aluno pagaria 25 e teria consumido a de 120 sem pedir."""
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "ocr_redacao", _ocr_fake(
        {"texto": "Texto reconhecido.", "linhas": 20, "legivel": True, "observacao": ""},
    ))
    _run(routes.digitalizar(
        routes.DigitalizarRequest(imagem_base64=_IMAGEM, idempotency_key="foto-aaaa-2"),
        user=_user(),
    ))
    assert _run(fake_db.redacoes.count_documents({})) == 0
    assert _run(fake_db.redacao_avaliacoes.count_documents({})) == 0


def test_mesma_foto_reenviada_nao_cobra_de_novo(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "ocr_redacao", _ocr_fake(
        {"texto": "Transcrição.", "linhas": 12, "legivel": True, "observacao": ""},
    ))
    pedido = routes.DigitalizarRequest(imagem_base64=_IMAGEM, idempotency_key="foto-aaaa-3")
    primeira = _run(routes.digitalizar(pedido, user=_user()))
    segunda = _run(routes.digitalizar(pedido, user=_user()))
    assert segunda["texto"] == primeira["texto"]
    assert segunda["cobrado"] == 0
    assert carteira.debitos == [("user-1", routes.DIGITALIZACAO_COST)]


def test_foto_ilegivel_devolve_os_sparks(fake_db, carteira, monkeypatch):
    """Foto tremida é erro do aluno; cobrar por ela é erro do produto — e sem
    o reembolso, tentar de novo custaria de novo."""
    routes.set_db(fake_db)
    monkeypatch.setattr(ai_service, "ocr_redacao", _ocr_fake(
        {"texto": "", "linhas": None, "legivel": False, "observacao": "Foto escura demais."},
    ))
    with pytest.raises(HTTPException) as exc:
        _run(routes.digitalizar(
            routes.DigitalizarRequest(imagem_base64=_IMAGEM, idempotency_key="foto-aaaa-4"),
            user=_user(),
        ))
    assert exc.value.status_code == 422
    assert "escura" in exc.value.detail
    assert carteira.debitos == [("user-1", routes.DIGITALIZACAO_COST)]
    assert carteira.reembolsos == [("user-1", routes.DIGITALIZACAO_COST)]


def test_falha_do_modelo_devolve_os_sparks(fake_db, carteira, monkeypatch):
    routes.set_db(fake_db)

    async def _explode(_imagem):
        raise RuntimeError("Gemini fora do ar")

    monkeypatch.setattr(ai_service, "ocr_redacao", _explode)
    with pytest.raises(HTTPException) as exc:
        _run(routes.digitalizar(
            routes.DigitalizarRequest(imagem_base64=_IMAGEM, idempotency_key="foto-aaaa-5"),
            user=_user(),
        ))
    assert exc.value.status_code == 503
    assert carteira.reembolsos == [("user-1", routes.DIGITALIZACAO_COST)]


def test_imagem_grande_demais_e_recusada_antes_de_cobrar(fake_db, carteira):
    routes.set_db(fake_db)
    gigante = "data:image/png;base64," + ("A" * (routes.DIGITALIZACAO_MAX_BYTES + 1))
    with pytest.raises(HTTPException) as exc:
        _run(routes.digitalizar(
            routes.DigitalizarRequest(imagem_base64=gigante, idempotency_key="foto-aaaa-6"),
            user=_user(),
        ))
    assert exc.value.status_code == 413
    assert carteira.debitos == []


def test_os_tres_precos_da_redacao_estao_na_rota_de_precos():
    precos = _run(routes.precos(_user()))
    assert precos["custo_correcao"] == routes.CORRECAO_COST
    assert precos["custo_feedback"] == routes.FEEDBACK_COST
    assert precos["custo_digitalizacao"] == routes.DIGITALIZACAO_COST
    # A digitalização é a mais barata das três, e precisa continuar sendo: ela
    # não avalia nada, só poupa o aluno de digitar.
    assert precos["custo_digitalizacao"] < precos["custo_feedback"] < precos["custo_correcao"]
