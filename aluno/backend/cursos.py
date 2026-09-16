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


@dataclass(frozen=True)
class Curso:
    curso_id: str
    titulo: str
    chamada: str          # uma linha, o que o curso resolve
    descricao: str        # o parágrafo do card
    modulos: tuple[str, ...]
    carga: str            # duração prometida, em texto
    nivel: str
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
    ),
)

CURSOS_POR_ID: dict[str, Curso] = {c.curso_id: c for c in CURSOS}

# Preço único para qualquer curso do catálogo, cobrado UMA vez por curso —
# depois disso o acesso é vitalício. Preço plano e não por curso porque a
# promessa é a mesma nos quatro, e um preço por card seria uma tabela a mais
# para manter sem responder nenhuma pergunta do aluno.
CURSO_CUSTO_SPARKS = 500


def listar_cursos() -> list[dict]:
    return [{**asdict(c), "custo_sparks": CURSO_CUSTO_SPARKS} for c in CURSOS]


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
LIVE_DURACAO_MINUTOS = 90

LIVE_TITULO = "Aula ao vivo de quinta"
LIVE_APRESENTADOR = "1º colocado de Medicina da USP"

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
