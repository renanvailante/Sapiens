"""Validador de Item Annotation contra a Ontologia Cognitiva Sapiens v1.4.

- Carrega docs/ontology/ontology_v1.4.json
- Expõe conjuntos de IDs válidos
- validate_item_annotation(ann) -> ValidationResult

Schema esperado de `ann` (dict), alinhado ao Manual de Anotação:
{
  "item_id": str,
  "annotator_id": str,
  "date": str (ISO opcional),
  "dominio_id": "DOM-...",
  "competencia_id": "COMP-...",
  "processo_dominante": {"id": "PROC-...", "peso": 0.7},
  "processos_secundarios": [{"id": "PROC-...", "peso": 0.3}, ...],
  "habilidades": ["HAB-..", ...],
  "alternativas": [
      {"label": "A", "correta": true},
      {"label": "B", "correta": false, "erro_id": "ERR-..." | null,
       "intervencao_id": "INT-..." | null}
  ],
  "justificativa": str
}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "docs/ontology/ontology_v1.4.json"

_ID_KEYS = {
    "dominios": "DOM",
    "competencias": "COMP",
    "processos_cognitivos": "PROC",
    "habilidades_observaveis": "HAB",
    "tipos_erro": "ERR",
    "intervencoes_pedagogicas": "INT",
}


class OntologyRegistry:
    """Carrega e indexa a ontologia. Fonte única de IDs válidos."""

    def __init__(self, path: Path | str = ONTOLOGY_PATH):
        self.path = Path(path)
        with self.path.open(encoding="utf-8") as f:
            self.data: dict[str, Any] = json.load(f)

        self.version: str = self.data.get("version", "?")
        self._by_key: dict[str, dict[str, dict]] = {}
        for key in _ID_KEYS:
            items = self.data.get(key, []) or []
            self._by_key[key] = {it["id"]: it for it in items if isinstance(it, dict) and "id" in it}

        # Cross-index processo -> tipos_erro válidos
        self.err_by_proc: dict[str, set[str]] = {}
        for err in self._by_key.get("tipos_erro", {}).values():
            for proc_id in err.get("processos_cognitivos", []) or []:
                self.err_by_proc.setdefault(proc_id, set()).add(err["id"])

    # ---- IDs válidos ---------------------------------------------------
    def ids(self, key: str) -> set[str]:
        return set(self._by_key.get(key, {}).keys())

    @property
    def dominios(self) -> set[str]: return self.ids("dominios")

    @property
    def competencias(self) -> set[str]: return self.ids("competencias")

    @property
    def processos(self) -> set[str]: return self.ids("processos_cognitivos")

    @property
    def habilidades(self) -> set[str]: return self.ids("habilidades_observaveis")

    @property
    def tipos_erro(self) -> set[str]: return self.ids("tipos_erro")

    @property
    def intervencoes(self) -> set[str]: return self.ids("intervencoes_pedagogicas")

    def get(self, key: str, _id: str) -> dict | None:
        return self._by_key.get(key, {}).get(_id)


# ---- Resultado -----------------------------------------------------------
@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def err(self, msg: str) -> None:
        self.valid = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


# ---- Regras de validação -------------------------------------------------
_REQUIRED_FIELDS = ("item_id", "dominio_id", "competencia_id", "processo_dominante",
                    "alternativas")

_WEIGHT_TOLERANCE = 1e-6


def _check_id(res: ValidationResult, label: str, value: Any, valid: set[str]) -> None:
    if not isinstance(value, str):
        res.err(f"{label}: esperado string, recebeu {type(value).__name__}")
        return
    if value not in valid:
        res.err(f"{label}: id '{value}' não existe na ontologia")


def _iter_weighted(procs: Iterable) -> list[tuple[str, float]]:
    out = []
    for p in procs or []:
        if isinstance(p, dict):
            out.append((p.get("id"), float(p.get("peso", 0))))
    return out


def validate_item_annotation(ann: dict, registry: OntologyRegistry | None = None) -> ValidationResult:
    reg = registry or OntologyRegistry()
    res = ValidationResult()

    if not isinstance(ann, dict):
        res.err("annotation deve ser um objeto/dict")
        return res

    # Campos obrigatórios
    for f in _REQUIRED_FIELDS:
        if f not in ann:
            res.err(f"campo obrigatório ausente: '{f}'")
    if res.errors:
        return res

    # Domínio / competência
    _check_id(res, "dominio_id", ann["dominio_id"], reg.dominios)
    _check_id(res, "competencia_id", ann["competencia_id"], reg.competencias)

    # Processos: dominante + secundários, pesos somam 1.0
    dom = ann["processo_dominante"]
    if not isinstance(dom, dict) or "id" not in dom or "peso" not in dom:
        res.err("processo_dominante: deve ser {'id':..., 'peso':...}")
        return res

    procs = [(dom["id"], float(dom.get("peso", 0)))]
    procs += _iter_weighted(ann.get("processos_secundarios", []))

    seen_ids: set[str] = set()
    for pid, w in procs:
        _check_id(res, "processo", pid, reg.processos)
        if pid in seen_ids:
            res.err(f"processo '{pid}' repetido")
        seen_ids.add(pid)
        if w <= 0 or w > 1:
            res.err(f"peso de '{pid}' fora de (0,1]: {w}")

    dom_w = procs[0][1]
    if any(w > dom_w for _, w in procs[1:]):
        res.err("processo_dominante deve ter peso >= a todos os secundários")

    total = sum(w for _, w in procs)
    if abs(total - 1.0) > _WEIGHT_TOLERANCE:
        res.err(f"pesos dos processos devem somar 1.0 (atual: {total:.6f})")

    # Competência ↔ processo dominante (aviso, não bloqueio)
    comp = reg.get("competencias", ann["competencia_id"])
    if comp and dom["id"] not in (comp.get("processos") or []):
        res.warn(f"processo dominante '{dom['id']}' não listado em "
                 f"'{ann['competencia_id']}'.processos")

    # Habilidades
    for hid in ann.get("habilidades", []) or []:
        _check_id(res, "habilidade", hid, reg.habilidades)

    # Alternativas
    alts = ann.get("alternativas") or []
    if not isinstance(alts, list) or len(alts) < 2:
        res.err("alternativas: deve haver pelo menos 2")
    corretas = 0
    for i, alt in enumerate(alts if isinstance(alts, list) else []):
        prefix = f"alternativas[{i}]"
        if not isinstance(alt, dict):
            res.err(f"{prefix}: objeto esperado")
            continue
        if alt.get("correta"):
            corretas += 1
        else:
            eid = alt.get("erro_id")
            if eid is not None:
                _check_id(res, f"{prefix}.erro_id", eid, reg.tipos_erro)
                # coerência erro ↔ processo dominante
                allowed = reg.err_by_proc.get(dom["id"], set())
                if allowed and eid not in allowed:
                    res.warn(f"{prefix}.erro_id '{eid}' não é catalogado para "
                             f"processo '{dom['id']}' (permitidos: {sorted(allowed) or '—'})")
            iid = alt.get("intervencao_id")
            if iid is not None:
                _check_id(res, f"{prefix}.intervencao_id", iid, reg.intervencoes)
                if eid:
                    err = reg.get("tipos_erro", eid) or {}
                    if err.get("intervencao") and iid != err["intervencao"]:
                        res.warn(f"{prefix}.intervencao_id '{iid}' difere da prescrita "
                                 f"por '{eid}' ({err['intervencao']})")

    if corretas != 1:
        res.err(f"alternativas: exatamente 1 correta esperada (achadas: {corretas})")

    # Justificativa (Manual §checklist)
    if not (ann.get("justificativa") or "").strip():
        res.warn("justificativa vazia — Manual exige 1–2 frases")

    return res


# ---- CLI de sanidade -----------------------------------------------------
if __name__ == "__main__":
    reg = OntologyRegistry()
    print(f"Ontologia v{reg.version}")
    print(f"  DOM={len(reg.dominios)} COMP={len(reg.competencias)} "
          f"PROC={len(reg.processos)} HAB={len(reg.habilidades)} "
          f"ERR={len(reg.tipos_erro)} INT={len(reg.intervencoes)}")
