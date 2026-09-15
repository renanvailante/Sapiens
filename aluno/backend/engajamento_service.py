"""Persistência do motor de engajamento — XP, missões, ligas e congeladores.

**Onde cada coisa mora, e por quê.** O estado de engajamento fica no MONGO, não
no Firestore. Não é preferência: é a regra de custo da casa
(`project_aluno_disciplina_leitura_firestore`, escrita depois do apagão de
2026-09-04). Uma liga semanal é, por natureza, uma leitura de O(alunos) várias
vezes por dia — em Firestore isso é a cota gratuita inteira num almoço. No
Mongo não há cota, e a mesma consulta sai indexada e de graça.

O que continua no Firestore, intocado:

* **Sparks**, porque é dinheiro e já tem concessão atômica auditável;
* **`agregado.dias_ativos`**, porque é a prova de que o aluno estudou de verdade
  — a ofensiva PRECISA derivar dali, e não de um contador de XP que este módulo
  poderia incrementar sozinho. Se a sequência viesse do Mongo, ela mediria
  chamadas de API, não estudo.

Custo por chamada de `estado()`: 1 leitura no Firestore (o agregado, que várias
outras telas já leem) e 3 consultas indexadas no Mongo.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import engajamento as eng
import firestore_service as fs

logger = logging.getLogger("sapiens.engajamento")

_db = None


def set_db(db):
    global _db
    _db = db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hoje() -> str:
    return fs.dia_local()


# ---------------------------------------------------------------------------
# Escrita — o único caminho por onde XP entra no sistema
# ---------------------------------------------------------------------------

async def registrar_acao(
    uid: str,
    acoes: list[str],
    *,
    contadores: dict[str, int] | None = None,
    nome: str | None = None,
    chave_unica: str | None = None,
) -> dict[str, Any]:
    """Soma o XP de `acoes` e incrementa os contadores do dia.

    `chave_unica` é para ações que o aluno pode desfazer e refazer — marcar um
    bloco do cronograma como feito, desmarcar e marcar de novo. Sem ela, o
    check virava um botão de fabricar XP. Com ela, o `$addToSet` no perfil só
    deixa a PRIMEIRA vez passar, e o aluno pode desmarcar à vontade sem que o
    produto o castigue nem o premie de novo.

    Chamado de dentro das rotas que já fazem o trabalho de verdade (responder
    questão, concluir revisão, corrigir redação). **Nunca pode derrubar o que
    chamou**: engajamento é a camada de cima: perder o XP de uma resposta é um
    aborrecimento; perder a resposta é perder o estudo do aluno. Por isso toda
    falha aqui é logada e engolida.

    `nome` é guardado para a liga não precisar cruzar com a coleção de usuários
    a cada leitura do ranking.
    """
    if _db is None or not uid:
        return {"xp": 0}
    xp = sum(eng.XP_POR_ACAO.get(a, 0) for a in acoes)
    dia = _hoje()
    semana = eng.semana_de(dia)

    if chave_unica:
        try:
            marca = await _db.engajamento_perfil.update_one(
                {"_id": uid},
                {"$addToSet": {"ja_premiado": chave_unica}, "$set": {"uid": uid}},
                upsert=True,
            )
            # `modified_count == 0` num upsert que não inseriu significa que a
            # chave já estava lá: esta ação já foi paga antes.
            if marca.modified_count == 0 and marca.upserted_id is None:
                return {"xp": 0, "ja_premiado": True}
        except Exception:  # noqa: BLE001
            logger.exception("guarda de chave única falhou para %s (%s)", uid, chave_unica)
            return {"xp": 0}

    try:
        incrementos = {f"contadores.{k}": v for k, v in (contadores or {}).items() if v}
        if xp:
            incrementos["xp"] = xp
        if incrementos:
            await _db.engajamento_dia.update_one(
                {"_id": f"{uid}:{dia}"},
                {
                    "$inc": incrementos,
                    "$set": {"uid": uid, "dia": dia, "atualizado_em": _now_iso()},
                    # O contador do dia não serve para nada depois de alguns
                    # meses e não é fonte de verdade de nada (o histórico real
                    # são os eventos de behavior). O TTL evita que a coleção
                    # cresça um documento por aluno por dia para sempre.
                    "$setOnInsert": {"expurgo_em_dt": datetime.now(timezone.utc) + timedelta(days=120)},
                },
                upsert=True,
            )
        if xp:
            await _db.engajamento_perfil.update_one(
                {"_id": uid},
                {"$inc": {"xp_total": xp}, "$set": {"uid": uid, "atualizado_em": _now_iso()}},
                upsert=True,
            )
            campos = {"uid": uid, "semana": semana, "atualizado_em": _now_iso()}
            if nome:
                campos["nome"] = nome
            # Tentativa direta primeiro: na esmagadora maioria das chamadas a
            # linha da semana já existe, e descobrir a divisão de entrada custa
            # duas consultas a mais. Só quando nada foi atualizado é que vale a
            # pena pagar por `_liga_de_entrada` — uma vez por aluno por semana.
            alvo = {"_id": f"{uid}:{semana}"}
            r = await _db.liga_semana.update_one(alvo, {"$inc": {"pontos": xp}, "$set": campos})
            if r.matched_count == 0:
                await _db.liga_semana.update_one(
                    alvo,
                    {
                        "$inc": {"pontos": xp},
                        "$set": campos,
                        "$setOnInsert": {"liga_id": await _liga_de_entrada(uid, semana)},
                    },
                    upsert=True,
                )
    except Exception:  # noqa: BLE001
        logger.exception("registrar_acao falhou para %s (%s) — a ação em si já foi gravada", uid, acoes)
        return {"xp": 0}
    return {"xp": xp}


async def _liga_de_entrada(uid: str, semana: str) -> str:
    """Divisão em que o aluno entra nesta semana.

    É aqui que a subida e a descida acontecem, de forma PREGUIÇOSA: na primeira
    ação da semana, olha-se o resultado da semana passada e aplica-se
    `promover()`. Sem laço agendado, sem janela em que o resultado "ainda não
    saiu" — quem volta na terça vê a promoção de segunda acontecer no ato.
    """
    anterior = await _db.liga_semana.find_one({"uid": uid}, sort=[("semana", -1)])
    if not anterior or anterior.get("semana") == semana:
        return (anterior or {}).get("liga_id") or eng.LIGAS[0]["id"]
    liga_id = anterior.get("liga_id") or eng.LIGAS[0]["id"]
    pontos = int(anterior.get("pontos") or 0)
    grupo = {"semana": anterior["semana"], "liga_id": liga_id}
    total = await _db.liga_semana.count_documents(grupo)
    acima = await _db.liga_semana.count_documents({**grupo, "pontos": {"$gt": pontos}})
    return eng.promover(liga_id, acima + 1, total)


# ---------------------------------------------------------------------------
# Leitura — o estado inteiro que o painel consome
# ---------------------------------------------------------------------------

async def estado(uid: str, *, nome: str | None = None) -> dict[str, Any]:
    """Ofensiva, nível, missões, liga, conquistas e contagem do ENEM."""
    if _db is None:
        raise RuntimeError("engajamento_service.set_db não foi chamado")
    dia = _hoje()
    semana = eng.semana_de(dia)

    agregado = await _ler_agregado(uid)
    dias_ativos = agregado.get("dias_ativos") or []
    total_respostas = int(agregado.get("total_respostas") or 0)

    perfil = (await _db.engajamento_perfil.find_one({"_id": uid})) or {}
    doc_dia = (await _db.engajamento_dia.find_one({"_id": f"{uid}:{dia}"})) or {}
    contadores = doc_dia.get("contadores") or {}

    ofensiva = eng.calcular_ofensiva(
        dias_ativos,
        hoje=dia,
        dias_congelados=perfil.get("dias_congelados") or [],
        congeladores=int(perfil.get("congeladores") or 0),
    )
    if ofensiva.congelar:
        await _consumir_congeladores(uid, list(ofensiva.congelar))

    nivel = eng.nivel_de_xp(int(perfil.get("xp_total") or 0))
    liga = await _liga(uid, semana, nome=nome)

    # Conquistas NÃO saem daqui: o Painel já tem o próprio conjunto, derivado
    # dos mesmos dados brutos. Dois sistemas de conquista sobre a mesma
    # realidade divergem — e uma conquista que discorda da outra metade da tela
    # é pior do que conquista nenhuma.
    return {
        "ofensiva": {
            "dias": ofensiva.dias,
            "recorde": ofensiva.recorde,
            "estudou_hoje": ofensiva.estudou_hoje,
            "em_risco": ofensiva.em_risco,
            "congeladores": ofensiva.congeladores_restantes,
            "max_congeladores": eng.MAX_CONGELADORES,
            "custo_congelador": eng.CUSTO_CONGELADOR,
            "semana": _semana_visual(dias_ativos, perfil.get("dias_congelados") or [], dia),
        },
        "nivel": nivel,
        "missoes": eng.missoes_do_dia(uid, dia, contadores, doc_dia.get("resgatadas") or []),
        "liga": liga,
        "enem": eng.dias_para_o_enem(dia),
        "hoje": dia,
        "total_respostas": total_respostas,
    }


async def _ler_agregado(uid: str) -> dict[str, Any]:
    """O agregado do Firestore, com o apagão dele tratado como estado normal.

    Cota estourada não pode virar "aluno sem ofensiva": zerar a sequência de
    quem estudou 40 dias por causa de um problema de infraestrutura seria a
    pior falha possível desta tela. Devolver vazio faz a ofensiva aparecer como
    0 nesta requisição e voltar sozinha na próxima — nada é gravado a partir de
    uma leitura que falhou (ver a guarda em `_consumir_congeladores`).
    """
    try:
        return await asyncio.to_thread(fs.ler_agregado, uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("engajamento: agregado indisponível para %s: %s", uid, exc)
        return {"_indisponivel": True}


async def _consumir_congeladores(uid: str, dias: list[str]) -> None:
    """Gasta congeladores para salvar a ofensiva — e só isso.

    `calcular_ofensiva` já garantiu que estes dias SALVAM a sequência; aqui só
    persistimos. O `$inc` negativo com a guarda `congeladores >= len(dias)` na
    própria consulta impede que duas requisições simultâneas do mesmo aluno
    (duas abas abertas) gastem o mesmo congelador duas vezes.
    """
    if not dias:
        return
    try:
        await _db.engajamento_perfil.update_one(
            {"_id": uid, "congeladores": {"$gte": len(dias)}},
            {
                "$inc": {"congeladores": -len(dias)},
                "$addToSet": {"dias_congelados": {"$each": dias}},
                "$set": {"atualizado_em": _now_iso()},
            },
        )
        logger.info("Ofensiva de %s salva por congelador nos dias %s.", uid, dias)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao consumir congelador de %s", uid)


def _semana_visual(dias_ativos: list[str], congelados: list[str], hoje: str) -> list[dict[str, Any]]:
    """Os 7 dias até hoje, para as bolinhas da interface. Nunca inventa
    atividade: um dia só acende se houver evento real (ou congelador gasto)."""
    ativos, frios = set(dias_ativos), set(congelados)
    base = date.fromisoformat(hoje)
    saida = []
    for i in range(6, -1, -1):
        d = (base - timedelta(days=i)).isoformat()
        saida.append({
            "dia": d,
            "ativo": d in ativos,
            "congelado": d in frios and d not in ativos,
            "hoje": i == 0,
        })
    return saida


async def _liga(uid: str, semana: str, *, nome: str | None = None) -> dict[str, Any]:
    """Ranking da divisão do aluno nesta semana.

    Sem bots e sem preenchimento: se só há três pessoas na divisão, o ranking
    mostra três pessoas. Ver a linha ética em `engajamento.py`.
    """
    minha = await _db.liga_semana.find_one({"_id": f"{uid}:{semana}"})
    liga_id = (minha or {}).get("liga_id") or await _liga_de_entrada(uid, semana)
    filtro = {"semana": semana, "liga_id": liga_id}

    total = await _db.liga_semana.count_documents(filtro)
    cursor = _db.liga_semana.find(filtro, {"_id": 0}).sort([("pontos", -1), ("atualizado_em", 1)]).limit(eng.TAMANHO_GRUPO)
    linhas = await cursor.to_list(length=eng.TAMANHO_GRUPO)

    tabela = [
        {
            "posicao": i + 1,
            "uid": l.get("uid"),
            "nome": l.get("nome") or "Aluno",
            "pontos": int(l.get("pontos") or 0),
            "voce": l.get("uid") == uid,
        }
        for i, l in enumerate(linhas)
    ]
    minha_posicao = next((l["posicao"] for l in tabela if l["voce"]), None)
    if minha_posicao is None and minha:
        # Fora dos 30 primeiros: a posição real é contada, nunca omitida —
        # esconder onde a pessoa está é pior do que ela estar em 41º.
        acima = await _db.liga_semana.count_documents({**filtro, "pontos": {"$gt": int(minha.get("pontos") or 0)}})
        minha_posicao = acima + 1

    info = eng.liga_por_id(liga_id)
    return {
        "id": liga_id,
        "nome": info["nome"],
        "cor": info["cor"],
        "indice": [l["id"] for l in eng.LIGAS].index(liga_id),
        "semana": semana,
        "fecha_em": eng.fim_da_semana(semana),
        "tabela": tabela,
        "total": total,
        "minha_posicao": minha_posicao,
        "meus_pontos": int((minha or {}).get("pontos") or 0),
        "sobem": eng.SOBEM,
        "caem": eng.CAEM,
    }


# ---------------------------------------------------------------------------
# Ações do aluno
# ---------------------------------------------------------------------------

async def resgatar_missao(uid: str, missao_id: str) -> dict[str, Any]:
    """Paga a missão cumprida, uma vez só.

    Duas travas, de propósito redundantes: o `$ne` no filtro do Mongo (que
    torna o resgate um vencedor único entre requisições concorrentes) e a chave
    determinística no Firestore (`grant_sparks_evento`), que não paga duas
    vezes o mesmo `dia:missao` nem que o Mongo seja restaurado de um backup.
    """
    dia = _hoje()
    doc_dia = (await _db.engajamento_dia.find_one({"_id": f"{uid}:{dia}"})) or {}
    missoes = eng.missoes_do_dia(uid, dia, doc_dia.get("contadores") or {}, doc_dia.get("resgatadas") or [])
    missao = next((m for m in missoes if m["id"] == missao_id), None)

    if missao is None:
        return {"ok": False, "motivo": "Esta missão não é uma das suas de hoje."}
    if not missao["concluida"]:
        return {"ok": False, "motivo": "Missão ainda não concluída."}
    if missao["resgatada"]:
        return {"ok": False, "motivo": "Você já resgatou esta missão."}

    marcado = await _db.engajamento_dia.update_one(
        {"_id": f"{uid}:{dia}", "resgatadas": {"$ne": missao_id}},
        {"$addToSet": {"resgatadas": missao_id}},
    )
    if marcado.modified_count == 0:
        return {"ok": False, "motivo": "Você já resgatou esta missão."}

    concessao = await asyncio.to_thread(
        fs.grant_sparks_evento,
        uid,
        categoria="missoes",
        chave=f"{dia}:{missao_id}",
        amount=missao["sparks"],
        meta={"titulo": missao["titulo"]},
    )
    await registrar_acao(uid, ["missao_concluida"])
    saldo = await asyncio.to_thread(fs.read_sparks_balance, uid)
    return {
        "ok": True,
        "sparks_ganhos": concessao.get("sparks_ganhos", 0),
        "sparks_balance": saldo,
        "xp_ganho": eng.XP_POR_ACAO["missao_concluida"],
    }


async def comprar_congelador(uid: str) -> dict[str, Any]:
    """Compra um congelador de ofensiva.

    O preço é fixo e anunciado antes (`CUSTO_CONGELADOR`), o teto é `MAX_
    CONGELADORES`, e o débito acontece ANTES do crédito do item — se a escrita
    do item falhar, os Sparks voltam. Não existe versão "com desconto para quem
    está prestes a perder a sequência": preço que reage ao desespero é a
    definição de dark pattern.
    """
    perfil = (await _db.engajamento_perfil.find_one({"_id": uid})) or {}
    atuais = int(perfil.get("congeladores") or 0)
    if atuais >= eng.MAX_CONGELADORES:
        return {"ok": False, "motivo": f"Você já tem o máximo de {eng.MAX_CONGELADORES} congeladores."}

    try:
        saldo = await asyncio.to_thread(fs.deduct_sparks, uid, eng.CUSTO_CONGELADOR)
    except fs.InsufficientSparksError as exc:
        return {"ok": False, "motivo": f"Faltam {exc.needed - exc.balance} Sparks.", "faltam": exc.needed - exc.balance}

    try:
        await _db.engajamento_perfil.update_one(
            {"_id": uid},
            {"$inc": {"congeladores": 1}, "$set": {"uid": uid, "atualizado_em": _now_iso()}},
            upsert=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Congelador não creditado para %s — devolvendo Sparks", uid)
        saldo = await asyncio.to_thread(fs.refund_sparks, uid, eng.CUSTO_CONGELADOR)
        return {"ok": False, "motivo": "Não foi possível concluir agora. Seus Sparks foram devolvidos."}

    return {"ok": True, "congeladores": atuais + 1, "sparks_balance": saldo}


async def somar_ao_perfil(uid: str, campo: str, quantidade: int = 1) -> None:
    """Contadores de vida inteira que alimentam conquistas (redações
    corrigidas, respostas úteis). Separado de `registrar_acao` porque não são
    XP nem contador do dia — são marcos permanentes."""
    if _db is None:
        return
    try:
        await _db.engajamento_perfil.update_one(
            {"_id": uid}, {"$inc": {campo: quantidade}, "$set": {"uid": uid}}, upsert=True
        )
    except Exception:  # noqa: BLE001
        logger.exception("somar_ao_perfil(%s, %s) falhou para %s", campo, quantidade, uid)
