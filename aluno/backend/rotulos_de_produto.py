"""Rótulos de PRODUTO para os pontos fracos — o que o aluno lê no lugar dos
nomes reais da ontologia.

A regra é inviolável (`Cerebro/regras/inviolaveis.md`): **os nomes reais da
ontologia nunca aparecem para o aluno; são a IP do produto.** Até 2026-10-06
ela valia para o mapa de habilidades (`components/mapa3d/missoes.js`) e para
mais nada: `processo_nome` e `erro_nome` chegavam crus ao Próximo Passo, ao
cabeçalho da prática dirigida, à fila de revisão, à trajetória, ao chat da
Mentis e à venda da live — e, mesmo onde a tela não desenhava o nome, ele
viajava no JSON, legível na aba Rede de qualquer navegador.

Por isso a troca acontece AQUI, na fronteira do servidor (`vestir`), e não só
na tela: as rotas do aluno passam a resposta por este módulo antes de sair. As
rotas de admin e de curadoria continuam com o nome real — é com ele que a
equipe trabalha.

O espelho no frontend é `aluno/frontend/src/lib/rotulosDoMotor.js` (no molde
de `missoes.js`), para as telas que só têm o `id` na mão. Os dois mapas são o
MESMO mapa: `tests/test_rotulos_de_produto.py` lê o arquivo JS e quebra se um
divergir do outro.

O pipeline e a ontologia continuam congelados: nada aqui muda id, catálogo ou
contrato. É só a camada de apresentação.

Os rótulos foram escolhidos em 2026-10-06 (decisão de quem implementou, não do
dono): curtos, na língua de quem estuda, e nenhum igual ao nome do catálogo.
Mudar um rótulo é mudar UMA linha aqui e a mesma linha no JS.
"""
from __future__ import annotations

import copy
import re
import unicodedata
from typing import Any

PROCESSOS: dict[str, str] = {
    "PROC-QUANT-01": "Ordem e comparação",
    "PROC-QUANT-02": "Proporção",
    "PROC-QUANT-03": "Estimativa",
    "PROC-QUANT-04": "Unidades e escala",
    "PROC-ESPACO-01": "Leitura de figuras",
    "PROC-ESPACO-02": "Áreas e volumes",
    "PROC-ESPACO-03": "Forma e função",
    "PROC-MUD-01": "Taxas de variação",
    "PROC-MUD-02": "O que se conserva",
    "PROC-INC-01": "Chance com condição",
    "PROC-INC-02": "Médias",
    "PROC-INC-03": "Espalhamento dos dados",
    "PROC-INC-04": "Contagem de chances",
    "PROC-CAUSAL-01": "Cadeias de causa",
    "PROC-LOGICO-01": "Lógica dos argumentos",
    "PROC-SIMB-01": "Montar a equação",
    "PROC-SIMB-02": "Ler fórmulas",
    "PROC-TEXT-01": "Achar o dado",
    "PROC-TEXT-02": "Ler nas entrelinhas",
    "PROC-TEXT-03": "Cruzar fontes",
    "PROC-EXP-01": "Hipóteses",
    "PROC-EXP-02": "Variáveis do experimento",
    "PROC-SIST-01": "Reação do sistema",
    "PROC-SIST-02": "Fluxos e ciclos",
    "PROC-CLASSIF-01": "Agrupar por critério",
}

ERROS: dict[str, str] = {
    "ERR-01": "Dado que passou batido",
    "ERR-02": "Ir além do texto",
    "ERR-03": "Conta que não é a da situação",
    "ERR-04": "Unidade trocada",
    "ERR-05": "Proporção invertida",
    "ERR-06": "Ponto errado no gráfico",
    "ERR-07": "Coincidência vista como causa",
    "ERR-08": "Conclusão grande demais",
    "ERR-09": "Variável esquecida",
    "ERR-10": "Símbolo mal lido",
    "ERR-11": "Número fora de escala",
    "ERR-12": "Argumento que não fecha",
    "ERR-13": "Critério de aparência",
    # Os dois sentinelas do motor (`motor_cognitivo.SENTINELAS`): erro real,
    # sem nome no catálogo desta versão.
    "erro-nao-catalogado-nesta-versao": "Padrão ainda sem nome",
    "sem-mecanismo-cognitivo-identificavel": "Padrão ainda sem nome",
}

# As intervenções (`INT-*`) aparecem ao lado do erro — "Abordagem catalogada:
# …" — e são nome de catálogo do mesmo jeito.
INTERVENCOES: dict[str, str] = {
    "INT-01": "Reler com roteiro",
    "INT-02": "Do texto ao esquema",
    "INT-03": "Treino de proporção",
    "INT-04": "Leitura atenta de gráficos",
    "INT-05": "Desmontar argumentos",
    "INT-06": "Treino de estimativa",
    "INT-07": "Conferir unidades",
    "INT-08": "Causa ou coincidência",
    "INT-09": "Provar pelo texto",
    "INT-10": "Montar o experimento",
    "INT-11": "Classificar pelo que importa",
}

PROCESSO_DESCONHECIDO = "Ponto de atenção"
ERRO_DESCONHECIDO = "Padrão de erro"


def rotulo_do_processo(pid: Any) -> str:
    return PROCESSOS.get(pid) if isinstance(pid, str) and pid in PROCESSOS else PROCESSO_DESCONHECIDO


def rotulo_do_erro(eid: Any) -> str:
    return ERROS.get(eid) if isinstance(eid, str) and eid in ERROS else ERRO_DESCONHECIDO


def rotulo_da_intervencao(iid: Any) -> str | None:
    return INTERVENCOES.get(iid) if isinstance(iid, str) else None


# ---------------------------------------------------------------------------
# A troca nos textos livres
# ---------------------------------------------------------------------------
# Campo estruturado é trocado pelo id (abaixo). Mas há frase montada no
# servidor com o nome dentro ("O ponto onde você mais escorrega é …"), e o
# nome real pode estar em qualquer string. A rede de segurança: todo nome do
# catálogo (processo, erro, intervenção, competência e domínio que coincidem
# com eles) é procurado em toda string da resposta, sem diferença de caixa
# nem de acento, e trocado pelo rótulo.

def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


_PADROES: list[tuple[re.Pattern, str]] | None = None


def _padroes() -> list[tuple[re.Pattern, str]]:
    global _PADROES
    if _PADROES is not None:
        return _PADROES
    import motor_cognitivo

    cat = motor_cognitivo._catalogo()
    pares: dict[str, str] = {}
    for pid, p in (cat.get("processos") or {}).items():
        if p.get("nome"):
            pares[p["nome"]] = rotulo_do_processo(pid)
    for eid, e in (cat.get("erros") or {}).items():
        if e.get("nome"):
            pares[e["nome"]] = rotulo_do_erro(eid)
    for iid, i in (cat.get("intervencoes") or {}).items():
        if i.get("nome") and iid in INTERVENCOES:
            pares[i["nome"]] = INTERVENCOES[iid]
    padroes = []
    # O mais longo primeiro: "Relacionar estrutura a funcao" não pode ser
    # comido por um nome menor contido nele.
    for nome in sorted(pares, key=len, reverse=True):
        # Casa a forma com e sem acento ("Inferencia"/"Inferência"): o catálogo
        # está sem acento, e um texto escrito por gente (ou pelo modelo) não.
        letras = []
        for ch in _sem_acento(nome):
            variantes = _ACENTUADAS.get(ch.lower(), "")
            if variantes:
                letras.append(f"[{re.escape(ch.lower())}{variantes}]")
            elif ch.isspace():
                letras.append(r"\s+")
            else:
                letras.append(re.escape(ch))
        padroes.append((re.compile("".join(letras), re.IGNORECASE), pares[nome]))
    _PADROES = padroes
    return padroes


_ACENTUADAS = {
    "a": "áàâãä", "e": "éèêë", "i": "íìîï", "o": "óòôõö", "u": "úùûü", "c": "ç",
}


def trocar_no_texto(texto: str) -> str:
    if not texto or not isinstance(texto, str):
        return texto
    for padrao, rotulo in _padroes():
        texto = padrao.sub(rotulo, texto)
    return texto


# ---------------------------------------------------------------------------
# A fronteira
# ---------------------------------------------------------------------------

def _id_de_erro(d: dict) -> Any:
    for chave in ("erro_id", "erro"):
        if isinstance(d.get(chave), str):
            return d[chave]
    dominante = d.get("erro_dominante")
    if isinstance(dominante, str):
        return dominante
    if isinstance(dominante, dict):
        return dominante.get("id")
    return None


def _id_de_processo(d: dict) -> Any:
    for chave in ("processo_id", "processo_afetado"):
        if isinstance(d.get(chave), str):
            return d[chave]
    if isinstance(d.get("processo"), str):
        return d["processo"]
    return None


def _vestir_dict(d: dict) -> dict:
    for k, v in list(d.items()):
        d[k] = _vestir(v)
    if "processo_nome" in d:
        d["processo_nome"] = rotulo_do_processo(_id_de_processo(d))
    if "erro_nome" in d and d["erro_nome"] is not None:
        d["erro_nome"] = rotulo_do_erro(_id_de_erro(d))
    if "intervencao_nome" in d and d["intervencao_nome"] is not None:
        d["intervencao_nome"] = rotulo_da_intervencao(d.get("intervencao_id")) or trocar_no_texto(d["intervencao_nome"])
    ident = d.get("id")
    if isinstance(ident, str) and "nome" in d:
        if ident in PROCESSOS or ident.startswith("PROC-"):
            d["nome"] = rotulo_do_processo(ident)
        elif ident in ERROS or ident.startswith("ERR-"):
            d["nome"] = rotulo_do_erro(ident)
        elif ident in INTERVENCOES:
            d["nome"] = INTERVENCOES[ident]
    return d


def _vestir(valor: Any) -> Any:
    if isinstance(valor, dict):
        return _vestir_dict(valor)
    if isinstance(valor, list):
        return [_vestir(v) for v in valor]
    if isinstance(valor, tuple):
        return tuple(_vestir(v) for v in valor)
    if isinstance(valor, str):
        return trocar_no_texto(valor)
    return valor


def vestir(resposta: Any) -> Any:
    """A resposta de uma rota DO ALUNO, com rótulo de produto no lugar de
    todo nome da ontologia. Devolve uma cópia: o objeto original pode estar
    num cache de processo (`motor_cognitivo._HISTORICO_MEMO`) que o admin
    também lê."""
    return _vestir(copy.deepcopy(resposta))
