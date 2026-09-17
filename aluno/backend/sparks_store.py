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
    # Direitos PERMANENTES que a compra concede, além dos Sparks. Moram no
    # catálogo (e não numa checagem de `package_id` espalhada pelo código)
    # porque são decisão de produto, e porque anunciar o benefício e
    # concedê-lo têm de sair da MESMA fonte — prometer na loja o que o
    # servidor não entrega é o pior defeito possível numa tela de pagamento.
    #
    # `DIREITOS` é a lista fechada: cada chave aqui é um campo booleano no
    # documento do aluno (`students/{uid}`) e uma porta no backend.
    direitos: tuple[str, ...] = ()
    # O que a LOJA escreve no card, na ordem. Uma linha por direito.
    beneficios: tuple[str, ...] = ()


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
        SparksPackage(
            "spark_1500", "1.500 Sparks", 1500, 5490,
            highlight="Mais vendido", destaque_tamanho=3,
            # R$54,90 é SALDO, e só saldo. Até 2026-09-16 este pacote incluía
            # as aulas ao vivo de quinta; o produto decidiu que a aula volta a
            # custar 200 Sparks por edição para todo mundo, e que o ÚNICO
            # pacote que a dispensa é o de 4.000 Sparks.
            #
            # Tirar daqui muda só quem compra DAQUI PARA A FRENTE: quem já
            # pagou os R$54,90 tem a flag `lives_inclusas` gravada no próprio
            # documento (`students/{uid}`) e continua entrando sem pagar. A
            # promessa feita a quem comprou não se desfaz com uma linha de
            # catálogo — ela só deixa de ser feita de novo.
            direitos=(),
            beneficios=(),
        ),
        SparksPackage(
            "spark_4000", "4.000 Sparks", 4000, 11990,
            highlight="Melhor valor", destaque_tamanho=2,
            # R$119,90 é o pacote que compra mais DIREITO, e não só saldo:
            #  * `cursos_inclusos` — os quatro cursos do catálogo, sem pagar
            #    os 500 Sparks de cada um (ver `cursos_routes.comprar_curso`);
            #  * `lives_inclusas` — desde 2026-09-16 é o ÚNICO pacote que
            #    dispensa os 200 Sparks da aula ao vivo de quinta. Toda
            #    quinta, sem cobrança por edição (ver
            #    `cursos_routes._montar_live`). A escada de direito continua
            #    valendo, e agora ela é trivial: nenhum pacote mais barato
            #    concede direito nenhum (ver o teste da escada em
            #    `tests/test_direitos_do_pacote.py`);
            #  * `mentis_ilimitada` — abrir o chat, cada mensagem, a
            #    explicação de questão e a intervenção da causa raiz param de
            #    cobrar Spark (ver o atalho em `mentis_routes._cobrar`).
            #    ATENÇÃO (2026-09-16): a loja passou a anunciar este direito
            #    como "por um mês", mas o backend continua concedendo uma
            #    FLAG PERMANENTE (`firestore_service.marcar_mentis_ilimitada`,
            #    sem data de validade). Hoje entregamos MAIS do que
            #    anunciamos — o lado seguro da divergência, mas ainda uma
            #    divergência. Fechar isso exige guardar o vencimento por
            #    aluno e checá-lo em `mentis_routes`; enquanto não existir,
            #    NÃO escreva em lugar nenhum que o direito expira de fato.
            #  * `comunidade_vip` — a sala fechada do mural, onde a equipe e o
            #    1º colocado respondem (ver `comunidade.SALA_VIP`).
            direitos=("cursos_inclusos", "lives_inclusas", "mentis_ilimitada", "comunidade_vip"),
            beneficios=(
                "Todos os cursos inclusos",
                "Todas as aulas ao vivo de quinta inclusas",
                "Mentis ILIMITADA por um mês",
                "Comunidade VIP — sala fechada",
            ),
        ),
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


# A lista fechada de direitos que um pacote pode conceder. Só o que está
# aqui vira campo no documento do aluno — um pacote não pode inventar um
# direito novo sem que exista a porta correspondente no backend.
#
#  * `cursos_inclusos`  -> os quatro cursos do catálogo, sem os 500 Sparks de
#                          cada (porta: `cursos_routes`);
#  * `lives_inclusas`   -> toda edição da aula ao vivo de quinta, sem os 200
#                          Sparks por edição (porta: `cursos_routes`). Só o
#                          pacote de 4.000 Sparks o vende;
#  * `mentis_ilimitada` -> a Mentis para de cobrar (porta: `mentis_routes`);
#  * `comunidade_vip`   -> a sala fechada do mural (porta: `comunidade_routes`).
DIREITOS: tuple[str, ...] = (
    "cursos_inclusos",
    "lives_inclusas",
    "mentis_ilimitada",
    "comunidade_vip",
)


def direitos_do_pacote(package_id: str) -> tuple[str, ...]:
    """O que ESTE pacote concede. Fonte única, lida tanto pela loja (para
    anunciar) quanto pelo webhook (para conceder)."""
    pkg = PACKAGES.get(package_id)
    if not pkg:
        return ()
    return tuple(d for d in pkg.direitos if d in DIREITOS)


def concede_mentis_ilimitada(package_id: str) -> bool:
    return "mentis_ilimitada" in direitos_do_pacote(package_id)


def pacote_com_direito(direito: str) -> SparksPackage | None:
    """O pacote VISÍVEL MAIS BARATO que vende este direito — para a tela que
    precisa dizer "isto vem no pacote X" sem escrever um `package_id` no meio
    do texto. Se o produto mudar qual pacote dá o quê, a frase acompanha.

    Mais barato, e não "o primeiro que aparecer": um direito pode ser vendido
    por mais de um pacote (as lives estavam no de 1.500 e no de 4.000 até
    2026-09-16), e o que a oferta precisa dizer é a porta de entrada mais
    barata, não a mais cara. `PACKAGES` está em ordem crescente de preço, que
    é a ordem da loja.
    """
    for p in PACKAGES.values():
        if not p.oculto and direito in direitos_do_pacote(p.package_id):
            return p
    return None
