"""Direitos do titular (LGPD art. 18) — exportar e excluir os dados do aluno.

A Política de Privacidade publicada promete três coisas com prazo de 15 dias:
cópia dos dados, exclusão e portabilidade. Prometer isso sem ter como cumprir
é pior do que não prometer — e cumprir à mão, numa base espalhada por 20
coleções do Mongo mais uma árvore de subcoleções do Firestore, é o tipo de
tarefa em que esquecer um lugar não gera erro nenhum: só deixa dado de menor
de idade para trás, em silêncio.

Por isso o inventário abaixo é DECLARATIVO e vive num lugar só. Coleção nova
que guarde dado de aluno precisa entrar aqui; `tests/test_dados_pessoais.py`
tem um teste que varre o código à procura de coleções esquecidas e falha
quando aparece uma que este módulo não conhece.

O QUE NÃO ENTRA, e por quê:

* `mentis_explicacoes`, `mentis_intervencoes`, `treino_conceitos` — cache de
  LLM por hash do conteúdo, compartilhado entre alunos. Não tem identidade.
* `mentis_llm_chamadas`, `redacao_llm_chamadas` — telemetria de custo, sem
  identidade (conferido: nenhum campo de usuário).
* `autorrelato_pares` — contador anônimo por par (erro, processo). O relato do
  aluno em si mora no evento de behavior, que É apagado; o que fica é um
  agregado já anonimizado, que a LGPD não alcança (art. 12).
* `questoes_public`, `questoes_master`, `exams`, `answer_keys`, `feed_items` —
  acervo, não dado pessoal.

O ÚNICO dado que sobrevive à exclusão é o registro de pagamento, anonimizado:
ver `_anonimizar_pagamentos`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sapiens.dados_pessoais")

_db = None


def set_db(db):
    global _db
    _db = db


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


# Coleções cujos documentos pertencem a UM aluno, localizáveis por um campo
# com o `user_id`. Exportadas inteiras e apagadas inteiras.
COLECOES_POR_USUARIO: tuple[tuple[str, str], ...] = (
    ("users", "user_id"),
    ("user_sessions", "user_id"),
    ("password_resets", "user_id"),
    ("analyses", "user_id"),
    ("redacoes", "user_id"),
    ("redacao_cobrancas", "user_id"),
    ("redacao_feedbacks", "user_id"),
    ("sparks_auto_recharge", "user_id"),
    ("mentis_sessoes", "user_id"),
    ("feed_interactions", "user_id"),
    ("feed_progress", "user_id"),
    ("question_reports", "user_id"),
    ("sugestoes", "user_id"),
    ("aulas_particulares", "user_id"),
    # Quem pagou a aula ao vivo de quinta e em quais cursos se inscreveu para
    # ser avisado. É histórico de consumo do titular — sai com a conta. O
    # registro de que a edição aconteceu não depende disto (é o documento de
    # configuração, que não tem aluno nenhum dentro).
    ("cursos_live_acessos", "user_id"),
    ("cursos_acessos", "user_id"),
    ("cursos_interesse", "user_id"),
    ("treino_geracoes", "user_id"),
    ("perfil_derivado_cache", "user_id"),
    ("client_errors", "user_id"),
    # A agenda do aluno é o dado mais íntimo que o produto guarda: diz onde
    # ele está, em que horário, todos os dias da semana. Sai inteira com a
    # conta, pelo `student_id` que `cronograma_routes._gravar` sempre grava.
    ("cronogramas", "student_id"),
    # O que o aluno declarou sobre si no primeiro acesso: objetivo, tempo
    # disponível, meta no ENEM e onde ELE diz ter dificuldade. É declaração do
    # titular sobre a própria vida — sai inteira com a conta, pelo mesmo
    # `student_id` que `onboarding_routes._gravar` sempre grava.
    ("onboarding_perfil", "student_id"),
    # Engajamento: XP, ofensiva, missões e posição na liga. Tudo é perfil de
    # comportamento do titular e sai inteiro — inclusive `liga_semana`, que
    # guarda o NOME exibido no ranking.
    ("engajamento_perfil", "uid"),
    ("engajamento_dia", "uid"),
    ("liga_semana", "uid"),
    # Voto na comunidade é opinião individual identificada: sai com a conta.
    # A contagem agregada no conteúdo votado não é reconstruível a partir de
    # quem votou, então ela fica (art. 12).
    ("comunidade_votos", "uid"),
)

# Coleções que guardam dado de aluno mas NÃO cabem no padrão acima — cada uma
# tem um motivo, tratado explicitamente em `excluir`.
COLECOES_TRATAMENTO_ESPECIAL: tuple[str, ...] = (
    "sparks_payments",            # anonimizada, não apagada (art. 16, I)
    "redacao_avaliacoes",         # pende de `redacao_id`, não de `user_id`
    "treino_questoes_ia",         # `$pull` do aluno; a questão é conteúdo e fica
    "mentis_intervencoes_abertas",  # `_id` composto `"{uid}|{chave}"`
    # Mural de dúvidas: ANONIMIZADO, não apagado. Ver `_anonimizar_comunidade`.
    "comunidade_duvidas",
    "comunidade_respostas",
    "comunidade_reportes",
)

# Coleções SEM dado pessoal, classificadas de propósito para que o teste de
# completude do inventário saiba que elas foram consideradas — e não fique
# calado sobre uma coleção nova só porque ninguém a listou.
COLECOES_SEM_DADO_PESSOAL: tuple[str, ...] = (
    # Acervo e conteúdo
    "exams", "answer_keys", "questoes_public", "questoes_master", "feed_items",
    "question_annotations", "promo_codes",
    # Link do Meet e tema de cada edição da aula ao vivo: conteúdo publicado
    # pelo admin, chaveado pela DATA da edição. Nenhum aluno dentro.
    "cursos_config",
    # Caches de LLM: chaveados por hash do conteúdo, compartilhados entre alunos
    "mentis_explicacoes", "mentis_intervencoes", "treino_conceitos",
    # Telemetria de custo: sem campo de usuário
    "mentis_llm_chamadas", "redacao_llm_chamadas", "cronograma_llm_chamadas",
    # Contador anônimo por par (erro, processo). O relato do aluno mora no
    # evento de behavior, que é apagado; isto é agregado, fora da LGPD (art. 12)
    "autorrelato_pares",
    # Registro operacional de notificação do Mercado Pago. Guarda `data_id` do
    # pagamento, nunca o aluno — e o pagamento em si é anonimizado na exclusão
    "webhook_events", "webhook_recebimentos",
)

# Campos que NUNCA saem numa exportação: credencial ou material de sessão.
# Entregar o hash da senha ao titular não atende direito nenhum e cria um
# alvo offline; entregar token de sessão é entregar a própria sessão.
CAMPOS_SENSIVEIS = ("password_hash", "session_token", "token_hash")

# Subcoleções de `students/{uid}` no Firestore. `recursive_delete` apaga todas
# sozinho; esta lista é para a EXPORTAÇÃO, que precisa saber o que ler.
SUBCOLECOES_FIRESTORE = (
    "behavior",
    "perfil_cognitivo",
    "sparks_rounds",
    "sparks_purchases",
    "sparks_questoes",
    "sparks_reports",
    "sparks_admin_grants",
    # Concedidas por `firestore_service.grant_sparks_evento` — o nome da
    # subcoleção é `sparks_{categoria}`. Cada categoria nova precisa entrar
    # aqui, senão o comprovante daquele ganho não sai na exportação.
    "sparks_missoes",
    "sparks_comunidade",
)

TOMBSTONE = "<titular-excluido>"


def _limpar(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in CAMPOS_SENSIVEIS and k != "_id"}


# ---------------------------------------------------------------------------
# Exportação (art. 18, II e V — acesso e portabilidade)
# ---------------------------------------------------------------------------

async def exportar(user_id: str) -> dict[str, Any]:
    """Tudo o que guardamos sobre `user_id`, em JSON.

    Lê o Firestore evento a evento (O(eventos) do aluno). É a única rota do
    produto que faz isso de propósito: não está em caminho quente, é pedida
    explicitamente pelo titular e tem limite de taxa próprio. O agregado usado
    no resto do app não serve aqui — ele é um resumo, e portabilidade é o dado.
    """
    export: dict[str, Any] = {
        "gerado_em": _agora(),
        "user_id": user_id,
        "aviso": (
            "Cópia dos seus dados pessoais no Sapiens (LGPD art. 18). Não inclui "
            "senha nem tokens de sessão, que são credenciais e não dados pessoais "
            "no sentido do artigo."
        ),
        "mongo": {},
        "firestore": {},
    }

    for colecao, campo in COLECOES_POR_USUARIO:
        try:
            docs = await _db[colecao].find({campo: user_id}).to_list(10000)
            if docs:
                export["mongo"][colecao] = [_limpar(d) for d in docs]
        except Exception:  # noqa: BLE001
            logger.exception("exportar: falha lendo %s", colecao)
            export["mongo"][colecao] = {"erro": "não foi possível ler esta coleção"}

    # Avaliações de redação não têm `user_id`: pendem de `redacao_id`.
    try:
        ids = [r["redacao_id"] for r in export["mongo"].get("redacoes", []) if r.get("redacao_id")]
        if ids:
            docs = await _db.redacao_avaliacoes.find({"redacao_id": {"$in": ids}}).to_list(10000)
            if docs:
                export["mongo"]["redacao_avaliacoes"] = [_limpar(d) for d in docs]
    except Exception:  # noqa: BLE001
        logger.exception("exportar: falha lendo redacao_avaliacoes")

    # Comunidade: o que o aluno escreveu no mural é dele e tem que sair na
    # cópia. Pende de `student_id` e não do `user_id` padrão, por isso fica
    # fora do laço acima.
    for colecao in ("comunidade_duvidas", "comunidade_respostas"):
        try:
            docs = await _db[colecao].find({"student_id": user_id}).to_list(10000)
            if docs:
                export["mongo"][colecao] = [_limpar(d) for d in docs]
        except Exception:  # noqa: BLE001
            logger.exception("exportar: falha lendo %s", colecao)
            export["mongo"][colecao] = {"erro": "não foi possível ler esta coleção"}

    # Pagamentos: o titular tem direito à própria cópia mesmo sendo o registro
    # que sobrevive à exclusão.
    try:
        docs = await _db.sparks_payments.find({"user_id": user_id}).to_list(10000)
        if docs:
            export["mongo"]["sparks_payments"] = [_limpar(d) for d in docs]
    except Exception:  # noqa: BLE001
        logger.exception("exportar: falha lendo sparks_payments")

    export["firestore"] = await _exportar_firestore(user_id)
    return export


async def _exportar_firestore(user_id: str) -> dict[str, Any]:
    import asyncio

    def _ler() -> dict[str, Any]:
        import firestore_service as fs

        cliente = fs.get_firestore()
        ref = cliente.collection("students").document(user_id)
        snap = ref.get()
        saida: dict[str, Any] = {"students": snap.to_dict() if snap.exists else None}
        for sub in SUBCOLECOES_FIRESTORE:
            docs = [d.to_dict() for d in ref.collection(sub).stream()]
            if docs:
                saida[sub] = docs
        return saida

    try:
        return await asyncio.to_thread(_ler)
    except Exception:  # noqa: BLE001
        logger.exception("exportar: falha lendo Firestore de %s", user_id)
        return {"erro": "não foi possível ler o Firestore"}


# ---------------------------------------------------------------------------
# Exclusão (art. 18, VI)
# ---------------------------------------------------------------------------

async def _anonimizar_pagamentos(user_id: str) -> int:
    """Pagamento não é apagado — é desligado da pessoa.

    A LGPD (art. 16, I) permite guardar o que a lei obriga a guardar, e
    registro de operação financeira é isso: some com ele e a contabilidade
    fica sem lastro, a conciliação com o Mercado Pago passa a acusar cobrança
    órfã, e uma eventual disputa de estorno fica sem prova dos dois lados.

    O que fica: identificador do pagamento, valor, moeda, data, status. O que
    sai: o vínculo com a pessoa. Isso é anonimização, não retenção de dado
    pessoal — ninguém reconstrói o titular a partir do que sobra.
    """
    r = await _db.sparks_payments.update_many(
        {"user_id": user_id},
        {"$set": {"user_id": TOMBSTONE, "titular_excluido_em": _agora()}},
    )
    return r.modified_count


async def _anonimizar_comunidade(user_id: str) -> dict[str, int]:
    """O mural é conversa entre pessoas: o titular sai, a conversa fica.

    Apagar a dúvida de quem pediu a conta de volta destruiria junto as
    respostas que OUTROS alunos escreveram — trabalho deles, não dele. E
    apagar a resposta dele arrancaria o meio de uma thread que outra pessoa
    ainda usa para estudar.

    A saída é a mesma de `_anonimizar_pagamentos`: cortar o vínculo com a
    pessoa em vez de destruir o registro. Some o `student_id`, some o nome, e
    o que resta ("Aluno removido" + o texto sobre matemática) não reconstrói o
    titular — é dado anonimizado, fora do alcance da LGPD por força do art. 12.

    O `$pull` em `reportada_por` é o mesmo raciocínio pelo avesso: a lista é
    de PESSOAS e precisa perder esta; o conteúdo moderado continua moderado.
    """
    saida: dict[str, int] = {}
    anonimo = {"student_id": TOMBSTONE, "autor_nome": "Aluno removido", "titular_excluido_em": _agora()}
    for colecao in ("comunidade_duvidas", "comunidade_respostas"):
        try:
            r = await _db[colecao].update_many({"student_id": user_id}, {"$set": anonimo})
            saida[f"{colecao}_anonimizadas"] = r.modified_count
            r2 = await _db[colecao].update_many(
                {"reportada_por": user_id}, {"$pull": {"reportada_por": user_id}}
            )
            saida[f"{colecao}_reportes_desvinculados"] = r2.modified_count
        except Exception:  # noqa: BLE001
            logger.exception("excluir: falha anonimizando %s", colecao)
            saida[colecao] = -1
    # O reporte guarda POR QUE um conteúdo saiu do ar: é prova da decisão de
    # moderação e não pode sumir junto com quem reportou — mas quem reportou,
    # sim, é dado pessoal e vira lápide.
    try:
        r = await _db.comunidade_reportes.update_many(
            {"reportado_por": user_id}, {"$set": {"reportado_por": TOMBSTONE}}
        )
        saida["comunidade_reportes_anonimizados"] = r.modified_count
    except Exception:  # noqa: BLE001
        logger.exception("excluir: falha anonimizando comunidade_reportes")
    return saida


async def excluir(user_id: str) -> dict[str, Any]:
    """Apaga o aluno. Devolve o relatório do que saiu, coleção a coleção.

    O relatório existe para que o pedido possa ser RESPONDIDO com precisão —
    "apagamos X documentos em Y lugares" — e para que uma falha parcial
    apareça em vez de passar por sucesso. Nenhuma etapa aborta a seguinte: se
    o Firestore estiver fora, o Mongo ainda é limpo e o relatório diz o que
    ficou pendente.
    """
    relatorio: dict[str, Any] = {"user_id": user_id, "executado_em": _agora(), "mongo": {}}

    # Antes de apagar `redacoes`, guarda os ids para alcançar as avaliações.
    redacao_ids: list[str] = []
    try:
        docs = await _db.redacoes.find({"user_id": user_id}, {"redacao_id": 1}).to_list(10000)
        redacao_ids = [d["redacao_id"] for d in docs if d.get("redacao_id")]
    except Exception:  # noqa: BLE001
        logger.exception("excluir: não consegui listar redações de %s", user_id)

    relatorio["mongo"]["sparks_payments_anonimizados"] = await _anonimizar_pagamentos(user_id)
    relatorio["mongo"].update(await _anonimizar_comunidade(user_id))

    for colecao, campo in COLECOES_POR_USUARIO:
        try:
            r = await _db[colecao].delete_many({campo: user_id})
            if r.deleted_count:
                relatorio["mongo"][colecao] = r.deleted_count
        except Exception:  # noqa: BLE001
            logger.exception("excluir: falha apagando %s", colecao)
            relatorio["mongo"][colecao] = "erro"

    if redacao_ids:
        try:
            r = await _db.redacao_avaliacoes.delete_many({"redacao_id": {"$in": redacao_ids}})
            relatorio["mongo"]["redacao_avaliacoes"] = r.deleted_count
        except Exception:  # noqa: BLE001
            logger.exception("excluir: falha apagando redacao_avaliacoes")
            relatorio["mongo"]["redacao_avaliacoes"] = "erro"

    # Questão gerada por IA é conteúdo, não dado pessoal — fica. O que sai é o
    # vínculo "este aluno já viu esta questão".
    try:
        r = await _db.treino_questoes_ia.update_many(
            {"mostrada_para": user_id}, {"$pull": {"mostrada_para": user_id}}
        )
        relatorio["mongo"]["treino_questoes_ia_desvinculadas"] = r.modified_count
    except Exception:  # noqa: BLE001
        logger.exception("excluir: falha desvinculando treino_questoes_ia")

    # Desbloqueios da Mentis usam `_id` composto `"{uid}|{chave}"`.
    try:
        import re

        r = await _db.mentis_intervencoes_abertas.delete_many(
            {"_id": {"$regex": f"^{re.escape(user_id)}\\|"}}
        )
        if r.deleted_count:
            relatorio["mongo"]["mentis_intervencoes_abertas"] = r.deleted_count
    except Exception:  # noqa: BLE001
        logger.exception("excluir: falha apagando mentis_intervencoes_abertas")

    relatorio["firestore"] = await _excluir_firestore(user_id)
    logger.warning("EXCLUSÃO DE CONTA concluída para %s: %s", user_id, relatorio)
    return relatorio


async def _excluir_firestore(user_id: str) -> Any:
    import asyncio

    def _apagar() -> int:
        import firestore_service as fs

        cliente = fs.get_firestore()
        ref = cliente.collection("students").document(user_id)
        # Apaga o documento E toda a árvore de subcoleções. Apagar só o
        # documento deixaria `behavior` órfã e legível — no Firestore,
        # subcoleção não morre com o pai.
        return cliente.recursive_delete(ref)

    try:
        return {"documentos_apagados": await asyncio.to_thread(_apagar)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("excluir: Firestore de %s NÃO foi apagado", user_id)
        return {"erro": str(exc)[:200], "pendente": True}
