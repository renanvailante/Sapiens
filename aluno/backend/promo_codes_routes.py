"""Rotas de códigos promocionais — bônus de Sparks no cadastro.

Um código é opcional no signup (e-mail/senha ou Google). Sem código válido, a
conta nova recebe o bônus padrão (`firestore_service.SPARKS_INITIAL_BALANCE`,
hoje 100). Com um código ativo, recebe a quantidade programada pelo admin em
vez do padrão — nunca as duas coisas somadas.

O catálogo vive no Mongo (`promo_codes`), não no Firestore: é configuração de
produto (como o catálogo de `sparks_store.py`), não estado do aluno.

Gestão é 100% admin (`/admin/promo-codes`); a validação em si
(`validar_e_registrar_uso`) é chamada só por `auth.py` no momento do signup —
não existe rota pública que aceite um código, então não há como sondar quais
códigos existem tentando um por um.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin
from models import CreatePromoCodeRequest, UpdatePromoCodeRequest, User, _now_iso

router = APIRouter(prefix="/admin/promo-codes", tags=["promo-codes"])

_db = None
def set_db(db):
    global _db
    _db = db


def _normalizar(code: str) -> str:
    return (code or "").strip().upper()


def _normalizar_promoter_email(email: str | None) -> str | None:
    """`None`/vazio limpa o vínculo; qualquer outra coisa exige um "@" —
    validação frouxa de propósito (é o admin digitando, não um formulário
    público), só o bastante para pegar o typo óbvio antes de virar a conta
    que decide quem vê o painel do promoter."""
    limpo = (email or "").strip().lower()
    if not limpo:
        return None
    if "@" not in limpo:
        raise HTTPException(status_code=422, detail="E-mail do promoter inválido.")
    return limpo


@router.get("")
async def list_promo_codes(admin: User = Depends(require_admin)):
    return await _db.promo_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@router.post("")
async def create_promo_code(payload: CreatePromoCodeRequest, admin: User = Depends(require_admin)):
    code = _normalizar(payload.code)
    if not code:
        raise HTTPException(status_code=422, detail="Código vazio.")
    if await _db.promo_codes.find_one({"code": code}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="Já existe um código com esse nome.")
    doc = {
        "code": code,
        "sparks_amount": payload.sparks_amount,
        "active": True,
        "usos": 0,
        "created_at": _now_iso(),
        "promoter_email": _normalizar_promoter_email(payload.promoter_email),
    }
    await _db.promo_codes.insert_one(doc)
    return doc


@router.patch("/{code}")
async def update_promo_code(code: str, payload: UpdatePromoCodeRequest, admin: User = Depends(require_admin)):
    # `exclude_unset`, não `exclude_none`: é o único jeito de o admin poder
    # LIMPAR o e-mail do promoter (mandar `promoter_email: null` de propósito)
    # em vez de "ausente" e "vazio" caírem no mesmo lugar.
    campos = payload.model_dump(exclude_unset=True)
    if not campos:
        raise HTTPException(status_code=422, detail="Nada para atualizar.")
    if "promoter_email" in campos:
        campos["promoter_email"] = _normalizar_promoter_email(campos["promoter_email"])
    alvo = _normalizar(code)
    res = await _db.promo_codes.update_one({"code": alvo}, {"$set": campos})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Código não encontrado.")
    return await _db.promo_codes.find_one({"code": alvo}, {"_id": 0})


@router.delete("/{code}")
async def delete_promo_code(code: str, admin: User = Depends(require_admin)):
    res = await _db.promo_codes.delete_one({"code": _normalizar(code)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Código não encontrado.")
    return {"ok": True}


async def validar_e_registrar_uso(code: str | None) -> dict | None:
    """Valida um código informado no signup e conta o uso.

    Retorna `{"code", "sparks_amount"}` do código aplicado, ou `None` se o
    código for vazio, inexistente ou desativado — nesse caso quem chamou
    aplica o bônus padrão. Um código digitado errado nunca vira erro de
    cadastro: só faz a conta nova entrar sem o bônus especial.

    Devolve o `code` NORMALIZADO junto do valor (e não só o valor, como
    antes) porque quem chama precisa gravar na conta QUAL cupom valeu — e o
    que a pessoa digitou pode diferir em caixa do que está no catálogo.
    """
    normalizado = _normalizar(code) if code else ""
    if not normalizado:
        return None
    doc = await _db.promo_codes.find_one_and_update(
        {"code": normalizado, "active": True},
        {"$inc": {"usos": 1}},
    )
    if not doc:
        return None
    return {"code": normalizado, "sparks_amount": doc.get("sparks_amount")}


@router.get("/uso")
async def uso_por_codigo(admin: User = Depends(require_admin)):
    """Quantos alunos usaram cada código — e quais.

    Duas contagens, de propósito, porque medem coisas diferentes:

    * `usos` é o contador incrementado em `validar_e_registrar_uso` desde que
      os códigos existem. É o histórico completo, mas anônimo.
    * `alunos` são as contas que carregam `promo_code`, gravado a partir de
      2026-09-15. Diz QUEM, e só enxerga cadastros posteriores a essa data.

    Quando os dois divergem, a diferença (`usos_sem_vinculo`) é exatamente o
    número de cadastros antigos, de antes do vínculo existir — não um defeito.
    """
    codigos = await _db.promo_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # Uma consulta só para todos os códigos, agrupada em memória: a base de
    # alunos é da ordem de dezenas/centenas e cabe inteira aqui; uma consulta
    # por código seria N idas ao Mongo para responder a mesma pergunta.
    vinculados = await _db.users.find(
        {"promo_code": {"$ne": None}},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1, "promo_code": 1,
         "promo_sparks": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(5000)

    por_codigo: dict[str, list[dict]] = {}
    for u in vinculados:
        por_codigo.setdefault(u["promo_code"], []).append(u)

    linhas = []
    for c in codigos:
        alunos = por_codigo.pop(c["code"], [])
        linhas.append({
            **c,
            "alunos": alunos,
            "alunos_count": len(alunos),
            "usos_sem_vinculo": max(0, int(c.get("usos") or 0) - len(alunos)),
        })

    # Cupons já EXCLUÍDOS do catálogo que ainda têm alunos ligados a eles.
    # Sumir com essas contas da tela seria perder a informação que o admin
    # veio buscar — o código não existe mais, mas o aluno usou.
    for code, alunos in por_codigo.items():
        linhas.append({
            "code": code, "sparks_amount": alunos[0].get("promo_sparks"),
            "active": False, "excluido": True, "usos": len(alunos),
            "created_at": None, "alunos": alunos, "alunos_count": len(alunos),
            "usos_sem_vinculo": 0,
        })

    return {
        "items": linhas,
        "total_alunos_com_cupom": len(vinculados),
        "vinculo_registrado_desde": "2026-09-15",
    }
