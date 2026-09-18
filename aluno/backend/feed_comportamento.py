"""Uma resposta do feed vira um evento do MESMO contrato de behavior do ENEM.

Mesma decisão que `cursos_comportamento.py` já tomou, pela mesma razão: o
Sapiens tem UM registro comportamental — o contrato **BEH-1.1**
(`pipeline/docs/behavior/07 behavior student 1.4.md`), escrito por
`firestore_service.write_behavior_event` em `students/{uid}/behavior`. É dele
que a Mentis e o painel de eventos (`events_routes.py`) já leem. O feed **não
ganha um histórico paralelo** — ganhar um seria a maneira mais eficiente de
tornar impossível a pergunta que justifica o registro existir: *este aluno
erra o mesmo tipo de coisa na prova, no curso e no feed?*

`feed_routes.py` continua gravando `feed_interactions`/`feed_progress` em
Mongo — isso é ESTADO DE PRODUTO (o que mostrar quando o aluno volta, quanto
tempo passou neste card specific), não claim cognitivo, e seria perda de
informação jogá-lo fora. Este módulo cobre só a outra metade: o evento
CANÔNICO que entra na mesma régua da prova e do curso.

Onde o feed cabe no contrato, campo a campo
--------------------------------------------
| campo canônico | o que o feed põe nele |
|---|---|
| `item_id` | `FEED:{content_id}` |
| `contexto.tipo` | `"feed"` |
| `contexto.origem` | `"feed_local"` |
| `ontology_version` | `feed-conteudo-{SCHEMA_VERSION}` |
| `item_hash` | hash do card como ele foi SERVIDO (`feed_conteudo.para_a_tela`) |
| `resposta.*` | a alternativa/resposta e o acerto, decididos por `feed_conteudo.corrigir` |

Card de leitura pura (Insight, Conceito, Lista) e enquete não têm gabarito —
`acertou` vai `None`, e o contrato aceita isso (é a mesma convenção que
material sem correção já usa). Autoavaliação (Flashcard, Revisão) grava o
julgamento do próprio aluno em `resposta.acertou`: é dado real sobre o que ele
diz lembrar, não uma correção — e por isso `alternativa_escolhida` fica vazio,
não fabricamos uma alternativa que não existiu.

Nada aqui pode derrubar a resposta do aluno: falha de escrita é logada e
engolida, como em todo o resto da pilha.
"""
from __future__ import annotations

import asyncio
import logging

import feed_ingestao as fi

logger = logging.getLogger("sapiens.feed.comportamento")

ONTOLOGY_VERSION_FEED = f"feed-conteudo-{fi.SCHEMA_VERSION}"
CONTEXTO = "feed"
ORIGEM = "feed_local"


def item_id(content_id: str) -> str:
    return f"FEED:{content_id}"


async def registrar(
    uid: str,
    *,
    card: dict,
    card_na_tela: dict,
    acertou: bool | None,
    alternativa: str | None,
    tempo_segundos: float | None = None,
) -> None:
    """Escreve o evento canônico desta interação. Nunca levanta.

    `card_na_tela` é o que o aluno efetivamente viu (`para_a_tela`, sem
    gabarito) — é ELE que vira `item_hash`, pela mesma razão que
    `cursos_comportamento` faz hash do bloco sanitizado: corrigir o gabarito
    ou o feedback no texto-fonte não pode reescrever, em silêncio, a versão do
    item que esta pessoa respondeu.

    `acertou=None` (leitura, enquete sem resposta ainda) não grava nada — não
    virou uma resposta, e um evento sem resposta seria ruído na história.
    """
    if acertou is None:
        return
    try:
        import firestore_service as fs

        await asyncio.to_thread(
            fs.write_behavior_event,
            uid,
            item_id=item_id(card["content_id"]),
            ontology_version=ONTOLOGY_VERSION_FEED,
            alternativa_escolhida=alternativa,
            acertou=acertou,
            item_schema_version=fi.SCHEMA_VERSION,
            item_content=card_na_tela,
            contexto_tipo=CONTEXTO,
            prova_id=card["content_id"],
            origem=ORIGEM,
            tempo_resposta_segundos=float(tempo_segundos or 0),
            numero_tentativas=1,
            # O feed não deixa responder de novo depois de revelado (mesma
            # regra do curso): o clique JÁ é o envio.
            mudou_resposta=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Evento de behavior do card de feed %s não gravado para %s.",
            card.get("content_id"), uid,
        )
