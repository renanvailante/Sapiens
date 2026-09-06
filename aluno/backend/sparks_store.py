"""Catálogo de pacotes de Sparks e frequências de recarga automática.

Preço, quantidade de Sparks e frequências permitidas vivem só aqui — o
frontend nunca envia nenhum desses valores, só um `package_id`/`days` que o
backend reconhece. Mesmo estilo de constante fixa em código que
`SKILLS_MAP_COST` já usa em `skills_map_routes.py`, em vez de configuração
por env: são valores de produto, revisados em código com o resto do catálogo.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SparksPackage:
    package_id: str
    label: str
    sparks_amount: int
    price_cents: int
    currency: str = "BRL"
    highlight: str | None = None  # selo de destaque, ex.: "Mais escolhido"


# Catálogo aprovado 2026-09.
PACKAGES: dict[str, SparksPackage] = {
    p.package_id: p
    for p in [
        SparksPackage("spark_200", "200 Sparks", 200, 990),
        SparksPackage("spark_600", "600 Sparks", 600, 2490),
        SparksPackage("spark_1500", "1.500 Sparks", 1500, 5490, highlight="Mais escolhido"),
        SparksPackage("spark_4000", "4.000 Sparks", 4000, 11990, highlight="Melhor valor"),
    ]
}

# Frequências de recarga automática permitidas (dias). Fixo — a assinatura do
# Mercado Pago não permite alterar `auto_recurring.frequency` depois de
# criada, então a lista curta aqui é também o menu de opções do frontend.
AUTO_RECHARGE_FREQUENCIES_DAYS: tuple[int, ...] = (7, 15, 30)

DEFAULT_BASELINE = 50  # aviso de saldo baixo — não dispara cobrança nenhuma.


def get_package(package_id: str) -> SparksPackage | None:
    return PACKAGES.get(package_id)


def list_packages() -> list[SparksPackage]:
    return list(PACKAGES.values())


def is_valid_frequency(days: int) -> bool:
    return days in AUTO_RECHARGE_FREQUENCIES_DAYS
