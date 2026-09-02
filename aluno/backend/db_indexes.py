"""Índices do MongoDB, criados no startup.

O banco não tinha nenhum índice. Três consequências, da mais grave para a
menos:

* **`user_sessions.session_token`** — `auth._resolve_user` roda em TODA
  requisição autenticada e fazia varredura completa de uma coleção que cresce
  um documento por login e nunca era limpa. Instantâneo com 10 alunos,
  degradação contínua e silenciosa a partir daí. O TTL em `expires_at` resolve
  a outra metade: sessão vencida some sozinha em vez de acumular para sempre.

* **`users.email` único** — sem ele o "e-mail já registrado" de `/auth/signup`
  é uma corrida: dois cadastros simultâneos com o mesmo e-mail criam duas
  contas, e a partir daí o login pega uma das duas arbitrariamente.

* **`webhook_events.dedupe_key` único** — é a garantia atômica de que uma
  notificação repetida do Mercado Pago não é processada duas vezes
  (`sparks_payments_service.dedupe_or_skip` conta com o `DuplicateKeyError`).
  Sem o índice, o `insert_one` sempre passa e o dedupe silenciosamente não
  existe.

`create_index` é idempotente: chamar de novo com a mesma especificação não faz
nada. Falha de criação é logada e NÃO derruba o processo — um índice ausente
deixa o app lento ou sem uma trava, mas subir sem app nenhum é pior.

O TTL do Mongo compara um campo BSON de data. `expires_at` é gravado como
string ISO (`UserSession`), e sobre string o TTL simplesmente não roda — daí
`expires_at_dt`, escrito junto em `auth._create_session` só para o índice.
"""
from __future__ import annotations

import logging

import pymongo

logger = logging.getLogger("sapiens.indexes")

# (coleção, chaves, kwargs) — kwargs vai direto para `create_index`.
INDICES: list[tuple[str, list[tuple[str, int]], dict]] = [
    # --- sessão: o caminho quente de toda requisição autenticada ---
    ("user_sessions", [("session_token", pymongo.ASCENDING)],
     {"name": "session_token_unico", "unique": True}),
    ("user_sessions", [("expires_at_dt", pymongo.ASCENDING)],
     {"name": "sessao_ttl", "expireAfterSeconds": 0}),
    ("user_sessions", [("user_id", pymongo.ASCENDING)],
     {"name": "sessoes_por_usuario"}),  # base do "sair de todos os dispositivos"

    # --- identidade ---
    ("users", [("email", pymongo.ASCENDING)], {"name": "email_unico", "unique": True}),
    ("users", [("user_id", pymongo.ASCENDING)], {"name": "user_id_unico", "unique": True}),

    # --- acervo: filtros de /api/questoes e /api/provas ---
    ("questoes_public", [("item_id", pymongo.ASCENDING)], {"name": "item_id_idx"}),
    ("questoes_public", [
        ("fonte.banca", pymongo.ASCENDING),
        ("fonte.ano", pymongo.ASCENDING),
        ("fonte.prova", pymongo.ASCENDING),
        ("fonte.numero", pymongo.ASCENDING),
    ], {"name": "bloco_idx"}),
    ("questoes_master", [("id", pymongo.ASCENDING)], {"name": "master_id_idx"}),

    # --- histórico do aluno ---
    ("analyses", [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "analises_do_aluno"}),
    ("analyses", [("analysis_id", pymongo.ASCENDING)], {"name": "analysis_id_idx"}),

    # --- pagamentos ---
    # `mp_payment_id` único fecha a última brecha de crédito duplicado: mesmo
    # que dois webhooks passem juntos pelo dedupe, só um registro existe.
    ("sparks_payments", [("mp_payment_id", pymongo.ASCENDING)],
     {"name": "mp_payment_id_unico", "unique": True, "sparse": True}),
    ("sparks_payments", [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "compras_do_aluno"}),
    ("sparks_auto_recharge", [("user_id", pymongo.ASCENDING)],
     {"name": "recarga_do_aluno_unica", "unique": True}),
    ("sparks_auto_recharge", [("mp_preapproval_id", pymongo.ASCENDING)],
     {"name": "preapproval_idx"}),
    ("webhook_events", [("dedupe_key", pymongo.ASCENDING)],
     {"name": "dedupe_key_unico", "unique": True}),
    # Notificação já processada não precisa ficar guardada para sempre; 30 dias
    # cobrem com folga a janela de reenvio do Mercado Pago.
    ("webhook_events", [("received_at_dt", pymongo.ASCENDING)],
     {"name": "webhook_ttl", "expireAfterSeconds": 30 * 24 * 3600}),

    # --- redação e aulas particulares ---
    ("redacoes", [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "redacoes_do_aluno"}),
    ("redacoes", [("redacao_id", pymongo.ASCENDING)], {"name": "redacao_id_idx"}),
    ("redacao_avaliacoes", [("redacao_id", pymongo.ASCENDING)], {"name": "avaliacao_por_redacao"}),
    ("aulas_particulares", [("created_at", pymongo.DESCENDING)], {"name": "aulas_recentes"}),

    # --- monitoramento ---
    ("client_errors", [("recebido_em_dt", pymongo.ASCENDING)],
     {"name": "client_errors_ttl", "expireAfterSeconds": 30 * 24 * 3600}),

    # --- recuperação de senha ---
    ("password_resets", [("token_hash", pymongo.ASCENDING)],
     {"name": "reset_token_unico", "unique": True}),
    ("password_resets", [("expires_at_dt", pymongo.ASCENDING)],
     {"name": "reset_ttl", "expireAfterSeconds": 0}),
]


async def _equivalente_ja_existe(db, colecao: str, chaves: list[tuple[str, int]], kwargs: dict) -> bool:
    """Já existe um índice com as MESMAS chaves e a mesma unicidade, só que com
    outro nome?

    Acontece quando o índice foi criado antes deste módulo existir (à mão, ou
    por uma versão anterior do código): o Mongo gera nomes como `dedupe_key_1`
    e recusa recriá-lo com nome diferente. A garantia que importa — as chaves e
    o `unique` — está de pé, então isso é sucesso, não falha.

    Só o nome é ignorado. Um índice com as mesmas chaves mas SEM `unique`
    continua sendo falha, porque aí a trava de verdade não existe.
    """
    try:
        existentes = await db[colecao].index_information()
    except Exception:  # noqa: BLE001
        return False
    alvo_chaves = [list(par) for par in chaves]
    alvo_unico = bool(kwargs.get("unique", False))
    for info in existentes.values():
        mesmas_chaves = [list(par) for par in info.get("key", [])] == alvo_chaves
        if mesmas_chaves and bool(info.get("unique", False)) == alvo_unico:
            return True
    return False


async def criar_indices(db) -> dict[str, int]:
    """Cria (idempotentemente) todos os índices. Devolve quantos foram
    processados e quantos falharam — o chamador loga, ninguém aborta."""
    criados = 0
    falhas = 0
    for colecao, chaves, kwargs in INDICES:
        try:
            await db[colecao].create_index(chaves, **kwargs)
            criados += 1
        except Exception as exc:  # noqa: BLE001
            # Conflito de NOME com um índice equivalente não é problema — e
            # deixá-lo virar WARNING a cada boot afogaria a falha que importa
            # no meio do ruído.
            if await _equivalente_ja_existe(db, colecao, chaves, kwargs):
                criados += 1
                logger.info(
                    "Índice %s.%s já existe sob outro nome — garantia mantida.",
                    colecao, kwargs.get("name", chaves),
                )
                continue
            falhas += 1
            # Causa mais comum: dado pré-existente que viola um índice único
            # (ex.: dois usuários com o mesmo e-mail criados antes desta
            # trava existir). O log diz qual, para a limpeza ser dirigida.
            logger.warning(
                "Índice %s.%s não pôde ser criado: %s",
                colecao, kwargs.get("name", chaves), exc,
            )
    return {"criados": criados, "falhas": falhas}
