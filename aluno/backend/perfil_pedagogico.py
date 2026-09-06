"""Camada pedagógica derivada — a única forma como o desempenho cognitivo do
aluno pode ser exposta ao cliente.

Domínio, competência, processo cognitivo, habilidade observável, tipo de
erro e intervenção pedagógica são propriedade intelectual do produto
(catálogo em `pipeline/docs/ontology/ontology_v1.4.json`) e nunca devem
chegar ao aluno como nome, ID, categoria ou percentual — nem em campo de
resposta de API que o cliente só usa como parâmetro opaco. Este módulo é a
fronteira: lê o dado real de `annotation_service.compute_diagnostico_real`
(engenharia interna, intocada) e devolve só `rotulo` + `explicacao`, escritos
à mão para cada processo cognitivo, nunca derivados automaticamente do nome
interno.

Granularidade: PROCESSO (25 no catálogo vigente), por ser o nível mais fino
que `compute_diagnostico_real` já rankeia com nome e definição operacional
claros. Chave de processo ausente do glossário é erro de programação — se a
ontologia ganhar um processo novo, isto tem que ser atualizado à mão, nunca
cair num rótulo genérico.
"""
from __future__ import annotations

from typing import Any

import annotation_service

TOPO_N = 5

# rotulo: título curto, linguagem de aluno, nunca o nome do catálogo.
# descricao_forte / descricao_fraca: frase pronta, usada quando não há
# evidência mais específica disponível (ver `_explicacao_fraca`).
GLOSSARIO_PROCESSO: dict[str, dict[str, str]] = {
    "PROC-QUANT-01": {
        "rotulo": "Comparar valores e ordená-los",
        "descricao_forte": "Você compara números e grandezas com segurança e coloca as coisas na ordem certa sem hesitar.",
        "descricao_fraca": "Comparar e ordenar valores ou medidas ainda exige mais atenção — vale praticar colocar números em ordem crescente ou decrescente.",
    },
    "PROC-QUANT-02": {
        "rotulo": "Raciocínio proporcional",
        "descricao_forte": "Você entende bem como duas grandezas crescem ou diminuem juntas, na mesma proporção ou de forma inversa.",
        "descricao_fraca": "Relacionar duas grandezas que variam juntas, na mesma proporção ou de forma inversa, ainda é um ponto a fortalecer.",
    },
    "PROC-QUANT-03": {
        "rotulo": "Estimar valores com bom senso",
        "descricao_forte": "Você consegue chegar a um valor aproximado plausível mesmo sem fazer a conta exata.",
        "descricao_fraca": "Estimar um valor aproximado a partir de pistas do contexto, sem calcular tudo exatamente, ainda é uma habilidade a desenvolver.",
    },
    "PROC-QUANT-04": {
        "rotulo": "Converter unidades e escalas",
        "descricao_forte": "Você transita bem entre unidades diferentes e percebe quando uma conta não bate em termos de escala.",
        "descricao_fraca": "Trocar entre unidades de medida e perceber se uma expressão faz sentido em termos de escala ainda merece atenção.",
    },
    "PROC-ESPACO-01": {
        "rotulo": "Ler figuras geométricas",
        "descricao_forte": "Você extrai bem medidas e relações (lados, ângulos, semelhança) a partir de uma figura geométrica.",
        "descricao_fraca": "Tirar informações métricas de uma figura geométrica, como lados, ângulos ou semelhança, ainda é um desafio.",
    },
    "PROC-ESPACO-02": {
        "rotulo": "Somar partes para achar o todo",
        "descricao_forte": "Você quebra uma forma complexa em pedaços conhecidos e soma tudo certinho para achar área ou volume.",
        "descricao_fraca": "Decompor uma forma complexa em partes conhecidas para calcular área ou volume total ainda precisa de prática.",
    },
    "PROC-ESPACO-03": {
        "rotulo": "Ligar estrutura à função",
        "descricao_forte": "Você entende bem por que uma parte de um sistema tem o formato ou a posição que tem, ligando isso ao papel que ela cumpre.",
        "descricao_fraca": "Relacionar a forma ou a posição de uma parte de um sistema ao papel que ela exerce ainda é um ponto de atenção.",
    },
    "PROC-MUD-01": {
        "rotulo": "Acompanhar variações",
        "descricao_forte": "Você percebe bem como a variação de uma grandeza se relaciona à variação de outra, ao longo de um processo.",
        "descricao_fraca": "Perceber como a variação de uma grandeza afeta outra, ao longo de um processo, ainda é algo a fortalecer.",
    },
    "PROC-MUD-02": {
        "rotulo": "Reconhecer o que se conserva",
        "descricao_forte": "Você identifica bem o que permanece constante, como massa ou energia, antes e depois de uma transformação.",
        "descricao_fraca": "Reconhecer o que se mantém constante durante uma transformação, como massa ou energia, ainda precisa de reforço.",
    },
    "PROC-INC-01": {
        "rotulo": "Probabilidade condicional",
        "descricao_forte": "Você entende bem como a ocorrência de um evento muda a chance de outro acontecer.",
        "descricao_fraca": "Entender como a ocorrência de um evento altera a probabilidade de outro ainda é um ponto a desenvolver.",
    },
    "PROC-INC-02": {
        "rotulo": "Resumir dados num só número",
        "descricao_forte": "Você resume bem um conjunto de dados usando média, mediana ou moda.",
        "descricao_fraca": "Resumir um conjunto de dados com um valor representativo, como média, mediana ou moda, ainda merece prática.",
    },
    "PROC-INC-03": {
        "rotulo": "Avaliar o quanto os dados variam",
        "descricao_forte": "Você avalia bem o quanto os dados de um conjunto variam entre si.",
        "descricao_fraca": "Avaliar a variabilidade de um conjunto de dados, como amplitude ou dispersão, ainda é um desafio.",
    },
    "PROC-INC-04": {
        "rotulo": "Prever proporções em sorteios e combinações",
        "descricao_forte": "Você prevê bem proporções esperadas em processos de sorteio ou combinação.",
        "descricao_fraca": "Prever a proporção esperada de resultados num processo de sorteio ou combinação ainda precisa de prática.",
    },
    "PROC-CAUSAL-01": {
        "rotulo": "Enxergar causa e efeito",
        "descricao_forte": "Você identifica bem a relação de causa e efeito entre um evento e sua consequência.",
        "descricao_fraca": "Identificar com segurança o que é causa e o que é consequência de um fenômeno ainda é um ponto a desenvolver.",
    },
    "PROC-LOGICO-01": {
        "rotulo": "Avaliar a lógica de um argumento",
        "descricao_forte": "Você julga bem se uma conclusão realmente decorre das premissas de um argumento, independentemente de concordar com ele.",
        "descricao_fraca": "Julgar se uma conclusão realmente decorre logicamente das premissas de um argumento ainda merece atenção.",
    },
    "PROC-SIMB-01": {
        "rotulo": "Traduzir situações em fórmulas",
        "descricao_forte": "Você converte bem uma situação descrita em palavras para uma equação ou expressão.",
        "descricao_fraca": "Converter uma situação descrita em palavras para uma equação, fórmula ou modelo ainda é um desafio.",
    },
    "PROC-SIMB-02": {
        "rotulo": "Ler símbolos e fórmulas",
        "descricao_forte": "Você lê bem símbolos, coeficientes e unidades dentro de uma expressão já pronta.",
        "descricao_fraca": "Ler corretamente os símbolos, coeficientes e unidades de uma expressão formal já pronta ainda precisa de reforço.",
    },
    "PROC-TEXT-01": {
        "rotulo": "Localizar informação explícita",
        "descricao_forte": "Você encontra rápido um dado que está escrito literalmente no texto, tabela ou gráfico.",
        "descricao_fraca": "Localizar um dado escrito literalmente no enunciado, tabela ou gráfico ainda merece atenção.",
    },
    "PROC-TEXT-02": {
        "rotulo": "Ler nas entrelinhas",
        "descricao_forte": "Você deduz bem informações que não estão escritas de forma literal, a partir de pistas do texto.",
        "descricao_fraca": "Deduzir uma informação que não está escrita literalmente, a partir de pistas do texto ou da imagem, ainda é um ponto a desenvolver.",
    },
    "PROC-TEXT-03": {
        "rotulo": "Juntar informações de fontes diferentes",
        "descricao_forte": "Você combina bem texto, tabela e imagem numa única conclusão.",
        "descricao_fraca": "Combinar informações de texto, tabela e imagem numa única conclusão ainda precisa de prática.",
    },
    "PROC-EXP-01": {
        "rotulo": "Formular hipóteses testáveis",
        "descricao_forte": "Você propõe bem explicações que dá para testar a partir de uma observação.",
        "descricao_fraca": "Propor uma explicação que realmente dá para testar, a partir do que foi observado, ainda é um desafio.",
    },
    "PROC-EXP-02": {
        "rotulo": "Controlar variáveis de um experimento",
        "descricao_forte": "Você identifica e isola bem as variáveis de um experimento: o que muda, o que é medido e o que fica fixo.",
        "descricao_fraca": "Identificar e isolar as variáveis de um experimento, o que muda, o que é medido e o que fica fixo, ainda precisa de reforço.",
    },
    "PROC-SIST-01": {
        "rotulo": "Prever a reação de um sistema",
        "descricao_forte": "Você prevê bem para que lado um sistema se ajusta depois de sofrer uma alteração.",
        "descricao_fraca": "Prever a direção em que um sistema se ajusta depois de sofrer uma alteração ainda é um ponto a desenvolver.",
    },
    "PROC-SIST-02": {
        "rotulo": "Mapear fluxos entre partes de um sistema",
        "descricao_forte": "Você relaciona bem como matéria, energia ou informação circulam entre as partes de um sistema.",
        "descricao_fraca": "Relacionar como matéria, energia ou informação circula entre partes interdependentes de um sistema ainda merece atenção.",
    },
    "PROC-CLASSIF-01": {
        "rotulo": "Classificar por critério",
        "descricao_forte": "Você agrupa bem elementos numa categoria a partir de uma característica em comum.",
        "descricao_fraca": "Agrupar elementos numa categoria a partir de uma característica declarada ainda precisa de prática.",
    },
}


def _explicacao_fraca(processo_id: str, padroes_por_processo: dict[str, dict[str, Any]]) -> str:
    """Prefere a evidência observável específica do aluno (já em linguagem
    livre, sem jargão) quando existir; senão cai na descrição genérica do
    glossário. Nunca usa `erro_nome`/`intervencao_nome` — são categorias
    internas."""
    padrao = padroes_por_processo.get(processo_id)
    if padrao and padrao.get("erro_evidencia_observavel"):
        return padrao["erro_evidencia_observavel"]
    return GLOSSARIO_PROCESSO[processo_id]["descricao_fraca"]


async def perfil_publico(user_id: str) -> dict[str, Any]:
    """`{"pontos_fortes": [...], "pontos_a_desenvolver": [...],
    "amostra_insuficiente": bool}` — nenhum campo carrega id, nome interno
    ou percentual. Cada item é `{"rotulo", "explicacao"}`."""
    diagnostico = await annotation_service.compute_diagnostico_real(user_id)
    por_processo = diagnostico.get("por_processo") or {"fortes": [], "fracos": []}
    fortes = (por_processo.get("fortes") or [])[:TOPO_N]
    fracos = (por_processo.get("fracos") or [])[:TOPO_N]
    padroes_por_processo = {
        p["processo_id"]: p for p in (diagnostico.get("padroes_associados") or [])
    }

    pontos_fortes = [
        {"rotulo": GLOSSARIO_PROCESSO[item["id"]]["rotulo"],
         "explicacao": GLOSSARIO_PROCESSO[item["id"]]["descricao_forte"]}
        for item in fortes
    ]
    pontos_a_desenvolver = [
        {"rotulo": GLOSSARIO_PROCESSO[item["id"]]["rotulo"],
         "explicacao": _explicacao_fraca(item["id"], padroes_por_processo)}
        for item in fracos
    ]

    return {
        "pontos_fortes": pontos_fortes,
        "pontos_a_desenvolver": pontos_a_desenvolver,
        "amostra_insuficiente": not fortes and not fracos,
    }
