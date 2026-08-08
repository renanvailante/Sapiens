"""Extrai JSON embutido em backticks no arquivo MD da Ontologia Sapiens v1.4.

Uso:
    python scripts/extract_ontology_json.py
Gera:
    docs/ontology/ontology_v1.4.json
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs/ontology/04 Ontologia Cognitiva Sapiens \u2014 v1.4 JSON.md"
DST = ROOT / "docs/ontology/ontology_v1.4.json"


def extract() -> dict:
    raw = SRC.read_text(encoding="utf-8")
    # Cada linha JSON está envolta em backticks: `...`
    lines = []
    for ln in raw.splitlines():
        s = ln.strip()
        if s.startswith("`") and s.endswith("`") and len(s) >= 2:
            lines.append(s[1:-1])
    text = "\n".join(lines)
    # Sanidade: começar em '{' e terminar em '}'
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1:
        raise RuntimeError("Delimitadores JSON não encontrados.")
    text = text[i : j + 1]
    return json.loads(text)


def main() -> None:
    data = extract()
    DST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Resumo
    def count(key):
        return len(data.get(key, [])) if isinstance(data.get(key), list) else 0

    print(f"OK -> {DST}")
    print(f"version={data.get('version')}")
    for k in ("dominios", "competencias", "processos", "habilidades",
             "conteudos", "cadeias_causais", "tipos_erro", "intervencoes"):
        if k in data:
            print(f"  {k}: {count(k)}")


if __name__ == "__main__":
    main()
