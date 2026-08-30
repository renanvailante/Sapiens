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


PACKAGES: dict[str, SparksPackage] = {
    p.package_id: p
    for p in [
        SparksPackage("spark_200", "200 Sparks", 200, 1990),
        SparksPackage("spark_500", "500 Sparks", 500, 3990),
        SparksPackage("spark_1200", "1.200 Sparks", 1200, 7990),
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
