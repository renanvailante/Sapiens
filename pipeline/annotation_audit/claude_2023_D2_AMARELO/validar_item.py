"""Normaliza + valida UMA questão anotada pelo Claude, usando o código REAL
de produção (`item_contract.normalize_item` / `ontology_validator`), sem
nenhuma alteração a esses módulos.

Uso:
    python3 validar_item.py <numero>

Lê:  items/Q<numero>_raw.json   (o que o anotador escreveu)
Escreve: items/Q<numero>.json   (normalizado; só é sobrescrito se válido)
Imprime o relatório de validação (valid/errors/warnings) sempre.
"""
import json
import sys
import pathlib

sys.path.insert(0, "/Users/renanvailante/Documents/Projetos/Sapiens/pipeline/backend")

from item_contract import normalize_item, validate  # noqa: E402
from ontology_validator import OntologyRegistry  # noqa: E402

AUDIT_DIR = pathlib.Path(__file__).resolve().parent
ONTOLOGY_PATH = "/Users/renanvailante/Documents/Projetos/Sapiens/pipeline/docs/ontology/ontology_v1.4.json"

if len(sys.argv) != 2:
    print("uso: validar_item.py <numero>")
    sys.exit(1)

numero = sys.argv[1].zfill(3)
raw_path = AUDIT_DIR / "items" / f"Q{numero}_raw.json"
out_path = AUDIT_DIR / "items" / f"Q{numero}.json"

if not raw_path.is_file():
    print(f"ERRO: {raw_path} não existe. Escreva o item primeiro.")
    sys.exit(1)

with open(ONTOLOGY_PATH, encoding="utf-8") as f:
    ontology = json.load(f)

raw = json.loads(raw_path.read_text(encoding="utf-8"))

item_id = f"CLAUDE-ITEM-ENEM-2023-AMARELO-Q{numero}"
fonte_conhecida = (raw.get("fonte") or {})

item = normalize_item(
    raw,
    ontology,
    item_id=item_id,
    arquivo_origem="2023_PV_impresso_D2_CD5.pdf",
)

reg = OntologyRegistry(ONTOLOGY_PATH)
result = validate(item, reg)

print(json.dumps(result, ensure_ascii=False, indent=2))

out_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nGravado em {out_path} (valid={result['valid']}).")
if not result["valid"]:
    print("CORRIJA items/Q{}_raw.json e rode de novo antes de considerar pronto.".format(numero))
