"""Notificação no celular (Web Push do PWA) — as regras, sem I/O.

Este módulo decide **se**, **quando** e **o quê**. Quem lê o banco, assina com
VAPID e fala com o serviço de push é `push_service`; quem expõe as rotas é
`push_routes`. A separação é a mesma de `engajamento.py`: a regra cabe num
teste offline e o teste não precisa de rede para provar a ética da mensagem.

A linha ética é a do motor de engajamento (ver o cabeçalho de
`engajamento.py`): **toda frase é aritmética sobre dado que o próprio aluno
gerou**. Sem número, sem mensagem — um aluno sem sinal nenhum não recebe nada,
em vez de receber "Bora estudar hoje?". Notificação genérica é a que ensina o
aluno a desligar as notificações.

Três limites, e por que cada um existe:

* **No máximo UMA por aluno por dia** (`push_envios`, `_id = "{uid}:{dia}"`).
  Mais que isso, a notificação deixa de ser um aviso e vira ruído; e ruído é o
  que faz alguém desinstalar o app inteiro, não só desligar o aviso.
* **Só entre 8h e 21h de Brasília** (`dentro_da_janela`). Ninguém estuda
  porque o celular vibrou às 23h40.
* **A ordem de prioridade é do dono do produto** e não se reordena sem ele:
  sequência em risco hoje > trechos/revisões que voltaram hoje > padrão de
  erro com questões novas > missão do dia.

A consequência que não é óbvia: como a sequência só está "em risco" de verdade
no fim do dia, e como o teto é de uma por dia, a avaliação acontece UMA vez,
à noite (`HORA_DA_AVALIACAO`). Avaliar de manhã e mandar a revisão gastaria o
único aviso do dia antes de saber se a sequência — a primeira da fila — ia
precisar dele.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import rotas_do_app as rotas

# ---------------------------------------------------------------------------
# Quando
# ---------------------------------------------------------------------------

# Horário de Brasília. Fim EXCLUSIVO: às 21h00 a janela já fechou.
JANELA_INICIO = 8
JANELA_FIM = 21

# A hora em que o laço passa a avaliar quem está inscrito. 19h deixa cinco
# horas até a meia-noite — tempo para responder uma questão e salvar a
# sequência — e cabe com folga dentro da janela.
HORA_DA_AVALIACAO_PADRAO = 19


def hora_da_avaliacao(bruto: str | int | None) -> int:
    """A hora configurada, presa dentro da janela. Um valor fora dela (ou
    lixo) volta ao padrão em vez de criar um laço que nunca avalia ninguém."""
    try:
        hora = int(bruto)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return HORA_DA_AVALIACAO_PADRAO
    if JANELA_INICIO <= hora < JANELA_FIM:
        return hora
    return HORA_DA_AVALIACAO_PADRAO


def dentro_da_janela(agora_local: datetime) -> bool:
    """Se uma notificação pode SAIR agora. `agora_local` já em Brasília."""
    return JANELA_INICIO <= agora_local.hour < JANELA_FIM


def hora_de_avaliar(agora_local: datetime, hora_avaliacao: int = HORA_DA_AVALIACAO_PADRAO) -> bool:
    """Se o laço deve olhar para os inscritos neste ciclo. Fora disso ele não
    toca em banco nenhum — é só a leitura do relógio."""
    return dentro_da_janela(agora_local) and agora_local.hour >= hora_avaliacao


def chave_do_dia(uid: str, dia: str) -> str:
    """`_id` da reivindicação diária em `push_envios`. Determinística: duas
    máquinas do Fly rodando o laço ao mesmo tempo disputam o MESMO `_id`, e o
    `insert_one` da segunda esbarra em `DuplicateKeyError` — é o teto de 1/dia
    garantido pelo banco, não por memória de processo."""
    return f"{uid}:{dia}"


# ---------------------------------------------------------------------------
# Para onde (o endpoint que o navegador entregou)
# ---------------------------------------------------------------------------

# O servidor faz um POST para o `endpoint` que o NAVEGADOR mandou. Sem esta
# lista, a rota de inscrição seria um repetidor de requisições: qualquer conta
# cadastraria `http://169.254.169.254/...` e o laço bateria lá todo dia.
# Só os serviços de push dos navegadores que existem.
_HOSTS_DE_PUSH = (
    "fcm.googleapis.com",                 # Chrome, Edge (Android), Samsung, Opera
    "android.googleapis.com",
    "updates.push.services.mozilla.com",  # Firefox
    "push.services.mozilla.com",
    "web.push.apple.com",                 # Safari (macOS 13+, iOS 16.4+ instalado)
    "push.apple.com",
    "notify.windows.com",                 # Edge no Windows (wns2-*.notify.windows.com)
)

MAX_ENDPOINT = 2048


def endpoint_valido(endpoint: Any) -> bool:
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > MAX_ENDPOINT:
        return False
    try:
        url = urlparse(endpoint)
    except ValueError:
        return False
    if url.scheme != "https" or not url.hostname or url.port not in (None, 443):
        return False
    host = url.hostname.lower()
    return any(host == h or host.endswith("." + h) for h in _HOSTS_DE_PUSH)


def chave_valida(valor: Any, *, minimo: int, maximo: int) -> bool:
    """`p256dh` e `auth` chegam em base64url. Só o formato e o tamanho: quem
    prova que a chave serve é a criptografia, no primeiro envio."""
    if not isinstance(valor, str) or not (minimo <= len(valor) <= maximo):
        return False
    return all(c.isalnum() or c in "-_=" for c in valor)


# ---------------------------------------------------------------------------
# O quê
# ---------------------------------------------------------------------------

TAG = "sapiens-dia"  # uma por dia: uma nova substitui a anterior na bandeja


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _mensagem(tipo: str, titulo: str, corpo: str, rota: str) -> dict[str, str]:
    return {"tipo": tipo, "titulo": titulo, "corpo": corpo, "rota": rota, "tag": TAG}


def escolher_mensagem(sinais: dict[str, Any] | None) -> dict[str, str] | None:
    """A notificação do dia, ou `None`.

    `sinais` é o que `push_service.sinais_do_aluno` mediu — números, nunca
    texto livre:

    * `ofensiva`: `{"dias", "estudou_hoje", "em_risco"}` (de `agregado.dias_ativos`)
    * `trechos_hoje`: trechos guardados com a Mentis cuja volta é hoje ou antes
    * `revisoes_hoje`: retestes da revisão espaçada vencidos hoje ou antes
    * `padrao`: `{"questoes_novas"}` — questões ainda não respondidas no ponto
      em que o aluno mais erra, ou `None`
    * `missao`: a primeira missão do dia ainda não cumprida, ou `None`

    **O nome do ponto fraco não aparece**, de propósito: os nomes reais da
    ontologia nunca chegam ao aluno, e a bandeja de notificações do celular é
    lida por cima do ombro.
    """
    if not sinais:
        return None

    of = sinais.get("ofensiva") or {}
    dias = int(of.get("dias") or 0)
    if of.get("em_risco") and dias > 0 and not of.get("estudou_hoje"):
        return _mensagem(
            "sequencia",
            f"Sua sequência de {dias} {_plural(dias, 'dia', 'dias')} acaba à meia-noite",
            "Você ainda não estudou hoje. Uma questão respondida já mantém a sequência.",
            rotas.HOJE,
        )

    trechos = max(0, int(sinais.get("trechos_hoje") or 0))
    revisoes = max(0, int(sinais.get("revisoes_hoje") or 0))
    if trechos or revisoes:
        partes = []
        if trechos:
            partes.append(f"{trechos} {_plural(trechos, 'trecho que você guardou', 'trechos que você guardou')}")
        if revisoes:
            partes.append(f"{revisoes} {_plural(revisoes, 'revisão', 'revisões')}")
        total = trechos + revisoes
        titulo = " e ".join(partes) + f" {_plural(total, 'voltou', 'voltaram')} hoje"
        return _mensagem(
            "revisao",
            titulo[0].upper() + titulo[1:],
            "Estão na sua Agenda, prontos para rever.",
            rotas.AGENDA_LEMBRETES if trechos and not revisoes else rotas.AGENDA_REVISOES,
        )

    padrao = sinais.get("padrao") or {}
    novas = int(padrao.get("questoes_novas") or 0)
    if novas > 0:
        return _mensagem(
            "padrao",
            f"{novas} {_plural(novas, 'questão nova', 'questões novas')} no ponto em que você mais erra",
            "Escolhidas pelo seu padrão de erro, entre as que você ainda não respondeu.",
            rotas.HOJE,
        )

    missao = sinais.get("missao") or {}
    if missao.get("titulo") and not missao.get("concluida"):
        progresso = int(missao.get("progresso") or 0)
        alvo = int(missao.get("alvo") or 0)
        sparks = int(missao.get("sparks") or 0)
        premio = f"+{sparks} Sparks" if sparks > 0 else "o prêmio da missão"
        corpo = (
            f"Você está em {progresso}/{alvo}. Concluir vale {premio}."
            if progresso > 0 and alvo > 0
            else f"Concluir vale {premio}."
        )
        return _mensagem("missao", f"Missão de hoje: {missao['titulo']}", corpo, rotas.HOJE_MISSOES)

    return None
