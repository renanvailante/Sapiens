"""Uma resposta de curso vira um evento do MESMO contrato de behavior do ENEM.

Por que isto existe
-------------------
O Sapiens já tem um registro comportamental — o contrato **BEH-1.1**
(`pipeline/docs/behavior/07 behavior student 1.4.md`), escrito por
`firestore_service.write_behavior_event` em `students/{uid}/behavior`. É dele
que sai tudo o que o produto sabe sobre como o aluno responde: a prova do
ENEM, o Treino de habilidades e, a partir daqui, o curso.

**Curso NÃO ganha um formato próprio.** Um segundo esquema "parecido" seria a
maneira mais eficiente de tornar impossível a pergunta que justifica o
ecossistema inteiro: *este aluno erra o mesmo tipo de coisa na prova e na
aula?* Duas coleções com campos diferentes não se cruzam; uma coleção com os
mesmos campos se cruza com um `where`.

Como o curso cabe no contrato canônico, campo a campo
-----------------------------------------------------
O contrato tem os campos que tem, e é governado (GOV-1.0 §6.1) — este módulo
o PREENCHE, não o estende:

| campo canônico | o que o curso põe nele |
|---|---|
| `item_id` | `CURSO:{curso}:{estacao}:{bloco}` — o mesmo endereço do crédito de Spark |
| `contexto.tipo` | `"curso"` (ou `"curso_dominio"` na sondagem) |
| `contexto.prova_id` | `{curso}:{estacao}` — a estação é a atividade a que o item pertence |
| `contexto.origem` | `"curso_local"`: conteúdo do repositório, corrigido pelo servidor |
| `ontology_version` | `cursos-conteudo-1.0` — a versão do contrato contra o qual o item foi escrito |
| `item_schema_version` | a `versao` daquela estação: é ela que muda quando o texto é reescrito |
| `item_hash` | hash do bloco **sanitizado** (ver abaixo) |
| `resposta.*` | alternativa escolhida e acerto, os dois decididos pelo servidor |
| `desempenho.*` | tempo, número da tentativa, se mudou de resposta |

**O hash é do bloco sanitizado, e isso é deliberado.** `sanitizar_bloco`
remove gabarito, dica, feedback e solução — ou seja, o hash cobre exatamente
o que o aluno viu. Corrigir uma vírgula no feedback não muda o hash do item
que ele respondeu; mudar o enunciado, sim. É a definição útil de "a versão do
item que esta pessoa respondeu".

O que NÃO vem para cá, e onde está
----------------------------------
Nível de dificuldade, conceitos, trilha, tentativa, tempo por bloco e se o
acerto foi de primeira **não** são campos do BEH-1.1, e este módulo não os
inventa dentro dele. Eles já são gravados, com mais detalhe, em
`cursos_eventos` (Mongo, append-only, ver `cursos_progresso._evento`). Quem
for interpretar a trajetória tem as duas metades: o evento canônico para
cruzar com a prova, e o evento de curso para a pedagogia fina.

Nada aqui pode derrubar a resposta do aluno: falha de escrita é logada e
engolida, como em todo o resto da pilha.
"""
from __future__ import annotations

import asyncio
import logging

import cursos_conteudo as cc
import cursos_recompensa as cr

logger = logging.getLogger("sapiens.cursos.comportamento")

# A "ontologia" contra a qual um item de curso está anotado é o contrato de
# conteúdo que ele obedece. Mesmo padrão do Treino
# (`treino_habilidades.ONTOLOGY_VERSION_TREINO`): o campo é obrigatório desde
# a 1.1 e precisa dizer a verdade sobre a origem do item, não copiar a versão
# da ontologia cognitiva — que nunca anotou este item.
ONTOLOGY_VERSION_CURSOS = f"cursos-conteudo-{cc.SCHEMA_VERSION}"

CONTEXTO_ESTUDO = "curso"
CONTEXTO_DOMINIO = "curso_dominio"
ORIGEM = "curso_local"


async def registrar(
    uid: str,
    *,
    estacao: cc.Estacao,
    bloco: dict,
    acertou: bool,
    alternativa: str | None,
    tentativa: int,
    tempo_segundos: float | None = None,
    sondagem: bool = False,
) -> None:
    """Escreve o evento canônico desta resposta. Nunca levanta.

    Roda em thread porque o cliente do Firestore é síncrono — a rota é async e
    não pode bloquear o laço de eventos por uma escrita de rede.
    """
    try:
        import firestore_service as fs

        await asyncio.to_thread(
            fs.write_behavior_event,
            uid,
            item_id=cr.item_id(estacao.curso_id, estacao.estacao_id, bloco["bloco_id"]),
            ontology_version=ONTOLOGY_VERSION_CURSOS,
            alternativa_escolhida=alternativa,
            acertou=acertou,
            item_schema_version=estacao.versao,
            item_content=cc.sanitizar_bloco(bloco),
            contexto_tipo=CONTEXTO_DOMINIO if sondagem else CONTEXTO_ESTUDO,
            prova_id=f"{estacao.curso_id}:{estacao.estacao_id}",
            origem=ORIGEM,
            tempo_resposta_segundos=float(tempo_segundos or 0),
            numero_tentativas=max(1, int(tentativa)),
            # O produto não deixa trocar de alternativa antes de enviar: o
            # clique JÁ é o envio (ver `Blocos.jsx`). Declarado `False` em vez
            # de omitido porque o campo é obrigatório no contrato e "não sei"
            # e "não aconteceu" não são a mesma coisa.
            mudou_resposta=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Evento de behavior do exercício %s (%s) não gravado para %s.",
            bloco.get("bloco_id"), estacao.estacao_id, uid,
        )


def alternativa_registravel(bloco: dict, resposta) -> str | None:
    """O que vai em `resposta.alternativa_escolhida`.

    Múltipla escolha tem alternativa de verdade — é o id dela, e é o que
    permite descobrir depois qual distrator atrai mais gente. Numérico e texto
    curto não têm alternativa: mandar a digitação do aluno num campo que o
    contrato define como "identificador da alternativa selecionada" encheria
    o histórico de valores que não são identificador de nada. O que o aluno
    escreveu fica no evento de curso, onde o campo existe.
    """
    if bloco.get("formato") != "multipla_escolha":
        return None
    return str(resposta).strip() if resposta is not None else None
