"""O cronograma e o motor de prioridade do ENEM.

O que estes testes travam não é a interface — é a promessa que a feature faz:

  * o horário de um bloco de estudo NUNCA cai em cima de um compromisso;
  * a ordem do que estudar sai de peso na prova x lacuna medida, e não da
    ordem em que os dados chegaram;
  * o aluno sem histórico nenhum recebe uma semana dominada por Matemática e
    Redação, que é onde o ponto está;
  * o modelo de linguagem não consegue mover bloco, mesmo mandando.
"""
from __future__ import annotations

from datetime import date

import pytest

import cronograma as cg
import prioridade_enem as pe


# ---------------------------------------------------------------------------
# Semana
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dia,esperado", [
    ("2026-09-12", "2026-09-07"),   # sexta -> segunda da mesma semana
    ("2026-09-07", "2026-09-07"),   # a própria segunda
    ("2026-09-13", "2026-09-07"),   # domingo ainda é a semana que começou dia 7
    ("2026-09-14", "2026-09-14"),   # segunda seguinte já é outra semana
])
def test_semana_comeca_na_segunda(dia, esperado):
    assert cg.segunda_da_semana(date.fromisoformat(dia)) == esperado


def test_horario_invalido_nao_vira_compromisso():
    with pytest.raises(ValueError):
        cg.hhmm_para_minutos("24:00")
    with pytest.raises(ValueError):
        cg.normalizar_compromisso({"titulo": "Aula", "dia": 0, "inicio": "10:00", "fim": "09:00"})
    with pytest.raises(ValueError):
        cg.normalizar_compromisso({"titulo": "Aula", "dia": 9, "inicio": "08:00", "fim": "09:00"})


def test_compromisso_datado_so_aparece_na_semana_dele():
    prova = cg.normalizar_compromisso({
        "titulo": "Prova de química", "data": "2026-09-17", "inicio": "08:00", "fim": "10:00", "tipo": "prova",
    })
    rotina = cg.normalizar_compromisso({"titulo": "Inglês", "dia": 1, "inicio": "19:00", "fim": "20:00"})
    desta = cg.compromissos_da_semana([prova, rotina], "2026-09-14")
    outra = cg.compromissos_da_semana([prova, rotina], "2026-09-21")
    assert {c["titulo"] for c in desta} == {"Prova de química", "Inglês"}
    # A rotina reaparece toda semana; o evento datado não.
    assert {c["titulo"] for c in outra} == {"Inglês"}


# ---------------------------------------------------------------------------
# A promessa central: estudo nunca cai em cima de compromisso
# ---------------------------------------------------------------------------


def _minutos(bloco):
    return cg.hhmm_para_minutos(bloco["inicio"]), cg.hhmm_para_minutos(bloco["fim"])


def test_nenhum_slot_invade_compromisso():
    compromissos = [
        cg.normalizar_compromisso({"titulo": "Escola", "dia": d, "inicio": "07:00", "fim": "12:30"})
        for d in range(5)
    ] + [cg.normalizar_compromisso({"titulo": "Trabalho", "dia": 5, "inicio": "09:00", "fim": "18:00"})]

    slots = cg.slots_livres(compromissos, {}, "2026-09-07")
    assert slots
    ocupados = cg.compromissos_da_semana(compromissos, "2026-09-07")
    for s in slots:
        si, sf = _minutos(s)
        for c in ocupados:
            if c["dia"] != s["dia"]:
                continue
            ci, cf = _minutos(c)
            assert sf <= ci or si >= cf, f"{s} invade {c}"


def test_compromissos_sobrepostos_nao_criam_janela_fantasma():
    """Aula 8-12 e monitoria 11-13 se sobrepõem. Antes da fusão dos
    intervalos, a subtração produzia uma janela livre invertida (12 -> 11) e o
    cronograma marcava estudo dentro da aula."""
    compromissos = [
        cg.normalizar_compromisso({"titulo": "Aula", "dia": 0, "inicio": "08:00", "fim": "12:00"}),
        cg.normalizar_compromisso({"titulo": "Monitoria", "dia": 0, "inicio": "11:00", "fim": "13:00"}),
    ]
    livres = cg.janelas_livres_do_dia(
        cg.compromissos_da_semana(compromissos, "2026-09-07"),
        cg.hhmm_para_minutos("07:00"), cg.hhmm_para_minutos("22:00"),
    )
    assert all(fim > inicio for inicio, fim in livres)
    assert livres == [(7 * 60, 8 * 60), (13 * 60, 22 * 60)]


def test_dia_de_folga_nao_recebe_bloco():
    slots = cg.slots_livres([], {"dias_de_folga": [5, 6]}, "2026-09-07")
    assert {s["dia"] for s in slots}.isdisjoint({5, 6})


def test_semana_sem_dia_livre_e_recusada_com_mensagem():
    with pytest.raises(ValueError):
        cg.normalizar_preferencias({"dias_de_folga": [0, 1, 2, 3, 4, 5, 6]})


# ---------------------------------------------------------------------------
# Prioridade: peso na prova x lacuna medida
# ---------------------------------------------------------------------------


def test_aluno_novo_comeca_por_matematica_e_redacao():
    """Sem histórico nenhum, a ordem é o peso na prova — e é assim que tem de
    ser: um cronograma vazio (ou aleatório) é a pior resposta possível para
    quem acabou de entrar."""
    topo = [l["chave"] for l in pe.ranking()][:2]
    assert set(topo) == {"matematica", "redacao"}


def test_lacuna_medida_supera_peso_quando_a_evidencia_e_grande():
    """Linguagens pesa metade de Matemática. Com 10% de acerto medido em 40
    questões contra 90% em 40, a lacuna medida tem de virar o jogo — senão o
    peso vira dogma e o diagnóstico do aluno não serve para nada."""
    linhas = pe.ranking({
        "matematica": {"respondidas": 40, "acertos": 36},
        "linguagens": {"respondidas": 40, "acertos": 4},
    })
    ordem = [l["chave"] for l in linhas]
    assert ordem.index("linguagens") < ordem.index("matematica")


def test_amostra_curta_nao_apaga_o_peso_da_frente():
    """Piso de confiança: 4 questões de Matemática com 25% de acerto ainda
    rendem mais que Biologia sem medida nenhuma. Sem o piso, começar a medir
    rebaixava a área — punindo o aluno por ter respondido."""
    linhas = {l["chave"]: l for l in pe.ranking({"matematica": {"respondidas": 4, "acertos": 1}})}
    assert linhas["matematica"]["rendimento"] > linhas["biologia"]["rendimento"]
    assert linhas["matematica"]["estado"] == "amostra_curta"


def test_educacao_fisica_nao_e_fisica():
    assert pe.classificar_disciplina("Educação Física") == "linguagens"
    assert pe.classificar_disciplina("FÍSICA") == "fisica"
    assert pe.classificar_disciplina("Ciências da Natureza e suas Tecnologias") == "natureza"
    assert pe.classificar_disciplina("Xadrez avançado") is None


def test_guarda_chuva_de_natureza_some_quando_nao_tem_medida():
    """Sem isto, o aluno novo via quatro frentes de Ciências da Natureza
    empatadas — a mesma coisa escrita de quatro jeitos ocupando metade da
    semana."""
    chaves = {l["chave"] for l in pe.ranking()}
    assert "natureza" not in chaves
    com_medida = {l["chave"] for l in pe.ranking({"natureza": {"respondidas": 10, "acertos": 5}})}
    assert "natureza" in com_medida


# ---------------------------------------------------------------------------
# Alocação
# ---------------------------------------------------------------------------


def _semana_cheia(**kwargs):
    compromissos = [
        cg.normalizar_compromisso({"titulo": "Escola", "dia": d, "inicio": "07:00", "fim": "12:30"})
        for d in range(5)
    ]
    slots = cg.slots_livres(compromissos, {}, "2026-09-07")
    return compromissos, slots, cg.alocar(slots, pe.ranking(), **kwargs)


def test_revisao_marcada_pega_o_primeiro_horario():
    _, _, plano = _semana_cheia(revisoes=[{"processo_nome": "Comparar grandezas", "motivo": "Reteste hoje."}])
    primeiro = plano["blocos"][0]
    assert primeiro["tipo"] == "revisao"
    assert primeiro["rota"] == "/revisoes"


def test_redacao_entra_na_semana_de_quem_nunca_escreveu():
    _, _, plano = _semana_cheia()
    assert any(b["tipo"] == "redacao" for b in plano["blocos"])


def test_nenhuma_frente_toma_a_semana_inteira():
    """Teto por frente. Um aluno com lacuna gigante em Matemática recebia sete
    dias de Matemática e parava de abrir o app na quarta."""
    linhas = pe.ranking({"matematica": {"respondidas": 50, "acertos": 2}})
    compromissos = []
    slots = cg.slots_livres(compromissos, {}, "2026-09-07")
    plano = cg.alocar(slots, linhas)
    questoes = [b for b in plano["blocos"] if b["tipo"] == "questoes"]
    de_matematica = [b for b in questoes if b["frente"] == "matematica"]
    assert questoes
    assert len(de_matematica) <= round(len(questoes) * cg.TETO_POR_FRENTE) + 1
    assert len({b["frente"] for b in questoes}) >= 3


def test_todo_bloco_tem_saida():
    """Contrato herdado dos cards de dificuldade: nada que aponta uma tarefa
    morre em si mesmo — todo bloco leva a uma tela onde ela é feita."""
    _, _, plano = _semana_cheia(
        revisoes=[{"processo_nome": "Ler gráfico", "motivo": "Reteste."}],
        habilidades_fracas=[{"hab_id": "HAB-07", "nome": "Ler gráfico", "percentual_acerto": 30, "respondidas": 9}],
    )
    assert plano["blocos"]
    for b in plano["blocos"]:
        assert b.get("rota"), f"bloco sem saída: {b}"
        assert b.get("titulo")


def test_alocacao_e_deterministica():
    a = _semana_cheia()[2]
    b = _semana_cheia()[2]
    chave = lambda p: [(x["dia"], x["inicio"], x["tipo"], x.get("frente")) for x in p["blocos"]]
    assert chave(a) == chave(b)


def test_maior_resto_nao_perde_nem_inventa_vaga():
    for total in (0, 1, 5, 17, 40):
        cotas = cg._maior_resto([0.6, 0.21, 0.21, 0.15], total)
        assert sum(cotas) == total


def test_sem_horario_livre_devolve_semana_vazia_sem_estourar():
    lotado = [
        cg.normalizar_compromisso({"titulo": "Trabalho", "dia": d, "inicio": "07:00", "fim": "22:00"})
        for d in range(7)
    ]
    slots = cg.slots_livres(lotado, {"dias_de_folga": []}, "2026-09-07")
    plano = cg.alocar(slots, pe.ranking())
    assert plano["blocos"] == []
    assert "Ajuste a janela" in cg.resumo_deterministico([], [], pe.ranking())


# ---------------------------------------------------------------------------
# O que o modelo NÃO pode fazer
# ---------------------------------------------------------------------------


def test_mentis_nao_consegue_mover_bloco():
    """A trava estrutural da feature: o modelo devolve dia, horário, tipo e
    rota junto do texto — e nada disso é aplicado. Se este teste cair, a
    Mentis passa a poder marcar estudo em cima da aula do aluno."""
    _, _, plano = _semana_cheia()
    original = plano["blocos"][0]
    blocos, reescritos = cg.aplicar_enriquecimento(plano["blocos"], {
        "blocos": [{
            "indice": 0,
            "titulo": "Maratona de madrugada",
            "detalhe": "Estude a noite inteira.",
            "dia": 6, "inicio": "03:00", "fim": "06:00",
            "tipo": "prova", "rota": "https://exemplo.invalido", "hab_id": "HAB-99",
        }],
    })
    assert reescritos == 1
    assert blocos[0]["titulo"] == "Maratona de madrugada"
    for campo in ("dia", "inicio", "fim", "tipo", "rota"):
        assert blocos[0][campo] == original[campo]


def test_enriquecimento_vazio_e_detectavel():
    """Zero reescritos é o sinal que a rota usa para devolver os Sparks e
    servir a semana determinística mesmo assim."""
    _, _, plano = _semana_cheia()
    _, reescritos = cg.aplicar_enriquecimento(plano["blocos"], {"blocos": "não é lista"})
    assert reescritos == 0


def test_compromisso_inventado_pelo_modelo_e_descartado():
    validos = cg.validar_compromissos_do_modelo({
        "compromissos": [
            {"titulo": "Aula de inglês", "dia": 1, "inicio": "19:00", "fim": "20:30", "tipo": "aula"},
            {"titulo": "Impossível", "dia": 9, "inicio": "19:00", "fim": "20:30"},
            {"titulo": "Invertido", "dia": 2, "inicio": "20:00", "fim": "19:00"},
            {"titulo": "", "dia": 3, "inicio": "08:00", "fim": "09:00"},
            "nem é um objeto",
        ],
    }, semana_iso="2026-09-07")
    assert [c["titulo"] for c in validos] == ["Aula de inglês"]
    assert validos[0]["origem"] == "chat"


def test_resposta_sem_o_campo_esperado_levanta():
    with pytest.raises(ValueError):
        cg.validar_compromissos_do_modelo({"qualquer": "coisa"}, semana_iso="2026-09-07")


# ---------------------------------------------------------------------------
# Importação de agenda externa
# ---------------------------------------------------------------------------

_ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:aula-ingles
SUMMARY:Aula de inglês\\, turma B
DTSTART;TZID=America/Sao_Paulo:20260908T190000
DTEND;TZID=America/Sao_Paulo:20260908T203000
RRULE:FREQ=WEEKLY;BYDAY=TU
END:VEVENT
BEGIN:VEVENT
UID:prova-bio
SUMMARY:Prova de Biologia
DTSTART:20260910T130000Z
DTEND:20260910T150000Z
END:VEVENT
BEGIN:VEVENT
UID:fora-da-semana
SUMMARY:Casamento
DTSTART;TZID=America/Sao_Paulo:20261225T160000
DTEND;TZID=America/Sao_Paulo:20261225T230000
END:VEVENT
END:VCALENDAR"""


def _tz():
    from zoneinfo import ZoneInfo
    return ZoneInfo("America/Sao_Paulo")


def test_ics_vira_compromisso_com_tipo_e_recorrencia():
    eventos = cg.eventos_do_ics(_ICS, _tz())
    compromissos = cg.compromissos_de_eventos(eventos, "2026-09-07")
    por_titulo = {c["titulo"]: c for c in compromissos}

    # Evento semanal vira RECORRENTE: gravá-lo datado faria a semana seguinte
    # nascer achando que a terça está livre.
    ingles = por_titulo["Aula de inglês, turma B"]
    assert ingles["data"] is None and ingles["dia"] == 1 and ingles["tipo"] == "aula"

    # UTC convertido para o fuso do aluno: 13:00Z é 10:00 em São Paulo.
    bio = por_titulo["Prova de Biologia"]
    assert bio["inicio"] == "10:00" and bio["tipo"] == "prova" and bio["data"] == "2026-09-10"

    # Evento de outra semana não entra.
    assert "Casamento" not in por_titulo


def test_reimportar_atualiza_em_vez_de_duplicar():
    eventos = cg.eventos_do_ics(_ICS, _tz())
    primeira = cg.compromissos_de_eventos(eventos, "2026-09-07")
    manual = cg.normalizar_compromisso({"titulo": "Academia", "dia": 3, "inicio": "18:00", "fim": "19:00"})

    atuais, criados, _ = cg.mesclar_compromissos([manual], primeira)
    assert criados == len(primeira)
    id_antes = next(c["id"] for c in atuais if c.get("externo_id") == "aula-ingles")

    segunda = cg.compromissos_de_eventos(eventos, "2026-09-07")
    depois, criados2, atualizados = cg.mesclar_compromissos(atuais, segunda)
    assert criados2 == 0 and atualizados == len(segunda)
    assert len(depois) == len(atuais)
    # O id interno sobrevive: a tela pode ter o bloco aberto na hora.
    assert next(c["id"] for c in depois if c.get("externo_id") == "aula-ingles") == id_antes
    # E o que o aluno digitou à mão não é tocado pela importação.
    assert any(c["titulo"] == "Academia" and c["origem"] == "manual" for c in depois)


def test_evento_do_google_vira_o_mesmo_formato():
    cru = cg.normalizar_evento_google({
        "id": "g1", "summary": "Estágio",
        "start": {"dateTime": "2026-09-09T14:00:00-03:00"},
        "end": {"dateTime": "2026-09-09T18:00:00-03:00"},
        "location": "Centro",
    })
    compromissos = cg.compromissos_de_eventos([cru], "2026-09-07", origem="google")
    assert compromissos[0]["inicio"] == "14:00"
    assert compromissos[0]["tipo"] == "trabalho"
    assert compromissos[0]["origem"] == "google"


def test_evento_quebrado_nao_derruba_a_importacao_inteira():
    eventos = cg.eventos_do_ics(_ICS, _tz())
    eventos.insert(0, {"titulo": "Sem início", "inicio": None})
    assert len(cg.compromissos_de_eventos(eventos, "2026-09-07")) == 2


# ---------------------------------------------------------------------------
# As rotas, de ponta a ponta (Mongo, Firestore e Gemini dublados)
# ---------------------------------------------------------------------------
#
# `asyncio.run` por chamada, e não pytest-asyncio: é o padrão da casa
# (`test_mentis.py`, `test_redacao_routes.py`) e funciona porque os dublês são
# de memória — nenhum deles guarda referência a um loop de eventos.

import asyncio  # noqa: E402

import cronograma_routes as cr  # noqa: E402
import firestore_service as fs  # noqa: E402
from models import User  # noqa: E402

_ALUNO = User(user_id="U-cron", email="aluno@exemplo.com", name="Joana")


class _Carteira:
    """Carteira em memória com a interface que `cronograma_routes` usa."""

    def __init__(self, saldo=1000):
        self.saldo = saldo
        self.debitos: list[int] = []
        self.reembolsos: list[int] = []

    def instalar(self, monkeypatch):
        monkeypatch.setattr(fs, "ensure_sparks_balance", lambda uid: self.saldo)
        monkeypatch.setattr(fs, "read_sparks_balance", lambda uid: self.saldo)
        monkeypatch.setattr(fs, "ensure_student_profile", lambda *a, **k: True)
        monkeypatch.setattr(fs, "deduct_sparks", self._debitar)
        monkeypatch.setattr(fs, "refund_sparks", self._reembolsar)
        monkeypatch.setattr(fs, "ler_treino_stats", lambda uid: {})
        return self

    def _debitar(self, uid, quanto):
        if self.saldo < quanto:
            raise fs.InsufficientSparksError(balance=self.saldo, needed=quanto)
        self.saldo -= quanto
        self.debitos.append(quanto)
        return self.saldo

    def _reembolsar(self, uid, quanto):
        self.saldo += quanto
        self.reembolsos.append(quanto)
        return self.saldo


@pytest.fixture
def rotas(fake_db, monkeypatch):
    """Rotas prontas para chamar: banco falso, carteira falsa, sem Firestore e
    sem Gemini. Quem precisar do modelo o injeta no próprio teste."""
    cr.set_db(fake_db)
    carteira = _Carteira().instalar(monkeypatch)

    async def _diagnostico_vazio(uid):
        return {"por_disciplina": {}}

    monkeypatch.setattr(cr.annotation_service, "compute_diagnostico_real", _diagnostico_vazio)
    monkeypatch.setattr(cr.revisao_service, "fila", lambda uid, limite=3: {"itens": []})
    yield carteira
    cr.set_db(None)


def _criar(titulo, dia, inicio, fim, tipo="aula"):
    return asyncio.run(cr.criar_compromisso(
        cr.CompromissoPayload(titulo=titulo, dia=dia, inicio=inicio, fim=fim, tipo=tipo), _ALUNO
    ))


def _gerar(**kwargs):
    return asyncio.run(cr.gerar_cronograma(cr.GerarPayload(**kwargs), _ALUNO))


def _ler():
    return asyncio.run(cr.ler_cronograma(None, _ALUNO))


def test_fluxo_completo_do_cronograma(rotas):
    """Anotar compromisso -> montar a semana -> marcar um bloco como feito."""
    carteira = rotas
    _criar("Escola", 0, "07:00", "12:30")
    _criar("Escola", 1, "07:00", "12:30")

    semana = _gerar()["semana"]
    assert semana["total_blocos"] > 0
    assert carteira.debitos == [], "montar a semana não pode custar Spark nenhum"

    # Segunda e terça: o estudo só começa depois que a escola acaba.
    for dia in semana["dias"][:2]:
        for b in dia["blocos"]:
            assert b["inicio"] >= "12:30"

    bloco = next(b for d in semana["dias"] for b in d["blocos"])
    feito = asyncio.run(cr.concluir_bloco(bloco["id"], cr.ConcluirPayload(concluido=True), _ALUNO))
    assert feito["total_concluidos"] == 1

    marcados = [b for d in _ler()["dias"] for b in d["blocos"] if b["concluido"]]
    assert [b["id"] for b in marcados] == [bloco["id"]]


def test_remontar_a_semana_nao_deixa_check_orfao(rotas):
    """Os ids dos blocos são novos a cada montagem. Manter a marcação antiga
    daria check num bloco que não existe mais."""
    _criar("Escola", 0, "07:00", "12:30")
    bloco = next(b for d in _gerar()["semana"]["dias"] for b in d["blocos"])
    asyncio.run(cr.concluir_bloco(bloco["id"], cr.ConcluirPayload(concluido=True), _ALUNO))
    assert _gerar()["semana"]["total_concluidos"] == 0


def test_apagar_compromisso_devolve_o_horario(rotas):
    criado = _criar("Trabalho", 2, "08:00", "22:00")
    ocupado = _ler()
    asyncio.run(cr.apagar_compromisso(criado["compromisso"]["id"], _ALUNO))
    livre = _ler()
    assert ocupado["dias"][2]["compromissos"] and not livre["dias"][2]["compromissos"]


def test_bloco_inexistente_nao_e_marcado(rotas):
    _gerar()
    with pytest.raises(cr.HTTPException) as exc:
        asyncio.run(cr.concluir_bloco("nao-existe", cr.ConcluirPayload(concluido=True), _ALUNO))
    assert exc.value.status_code == 404


def test_mentis_fora_do_ar_devolve_sparks_e_o_cronograma(rotas, monkeypatch):
    """A promessa da feature: quem pede cronograma nunca fica sem cronograma.
    O modelo escreve o texto dos blocos — a semana existe sem ele."""
    carteira = rotas
    _criar("Escola", 0, "07:00", "12:30")

    async def _explode(*a, **k):
        raise RuntimeError("Gemini fora do ar")

    monkeypatch.setattr(cr.ai_service, "generate_json_resiliente", _explode)
    resposta = _gerar(com_mentis=True)

    assert carteira.debitos == [cr.MENTIS_COST]
    assert carteira.reembolsos == [cr.MENTIS_COST]
    assert resposta["cobrado"] == 0
    assert "devolvidos" in resposta["aviso"]
    assert resposta["semana"]["total_blocos"] > 0


def test_mentis_muda_o_texto_e_nao_o_horario(rotas, monkeypatch):
    _criar("Escola", 0, "07:00", "12:30")
    sem_mentis = _gerar()["semana"]
    horarios = [(b["dia"], b["inicio"], b["rota"]) for d in sem_mentis["dias"] for b in d["blocos"]]

    async def _responde(system, prompt, **k):
        assert "NÃO decide horário" in system
        return {
            "resumo": "Semana focada em Matemática.",
            "recado": "O risco é a segunda-feira.",
            "blocos": [
                {"indice": i, "titulo": f"Bloco {i}", "detalhe": "Faça isto.",
                 "dia": 6, "inicio": "03:00", "fim": "04:00", "rota": "https://exemplo.invalido"}
                for i in range(len(horarios))
            ],
        }

    monkeypatch.setattr(cr.ai_service, "generate_json_resiliente", _responde)
    semana = _gerar(com_mentis=True)["semana"]

    assert semana["plano"]["resumo"] == "Semana focada em Matemática."
    assert semana["plano"]["com_mentis"] is True
    assert [(b["dia"], b["inicio"], b["rota"]) for d in semana["dias"] for b in d["blocos"]] == horarios
    assert all(b["titulo"].startswith("Bloco ") for d in semana["dias"] for b in d["blocos"])


def test_texto_sem_compromisso_reconhecido_devolve_os_sparks(rotas, monkeypatch):
    carteira = rotas

    async def _nada(*a, **k):
        return {"compromissos": [], "resposta": "Não entendi."}

    monkeypatch.setattr(cr.ai_service, "generate_json_resiliente", _nada)
    resposta = asyncio.run(cr.compromissos_por_texto(cr.TextoPayload(texto="bom dia tudo bem"), _ALUNO))
    assert resposta["criados"] == 0 and resposta["cobrado"] == 0
    assert carteira.debitos == [cr.TEXTO_COST] and carteira.reembolsos == [cr.TEXTO_COST]


def test_texto_vira_compromisso_de_verdade(rotas, monkeypatch):
    async def _extrai(*a, **k):
        return {
            "compromissos": [{"titulo": "Inglês", "dia": 1, "inicio": "19:00", "fim": "20:30", "tipo": "aula"}],
            "resposta": "Anotei sua aula de inglês.",
        }

    monkeypatch.setattr(cr.ai_service, "generate_json_resiliente", _extrai)
    resposta = asyncio.run(cr.compromissos_por_texto(
        cr.TextoPayload(texto="tenho inglês terça às 19h", origem="voz"), _ALUNO
    ))
    assert resposta["criados"] == 1
    assert resposta["compromissos"][0]["origem"] == "voz"
    assert resposta["semana"]["dias"][1]["compromissos"][0]["titulo"] == "Inglês"


def test_ics_so_aceita_os_provedores_da_lista(rotas):
    """A trava contra usar o servidor como buscador de URL arbitrária. Se este
    teste cair, `/cronograma/importar/ics` vira uma alavanca para alcançar
    endereços internos da infraestrutura."""
    for url in (
        "http://169.254.169.254/latest/meta-data/",
        "https://exemplo.invalido/agenda.ics",
        "https://calendar.google.com.atacante.test/x.ics",
        "file:///etc/passwd",
    ):
        assert cr._host_permitido(url) is False, url
    assert cr._host_permitido("https://calendar.google.com/calendar/ical/x/basic.ics")
    assert cr._host_permitido("https://outlook.office365.com/owa/calendar/x/calendar.ics")

    with pytest.raises(cr.HTTPException) as exc:
        asyncio.run(cr.importar_ics(cr.IcsPayload(url="https://exemplo.invalido/a.ics"), _ALUNO))
    assert exc.value.status_code == 422


def test_prioridades_sobrevivem_ao_diagnostico_fora_do_ar(rotas, monkeypatch):
    """Sem diagnóstico, a resposta honesta é o ranking por peso na prova — e
    não uma tela de erro que deixa o aluno sem saber o que estudar."""
    async def _explode(uid):
        raise RuntimeError("Firestore fora do ar")

    monkeypatch.setattr(cr.annotation_service, "compute_diagnostico_real", _explode)
    resposta = asyncio.run(cr.minhas_prioridades(_ALUNO))
    assert {p["chave"] for p in resposta["prioridades"][:2]} == {"matematica", "redacao"}


# ---------------------------------------------------------------------------
# O PREÇO DE MONTAR A SEMANA (2026-09-17)
# ---------------------------------------------------------------------------
#
# Montar pela primeira vez é grátis; REMONTAR custa (a remontagem apaga os
# blocos marcados como feitos); com a Mentis custa o preço dela. E os dois
# nunca se somam: uma ação, uma cobrança.
#
# São chamadas diretas a `_custo_da_montagem`, e não à rota inteira: a regra de
# preço é a coisa que precisa estar certa, e testá-la por dentro de uma rota
# que toca Mongo, Firestore e Gemini seria testar três outras coisas junto.

import cronograma_routes as cr  # noqa: E402


def test_primeira_montagem_da_semana_e_gratis():
    assert cr._custo_da_montagem(com_mentis=False, remontagem=False) == 0


def test_remontar_custa_o_preco_da_remontagem():
    assert cr._custo_da_montagem(com_mentis=False, remontagem=True) == cr.REMONTAGEM_COST
    assert cr.REMONTAGEM_COST > 0


def test_com_a_mentis_custa_o_preco_da_mentis():
    assert cr._custo_da_montagem(com_mentis=True, remontagem=False) == cr.MENTIS_COST
    assert cr.MENTIS_COST == 50


def test_remontar_com_a_mentis_nao_soma_os_dois_precos():
    """A regra que protege o aluno de uma cobrança que ele não entende: o
    mesmo botão não pode custar 50 na primeira semana e 60 na segunda."""
    assert cr._custo_da_montagem(com_mentis=True, remontagem=True) == cr.MENTIS_COST
    assert cr._custo_da_montagem(com_mentis=True, remontagem=True) < (
        cr.MENTIS_COST + cr.REMONTAGEM_COST
    )
