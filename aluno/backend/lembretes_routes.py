"""“Lembrar-me com a Mentis” — a fila do que o aluno marcou para não esquecer.

O gesto é o mesmo em toda parte do produto: o aluno seleciona um trecho (ou
um objeto marcado com `data-lembrar-*`), aparece um botão flutuante, e aquilo
entra numa fila que a aba de Revisões mostra. Isto é o servidor desse gesto.

**Por que uma fila DECLARADA, se já existe `revisao_espacada`.** A fila do
`/revisao/fila` é inferida: ela nasce de um erro que o motor cognitivo
conseguiu explicar, e só existe para o que o acervo sabe anotar. Nada nela
pode nascer de "eu li isto e não entendi" — que é a coisa mais comum que
acontece com um aluno estudando, e a que o produto não tinha onde guardar.
As duas convivem de propósito:

* `/revisao/fila`   — o que o SAPIENS deduziu que você precisa rever.
* `/lembretes`      — **esta**: o que VOCÊ disse que quer dominar.

**Nenhuma chamada a LLM acontece aqui, e isso é a regra, não o estado atual.**
`mentis_routes.explicar_trecho` guarda a regra da casa em maiúsculas: *o texto
nunca vem do cliente*, porque um botão que manda texto livre para o Gemini é
um chat genérico disfarçado de botão de 10 Sparks. Aqui o texto VEM do cliente
— é uma seleção da tela dele — e é justamente por isso que ele não vira prompt
nenhum neste arquivo: o que se compra por `LEMBRETE_COST` é o LUGAR NA FILA,
não geração. Quando a revisão programada existir, o que ela mandar para a
Mentis será montado a partir do que o servidor já sabe sobre a origem, e não
do texto solto — a mesma disciplina de `explicar_trecho`.

**Cobra-se uma vez por trecho, para sempre.** O `_id` do documento é o hash do
texto normalizado + a origem: marcar duas vezes o mesmo parágrafo da mesma
tela é a MESMA linha da fila, e a segunda não cobra. Isso cobre de uma vez o
duplo toque no celular, o retry do axios, o F5 no meio e o aluno que volta na
mesma página semanas depois — nenhum desses precisa de chave de idempotência
para funcionar, porque a identidade do conteúdo já é a chave.

**A revisão programada** (desde 2026-10-01). Cada lembrete carrega um bloco
`agendamento` com a forma de `revisao_espacada` (`degrau`, `revisar_em`) e a
MESMA escada (`INTERVALOS_DIAS`: 1, 3, 7, 16, 35 dias). O trecho volta no dia
seguinte ao que foi guardado; "Revisei" (`/revisei`) sobe um degrau e marca a
próxima volta; quem revisa no último degrau completa o ciclo e o trecho sai da
fila como revisado. "Já domino isto" (`/revisado`) continua sendo a saída
direta, a qualquer momento. Lembrete anterior a isto (estado `aguardando`,
sem data) vence no dia seguinte ao que foi guardado — calculado na leitura,
sem migração, que é exatamente o que o campo nascer pronto comprou.

Nada aqui chama modelo e nada aqui cobra: rever o que se guardou é de graça,
como ver e remover. O que os 10 Sparks compraram foi o lugar na fila — e um
lugar que nunca volta não valia o que custou.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, timedelta
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

import firestore_service as fs
import rate_limit
import revisao_espacada as rev  # pura, zero I/O — só a escada de intervalos
from auth import require_user
from models import User, _now_iso
import rotas_do_app as rotas

logger = logging.getLogger("sapiens.lembretes")

router = APIRouter(prefix="/lembretes", tags=["lembretes"])

COLECAO = "lembretes_revisao"

# ---------------------------------------------------------------------------
# O preço
# ---------------------------------------------------------------------------
#
# Dez Sparks — o mesmo preço de "Explicar melhor" num trecho de curso
# (`mentis_routes.EXPLICACAO_CONTEUDO_COST`) e de uma mensagem no chat. Não é
# monetização de um `insert_one`: é o que faz a fila significar alguma coisa,
# pela mesma razão que a lista de espera da mentoria passou a custar
# (`mentoria_routes.ENTRADA_COST`).
#
# Uma fila de graça enche de trecho marcado "por via das dúvidas" — e uma fila
# de 200 linhas é uma fila que o aluno nunca mais abre, o que é o mesmo que não
# ter fila. Um preço pequeno faz cada linha ser uma escolha.
LEMBRETE_COST = 10

# Um trecho é uma FRASE ou um parágrafo, não um capítulo. O teto existe para o
# que a Mentis vai conseguir revisar depois: um lembrete de 20 mil caracteres
# não é um ponto a dominar, é a página inteira copiada — e revisar "a página
# inteira" não é revisar nada. O excedente é cortado, não recusado: recusar
# depois de o aluno ter selecionado é perder o gesto por causa de um limite
# que ele não tinha como conhecer.
MAX_TEXTO = 1200

# Abaixo disto não há o que rever. Uma seleção de duas letras é quase sempre
# um toque acidental num parágrafo, e cobrar por ela seria cobrar por engano.
MIN_TEXTO = 3

MAX_ROTULO = 200
# Teto da fila por aluno. Não é limite de banco — é a mesma razão do preço:
# passar daqui, a fila deixou de ser uma lista de intenções e virou um arquivo
# morto. Quando enche, o aluno tira alguma coisa (de graça) antes de pôr outra.
TETO_DA_FILA = 200

_db = None


def set_db(db):
    global _db
    _db = db


# ---------------------------------------------------------------------------
# Dinheiro
# ---------------------------------------------------------------------------


def _cobrar(uid: str, custo: int) -> int:
    fs.ensure_sparks_balance(uid)
    try:
        return fs.deduct_sparks(uid, custo)
    except fs.InsufficientSparksError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"Sparks insuficientes: saldo {exc.balance}, custo {exc.needed}.",
        ) from exc


def _saldo(uid: str) -> Optional[int]:
    try:
        return fs.read_sparks_balance(uid)
    except Exception:  # noqa: BLE001
        logger.exception("lembretes: leitura de saldo falhou para %s", uid)
        return None


# ---------------------------------------------------------------------------
# Identidade de um lembrete
# ---------------------------------------------------------------------------


def normalizar(texto: str) -> str:
    """O texto como ele conta para a IDENTIDADE do lembrete.

    Espaços colapsados e caixa ignorada porque a mesma frase selecionada duas
    vezes quase nunca sai igual byte a byte: o navegador inclui (ou não) a
    quebra de linha do fim do parágrafo, a seleção de toque pega o espaço
    seguinte, e o aluno raramente acerta o mesmo começo. Se essas diferenças
    contassem, "cobra uma vez por trecho" seria falso na prática — que é o
    único jeito de esta regra falhar.
    """
    return re.sub(r"\s+", " ", (texto or "")).strip().casefold()


def chave_do_lembrete(uid: str, texto: str, origem: str) -> str:
    """`_id` determinístico: mesmo aluno + mesmo texto + mesma origem.

    A ORIGEM entra no hash de propósito. O mesmo conceito marcado na aula de
    um curso e depois no enunciado de uma questão são duas lembranças
    diferentes — a segunda tem contexto que a primeira não tem, e apagar uma
    não deveria apagar a outra. O que a chave impede é marcar DUAS VEZES a
    mesma coisa no mesmo lugar.

    > A origem é **normalizada** antes de entrar no hash, e isso é dinheiro.
    >
    > A origem é a rota da tela. Quando `/redacao` virou `/estudar/redacao`
    > (2026-09-18), todo lembrete guardado antes da renomeação passou a ter uma
    > chave que o app não consegue mais reconstruir: o aluno que marcasse o
    > MESMO trecho de novo pagaria os 10 Sparks uma segunda vez, e a lista
    > mostraria a mesma frase duplicada. Uma renomeação de tela virando
    > cobrança em dobro.
    >
    > `rotas.normalizar` traduz o endereço antigo no atual, então as duas
    > formas colapsam na mesma chave — em qualquer direção, e para sempre.
    """
    return _chave(uid, texto, rotas.normalizar(origem))


def _chave(uid: str, texto: str, origem: str) -> str:
    digest = hashlib.sha256(f"{normalizar(texto)}|{origem or ''}".encode()).hexdigest()
    return f"{uid}:{digest[:32]}"


def chaves_do_lembrete(uid: str, texto: str, origem: str) -> list[str]:
    """A chave canônica primeiro, e depois as que o MESMO trecho teria tido nos
    endereços antigos daquela tela.

    Quem escreve usa `chave_do_lembrete` (a primeira desta lista). Quem PROCURA
    usa todas: sem isso, o aluno que guardou um trecho em `/redacao` antes da
    renomeação de 2026-09-18 pagaria os 10 Sparks de novo pelo mesmo trecho em
    `/estudar/redacao`, e a fila mostraria a frase duplicada.

    A ordem importa: a canônica na frente, para que um documento novo vença um
    antigo caso os dois existam (o antigo só existe se o aluno guardou o trecho
    nas duas épocas, e aí o recente é o que ele acabou de ver).
    """
    canonica = rotas.normalizar(origem)
    chaves = [_chave(uid, texto, canonica)]
    for antiga in rotas.antecessores(canonica):
        chave = _chave(uid, texto, antiga)
        if chave not in chaves:
            chaves.append(chave)
    return chaves


def _limpar(doc: dict) -> dict[str, Any]:
    return {k: v for k, v in (doc or {}).items() if k != "_id"} | {
        "lembrete_id": (doc or {}).get("_id", "").split(":", 1)[-1]
    }


def _somar_dias(dia: str, dias: int) -> str:
    return (date.fromisoformat(dia) + timedelta(days=dias)).isoformat()


def _agendamento_inicial(agora: str | None = None) -> dict[str, Any]:
    """O trecho volta no dia seguinte ao que foi guardado (`INTERVALOS_DIAS[0]`),
    no fuso do aluno. Os nomes são os de `revisao_espacada`."""
    return {
        "estado": "agendado",     # agendado → revisado
        "degrau": 0,
        "revisar_em": _somar_dias(fs.dia_local(agora), rev.INTERVALOS_DIAS[0]),
        "revisoes": 0,
        "ultima_revisao_em": None,
    }


def _revisar_em(doc: dict) -> Optional[str]:
    """Quando o trecho volta. O lembrete anterior à revisão programada não
    tem data (`aguardando`): vence no dia seguinte ao que foi guardado,
    calculado aqui na leitura — sem migrar coleção nenhuma."""
    ag = doc.get("agendamento") or {}
    if ag.get("revisar_em"):
        return ag["revisar_em"]
    criado = doc.get("criado_em")
    return _somar_dias(fs.dia_local(criado), rev.INTERVALOS_DIAS[0]) if criado else None


def _vestir(doc: dict, hoje: str) -> dict[str, Any]:
    """A linha como a tela a lê: com a data efetiva da volta e se é hoje."""
    linha = _limpar(doc)
    quando = _revisar_em(doc)
    linha["revisar_em"] = quando
    linha["vencido"] = bool(doc.get("status") == "aberto" and quando and quando <= hoje)
    return linha


# ---------------------------------------------------------------------------
# Entrada da fila
# ---------------------------------------------------------------------------


class LembretePayload(BaseModel):
    """O que a camada global de captura manda. Tudo é do CLIENTE, e nada disto
    vira prompt — ver o docstring do módulo."""

    texto: str = Field(..., min_length=1)
    # Onde o aluno estava. `rota` é o caminho do app (`/cursos/x/estacao/y`),
    # `titulo` é o que a tela se chamava e `contexto` é a frase que a página já
    # declara para a Mentis (`useDeclararContextoMentis`) — três camadas da
    # mesma resposta, porque a rota sozinha não diz nada a um humano seis
    # semanas depois, e o título sozinho não permite voltar lá.
    rota: str = Field(default="", max_length=400)
    titulo: str = Field(default="", max_length=MAX_ROTULO)
    contexto: str = Field(default="", max_length=400)
    # "texto" (seleção) ou "objeto" (elemento marcado com `data-lembrar-*`).
    tipo: str = Field(default="texto", max_length=20)
    # Referência estruturada quando a tela sabe dar uma (`item_id` de questão,
    # `curso:estacao`, `ebook:pagina`). É o que a revisão programada vai usar
    # para montar o pedido à Mentis a partir do CONTEÚDO PUBLICADO, em vez do
    # texto solto — ver o docstring do módulo.
    ref: str = Field(default="", max_length=200)
    nota: str = Field(default="", max_length=400)


def _texto_valido(bruto: str) -> str:
    texto = re.sub(r"[ \t]+", " ", (bruto or "").strip())
    if len(normalizar(texto)) < MIN_TEXTO:
        raise HTTPException(
            status_code=422,
            detail="Selecione um trecho um pouco maior para a Mentis conseguir revisar.",
        )
    return texto[:MAX_TEXTO]


@router.post("")
async def guardar(
    payload: LembretePayload,
    user: User = Depends(require_user),
    _: None = Depends(rate_limit.por_usuario("lembretes")),
):
    """Põe um trecho na fila de revisões do aluno, cobrando `LEMBRETE_COST`.

    **Reivindica, depois cobra.** Mesma ordem de `cursos_routes.
    _reivindicar_e_cobrar`: o `insert_one` de `_id` determinístico é a única
    primitiva do Mongo que decide um empate entre dois cliques sem transação.
    Se o débito falhar, a reivindicação é DESFEITA — um lembrete gravado sem
    cobrança é uma linha de graça, e uma cobrança sem lembrete é pior ainda.

    Marcar de novo o mesmo trecho não é erro nem 409: é o aluno reafirmando
    algo que já está na fila. Devolve a linha existente com `cobrado: 0`.
    """
    texto = _texto_valido(payload.texto)
    rota = (payload.rota or "").strip()[:400]
    chaves = chaves_do_lembrete(user.user_id, texto, rota)
    doc_id = chaves[0]

    # Procura por TODAS as formas que esta chave já teve — ver
    # `chaves_do_lembrete`. Uma renomeação de tela não pode virar cobrança
    # nova em cima de um trecho que o aluno já pagou.
    ja = await _db[COLECAO].find_one({"_id": {"$in": chaves}})
    if ja is not None:
        return {
            "lembrete": _limpar(ja),
            "ja_estava": True,
            "cobrado": 0,
            "sparks_balance": _saldo(user.user_id),
        }

    if await _db[COLECAO].count_documents({"user_id": user.user_id}) >= TETO_DA_FILA:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A sua fila já tem {TETO_DA_FILA} pontos guardados. "
                "Revise ou remova alguns antes de guardar outro."
            ),
        )

    agora = _now_iso()
    doc = {
        "_id": doc_id,
        "user_id": user.user_id,
        "texto": texto,
        "rota": rota,
        "titulo": (payload.titulo or "").strip()[:MAX_ROTULO],
        "contexto": (payload.contexto or "").strip()[:400],
        "tipo": "objeto" if payload.tipo == "objeto" else "texto",
        "ref": (payload.ref or "").strip()[:200],
        "nota": (payload.nota or "").strip()[:400],
        "status": "aberto",              # aberto → revisado
        "criado_em": agora,
        "atualizado_em": agora,
        "custo_sparks": LEMBRETE_COST,
        "agendamento": _agendamento_inicial(agora),
    }

    try:
        await _db[COLECAO].insert_one(doc)
    except DuplicateKeyError:
        # Duplo toque no mesmo instante: o outro venceu a corrida e já pagou.
        existente = await _db[COLECAO].find_one({"_id": doc_id})
        return {
            "lembrete": _limpar(existente or doc),
            "ja_estava": True,
            "cobrado": 0,
            "sparks_balance": _saldo(user.user_id),
        }

    try:
        fs.ensure_student_profile(user.user_id, user.name, user.email)
        saldo = _cobrar(user.user_id, LEMBRETE_COST)
    except HTTPException:
        await _db[COLECAO].delete_one({"_id": doc_id})
        raise
    except Exception as exc:  # noqa: BLE001
        await _db[COLECAO].delete_one({"_id": doc_id})
        logger.exception("lembretes: falha ao cobrar de %s", user.user_id)
        raise HTTPException(
            status_code=503,
            detail="Não foi possível guardar agora. Nenhum Spark foi debitado — tente de novo.",
        ) from exc

    await _db[COLECAO].update_one({"_id": doc_id}, {"$set": {"cobrado": True, "saldo_apos": saldo}})
    logger.info("lembrete guardado para %s (-%d Sparks).", user.user_id, LEMBRETE_COST)
    return {
        "lembrete": _limpar({**doc, "cobrado": True, "saldo_apos": saldo}),
        "ja_estava": False,
        "cobrado": LEMBRETE_COST,
        "sparks_balance": saldo,
    }


# ---------------------------------------------------------------------------
# Leitura e manutenção da fila — de graça, sempre
# ---------------------------------------------------------------------------
#
# Ver, remover e marcar como revisado não custam Spark. Pelo mesmo motivo de
# `revisao_routes`: cobrar para OLHAR a própria fila faria o aluno não olhar, e
# cobrar para remover o lembrete errado faria ele conviver com o erro — que é
# exatamente o contrário do que a fila existe para produzir.


@router.get("")
async def meus_lembretes(
    # `Annotated` e não `= Query(...)`: o DEFAULT continua sendo um valor
    # Python de verdade. Com `= Query(False)` o default é o objeto `Query`, que
    # é truthy — a rota se comporta certo sob HTTP e errado em qualquer chamada
    # direta, que é justamente como os testes deste repo a exercitam.
    limite: Annotated[int, Query(ge=1, le=TETO_DA_FILA)] = 100,
    incluir_revisados: Annotated[bool, Query()] = False,
    user: User = Depends(require_user),
):
    filtro: dict[str, Any] = {"user_id": user.user_id}
    if not incluir_revisados:
        filtro["status"] = "aberto"
    docs = await _db[COLECAO].find(filtro).sort("criado_em", -1).to_list(length=limite)
    abertos = await _db[COLECAO].count_documents({"user_id": user.user_id, "status": "aberto"})

    hoje = fs.dia_local()
    itens = [_vestir(d, hoje) for d in docs]
    # Os que voltam hoje vêm primeiro; dentro de cada grupo, a ordem de sempre.
    itens.sort(key=lambda i: 0 if i["vencido"] else 1)

    # `vencidos` conta a fila ABERTA inteira, não só a página pedida: o Hoje
    # pede `limite=1` e precisa do número certo. A fila tem teto
    # (`TETO_DA_FILA`), então isto é limitado por construção — e é Mongo.
    if not incluir_revisados and limite >= abertos:
        abertos_docs = docs
    else:
        abertos_docs = await _db[COLECAO].find(
            {"user_id": user.user_id, "status": "aberto"},
        ).to_list(length=TETO_DA_FILA)
    vencidos = [d for d in abertos_docs if _vestir(d, hoje)["vencido"]]
    primeiro = _vestir(vencidos[0], hoje) if vencidos else None
    return {
        "itens": itens,
        "abertos": abertos,
        "vencidos": len(vencidos),
        # O suficiente para o Hoje dizer DE QUE é o trecho que voltou, sem
        # carregar a fila: a tela de origem e o começo do texto.
        "primeiro_vencido": (
            {"titulo": primeiro.get("titulo") or "", "texto": (primeiro.get("texto") or "")[:120]}
            if primeiro else None
        ),
        "custo": LEMBRETE_COST,
        "teto": TETO_DA_FILA,
    }


async def _meu(uid: str, lembrete_id: str) -> dict:
    """Carrega o lembrete garantindo que ele é DESTE aluno.

    A checagem é a chave composta, não um `find_one` pelo id seguido de um
    `if doc["user_id"] != uid`: o dono já faz parte do `_id`, então um id de
    outra pessoa simplesmente não existe para quem pergunta.
    """
    doc = await _db[COLECAO].find_one({"_id": f"{uid}:{lembrete_id}"})
    if doc is None:
        raise HTTPException(status_code=404, detail="Este lembrete não existe mais.")
    return doc


@router.post("/{lembrete_id}/revisado")
async def marcar_revisado(lembrete_id: str, user: User = Depends(require_user)):
    """O aluno diz que já dominou aquilo. Sai da fila aberta e fica guardado.

    Não apaga: o histórico do que ele mesmo marcou e depois resolveu é a única
    evidência que a fila declarada produz sobre si mesma — e é o que a revisão
    programada vai ler para saber se vale reapresentar o ponto ou não.
    """
    doc = await _meu(user.user_id, lembrete_id)
    agora = _now_iso()
    agendamento = {**(doc.get("agendamento") or _agendamento_inicial())}
    agendamento.update({
        "estado": "revisado",
        "revisoes": int(agendamento.get("revisoes") or 0) + 1,
        "ultima_revisao_em": agora,
    })
    await _db[COLECAO].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "revisado", "atualizado_em": agora, "agendamento": agendamento}},
    )
    return {"lembrete": _limpar({**doc, "status": "revisado", "agendamento": agendamento})}


@router.post("/{lembrete_id}/revisei")
async def revisei(lembrete_id: str, user: User = Depends(require_user)):
    """O aluno reviu o trecho no dia em que ele voltou: sobe um degrau e marca
    a próxima volta (`INTERVALOS_DIAS`). No último degrau o ciclo se completa
    e o trecho sai da fila como revisado — o mesmo estado de "Já domino isto",
    alcançado pelo caminho longo.

    Só no dia da volta (ou depois): rever antes faria a escada inteira caber
    numa tarde, e espaçar é o ponto. De graça, como ver e remover.
    """
    doc = await _meu(user.user_id, lembrete_id)
    if doc.get("status") != "aberto":
        raise HTTPException(status_code=409, detail="Este trecho já saiu da sua fila.")

    agora = _now_iso()
    hoje = fs.dia_local(agora)
    quando = _revisar_em(doc)
    if quando and quando > hoje:
        dia_mes = "/".join(reversed(quando.split("-")[1:]))
        raise HTTPException(status_code=409, detail=f"Ainda não é dia de rever isto: ele volta em {dia_mes}.")

    agendamento = {**(doc.get("agendamento") or {})}
    degrau = int(agendamento.get("degrau") or 0)
    revisoes = int(agendamento.get("revisoes") or 0) + 1
    if degrau >= len(rev.INTERVALOS_DIAS) - 1:
        status = "revisado"
        agendamento.update({
            "estado": "revisado", "revisoes": revisoes, "ultima_revisao_em": agora, "revisar_em": None,
        })
    else:
        status = "aberto"
        novo = degrau + 1
        agendamento.update({
            "estado": "agendado",
            "degrau": novo,
            "revisoes": revisoes,
            "ultima_revisao_em": agora,
            "revisar_em": _somar_dias(hoje, rev.INTERVALOS_DIAS[novo]),
        })
    await _db[COLECAO].update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": status, "atualizado_em": agora, "agendamento": agendamento}},
    )
    return {
        "lembrete": _vestir({**doc, "status": status, "agendamento": agendamento}, hoje),
        "ciclo_completo": status == "revisado",
    }


@router.delete("/{lembrete_id}")
async def remover(lembrete_id: str, user: User = Depends(require_user)):
    """Tira da fila. **Não devolve Sparks**, e é assim de propósito.

    Guardar é a compra; a fila é o que foi entregue. Devolver no apagar
    transformaria "guardar" em grátis com passos extras, e a fila voltaria a
    encher — que é o problema que o preço existe para resolver. O que protege
    o aluno do toque errado é o preço estar ESCRITO no botão que ele aperta,
    antes de apertar.
    """
    doc = await _meu(user.user_id, lembrete_id)
    await _db[COLECAO].delete_one({"_id": doc["_id"]})
    return {"removido": lembrete_id}
