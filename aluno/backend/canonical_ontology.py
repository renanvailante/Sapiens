"""Resolução da ontologia canônica para o app `aluno`.

**Fonte única (GOV-1.0 §1.1):** `pipeline/docs/ontology/ontology_v1.4.json`.
Este módulo NÃO redefine, não copia e não normaliza a ontologia — apenas
localiza o artefato canônico e o carrega.

Até 2026-08-21 o `aluno` mantinha uma réplica privada do catálogo em
`aluno/backend/docs/ontology JSON v1.4`. Sob GOV-1.0 §12.2 isso é uma
**duplicata** (não declarava `derivado_de:` e não era membro do Conjunto
Normativo Indivisível). A comparação campo a campo exigida por §12.3, passo 2,
foi executada e não encontrou divergência de conteúdo — nenhuma decisão
não-registrada estava escondida na cópia. A réplica foi então removida e as
citações redirecionadas para cá.

Ordem de resolução do caminho:

1. ``SAPIENS_ONTOLOGY_PATH`` — necessário quando os apps são publicados
   separadamente e `pipeline/docs/` não acompanha o artefato do `aluno`.
2. Caminho canônico relativo ao repositório (layout de monorepo).

Não há fallback silencioso: se nenhum dos dois resolver, o carregamento falha
com mensagem explícita. Um catálogo ausente precisa quebrar de forma visível —
degradar para um catálogo vazio produziria perfis cognitivos silenciosamente
errados.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_ENV_VAR = "SAPIENS_ONTOLOGY_PATH"
_VALIDATOR_ENV_VAR = "SAPIENS_CONTRACTS_PATH"


def _repo_root() -> Path | None:
    """Raiz do monorepo, quando o código roda a partir dele.

    Calculado sob demanda, e não no import: dentro do container este arquivo
    fica em `/app/`, que não tem dois níveis acima, e `parents[2]` levantava
    `IndexError` **durante o import do módulo** — o processo morria antes de
    olhar as variáveis de ambiente que tornam o caminho relativo desnecessário.
    """
    p = Path(__file__).resolve()
    return p.parents[2] if len(p.parents) > 2 else None


def canonical_path() -> Path:
    override = os.environ.get(_ENV_VAR)
    if override:
        p = Path(override)
        if not p.is_file():
            raise RuntimeError(f"{_ENV_VAR}={override!r} não aponta para um arquivo legível.")
        return p

    raiz = _repo_root()
    relativo = (
        raiz / "pipeline" / "docs" / "ontology" / "ontology_v1.4.json" if raiz else None
    )
    if relativo and relativo.is_file():
        return relativo
    raise RuntimeError(
        "Ontologia canônica não encontrada. Esperada em "
        f"{relativo or '<sem layout de monorepo>'} ou no caminho indicado por "
        f"{_ENV_VAR}. O app `aluno` não mantém cópia própria do catálogo por "
        "decisão de governança (GOV-1.0 §12)."
    )


@lru_cache(maxsize=1)
def load_ontology() -> dict:
    """Catálogo canônico completo, tal como está no disco."""
    with canonical_path().open(encoding="utf-8") as f:
        return json.load(f)


def ontology_version() -> str:
    """Versão declarada pelo catálogo (ex.: ``'1.4.1'``).

    Este é o valor que alimenta o campo `ontology_version`, obrigatório em todo
    objeto persistido pelos contratos vigentes (Schema 2.2, behavior 1.1,
    Error Trace 1.0), por exigência de GOV-1.0 §6.1.
    """
    return str(load_ontology().get("version") or "")


@lru_cache(maxsize=1)
def _validator_module():
    """Importa o validador de contratos, mantido junto do espaço canônico.

    [Decisão de engenharia, registrada.] Existe **uma única implementação** de
    validação dos contratos (`pipeline/backend/ontology_validator.py`),
    compartilhada pelos apps em vez de reimplementada em cada um. Duas
    implementações do mesmo contrato divergem com o tempo — é exatamente o modo
    de falha que GOV-1.0 §12 existe para impedir, e reproduzi-lo em código seria
    contraditório com o que o corpus exige dos documentos.

    Em deploy separado, aponte ``SAPIENS_CONTRACTS_PATH`` para o diretório que
    contém `ontology_validator.py`.
    """
    import sys

    override = os.environ.get(_VALIDATOR_ENV_VAR)
    if override:
        base = Path(override)
    else:
        raiz = _repo_root()
        if raiz is None:
            raise RuntimeError(
                f"Sem layout de monorepo e sem {_VALIDATOR_ENV_VAR}: aponte-a para "
                "o diretório que contém 'ontology_validator.py'."
            )
        base = raiz / "pipeline" / "backend"
    if not (base / "ontology_validator.py").is_file():
        raise RuntimeError(
            f"Validador de contratos não encontrado em {base}. Aponte "
            f"{_VALIDATOR_ENV_VAR} para o diretório que contém 'ontology_validator.py'."
        )
    if str(base) not in sys.path:
        sys.path.append(str(base))
    import ontology_validator  # noqa: PLC0415

    return ontology_validator


def validate_item(item: dict) -> dict:
    """Valida um item contra o Schema Sapiens 2.2. Devolve `{valid, errors, warnings}`."""
    mod = _validator_module()
    registry = mod.OntologyRegistry.from_dict(load_ontology())
    return mod.validate_item_annotation(item, registry).to_dict()


def normalize_item(item: dict, *, item_id: str | None = None) -> dict:
    """Aplica ao item as partes mecânicas do contrato, antes de validar.

    Carimba `schema_version`/`ontology_version`, recalcula `item_hash` e
    **deriva** domínios e competências a partir dos processos. Um remetente
    humano não deveria ter de calcular a derivação à mão — ela é determinística
    e a Constituição §4.4 proíbe que seja atribuída de outra forma. `item_id`
    informado é preservado: é a identidade que o remetente afirma.
    """
    _validator_module()  # garante o sys.path
    import item_contract  # noqa: PLC0415

    registry = _validator_module().OntologyRegistry.from_dict(load_ontology())
    return item_contract.normalize_item(
        item, load_ontology(), item_id=item_id or item.get("item_id"), registry=registry
    )
