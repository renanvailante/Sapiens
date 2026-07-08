"""Parser + seed helpers for ENEM answer keys pasted from INEP.

The paste typically looks like:

    QUESTÃO GABARITO
    INGLÊS ESPANHOL
    1 D B
    2 D A
    3 D D
    ...
    6 C
    7 E
    ...

Rules:
- Lines starting with a number followed by 1 or 2 letters (A-E or *) are parsed.
- Header lines and blank lines are ignored.
- If a line has 2 letters, first is English, second is Spanish.
- If only 1 letter, both languages share it (common for non-language questions).
- Duplicate numbers keep the last occurrence.
"""
from __future__ import annotations

import re

from models import AnswerKey, AnswerKeyItem, Exam

LINE_RE = re.compile(
    r"^\s*(\d{1,3})\s+([A-Ea-e\*])(?:\s+([A-Ea-e\*]))?\s*$"
)


def parse_answer_key_text(raw: str) -> tuple[list[AnswerKeyItem], list[AnswerKeyItem]]:
    """Return (english_answers, spanish_answers)."""
    english: dict[int, str] = {}
    spanish: dict[int, str] = {}
    for line in raw.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        num = int(m.group(1))
        a = m.group(2).upper()
        b = (m.group(3) or "").upper()
        if b:
            english[num] = a
            spanish[num] = b
        else:
            # shared answer for both languages
            english[num] = a
            spanish[num] = a
    en_items = [AnswerKeyItem(number=n, letter=english[n]) for n in sorted(english)]
    es_items = [AnswerKeyItem(number=n, letter=spanish[n]) for n in sorted(spanish)]
    return en_items, es_items


async def import_pasted_key(db, provider: str, year: int, day: int, color: str, raw_text: str) -> dict:
    en_items, es_items = parse_answer_key_text(raw_text)
    if not en_items and not es_items:
        raise ValueError("Nenhuma linha reconhecida no gabarito.")

    diverge = any(en_items[i].letter != es_items[i].letter for i in range(min(len(en_items), len(es_items))))
    has_english = len(en_items) > 0
    has_spanish = len(es_items) > 0 and diverge  # only mark as separate if actually differs

    total = max(len(en_items), len(es_items))
    title = f"ENEM {year} · Dia {day} · {color}"

    # Upsert exam by (provider, year, day, color)
    existing = await db.exams.find_one(
        {"provider": provider, "year": year, "day": day, "color": color},
        {"_id": 0},
    )
    if existing:
        exam_id = existing["exam_id"]
        await db.exams.update_one(
            {"exam_id": exam_id},
            {"$set": {"title": title, "total_questions": total,
                      "has_english": has_english, "has_spanish": has_spanish}},
        )
        await db.answer_keys.delete_many({"exam_id": exam_id})
    else:
        exam = Exam(
            provider=provider, year=year, day=day, color=color,
            title=title, total_questions=total,
            has_english=has_english, has_spanish=has_spanish,
        )
        await db.exams.insert_one(exam.model_dump())
        exam_id = exam.exam_id

    if en_items:
        await db.answer_keys.insert_one(
            AnswerKey(exam_id=exam_id, language="english", answers=en_items).model_dump()
        )
    if es_items and has_spanish:
        await db.answer_keys.insert_one(
            AnswerKey(exam_id=exam_id, language="spanish", answers=es_items).model_dump()
        )
    return {"exam_id": exam_id, "total": total, "english": has_english, "spanish": has_spanish}


# ---------- Sample seed (real-looking ENEM 2023 Dia 1 Azul, for demo) ----------

SAMPLE_ENEM_2023_D1_AZUL = """QUESTÃO GABARITO
INGLÊS ESPANHOL
1 D B
2 E C
3 A A
4 C D
5 B B
6 D
7 A
8 C
9 E
10 B
11 D
12 A
13 C
14 E
15 B
16 D
17 A
18 C
19 E
20 B
21 D
22 A
23 C
24 E
25 B
26 D
27 A
28 C
29 E
30 B
31 D
32 A
33 C
34 E
35 B
36 D
37 A
38 C
39 E
40 B
41 D
42 A
43 C
44 E
45 B
46 C
47 D
48 A
49 B
50 E
51 C
52 D
53 A
54 B
55 E
56 C
57 D
58 A
59 B
60 E
61 C
62 D
63 A
64 B
65 E
66 C
67 D
68 A
69 B
70 E
71 C
72 D
73 A
74 B
75 E
76 C
77 D
78 A
79 B
80 E
81 C
82 D
83 A
84 B
85 E
86 C
87 D
88 A
89 B
90 E
"""

SAMPLE_ENEM_2023_D2_AZUL = """QUESTÃO GABARITO
91 A
92 B
93 C
94 D
95 E
96 A
97 B
98 C
99 D
100 E
101 A
102 B
103 C
104 D
105 E
106 A
107 B
108 C
109 D
110 E
111 A
112 B
113 C
114 D
115 E
116 A
117 B
118 C
119 D
120 E
121 A
122 B
123 C
124 D
125 E
126 A
127 B
128 C
129 D
130 E
131 A
132 B
133 C
134 D
135 E
136 C
137 D
138 A
139 B
140 E
141 C
142 D
143 A
144 B
145 E
146 C
147 D
148 A
149 B
150 E
151 C
152 D
153 A
154 B
155 E
156 C
157 D
158 A
159 B
160 E
161 C
162 D
163 A
164 B
165 E
166 C
167 D
168 A
169 B
170 E
171 C
172 D
173 A
174 B
175 E
176 C
177 D
178 A
179 B
180 E
"""


SEEDS = [
    (2023, 1, "Azul", SAMPLE_ENEM_2023_D1_AZUL),
    (2023, 2, "Azul", SAMPLE_ENEM_2023_D2_AZUL),
]


async def migrate_and_seed(db):
    """Run once: drop old collections tied to prior schema, seed sample keys."""
    marker = await db.settings.find_one({"key": "schema_version"}, {"_id": 0})
    version = marker.get("value", 0) if marker else 0
    if version >= 2:
        return
    # Wipe legacy data (schema change)
    await db.exams.drop()
    await db.questions.drop()
    await db.analyses.drop()
    await db.answer_keys.drop()
    # Seed sample answer keys
    for year, day, color, raw in SEEDS:
        await import_pasted_key(db, "ENEM", year, day, color, raw)
    await db.settings.update_one(
        {"key": "schema_version"},
        {"$set": {"key": "schema_version", "value": 2}},
        upsert=True,
    )
