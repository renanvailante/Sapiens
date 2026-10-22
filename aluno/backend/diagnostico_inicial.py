"""As 10 questões do diagnóstico do primeiro acesso — regra pura, sem banco.

**Por que existe (2026-10-22).** 28 de 43 alunos se cadastravam e nunca
respondiam uma questão. Entre o cadastro e a primeira questão havia o
formulário, cinco etapas de boas-vindas, um tour de cinco balões e, no fim, a
primeira questão de Matemática de um caderno qualquer, ordenado pelo número da
prova — a área em que o vestibulando mais erra, aberta pela questão 136. Agora
o cadastro abre direto nestas dez, e o plano da semana vem depois delas.

**O que a regra escolhe, e o que ela NÃO afirma.** O acervo não tem
dificuldade por questão (nem TRI, nem taxa de acerto), então a regra não diz
escolher "as fáceis". Ela escolhe o que dá para medir de verdade:

- **só texto** — sem figura, sem imagem de recursos, sem alternativa em
  figura, e sem enunciado que cite uma figura que não veio. No celular, uma
  imagem que demora ou não carrega na primeira questão é a pior abertura
  possível;
- **sem língua estrangeira** (questões 1-5 do caderno de Linguagens e
  disciplina de inglês/espanhol): metade da turma não fez a mesma opção;
- **as mais curtas** de cada área (enunciado + alternativas): é a carga de
  leitura, e é ela que decide quanto tempo leva a primeira resposta;
- **intercaladas** (Linguagens, Humanas, Natureza, Matemática, ...): o
  diagnóstico vê as quatro áreas, e a de menor acerto no ENEM (Matemática) não
  abre a sequência.

A lista é a MESMA para todo mundo enquanto o acervo não muda: é ela que deixa
retomar no meio (o runner começa na primeira não respondida) e comparar alunos.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable

TOTAL = 10

LINGUAGENS = "Linguagens e Códigos"
HUMANAS = "Ciências Humanas"
NATUREZA = "Ciências da Natureza"
MATEMATICA = "Matemática"

# A ordem é a do aluno: a primeira questão é a que mais pesa, e é a que tem de
# ser respondida em menos de um minuto depois do cadastro.
ORDEM: tuple[str, ...] = (
    LINGUAGENS, HUMANAS, NATUREZA, MATEMATICA,
    LINGUAGENS, HUMANAS, NATUREZA, MATEMATICA,
    HUMANAS, LINGUAGENS,
)

# Enunciado que cita uma peça visual sem trazer a peça é questão quebrada na
# tela, não questão curta. A lista pega a maioria; o que escapa ainda passa
# pela régua de "sem asset".
_CITA_VISUAL = re.compile(
    r"\b(figura|imagem|gr[áa]fico|charge|tirinha|cartum|quadrinho|mapa|tabela|"
    r"infogr[áa]fico|fotografia|foto|ilustra[çc][ãa]o|esquema|diagrama)s?\b",
    re.IGNORECASE,
)
_LINGUA_ESTRANGEIRA = re.compile(r"ingl[êe]s|espanhol|estrangeira", re.IGNORECASE)
# Texto em inglês ou espanhol sem rótulo de disciplina: palavras que o
# português não usa. Quatro ou mais no enunciado e a questão é de língua
# estrangeira, seja qual for a numeração.
_PALAVRAS_ESTRANGEIRAS = re.compile(
    r"\b(the|and|of|with|you|are|is|this|el|los|las|del|una|muy|pero)\b", re.IGNORECASE,
)

# `server._area_enem` reconhece a área pelo nome largo ("Ciências Humanas",
# "Física"); a extração às vezes grava a disciplina fina. Estas pistas só
# completam o que ela devolveu fora das quatro áreas.
_PISTAS_EXTRAS: tuple[tuple[str, str], ...] = (
    ("hist", "Ciências Humanas"), ("geograf", "Ciências Humanas"),
    ("filosof", "Ciências Humanas"), ("sociolog", "Ciências Humanas"),
    ("portugu", "Linguagens e Códigos"), ("literatura", "Linguagens e Códigos"),
    ("artes", "Linguagens e Códigos"), ("educação física", "Linguagens e Códigos"),
)

# Abaixo disso o "enunciado" costuma ser um pedaço de extração, não uma questão.
_MINIMO_DE_ENUNCIADO = 120


def area(disciplina: str | None, area_de: Callable[[str | None], str | None]) -> str | None:
    """A área do ENEM da disciplina: a de `area_de`, ou a das pistas extras."""
    achada = area_de(disciplina)
    if achada in ORDEM:
        return achada
    baixo = (disciplina or "").lower()
    if _LINGUA_ESTRANGEIRA.search(baixo):
        return None
    for pista, a in _PISTAS_EXTRAS:
        if pista in baixo:
            return a
    return achada


def _texto(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def _alternativas(item: dict) -> list[dict]:
    alts = (item.get("questao") or {}).get("alternativas") or []
    return [a for a in alts if isinstance(a, dict)]


def carga(item: dict) -> int:
    """Caracteres que o aluno precisa ler para responder."""
    q = item.get("questao") or {}
    return len(_texto(q.get("enunciado"))) + sum(len(_texto(a.get("texto"))) for a in _alternativas(item))


def tem_figura(item: dict) -> bool:
    q = item.get("questao") or {}
    if q.get("visual_assets"):
        return True
    imagens = ((q.get("recursos") or {}).get("imagens")) or []
    return any(isinstance(img, dict) and img.get("arquivo") for img in imagens)


def lingua_estrangeira(item: dict, area: str | None) -> bool:
    f = item.get("fonte") or {}
    if _LINGUA_ESTRANGEIRA.search(_texto(f.get("disciplina"))):
        return True
    enunciado = _texto((item.get("questao") or {}).get("enunciado"))
    if len(_PALAVRAS_ESTRANGEIRAS.findall(enunciado)) >= 4:
        return True
    try:
        numero = int(f.get("numero"))
    except (TypeError, ValueError):
        return False
    # 1-5 no caderno de Linguagens desde 2017; 91-95 de 2009 a 2016, quando
    # Linguagens abria o segundo dia.
    return area == LINGUAGENS and (1 <= numero <= 5 or 91 <= numero <= 95)


def elegivel(item: dict, area: str | None, *, estrito: bool = True) -> bool:
    """Cabe no diagnóstico? `estrito=False` só relaxa a citação de figura —
    nunca a figura em si nem a língua estrangeira."""
    if not item.get("item_id") or area not in ORDEM:
        return False
    enunciado = _texto((item.get("questao") or {}).get("enunciado"))
    if len(enunciado) < _MINIMO_DE_ENUNCIADO:
        return False
    alts = _alternativas(item)
    if len(alts) < 4 or not all(_texto(a.get("texto")) and a.get("letra") for a in alts):
        return False
    if tem_figura(item) or lingua_estrangeira(item, area):
        return False
    if estrito and _CITA_VISUAL.search(enunciado):
        return False
    return True


def escolher(itens: Iterable[dict], area_de: Callable[[str | None], str | None]) -> list[str]:
    """Os `item_id` do diagnóstico, na ordem em que o aluno os responde.

    Desempate estável (carga, edição mais recente, id): a mesma entrada dá a
    mesma lista em qualquer máquina. Uma área sem questão suficiente cede a
    vaga às outras; a passada relaxada só entra se a estrita não fechar dez.
    """
    itens = list(itens)
    por_area: dict[str, list[dict]] = {a: [] for a in set(ORDEM)}
    reserva: list[dict] = []
    for it in itens:
        a = area((it.get("fonte") or {}).get("disciplina"), area_de)
        if elegivel(it, a):
            por_area[a].append(it)
        elif elegivel(it, a, estrito=False):
            reserva.append(it)

    def chave(it: dict) -> tuple:
        ano = (it.get("fonte") or {}).get("ano")
        return (carga(it), -(ano if isinstance(ano, int) else 0), str(it.get("item_id")))

    for lista in por_area.values():
        lista.sort(key=chave)
    reserva.sort(key=chave)

    escolhidos: list[str] = []
    vistos_ids: set[str] = set()
    vistos_textos: set[str] = set()

    def pegar(candidatos: list[dict]) -> bool:
        while candidatos:
            it = candidatos.pop(0)
            # Duas questões do mesmo texto-base (o ENEM faz pares) leriam como
            # a mesma questão duas vezes.
            inicio = _texto((it.get("questao") or {}).get("enunciado"))[:120].lower()
            if it["item_id"] in vistos_ids or inicio in vistos_textos:
                continue
            escolhidos.append(it["item_id"])
            vistos_ids.add(it["item_id"])
            vistos_textos.add(inicio)
            return True
        return False

    # Uma volta pela ordem por vez: faltou uma área, as outras cobrem a vaga
    # sem que nenhuma passe na frente da sequência intercalada.
    andou = True
    while len(escolhidos) < TOTAL and andou:
        andou = False
        for a in ORDEM:
            if len(escolhidos) >= TOTAL:
                break
            andou = pegar(por_area[a]) or andou
    while len(escolhidos) < TOTAL and pegar(reserva):
        pass
    return escolhidos[:TOTAL]
