"""Intervenção pedagógica — montagem local, sem IA.

De onde vem cada pedaço do plano que o aluno lê
-----------------------------------------------
1. **O nome da intervenção** vem do catálogo canônico (`INT-01`..`INT-11`).
   Não é reescrito aqui. O vínculo Erro→Intervenção também é do catálogo:
   este módulo nunca escolhe intervenção por semelhança de tema.
2. **A ação concreta** vem do próprio item que o aluno errou, no bloco
   `intervencoes[]` que o anotador escreveu para aquele item — com `gatilho`
   `{processo, erro}` casando com a RAIZ da cadeia do aluno. Esse bloco estava
   no banco desde a primeira sincronização e nenhuma tela lia.
3. **Os passos de resolução** vêm de `pedagogia.passos` do item, e só de itens
   que o aluno **já respondeu** — ver `_SEGURANCA` abaixo.
4. **O enquadramento** (`objetivo`, `como_praticar`, `sinal_de_progresso`) é
   texto autoral deste módulo, declaradamente **não normativo**: ele explica
   em linguagem cotidiana o que a intervenção catalogada quer treinar, e não
   define nada. Mesma disciplina de `feedback_templates`, que foi corrigido em
   2026-08-21 justamente por ter um mapa `ERR-NN → significado` divergente do
   catálogo. Aqui nenhum significado de `ERR-*`/`INT-*` é redefinido: se um ID
   novo entrar na ontologia, a ausência degrada para o nome do catálogo, nunca
   para uma descrição errada.

_SEGURANCA
----------
Resolução de questão é gabarito. `pedagogia` e a `explicacao` do distrator só
aparecem para itens que o aluno **já respondeu** — a sugestão de prática leva
apenas identificação (banca/ano/prova/número/tema), pela mesma razão que
`PROJECAO_SEM_GABARITO` existe no `server.py`.
"""
from __future__ import annotations

from typing import Any, Iterable

import annotation_service
from canonical_ontology import load_ontology

# Enquadramento autoral por intervenção catalogada. Chave = ID do catálogo;
# o `nome` NUNCA vem daqui (vem da ontologia) — só o texto de apoio.
_ENQUADRAMENTO: dict[str, dict[str, Any]] = {
    "INT-01": {
        "objetivo": "Voltar ao enunciado antes de calcular, para não responder a uma pergunta que não foi feita.",
        "como_praticar": [
            "Leia o enunciado uma vez inteiro, sem parar para pensar na resposta.",
            "Na segunda leitura, sublinhe só os dados explícitos: números, unidades, condições.",
            "Escreva com suas palavras, em uma frase, o que exatamente está sendo pedido.",
            "Só então olhe as alternativas — e confira se a sua frase bate com a que você escolheu.",
        ],
        "sinal_de_progresso": "Você passa a descartar alternativas por elas responderem a outra pergunta, não por 'parecerem estranhas'.",
    },
    "INT-02": {
        "objetivo": "Transformar a descrição em texto numa expressão formal, passo a passo, em vez de pular direto para a fórmula lembrada.",
        "como_praticar": [
            "Liste cada grandeza citada no enunciado com o símbolo e a unidade.",
            "Desenhe a situação, mesmo que toscamente — o desenho revela relação que a frase esconde.",
            "Escreva a relação entre as grandezas antes de substituir qualquer número.",
            "Só substitua valores depois que a expressão estiver montada.",
        ],
        "sinal_de_progresso": "A fórmula deixa de ser lembrada e passa a ser construída — e você percebe quando a lembrada não servia.",
    },
    "INT-03": {
        "objetivo": "Fixar a direção da relação: quando uma grandeza sobe, a outra sobe ou desce?",
        "como_praticar": [
            "Antes de montar a conta, responda em voz alta: se A dobrar, o que acontece com B?",
            "Teste com um número fácil (dobro, metade) e veja se o resultado tem a direção esperada.",
            "Escreva se é proporção direta ou inversa antes de escrever a expressão.",
            "No fim, confira se a resposta anda no sentido que você previu.",
        ],
        "sinal_de_progresso": "Você detecta sozinho a resposta absurda porque ela anda no sentido contrário ao previsto.",
    },
    "INT-04": {
        "objetivo": "Ler gráfico e tabela como se lê texto: eixo, unidade e escala antes do formato da curva.",
        "como_praticar": [
            "Leia primeiro os dois eixos: o que é medido e em que unidade.",
            "Confira a escala — ela começa em zero? é logarítmica? o intervalo é uniforme?",
            "Descreva o comportamento em uma frase antes de olhar as alternativas.",
            "Localize no gráfico o ponto exato que a pergunta pede, e leia o valor dele.",
        ],
        "sinal_de_progresso": "Você percebe manipulação de escala e para de confundir 'subiu muito' com 'subiu'.",
    },
    "INT-05": {
        "objetivo": "Separar se a conclusão é verdadeira de se ela decorre das premissas.",
        "como_praticar": [
            "Marque no texto o que é premissa e o que é conclusão.",
            "Pergunte: existe um caso em que as premissas valem e a conclusão falha?",
            "Se existir, o argumento é inválido — mesmo que a conclusão pareça certa.",
            "Desconfie de alternativa que você aceita porque concorda com ela.",
        ],
        "sinal_de_progresso": "Você rejeita conclusão verdadeira mal sustentada, e aceita conclusão desconfortável bem sustentada.",
    },
    "INT-06": {
        "objetivo": "Estimar a ordem de grandeza antes de calcular, para reconhecer resultado impossível.",
        "como_praticar": [
            "Arredonde tudo para uma potência de dez e faça a conta de cabeça.",
            "Anote a estimativa antes de fazer a conta exata.",
            "Compare: se a exata ficou 1000 vezes distante da estimativa, o erro está na conta.",
            "Cheque se o resultado é plausível no mundo real (massa, distância, tempo).",
        ],
        "sinal_de_progresso": "Alternativas com ordem de grandeza absurda caem antes de você calcular.",
    },
    "INT-07": {
        "objetivo": "Converter unidades e checar a dimensão antes de aceitar o número.",
        "como_praticar": [
            "Escreva a unidade ao lado de cada valor, sempre — inclusive nos passos intermediários.",
            "Converta tudo para o mesmo sistema antes de substituir.",
            "No fim, verifique se a unidade que sobrou é a unidade pedida.",
            "Se a unidade não fecha, a conta está errada mesmo que o número pareça bonito.",
        ],
        "sinal_de_progresso": "A unidade final vira sua conferência automática de resultado.",
    },
    "INT-08": {
        "objetivo": "Distinguir 'acontece junto' de 'causa', que é onde a maioria dos erros de interpretação nasce.",
        "como_praticar": [
            "Para cada relação afirmada, procure uma terceira causa que explique as duas coisas.",
            "Pergunte se a ordem no tempo está estabelecida ou apenas sugerida.",
            "Procure um contraexemplo: existe caso com a causa e sem o efeito?",
            "Cuidado com generalização: o que vale para a amostra vale para a população?",
        ],
        "sinal_de_progresso": "Você identifica a variável escondida sem que o enunciado a aponte.",
    },
    "INT-09": {
        "objetivo": "Só afirmar o que o texto sustenta — e saber apontar onde.",
        "como_praticar": [
            "Para cada alternativa, procure o trecho exato que a sustenta.",
            "Se não achar o trecho, a alternativa é inferência sua, não do texto.",
            "Desconfie de alternativa que 'faz sentido' mas não tem apoio textual.",
            "Marque a diferença entre o que o autor afirma e o que ele apenas cita.",
        ],
        "sinal_de_progresso": "Você consegue justificar a escolha citando a linha do texto.",
    },
    "INT-10": {
        "objetivo": "Identificar o que varia, o que é medido e o que precisa ficar constante.",
        "como_praticar": [
            "Nomeie a variável manipulada, a medida e as controladas.",
            "Pergunte o que o grupo de controle isola.",
            "Verifique se sobrou alguma diferença entre os grupos além da intencional.",
            "Se sobrou, a conclusão do experimento não se sustenta.",
        ],
        "sinal_de_progresso": "Você aponta a falha de desenho experimental antes de discutir o resultado.",
    },
    "INT-11": {
        "objetivo": "Classificar pelo critério que a questão define, não pela aparência.",
        "como_praticar": [
            "Escreva o critério de classificação antes de olhar os exemplos.",
            "Para cada caso, teste o critério explicitamente — sim ou não.",
            "Desconfie de agrupamento feito por semelhança visual ou de nome.",
            "Procure o caso limite: aquele que parece de um grupo e é de outro.",
        ],
        "sinal_de_progresso": "Você acerta os casos-limite, que são os que a prova costuma cobrar.",
    },
}

# Quando a raiz é sentinela (`erro-nao-catalogado-nesta-versao`), o catálogo
# não prescreve intervenção — e inventar uma seria exatamente o que o Error
# Trace §3 R-2 evita ao tornar a sentinela um valor de primeira classe.
_SEM_CATALOGO = {
    "objetivo": "Este tipo de erro ainda não tem intervenção catalogada nesta versão da ontologia.",
    "como_praticar": [
        "Refaça as questões abaixo prestando atenção no passo em que a sua resposta se separou da correta.",
        "Escreva, com suas palavras, qual decisão você tomou ali e por quê.",
    ],
    "sinal_de_progresso": "Você consegue nomear o ponto exato em que o raciocínio virou — que é o que falta para catalogar este erro.",
}


def _onto() -> dict:
    return load_ontology()


def _nome_intervencao(int_id: str | None) -> str | None:
    if not int_id:
        return None
    for i in _onto().get("intervencoes_pedagogicas") or []:
        if i.get("id") == int_id:
            return i.get("nome") or int_id
    return int_id


def _intervencao_do_erro(erro_id: str) -> str | None:
    for e in _onto().get("tipos_erro") or []:
        if e.get("id") == erro_id:
            return e.get("intervencao")
    return None


def previa(erro_id: str) -> dict[str, Any]:
    """O que o aluno lê ANTES de pagar: o enquadramento autoral já existente.

    Custa zero — nem IA, nem leitura. Existe para o botão de 10 Sparks ser uma
    escolha informada, e não uma caixa fechada: a prévia diz o objetivo, e o
    que se compra é o aprofundamento gerado pela Mentis.
    """
    int_id = _intervencao_do_erro(erro_id)
    enq = _ENQUADRAMENTO.get(int_id or "") or _SEM_CATALOGO
    return {
        "intervencao_id": int_id,
        "intervencao_nome": _nome_intervencao(int_id),
        "objetivo": enq["objetivo"],
        "como_praticar": list(enq["como_praticar"]),
        "sinal_de_progresso": enq["sinal_de_progresso"],
    }


def _acoes_dos_itens(tracos: list[dict], processo_id: str, erro_id: str) -> list[dict[str, Any]]:
    """A ação escrita pelo anotador PARA os itens que este aluno errou, quando
    o `gatilho` do bloco casa com a raiz da cadeia dele. É o que torna o plano
    concreto em vez de genérico — e não custa nada, já estava anotado."""
    index = annotation_service._build_item_index()
    saida: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for t in tracos:
        item = index.get(t.get("item_id") or "") or index.get(t.get("item_hash") or "")
        if not item:
            continue
        for bloco in item.get("intervencoes") or []:
            if not isinstance(bloco, dict):
                continue
            gatilho = bloco.get("gatilho") or {}
            if gatilho.get("processo") != processo_id or gatilho.get("erro") != erro_id:
                continue
            acao = (bloco.get("acao") or "").strip()
            if not acao or acao in vistos:
                continue
            vistos.add(acao)
            saida.append({"acao": acao, "intervencao_id": bloco.get("id"), "item": t.get("contexto_item")})
    return saida


def _resolucoes(tracos: list[dict]) -> list[dict[str, Any]]:
    """`pedagogia` dos itens que o aluno JÁ respondeu. Não é gabarito vazado:
    ele já respondeu, já viu o resultado. Ver `_SEGURANCA` no topo."""
    index = annotation_service._build_item_index()
    saida = []
    for t in tracos:
        item = index.get(t.get("item_id") or "") or index.get(t.get("item_hash") or "")
        ped = (item or {}).get("pedagogia") or {}
        passos = [p for p in (ped.get("passos") or []) if isinstance(p, str)]
        if not passos:
            continue
        saida.append(
            {
                "item": t.get("contexto_item"),
                "sua_alternativa": t.get("alternativa_escolhida"),
                "porque_engana": t.get("porque_essa_alternativa_engana"),
                "passos": passos,
                "erros_comuns": [e for e in (ped.get("erros_comuns") or []) if isinstance(e, str)],
            }
        )
    return saida


def sugerir_pratica(processo_id: str, itens_respondidos: Iterable[str], limite: int = 6) -> dict[str, Any]:
    """Questões do acervo que exercitam este processo e que o aluno ainda não
    respondeu. Só identificação — nenhuma anotação, nenhuma resolução,
    nenhum gabarito."""
    index = annotation_service._build_item_index()
    ja = set(itens_respondidos or [])
    vistos: set[str] = set()
    candidatos: list[dict[str, Any]] = []
    for item in index.values():
        item_id = item.get("item_id")
        if not item_id or item_id in ja or item_id in vistos:
            continue
        processos = (item.get("estrutura_cognitiva") or {}).get("processos") or []
        ids = {p.get("id") if isinstance(p, dict) else p for p in processos}
        if processo_id not in ids:
            continue
        vistos.add(item_id)
        fonte = item.get("fonte") or {}
        candidatos.append(
            {
                "item_id": item_id,
                "banca": fonte.get("banca"),
                "ano": fonte.get("ano"),
                "prova": fonte.get("prova"),
                "numero": fonte.get("numero"),
                "tema": fonte.get("tema"),
            }
        )
    candidatos.sort(key=lambda c: (-(c["ano"] or 0), c["numero"] or 0))
    return {"itens": candidatos[:limite], "total_disponivel": len(candidatos)}


def montar(*, processo_id: str, tracos: list[dict], itens_respondidos: Iterable[str]) -> dict[str, Any]:
    """O plano completo para uma habilidade clicada.

    `tracos` são os traços em que `processo_id` é a RAIZ (`ordem: 1`). Sem
    traço não há erro dominante, e o plano degrada para prática dirigida ao
    processo — nunca para uma intervenção escolhida por chute.
    """
    pratica = sugerir_pratica(processo_id, itens_respondidos)
    if not tracos:
        return {
            "origem": "sem_traco",
            "intervencao_id": None,
            "intervencao_nome": None,
            "erro_raiz": None,
            **_SEM_CATALOGO,
            "acoes_do_seu_historico": [],
            "resolucoes_do_seu_historico": [],
            "praticar": pratica,
        }

    pesos: dict[str, float] = {}
    for t in tracos:
        raiz = t["cadeia"][0]
        pesos[raiz["erro"]] = pesos.get(raiz["erro"], 0.0) + raiz["confianca"]
    erro_id = max(pesos.items(), key=lambda kv: kv[1])[0]

    int_id = _intervencao_do_erro(erro_id)
    enquadramento = _ENQUADRAMENTO.get(int_id or "") or _SEM_CATALOGO
    return {
        "origem": "error_trace",
        "intervencao_id": int_id,
        "intervencao_nome": _nome_intervencao(int_id),
        "erro_raiz": {"id": erro_id, "peso": round(pesos[erro_id], 3)},
        "objetivo": enquadramento["objetivo"],
        "como_praticar": list(enquadramento["como_praticar"]),
        "sinal_de_progresso": enquadramento["sinal_de_progresso"],
        "acoes_do_seu_historico": _acoes_dos_itens(tracos, processo_id, erro_id),
        "resolucoes_do_seu_historico": _resolucoes(tracos),
        "praticar": pratica,
    }
