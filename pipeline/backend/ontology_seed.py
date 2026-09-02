"""Ontologia Cognitiva Sapiens - Semente inicial.

Fonte única de verdade: `pipeline/docs/ontology/ontology_v1.4.json`. Este
módulo NÃO redefine a ontologia — apenas carrega o JSON canônico do disco,
para que o runtime nunca divirja do contrato documentado. Para publicar uma
nova versão oficial, edite `pipeline/docs/ontology/` (fora do escopo deste
código) e reinicie o serviço, ou use a rota `/ontology/import`.
"""
import json
from pathlib import Path

_CANONICAL_PATH = Path(__file__).resolve().parent.parent / "docs" / "ontology" / "ontology_v1.4.json"

with _CANONICAL_PATH.open(encoding="utf-8") as _f:
    DEFAULT_ONTOLOGY: dict = json.load(_f)
