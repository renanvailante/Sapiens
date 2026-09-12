"""Onde a próxima hora de estudo rende mais ponto no ENEM.

Este módulo é a resposta a uma pergunta que o produto inteiro precisava
responder do mesmo jeito em toda tela: **entre tudo que este aluno pode
estudar agora, o que move mais a nota dele?**

Antes desta peça, cada superfície respondia sozinha e com critério diferente:
o Painel ordenava por menor taxa de acerto, o Treino por habilidade fraca, o
chat da Mentis pelo que o dossiê listasse primeiro. Todos os três respondiam
"onde você erra mais" — que **não é** a mesma pergunta. Errar muito numa área
que vale pouco rende menos ponto do que errar médio numa área que vale muito.

Duas medidas entram no cálculo, e nenhuma delas é inferida por IA:

**1. O peso da área na prova** (`DISCIPLINAS`) — decisão de produto do dono do
Sapiens, fixada em 2026-09-12:

  * **Matemática e Redação valem mais.** A Redação é 1000 pontos isolados, um
    quinto da nota final, e é o único componente que não depende de acertar
    item nenhum. Matemática é a área de maior dispersão na TRI do ENEM: a
    mesma quantidade de acertos a mais mexe mais na nota ali do que em
    qualquer outra área.
  * **Depois vêm Biologia, Química e Física.**
  * **Por último, Ciências Humanas e Linguagens** — onde a nota da maioria já
    nasce alta e o teto de ganho por hora estudada é menor.

**2. A lacuna medida do aluno** — quanto falta para o acerto pleno naquilo,
com a amostra ao lado. É contagem determinística sobre o que ele respondeu
(`annotation_service`), nunca opinião.

    rendimento = peso × lacuna × confiança

`confiança` é o freio contra falar alto com amostra pequena: quem respondeu 3
questões de Física tem uma hipótese, não um diagnóstico, e o número reflete
isso em vez de a interface fingir certeza.

**O aluno sem histórico nenhum não fica sem resposta.** Uma área nunca medida
não é tratada como "sem lacuna" (o que a jogaria para o fim da fila e daria a
um aluno novo um cronograma vazio): ela entra com uma lacuna neutra e o
estado `sem_medida`, ou seja, **entra pelo peso na prova**. É por isso que o
primeiro cronograma de quem acabou de se cadastrar já vem dominado por
Matemática e Redação — que é exatamente onde ele deveria começar.
"""
from __future__ import annotations

from typing import Any, Optional

# Peso de cada frente na nota final. Ver o cabeçalho: é decisão de produto,
# não estimativa estatística — e por isso mora aqui, num lugar só, em vez de
# reaparecer como número mágico em cada tela.
DISCIPLINAS: list[dict[str, Any]] = [
    {"chave": "matematica", "nome": "Matemática", "peso": 1.00,
     "area_enem": "Matemática", "rota": "/exams?area=Matemática"},
    {"chave": "redacao", "nome": "Redação", "peso": 1.00,
     "area_enem": None, "rota": "/redacao"},
    {"chave": "biologia", "nome": "Biologia", "peso": 0.70,
     "area_enem": "Ciências da Natureza", "rota": "/exams?area=Ciências da Natureza"},
    {"chave": "quimica", "nome": "Química", "peso": 0.70,
     "area_enem": "Ciências da Natureza", "rota": "/exams?area=Ciências da Natureza"},
    {"chave": "fisica", "nome": "Física", "peso": 0.70,
     "area_enem": "Ciências da Natureza", "rota": "/exams?area=Ciências da Natureza"},
    # O acervo nem sempre diz QUAL ciência da natureza é o item: muita fonte
    # traz só o rótulo da área ("Ciências da Natureza e suas Tecnologias").
    # Inventar Biologia ali seria fabricar medida, então essas respostas
    # contam numa frente própria, com o mesmo peso das três.
    {"chave": "natureza", "nome": "Ciências da Natureza", "peso": 0.70,
     "area_enem": "Ciências da Natureza", "rota": "/exams?area=Ciências da Natureza"},
    {"chave": "humanas", "nome": "Ciências Humanas", "peso": 0.50,
     "area_enem": "Ciências Humanas", "rota": "/exams?area=Ciências Humanas"},
    {"chave": "linguagens", "nome": "Linguagens e Códigos", "peso": 0.50,
     "area_enem": "Linguagens e Códigos", "rota": "/exams?area=Linguagens e Códigos"},
]

_POR_CHAVE = {d["chave"]: d for d in DISCIPLINAS}

# `fonte.disciplina` é texto livre extraído pelo modelo do pipeline: vem com
# caixa, acento e granularidade variados ("Física", "FISICA", "Ciências da
# Natureza e suas Tecnologias"). A ordem importa — a pista mais específica
# precisa ser testada antes do guarda-chuva da área.
_PISTAS: list[tuple[str, str]] = [
    ("matem", "matematica"),
    ("biolog", "biologia"),
    ("quimic", "quimica"),
    # ANTES de "fisic": "Educação Física" contém a pista de Física e cairia na
    # frente errada — é matéria de Linguagens no ENEM, não de Natureza.
    ("educacao fisica", "linguagens"),
    ("fisic", "fisica"),
    ("natureza", "natureza"),
    ("histor", "humanas"),
    ("geograf", "humanas"),
    ("filosof", "humanas"),
    ("sociolog", "humanas"),
    ("human", "humanas"),
    ("portugu", "linguagens"),
    ("literat", "linguagens"),
    ("ingl", "linguagens"),
    ("espanhol", "linguagens"),
    ("gramat", "linguagens"),
    ("interpretacao de texto", "linguagens"),
    ("arte", "linguagens"),
    ("linguagen", "linguagens"),
]

_ACENTOS = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
                         "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")

# Abaixo disto não se afirma nada sobre a frente: ela fica `sem_medida` e
# entra pelo peso, como se nunca tivesse sido tocada.
AMOSTRA_MINIMA = 3
# A partir daqui a medida vale inteira. Entre um e outro, a confiança sobe
# proporcionalmente — é o que impede "40% de acerto em 4 questões" de pesar
# igual a "40% em 40".
AMOSTRA_PLENA = 8
# Lacuna atribuída a quem ainda não foi medido naquela frente. Metade do
# caminho: nem otimismo (que esconderia a frente), nem alarme (que a jogaria
# para o topo sem nenhuma evidência).
LACUNA_SEM_MEDIDA = 0.50
# Desconto aplicado ao rendimento de uma frente sem medida, para que uma
# lacuna comprovada sempre passe na frente de uma presumida de mesmo tamanho.
FATOR_SEM_MEDIDA = 0.60

REDACAO_NOTA_MAXIMA = 1000


def _sem_acento(texto: str) -> str:
    return texto.translate(_ACENTOS).lower()


def classificar_disciplina(bruta: Optional[str]) -> Optional[str]:
    """`fonte.disciplina` (texto livre do acervo) -> chave de frente, ou None.

    None quer dizer "não sei onde isto entra" — e o certo aí é a resposta não
    contar para frente nenhuma, nunca ser chutada para a mais próxima.
    """
    if not bruta or not isinstance(bruta, str):
        return None
    baixo = _sem_acento(bruta.strip())
    if not baixo:
        return None
    for pista, chave in _PISTAS:
        if pista in baixo:
            return chave
    return None


def _confianca(respondidas: int) -> float:
    if respondidas <= 0:
        return 0.0
    return round(min(1.0, respondidas / AMOSTRA_PLENA), 3)


# Piso da confiança no cálculo do rendimento. Amostra curta torna a ESTIMATIVA
# menos certa — não torna a área menos valiosa na prova. Sem este piso, uma
# lacuna real medida em 4 questões de Matemática pesava menos que uma lacuna
# presumida de Biologia, e a ordem passava a punir o aluno justamente por ter
# começado a medir. O peso continua aparecendo inteiro na interface
# (`confianca`), que é o número usado para dizer "trate como hipótese".
_PISO_CONFIANCA = 0.60


def _confianca_efetiva(confianca: float) -> float:
    return _PISO_CONFIANCA + (1.0 - _PISO_CONFIANCA) * confianca


def _estado(respondidas: int) -> str:
    if respondidas < AMOSTRA_MINIMA:
        return "sem_medida"
    if respondidas < AMOSTRA_PLENA:
        return "amostra_curta"
    return "medido"


def _porque(nome: str, peso: float, estado: str, taxa: Optional[float], respondidas: int) -> str:
    """A frase que a interface mostra. Sempre diz as DUAS metades: o peso na
    prova e a medida do aluno — sem uma delas o aluno não consegue discordar
    da ordem, e uma recomendação com a qual não dá para discordar é ordem, não
    orientação."""
    if peso >= 1.0:
        peso_txt = f"{nome} é uma das duas frentes que mais movem a nota do ENEM"
    elif peso >= 0.7:
        peso_txt = f"{nome} tem peso intermediário na sua nota"
    else:
        peso_txt = f"{nome} rende menos ponto por hora estudada"
    if estado == "sem_medida":
        return (
            f"{peso_txt}, e você ainda não respondeu o bastante aqui para eu medir. "
            "Entra na sua semana pelo peso na prova, não por diagnóstico."
        )
    medida = f"você acerta {taxa}% ({respondidas} questões medidas)"
    if estado == "amostra_curta":
        return f"{peso_txt}. Por enquanto {medida} — amostra ainda curta, então trate como hipótese."
    return f"{peso_txt}, e {medida}."


def _linha(chave: str, respondidas: int, acertos: int) -> dict[str, Any]:
    base = _POR_CHAVE[chave]
    estado = _estado(respondidas)
    if estado == "sem_medida":
        taxa: Optional[float] = round(100 * acertos / respondidas, 1) if respondidas else None
        lacuna = LACUNA_SEM_MEDIDA
        rendimento = base["peso"] * lacuna * FATOR_SEM_MEDIDA
        confianca = _confianca(respondidas)
    else:
        taxa = round(100 * acertos / respondidas, 1)
        lacuna = max(0.0, 1.0 - (acertos / respondidas))
        confianca = _confianca(respondidas)
        rendimento = base["peso"] * lacuna * _confianca_efetiva(confianca)
    return {
        "chave": chave,
        "nome": base["nome"],
        "peso": base["peso"],
        "area_enem": base["area_enem"],
        "rota": base["rota"],
        "respondidas": respondidas,
        "acertos": acertos,
        "taxa_acerto": taxa,
        "lacuna": round(lacuna, 3),
        "confianca": confianca,
        "estado": estado,
        "rendimento": round(rendimento, 4),
        "porque": _porque(base["nome"], base["peso"], estado, taxa, respondidas),
    }


def _linha_redacao(redacao: Optional[dict[str, Any]]) -> dict[str, Any]:
    """A Redação não tem taxa de acerto — tem nota de 0 a 1000. A lacuna é o
    quanto falta para 1000 na MELHOR redação já corrigida (a melhor, não a
    última: uma redação ruim num dia ruim não apaga o que o aluno provou que
    consegue escrever)."""
    base = _POR_CHAVE["redacao"]
    corrigidas = int((redacao or {}).get("corrigidas") or 0)
    nota = (redacao or {}).get("melhor_nota")
    if not corrigidas or nota is None:
        return {
            "chave": "redacao", "nome": base["nome"], "peso": base["peso"],
            "area_enem": None, "rota": base["rota"],
            "respondidas": 0, "acertos": 0, "taxa_acerto": None,
            "nota": None, "corrigidas": 0,
            "lacuna": LACUNA_SEM_MEDIDA, "confianca": 0.0, "estado": "sem_medida",
            "rendimento": round(base["peso"] * LACUNA_SEM_MEDIDA * FATOR_SEM_MEDIDA, 4),
            "porque": (
                "A Redação vale 1000 pontos sozinha e é a nota que mais sobe com treino — "
                "e você ainda não corrigiu nenhuma aqui. É o ponto de partida mais barato "
                "que a sua semana tem."
            ),
        }
    nota = int(nota)
    lacuna = max(0.0, 1.0 - nota / REDACAO_NOTA_MAXIMA)
    # Uma redação corrigida já é uma medida real (ao contrário de uma questão
    # só), mas três dão a curva. A confiança sobe até a terceira.
    confianca = round(min(1.0, corrigidas / 3), 3)
    return {
        "chave": "redacao", "nome": base["nome"], "peso": base["peso"],
        "area_enem": None, "rota": base["rota"],
        "respondidas": corrigidas, "acertos": 0, "taxa_acerto": None,
        "nota": nota, "corrigidas": corrigidas,
        "lacuna": round(lacuna, 3), "confianca": confianca,
        "estado": "medido" if corrigidas >= 3 else "amostra_curta",
        "rendimento": round(base["peso"] * lacuna * _confianca_efetiva(confianca), 4),
        "porque": (
            f"Sua melhor redação corrigida deu {nota} de 1000, e faltam "
            f"{REDACAO_NOTA_MAXIMA - nota} pontos que valem tanto quanto uma área inteira "
            "de questões."
        ),
    }


# As quatro frentes que dividem Ciências da Natureza. "natureza" é o
# guarda-chuva, e existe só porque parte do acervo rotula o item pela área em
# vez da matéria.
_GRUPO_NATUREZA = ("biologia", "quimica", "fisica", "natureza")


def _consolidar_natureza(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tira o guarda-chuva da frente quando ele não tem medida própria.

    Sem isto, o aluno recém-cadastrado recebia QUATRO frentes de Ciências da
    Natureza empatadas no mesmo rendimento — Biologia, Química, Física e mais
    uma chamada "Ciências da Natureza" —, o que enche metade do cronograma com
    a mesma coisa escrita de quatro jeitos. Biologia, Química e Física ficam
    sempre (são as matérias que o aluno reconhece); o guarda-chuva só aparece
    quando ele carrega respostas que o acervo não soube separar.
    """
    guarda_chuva = next((l for l in linhas if l["chave"] == "natureza"), None)
    if guarda_chuva is None or guarda_chuva["respondidas"] >= AMOSTRA_MINIMA:
        return linhas
    return [l for l in linhas if l["chave"] != "natureza"]


def ranking(
    disciplina_stats: Optional[dict[str, dict[str, int]]] = None,
    redacao: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Todas as frentes, da que mais rende ponto para a que menos rende.

    `disciplina_stats` é `{chave: {"respondidas": n, "acertos": n}}` — já
    classificado por `classificar_disciplina`. `redacao` é
    `{"melhor_nota": int, "corrigidas": int}` ou None.

    Devolve SEMPRE a lista inteira, inclusive as frentes sem medida: uma
    frente que some da resposta é uma frente que o aluno nunca descobre que
    existe. Quem decide o que mostrar é a tela.
    """
    stats = disciplina_stats or {}
    linhas = [
        _linha(d["chave"], int((stats.get(d["chave"]) or {}).get("respondidas") or 0),
               int((stats.get(d["chave"]) or {}).get("acertos") or 0))
        for d in DISCIPLINAS
        if d["chave"] != "redacao"
    ]
    linhas.append(_linha_redacao(redacao))
    linhas = _consolidar_natureza(linhas)
    # Desempate por peso e depois por nome: sem isso, duas frentes de
    # rendimento idêntico trocariam de lugar entre duas leituras seguidas e o
    # aluno veria a ordem "mudar sozinha" sem ter respondido nada.
    linhas.sort(key=lambda l: (-l["rendimento"], -l["peso"], l["nome"]))
    return linhas


def texto_para_modelo(linhas: list[dict[str, Any]], teto: int = 5) -> str:
    """O ranking compactado numa linha por frente, para entrar em prompt.

    Formato fixo e curto de propósito: este texto vai junto de TODA abertura
    de sessão da Mentis e de toda geração de cronograma, então o seu tamanho é
    custo recorrente.
    """
    partes = []
    for i, l in enumerate(linhas[:teto], start=1):
        if l["chave"] == "redacao" and l.get("nota") is not None:
            medida = f"melhor nota {l['nota']}/1000 em {l['corrigidas']} redação(ões)"
        elif l["estado"] == "sem_medida":
            medida = "ainda sem medida"
        else:
            medida = f"{l['taxa_acerto']}% de acerto em {l['respondidas']} questões"
        partes.append(f"{i}. {l['nome']} (peso {l['peso']:.2f} na nota; {medida})")
    return "; ".join(partes) + "."
