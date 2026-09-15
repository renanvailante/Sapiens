"""Limitador de requisições — janela deslizante em memória.

Existe porque não havia nenhum limite em rota alguma. Três exposições reais:

* `/auth/login` aceitava tentativas de senha ilimitadas;
* `/students/me/sessao/diagnostico` e o corretor de redação chamam o Gemini,
  são gratuitos para o aluno e podiam ser disparados em laço, gastando cota;
* `/questoes` permitia varrer o acervo inteiro (`limit=500`) em sequência.

**Em memória, de propósito.** O app roda hoje com `min_machines_running = 1`
(fly.toml) — uma instância, um processo, então o contador é global de fato.
Com mais de uma máquina cada uma passa a ter seu próprio contador, e o limite
efetivo vira `N × limite`: continua barrando força bruta e laço automático (a
ordem de grandeza importa mais que o número exato), mas deixa de ser preciso.
Trocar por Redis é o passo natural quando houver segunda máquina — e não antes,
porque uma dependência a mais no caminho do login é risco novo por precisão que
ainda não muda decisão nenhuma.

Não há limpeza agendada: cada chave é podada na própria consulta, e chaves nunca
mais consultadas somem no próximo restart. Um dicionário de contadores por
IP/usuário não cresce a ponto de importar na escala de um beta.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# nome -> (máximo de eventos, janela em segundos)
LIMITES: dict[str, tuple[int, int]] = {
    # Força bruta de senha. 10/min por IP deixa o aluno errar à vontade e
    # torna varredura de dicionário inviável.
    "login": (10, 60),
    "signup": (5, 300),
    # Recuperação de senha: barato para quem esqueceu, caro para quem quer
    # usar o produto como máquina de spam contra terceiros.
    "password_reset": (3, 900),
    # Rotas que gastam Gemini. Por usuário, não por IP.
    "llm": (20, 3600),
    # Chat da Mentis. Cada mensagem já custa 10 Sparks, então o dinheiro
    # é o freio principal; isto existe para o caso de um script com saldo
    # alto virar um laço de chamadas ao Gemini.
    "mentis": (60, 3600),
    # Leitura do acervo — generoso para uso normal, barra raspagem.
    "acervo": (120, 60),
    # Criação de pagamento: dinheiro real, e cada tentativa toca o MP.
    "pagamento": (10, 600),
    # Relato de erro de frontend: generoso (uma tela quebrada gera vários),
    # mas o suficiente para a rota não virar depósito de lixo.
    "client_error": (30, 300),
    # Direitos do titular (LGPD art. 18). A exportação varre o histórico
    # inteiro do aluno no Firestore — é a única rota que lê O(eventos) de
    # propósito. Cinco por hora atende qualquer pedido legítimo (normalmente
    # um) e impede que a rota vire uma alavanca de custo.
    "dados_pessoais": (5, 3600),
    # Reclamações e sugestões: dez por hora é mais do que qualquer aluno
    # honesto escreve, e impede que o canal vire depósito de spam.
    "sugestoes": (10, 3600),
    # Cronograma. Montar a semana é grátis e barato, mas duas rotas aqui saem
    # da máquina: a extração de compromissos chama o Gemini e a importação de
    # .ics faz o servidor buscar uma URL. Trinta por hora cobre remontar a
    # semana várias vezes enquanto se ajustam os horários, e fecha a porta
    # para a rota de .ics virar um repetidor de requisições.
    "cronograma": (30, 3600),
    # Engajamento: resgatar missão e comprar congelador. Poucas ações por dia
    # por natureza; o limite existe só para um script não ficar batendo na
    # rota de resgate à espera de uma corrida que a trava do Mongo já fecha.
    "engajamento": (60, 3600),
    # Mural de dúvidas. É a única superfície do produto onde um aluno escreve
    # algo que outro lê, então o limite é também a primeira defesa contra spam:
    # 40/hora cobre uma tarde inteira respondendo colegas e torna inviável
    # despejar conteúdo em massa.
    "comunidade": (40, 3600),
}

_eventos: dict[str, deque[float]] = defaultdict(deque)


# Header que o proxy do Fly escreve com o IP real de quem conectou. Ao
# contrário de `X-Forwarded-For`, ele é SOBRESCRITO pelo proxy a cada
# requisição, então o cliente não consegue forjá-lo.
_HEADER_FLY = "fly-client-ip"


def _cliente(request: Request) -> str:
    """Identidade do chamador para fins de limite.

    **O primeiro elemento de `X-Forwarded-For` não serve — é do atacante.**
    Esta função lia justamente esse elemento, com o comentário de que "só o
    proxy consegue definir" o header. Não é o caso: `X-Forwarded-For` é uma
    LISTA, e cada proxy ACRESCENTA ao que já veio. Quem manda
    `X-Forwarded-For: 1.2.3.4` recebe de volta `1.2.3.4, <ip real>` — o valor
    forjado na frente, o verdadeiro no fim. Girando um IP falso por requisição,
    cada tentativa de senha caía num contador novo e o limite de 10/min do
    `login` deixava de existir. O mesmo valia para `signup`, `password_reset` e
    `client_error`, todos limitados por IP.

    `request.client.host` não era saída: o Dockerfile roda uvicorn com
    `--forwarded-allow-ips='*'`, e nesse modo o próprio uvicorn reescreve
    `client.host` com o PRIMEIRO item da lista
    (`uvicorn/middleware/proxy_headers.py`) — isto é, com o valor forjado.

    A ordem abaixo é a única confiável:

    1. `Fly-Client-IP`, que o proxy sobrescreve e o cliente não alcança;
    2. o ÚLTIMO item de `X-Forwarded-For` — o que o proxy mais próximo
       acrescentou, atrás de tudo que o cliente possa ter inventado;
    3. `request.client.host`, para desenvolvimento sem proxy nenhum na frente.
    """
    do_fly = request.headers.get(_HEADER_FLY, "").strip()
    if do_fly:
        return do_fly
    partes = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if partes:
        return partes[-1]
    return request.client.host if request.client else "desconhecido"


def checar(nome: str, chave: str) -> None:
    """Registra um evento e levanta 429 se `chave` estourou o limite `nome`."""
    maximo, janela = LIMITES[nome]
    agora = time.monotonic()
    marcas = _eventos[f"{nome}:{chave}"]
    while marcas and agora - marcas[0] > janela:
        marcas.popleft()
    if len(marcas) >= maximo:
        espera = int(janela - (agora - marcas[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas. Tente de novo em {espera}s.",
            headers={"Retry-After": str(espera)},
        )
    marcas.append(agora)


def por_ip(nome: str):
    """Dependência FastAPI que limita por IP de origem."""

    async def _dep(request: Request) -> None:
        checar(nome, _cliente(request))

    return _dep


def por_usuario(nome: str):
    """Dependência que limita por usuário autenticado (cai para IP se não
    houver sessão). Usada nas rotas caras, onde o custo é por conta e não por
    origem de rede — trocar de IP não deve reabrir a cota."""
    from auth import _resolve_user

    async def _dep(request: Request) -> None:
        user = await _resolve_user(request)
        checar(nome, user.user_id if user else _cliente(request))

    return _dep


def limpar() -> None:
    """Zera todos os contadores. Só para testes."""
    _eventos.clear()
