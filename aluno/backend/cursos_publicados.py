"""Conteúdo de curso publicado pelo PAINEL, e não por commit.

`cursos_conteudo` explica por que o conteúdo mora em arquivo: revisão antes de
publicar, diff do que mudou, rollback de uma versão ruim e custo zero de
leitura em produção. Tudo isso continua verdade — e continua sendo o caminho
de quem escreve um curso inteiro.

Este módulo existe para o outro caso, que o arquivo não atende: **escrever uma
estação e vê-la no ar agora**, sem deploy. É o ciclo de quem está produzindo
conteúdo, e ele é medido em minutos, não em commits. O admin cola o texto, o
compilador (`cursos_ingestao`) transforma em blocos, o MESMO validador do
disco decide se entra, e o resultado é gravado no Mongo.

As quatro regras que este módulo não negocia
--------------------------------------------
1. **Passa pelo mesmo validador.** `cursos_conteudo.compor` é o único portão.
   Conteúdo publicado pelo painel obedece às cinco regras do contrato ou não
   é publicado — não existe validação "mais fácil" para o caminho rápido.
2. **O arquivo continua sendo a base.** Publicar uma estação nova num curso
   que já existe em arquivo ACRESCENTA: o disco é lido, a estação entra por
   cima e o conjunto inteiro é revalidado. O arquivo nunca é reescrito, então
   um `git checkout` continua sendo o rollback do que veio de commit.
3. **Nenhuma leitura por acesso de aluno.** O conteúdo vive em memória, como o
   do disco. O que custa é uma consulta minúscula (`_id` e `revisao`) no
   máximo a cada `INTERVALO_DE_CONFERENCIA` segundos, e só quando alguém está
   estudando — é O(1) por processo por minuto, não O(uso). A lição de
   2026-09-04 vale aqui inteira: nada em caminho quente pode custar uma
   leitura por requisição.
4. **Preço nunca entra.** A regra 1 do contrato é verificada por chave em todo
   o documento; um texto que declarasse "custo_sparks" seria recusado com a
   mesma mensagem que um arquivo faria.

Por que Mongo e não arquivo no disco da máquina
-----------------------------------------------
Porque o disco do Fly é efêmero e há mais de uma máquina: um arquivo escrito
em produção some no próximo deploy e nunca existiu para a máquina do lado. O
Mongo é o único lugar deste produto onde escrita de admin sobrevive — e é
barato: o documento inteiro de um curso é lido uma vez por processo.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import cursos_conteudo as cc
import cursos_ingestao as ci

logger = logging.getLogger("sapiens.cursos.publicados")

_db = None

# De quanto em quanto tempo um processo confere se OUTRO processo publicou
# alguma coisa. Sessenta segundos porque o Fly roda mais de uma máquina: quem
# publica atualiza a própria memória na hora, e as demais levam no máximo um
# minuto para enxergar. A conferência é uma projeção de `_id` e `revisao` sobre
# um punhado de documentos — comparável a nada, e ainda assim limitada no
# tempo, porque "barato vezes toda requisição" foi exatamente a conta que
# derrubou o app em 2026-09-04.
INTERVALO_DE_CONFERENCIA = 60.0

_ultima_conferencia = 0.0
_revisoes: dict[str, int] = {}


def set_db(db) -> None:
    global _db
    _db = db


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def versao_de_agora() -> str:
    """A versão do conteúdo publicado agora. É ela que separa quem estudou o
    quê nos dados — o progresso guarda a versão que o aluno de fato viu."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


# ---------------------------------------------------------------------------
# Mesclar arquivo + painel
# ---------------------------------------------------------------------------


def mesclar(curso_id: str, doc: dict) -> tuple[object | None, list[str]]:
    """Disco + o que o painel publicou, validado como um curso só.

    A ordem das trilhas e das estações que já existem em arquivo é preservada;
    o que o painel acrescenta entra no fim da trilha que ele indicou (ou numa
    trilha nova, se ela ainda não existir). Estação com id que já existe é
    SUBSTITUÍDA — é assim que se corrige um enunciado errado sem esperar
    deploy — e não entra de novo no manifesto, senão o mesmo conteúdo teria
    dois endereços e dois progressos.
    """
    disco = cc.do_disco().curso(curso_id)
    if disco is not None:
        manifesto = cc.manifesto_do_curso(disco)
        estacoes = {eid: cc.estacao_para_dados(e) for eid, e in disco.estacoes.items()}
    else:
        manifesto = {
            "schema_version": cc.SCHEMA_VERSION,
            "curso_id": curso_id,
            "versao": doc.get("versao") or versao_de_agora(),
            "trilhas": [],
        }
        estacoes = {}

    for dados in doc.get("estacoes") or []:
        eid = dados.get("estacao_id")
        if eid:
            estacoes[eid] = dados

    citadas = {e for t in manifesto["trilhas"] for e in t["estacoes"]}
    for trilha in doc.get("trilhas") or []:
        novas = [e for e in (trilha.get("estacoes") or []) if e in estacoes and e not in citadas]
        citadas |= set(novas)
        existente = next(
            (t for t in manifesto["trilhas"] if t["trilha_id"] == trilha.get("trilha_id")), None,
        )
        if existente is not None:
            existente["estacoes"] = list(existente["estacoes"]) + novas
        elif novas:
            manifesto["trilhas"].append({
                "trilha_id": trilha["trilha_id"],
                "titulo": trilha.get("titulo") or trilha["trilha_id"],
                **({"resumo": trilha["resumo"]} if trilha.get("resumo") else {}),
                "estacoes": novas,
            })

    if doc.get("versao"):
        manifesto["versao"] = doc["versao"]
    return cc.compor(curso_id, manifesto, estacoes)


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------


async def recarregar() -> dict[str, list[str]]:
    """Lê os cursos publicados no banco e aplica na biblioteca em memória.

    Devolve `{curso_id: problemas}` — curso com problema NÃO é aplicado e fica
    registrado para o painel. Acontece, e não é hipótese: o conteúdo em arquivo
    pode ter mudado por deploy depois da publicação (uma estação renomeada
    quebra o pré-requisito que apontava para ela), e é melhor o curso voltar a
    ser o do arquivo do que ir ao ar pela metade.
    """
    global _ultima_conferencia, _revisoes
    if _db is None:
        return {}

    docs = await _db.cursos_publicados.find({}).to_list(50)
    cursos: dict[str, object] = {}
    problemas: dict[str, list[str]] = {}
    for doc in docs:
        curso_id = doc.get("_id")
        if not curso_id:
            continue
        montado, erros = mesclar(curso_id, doc)
        if montado is None:
            problemas[curso_id] = erros
            logger.warning("Curso publicado `%s` fora do ar: %s", curso_id, "; ".join(erros[:3]))
            continue
        cursos[curso_id] = montado

    cc.aplicar_publicados(cursos)
    _revisoes = {d["_id"]: int(d.get("revisao") or 0) for d in docs if d.get("_id")}
    _ultima_conferencia = time.monotonic()
    logger.info("Conteúdo publicado pelo painel: %d curso(s) aplicado(s).", len(cursos))
    return problemas


async def garantir_atual() -> None:
    """Confere, no máximo uma vez por minuto, se outro processo publicou algo.

    Só a projeção `{_id, revisao}` sai do banco na conferência; o documento
    inteiro só é lido quando a revisão de fato mudou. Uma falha aqui é
    silenciosa de propósito: o conteúdo que já está em memória continua
    servindo, e um aluno no meio de uma estação não pode ver erro porque o
    banco piscou.
    """
    global _ultima_conferencia
    if _db is None:
        return
    if time.monotonic() - _ultima_conferencia < INTERVALO_DE_CONFERENCIA:
        return
    _ultima_conferencia = time.monotonic()
    try:
        atuais = await _db.cursos_publicados.find({}, {"revisao": 1}).to_list(50)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Não foi possível conferir o conteúdo publicado: %s", exc)
        return
    mapa = {d["_id"]: int(d.get("revisao") or 0) for d in atuais if d.get("_id")}
    if mapa != _revisoes:
        await recarregar()


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------


async def _gravar(doc: dict) -> None:
    """Grava o documento inteiro do curso. `$set` e não `replace_one` porque
    todo campo é escrito em toda gravação: o documento é montado inteiro em
    `publicar`, e um `$set` completo tem o mesmo efeito com metade das
    surpresas (e sem tocar no `_id`)."""
    corpo = {k: v for k, v in doc.items() if k != "_id"}
    await _db.cursos_publicados.update_one({"_id": doc["_id"]}, {"$set": corpo}, upsert=True)


async def documento(curso_id: str) -> dict:
    if _db is None:
        return {}
    return await _db.cursos_publicados.find_one({"_id": curso_id}) or {}


async def publicar(
    curso_id: str,
    estacoes: list[dict],
    *,
    trilha_id: str,
    trilha_titulo: str,
    trilha_resumo: str | None = None,
    por: str,
    versao: str | None = None,
) -> tuple[list[str], dict]:
    """Grava as estações compiladas e as aplica na hora.

    Devolve `(problemas, resumo)`. Com problema, **nada é gravado**: o painel
    mostra a lista e o curso continua exatamente como estava. Validar depois
    de gravar transformaria um erro de digitação numa estação quebrada no ar.
    """
    if _db is None:
        return ["Banco indisponível."], {}

    anterior = await documento(curso_id)
    por_id = {d["estacao_id"]: d for d in (anterior.get("estacoes") or [])}
    ordem = [d["estacao_id"] for d in (anterior.get("estacoes") or [])]
    for dados in estacoes:
        if dados["estacao_id"] not in por_id:
            ordem.append(dados["estacao_id"])
        por_id[dados["estacao_id"]] = dados

    trilhas = [dict(t) for t in (anterior.get("trilhas") or [])]
    alvo = next((t for t in trilhas if t["trilha_id"] == trilha_id), None)
    novas = [d["estacao_id"] for d in estacoes]
    if alvo is None:
        trilhas.append({
            "trilha_id": trilha_id,
            "titulo": trilha_titulo,
            **({"resumo": trilha_resumo} if trilha_resumo else {}),
            "estacoes": novas,
        })
    else:
        alvo["estacoes"] = list(alvo["estacoes"]) + [e for e in novas if e not in alvo["estacoes"]]

    doc = {
        "_id": curso_id,
        "versao": versao or versao_de_agora(),
        "revisao": int(anterior.get("revisao") or 0) + 1,
        "estacoes": [por_id[e] for e in ordem],
        "trilhas": trilhas,
        "publicado_em": _agora_iso(),
        "publicado_por": por,
        "origem": "texto",
    }

    montado, problemas = mesclar(curso_id, doc)
    if montado is None:
        return problemas, {}

    await _gravar(doc)
    await recarregar()
    return [], resumo_do_documento(doc)


async def despublicar(curso_id: str, *, estacao_id: str | None = None) -> dict:
    """Tira do ar o que o painel publicou — um curso inteiro ou uma estação.

    O conteúdo que veio de arquivo volta a valer sozinho: ele nunca foi
    apagado, só estava coberto. É o desfazer de quem publicou um texto errado,
    e ele precisa existir sem deploy pelo mesmo motivo que o publicar.
    """
    if _db is None:
        return {}
    doc = await documento(curso_id)
    if not doc:
        return {}

    if estacao_id:
        doc["estacoes"] = [d for d in (doc.get("estacoes") or []) if d["estacao_id"] != estacao_id]
        doc["trilhas"] = [
            {**t, "estacoes": [e for e in t["estacoes"] if e != estacao_id]}
            for t in (doc.get("trilhas") or [])
        ]
        doc["trilhas"] = [t for t in doc["trilhas"] if t["estacoes"]]

    if not estacao_id or not doc.get("estacoes"):
        await _db.cursos_publicados.delete_one({"_id": curso_id})
        await recarregar()
        return {"curso_id": curso_id, "removido": True}

    doc["revisao"] = int(doc.get("revisao") or 0) + 1
    await _gravar(doc)
    await recarregar()
    return resumo_do_documento(doc)


def resumo_do_documento(doc: dict) -> dict:
    """O que o painel mostra de um curso publicado — nunca os blocos inteiros,
    que são grandes e não cabem numa lista."""
    return {
        "curso_id": doc.get("_id"),
        "versao": doc.get("versao"),
        "revisao": doc.get("revisao"),
        "publicado_em": doc.get("publicado_em"),
        "publicado_por": doc.get("publicado_por"),
        "estacoes": [
            {
                "estacao_id": d["estacao_id"],
                "titulo": d.get("titulo"),
                "numero": d.get("numero"),
                "exercicios": sum(1 for b in d.get("blocos") or [] if b["tipo"] == "exercicio"),
                "blocos": len(d.get("blocos") or []),
            }
            for d in (doc.get("estacoes") or [])
        ],
        "trilhas": [
            {"trilha_id": t["trilha_id"], "titulo": t.get("titulo"), "estacoes": len(t["estacoes"])}
            for t in (doc.get("trilhas") or [])
        ],
    }


async def listar() -> list[dict]:
    if _db is None:
        return []
    docs = await _db.cursos_publicados.find({}).to_list(50)
    return [resumo_do_documento(d) for d in docs]


# ---------------------------------------------------------------------------
# Compilar (sem gravar)
# ---------------------------------------------------------------------------


def compilar_texto(curso_id: str, texto: str, *, versao: str | None = None) -> ci.Compilada:
    """Compila o texto contra o que o curso JÁ tem.

    Duas coisas saem do estado atual do curso e não do texto: o número da
    primeira estação sem número declarado (quem cola a 25ª não deveria ter de
    dizer que é a 25ª) e a lista de endereços já usados, para uma estação nova
    não nascer com o endereço de uma que existe.
    """
    existente = cc.biblioteca().curso(curso_id)
    ids = set(existente.estacoes) if existente else set()
    numeros = [e.numero for e in existente.estacoes.values() if e.numero] if existente else []
    return ci.compilar(
        curso_id,
        texto,
        versao=versao or versao_de_agora(),
        numero_inicial=(max(numeros) + 1) if numeros else 1,
        ids_existentes=ids,
    )
