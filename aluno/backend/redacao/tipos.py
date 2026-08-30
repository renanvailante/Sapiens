"""Tipos compartilhados entre os módulos de correção de redação."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RedacaoEntrada:
    """Entrada de uma correção. `linhas_manuscritas`/`textos_motivadores` são
    opcionais e habilitam checagens mais precisas quando disponíveis (ver
    `elegibilidade.py`/`heuristicas.py` para o que muda sem eles)."""

    texto: str
    titulo: str | None = None
    tema_frase: str | None = None
    tema_elementos_obrigatorios: list[str] = field(default_factory=list)
    linhas_manuscritas: int | None = None
    textos_motivadores: list[str] = field(default_factory=list)
