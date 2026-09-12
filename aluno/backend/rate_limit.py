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
    # Reclamações e sugestões: dez por hora é mais do que qualquer aluno
    # honesto escreve, e impede que o canal vire depósito de spam.
    "sugestoes": (10, 3600),
}

_eventos: dict[str, deque[float]] = defaultdict(deque)


def _cliente(request: Request) -> str:
    """Identidade do chamador para fins de limite.

    Atrás do proxy do Fly, `request.client.host` é o IP do proxy e barraria
    todo mundo junto; o primeiro valor de `X-Forwarded-For` é o IP real do
    cliente. Uvicorn roda com `--proxy-headers`, então este header é confiável
    aqui (só o proxy consegue defini-lo).
    """
    encaminhado = request.headers.get("x-forwarded-for", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
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
