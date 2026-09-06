#!/usr/bin/env python3
"""Converte os 56 arquivos-fonte HAB-01..HAB-56 (markdown) num JSON único.

Regra-chave de parsing: os alternativas de RESPOSTA são sempre o bloco
contíguo de linhas `LETRA) texto` que vem IMEDIATAMENTE antes de `Gabarito:`.
Isso distingue as alternativas reais de qualquer lista rotulada A)/B)/C)
que apareça DENTRO do enunciado como dado do problema (ex.: HAB-01, onde a
lista de temperaturas A-D é dado, não resposta).

Não altera conteúdo: só re-estrutura. Falha alto (assert) em qualquer
inconsistência em vez de silenciosamente aceitar.

Uso: python3 gerar_banco_treino_habilidades.py <pasta com os 56 .md> \
    pipeline/docs/treino-habilidades/banco_treino_habilidades_v1.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SRC_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT_PATH = Path(sys.argv[2] if len(sys.argv) > 2 else "banco_treino_habilidades_v1.json")

DIFICULDADE_MAP = {
    "FÁCIL": "FACIL",
    "MÉDIO-FÁCIL": "MEDIO_FACIL",
    "MÉDIO": "MEDIO",
    "DIFÍCIL": "DIFICIL",
}

RE_QUESTAO = re.compile(r"^QUEST[ÃA]O\s+(\d+)\s*\|\s*(.+?)\s*$")
RE_GABARITO = re.compile(r"^Gabarito:\s*([A-E](?:\s*(?:,|e)\s*[A-E])*)\s*$")
RE_ALT = re.compile(r"^([A-E])\)\s*(.*?)\s*$")
RE_ELUCIDACAO = re.compile(r"^Elucida[cç][ãa]o:\s*(.+)$", re.IGNORECASE)
RE_PALAVRAS = re.compile(r"^Palavras-chave:\s*(.+)$", re.IGNORECASE)
RE_CONTEUDOS = re.compile(r"^Conte[úu]dos escolares:\s*(.+)$", re.IGNORECASE)
RE_PREREQ = re.compile(r"^Pr[ée]-requisitos:\s*(.+)$", re.IGNORECASE)
RE_TABLE_ROW = re.compile(r"^\|?.*\|.*$")
RE_TABLE_SEP = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def _split_lista(texto: str) -> list[str]:
    itens = [p.strip().rstrip(".") for p in texto.split(";")]
    return [p for p in itens if p]


def _strip_bold(s: str) -> str:
    return re.sub(r"\*\*(.*?)\*\*", r"\1", s).strip()


def _split_row(line: str) -> list[str]:
    cells = line.split("|")
    # remove UMA célula vazia externa em cada ponta, se veio de pipe de borda
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return [_strip_bold(c) for c in cells]


def _extrair_tabela(corpo_lines: list[str]) -> tuple[list[str], dict | None, list[str]]:
    """Acha a primeira tabela markdown em `corpo_lines`. Devolve
    (linhas_antes, tabela_ou_None, linhas_depois)."""
    for i in range(len(corpo_lines) - 1):
        linha, prox = corpo_lines[i], corpo_lines[i + 1]
        if "|" in linha and RE_TABLE_SEP.match(prox):
            headers = _split_row(linha)
            j = i + 2
            rows = []
            while j < len(corpo_lines) and corpo_lines[j].strip() and "|" in corpo_lines[j]:
                rows.append(_split_row(corpo_lines[j]))
                j += 1
            for r in rows:
                assert len(r) == len(headers), (
                    f"linha de tabela com {len(r)} colunas, cabeçalho tem {len(headers)}: {r} vs {headers}"
                )
            return corpo_lines[:i], {"headers": headers, "rows": rows}, corpo_lines[j:]
    return corpo_lines, None, []


def _join(lines: list[str]) -> str:
    # remove blanks nas pontas, preserva quebras internas (ex.: listas A)/B)
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_arquivo(path: Path) -> dict:
    linhas_raw = path.read_text(encoding="utf-8").splitlines()
    linhas = [l.rstrip() for l in linhas_raw]

    titulo_idx = next(i for i, l in enumerate(linhas) if l.strip())
    titulo = linhas[titulo_idx].strip()
    hab_id, nome = [p.strip() for p in titulo.split("|", 1)]
    assert re.match(r"^HAB-\d\d$", hab_id), f"hab_id inesperado: {hab_id!r} em {path.name}"

    headers_idx = [i for i, l in enumerate(linhas) if RE_QUESTAO.match(l)]
    assert headers_idx, f"nenhuma QUESTÃO encontrada em {path.name}"

    questoes = []
    for k, h_idx in enumerate(headers_idx):
        m = RE_QUESTAO.match(linhas[h_idx])
        indice = int(m.group(1))
        dificuldade_raw = m.group(2).strip()
        assert dificuldade_raw in DIFICULDADE_MAP, f"dificuldade desconhecida {dificuldade_raw!r} em {path.name}"

        fim = headers_idx[k + 1] if k + 1 < len(headers_idx) else len(linhas)
        bloco = linhas[h_idx + 1 : fim]

        gab_idx = next((i for i, l in enumerate(bloco) if RE_GABARITO.match(l)), None)
        assert gab_idx is not None, f"Gabarito ausente em {path.name} questão {indice}"
        gabarito_raw = RE_GABARITO.match(bloco[gab_idx]).group(1)
        gabarito = sorted(set(re.findall(r"[A-E]", gabarito_raw)))
        if len(gabarito) > 1:
            print(f"AVISO: gabarito com {len(gabarito)} letras ({gabarito}) em {path.name} questão {indice} — conteúdo original preservado", file=sys.stderr)

        pre_gabarito = bloco[:gab_idx]
        pos_gabarito = bloco[gab_idx + 1 :]

        # alternativas: bloco contíguo de linhas LETRA) no fim de pre_gabarito
        while pre_gabarito and not pre_gabarito[-1].strip():
            pre_gabarito.pop()
        alt_rev = []
        while pre_gabarito and RE_ALT.match(pre_gabarito[-1]):
            alt_rev.append(pre_gabarito.pop())
        assert alt_rev, f"alternativas não encontradas em {path.name} questão {indice}"
        alternativas = []
        for l in reversed(alt_rev):
            am = RE_ALT.match(l)
            alternativas.append({"letra": am.group(1), "texto": am.group(2).strip()})
        letras = {a["letra"] for a in alternativas}
        assert len(alternativas) in (4, 5), f"{len(alternativas)} alternativas em {path.name} questão {indice}"
        assert set(gabarito) <= letras, f"gabarito {gabarito} fora das alternativas {letras} em {path.name} questão {indice}"

        antes, tabela, depois = _extrair_tabela(pre_gabarito)
        enunciado_antes = _join(antes)
        enunciado_depois = _join(depois)
        assert enunciado_antes, f"enunciado vazio em {path.name} questão {indice}"

        campos = {"elucidacao": None, "palavras_chave": [], "conteudos_escolares": [], "pre_requisitos": []}
        for l in pos_gabarito:
            if (mm := RE_ELUCIDACAO.match(l)):
                campos["elucidacao"] = mm.group(1).strip()
            elif (mm := RE_PALAVRAS.match(l)):
                campos["palavras_chave"] = _split_lista(mm.group(1))
            elif (mm := RE_CONTEUDOS.match(l)):
                campos["conteudos_escolares"] = _split_lista(mm.group(1))
            elif (mm := RE_PREREQ.match(l)):
                campos["pre_requisitos"] = _split_lista(mm.group(1))
        assert campos["elucidacao"], f"elucidação ausente em {path.name} questão {indice}"
        assert campos["palavras_chave"], f"palavras-chave ausentes em {path.name} questão {indice}"

        questoes.append({
            "indice": indice,
            "dificuldade": DIFICULDADE_MAP[dificuldade_raw],
            "enunciado_antes": enunciado_antes,
            "tabela": tabela,
            "enunciado_depois": enunciado_depois,
            "alternativas": alternativas,
            "gabarito": gabarito,
            **campos,
        })

    return {"hab_id": hab_id, "nome": nome, "questoes": questoes}


def main() -> None:
    arquivos = sorted(SRC_DIR.glob("HAB-*.md"))
    assert len(arquivos) == 56, f"esperado 56 arquivos, achei {len(arquivos)} em {SRC_DIR}"

    habilidades = [parse_arquivo(p) for p in arquivos]
    habilidades.sort(key=lambda h: int(h["hab_id"].split("-")[1]))

    ids = [h["hab_id"] for h in habilidades]
    esperado = [f"HAB-{i:02d}" for i in range(1, 57)]
    assert ids == esperado, f"conjunto de HABs inesperado: {set(esperado) - set(ids)} faltando, {set(ids) - set(esperado)} sobrando"

    contagens = {h["hab_id"]: len(h["questoes"]) for h in habilidades}
    anomalos = {k: v for k, v in contagens.items() if v != 5}
    print(f"HABs com contagem != 5 questões: {anomalos}", file=sys.stderr)

    total_tabelas = sum(1 for h in habilidades for q in h["questoes"] if q["tabela"])
    print(f"Total de questões com tabela: {total_tabelas}", file=sys.stderr)

    banco = {"versao": "1.0", "habilidades": habilidades}
    OUT_PATH.write_text(json.dumps(banco, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {OUT_PATH} ({sum(contagens.values())} questões em {len(habilidades)} habilidades)", file=sys.stderr)


if __name__ == "__main__":
    main()
