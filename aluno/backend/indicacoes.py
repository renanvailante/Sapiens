"""Indicação de amigo — o código que cada aluno carrega e o prêmio da
primeira compra de quem ele trouxe.

**O que é, em uma frase.** Todo aluno tem um código pessoal; quem se cadastra
usando esse código fica ligado a ele para sempre; na PRIMEIRA compra do
indicado, o indicador recebe METADE dos Sparks que o indicado comprou. Uma
vez por indicado, nunca mais.

**Por que não é um `promo_code`.** Os cupons de `promo_codes_routes.py` são
catálogo de marketing: o admin cria, escolhe quantos Sparks o cadastro ganha,
liga e desliga. Aqui não há catálogo — o código nasce com a conta, pertence a
um aluno, e o que ele paga não é bônus de cadastro e sim comissão de compra.
São duas coisas com o mesmo formato e regras opostas, então moram em lugares
diferentes: cupom no Mongo em `promo_codes`, indicação no próprio documento do
aluno (`users.referral_code`) mais um registro de vínculo em `indicacoes`.

O aluno que se cadastra digita num campo SÓ, porque quem recebeu um código de
um amigo não tem como saber de que tipo ele é. A resolução é em ordem:
cupom do catálogo primeiro, indicação depois (ver `auth._bonus_de_cadastro`) —
o catálogo do admin vence um eventual empate de texto.

**Onde está a garantia de pagar uma vez só.** Não no "conte as compras
anteriores": essa contagem é uma leitura seguida de uma escrita, e dois
webhooks do Mercado Pago chegando juntos leem o mesmo zero. A garantia é a
REIVINDICAÇÃO ATÔMICA em `creditar_primeira_compra`: um `find_one_and_update`
carimba no vínculo qual pagamento ganhou o prêmio, e o filtro só aceita
vínculo ainda não carimbado OU carimbado por ESTE mesmo pagamento. O primeiro
caso é a primeira compra; o segundo é o reenvio de webhook, que precisa poder
repetir o caminho inteiro sem pagar de novo (o crédito em si é idempotente por
`chave=mp_payment_id` no Firestore).
"""
from __future__ import annotations

import logging
import secrets
import unicodedata
import re
from typing import Any

logger = logging.getLogger("sapiens.indicacoes")

# Sem I, O, 0 e 1: o código é lido em voz alta e digitado à mão a partir de um
# print no WhatsApp, e esses quatro são exatamente os que viram outro caractere
# no caminho.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_SUFIXO = 4
_PREFIXO_MAX = 6

#: Fração dos Sparks da compra do indicado que vai para quem indicou.
FRACAO_RECOMPENSA = 0.5


def normalizar(code: str | None) -> str:
    return (code or "").strip().upper()


def _prefixo(nome: str) -> str:
    """Primeiro nome, sem acento, só letras — é o que faz o aluno reconhecer
    o próprio código e conseguir ditá-lo. Nome que não sobra letra nenhuma
    (só emoji, só número) cai em `AMIGO`."""
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii")
    primeiro = re.sub(r"[^A-Za-z]", "", sem_acento.split(" ")[0]).upper()
    return primeiro[:_PREFIXO_MAX] or "AMIGO"


def _sortear(nome: str, tamanho: int = _SUFIXO) -> str:
    sufixo = "".join(secrets.choice(_ALFABETO) for _ in range(tamanho))
    return f"{_prefixo(nome)}{sufixo}"


class ContaSemCadastro(LookupError):
    """Pediram o código de um `user_id` que não existe em `users`.

    Alto de propósito. A alternativa — devolver um código bonito sem gravá-lo —
    entregaria ao aluno um texto que ninguém consegue resolver de volta: o
    amigo se cadastraria com ele, `resolver_indicador` não acharia dono, e o
    prêmio simplesmente não aconteceria, sem erro em lugar nenhum.
    """


async def _codigo_livre(db, codigo: str) -> bool:
    """Livre = não é de outro aluno E não é um cupom do catálogo.

    A segunda metade importa: os dois vivem no mesmo campo do cadastro, e um
    código de indicação que repetisse o texto de um cupom ativo seria sempre
    lido como cupom (o catálogo tem precedência) — o indicador nunca receberia
    nada e não haveria como descobrir por quê.
    """
    if await db.users.find_one({"referral_code": codigo}, {"_id": 1}):
        return False
    if await db.promo_codes.find_one({"code": codigo}, {"_id": 1}):
        return False
    return True


async def garantir_codigo(db, user_id: str, nome: str) -> str:
    """Código do aluno, criando-o na primeira vez que alguém pergunta.

    Preguiçoso de propósito: assim as contas que já existiam antes desta
    feature ganham o código ao abrir a tela, sem migração e sem uma escrita
    em cada conta da base.
    """
    doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "referral_code": 1})
    if doc is None:
        raise ContaSemCadastro(user_id)
    if doc.get("referral_code"):
        return doc["referral_code"]

    for tentativa in range(8):
        # 32^4 sufixos por prefixo de nome: colidir uma vez já é raro. Se
        # mesmo assim colidir seis vezes, o sufixo DOBRA em vez de a tela
        # quebrar — 32^8 encerra o assunto, e o código continua sem I/O/0/1.
        candidato = _sortear(nome, _SUFIXO if tentativa < 6 else _SUFIXO * 2)
        if not await _codigo_livre(db, candidato):
            continue
        # `referral_code: None` no filtro cobre também o campo AUSENTE (é assim
        # que o Mongo trata null), e é o que impede duas requisições
        # simultâneas do mesmo aluno de gravarem códigos diferentes: a segunda
        # não casa mais e cai no `find_one` de baixo, que devolve o primeiro.
        res = await db.users.update_one(
            {"user_id": user_id, "referral_code": None},
            {"$set": {"referral_code": candidato}},
        )
        if res.matched_count:
            return candidato
        atual = await db.users.find_one({"user_id": user_id}, {"_id": 0, "referral_code": 1})
        if atual is None:
            raise ContaSemCadastro(user_id)
        if atual.get("referral_code"):
            return atual["referral_code"]

    raise RuntimeError(f"Não consegui sortear um código livre para {user_id}.")


async def resolver_indicador(db, code: str | None) -> dict | None:
    """Dono do código, ou `None`. Só o que o vínculo precisa saber."""
    codigo = normalizar(code)
    if not codigo:
        return None
    return await db.users.find_one(
        {"referral_code": codigo}, {"_id": 0, "user_id": 1, "name": 1, "referral_code": 1}
    )


async def registrar_indicacao(db, *, indicado_id: str, indicador_id: str, codigo: str) -> None:
    """Grava o vínculo no cadastro do indicado.

    Duas gravações, de propósito:

    * `users.{indicado}.indicado_por` — a conta carrega de quem ela veio, do
      mesmo jeito que já carrega `promo_code`. É o que a ficha do aluno lê.
    * `indicacoes` — o documento de PRÊMIO, com `_id` igual ao id do indicado.
      Ter `_id` determinístico é o que torna o vínculo único por aluno sem
      depender de índice, e é sobre ele que a reivindicação atômica da
      primeira compra acontece.

    Ninguém pode indicar a si mesmo — no cadastro isso é impossível (a conta
    não existia para ter código), mas a guarda fica aqui porque é aqui que a
    regra mora.
    """
    if not indicador_id or indicador_id == indicado_id:
        return
    await db.users.update_one(
        {"user_id": indicado_id},
        {"$set": {"indicado_por": indicador_id, "indicado_por_codigo": codigo}},
    )
    from models import _now_iso

    try:
        await db.indicacoes.insert_one({
            "_id": indicado_id,
            "indicado_id": indicado_id,
            "indicador_id": indicador_id,
            "codigo": codigo,
            "created_at": _now_iso(),
            # Carimbo da reivindicação — ver `creditar_primeira_compra`.
            "premio_mp_payment_id": None,
            "premio_sparks": 0,
            "premio_em": None,
        })
    except Exception:  # noqa: BLE001  (DuplicateKey: já havia vínculo)
        logger.info("Vínculo de indicação já existia para %s — mantido o primeiro.", indicado_id)


async def creditar_primeira_compra(
    db, *, comprador_id: str, mp_payment_id: str, sparks_comprados: int,
) -> dict[str, Any] | None:
    """Paga ao indicador metade dos Sparks desta compra — se esta for a
    primeira compra do indicado.

    Devolve `None` quando não há nada a pagar (aluno sem indicador, ou prêmio
    já pago numa compra anterior). Chamado de dentro do webhook de pagamento,
    logo depois do crédito do comprador, e NUNCA pode derrubá-lo: quem chama
    trata a exceção.

    A ordem — reivindicar no Mongo, creditar no Firestore — é deliberada. Se o
    processo morrer entre as duas, o vínculo fica carimbado com este pagamento
    e sem `premio_em`; o reenvio do webhook casa de novo pelo braço
    `premio_mp_payment_id == mp_payment_id`, refaz o crédito (idempotente por
    chave no Firestore) e fecha o carimbo. A ordem inversa pagaria duas vezes
    duas compras diferentes que chegassem juntas.
    """
    import firestore_service as fs
    from models import _now_iso

    premio = int(sparks_comprados * FRACAO_RECOMPENSA)
    if premio <= 0:
        return None

    vinculo = await db.indicacoes.find_one_and_update(
        {
            "indicado_id": comprador_id,
            "premio_mp_payment_id": {"$in": [None, mp_payment_id]},
        },
        {"$set": {"premio_mp_payment_id": mp_payment_id}},
    )
    if not vinculo:
        return None

    indicador_id = vinculo["indicador_id"]
    resultado = fs.grant_sparks_evento(
        indicador_id,
        categoria="indicacao",
        chave=str(mp_payment_id),
        amount=premio,
        meta={"indicado_id": comprador_id, "sparks_da_compra": sparks_comprados},
    )
    await db.indicacoes.update_one(
        {"indicado_id": comprador_id},
        {"$set": {"premio_sparks": premio, "premio_em": _now_iso()}},
    )
    logger.info(
        "Indicação: %s recebeu %s Sparks pela primeira compra de %s (pagamento %s).",
        indicador_id, premio, comprador_id, mp_payment_id,
    )
    return {
        "indicador_id": indicador_id,
        "premio_sparks": premio,
        "ja_creditado": bool(resultado.get("ja_concedido")),
    }


async def resumo(db, user_id: str, nome: str) -> dict[str, Any]:
    """O que a tela do aluno mostra: o código dele e quem entrou por ele.

    Uma consulta ao Mongo para os vínculos e uma para os nomes — nunca uma por
    amigo. Nenhum dado do Firestore entra aqui: o saldo já vem pelo caminho de
    sempre e ler um documento por indicado seria pagar leitura do Firestore
    por abrir uma tela (ver `project_aluno_disciplina_leitura_firestore`).
    """
    codigo = await garantir_codigo(db, user_id, nome)
    vinculos = await db.indicacoes.find(
        {"indicador_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    nomes: dict[str, str] = {}
    if vinculos:
        ids = [v["indicado_id"] for v in vinculos]
        contas = await db.users.find(
            {"user_id": {"$in": ids}}, {"_id": 0, "user_id": 1, "name": 1}
        ).to_list(500)
        nomes = {c["user_id"]: c.get("name") or "Amigo" for c in contas}

    amigos = [
        {
            "nome": nomes.get(v["indicado_id"], "Amigo"),
            "entrou_em": v.get("created_at"),
            "ja_comprou": bool(v.get("premio_em")),
            "premio_sparks": int(v.get("premio_sparks") or 0),
        }
        for v in vinculos
    ]
    return {
        "codigo": codigo,
        "amigos": amigos,
        "total_amigos": len(amigos),
        "total_sparks": sum(a["premio_sparks"] for a in amigos),
        "aguardando_primeira_compra": sum(1 for a in amigos if not a["ja_comprou"]),
        "fracao": FRACAO_RECOMPENSA,
    }
