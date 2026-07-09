"""Placeholder seed data for the learning feed.

These are DEMO items only. They exercise every content_type and payload
shape supported by the schema. Real content will replace them via the
admin panel or ingestion pipeline.
"""
from __future__ import annotations

from feed_models import FeedItem


SAMPLE_ITEMS: list[dict] = [
    {
        "content_type": "explanation",
        "sequence_order": 1,
        "question_data": {
            "prompt": "Bem-vindo ao Feed Sapiens.",
            "subtitle": "Deslize para cima para aprender.",
        },
        "explanation_data": {
            "text": "Cada card é uma unidade de aprendizagem. Você lê, responde, revisa e segue. Sem propaganda. Sem distração.",
        },
        "background_theme": "slate",
    },
    {
        "content_type": "question",
        "sequence_order": 2,
        "question_data": {
            "prompt": "Se 3 xícaras de farinha fazem 12 biscoitos, quantas xícaras são necessárias para 20 biscoitos?",
            "subject_hint": "Proporcionalidade",
        },
        "answer_options": [
            {"key": "A", "label": "4", "is_correct": False},
            {"key": "B", "label": "5", "is_correct": True},
            {"key": "C", "label": "6", "is_correct": False},
            {"key": "D", "label": "7", "is_correct": False},
        ],
        "explanation_data": {
            "text": "12 biscoitos ↔ 3 xícaras. Dividimos: 1 biscoito precisa de 3/12 = 0,25 xícara. Multiplicamos por 20 → 5 xícaras.",
        },
        "background_theme": "violet",
    },
    {
        "content_type": "flashcard",
        "sequence_order": 3,
        "question_data": {"prompt": "Qual a fórmula do trabalho de uma força constante?"},
        "explanation_data": {"text": "W = F · d · cos(θ)", "subtitle": "Onde θ é o ângulo entre força e deslocamento."},
        "background_theme": "emerald",
    },
    {
        "content_type": "question",
        "sequence_order": 4,
        "question_data": {
            "prompt": "The word 'nevertheless' can be replaced by:",
            "subject_hint": "Inglês · Coesão textual",
        },
        "answer_options": [
            {"key": "A", "label": "however", "is_correct": True},
            {"key": "B", "label": "because", "is_correct": False},
            {"key": "C", "label": "therefore", "is_correct": False},
            {"key": "D", "label": "meanwhile", "is_correct": False},
        ],
        "explanation_data": {"text": "‘Nevertheless’ e ‘however’ marcam contraste — ambas equivalentes a ‘entretanto’."},
        "background_theme": "ocean",
    },
    {
        "content_type": "diagram",
        "sequence_order": 5,
        "question_data": {"prompt": "Ciclo celular"},
        "multimedia_assets": [{"type": "image", "url": "", "caption": "G1 → S → G2 → M"}],
        "explanation_data": {"text": "A fase S é onde ocorre a duplicação do DNA. G2 prepara a mitose."},
        "background_theme": "amber",
    },
    {
        "content_type": "question",
        "sequence_order": 6,
        "question_data": {"prompt": "Um carro percorre 240 km em 3h. Qual sua velocidade média?"},
        "answer_options": [
            {"key": "A", "label": "60 km/h", "is_correct": False},
            {"key": "B", "label": "70 km/h", "is_correct": False},
            {"key": "C", "label": "80 km/h", "is_correct": True},
            {"key": "D", "label": "90 km/h", "is_correct": False},
        ],
        "explanation_data": {"text": "v = Δs/Δt = 240/3 = 80 km/h."},
        "background_theme": "rose",
    },
    {
        "content_type": "flashcard",
        "sequence_order": 7,
        "question_data": {"prompt": "O que é sinapse?"},
        "explanation_data": {
            "text": "Ponto de comunicação entre dois neurônios ou entre um neurônio e uma célula efetora — via neurotransmissores químicos ou impulsos elétricos.",
        },
        "background_theme": "slate",
    },
    {
        "content_type": "question",
        "sequence_order": 8,
        "question_data": {
            "prompt": "Em Aa × Aa, qual a proporção esperada de descendentes homozigotos recessivos (aa)?",
        },
        "answer_options": [
            {"key": "A", "label": "1/2", "is_correct": False},
            {"key": "B", "label": "1/4", "is_correct": True},
            {"key": "C", "label": "3/4", "is_correct": False},
            {"key": "D", "label": "1/8", "is_correct": False},
        ],
        "explanation_data": {"text": "O quadrado de Punnett gera AA:2Aa:aa (1:2:1). aa = 1/4."},
        "background_theme": "emerald",
    },
    {
        "content_type": "explanation",
        "sequence_order": 9,
        "question_data": {"prompt": "Semana de Arte Moderna de 1922"},
        "explanation_data": {
            "text": "Realizada em São Paulo, marcou a ruptura com o academicismo europeu e a valorização de uma identidade brasileira. Nomes-chave: Mário de Andrade, Oswald de Andrade, Anita Malfatti, Tarsila do Amaral.",
        },
        "background_theme": "violet",
    },
    {
        "content_type": "question",
        "sequence_order": 10,
        "question_data": {"prompt": "Resolva: 3x + 12 = 5x − 4"},
        "answer_options": [
            {"key": "A", "label": "x = 4", "is_correct": False},
            {"key": "B", "label": "x = 6", "is_correct": False},
            {"key": "C", "label": "x = 8", "is_correct": True},
            {"key": "D", "label": "x = 10", "is_correct": False},
        ],
        "explanation_data": {"text": "3x + 12 = 5x − 4 → 16 = 2x → x = 8."},
        "background_theme": "ocean",
    },
    {
        "content_type": "flashcard",
        "sequence_order": 11,
        "question_data": {"prompt": "Definição de entropia"},
        "explanation_data": {
            "text": "Medida da desordem de um sistema. Em processos espontâneos isolados, a entropia sempre aumenta (2ª Lei da Termodinâmica).",
        },
        "background_theme": "amber",
    },
    {
        "content_type": "question",
        "sequence_order": 12,
        "question_data": {"prompt": "A média das notas de 5 alunos é 7. Se um novo aluno com nota 4 for incluído, qual será a nova média?"},
        "answer_options": [
            {"key": "A", "label": "5,5", "is_correct": False},
            {"key": "B", "label": "6,0", "is_correct": False},
            {"key": "C", "label": "6,3", "is_correct": False},
            {"key": "D", "label": "6,5", "is_correct": True},
        ],
        "explanation_data": {"text": "Soma antiga: 5 × 7 = 35. Nova soma: 39. Nova média: 39/6 = 6,5."},
        "background_theme": "rose",
    },
    {
        "content_type": "explanation",
        "sequence_order": 13,
        "question_data": {"prompt": "Como o feed evolui"},
        "explanation_data": {
            "text": "Cada interação sua vira dado. Com o tempo, o feed aprende quais formatos e temas fazem sua compreensão crescer — e passa a priorizá-los. O motor cognitivo será conectado em breve.",
        },
        "background_theme": "slate",
    },
    {
        "content_type": "question",
        "sequence_order": 14,
        "question_data": {"prompt": "Em H₂ + 1/2 O₂ → H₂O, quantos mols de H₂O saem de 4 mols de H₂?"},
        "answer_options": [
            {"key": "A", "label": "1", "is_correct": False},
            {"key": "B", "label": "2", "is_correct": False},
            {"key": "C", "label": "4", "is_correct": True},
            {"key": "D", "label": "8", "is_correct": False},
        ],
        "explanation_data": {"text": "Proporção 1:1 entre H₂ e H₂O. Logo 4 mols de H₂ → 4 mols de H₂O."},
        "background_theme": "emerald",
    },
    {
        "content_type": "flashcard",
        "sequence_order": 15,
        "question_data": {"prompt": "Metrópole vs megalópole"},
        "explanation_data": {
            "text": "Metrópole é uma cidade que polariza serviços e economia sobre outras. Megalópole é a conurbação de duas ou mais metrópoles em um mesmo tecido urbano — ex.: eixo Rio–São Paulo.",
        },
        "background_theme": "violet",
    },
]


async def seed_feed(db):
    marker = await db.settings.find_one({"key": "feed_seed_version"}, {"_id": 0})
    if marker and marker.get("value", 0) >= 1:
        return
    await db.feed_items.delete_many({})
    for it in SAMPLE_ITEMS:
        item = FeedItem(**it)
        await db.feed_items.insert_one(item.model_dump())
    await db.settings.update_one(
        {"key": "feed_seed_version"},
        {"$set": {"key": "feed_seed_version", "value": 1}},
        upsert=True,
    )
