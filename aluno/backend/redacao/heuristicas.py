"""Nível 1-2 — heurísticas locais e extração de evidência determinística.

Nenhuma função aqui decide um veredito final: cada uma devolve uma
`decision_gate.Evidencia`, sempre passada ao Decision Gate depois (em
`avaliador_local.py`). Sem chamada de rede, sem LLM.

**Assimetria de segurança** para os gatilhos de zero-redação-inteira e o
localizado (`DH-ZERO-01`): uma heurística local pode confirmar "não
disparou" com suporte forte (o custo de errar nessa direção é baixo — só
significa que o item vai para confirmação por LLM em vez de ser descartado
de graça), mas nunca propõe "disparou" com suporte acima de
`_TETO_SUPORTE_GATILHO_POSITIVO` (abaixo do `suporte_minimo_forte` padrão do
Decision Gate) — então nunca vira `DETERMINADO` sozinha nessa direção. Zerar
uma redação inteira (ou a Competência V, no caso de `DH-ZERO-01`) por engano
de uma heurística seria um erro caro demais para decidir sem confirmação.

Para as 5 competências não há essa assimetria (o custo de um nível estimado
errado é bem menor que zerar a prova inteira), mas cada heurística ainda
assim só propõe suporte forte nos extremos claros — a zona intermediária
(onde a diferença entre "bom" e "mediano" é qualitativa, não numérica) fica
deliberadamente com suporte fraco, forçando `AMBIGUO` e escalonamento em vez
de uma estimativa numérica inventada.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from decision_gate import Evidencia
from redacao.tipos import RedacaoEntrada

_TETO_SUPORTE_GATILHO_POSITIVO = 0.5  # sempre < suporte_minimo_forte padrão (1.0)


def _tokens(texto: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", (texto or "").lower(), flags=re.UNICODE)


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _paragrafos(texto: str) -> list[str]:
    partes = re.split(r"\n\s*\n", (texto or "").strip())
    return [p.strip() for p in partes if p.strip()]


def _frases(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?])\s+", (texto or "").strip())
    return [p.strip() for p in partes if p.strip()]


def _evidencia_gatilho(
    criterio_id: str, disparado: bool, suporte_limpo: float,
    *, evidencias_presentes: Iterable[str] = (), evidencias_ausentes: Iterable[str] = (),
) -> Evidencia:
    """Aplica a assimetria de segurança descrita no docstring do módulo."""
    suporte = suporte_limpo if not disparado else min(suporte_limpo, _TETO_SUPORTE_GATILHO_POSITIVO)
    return Evidencia(
        criterio_id, "heuristica_local", [(disparado, suporte)],
        list(evidencias_presentes), list(evidencias_ausentes),
    )


# ------------------------------------------------------------------- tema

def _cobertura_tematica(entrada: RedacaoEntrada) -> tuple[int, int, list[str]]:
    elementos = entrada.tema_elementos_obrigatorios or []
    if not elementos:
        return 0, 0, []
    texto_norm = _sem_acento((entrada.texto or "").lower())
    encontrados = [e for e in elementos if _sem_acento(e.lower().strip()) in texto_norm]
    return len(encontrados), len(elementos), encontrados


def checar_fuga_tema(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-01 — fuga total ao tema (nem o assunto amplo nem o recorte específico)."""
    if not entrada.tema_elementos_obrigatorios:
        return Evidencia("ZERO-01", "heuristica_local",
                          qualidade_entrada="tema_elementos_obrigatorios não informado")
    encontrados, total, presentes = _cobertura_tematica(entrada)
    cobertura = encontrados / total
    if cobertura >= 0.75:
        return _evidencia_gatilho("ZERO-01", False, 2.0, evidencias_presentes=presentes)
    ausentes = [e for e in entrada.tema_elementos_obrigatorios if e not in presentes]
    return _evidencia_gatilho("ZERO-01", cobertura == 0, 0.5,
                               evidencias_presentes=presentes, evidencias_ausentes=ausentes)


def checar_tangenciamento(entrada: RedacaoEntrada) -> Evidencia:
    """TEMA-02 — aborda só o assunto amplo, sem o recorte específico."""
    if not entrada.tema_elementos_obrigatorios:
        return Evidencia("TEMA-02", "heuristica_local",
                          qualidade_entrada="tema_elementos_obrigatorios não informado")
    encontrados, total, presentes = _cobertura_tematica(entrada)
    cobertura = encontrados / total
    if cobertura >= 0.75:
        return _evidencia_gatilho("TEMA-02", False, 2.0, evidencias_presentes=presentes)
    if cobertura == 0:
        # cobertura zero é candidato a ZERO-01 (fuga total), não a tangenciamento
        # (que pressupõe abordar ao menos o assunto amplo) — não propõe candidato aqui.
        return Evidencia("TEMA-02", "heuristica_local",
                          qualidade_entrada="cobertura temática zero — ver ZERO-01, não tangenciamento")
    ausentes = [e for e in entrada.tema_elementos_obrigatorios if e not in presentes]
    return _evidencia_gatilho("TEMA-02", 0 < cobertura < 0.75, 0.5,
                               evidencias_presentes=presentes, evidencias_ausentes=ausentes)


# ------------------------------------------------------------ tipo textual

_MARCADORES_ARGUMENTATIVOS = [
    "portanto", "contudo", "todavia", "entretanto", "ademais", "outrossim",
    "porquanto", "assim", "logo", "porem", "porque", "pois", "visto que",
    "dessa forma", "desse modo", "diante disso", "nesse sentido",
    "por conseguinte", "alem disso", "em vista disso", "sob essa otica",
]
_MARCADORES_NARRATIVOS = [
    "era uma vez", "certo dia", "de repente", "quando eu", "hoje eu",
    "lembro-me", "lembro me", "disse ele", "disse ela", "gritou", "sussurrou",
]


def checar_tipo_dissertativo_argumentativo(entrada: RedacaoEntrada) -> Evidencia:
    """Sinal único para `ZERO-02` (não atendimento ao tipo dissertativo-
    argumentativo) e `ZERO-10` (predominância de outro tipo textual) —
    nenhum método local distingue as duas leituras; `avaliador_local.py`
    aplica esta MESMA evidência a ambos os `criterio_id`, documentado ali.
    """
    texto_norm = _sem_acento((entrada.texto or "").lower())
    frases = _frases(entrada.texto or "")
    if len(frases) < 3:
        return Evidencia("TIPO-TEXTUAL", "heuristica_local",
                          qualidade_entrada="texto curto demais para avaliar tipo textual")
    hits_arg = sum(1 for m in _MARCADORES_ARGUMENTATIVOS if m in texto_norm)
    hits_narr = sum(1 for m in _MARCADORES_NARRATIVOS if m in texto_norm)
    densidade_arg = hits_arg / max(1, len(frases))
    if densidade_arg >= 0.15 and hits_narr == 0:
        return _evidencia_gatilho("TIPO-TEXTUAL", False, 2.0,
                                   evidencias_presentes=[f"{hits_arg} marcadores argumentativos"])
    return _evidencia_gatilho(
        "TIPO-TEXTUAL", hits_narr >= 2 or densidade_arg < 0.03, 0.5,
        evidencias_presentes=[f"{hits_arg} marcadores argumentativos", f"{hits_narr} marcadores narrativos"],
    )


# --------------------------------------------------- outros gatilhos Etapa 0

_TERMOS_IMPROPRIOS = [
    "buceta", "caralho", "porra", "foda-se", "puta que pariu",
    "nao vou escrever nada", "nao vou fazer essa redacao",
]


def checar_conteudo_improprio(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-05 — impropérios/anulação proposital. Lista curta e objetiva de
    propósito: captura o caso claro, deixa qualquer coisa ambígua para
    confirmação — não é (nem tenta ser) um filtro de baixo calão completo."""
    texto_norm = _sem_acento((entrada.texto or "").lower())
    hits = [t for t in _TERMOS_IMPROPRIOS if _sem_acento(t) in texto_norm]
    # `suporte_limpo=1.5` só se aplica quando `hits` está vazio (não disparado);
    # quando há hit, `_evidencia_gatilho` já limita a `_TETO_SUPORTE_GATILHO_POSITIVO`.
    return _evidencia_gatilho("ZERO-05", bool(hits), 1.5, evidencias_presentes=hits)


_PADROES_DESCONEXAO = [
    "querida banca", "prezado avaliador", "prezada avaliadora", "cara banca",
    "amem", "louvado seja", "gloria a deus",
]


def checar_parte_desconectada(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-06 — endereçamento à banca, mensagem religiosa/política isolada etc."""
    texto_norm = _sem_acento((entrada.texto or "").lower())
    hits = [p for p in _PADROES_DESCONEXAO if p in texto_norm]
    return _evidencia_gatilho("ZERO-06", bool(hits), 1.5, evidencias_presentes=hits)


def checar_titulo_anulavel(entrada: RedacaoEntrada) -> Evidencia:
    """ZERO-11 — título com desenho/sinal gráfico sem função evidente."""
    if not entrada.titulo or not entrada.titulo.strip():
        return _evidencia_gatilho("ZERO-11", False, 2.0,
                                   evidencias_presentes=["sem título (opcional, não anula)"])
    limpo = entrada.titulo.strip()
    caracteres_normais = re.fullmatch(r"[\w\sÀ-ÿ.,;:!?'\"()-]+", limpo, flags=re.UNICODE)
    if caracteres_normais:
        return _evidencia_gatilho("ZERO-11", False, 2.0, evidencias_presentes=["título com caracteres normais"])
    return _evidencia_gatilho("ZERO-11", True, 0.5, evidencias_presentes=["título com caracteres fora do esperado"])


_TERMOS_VIOLACAO_DH = [
    "pena de morte", "justica com as proprias maos", "linchamento",
    "extermínio", "exterminio", "tortura como solucao", "matar todos",
    "eliminar a populacao", "limpeza etnica", "limpeza social",
]


def checar_direitos_humanos(entrada: RedacaoEntrada) -> Evidencia:
    """DH-ZERO-01 — proposta de intervenção que desrespeita direitos humanos.
    Zera só a Competência V (não a redação inteira) — ver `pontuacao.py`."""
    texto_norm = _sem_acento((entrada.texto or "").lower())
    hits = [t for t in _TERMOS_VIOLACAO_DH if t in texto_norm]
    return _evidencia_gatilho("DH-ZERO-01", bool(hits), 1.5, evidencias_presentes=hits)


def checar_texto_curto_digital(entrada: RedacaoEntrada) -> Evidencia:
    """Proxy de `ZERO-04` para submissão digital sem `linhas_manuscritas` —
    ver `elegibilidade.checar_texto_insuficiente`. Só decide "não
    insuficiente" com segurança (texto claramente longo); abaixo disso fica
    ambíguo, nunca decide "insuficiente" sozinha."""
    if entrada.linhas_manuscritas is not None:
        return Evidencia("ZERO-04-PROXY", "heuristica_local",
                          qualidade_entrada="linhas_manuscritas informado — ver elegibilidade.checar_texto_insuficiente")
    n_palavras = len(_tokens(entrada.texto or ""))
    if n_palavras >= 150:
        return _evidencia_gatilho("ZERO-04-PROXY", False, 2.0, evidencias_presentes=[f"{n_palavras} palavras"])
    return _evidencia_gatilho("ZERO-04-PROXY", n_palavras < 40, 0.5, evidencias_presentes=[f"{n_palavras} palavras"])


def checar_copia_textos_motivadores(entrada: RedacaoEntrada) -> Evidencia:
    """COPIA-01/02 — sem os textos motivadores como insumo estruturado, cópia
    recorrente não é verificável (fica `INSUFICIENTE`, nunca adivinhada)."""
    if not entrada.textos_motivadores:
        return Evidencia("COPIA-02", "heuristica_local",
                          qualidade_entrada="textos_motivadores não informados")
    texto_norm = _sem_acento((entrada.texto or "").lower())
    trechos_copiados = 0
    for motivador in entrada.textos_motivadores:
        for frase in _frases(motivador):
            f = _sem_acento(frase.lower().strip())
            if len(f) > 30 and f in texto_norm:
                trechos_copiados += 1
    dispara = trechos_copiados >= 2
    return _evidencia_gatilho("COPIA-02", dispara, 1.5,
                               evidencias_presentes=[f"{trechos_copiados} trechos coincidentes (>=30 caracteres)"])


# --------------------------------------------------------------- competências

_SPELL_PT = None


def _spellchecker_pt():
    global _SPELL_PT
    if _SPELL_PT is None:
        from spellchecker import SpellChecker
        _SPELL_PT = SpellChecker(language="pt")
    return _SPELL_PT


def avaliar_comp_I(entrada: RedacaoEntrada) -> Evidencia:
    """Domínio da escrita formal — proxy local via taxa de desvio ortográfico
    (`pyspellchecker`, dicionário pt). Não avalia registro nem estrutura
    sintática (declarado como evidência ausente): um proxy honesto de UM
    aspecto da competência, não da competência inteira."""
    tokens = [t for t in _tokens(entrada.texto or "") if len(t) > 2]
    if len(tokens) < 30:
        return Evidencia("COMP-I", "heuristica_local",
                          qualidade_entrada="texto curto demais para estimar desvios ortográficos")
    try:
        desconhecidas = _spellchecker_pt().unknown(tokens)
    except Exception:  # noqa: BLE001
        return Evidencia("COMP-I", "heuristica_local",
                          qualidade_entrada="checagem ortográfica local indisponível")
    taxa = len(desconhecidas) / len(tokens)
    presentes = [f"taxa de desvio ortográfico {taxa:.1%} ({len(desconhecidas)}/{len(tokens)} palavras)"]
    ausentes = ["registro e estrutura sintática (não avaliados localmente)"]
    if taxa <= 0.03:
        return Evidencia("COMP-I", "heuristica_local", candidatos=[(200, 1.5), (160, 0.6)],
                          evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    if taxa >= 0.20:
        return Evidencia("COMP-I", "heuristica_local", candidatos=[(40, 1.2)],
                          evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    nivel_aprox = 160 if taxa <= 0.08 else (120 if taxa <= 0.13 else 80)
    return Evidencia("COMP-I", "heuristica_local", candidatos=[(nivel_aprox, 0.4)],
                      evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)


_CONECTIVOS = [
    "portanto", "contudo", "todavia", "entretanto", "ademais", "outrossim",
    "porquanto", "assim", "logo", "porem", "porque", "pois", "visto que",
    "dessa forma", "desse modo", "diante disso", "nesse sentido",
    "por conseguinte", "alem disso", "em vista disso", "sob essa otica",
    "em primeiro lugar", "em segundo lugar", "por fim", "primeiramente",
    "nao obstante", "apesar de", "embora", "conquanto", "uma vez que",
    "haja vista", "isto e", "ou seja", "por exemplo", "como resultado",
    "consequentemente", "em suma", "em sintese",
]


def avaliar_comp_IV(entrada: RedacaoEntrada) -> Evidencia:
    """Mecanismos coesivos — diversidade de conectivos distintos + cobertura
    entre parágrafos. Não avalia adequação semântica de cada conectivo
    (declarado como evidência ausente)."""
    paragrafos = _paragrafos(entrada.texto or "")
    if len(paragrafos) < 2:
        return Evidencia("COMP-IV", "heuristica_local",
                          qualidade_entrada="texto sem parágrafos suficientes para avaliar coesão")
    texto_norm = _sem_acento((entrada.texto or "").lower())
    distintos = {c for c in _CONECTIVOS if c in texto_norm}
    com_conectivo = sum(1 for p in paragrafos if any(c in _sem_acento(p.lower()) for c in _CONECTIVOS))
    cobertura = com_conectivo / len(paragrafos)
    n = len(distintos)
    presentes = [f"{n} conectivos distintos", f"{cobertura:.0%} dos parágrafos com conectivo"]
    ausentes = ["adequação semântica dos conectivos usados (não avaliada localmente)"]
    if n >= 5 and cobertura >= 0.75:
        return Evidencia("COMP-IV", "heuristica_local", candidatos=[(200, 1.5), (160, 0.6)],
                          evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    if n <= 1 or cobertura < 0.25:
        return Evidencia("COMP-IV", "heuristica_local", candidatos=[(40, 1.2)],
                          evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    nivel_aprox = 160 if n >= 4 else (120 if n >= 2 else 80)
    return Evidencia("COMP-IV", "heuristica_local", candidatos=[(nivel_aprox, 0.4)],
                      evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)


_LEXICO_AGENTE = [
    "governo", "estado", "escola", "escolas", "familia", "familias", "midia",
    "midias", "sociedade", "ongs", "ong", "poder publico", "ministerio",
    "prefeitura", "uniao", "municipios", "empresas", "universidades",
]
_LEXICO_ACAO = ["deve", "deveria", "e necessario", "e preciso", "cabe a", "faz-se necessario", "urge"]
_LEXICO_MEIO = ["por meio de", "atraves de", "mediante", "com base em", "utilizando", "por meio da", "atraves da"]
_LEXICO_EFEITO = ["a fim de", "para que", "com o objetivo de", "de modo a", "de forma a", "visando", "com o intuito de"]
_LEXICO_DETALHAMENTO = ["alem disso", "ademais", "por exemplo", "tal como"]


def avaliar_comp_V(entrada: RedacaoEntrada) -> Evidencia:
    """Proposta de intervenção — detecção lexical dos 5 elementos oficiais
    (ação, agente, meio, efeito, detalhamento) no último parágrafo."""
    paragrafos = _paragrafos(entrada.texto or "")
    if not paragrafos:
        return Evidencia("COMP-V", "heuristica_local",
                          qualidade_entrada="sem parágrafos para localizar a proposta de intervenção")
    ultimo = _sem_acento(paragrafos[-1].lower())
    elementos = {
        "agente": any(t in ultimo for t in _LEXICO_AGENTE),
        "acao": any(t in ultimo for t in _LEXICO_ACAO),
        "meio": any(t in ultimo for t in _LEXICO_MEIO),
        "efeito": any(t in ultimo for t in _LEXICO_EFEITO),
        "detalhamento": any(t in ultimo for t in _LEXICO_DETALHAMENTO),
    }
    presentes = [k for k, v in elementos.items() if v]
    ausentes = [k for k, v in elementos.items() if not v]
    n = len(presentes)
    if n >= 4:
        return Evidencia("COMP-V", "heuristica_local", candidatos=[(200, 1.2), (160, 0.6)],
                          evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    if n <= 1:
        return Evidencia("COMP-V", "heuristica_local", candidatos=[(0, 1.0), (40, 0.5)],
                          evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    nivel_aprox = 160 if n == 4 else (120 if n == 3 else 80)
    return Evidencia("COMP-V", "heuristica_local", candidatos=[(nivel_aprox, 0.4)],
                      evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)


def avaliar_comp_II(entrada: RedacaoEntrada) -> Evidencia:
    """Compreensão da proposta — cobertura temática + presença de estrutura
    de parágrafos. Nunca propõe o nível máximo localmente: distinguir
    repertório produtivo de repertório de bolso (AMB-04) exige leitura
    semântica que esta heurística não faz."""
    if not entrada.tema_elementos_obrigatorios:
        return Evidencia("COMP-II", "heuristica_local",
                          qualidade_entrada="tema_elementos_obrigatorios não informado")
    encontrados, total, presentes = _cobertura_tematica(entrada)
    cobertura = encontrados / total
    paragrafos = _paragrafos(entrada.texto or "")
    ausentes_tema = [e for e in entrada.tema_elementos_obrigatorios if e not in presentes]
    ausentes = ausentes_tema + ["qualidade do repertório sociocultural (exige leitura semântica)"]
    if cobertura >= 0.9 and len(paragrafos) >= 4:
        return Evidencia("COMP-II", "heuristica_local", candidatos=[(160, 1.2)],
                          evidencias_presentes=presentes + [f"{len(paragrafos)} parágrafos"],
                          evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    if cobertura == 0:
        return Evidencia("COMP-II", "heuristica_local", candidatos=[(0, 0.4)],
                          evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    nivel_aprox = 120 if cobertura >= 0.4 else 40
    return Evidencia("COMP-II", "heuristica_local", candidatos=[(nivel_aprox, 0.4)],
                      evidencias_presentes=presentes, evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)


def avaliar_comp_III(entrada: RedacaoEntrada) -> Evidencia:
    """Seleção/organização de argumentos — proxy via estrutura de parágrafos
    (contagem + equilíbrio de tamanho). Nunca propõe o nível máximo
    localmente: progressão argumentativa e ausência de lacunas de sentido
    exigem leitura semântica."""
    paragrafos = _paragrafos(entrada.texto or "")
    if len(paragrafos) < 3:
        return Evidencia("COMP-III", "heuristica_local",
                          qualidade_entrada="texto sem estrutura de parágrafos suficiente")
    tamanhos = [len(_tokens(p)) for p in paragrafos]
    media = sum(tamanhos) / len(tamanhos)
    equilibrado = media > 0 and max(tamanhos) <= 3 * media
    ausentes = ["progressão argumentativa e ausência de lacunas de sentido (exige leitura semântica)"]
    if len(paragrafos) >= 4 and equilibrado:
        return Evidencia("COMP-III", "heuristica_local", candidatos=[(160, 1.2)],
                          evidencias_presentes=[f"{len(paragrafos)} parágrafos, tamanho equilibrado"],
                          evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    if len(paragrafos) < 3 or not equilibrado:
        return Evidencia("COMP-III", "heuristica_local", candidatos=[(80, 0.4)],
                          evidencias_presentes=[f"{len(paragrafos)} parágrafos"],
                          evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)
    return Evidencia("COMP-III", "heuristica_local", candidatos=[(120, 0.4)],
                      evidencias_presentes=[f"{len(paragrafos)} parágrafos"],
                      evidencias_ausentes=ausentes, suporte_minimo_forte=1.0)


def avaliar_heuristicas_gatilhos(entrada: RedacaoEntrada) -> dict[str, Evidencia]:
    return {
        "ZERO-01": checar_fuga_tema(entrada),
        "TEMA-02": checar_tangenciamento(entrada),
        "TIPO-TEXTUAL": checar_tipo_dissertativo_argumentativo(entrada),
        "ZERO-05": checar_conteudo_improprio(entrada),
        "ZERO-06": checar_parte_desconectada(entrada),
        "ZERO-11": checar_titulo_anulavel(entrada),
        "DH-ZERO-01": checar_direitos_humanos(entrada),
        "ZERO-04-PROXY": checar_texto_curto_digital(entrada),
        "COPIA-02": checar_copia_textos_motivadores(entrada),
    }


def avaliar_heuristicas_competencias(entrada: RedacaoEntrada) -> dict[str, Evidencia]:
    return {
        "COMP-I": avaliar_comp_I(entrada),
        "COMP-II": avaliar_comp_II(entrada),
        "COMP-III": avaliar_comp_III(entrada),
        "COMP-IV": avaliar_comp_IV(entrada),
        "COMP-V": avaliar_comp_V(entrada),
    }
