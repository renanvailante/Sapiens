# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Sem .pyc e sem buffer: logs aparecem em tempo real no coletor da plataforma,
# em vez de ficarem presos num buffer até o processo morrer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Build a partir deste diretório:
#     docker build -t sapiens-professor professor/backend
WORKDIR /app

# Camada de dependências separada: só reconstrói quando requirements muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuário sem privilégios — um comprometimento do processo não vira root.
RUN useradd --create-home --uid 10001 sapiens && chown -R sapiens:sapiens /app
USER sapiens

# A plataforma injeta $PORT; 8000 é só o default local.
ENV PORT=8000
EXPOSE 8000

# --proxy-headers: atrás do balanceador da plataforma, sem isto o app enxerga
# o IP do proxy e monta URLs http:// mesmo servindo por HTTPS.
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
