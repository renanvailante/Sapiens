"""As rotas do app do aluno, do lado do servidor.

O backend **emite endereços de tela como dado**: o bloco do cronograma diz para
onde ir, a missão do dia leva o aluno a algum lugar, a Mentis escolhe um destino
de uma lista fechada, o painel do perfil sugere uma ação. Todos esses caminhos
eram strings digitadas à mão em cinco módulos.

O preço disso já foi pago e ninguém percebeu: `mentis_routes.DESTINOS` continuou
apontando para `/cognitive-profile` e `/cursos#live` **meses depois** de as duas
telas terem sido renomeadas. Não quebrou porque o frontend mantinha um redirect
calado — ou seja, o defeito ficou invisível justamente porque havia uma rede de
segurança. Rota digitada é rota que diverge.

Aqui há um lugar só. O espelho do lado do cliente é
`aluno/frontend/src/lib/rotas.js`, e `test_rotas_do_app.py` compara os dois
arquivos: se alguém renomear de um lado só, o teste cai.

**Por que não um endpoint que serve as rotas ao frontend:** porque o frontend
precisa delas para construir o roteador, antes de qualquer requisição — e uma
chamada de rede na inicialização para descobrir o próprio endereço das telas é
um ponto de falha novo em troca de nada.
"""
from __future__ import annotations

# --- As cinco áreas -------------------------------------------------------
HOJE = "/hoje"

ESTUDAR = "/estudar"
PROVAS = "/estudar/provas"
CURSOS = "/estudar/cursos"
REDACAO = "/estudar/redacao"
TREINO = "/estudar/treino"
FOLHEAR = "/estudar/folhear"

AGENDA = "/agenda"
PROGRESSO = "/progresso"
COMUNIDADE = "/comunidade"

# --- Camada e fluxos ------------------------------------------------------
MENTIS = "/mentis"
SPARKS = "/sparks"
SUGESTOES = "/sugestoes"
AULA_AO_VIVO = "/aula-ao-vivo"
MENTORIA = "/mentoria"

# --- Âncoras de seção -----------------------------------------------------
# Uma seção não é uma rota, mas o link para ela é público. Uma âncora digitada
# errada falha em silêncio: a página abre no topo e ninguém descobre.
HOJE_MISSOES = f"{HOJE}#missoes"
AGENDA_REVISOES = f"{AGENDA}#revisoes"
AGENDA_LEMBRETES = f"{AGENDA}#lembretes"
AGENDA_SEMANA = f"{AGENDA}#semana"
PROGRESSO_CONQUISTAS = f"{PROGRESSO}#conquistas"
PROGRESSO_HISTORICO = f"{PROGRESSO}#historico"
PROGRESSO_TRAJETORIA = f"{PROGRESSO}#trajetoria"

# --- Os endereços antigos -------------------------------------------------
# Mesma tabela do `LEGADO` do frontend, e ela existe aqui por um motivo que não
# é simetria: **a chave de idempotência dos lembretes é o hash do texto + a
# ROTA** (`lembretes_routes._chave`). Sem normalizar, o aluno que guardou um
# trecho em `/redacao` seria cobrado de novo pelo MESMO trecho em
# `/estudar/redacao` — uma renomeação de tela virando cobrança em dobro.
#
# Ver `Cerebro/arquitetura/dados.md`, "a digital do conteúdo é a chave".
LEGADO: dict[str, str] = {
    "/dashboard": HOJE,
    "/cronograma": AGENDA,
    "/desempenho": PROGRESSO,
    "/cognitive-profile": PROGRESSO,
    "/diagnostico": PROGRESSO,
    "/motor": PROGRESSO,
    "/revisoes": AGENDA_REVISOES,
    "/plan": AGENDA_REVISOES,
    "/conquistas": PROGRESSO_CONQUISTAS,
    "/liga": PROGRESSO_CONQUISTAS,
    "/history": PROGRESSO_HISTORICO,
    "/trash": PROGRESSO_HISTORICO,
    "/indicar": f"{SPARKS}#indicar",
    "/exams": PROVAS,
    "/cursos": CURSOS,
    "/redacao": REDACAO,
    "/treino": TREINO,
    "/feed": FOLHEAR,
    "/minhas-questoes": f"{TREINO}?fonte=geradas",
    "/questoes": PROVAS,
    "/aulas": MENTORIA,
    "/live": AULA_AO_VIVO,
    "/mural": COMUNIDADE,
    "/duvidas": COMUNIDADE,
}


def antecessores(rota: str | None) -> list[str]:
    """Os endereços ANTIGOS que levavam a esta rota canônica.

    Existe por causa da chave de idempotência dos lembretes. `normalizar`
    sozinha resolve metade do problema — ela faz um link velho chegar à chave
    nova —, mas não alcança o que já está GRAVADO: um lembrete guardado em
    `/redacao` antes de 2026-09-18 tem `_id` calculado sobre `/redacao`, e
    nenhuma normalização do texto novo vai reproduzir aquele hash.

    Então a busca prova as duas formas. Quem escreve usa a canônica; quem lê
    aceita qualquer uma que já tenha existido. É o que mantém verdadeira a
    regra "cobra uma vez por trecho, para sempre" através de uma renomeação.
    """
    if not rota:
        return []
    base = rota.split("?")[0].split("#")[0].rstrip("/") or "/"
    return [antiga for antiga, nova in LEGADO.items() if nova.split("?")[0].split("#")[0] == base]


def normalizar(rota: str | None) -> str:
    """O endereço atual de um caminho de tela.

    Preserva query e fragmento do chamador: `/exams?area=Matemática` vira
    `/estudar/provas?area=Matemática`. Perder a query aqui entregaria um caderno
    genérico onde o aluno pediu a questão que errou — falha silenciosa, que é a
    classe de defeito mais cara deste repositório.

    Caminho desconhecido volta como veio: esta função traduz, não valida.
    """
    if not rota:
        return ""

    base, sep, resto = rota.partition("?")
    if not sep:
        base, sep, resto = rota.partition("#")
    base = base.rstrip("/") or "/"

    novo = LEGADO.get(base)
    if novo is None:
        return rota

    # O destino pode já trazer âncora própria (`/revisoes` -> `/agenda#revisoes`).
    # A query/âncora de quem chamou vence, porque é ela que carrega a intenção.
    if sep:
        destino, _, ancora_do_destino = novo.partition("#")
        if sep == "?":
            return f"{destino}?{resto}" + (f"#{ancora_do_destino}" if ancora_do_destino else "")
        return f"{destino}#{resto}"
    return novo
