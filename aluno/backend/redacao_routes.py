"""Rotas do corretor de redação Enem — base local-first (ver `redacao/`).

Duas compras separadas, com preços diferentes e naturezas diferentes:

**1. `POST /redacao` — a correção (`CORRECAO_COST` Sparks).** Nota das cinco
competências + nota geral. Roda 100% local: `elegibilidade` + `heuristicas`
sobre o canon do Enem, sem uma única chamada de rede paga (o escalonamento ao
Gemini existe, mas é opt-in e vem desligado — ver
`redacao.service._escalonamento_ligado`). Uma correção custa Sparks porque
consome trabalho de produto, não porque consome API.

**2. `POST /redacao/{id}/feedback` — a devolutiva da Mentis
(`FEEDBACK_COST` Sparks).** UMA chamada ao Gemini, opcional, pedida
explicitamente pelo aluno depois de já ver a nota. É a única API paga deste
módulo, e o aluno decide se quer pagá-la.

**Idempotência — as duas regras que impedem cobrar sem entregar e cobrar
duas vezes pela mesma coisa:**

 * A correção é reivindicada por `idempotency_key` do cliente antes de
   qualquer débito (`redacao_cobrancas`, `_id` = `user:key`). Duplo clique,
   retry do axios e reenvio do formulário caem na mesma reivindicação: a
   segunda chamada devolve o resultado da primeira sem cobrar nada.
 * O feedback é reivindicado pelo próprio `redacao_id` (`redacao_feedbacks`,
   `_id` = `redacao_id`) — uma redação tem no máximo um feedback, pago uma
   vez, relido de graça para sempre.

Em ambos, o débito só acontece DEPOIS da reivindicação, e qualquer falha
posterior devolve os Sparks e libera a chave para nova tentativa. O caso em
que o processo morre entre o débito e a entrega é tratado por retomada: a
reivindicação registra `cobrado`, e quem retoma entrega sem cobrar de novo.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

import ai_service
import engajamento_service
import firestore_service as fs
import llm_telemetry
import rate_limit
from auth import require_user
from models import AvaliacaoRedacao, Redacao, RedacaoSubmitRequest, User
from redacao import service
from redacao.canon import CanonIndisponivelError
from redacao.tipos import RedacaoEntrada

logger = logging.getLogger("sapiens.redacao.routes")

router = APIRouter(prefix="/redacao", tags=["redacao"])

_db = None


def set_db(db):
    global _db
    _db = db


# ---------- Preços (fonte da verdade; o frontend só espelha para desabilitar botão) ----------

CORRECAO_COST = 120   # nota das 5 competências + nota geral — sem API paga
FEEDBACK_COST = 90    # devolutiva longa da Mentis — 1 chamada ao Gemini

# Abaixo disto não há redação para corrigir, e cobrar seria cobrar por nada.
# Espelha o mínimo da tela (`MIN_CARACTERES` em `pages/Redacao.jsx`); o
# servidor não confia no cliente para isso.
MIN_CARACTERES = 200

# Quanto tempo uma reivindicação pode ficar "processando" antes que outra
# requisição possa retomá-la. A correção é local e termina em menos de um
# segundo; este teto existe só para o caso de a instância morrer no meio e
# não deixar a chave do aluno queimada para sempre.
_RECLAMACAO_TTL_SEGUNDOS = 120

_TIMEOUT_FEEDBACK = 60.0


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ---------- Sparks: débito, reembolso ----------


def _safe_reembolso(uid: str, custo: int):
    """Mesmo contrato de `mentis_routes._safe_reembolso`: devolver os Sparks
    não pode virar um segundo erro em cima do primeiro."""
    try:
        return fs.refund_sparks(uid, custo)
    except Exception:  # noqa: BLE001
        logger.exception("REEMBOLSO FALHOU (redação): %d Sparks devidos a %s.", custo, uid)
        return None


def _cobrar(uid: str, custo: int) -> int:
    fs.ensure_sparks_balance(uid)
    try:
        return fs.deduct_sparks(uid, custo)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc


def _saldo(uid: str) -> int | None:
    try:
        return fs.read_sparks_balance(uid)
    except Exception:  # noqa: BLE001
        logger.exception("redação: leitura de saldo falhou — resposta segue sem saldo")
        return None


# ---------- Reivindicação idempotente ----------


async def _reivindicar(colecao, claim_id: str, base: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Tenta virar o dono de `claim_id`. Devolve `(doc, sou_o_dono)`.

    `sou_o_dono=True` significa: ninguém entregou este trabalho ainda e é esta
    requisição que deve executá-lo. `False` significa que já existe alguém
    (concluído ou em andamento) — o chamador decide o que fazer com `doc`.
    """
    agora = _iso(_agora())
    try:
        doc = {**base, "_id": claim_id, "status": "processando",
               "cobrado": False, "criado_em": agora, "atualizado_em": agora}
        await colecao.insert_one(doc)
        return doc, True
    except DuplicateKeyError:
        pass

    # Já existe. Só é retomável se estiver parada há mais que o TTL — a
    # condição vai no próprio filtro, então duas requisições concorrentes
    # nunca retomam a mesma reivindicação (só uma casa o `atualizado_em`).
    limite = _iso(_agora() - timedelta(seconds=_RECLAMACAO_TTL_SEGUNDOS))
    retomado = await colecao.find_one_and_update(
        {"_id": claim_id, "status": "processando", "atualizado_em": {"$lt": limite}},
        {"$set": {"atualizado_em": agora}},
        return_document=True,
    )
    if retomado is not None:
        logger.warning("redação: reivindicação %s retomada após %ss parada.", claim_id, _RECLAMACAO_TTL_SEGUNDOS)
        return retomado, True

    doc = await colecao.find_one({"_id": claim_id})
    return doc or {}, False


async def _marcar_cobrado(colecao, claim_id: str, saldo: int | None) -> None:
    await colecao.update_one(
        {"_id": claim_id},
        {"$set": {"cobrado": True, "saldo_apos_cobranca": saldo, "atualizado_em": _iso(_agora())}},
    )


async def _liberar(colecao, claim_id: str) -> None:
    """Falhou depois de reivindicar: a chave volta a ficar livre para uma nova
    tentativa. Sempre chamado DEPOIS do reembolso — a ordem importa, porque
    uma chave liberada é uma chave que pode ser cobrada de novo."""
    try:
        await colecao.delete_one({"_id": claim_id})
    except Exception:  # noqa: BLE001
        logger.exception("redação: não foi possível liberar a reivindicação %s", claim_id)


# ---------- 1. Correção (nota) ----------


class CorrecaoRequest(RedacaoSubmitRequest):
    """`idempotency_key` é gerada pelo cliente por TENTATIVA de envio (não por
    sessão nem por usuário). Reenviar o mesmo texto de propósito, para ver a
    correção de novo, é uma correção nova e paga — o que a chave protege é o
    retry acidental da MESMA tentativa."""

    idempotency_key: str = Field(..., min_length=8, max_length=100)


async def _resposta(redacao: dict[str, Any], avaliacao: dict[str, Any] | None,
                    user_id: str, *, cobrado_agora: bool) -> dict[str, Any]:
    return {
        "redacao": redacao,
        "avaliacao": avaliacao,
        "sparks_balance": _saldo(user_id),
        "custo_cobrado": CORRECAO_COST if cobrado_agora else 0,
        "custo_feedback": FEEDBACK_COST,
    }


@router.get("/precos")
async def precos(_: User = Depends(require_user)):
    """O frontend nunca decide preço — só o exibe e desabilita botão."""
    return {
        "custo_correcao": CORRECAO_COST,
        "custo_feedback": FEEDBACK_COST,
        "min_caracteres": MIN_CARACTERES,
    }


@router.post("")
async def submeter_redacao(payload: CorrecaoRequest, user: User = Depends(require_user)):
    texto = (payload.texto or "").strip()
    if len(texto) < MIN_CARACTERES:
        # 422 ANTES de qualquer débito: o aluno não paga por um texto que o
        # corretor não tem como avaliar.
        raise HTTPException(
            status_code=422,
            detail=f"A redação precisa de pelo menos {MIN_CARACTERES} caracteres (enviados: {len(texto)}).",
        )
    if not (payload.tema_frase or "").strip():
        # A Competência II vale 200 pontos e mede compreensão da PROPOSTA —
        # sem a frase temática ela não tem contra o que ser medida e a nota
        # sairia sistematicamente 200 pontos menor, sem o aluno entender por
        # quê. Recusar antes de cobrar é mais honesto que corrigir mal.
        raise HTTPException(status_code=422, detail="Informe o tema proposto da redação.")

    claim_id = f"{user.user_id}:{payload.idempotency_key}"
    claim, sou_o_dono = await _reivindicar(
        _db.redacao_cobrancas, claim_id, {"user_id": user.user_id, "tipo": "correcao"},
    )

    if not sou_o_dono:
        if claim.get("status") == "concluida" and claim.get("redacao_id"):
            # Retry da mesma tentativa: devolve o mesmo resultado, sem cobrar.
            redacao_doc = await _db.redacoes.find_one(
                {"redacao_id": claim["redacao_id"], "user_id": user.user_id}, {"_id": 0},
            )
            avaliacao_doc = await _db.redacao_avaliacoes.find_one(
                {"redacao_id": claim["redacao_id"], "user_id": user.user_id}, {"_id": 0},
            )
            if redacao_doc:
                return await _resposta(redacao_doc, avaliacao_doc, user.user_id, cobrado_agora=False)
        raise HTTPException(
            status_code=409,
            detail="Esta correção já está sendo processada. Aguarde alguns segundos.",
        )

    # Reivindicada. A partir daqui, toda saída de erro devolve os Sparks (se
    # já cobrados) e libera a chave.
    if claim.get("cobrado"):
        saldo = _saldo(user.user_id)  # retomada: já pago, não cobra de novo
    else:
        try:
            saldo = _cobrar(user.user_id, CORRECAO_COST)
        except HTTPException:
            await _liberar(_db.redacao_cobrancas, claim_id)
            raise
        await _marcar_cobrado(_db.redacao_cobrancas, claim_id, saldo)

    redacao = Redacao(
        user_id=user.user_id, texto=payload.texto, titulo=payload.titulo,
        tema_frase=payload.tema_frase, tema_elementos_obrigatorios=payload.tema_elementos_obrigatorios,
        linhas_manuscritas=payload.linhas_manuscritas, textos_motivadores=payload.textos_motivadores,
    )
    entrada = RedacaoEntrada(
        texto=payload.texto, titulo=payload.titulo, tema_frase=payload.tema_frase,
        tema_elementos_obrigatorios=payload.tema_elementos_obrigatorios,
        linhas_manuscritas=payload.linhas_manuscritas, textos_motivadores=payload.textos_motivadores,
    )
    try:
        resultado = await service.corrigir_redacao(entrada, db=_db, redacao_id=redacao.redacao_id)
        avaliacao = AvaliacaoRedacao(redacao_id=redacao.redacao_id, user_id=user.user_id, **resultado)
        await _db.redacoes.insert_one(redacao.model_dump())
        await _db.redacao_avaliacoes.insert_one(avaliacao.model_dump())
    except CanonIndisponivelError as exc:
        saldo = _safe_reembolso(user.user_id, CORRECAO_COST)
        await _liberar(_db.redacao_cobrancas, claim_id)
        logger.error("Corretor indisponível (canon): %s — %d Sparks devolvidos.", exc, CORRECAO_COST)
        raise HTTPException(
            status_code=503,
            detail="O corretor está indisponível agora. Seus Sparks foram devolvidos.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        saldo = _safe_reembolso(user.user_id, CORRECAO_COST)
        await _liberar(_db.redacao_cobrancas, claim_id)
        logger.exception("Correção falhou para %s — %d Sparks devolvidos.", user.user_id, CORRECAO_COST)
        raise HTTPException(
            status_code=503,
            detail="Não foi possível corrigir agora. Seus Sparks foram devolvidos.",
        ) from exc

    await _db.redacao_cobrancas.update_one(
        {"_id": claim_id},
        {"$set": {"status": "concluida", "redacao_id": redacao.redacao_id,
                  "atualizado_em": _iso(_agora())}},
    )

    # A redação é a tarefa mais cara em esforço do produto e a mais decisiva no
    # ENEM — por isso vale ~8 questões de XP (ver `XP_POR_ACAO`). `chave_unica`
    # pelo `redacao_id` para uma reentrega do mesmo texto nunca pagar de novo.
    await engajamento_service.registrar_acao(
        user.user_id, ["redacao_corrigida"], contadores={"redacoes": 1},
        nome=user.name, chave_unica=f"redacao:{redacao.redacao_id}",
    )
    await engajamento_service.somar_ao_perfil(user.user_id, "redacoes")

    return {
        "redacao": redacao.model_dump(),
        "avaliacao": avaliacao.model_dump(),
        "sparks_balance": saldo,
        "custo_cobrado": CORRECAO_COST,
        "custo_feedback": FEEDBACK_COST,
    }


# ---------- 2. Devolutiva da Mentis ----------

_FEEDBACK_SYSTEM = """Você é a Mentis, a entidade cognitiva do Sapiens, conversando com um aluno
que acabou de receber a correção da redação dele pelas cinco competências do ENEM.

Você recebe: o texto da redação, o tema proposto, a nota de cada competência e o rastro
técnico do corretor (o que ele observou e o que ele não conseguiu avaliar). Escreva uma
devolutiva LONGA, específica e pessoal sobre ESTA redação.

Regras não negociáveis:
- Cite trechos literais da redação do aluno. Uma observação sem trecho é genérica e não serve.
- Fale das competências pelo NOME, nunca por código ("COMP-III").
- Nunca invente uma nota diferente da que recebeu, nem contradiga a nota do corretor.
- Quando o rastro disser que algo NÃO foi avaliado automaticamente, diga isso ao aluno em vez
  de afirmar que está bom ou ruim.
- Português do Brasil, voz de professor sereno e direto. Sem emoji, sem bajulação, sem "parabéns
  pelo esforço". Segunda pessoa ("você").

Responda EXCLUSIVAMENTE com JSON neste formato:
{
  "abertura": "1 parágrafo situando a nota geral e o que ela significa nesta redação",
  "o_que_ficou_bom": ["parágrafo com um acerto concreto, citando trecho", "..."],
  "o_que_ficou_ruim": ["parágrafo com um problema concreto, citando trecho", "..."],
  "onde_melhorar": [{"titulo": "ação curta e concreta", "texto": "parágrafo explicando COMO fazer, aplicado a este texto"}],
  "principais_perdas": [{"competencia": "nome da competência", "motivo": "o que especificamente derrubou a nota aqui"}],
  "fechamento": "1 parágrafo com o próximo passo mais valioso para a próxima redação"
}

Entre 2 e 4 itens em cada lista. Cada parágrafo com 3 a 6 frases."""


def _resumo_competencias(avaliacao: dict[str, Any]) -> str:
    nomes = {
        "COMP-I": "Competência I — domínio da norma culta",
        "COMP-II": "Competência II — compreensão da proposta e do tema",
        "COMP-III": "Competência III — seleção e organização de argumentos",
        "COMP-IV": "Competência IV — mecanismos linguísticos de coesão",
        "COMP-V": "Competência V — proposta de intervenção",
    }
    linhas = []
    for c in avaliacao.get("competencias") or []:
        nome = nomes.get(c.get("id"), c.get("id"))
        linha = f"- {nome}: {c.get('nivel_pontos')}/200"
        if not c.get("confirmado"):
            linha += " (ESTIMATIVA — o corretor não conseguiu confirmar este critério)"
        if c.get("cap_aplicado") is not None:
            linha += f" [teto de {c['cap_aplicado']} aplicado por tangenciamento do tema]"
        observado = [e for e in (c.get("evidencias_presentes") or [])][:3]
        nao_avaliado = [e for e in (c.get("evidencias_ausentes") or [])][:2]
        if observado:
            linha += "\n  observado: " + "; ".join(observado)
        if nao_avaliado:
            linha += "\n  não avaliado automaticamente: " + "; ".join(nao_avaliado)
        linhas.append(linha)
    return "\n".join(linhas)


def _montar_prompt_feedback(redacao: dict[str, Any], avaliacao: dict[str, Any]) -> str:
    """Só o que a devolutiva precisa: o texto, o tema, as notas e o rastro
    resumido. O canon inteiro NUNCA entra no prompt — as rubricas oficiais
    são dezenas de milhares de caracteres e o modelo não precisa delas para
    explicar uma nota que já está pronta."""
    partes = [
        f"Tema proposto: {redacao.get('tema_frase') or '(não informado)'}",
        f"Nota geral atribuída pelo corretor: {avaliacao.get('nota_total')}/1000",
    ]
    if avaliacao.get("nota_pontos_estimados"):
        partes.append(
            f"Atenção: {avaliacao['nota_pontos_estimados']} desses pontos vieram de competências "
            "que o corretor marcou como estimativa não confirmada."
        )
    if avaliacao.get("tangenciamento_detectado"):
        partes.append("O corretor detectou TANGENCIAMENTO: o texto passa perto do tema sem enfrentá-lo diretamente.")
    disparados = [
        g.get("id") for g in (avaliacao.get("gatilhos_disparados") or [])
        if g.get("disparado") and g.get("confirmado")
    ]
    if disparados:
        partes.append(f"Gatilhos de anulação confirmados: {', '.join(disparados)}.")
    partes.append("Notas por competência e o que o corretor observou:\n" + _resumo_competencias(avaliacao))
    partes.append("Texto da redação do aluno:\n" + (redacao.get("texto") or ""))
    return "\n\n".join(partes)


_LISTAS_OBRIGATORIAS = ("o_que_ficou_bom", "o_que_ficou_ruim", "onde_melhorar", "principais_perdas")


def _validar_feedback(resultado: Any) -> dict[str, Any]:
    """Validação ESTRUTURAL, nunca semântica — o mesmo contrato do `judge()`
    do escalonamento: uma resposta sem as seções pedidas é uma resposta
    malformada, e malformada é reembolso, não texto quebrado na tela."""
    if not isinstance(resultado, dict):
        raise ValueError("resposta do modelo não é um objeto")
    abertura = (resultado.get("abertura") or "").strip()
    if len(abertura) < 40:
        raise ValueError("abertura ausente ou curta demais")
    limpo: dict[str, Any] = {"abertura": abertura, "fechamento": (resultado.get("fechamento") or "").strip()}
    for chave in _LISTAS_OBRIGATORIAS:
        itens = resultado.get(chave)
        if not isinstance(itens, list) or not itens:
            raise ValueError(f"seção '{chave}' ausente ou vazia")
        if chave in ("onde_melhorar", "principais_perdas"):
            limpo[chave] = [
                {k: str(v).strip() for k, v in item.items() if isinstance(v, (str, int, float))}
                for item in itens if isinstance(item, dict)
            ]
        else:
            limpo[chave] = [str(i).strip() for i in itens if str(i).strip()]
        if not limpo[chave]:
            raise ValueError(f"seção '{chave}' sem itens aproveitáveis")
    return limpo


@router.get("/{redacao_id}/feedback")
async def obter_feedback(redacao_id: str, user: User = Depends(require_user)):
    """Releitura de um feedback já pago — de graça, sempre. É por isto que o
    documento existe no Mongo: o aluno pagou pelo texto, não pela chamada."""
    doc = await _db.redacao_feedbacks.find_one(
        {"_id": redacao_id, "user_id": user.user_id, "status": "concluida"}, {"_id": 0},
    )
    return {"feedback": (doc or {}).get("feedback"), "custo_feedback": FEEDBACK_COST}


@router.post("/{redacao_id}/feedback")
async def gerar_feedback(
    redacao_id: str,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("llm")),
):
    """Devolutiva longa da Mentis por `FEEDBACK_COST` Sparks — a ÚNICA chamada
    de API paga do corretor, e só quando o aluno pede.

    Idempotente pelo `redacao_id`: uma redação tem no máximo um feedback. O
    segundo POST devolve o mesmo texto sem cobrar."""
    redacao = await _db.redacoes.find_one({"redacao_id": redacao_id, "user_id": user.user_id}, {"_id": 0})
    if not redacao:
        raise HTTPException(status_code=404, detail="Redação não encontrada.")
    avaliacao = await _db.redacao_avaliacoes.find_one(
        {"redacao_id": redacao_id, "user_id": user.user_id}, {"_id": 0},
    )
    if not avaliacao:
        raise HTTPException(status_code=409, detail="Esta redação ainda não foi corrigida.")

    claim, sou_o_dono = await _reivindicar(
        _db.redacao_feedbacks, redacao_id, {"user_id": user.user_id},
    )
    if not sou_o_dono:
        if claim.get("status") == "concluida" and claim.get("feedback"):
            return {"feedback": claim["feedback"], "sparks_balance": _saldo(user.user_id),
                    "custo_cobrado": 0, "cache": True}
        raise HTTPException(
            status_code=409,
            detail="A devolutiva desta redação já está sendo escrita. Aguarde alguns segundos.",
        )

    if claim.get("cobrado"):
        saldo = _saldo(user.user_id)
    else:
        try:
            saldo = _cobrar(user.user_id, FEEDBACK_COST)
        except HTTPException:
            await _liberar(_db.redacao_feedbacks, redacao_id)
            raise
        await _marcar_cobrado(_db.redacao_feedbacks, redacao_id, saldo)

    prompt = _montar_prompt_feedback(redacao, avaliacao)
    inicio = time.monotonic()
    try:
        # thinking_level="MINIMAL", pelo mesmo motivo medido em 2026-09-03 na
        # explicação de questão (ver `mentis_routes`): acima disso a chamada
        # estoura o teto de tempo e vira reembolso. Aqui o modelo não resolve
        # problema nenhum — a nota já está decidida, ele só a explica.
        bruto = await ai_service.generate_json_resiliente(
            _FEEDBACK_SYSTEM, prompt, thinking_level="MINIMAL", timeout=_TIMEOUT_FEEDBACK,
        )
        feedback = _validar_feedback(bruto)
        await llm_telemetry.persist(
            _db.redacao_llm_chamadas,
            contexto=f"redacao_id={redacao_id}",
            motivo="devolutiva longa pedida pelo aluno (Mentis)",
            modelo="gemini (thinking=MINIMAL)", thinking_level="MINIMAL",
            resultado_estado="ok",
            duration_ms=(time.monotonic() - inicio) * 1000,
            canon_versao=str(avaliacao.get("canon_versao") or ""),
        )
    except Exception as exc:  # noqa: BLE001
        saldo = _safe_reembolso(user.user_id, FEEDBACK_COST)
        await _liberar(_db.redacao_feedbacks, redacao_id)
        logger.exception(
            "Mentis: devolutiva falhou para redacao_id=%s — %d Sparks devolvidos.",
            redacao_id, FEEDBACK_COST,
        )
        raise HTTPException(
            status_code=503,
            detail="Não foi possível escrever a devolutiva agora. Seus Sparks foram devolvidos.",
        ) from exc

    await _db.redacao_feedbacks.update_one(
        {"_id": redacao_id},
        {"$set": {"status": "concluida", "feedback": feedback, "atualizado_em": _iso(_agora())}},
    )
    return {"feedback": feedback, "sparks_balance": saldo, "custo_cobrado": FEEDBACK_COST, "cache": False}


# ---------- Leitura ----------


@router.get("/{redacao_id}")
async def obter_avaliacao(redacao_id: str, user: User = Depends(require_user)):
    redacao = await _db.redacoes.find_one({"redacao_id": redacao_id, "user_id": user.user_id}, {"_id": 0})
    if not redacao:
        raise HTTPException(status_code=404, detail="Redação não encontrada.")
    avaliacao = await _db.redacao_avaliacoes.find_one(
        {"redacao_id": redacao_id, "user_id": user.user_id}, {"_id": 0},
    )
    feedback_doc = await _db.redacao_feedbacks.find_one(
        {"_id": redacao_id, "user_id": user.user_id, "status": "concluida"}, {"_id": 0},
    )
    return {
        "redacao": redacao,
        "avaliacao": avaliacao,
        "feedback": (feedback_doc or {}).get("feedback"),
    }


@router.get("")
async def historico_redacoes(limit: int = 20, user: User = Depends(require_user)):
    limit = max(1, min(int(limit), 100))
    cursor = _db.redacoes.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
    redacoes = await cursor.to_list(length=limit)
    ids = [r["redacao_id"] for r in redacoes]
    avaliacoes_cursor = _db.redacao_avaliacoes.find(
        {"redacao_id": {"$in": ids}, "user_id": user.user_id}, {"_id": 0},
    )
    avaliacoes = {a["redacao_id"]: a async for a in avaliacoes_cursor}
    # Só o SINAL de que existe devolutiva (para a lista mostrar o selo), não o
    # texto inteiro de cada uma: o histórico carrega até 100 redações e o
    # payload cresceria dezenas de KB sem nada na tela usar isso.
    feedbacks_cursor = _db.redacao_feedbacks.find(
        {"_id": {"$in": ids}, "user_id": user.user_id, "status": "concluida"}, {"_id": 1},
    )
    com_feedback = {f["_id"] async for f in feedbacks_cursor}
    return {
        "items": [
            {
                "redacao": r,
                "avaliacao": avaliacoes.get(r["redacao_id"]),
                "tem_feedback": r["redacao_id"] in com_feedback,
            }
            for r in redacoes
        ],
        "count": len(redacoes),
        "custo_correcao": CORRECAO_COST,
        "custo_feedback": FEEDBACK_COST,
    }
