"""Seed data for ENEM exams (2022-2024). Curated representative questions with rich tags.

Each exam has ~10 questions across areas, enough to demonstrate diagnostic flows end-to-end.
The database architecture supports any provider (ENEM/FUVEST/etc.) and any year.
"""
from __future__ import annotations

from models import Alternative, Exam, Question

# Compact tag builders
def _tags(**kwargs):
    base = {
        "interpretacao_textual": False,
        "interpretacao_grafico": False,
        "interpretacao_tabela": False,
        "visualizacao_espacial": False,
        "algebra": False,
        "geometria": False,
        "funcoes": False,
        "estatistica": False,
        "probabilidade": False,
        "proporcionalidade": False,
        "modelagem": False,
        "raciocinio_logico": False,
        "pegadinha": False,
        "tempo_medio_segundos": 180,
        "carga_cognitiva": 5,
        "complexidade_textual": 5,
        "complexidade_matematica": 5,
        "nivel_bloom": "aplicar",
        "probabilidade_acerto": 0.5,
    }
    base.update(kwargs)
    return base


def _q(number, area, subject, topic, statement, alts, correct, tags, difficulty="medio", competency=None):
    return {
        "number": number,
        "area": area,
        "subject": subject,
        "topic": topic,
        "statement": statement,
        "alternatives": [Alternative(letter=ltr, text=t).model_dump() for ltr, t in alts],
        "correct_answer": correct,
        "tags": tags,
        "difficulty": difficulty,
        "competency": competency,
    }


def _make_bank(area_offset):
    """Generate a rich sample bank spanning all areas & tag combinations."""
    # 12 questions per exam covering diverse cognitive tags
    return [
        _q(1, "MT", "Matemática", "Proporcionalidade",
           "Uma receita usa 3 xícaras de farinha para 6 biscoitos. Quantas xícaras são necessárias para 20 biscoitos?",
           [("A", "8"), ("B", "9"), ("C", "10"), ("D", "12"), ("E", "15")],
           "C", _tags(proporcionalidade=True, modelagem=True, complexidade_matematica=3, tipo_raciocinio="proporcional", tema="Razão e proporção"),
           difficulty="facil"),
        _q(2, "MT", "Matemática", "Álgebra - Equações",
           "Um valor x satisfaz 3x + 12 = 5x - 4. Quanto vale x?",
           [("A", "4"), ("B", "6"), ("C", "8"), ("D", "10"), ("E", "12")],
           "C", _tags(algebra=True, complexidade_matematica=4, numero_etapas=3, tipo_erro_comum="troca de sinal")),
        _q(3, "MT", "Matemática", "Funções",
           "O lucro L(x) de uma empresa em função do número x de unidades vendidas é L(x) = 20x - 200. Quantas unidades são necessárias para o lucro atingir R$ 1000?",
           [("A", "40"), ("B", "50"), ("C", "60"), ("D", "70"), ("E", "80")],
           "C", _tags(algebra=True, funcoes=True, modelagem=True, complexidade_matematica=5, numero_etapas=3)),
        _q(4, "MT", "Matemática", "Estatística",
           "A média das notas de 5 alunos é 7. Se um novo aluno com nota 4 for incluído, qual será a nova média?",
           [("A", "5,5"), ("B", "6,0"), ("C", "6,3"), ("D", "6,5"), ("E", "6,8")],
           "D", _tags(estatistica=True, complexidade_matematica=4, tipo_erro_comum="dividir pelo n antigo", pegadinha=True)),
        _q(5, "MT", "Matemática", "Geometria",
           "Um terreno retangular tem 20m por 15m. Qual sua área em m²?",
           [("A", "70"), ("B", "150"), ("C", "200"), ("D", "300"), ("E", "350")],
           "D", _tags(geometria=True, complexidade_matematica=2), difficulty="facil"),
        _q(6, "CN", "Física", "Cinemática",
           "Um carro percorre 240 km em 3 horas. Sua velocidade média em km/h é:",
           [("A", "60"), ("B", "70"), ("C", "80"), ("D", "90"), ("E", "100")],
           "C", _tags(proporcionalidade=True, conversao_unidades=True, complexidade_matematica=3, tema="Velocidade média"), difficulty="facil"),
        _q(7, "CN", "Química", "Estequiometria",
           "Na reação 2H₂ + O₂ → 2H₂O, quantos mols de água são formados a partir de 4 mols de H₂?",
           [("A", "1"), ("B", "2"), ("C", "3"), ("D", "4"), ("E", "8")],
           "D", _tags(proporcionalidade=True, conhecimento_conceitual=True, complexidade_matematica=4, tema="Reações químicas")),
        _q(8, "CN", "Biologia", "Genética",
           "Em cruzamento entre dois heterozigotos (Aa x Aa), qual a proporção esperada de descendentes homozigotos recessivos (aa)?",
           [("A", "1/2"), ("B", "1/3"), ("C", "1/4"), ("D", "3/4"), ("E", "1/8")],
           "C", _tags(probabilidade=True, conhecimento_conceitual=True, complexidade_matematica=3)),
        _q(9, "CH", "História", "República Brasileira",
           "A Semana de Arte Moderna de 1922, realizada em São Paulo, teve como principal objetivo:",
           [("A", "Consolidar o academicismo europeu no Brasil"),
            ("B", "Romper com padrões estéticos tradicionais e valorizar identidade nacional"),
            ("C", "Fundar um partido político"),
            ("D", "Criar universidades públicas"),
            ("E", "Difundir o realismo francês")],
           "B", _tags(interpretacao_textual=True, memorizacao=True, conhecimento_factual=True, complexidade_textual=6)),
        _q(10, "CH", "Geografia", "Urbanização",
            "O processo de metropolização no Brasil está mais fortemente associado a qual fenômeno?",
            [("A", "Êxodo rural intenso no século XX"),
             ("B", "Colonização portuguesa do século XVI"),
             ("C", "Chegada da Família Real em 1808"),
             ("D", "Descoberta do ouro em Minas Gerais"),
             ("E", "Descentralização produtiva do século XXI")],
            "A", _tags(interpretacao_textual=True, conhecimento_conceitual=True, complexidade_textual=7)),
        _q(11, "LC", "Português", "Interpretação de texto",
            "\"Ler é decodificar o mundo\". Nessa afirmação, a palavra 'decodificar' é usada em sentido:",
            [("A", "denotativo"), ("B", "conotativo"), ("C", "irônico"), ("D", "hiperbólico"), ("E", "eufemístico")],
            "B", _tags(interpretacao_textual=True, complexidade_textual=6, tipo_raciocinio="verbal")),
        _q(12, "LC", "Inglês", "Compreensão",
            "The phrase 'time flies' most likely means:",
            [("A", "time is expensive"),
             ("B", "time passes very quickly"),
             ("C", "birds are fast"),
             ("D", "clocks are broken"),
             ("E", "airplanes are late")],
            "B", _tags(interpretacao_textual=True, memorizacao=True, complexidade_textual=4), difficulty="facil"),
    ]


def build_seed_exams() -> list[tuple[Exam, list[Question]]]:
    """Return list of (exam, questions) tuples for ENEM 2022, 2023, 2024."""
    exams: list[tuple[Exam, list[Question]]] = []
    for year in (2022, 2023, 2024):
        for color, area in (
            ("Azul", "Dia 1 - LC + CH"),
            ("Amarela", "Dia 2 - MT + CN"),
        ):
            exam = Exam(
                provider="ENEM",
                year=year,
                color=color,
                area=area,
                title=f"ENEM {year} • {color}",
                total_questions=12,
            )
            questions = []
            for qraw in _make_bank(area_offset=0):
                q = Question(
                    exam_id=exam.exam_id,
                    number=qraw["number"],
                    area=qraw["area"],
                    subject=qraw["subject"],
                    topic=qraw["topic"],
                    statement=qraw["statement"],
                    alternatives=[Alternative(**a) for a in qraw["alternatives"]],
                    correct_answer=qraw["correct_answer"],
                    tags=qraw["tags"],
                    difficulty=qraw["difficulty"],
                    competency=qraw.get("competency"),
                )
                questions.append(q)
            exams.append((exam, questions))
    return exams


async def seed_if_empty(db):
    count = await db.exams.count_documents({})
    if count > 0:
        return
    for exam, questions in build_seed_exams():
        await db.exams.insert_one(exam.model_dump())
        for q in questions:
            await db.questions.insert_one(q.model_dump())
