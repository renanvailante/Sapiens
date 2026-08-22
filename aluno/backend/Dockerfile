# syntax=docker/dockerfile:1
#
# ATENÇÃO — o contexto de build é a RAIZ DO REPOSITÓRIO, não este diretório:
#
#     docker build -f aluno/backend/Dockerfile -t sapiens-aluno .
#
# O app do aluno lê o corpus canônico e o validador de contratos, que vivem em
# `pipeline/`. Buildar só a partir de `aluno/backend` produziria uma imagem que
# sobe e falha no primeiro acesso à ontologia — a única implementação da
# validação é compartilhada de propósito (GOV-1.0 §12: duas cópias do mesmo
# contrato divergem com o tempo).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY aluno/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aluno/backend/ /app/

# Corpus canônico e validador compartilhado, resolvidos por variável.
COPY pipeline/docs/ontology/ontology_v1.4.json /app/contracts/ontology/ontology_v1.4.json
COPY pipeline/backend/ontology_validator.py    /app/contracts/ontology_validator.py
COPY pipeline/backend/item_contract.py         /app/contracts/item_contract.py

ENV SAPIENS_ONTOLOGY_PATH=/app/contracts/ontology/ontology_v1.4.json \
    SAPIENS_CONTRACTS_PATH=/app/contracts

# `ontology_validator` resolve o catálogo por caminho relativo ao próprio
# arquivo (`parent.parent/docs/ontology/...`). Dentro da imagem esse caminho
# não existe, então o layout esperado é recriado.
RUN mkdir -p /app/docs/ontology \
    && cp /app/contracts/ontology/ontology_v1.4.json /app/docs/ontology/ontology_v1.4.json

RUN useradd --create-home --uid 10001 sapiens && chown -R sapiens:sapiens /app
USER sapiens

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
