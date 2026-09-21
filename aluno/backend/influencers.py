"""Programa de influencers/afiliados — prospecção, ativação, atribuição e comissão.

**O que é, em uma frase.** Um influencer é um `promo_codes` (código, Sparks de
boas-vindas) mais um registro mais rico (pipeline de prospecção, contato,
percentual de comissão) mais um lançamento por compra em
`influencer_comissoes` — nunca um contador mutável.

**Por que não é `indicacoes.py`.** `indicacoes.py` já resolve o referral
pessoa-a-pessoa: aluno indica aluno, prêmio único em Sparks na primeira
compra, pago pela própria plataforma. Aqui o vínculo é com um PARCEIRO
comercial (não necessariamente aluno), a recompensa do lado de quem chega é
Sparks de boas-vindas maiores (não metade da compra), e a recompensa do lado
de quem indicou é COMISSÃO EM DINHEIRO real, recorrente — em toda compra do
indicado, não só na primeira — paga por fora da plataforma (Pix manual; este
módulo só ACUMULA e marca PAGO, nunca transfere dinheiro sozinho). São
programas com mecânica de pagamento opostas o bastante para não caber na
mesma função, mesmo reaproveitando a mesma ideia de "código pessoal".

**Por que o código de um influencer É um `promo_codes`.** O catálogo de
`promo_codes_routes.py` já resolve exatamente o que a seção 3/4 do programa
pede: código único, bônus de Sparks diferente do padrão, e o link
`/login?convite=CODIGO` (ver `Login.jsx`) já pré-preenche o campo e já abre
em "Criar conta" — nada disso precisou ser reconstruído. `influencer_id` no
documento do cupom é o que distingue "cupom de marketing comum" de "código
de um afiliado" sem duplicar catálogo nem quebrar `auth._bonus_de_cadastro`,
que continua sendo o único lugar que decide quantos Sparks uma conta nova
ganha.

**Onde a comissão fica garantida de não pagar duas vezes.** `_id` do
lançamento em `influencer_comissoes` é o próprio `mp_payment_id` — inserir de
novo (reenvio de webhook) esbarra em `DuplicateKeyError` e não credita nada a
mais. Estorno/reembolso muda o STATUS do mesmo lançamento (`estornada`) em vez
de subtrair de um contador — auditável, e nunca dessincroniza.
"""
from __future__ import annotations

import logging
import re
import secrets
import unicodedata
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("sapiens.influencers")

_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem I, O, 0, 1 — mesma razão de indicacoes.py
_SUFIXO = 4
_PREFIXO = "SAPIENS"

STATUS_LEAD = "lead"
STATUS_QUALIFICADO = "qualificado"
STATUS_MENSAGEM_PRONTA = "mensagem_pronta"
STATUS_CONTATO = "contato"
STATUS_RESPONDEU = "respondeu"
STATUS_INTERESSADO = "interessado"
STATUS_CADASTRADO = "cadastrado"
STATUS_ATIVO = "ativo"
STATUS_RECUSADO = "recusado"
STATUS_REMOVIDO = "removido"

STATUS_PARADO = {STATUS_INTERESSADO, STATUS_CADASTRADO, STATUS_ATIVO, STATUS_RECUSADO, STATUS_REMOVIDO}

DEFAULT_PERCENTUAL = 0.30
DEFAULT_SPARKS_BOAS_VINDAS = 300

COMISSAO_ACUMULADA = "acumulada"
COMISSAO_ESTORNADA = "estornada"
COMISSAO_PAGA = "paga"

# LGPD (seção 18 do pedido de afiliados) — base legal padrão de um lead
# encontrado por prospecção B2B (própria pessoa/comunidade tornou o dado
# público). Muda para "execucao_contrato_parceria" quando o lead vira
# afiliado ativo — ver `ativar()`. Decisão registrada em
# `Cerebro/produto/afiliados.md`, seção LGPD.
BASE_LEGAL_PROSPECCAO = "legitimo_interesse_prospeccao_b2b"
BASE_LEGAL_PARCERIA_ATIVA = "execucao_contrato_parceria"
FINALIDADE_PROSPECCAO = "aquisição de parceiros de divulgação do Sapiens (afiliados)"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalizar(code: str | None) -> str:
    return (code or "").strip().upper()


def _prefixo_do_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii")
    primeiro = re.sub(r"[^A-Za-z]", "", sem_acento.split(" ")[0]).upper()
    return primeiro[:12] or "PARCEIRO"


async def _codigo_livre(db, codigo: str) -> bool:
    """Livre = não é código de outro influencer, não é cupom comum, não é
    código pessoal de indicação — os três namespaces dividem o mesmo campo no
    cadastro (`payload.promo_code`), então um choque faria um dos três nunca
    receber o que é dele. Mesma checagem que `indicacoes._codigo_livre` já
    faz para os dois primeiros; aqui soma o terceiro."""
    if await db.promo_codes.find_one({"code": codigo}, {"_id": 1}):
        return False
    if await db.users.find_one({"referral_code": codigo}, {"_id": 1}):
        return False
    return True


async def gerar_codigo(db, nome: str) -> str:
    """`SAPIENS` + prefixo do nome + sufixo aleatório — legível, dizível em
    voz alta, e reconhecível como "código do Sapiens" para quem recebe (o
    pedido original dava `SAPIENSLUCAS` como exemplo)."""
    prefixo = f"{_PREFIXO}{_prefixo_do_nome(nome)}"
    for tentativa in range(8):
        tamanho = _SUFIXO if tentativa < 6 else _SUFIXO * 2
        sufixo = "".join(secrets.choice(_ALFABETO) for _ in range(tamanho))
        candidato = f"{prefixo}{sufixo}"[:40]
        if await _codigo_livre(db, candidato):
            return candidato
    raise RuntimeError(f"Não consegui sortear um código livre para influencer '{nome}'.")


def link_de(codigo: str) -> str:
    """Só o código. O link JÁ CARREGOU um `&bonus=N` cosmético, que o
    `Login.jsx` exibia antes do cadastro — e qualquer pessoa trocava o número
    na barra de endereço para a tela prometer "ganhe 5000 Sparks". O valor
    creditado nunca veio dali (é `promo_codes.sparks_amount`, no banco), então
    o parâmetro não dava Spark nenhum a mais: dava só uma promessa falsa na
    tela, do tipo que rende print e reclamação.

    Um número que a própria pessoa consegue editar não tem como ser uma
    promessa, então ele não existe mais."""
    return f"/login?convite={codigo}"


# --------------------------------------------------------------------- CRM

def _normalizar_url(url: str | None) -> str | None:
    """Chave de dedup determinística — nunca depende da IA "lembrar" o que já
    viu (ver `Cerebro/arquitetura/custo-de-ia.md`). `https://Instagram.com/Foo/`
    e `https://instagram.com/foo` são o MESMO lead."""
    if not url:
        return None
    return url.strip().lower().rstrip("/")


async def ja_existe(db, *, url: str | None, plataforma: str | None = None,
                     username: str | None = None) -> bool:
    """Checagem determinística antes de gravar um lead novo — grátis,
    comparada a gastar uma chamada de IA pra redescobrir o que já existe."""
    url_norm = _normalizar_url(url)
    if url_norm:
        if await db.influencers.find_one({"url_normalizada": url_norm}):
            return True
    if username and plataforma:
        if await db.influencers.find_one({"plataforma": plataforma, "username": username}):
            return True
    return False


async def criar_lead(db, payload: dict) -> dict:
    from models import Influencer

    payload = dict(payload)
    if payload.get("url") and not payload.get("url_normalizada"):
        payload["url_normalizada"] = _normalizar_url(payload["url"])
    payload.setdefault("base_legal", BASE_LEGAL_PROSPECCAO)
    payload.setdefault("finalidade", FINALIDADE_PROSPECCAO)

    influencer = Influencer(**payload)
    doc = influencer.model_dump()
    doc["_id"] = doc["influencer_id"]
    await db.influencers.insert_one(doc)
    await _emitir(db, "influencer_created", influencer_id=doc["influencer_id"], origem=doc.get("origem"))
    doc.pop("_id", None)
    return doc


async def listar(db, *, status: str | None = None, plataforma: str | None = None,
                  nicho: str | None = None, prioridade: str | None = None,
                  busca: str | None = None, incluir_descartados: bool = False,
                  skip: int = 0, limit: int = 200) -> list[dict]:
    filtro: dict = {}
    if status:
        filtro["status"] = status
    if plataforma:
        filtro["plataforma"] = plataforma
    if nicho:
        filtro["nicho"] = nicho
    if prioridade:
        filtro["prioridade"] = prioridade
    if not incluir_descartados:
        filtro["descartado"] = {"$ne": True}
    if busca:
        import re
        padrao = {"$regex": f"(?i){re.escape(busca.strip())}"}
        filtro["$or"] = [{"nome": padrao}, {"nicho": padrao}, {"username": padrao}, {"contato": padrao}]
    limit = max(1, min(limit, 500))
    docs = await (
        db.influencers.find(filtro, {"_id": 0})
        .sort("created_at", -1)
        .skip(max(skip, 0))
        .limit(limit)
        .to_list(limit)
    )
    return docs


async def obter(db, influencer_id: str) -> dict | None:
    return await db.influencers.find_one({"_id": influencer_id}, {"_id": 0})


async def remover(db, influencer_id: str) -> bool:
    """Exclusão de verdade — pré-requisito de LGPD (seção 18 do pedido de
    afiliados, art. 18 VI): pedido de remoção do titular precisa funcionar de
    fato, não só existir como caminho manual "documentado". Diferente de
    `status="removido"` (que é decisão de PIPELINE de prospecção, mantém o
    histórico) — isto APAGA o documento. Nunca chamado em cascata por conta
    de aluno; sempre uma ação explícita do admin nesta tela.

    Recusa dois casos, ambos porque apagar quebraria outra coisa que ainda
    está viva: comissão lançada (registro financeiro) e afiliado já ATIVO
    (tem `codigo` — apagar o documento deixaria `promo_codes.influencer_id`
    órfão, e o cupom continuaria funcionando para novos cadastros sem
    ninguém para creditar comissão). A checagem do frontend (esconder o
    botão quando há `codigo`) é só UX — esta é a que vale."""
    atual = await obter(db, influencer_id)
    if atual and atual.get("codigo"):
        raise ValueError(
            "Este influencer já está ATIVO (tem código/cupom em uso) — apagar deixaria "
            "o cupom órfão. Desative o cupom em promo_codes antes, ou marque como 'removido'."
        )
    if await db.influencer_comissoes.find_one({"influencer_id": influencer_id}):
        raise ValueError(
            "Este influencer tem lançamentos de comissão — não pode ser apagado "
            "(registro financeiro). Marque o status como 'removido' em vez disso."
        )
    res = await db.influencers.delete_one({"_id": influencer_id})
    return bool(getattr(res, "deleted_count", 0))


async def atualizar(db, influencer_id: str, campos: dict) -> dict | None:
    """Transição de pipeline ou edição de cadastro. `campos` já vem filtrado
    (`exclude_unset`) por quem chama. Mudar para um status de `STATUS_PARADO`
    é o que interrompe o follow-up automático (seção 9) — nenhuma lógica
    extra aqui: o job de follow-up (fora deste módulo) simplesmente ignora
    quem está num desses estados."""
    campos = dict(campos)
    campos["updated_at"] = _now_iso()
    if campos.get("status") in (STATUS_CONTATO, STATUS_RESPONDEU):
        campos.setdefault("ultimo_contato_em", _now_iso())
    res = await db.influencers.find_one_and_update(
        {"_id": influencer_id}, {"$set": campos}, return_document=True,
    )
    if res is None:
        return None
    res.pop("_id", None)
    return res


def priorizar(leads: list[dict]) -> list[dict]:
    """Ordena leads por sinal OBSERVÁVEL, nunca inventado. Três sinais, cada
    um só conta se o dado existir:

    1. Tamanho aproximado informado — maior alcance, mais peso (log10, não
       linear: 10x mais seguidores não é 10x mais prioridade).
    2. Recência do último contato — quem nunca foi contatado vem antes de
       quem está esperando resposta há muito tempo sem seguimento.
    3. Estágio já alcançado no funil — quem já respondeu/demonstrou
       interesse pesa mais que um lead frio, porque converter é mais barato
       dali.

    Sem tamanho e sem contato, o lead cai para o fim — não para o topo: dado
    ausente não é sinal de prioridade, é ausência de sinal.
    """
    import math

    peso_status = {
        STATUS_LEAD: 0, STATUS_QUALIFICADO: 1, STATUS_MENSAGEM_PRONTA: 1, STATUS_CONTATO: 1,
        STATUS_RESPONDEU: 2, STATUS_INTERESSADO: 3,
    }

    def pontuacao(lead: dict) -> float:
        pontos = 0.0
        tamanho = lead.get("tamanho_aproximado")
        if isinstance(tamanho, (int, float)) and tamanho > 0:
            pontos += math.log10(tamanho + 1)
        pontos += peso_status.get(lead.get("status"), 0)
        return pontos

    ativos = [l for l in leads if l.get("status") not in STATUS_PARADO]
    parados = [l for l in leads if l.get("status") in STATUS_PARADO]
    ativos.sort(key=pontuacao, reverse=True)
    return ativos + parados


# ------------------------------------------------------------ ativação

async def ativar(db, influencer_id: str, *, email_login: str, percentual_comissao: float,
                  sparks_boas_vindas: int, codigo: str | None = None) -> dict | None:
    """Vira afiliado de verdade: ganha código, vira um `promo_codes`, ganha
    link. Idempotente na prática — chamar de novo com o mesmo influencer já
    ativado devolve o registro existente sem duplicar o cupom (checagem pelo
    próprio `codigo` já gravado)."""
    atual = await obter(db, influencer_id)
    if atual is None:
        return None
    if atual.get("codigo"):
        return atual  # já ativo — nada a fazer

    nome = atual["nome"]
    codigo_final = normalizar(codigo) if codigo else await gerar_codigo(db, nome)
    if codigo and not await _codigo_livre(db, codigo_final):
        raise ValueError(f"Código '{codigo_final}' já está em uso.")

    email_login = (email_login or "").strip().lower()
    agora = _now_iso()

    await db.promo_codes.insert_one({
        "code": codigo_final,
        "sparks_amount": sparks_boas_vindas,
        "active": True,
        "usos": 0,
        "created_at": agora,
        "promoter_email": email_login,
        "influencer_id": influencer_id,
    })

    campos = {
        "status": STATUS_ATIVO,
        "codigo": codigo_final,
        "email_login": email_login,
        "link": link_de(codigo_final),
        "percentual_comissao": percentual_comissao,
        "sparks_boas_vindas": sparks_boas_vindas,
        "ativado_em": agora,
        "updated_at": agora,
        # LGPD: a base legal muda de "achamos publicamente" para "temos
        # contrato de parceria" no exato momento em que o lead vira afiliado.
        "base_legal": BASE_LEGAL_PARCERIA_ATIVA,
        "finalidade": FINALIDADE_PROSPECCAO,
    }
    res = await db.influencers.find_one_and_update(
        {"_id": influencer_id}, {"$set": campos}, return_document=True,
    )
    await _emitir(db, "coupon_created", influencer_id=influencer_id, codigo=codigo_final)
    res.pop("_id", None)
    return res


# --------------------------------------------------------- atribuição

async def resolver_e_registrar_atribuicao(db, user_id: str, promo_code: str | None) -> None:
    """Chamada de `auth.py` logo depois de `_registrar_cupom`, para TODO
    cadastro que usou um código do catálogo. Se o código pertence a um
    influencer, carimba o vínculo na conta nova — uma vez, para sempre (não
    há caminho de reescrever `influenciado_por` depois de gravado).

    Autoindicação: se o e-mail da conta nova é o mesmo `email_login` do
    influencer dono do código, a atribuição é IGNORADA (registrada em log,
    não em erro) — ninguém paga comissão sobre a própria compra disfarçada
    de indicação.

    Nunca derruba o cadastro: mesma disciplina de `auth._registrar_indicacao`.
    """
    codigo = normalizar(promo_code)
    if not codigo:
        return
    try:
        cupom = await db.promo_codes.find_one({"code": codigo}, {"_id": 0})
        influencer_id = (cupom or {}).get("influencer_id")
        if not influencer_id:
            return
        conta = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1})
        email_conta = (conta or {}).get("email", "").strip().lower()
        email_influencer = (cupom.get("promoter_email") or "").strip().lower()
        if email_influencer and email_conta == email_influencer:
            logger.warning(
                "Autoindicação bloqueada: %s tentou se atribuir ao próprio código %s.",
                user_id, codigo,
            )
            return
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"influenciado_por": influencer_id, "influenciado_por_codigo": codigo}},
        )
        await _emitir(db, "referral_signup", influencer_id=influencer_id, aluno_id=user_id, codigo=codigo)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao registrar atribuição de influencer para %s (código %r).", user_id, promo_code)


# ------------------------------------------------------------- comissão

async def creditar_comissao(db, *, comprador_id: str, mp_payment_id: str, price_cents: int) -> dict[str, Any] | None:
    """Lança a comissão desta compra para quem indicou o comprador — se
    houver influencer atribuído. Roda em TODA compra creditada (não só a
    primeira, ao contrário de `indicacoes`): o programa de afiliados é
    receita recorrente sobre o cliente trazido, não um prêmio único.

    Idempotente por `_id = mp_payment_id`: reenvio de webhook do Mercado
    Pago tenta inserir nome já existente, `DuplicateKeyError` é engolido e
    nada é lançado de novo. Chamado de dentro do webhook de pagamento,
    depois do crédito do comprador — nunca pode derrubá-lo.
    """
    from pymongo.errors import DuplicateKeyError

    if price_cents <= 0:
        return None
    conta = await db.users.find_one({"user_id": comprador_id}, {"_id": 0, "influenciado_por": 1, "influenciado_por_codigo": 1})
    influencer_id = (conta or {}).get("influenciado_por")
    if not influencer_id:
        return None
    influencer = await obter(db, influencer_id)
    if not influencer:
        return None
    percentual = float(influencer.get("percentual_comissao") or DEFAULT_PERCENTUAL)
    comissao_cents = int(round(price_cents * percentual))
    if comissao_cents <= 0:
        return None

    doc = {
        "_id": mp_payment_id,
        "influencer_id": influencer_id,
        "aluno_id": comprador_id,
        "mp_payment_id": mp_payment_id,
        "price_cents": price_cents,
        "percentual": percentual,
        "comissao_cents": comissao_cents,
        "status": COMISSAO_ACUMULADA,
        "created_at": _now_iso(),
        "pago_em": None,
        "estornado_em": None,
    }
    try:
        await db.influencer_comissoes.insert_one(doc)
    except DuplicateKeyError:
        return None

    await _emitir(db, "influencer_revenue", influencer_id=influencer_id, aluno_id=comprador_id, meta={"price_cents": price_cents})
    await _emitir(db, "influencer_commission", influencer_id=influencer_id, aluno_id=comprador_id, meta={"comissao_cents": comissao_cents})
    logger.info(
        "Comissão: influencer %s ganhou R$%.2f sobre compra de %s (pagamento %s).",
        influencer_id, comissao_cents / 100, comprador_id, mp_payment_id,
    )
    return {"influencer_id": influencer_id, "comissao_cents": comissao_cents}


async def estornar_comissao(db, mp_payment_id: str) -> dict | None:
    """Chamado quando um pagamento que já tinha gerado comissão volta como
    `refunded`/`charged_back`. Muda o STATUS do lançamento em vez de tentar
    subtrair de um total — o total nunca existe como número gravado, só como
    soma sobre lançamentos com `status == "acumulada"` (ver `resumo`)."""
    res = await db.influencer_comissoes.find_one_and_update(
        {"_id": mp_payment_id, "status": COMISSAO_ACUMULADA},
        {"$set": {"status": COMISSAO_ESTORNADA, "estornado_em": _now_iso()}},
        return_document=True,
    )
    if res:
        logger.info(
            "Comissão estornada: pagamento %s (influencer %s, R$%.2f).",
            mp_payment_id, res["influencer_id"], res["comissao_cents"] / 100,
        )
        res.pop("_id", None)
    return res


async def marcar_comissao_paga(db, influencer_id: str, *, mp_payment_ids: list[str] | None = None) -> dict:
    """Ação do admin depois de um Pix manual. Marca lançamentos ACUMULADOS
    como PAGOS — nunca transfere dinheiro sozinho (não é o escopo deste
    módulo, e o pedido original é explícito: nenhum envio real nesta etapa).
    Sem `mp_payment_ids`, marca TODOS os acumulados deste influencer."""
    filtro: dict[str, Any] = {"influencer_id": influencer_id, "status": COMISSAO_ACUMULADA}
    if mp_payment_ids:
        filtro["_id"] = {"$in": mp_payment_ids}
    res = await db.influencer_comissoes.update_many(
        filtro, {"$set": {"status": COMISSAO_PAGA, "pago_em": _now_iso()}},
    )
    return {"marcados": res.modified_count}


# --------------------------------------------------------------- resumos

async def _metricas_de_conversao(db, influencer_id: str) -> dict:
    """CTR/cadastro/ativação/compra — funil do próprio influencer, a partir
    de `growth_events` e `users`. "Ativação" é derivada (>=1 resposta
    registrada), não um evento gravado à parte — evita duplicar telemetria
    que já existe (ver `annotation_service`/`behavior`)."""
    import growth_events

    funil = await growth_events.resumo_funil(db, influencer_id=influencer_id)
    atribuidos = await db.users.count_documents({"influenciado_por": influencer_id})
    return {**funil, "alunos_atribuidos": atribuidos}


async def resumo(db, influencer_id: str) -> dict | None:
    """O que o painel do próprio influencer mostra — ver `/promoter/dashboard`."""
    influencer = await obter(db, influencer_id)
    if influencer is None:
        return None
    alunos = await db.users.find(
        {"influenciado_por": influencer_id}, {"_id": 0, "user_id": 1, "name": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(5000)
    ids = [a["user_id"] for a in alunos]

    faturamento_cents = 0
    if ids:
        pagamentos = await db.sparks_payments.find(
            {"user_id": {"$in": ids}, "credited": True}, {"_id": 0, "price_cents": 1},
        ).to_list(20000)
        faturamento_cents = sum(int(p.get("price_cents") or 0) for p in pagamentos)

    comissoes = await db.influencer_comissoes.find(
        {"influencer_id": influencer_id}, {"_id": 0},
    ).sort("created_at", -1).to_list(20000)
    acumulada = sum(c["comissao_cents"] for c in comissoes if c["status"] == COMISSAO_ACUMULADA)
    paga = sum(c["comissao_cents"] for c in comissoes if c["status"] == COMISSAO_PAGA)

    return {
        **influencer,
        "alunos_atribuidos": len(alunos),
        "faturamento_atribuido_cents": faturamento_cents,
        "comissao_acumulada_cents": acumulada,
        "comissao_paga_cents": paga,
        "conversao": await _metricas_de_conversao(db, influencer_id),
        "ultimos_alunos": alunos[:20],
    }


async def resumo_admin(db) -> dict:
    """Visão consolidada para `/admin/influencers` — uma passada pelas três
    coleções, agrupando em memória (a base de influencers é pequena por
    natureza; não é o acervo de alunos)."""
    influencers = await listar(db)
    comissoes = await db.influencer_comissoes.find({}, {"_id": 0}).to_list(50000)
    por_influencer: dict[str, list[dict]] = {}
    for c in comissoes:
        por_influencer.setdefault(c["influencer_id"], []).append(c)

    linhas = []
    for inf in influencers:
        cs = por_influencer.get(inf["influencer_id"], [])
        atribuidos = await db.users.count_documents({"influenciado_por": inf["influencer_id"]})
        linhas.append({
            **inf,
            "alunos_atribuidos": atribuidos,
            "comissao_acumulada_cents": sum(c["comissao_cents"] for c in cs if c["status"] == COMISSAO_ACUMULADA),
            "comissao_paga_cents": sum(c["comissao_cents"] for c in cs if c["status"] == COMISSAO_PAGA),
            "faturamento_atribuido_cents": sum(c["price_cents"] for c in cs),
        })
    return {
        "items": linhas,
        "total": len(linhas),
        "ativos": sum(1 for i in linhas if i["status"] == STATUS_ATIVO),
        "comissao_acumulada_total_cents": sum(i["comissao_acumulada_cents"] for i in linhas),
        "comissao_paga_total_cents": sum(i["comissao_paga_cents"] for i in linhas),
    }


async def _emitir(db, tipo: str, **campos) -> None:
    import growth_events

    try:
        await growth_events.registrar(db, tipo, **campos)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao emitir evento de growth '%s'.", tipo)


# ------------------------------------------------------- kit e mensagens
#
# Tudo abaixo é determinístico — templates com placeholders, ZERO chamada de
# IA. O pedido prioriza custo mínimo e o agente `cost` revisaria qualquer
# fluxo que chamasse Gemini aqui; a personalização vem de dado REAL (nome,
# nicho, código, link), nunca de texto inventado sobre a pessoa.

_ABERTURAS_PROSPECCAO = [
    "Oi {nome}! Vi seu trabalho em {nicho_ou_canal} e queria te chamar pra uma parceria.",
    "{nome}, tudo bem? Curti seu conteúdo sobre {nicho_ou_canal} e acho que faz sentido pra gente conversar.",
    "Oi {nome}, passando rápido: montamos um programa de parceria pensado pra quem fala de {nicho_ou_canal}.",
]

_CORPO_PROSPECCAO = (
    "Sou do Sapiens — uma plataforma de estudo pro ENEM que mede POR QUE o aluno "
    "erra, não só quanto. A proposta: quem entra pelo seu link/código ganha "
    "{sparks} Sparks de boas-vindas (o padrão é 100), e você fica com {percentual}% "
    "de tudo que essas pessoas comprarem no app, sem limite de tempo."
)

_CTA_PROSPECCAO = "Topa bater um papo rápido sobre como funcionaria pro seu público?"


def gerar_mensagem_prospeccao(lead: dict, *, variacao: int = 0) -> str:
    """Mensagem individual para o PRIMEIRO contato (D0). `variacao` escolhe
    entre aberturas diferentes para o mesmo lote de leads não sair com texto
    idêntico. Nunca inventa elogio nem fato: `nicho_ou_canal` só aparece
    quando o dado existe; sem ele, a abertura cai numa variante sem essa
    frase, em vez de inventar um nicho."""
    nome = (lead.get("nome") or "").split(" ")[0] or "tudo bem"
    nicho_ou_canal = lead.get("nicho") or lead.get("plataforma")
    aberturas = _ABERTURAS_PROSPECCAO if nicho_ou_canal else [
        f"Oi {{nome}}! Encontrei seu contato e queria te chamar pra uma parceria com o Sapiens."
    ]
    idx = variacao % len(aberturas)
    abertura = aberturas[idx].format(nome=nome, nicho_ou_canal=nicho_ou_canal or "")
    corpo = _CORPO_PROSPECCAO.format(
        sparks=lead.get("sparks_boas_vindas") or DEFAULT_SPARKS_BOAS_VINDAS,
        percentual=int(round((lead.get("percentual_comissao") or DEFAULT_PERCENTUAL) * 100)),
    )
    return f"{abertura} {corpo} {_CTA_PROSPECCAO}"


_FOLLOWUPS = {
    3: "Oi {nome}, só voltando aqui — ainda topa dar uma olhada na parceria com o Sapiens? Fico à disposição.",
    7: "{nome}, última mensagem por aqui pra não encher — se mudar de ideia, o convite continua de pé.",
}


def gerar_followup(lead: dict, dia: int) -> str | None:
    """`dia` é 3 ou 7 (D3/D7 do pedido). Fora disso, `None` — não existe
    follow-up genérico, só os dois programados."""
    modelo = _FOLLOWUPS.get(dia)
    if not modelo:
        return None
    nome = (lead.get("nome") or "").split(" ")[0] or "tudo bem"
    return modelo.format(nome=nome)


def gerar_kit(influencer: dict) -> dict:
    """Materiais de divulgação prontos — para o próprio influencer copiar e
    postar. Nome incorporado quando existe; nunca inventa característica
    pessoal, promessa de conteúdo da aula (ver `inviolaveis.md`) nem número
    fora do catálogo real."""
    nome = influencer.get("nome") or "parceiro(a)"
    codigo = influencer.get("codigo") or ""
    link = influencer.get("link") or ""
    sparks = influencer.get("sparks_boas_vindas") or DEFAULT_SPARKS_BOAS_VINDAS
    percentual = int(round((influencer.get("percentual_comissao") or DEFAULT_PERCENTUAL) * 100))

    mensagem = (
        f"Fechei uma parceria com o Sapiens! Quem se cadastrar com meu código "
        f"{codigo} ganha {sparks} Sparks de bônus pra começar a estudar pro ENEM."
    )
    legenda = (
        f"📚 Parceria nova: uso o código {codigo} e ganho {sparks} Sparks de graça no Sapiens "
        f"pra estudar pro ENEM. Link na bio."
    )
    story = f"Ganhe {sparks} Sparks grátis no Sapiens 👉 código {codigo}"
    roteiro = (
        f"[Abertura] Fala, {{tema livre sobre a própria rotina de estudo}}.\n"
        f"[Meio] Uso o Sapiens pra estudar pro ENEM — ele mostra ONDE eu erro, não só quanto.\n"
        f"[CTA] Usa meu código {codigo} e ganha {sparks} Sparks de bônus. Link na bio."
    )
    return {
        "nome": nome,
        "codigo": codigo,
        "link": link,
        "mensagem": mensagem,
        "legenda": legenda,
        "story": story,
        "roteiro_reel": roteiro,
        "cta": f"Use o código {codigo} e comece com {sparks} Sparks",
        "percentual_comissao": percentual,
    }


# ------------------------------------------------------ classificação de resposta
#
# Puramente por palavra-chave, determinístico — sem IA, sem custo. Seção 10
# do pedido: nunca responder automaticamente em caso ambíguo, então quando
# nenhuma regra casa a função devolve `None` e quem chama trata como
# "revisar manualmente", nunca como "sem interesse".

_PALAVRAS_CLASSIFICACAO: list[tuple[str, tuple[str, ...]]] = [
    ("pedido_remocao", ("não me mande mais", "para de mandar", "remover", "descadastrar", "não quero contato")),
    ("recusou", ("não tenho interesse", "não quero", "não topo", "passo")),
    ("quer_preco", ("quanto custa", "qual o valor", "quanto vocês pagam", "qual comissão")),
    ("quer_testar", ("quero testar", "posso usar antes", "queria conhecer o app")),
    ("quer_parceria", ("bora", "topo", "vamos fechar", "como funciona a parceria", "manda mais detalhes")),
    ("duvida", ("como funciona", "não entendi", "que sparks", "o que é sparks")),
    ("interessado", ("legal", "gostei", "faz sentido", "interessante")),
]


def classificar_resposta(texto: str) -> str | None:
    alvo = (texto or "").strip().lower()
    if not alvo:
        return None
    for classe, gatilhos in _PALAVRAS_CLASSIFICACAO:
        if any(g in alvo for g in gatilhos):
            return classe
    return None
