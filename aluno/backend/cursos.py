"""Catálogo de cursos e a agenda da aula ao vivo de quinta-feira.

Duas coisas moram aqui, as duas como CONSTANTE de produto (mesmo estilo de
`sparks_store.PACKAGES`): o que o frontend mostra vem do servidor, e o
frontend nunca envia preço, data nem status — só um `curso_id` que o backend
reconhece.

**Os cursos estão todos "em breve", e são vendidos assim mesmo.** Cada um
custa `CURSO_CUSTO_SPARKS` Sparks, UMA vez, e o que o aluno compra é **acesso
vitalício**: quando o curso abrir, ele entra sem pagar de novo. É uma
pré-venda declarada, não uma entrega escondida — a tela diz com todas as
letras que as aulas ainda não existem, e quem prefere esperar tem o botão de
graça ("me avise quando abrir") ao lado do de compra.

`status` continua sendo estado declarado e não ausência de dado: a tela
precisa distinguir "comprei e ainda não abriu" de "comprei e posso assistir",
porque a promessa que ela faz muda.

**A aula ao vivo é o oposto:** ela existe, acontece TODA QUINTA e é a única
coisa paga deste módulo (`LIVE_CUSTO_SPARKS`). Quem calcula a data é aqui,
uma vez, no fuso de Brasília — a tela do aluno, o painel do admin e a
cobrança precisam concordar sobre qual edição está sendo vendida, e três
cálculos de "próxima quinta" em três lugares acabariam discordando em alguma
quinta-feira às 20h05.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ZONA_BRASIL = ZoneInfo("America/Sao_Paulo")

EM_BREVE = "em_breve"
DISPONIVEL = "disponivel"


# As ÁREAS do catálogo. Existem para o dia — que é o dia seguinte ao primeiro
# curso dar certo — em que o catálogo tiver Física, Química e Biologia: uma
# lista plana de dezoito cursos não é navegável, e a tela não pode descobrir a
# área pelo título do curso. `ordem` é a ordem visual, e ela não é alfabética
# de propósito: é a ordem de peso no ENEM (ver `prioridade_enem`).
@dataclass(frozen=True)
class Area:
    area_id: str
    titulo: str
    chamada: str
    ordem: int


AREAS: tuple[Area, ...] = (
    Area("matematica", "Matemática", "A conta que a prova assume que você já faz.", 1),
    Area("redacao", "Redação", "As cinco competências, uma de cada vez.", 2),
    Area("natureza", "Ciências da Natureza", "Química e Física do jeito que o ENEM cobra.", 3),
    Area("humanas", "Ciências Humanas", "O mundo de hoje lido com repertório de ontem.", 4),
    Area("linguagens", "Linguagens", "Ler o que está escrito, não o que você supôs.", 5),
    Area("metodo", "Método e prova", "Como o ENEM pensa — e como se estuda para ele.", 6),
)

AREAS_POR_ID: dict[str, Area] = {a.area_id: a for a in AREAS}


# A CAPA de um curso. Duas cores e um glifo, e não um arquivo de imagem.
#
# Um catálogo de vitrine precisa que cada card seja reconhecível de relance —
# sem capa, seis cards viram seis retângulos de texto e o olho não distingue um
# do outro. O que NÃO é preciso para isso é um JPEG por curso: arte por curso
# significa que nenhum curso novo entra no catálogo sem passar por um designer,
# e o objetivo declarado deste catálogo é crescer sem refazer a interface.
#
# Duas cores + um glifo dão identidade suficiente, pesam zero byte, nascem
# nítidas em qualquer tela e são uma linha no dado quando um curso entra.
# O dia em que houver arte de verdade, um campo `capa_url` convive com isto —
# a tela cai neste degradê quando ele faltar, do mesmo jeito que `MentorUSP`
# cai na medalha.
@dataclass(frozen=True)
class Capa:
    de: str        # cor inicial do degradê (hex)
    para: str      # cor final
    glifo: str     # nome do ícone que a tela desenha (ver `lib/capas.js`)


@dataclass(frozen=True)
class Curso:
    curso_id: str
    titulo: str
    chamada: str          # uma linha, o que o curso resolve
    descricao: str        # o parágrafo do card
    modulos: tuple[str, ...]
    carga: str            # duração prometida, em texto
    nivel: str
    capa: Capa
    # Onde o curso mora no catálogo: `area` é o topo da hierarquia
    # (Área → Categoria → Trilha → Curso → Estação) e `categoria` é o
    # agrupamento dentro dela. A tela NUNCA deduz nenhum dos dois do título.
    area: str = "metodo"
    categoria: str = "Geral"
    status: str = EM_BREVE


# Catálogo aprovado 2026-09-15. Ordem da lista = ordem visual na tela.
CURSOS: tuple[Curso, ...] = (
    Curso(
        curso_id="matematica-basica",
        titulo="Curso de Matemática Básica",
        chamada="A base que o ENEM assume que você já tem.",
        descricao=(
            "Fração, porcentagem, regra de três, potência, equação do 1º e 2º grau. "
            "É o curso que resolve o erro que não é de interpretação nem de tempo: "
            "é de conta."
        ),
        modulos=(
            "Operações e frações sem medo",
            "Porcentagem e regra de três no contexto do ENEM",
            "Potências, raízes e notação científica",
            "Equações, sistemas e proporcionalidade",
            "Leitura de gráficos e tabelas",
        ),
        carga="24 aulas",
        nivel="Do zero",
        capa=Capa("#4FD9FF", "#2F6BFF", "calculadora"),
        area="matematica",
        categoria="Fundamentos",
    ),
    Curso(
        curso_id="redacao-0-1000",
        titulo="Redação do 0 ao 1000",
        chamada="As cinco competências, uma de cada vez, até a nota mil.",
        descricao=(
            "Repertório, tese, argumento, coesão e proposta de intervenção — na ordem "
            "em que o corretor lê. Cada aula termina com um trecho seu escrito e "
            "corrigido pelo corretor do Sapiens."
        ),
        modulos=(
            "Como o corretor lê: as 5 competências por dentro",
            "Repertório legitimado que não é decoreba",
            "Tese e projeto de texto em 10 minutos",
            "Parágrafo argumentativo: a fórmula e as saídas dela",
            "Proposta de intervenção completa (os 5 elementos)",
            "Simulados cronometrados com devolutiva",
        ),
        carga="18 aulas + simulados",
        nivel="Todos os níveis",
        capa=Capa("#8B7BFF", "#4B2FBF", "caneta"),
        area="redacao",
        categoria="Redação nota mil",
    ),
    Curso(
        curso_id="hackeando-a-tri",
        titulo="Hackeando a TRI",
        chamada="Duas pessoas acertam 45 questões e tiram notas diferentes. Aqui está o porquê.",
        descricao=(
            "A TRI não conta acerto: ela estima o que você sabe a partir de QUAIS "
            "questões você acertou. Este curso mostra como o modelo pensa, por que "
            "ele pune o acerto por acaso e como usar isso a favor da sua nota."
        ),
        modulos=(
            "O que a TRI mede de verdade (e por que não é quantidade)",
            "Discriminação, dificuldade e acerto ao acaso: os 3 parâmetros",
            "Coerência pedagógica: o padrão de respostas que derruba a nota",
            "Por que acertar as fáceis vale mais do que parece",
            "Quando chutar ajuda, quando chutar te denuncia",
            "Lendo espelhos de notas reais: o que deu e o que não deu certo",
        ),
        carga="12 aulas",
        nivel="Intermediário",
        capa=Capa("#F2A93B", "#B24B2F", "alvo"),
        area="metodo",
        categoria="Como a prova funciona",
    ),
    Curso(
        curso_id="compreensao-interpretacao-texto",
        titulo="Compreensão e Interpretação de Texto",
        chamada="O erro mais caro do ENEM não é de conteúdo. É de leitura.",
        descricao=(
            "Ler o enunciado como ele foi escrito, separar o que o texto diz do que "
            "você supôs, identificar o comando da questão e rastrear a pegadinha. "
            "Vale para as quatro áreas, não só para Linguagens."
        ),
        modulos=(
            "O comando da questão: o que está sendo pedido de verdade",
            "Texto x inferência: onde a leitura apressada erra",
            "Gêneros, tirinhas, charges e infográficos",
            "Figuras de linguagem e efeito de sentido",
            "Interpretação em Humanas, Natureza e Matemática",
        ),
        carga="16 aulas",
        nivel="Todos os níveis",
        capa=Capa("#34D399", "#0E7490", "livro"),
        area="linguagens",
        categoria="Leitura e interpretação",
    ),
    # --- Aprovados em 2026-09-17. Entram em pré-venda como os quatro
    #     primeiros: cobra-se uma vez, o acesso é vitalício, e o selo do card
    #     vira "No ar" sozinho no dia em que a primeira estação de conteúdo
    #     for publicada (ver `cursos_conteudo`). Acrescentar um curso ao
    #     catálogo é acrescentar um item a esta tupla — a tela não muda.
    Curso(
        curso_id="calculos-quimicos",
        titulo="Cálculos Químicos",
        chamada="Mol, estequiometria e concentração — a parte de Química que é conta.",
        descricao=(
            "Massa molar, número de mol, balanceamento, reagente limitante, rendimento "
            "e concentração de soluções. É o bloco de Química que o ENEM cobra com "
            "número na mão, e o que separa quem entende a reação de quem acerta a questão."
        ),
        modulos=(
            "Massa atômica, massa molar e o que o mol realmente conta",
            "Balanceamento e proporção estequiométrica",
            "Reagente limitante, excesso e rendimento",
            "Concentração: g/L, mol/L, diluição e mistura",
            "Gases: as leis que caem, e só elas",
            "Estequiometria dentro de questão de contexto do ENEM",
        ),
        carga="20 aulas",
        nivel="Intermediário",
        capa=Capa("#22D3EE", "#0F766E", "frasco"),
        area="natureza",
        categoria="Química",
    ),
    Curso(
        curso_id="cinematica",
        titulo="Cinemática",
        chamada="Movimento, gráfico e a conta que sai em três linhas.",
        descricao=(
            "Velocidade média, MRU, MRUV, queda livre e lançamentos — com a leitura de "
            "gráfico que o ENEM adora e que derruba mais gente do que a fórmula. Do "
            "conceito à questão resolvida no tempo de prova."
        ),
        modulos=(
            "Referencial, deslocamento e velocidade média",
            "MRU e MRUV: as quatro equações e quando usar cada uma",
            "Gráficos de posição, velocidade e aceleração",
            "Queda livre e lançamento vertical",
            "Lançamento horizontal e oblíquo",
            "Questões de cinemática em contexto, cronometradas",
        ),
        carga="18 aulas",
        nivel="Intermediário",
        capa=Capa("#60A5FA", "#1E3A8A", "foguete"),
        area="natureza",
        categoria="Física",
    ),
    Curso(
        curso_id="atualidades",
        titulo="Atualidades",
        chamada="O repertório que a redação cobra e Humanas assume que você tem.",
        descricao=(
            "Os temas que atravessam a prova inteira — clima, desigualdade, tecnologia, "
            "geopolítica, saúde pública — organizados por eixo, com dado, marco legal e "
            "referência que podem entrar na sua redação sem parecer decoreba."
        ),
        modulos=(
            "Clima e crise ambiental: acordos, metas e o Brasil no meio",
            "Desigualdade, trabalho e renda",
            "Tecnologia, dados pessoais e desinformação",
            "Geopolítica: conflitos e blocos que a prova cita",
            "Saúde pública e o SUS depois da pandemia",
            "Como transformar atualidade em repertório legitimado",
        ),
        carga="14 aulas",
        nivel="Todos os níveis",
        capa=Capa("#FB7185", "#7C2D5E", "globo"),
        area="humanas",
        categoria="Repertório",
    ),
)

CURSOS_POR_ID: dict[str, Curso] = {c.curso_id: c for c in CURSOS}

# Preço único para qualquer curso do catálogo, cobrado UMA vez por curso —
# depois disso o acesso é vitalício. Preço plano e não por curso porque a
# promessa é a mesma nos quatro, e um preço por card seria uma tabela a mais
# para manter sem responder nenhuma pergunta do aluno.
#
# Baixado de 500 para 200 Sparks em 2026-09-17: decisão de produto para dar
# mais peso à prateleira de cursos e e-books dentro do catálogo de Sparks.
CURSO_CUSTO_SPARKS = 200


def listar_cursos() -> list[dict]:
    return [{**asdict(c), "custo_sparks": CURSO_CUSTO_SPARKS} for c in CURSOS]


# ---------------------------------------------------------------------------
# E-BOOKS
# ---------------------------------------------------------------------------
#
# Uma prateleira à parte no catálogo, e não um curso com nome diferente: o que
# se faz com um e-book é BAIXAR e ler (no ônibus, impresso, sem internet), e o
# que se faz com um curso é percorrer estações dentro do app. Empilhar os dois
# na mesma grade faria o aluno clicar num e esperar o outro.
#
# A estrutura é a mesma dos cursos de propósito — dataclass congelada, id
# estável, capa declarada, preço fora do conteúdo — porque o pedido é que a
# prateleira CRESÇA sem mexer na tela: um e-book novo é um item nesta tupla.
#
# `arquivo` é o caminho público do PDF (`public/ebooks/<nome>.pdf`), e ele é
# `None` enquanto o material ainda está sendo produzido. A tela lê esse `None`
# como "em breve" e oferece a lista de aviso, exatamente como faz com um curso
# sem estação publicada — nenhum link quebrado chega ao aluno.

@dataclass(frozen=True)
class Ebook:
    ebook_id: str
    titulo: str
    chamada: str
    descricao: str
    paginas: int
    capa: Capa
    area: str = "metodo"
    arquivo: str | None = None


EBOOKS: tuple[Ebook, ...] = (
    Ebook(
        ebook_id="formulario-matematica",
        titulo="Formulário de Matemática do ENEM",
        chamada="Tudo o que cai, em oito páginas, para imprimir.",
        descricao=(
            "As fórmulas que o ENEM realmente cobra — área, volume, progressões, "
            "trigonometria, estatística e financeira — organizadas por frequência na "
            "prova, não por ordem de livro."
        ),
        paginas=8,
        capa=Capa("#4FD9FF", "#2F6BFF", "calculadora"),
        area="matematica",
    ),
    Ebook(
        ebook_id="repertorio-redacao",
        titulo="30 repertórios para a redação",
        chamada="Trinta referências legitimadas, com a frase pronta para usar.",
        descricao=(
            "Filósofos, leis, dados e obras que cabem em qualquer tema — cada um com o "
            "que é, por que é legitimado e um exemplo de como encaixar no parágrafo sem "
            "parecer enfeite."
        ),
        paginas=24,
        capa=Capa("#8B7BFF", "#4B2FBF", "caneta"),
        area="redacao",
    ),
    Ebook(
        ebook_id="mapa-de-estudo-90-dias",
        titulo="Mapa de estudo dos últimos 90 dias",
        chamada="O que estudar, em que ordem, quando falta pouco.",
        descricao=(
            "Um plano de três meses até a prova, com a ordem de prioridade por peso no "
            "ENEM e o que cortar quando o tempo não fecha. Feito para ser colado na "
            "parede."
        ),
        paginas=12,
        capa=Capa("#F2A93B", "#B24B2F", "calendario"),
        area="metodo",
    ),
)

EBOOKS_POR_ID: dict[str, Ebook] = {e.ebook_id: e for e in EBOOKS}

# Os e-books vêm JUNTO com os cursos no pacote: quem tem `cursos_inclusos`
# tem a prateleira inteira. Não existe preço avulso de e-book, e é decisão de
# produto — uma segunda tabela de preços para um PDF de oito páginas custaria
# mais para manter do que o PDF vale.
EBOOK_CUSTO_SPARKS = 150


def listar_ebooks() -> list[dict]:
    return [
        {**asdict(e), "custo_sparks": EBOOK_CUSTO_SPARKS, "disponivel": bool(e.arquivo)}
        for e in EBOOKS
    ]


def get_ebook(ebook_id: str) -> Ebook | None:
    return EBOOKS_POR_ID.get(ebook_id)


def listar_areas() -> list[dict]:
    """As áreas com os cursos de cada uma, já na ordem visual.

    Montado aqui e não na tela: a hierarquia do catálogo é decisão de produto,
    e um `groupBy` no React seria uma segunda fonte de verdade que diverge no
    dia em que uma área nova entrar sem curso nenhum.
    """
    return [
        {
            **asdict(a),
            "cursos": [c.curso_id for c in CURSOS if c.area == a.area_id],
            "categorias": sorted({c.categoria for c in CURSOS if c.area == a.area_id}),
        }
        for a in sorted(AREAS, key=lambda a: a.ordem)
    ]


def get_curso(curso_id: str) -> Curso | None:
    return CURSOS_POR_ID.get(curso_id)


# ---------------------------------------------------------------------------
# A aula ao vivo de quinta-feira
# ---------------------------------------------------------------------------
#
# Preço fixo em código, como todo preço do produto (ver `sparks_store`): o
# cliente manda "quero entrar", nunca "custa 200".

LIVE_CUSTO_SPARKS = 200

LIVE_DIA_SEMANA = 3          # 0 = segunda ... 3 = quinta
LIVE_HORA = 20               # 20h de Brasília
LIVE_MINUTO = 0
LIVE_DURACAO_MINUTOS = 60

LIVE_TITULO = "Aula ao vivo de quinta"
# O nome passou a ser dito em 2026-09-17 — ver `frontend/src/lib/mentor.js`,
# que tem a cópia usada pelas telas sem sessão (a landing). As duas mudam
# juntas, pelo mesmo acordo já documentado para as datas do ENEM.
LIVE_APRESENTADOR = "Vitor Lara, 1º colocado de Medicina da USP"

# Quanto antes da aula o link fica visível para quem já pagou, e por quanto
# tempo depois do início a edição continua sendo "a de agora". A sala abre
# 30 min antes porque aluno chega cedo; a edição só vira a seguinte quando a
# atual termina, senão quem paga às 20h30 de quinta compraria a da semana que
# vem sem perceber.
LIVE_ABRE_MINUTOS_ANTES = 30


def _agora_brasil(agora: datetime | None = None) -> datetime:
    if agora is None:
        return datetime.now(ZONA_BRASIL)
    if agora.tzinfo is None:
        return agora.replace(tzinfo=ZONA_BRASIL)
    return agora.astimezone(ZONA_BRASIL)


def proxima_live(agora: datetime | None = None) -> dict:
    """A edição que está sendo vendida AGORA.

    Durante a aula (e nos 30 min de sala aberta antes dela), a edição corrente
    continua sendo a de hoje — é justamente quando mais gente compra. Só
    depois do fim ela passa a ser a da quinta seguinte.

    `edicao` é a chave de tudo (`AAAA-MM-DD` da quinta): é ela que identifica
    a compra do aluno, o link publicado pelo admin e a lista de inscritos.
    """
    ref = _agora_brasil(agora)
    dias = (LIVE_DIA_SEMANA - ref.weekday()) % 7
    inicio = (ref + timedelta(days=dias)).replace(
        hour=LIVE_HORA, minute=LIVE_MINUTO, second=0, microsecond=0
    )
    fim = inicio + timedelta(minutes=LIVE_DURACAO_MINUTOS)
    # Hoje é quinta e a aula já acabou -> a próxima é a da semana que vem.
    if ref > fim:
        inicio += timedelta(days=7)
        fim = inicio + timedelta(minutes=LIVE_DURACAO_MINUTOS)

    abre = inicio - timedelta(minutes=LIVE_ABRE_MINUTOS_ANTES)
    return {
        "edicao": inicio.date().isoformat(),
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "sala_abre": abre.isoformat(),
        "duracao_minutos": LIVE_DURACAO_MINUTOS,
        "custo_sparks": LIVE_CUSTO_SPARKS,
        "titulo": LIVE_TITULO,
        "apresentador": LIVE_APRESENTADOR,
        "ao_vivo_agora": abre <= ref <= fim,
        "segundos_para_comecar": max(0, int((inicio - ref).total_seconds())),
    }
