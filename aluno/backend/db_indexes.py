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
    # Reivindicações de cobrança (`redacao_routes`). A busca por chave usa o
    # `_id` (`user:chave`), que já é único e indexado pelo Mongo — o índice
    # aqui é só para a varredura por usuário numa eventual auditoria de
    # cobrança. NÃO tem TTL de propósito: uma reivindicação concluída é o
    # comprovante de que aquele aluno já pagou por aquela correção; apagá-la
    # devolveria a chave ao pool e um retry tardio cobraria de novo.
    ("redacao_cobrancas", [("user_id", pymongo.ASCENDING), ("criado_em", pymongo.DESCENDING)],
     {"name": "cobrancas_do_aluno"}),
    ("redacao_feedbacks", [("user_id", pymongo.ASCENDING)], {"name": "feedbacks_do_aluno"}),
    ("aulas_particulares", [("created_at", pymongo.DESCENDING)], {"name": "aulas_recentes"}),

    # Reivindicações de geração de questões novas do banco de treino
    # (`treino_routes`). Mesmo desenho de `redacao_cobrancas`: `_id`
    # (`user:chave`) já é único por padrão do Mongo, este índice é só para
    # auditoria por usuário. Sem TTL: uma reivindicação concluída prova que o
    # pedido já foi feito e os Sparks já foram devolvidos.
    ("treino_geracoes", [("user_id", pymongo.ASCENDING), ("criado_em", pymongo.DESCENDING)],
     {"name": "geracoes_treino_do_aluno"}),

    # Questões novas geradas por IA (`treino_routes.gerar_questoes`), salvas
    # para reaproveitamento entre alunos: a primeira pessoa a pedir prática
    # numa habilidade paga a geração, e ela fica disponível para os próximos.
    ("treino_questoes_ia", [("hab_id", pymongo.ASCENDING)],
     {"name": "questoes_ia_por_habilidade"}),
    ("treino_questoes_ia", [("mostrada_para", pymongo.ASCENDING), ("gerada_em", pymongo.DESCENDING)],
     {"name": "questoes_ia_do_aluno"}),

    # --- cache do agregado derivado do Firestore ---
    # Ver `annotation_service._agregado_com_cache`: troca N leituras do
    # Firestore (uma por evento de behavior do aluno) por 1. O documento é
    # descartável — o TTL só evita que a coleção cresça sem fim conforme os
    # alunos vão respondendo e as chaves antigas deixam de ser consultadas.
    ("perfil_derivado_cache", [("expurgo_em_dt", pymongo.ASCENDING)],
     {"name": "perfil_derivado_cache_ttl", "expireAfterSeconds": 0}),
    ("perfil_derivado_cache", [("user_id", pymongo.ASCENDING)],
     {"name": "perfil_derivado_por_aluno"}),

    # --- chat da Mentis ---
    # A busca por sessão ativa (`mentis_routes._sessao_ativa`) roda em toda
    # abertura do chat e em toda mensagem enviada: filtra por aluno e por
    # validade, ordenando pela mais recente — as três colunas do índice.
    ("mentis_sessoes", [("user_id", pymongo.ASCENDING), ("expira_em", pymongo.DESCENDING),
                        ("criada_em", pymongo.DESCENDING)],
     {"name": "sessao_ativa_do_aluno"}),
    # A conversa deixa de ser útil muito depois de a sessão vencer; 30 dias
    # dão margem para suporte olhar um caso sem guardar histórico para sempre.
    ("mentis_sessoes", [("expurgo_em_dt", pymongo.ASCENDING)],
     {"name": "mentis_sessoes_ttl", "expireAfterSeconds": 0}),

    # --- monitoramento ---
    ("client_errors", [("recebido_em_dt", pymongo.ASCENDING)],
     {"name": "client_errors_ttl", "expireAfterSeconds": 30 * 24 * 3600}),

    # --- sugestões de correção de questão (bandeira) ---
    ("question_reports", [("report_id", pymongo.ASCENDING)],
     {"name": "report_id_unico", "unique": True}),
    ("question_reports", [("item_id", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING)],
     {"name": "reportes_por_questao"}),
    ("question_reports", [("status", pymongo.ASCENDING)], {"name": "reportes_por_status"}),

    # --- reclamações e sugestões sobre o produto ---
    ("sugestoes", [("sugestao_id", pymongo.ASCENDING)],
     {"name": "sugestao_id_unico", "unique": True}),
    # A lista do aluno é sempre "as minhas, da mais recente para a mais
    # antiga" — sem este índice ela vira varredura da coleção inteira.
    ("sugestoes", [("student_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "sugestoes_por_aluno"}),
    ("sugestoes", [("status", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "sugestoes_por_status"}),

    # --- códigos de promoção ---
    # `validar_e_registrar_uso` faz `find_one_and_update` por `code`; a
    # unicidade é o que impede o admin de criar dois códigos iguais numa
    # corrida entre duas abas do painel.
    ("promo_codes", [("code", pymongo.ASCENDING)], {"name": "promo_code_unico", "unique": True}),

    # --- cronograma ---
    # O documento do cronograma tem `_id = user_id`, então a leitura da tela
    # já é busca por chave primária e não precisa de índice nenhum. Este aqui
    # é só para a auditoria por data ("quantos alunos remontaram a semana
    # depois da mudança X") não virar varredura da coleção.
    ("cronogramas", [("atualizado_em", pymongo.DESCENDING)],
     {"name": "cronogramas_por_atualizacao"}),
    # `cronograma_llm_chamadas` NÃO ganha índice, pelo mesmo motivo de
    # `mentis_llm_chamadas` e `redacao_llm_chamadas`: `llm_telemetry.persist`
    # grava `criado_em` como string ISO, e TTL sobre string não roda (é a
    # armadilha descrita no topo deste arquivo). Um índice TTL ali seria uma
    # limpeza que nunca acontece com cara de limpeza configurada.

    # --- recuperação de senha ---
    ("password_resets", [("token_hash", pymongo.ASCENDING)],
     {"name": "reset_token_unico", "unique": True}),
    ("password_resets", [("expires_at_dt", pymongo.ASCENDING)],
     {"name": "reset_ttl", "expireAfterSeconds": 0}),

    # --- engajamento (ofensiva, XP, missões, liga) ---
    # `engajamento_perfil` e `engajamento_dia` têm `_id` determinístico
    # (`uid` e `uid:dia`), então a leitura já é por chave primária.
    # O TTL existe porque `engajamento_dia` cresce um documento por aluno por
    # DIA e não é fonte de verdade de nada: o histórico real são os eventos de
    # behavior no Firestore. Sem ele, a coleção cresce para sempre guardando
    # contadores de missão de 2027.
    ("engajamento_dia", [("expurgo_em_dt", pymongo.ASCENDING)],
     {"name": "engajamento_dia_ttl", "expireAfterSeconds": 0}),
    # A consulta quente da liga: ranking de uma divisão numa semana, ordenado
    # por pontos. Sem este índice, cada abertura da tela varre a coleção
    # inteira — e a tela da liga é justamente a que se atualiza muitas vezes
    # no domingo à noite.
    ("liga_semana", [
        ("semana", pymongo.ASCENDING),
        ("liga_id", pymongo.ASCENDING),
        ("pontos", pymongo.DESCENDING),
    ], {"name": "liga_ranking"}),
    # `_liga_de_entrada` busca a última semana do aluno para aplicar subida
    # ou descida.
    ("liga_semana", [("uid", pymongo.ASCENDING), ("semana", pymongo.DESCENDING)],
     {"name": "liga_por_aluno"}),

    # --- comunidade (mural de dúvidas) ---
    ("comunidade_duvidas", [("duvida_id", pymongo.ASCENDING)],
     {"name": "duvida_id_unico", "unique": True}),
    # O mural: filtra por status e área, ordena por data. É a consulta que roda
    # a cada abertura da aba.
    ("comunidade_duvidas", [
        ("status", pymongo.ASCENDING),
        ("area", pymongo.ASCENDING),
        ("created_at", pymongo.DESCENDING),
    ], {"name": "mural_por_area"}),
    ("comunidade_duvidas", [("student_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "duvidas_do_aluno"}),
    ("comunidade_respostas", [("resposta_id", pymongo.ASCENDING)],
     {"name": "resposta_id_unico", "unique": True}),
    ("comunidade_respostas", [("duvida_id", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING)],
     {"name": "respostas_da_duvida"}),
    # Teto diário de Sparks por respostas úteis (`comunidade.MAX_SPARKS_DIA`):
    # sem índice, a contagem varre todas as respostas da plataforma a cada
    # "marcar melhor resposta".
    ("comunidade_respostas", [
        ("student_id", pymongo.ASCENDING),
        ("melhor", pymongo.ASCENDING),
        ("pago_em_dia", pymongo.ASCENDING),
    ], {"name": "teto_diario_sparks"}),
    # O voto único por (tipo, alvo, pessoa) é garantido pelo `_id`
    # determinístico; este índice serve à consulta "o que EU já votei nesta
    # thread", que a tela faz uma vez por abertura.
    ("comunidade_votos", [("uid", pymongo.ASCENDING), ("alvo", pymongo.ASCENDING)],
     {"name": "votos_do_aluno"}),
    ("comunidade_reportes", [("resolvido", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
     {"name": "fila_de_moderacao"}),
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
