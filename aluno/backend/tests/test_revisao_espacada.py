"""Revisão espaçada — o eixo do tempo sobre a fila do motor (Fases 1, 2 e 4).

O que estes testes travam, nesta ordem de importância:

1. **Só a RAIZ agenda.** Elo de ordem >= 2 é manifestação de superfície, e
   tratar manifestação como causa é o defeito que o Error Trace §1.1 existe
   para impedir. Um reteste agendado por manifestação seria esse defeito com
   um calendário em cima.
2. **Raiz nova colapsa; reteste acertado expande; reteste errado NÃO expande.**
   É a regra inteira do espaçamento adaptativo, e a que mais silenciosamente
   se perde numa refatoração.
3. **Disciplina de interrupção.** No máximo `_MAX_INTERVENCOES_ATIVAS` ativas
   por vez (nunca duas para o mesmo processo), cooldown por par, dispensa
   contada. Sem isto o Professor Invisível vira pop-up.
4. **Custo O(1).** Nada aqui varre evento — ver também
   `test_custo_firestore.py::TestCustoDaRevisao`.
5. **Hipótese continua hipótese.** O rótulo `provisorio` atravessa da raiz até
   a fila e a trajetória, e a trajetória não afirma nexo causal com o portão
   desligado.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import revisao_espacada as rev  # noqa: E402

PROC = "PROC-SIMB-01"
ERRO = "ERR-03"
OUTRO_PROC = "PROC-QUANT-04"
TERCEIRO_PROC = "PROC-CAUSAL-01"


def _raiz(erro=ERRO, processo=PROC, confianca=0.7, provisorio=False):
    return {"erro": erro, "processo": processo, "confianca": confianca, "provisorio": provisorio}


def _responder(bloco, *, dia, acertou=False, raiz=None, processos=(PROC,), contexto=None):
    return rev.registrar(
        bloco,
        processos=processos,
        acertou=acertou,
        dia=dia,
        quando=f"{dia}T10:00:00+00:00",
        raiz=raiz,
        contexto=contexto,
    )


def _entrada(bloco, pid=PROC):
    return bloco["processos"][pid]


# ============================================ agendamento


class TestAgendamento:
    def test_raiz_nova_agenda_o_primeiro_degrau(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        assert _entrada(b)["proximo_reteste"] == "2026-09-02"
        assert _entrada(b)["degrau"] == 0

    def test_raiz_nova_do_mesmo_par_colapsa_para_o_minimo(self):
        """O critério de aceite da Fase 1, literal."""
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-02", acertou=True)          # reteste ok
        b = _responder(b, dia="2026-09-05", acertou=True)          # reteste ok
        assert _entrada(b)["degrau"] == 2
        longe = _entrada(b)["proximo_reteste"]

        b = _responder(b, dia="2026-09-10", raiz=_raiz())
        assert _entrada(b)["degrau"] == 0
        assert _entrada(b)["proximo_reteste"] == "2026-09-11"
        assert _entrada(b)["proximo_reteste"] < longe

    def test_reteste_acertado_expande_o_intervalo(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        assert _entrada(b)["proximo_reteste"] == "2026-09-02"
        b = _responder(b, dia="2026-09-02", acertou=True)
        assert _entrada(b)["degrau"] == 1
        assert _entrada(b)["proximo_reteste"] == "2026-09-05"  # +3
        b = _responder(b, dia="2026-09-05", acertou=True)
        assert _entrada(b)["proximo_reteste"] == "2026-09-12"  # +7

    def test_reteste_errado_nao_expande(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-02", acertou=False)
        assert _entrada(b)["degrau"] == 0, "o degrau subiu com o reteste ERRADO"
        assert _entrada(b)["proximo_reteste"] == "2026-09-03"
        assert _entrada(b)["ultimo_reteste"]["acertou"] is False

    def test_resposta_antes_do_vencimento_nao_consome_o_reteste(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-01", acertou=True)
        assert _entrada(b)["retestes"]["total"] == 0
        assert _entrada(b)["proximo_reteste"] == "2026-09-02"

    def test_escada_tem_teto_e_nao_estoura(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        dia = "2026-09-02"
        for _ in range(len(rev.INTERVALOS_DIAS) + 3):
            b = _responder(b, dia=dia, acertou=True)
            dia = _entrada(b)["proximo_reteste"]
        assert _entrada(b)["degrau"] == len(rev.INTERVALOS_DIAS) - 1


class TestSoARaizAgenda:
    def test_manifestacao_nao_produz_agendamento(self):
        """`registrar` só recebe raiz; o processo que aparece como ordem >= 2
        entra apenas como processo exercitado pelo item, e não agenda nada."""
        b = _responder(
            None, dia="2026-09-01", raiz=_raiz(processo=PROC), processos=(PROC, OUTRO_PROC)
        )
        assert _entrada(b, PROC)["proximo_reteste"] is not None
        assert _entrada(b, OUTRO_PROC)["proximo_reteste"] is None
        assert _entrada(b, OUTRO_PROC)["raizes_recentes"] == []
        assert _entrada(b, OUTRO_PROC)["pesos_raiz"] == {}

    def test_processo_so_com_desempenho_nao_entra_na_fila_por_agendamento(self):
        b = None
        for i in range(4):
            b = _responder(b, dia=f"2026-09-0{i + 1}", acertou=True, processos=(OUTRO_PROC,))
        fila = rev.fila(b, "2026-09-10")
        assert [l["processo_id"] for l in fila] == []


# ============================================ estados


class TestEstados:
    def test_recorrencia_exige_dias_distintos(self):
        """Duas marcações do mesmo distrator na MESMA sessão são um lapso, não
        um padrão — e um padrão é o que autoriza interromper o aluno."""
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-01", raiz=_raiz())
        assert rev.estado(_entrada(b), "2026-09-01") != rev.ESTADO_RECORRENTE
        b = _responder(b, dia="2026-09-04", raiz=_raiz())
        assert rev.estado(_entrada(b), "2026-09-04") == rev.ESTADO_RECORRENTE

    def test_uma_unica_raiz_nunca_e_recorrencia(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        assert rev.estado(_entrada(b), "2026-09-01") == rev.ESTADO_CONSOLIDACAO

    def test_em_consolidacao_enquanto_o_reteste_nao_vence(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        assert rev.estado(_entrada(b), "2026-09-01") == rev.ESTADO_CONSOLIDACAO

    def test_deterioracao_precisa_de_queda_sobre_amostra_comparavel(self):
        b = None
        # Janela cheia com 7/8 (87,5%).
        for i in range(rev.JANELA_TAMANHO):
            b = _responder(b, dia="2026-09-01", acertou=(i != 0))
        # Janela nova com 1/4 (25%).
        for i in range(rev.JANELA_MINIMA):
            b = _responder(b, dia="2026-09-05", acertou=(i == 0))
        assert rev.estado(_entrada(b), "2026-09-05") == rev.ESTADO_DETERIORACAO

    def test_quem_nunca_esteve_estavel_nao_deteriora(self):
        b = None
        for _ in range(rev.JANELA_TAMANHO):
            b = _responder(b, dia="2026-09-01", acertou=False)
        for _ in range(rev.JANELA_MINIMA):
            b = _responder(b, dia="2026-09-05", acertou=False)
        assert rev.estado(_entrada(b), "2026-09-05") != rev.ESTADO_DETERIORACAO

    def test_queda_pequena_e_ruido_e_nao_deterioracao(self):
        b = None
        for i in range(rev.JANELA_TAMANHO):
            b = _responder(b, dia="2026-09-01", acertou=(i != 0))       # 87,5%
        for i in range(rev.JANELA_TAMANHO - 1):
            b = _responder(b, dia="2026-09-05", acertou=(i != 0))       # 85,7%
        assert rev.estado(_entrada(b), "2026-09-05") != rev.ESTADO_DETERIORACAO


# ============================================ fila diária


class TestFila:
    def test_recorrencia_vem_antes_de_consolidacao(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz(processo=OUTRO_PROC), processos=(OUTRO_PROC,))
        b = _responder(b, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-03", raiz=_raiz())
        fila = rev.fila(b, "2026-09-03")
        assert fila[0]["processo_id"] == PROC
        assert fila[0]["estado"] == rev.ESTADO_RECORRENTE

    def test_sentinela_vai_depois_do_prescritivel(self):
        sentinela = sorted(rev.SENTINELAS)[0]
        b = _responder(None, dia="2026-09-01", raiz=_raiz(erro=sentinela, processo=OUTRO_PROC), processos=(OUTRO_PROC,))
        b = _responder(b, dia="2026-09-01", raiz=_raiz())
        fila = rev.fila(b, "2026-09-01")
        assert [l["sem_intervencao_catalogada"] for l in fila] == [False, True]

    def test_fila_e_fechada_e_curta(self):
        b = None
        for i in range(20):
            b = _responder(b, dia="2026-09-01", raiz=_raiz(processo=f"PROC-{i}"), processos=(f"PROC-{i}",))
        assert len(rev.fila(b, "2026-09-01")) == rev.FILA_TAMANHO
        assert len(rev.fila(b, "2026-09-01", limite=3)) == 3

    def test_processo_estavel_fica_de_fora(self):
        b = None
        for _ in range(rev.JANELA_TAMANHO):
            b = _responder(b, dia="2026-09-01", acertou=True)
        assert rev.fila(b, "2026-09-01") == []

    def test_provisorio_atravessa_da_raiz_ate_a_fila(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz(provisorio=True))
        assert rev.fila(b, "2026-09-01")[0]["provisorio"] is True

    def test_fila_de_bloco_vazio_nao_explode(self):
        assert rev.fila(None, "2026-09-01") == []
        assert rev.fila({}, "2026-09-01") == []


# ============================================ Fase 2 — gatilho


class TestGatilho:
    def test_uma_unica_raiz_nao_dispara(self):
        """`MIN_TRACOS_RAIZ` é o limiar do motor, reusado. Um limiar novo aqui
        criaria duas noções divergentes de 'evidência suficiente'."""
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        assert rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-01") is None

    def test_recorrencia_dispara(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-03", raiz=_raiz())
        g = rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-03")
        assert g and g["motivo"] == rev.GATILHO_RECORRENCIA
        assert g["erro_id"] == ERRO and g["processo_id"] == PROC

    def test_reteste_falho_dispara(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-02", acertou=False)
        g = rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-02")
        assert g and g["motivo"] in (rev.GATILHO_RETESTE_FALHO, rev.GATILHO_RECORRENCIA)

    def test_cooldown_impede_redisparo_antes_do_reteste(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-03", raiz=_raiz())
        g = rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-03")
        b = rev.marcar_disparo(b, g, quando="2026-09-03T10:00:00+00:00", hoje="2026-09-03")
        b = rev.encerrar_intervencao(b, processo_id=PROC, quando="2026-09-03T10:05:00+00:00")

        b = _responder(b, dia="2026-09-03", raiz=_raiz())
        assert rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-03") is None, "redisparou no cooldown"

    def test_ate_duas_intervencoes_simultaneas_mas_nunca_a_terceira(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-03", raiz=_raiz())
        g = rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-03")
        b = rev.marcar_disparo(b, g, quando="2026-09-03T10:00:00+00:00", hoje="2026-09-03")

        # Um segundo processo, com evidência própria, PODE disparar em paralelo.
        b = _responder(b, dia="2026-09-03", raiz=_raiz(processo=OUTRO_PROC), processos=(OUTRO_PROC,))
        b = _responder(b, dia="2026-09-05", raiz=_raiz(processo=OUTRO_PROC), processos=(OUTRO_PROC,))
        g2 = rev.avaliar_gatilho(b, processo_id=OUTRO_PROC, hoje="2026-09-05")
        assert g2 is not None, "segundo processo represado pelo primeiro"
        b = rev.marcar_disparo(b, g2, quando="2026-09-05T10:00:00+00:00", hoje="2026-09-05")
        assert set(b["intervencoes_ativas"]) == {PROC, OUTRO_PROC}

        # Um terceiro esbarra no teto.
        b = _responder(b, dia="2026-09-05", raiz=_raiz(processo=TERCEIRO_PROC), processos=(TERCEIRO_PROC,))
        b = _responder(b, dia="2026-09-07", raiz=_raiz(processo=TERCEIRO_PROC), processos=(TERCEIRO_PROC,))
        assert rev.avaliar_gatilho(b, processo_id=TERCEIRO_PROC, hoje="2026-09-07") is None

    def test_dispensar_conta_como_sinal(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-03", raiz=_raiz())
        g = rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-03")
        b = rev.marcar_disparo(b, g, quando="2026-09-03T10:00:00+00:00", hoje="2026-09-03")
        b = rev.encerrar_intervencao(b, processo_id=PROC, quando="2026-09-03T10:01:00+00:00", dispensada=True)
        assert _entrada(b)["dispensas"] == 1
        assert PROC not in b["intervencoes_ativas"]

    def test_concluir_nao_conta_dispensa(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        b = _responder(b, dia="2026-09-03", raiz=_raiz())
        g = rev.avaliar_gatilho(b, processo_id=PROC, hoje="2026-09-03")
        b = rev.marcar_disparo(b, g, quando="2026-09-03T10:00:00+00:00", hoje="2026-09-03")
        b = rev.encerrar_intervencao(b, processo_id=PROC, quando="2026-09-03T10:01:00+00:00", dispensada=False)
        assert _entrada(b)["dispensas"] == 0


# ============================================ Fase 4 — trajetória e tetos


class TestTrajetoria:
    def test_marcos_registram_a_historia_e_nao_as_respostas(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        for _ in range(5):
            b = _responder(b, dia="2026-09-01", acertou=True)
        tipos = [m["tipo"] for m in rev.trajetoria(b, PROC)]
        assert tipos == [rev.MARCO_RAIZ], f"resposta virou marco: {tipos}"

    def test_reteste_e_transferencia_viram_marco(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz(), contexto="DOM-01")
        b = _responder(b, dia="2026-09-02", acertou=True, contexto="DOM-01")
        b = _responder(b, dia="2026-09-06", acertou=True, contexto="DOM-07")
        tipos = [m["tipo"] for m in rev.trajetoria(b, PROC)]
        assert rev.MARCO_RETESTE_OK in tipos
        assert rev.MARCO_TRANSFERENCIA in tipos

    def test_log_de_marcos_tem_teto(self):
        b = None
        dia = 1
        for _ in range(rev._MAX_MARCOS + 10):
            b = _responder(b, dia=f"2026-09-{dia:02d}", raiz=_raiz())
            dia = dia % 28 + 1
        assert len(_entrada(b)["marcos"]) == rev._MAX_MARCOS

    def test_raizes_recentes_tem_teto(self):
        b = None
        dia = 1
        for _ in range(rev._MAX_RAIZES + 10):
            b = _responder(b, dia=f"2026-09-{dia:02d}", raiz=_raiz())
            dia = dia % 28 + 1
        assert len(_entrada(b)["raizes_recentes"]) == rev._MAX_RAIZES

    def test_contextos_da_raiz_tem_teto(self):
        b = None
        for i in range(rev._MAX_CONTEXTOS + 5):
            b = _responder(b, dia="2026-09-01", raiz=_raiz(), contexto=f"DOM-{i}")
        assert len(_entrada(b)["contextos_da_raiz"]) == rev._MAX_CONTEXTOS

    def test_processos_acompanhados_tem_teto(self):
        b = None
        for i in range(rev._MAX_PROCESSOS + 12):
            b = _responder(b, dia="2026-09-01", acertou=True, processos=(f"PROC-{i}",))
        assert len(b["processos"]) == rev._MAX_PROCESSOS


# ============================================ §12 — a hipótese instrumentada


class TestInstrumentacao:
    def test_mede_reteste_e_transferencia_separadamente(self):
        """A hipótese do §12 não é 'a fila existe'. É: o reteste acerta mais, e
        a diferença SOBREVIVE à troca de contexto. Se não sobreviver, o ciclo
        ensinou o item e não a habilidade."""
        b = _responder(None, dia="2026-09-01", raiz=_raiz(), contexto="DOM-01")
        b = _responder(b, dia="2026-09-02", acertou=True, contexto="DOM-01")     # reteste ok, mesmo contexto
        b = _responder(b, dia="2026-09-05", acertou=False, contexto="DOM-09")    # outro contexto, errou
        i = rev.instrumentacao(b)
        assert i["retestes"]["total"] == 2 and i["retestes"]["acertos"] == 1
        assert i["transferencia"]["total"] == 1 and i["transferencia"]["acertos"] == 0
        assert i["retestes"]["taxa"] == 50.0
        assert i["transferencia"]["taxa"] == 0.0

    def test_bloco_vazio_devolve_taxas_nulas_e_nao_zero(self):
        """Zero por cento e 'ainda não medimos' são coisas diferentes."""
        i = rev.instrumentacao(None)
        assert i["retestes"]["taxa"] is None and i["transferencia"]["taxa"] is None


# ============================================ pureza


class TestPureza:
    def test_registrar_nao_muta_o_bloco_recebido(self):
        b = _responder(None, dia="2026-09-01", raiz=_raiz())
        antes = _entrada(b)["proximo_reteste"]
        _responder(b, dia="2026-09-10", raiz=_raiz())
        assert _entrada(b)["proximo_reteste"] == antes

    def test_modulo_nao_importa_ia_nem_firestore(self):
        fonte = (BACKEND / "revisao_espacada.py").read_text(encoding="utf-8")
        for proibido in ("ai_service", "firestore", "google.cloud", "requests"):
            assert proibido not in fonte, f"revisao_espacada importou {proibido}"
