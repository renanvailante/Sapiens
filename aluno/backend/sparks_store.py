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
    highlight: str | None = None  # selo de destaque, ex.: "Mais vendido"
    # Tamanho do card na loja: 0 (menor) a 3 (maior). Ordem crescente pelos
    # pacotes normais (200 < 600 < 4000), com UMA exceção pedida pelo produto:
    # o pacote de R$54,90 (1.500 Sparks) é o maior de todos, nível 3, maior
    # até que o de 4.000 Sparks. É produto (o que puxa mais atenção visual),
    # não preço — por isso mora aqui no catálogo do servidor, não no frontend.
    destaque_tamanho: int = 0
    # Fica de fora da grade principal da loja — usado só para o pacote de
    # teste de pagamento real (ver comentário abaixo). Nunca aparece como
    # card normal, mas continua um pacote válido para `/sparks/purchases`.
    oculto: bool = False


# Catálogo aprovado 2026-09.
PACKAGES: dict[str, SparksPackage] = {
    p.package_id: p
    for p in [
        # Ordem da lista = ordem visual na loja (esquerda->direita), sempre
        # crescente por preço. `destaque_tamanho` é independente da posição:
        # cresce 200(0) < 600(1) < 4000(2), com a EXCEÇÃO pedida — 1.500
        # Sparks (R$54,90) é o maior de todos (3), maior até que o de 4.000.
        SparksPackage("spark_200", "200 Sparks", 200, 990, highlight="Menor custo", destaque_tamanho=0),
        SparksPackage("spark_600", "600 Sparks", 600, 2490, destaque_tamanho=1),
        SparksPackage("spark_1500", "1.500 Sparks", 1500, 5490, highlight="Mais vendido", destaque_tamanho=3),
        SparksPackage("spark_4000", "4.000 Sparks", 4000, 11990, highlight="Melhor valor", destaque_tamanho=2),
        # TEMPORÁRIO — só para confirmar o fim-a-fim de um pagamento real em
        # produção (cartão real, não TEST). Remover este pacote (e o botão
        # correspondente em SparksStore.jsx) depois do teste.
        SparksPackage("spark_test_15", "15 Sparks (teste)", 15, 100, oculto=True),
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
