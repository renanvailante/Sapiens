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

# NOTA: `aluno/backend/conteudo/` (trilhas, estações e blocos dos cursos) entra
# na imagem por esta linha, sem precisar de COPY própria — ao contrário do
# canon do Enem e do banco de treino, que moram fora de `aluno/backend/`. Se um
# dia alguém restringir o COPY acima ou excluir `conteudo/` no `.dockerignore`
# da raiz, o app SOBE e a aba de estudo dos cursos fica vazia sem erro nenhum,
# que é exatamente a classe de bug descrita logo abaixo. `CURSOS_CONTEUDO_DIR`
# é a válvula para apontar a raiz para outro lugar (volume, bucket).

# Corpus canônico e validador compartilhado, resolvidos por variável.
COPY pipeline/docs/ontology/ontology_v1.4.json /app/contracts/ontology/ontology_v1.4.json
COPY pipeline/backend/ontology_validator.py    /app/contracts/ontology_validator.py
COPY pipeline/backend/item_contract.py         /app/contracts/item_contract.py

# Canon do Enem (apoio_externo, GOV-1.0 §1.1) — sem este arquivo dentro da
# imagem, `redacao/canon.py` não acha nada e TODA correção de redação falha.
# Foi exatamente o que aconteceu entre o lançamento do corretor e 2026-09-06:
# a feature existia no código, tinha testes passando na árvore do repo, e
# respondia erro em produção porque o dado nunca tinha sido copiado.
COPY ["pipeline/docs/enem-redacao/13 enem_regras_computaveis.json", "/app/contracts/enem-redacao/13 enem_regras_computaveis.json"]

# Banco de treino (HAB-01..HAB-56) — mesma classe de bug do canon acima:
# sem esta linha, `treino_habilidades.py` sobe, mas toda a tela /treino
# responde 503 "banco de treino indisponível" no primeiro acesso em produção.
COPY pipeline/docs/treino-habilidades/banco_treino_habilidades_v1.json /app/contracts/treino-habilidades/banco_treino_habilidades_v1.json

ENV SAPIENS_ONTOLOGY_PATH=/app/contracts/ontology/ontology_v1.4.json \
    SAPIENS_CONTRACTS_PATH=/app/contracts \
    ENEM_CANON_PATH="/app/contracts/enem-redacao/13 enem_regras_computaveis.json" \
    TREINO_HABILIDADES_PATH=/app/contracts/treino-habilidades/banco_treino_habilidades_v1.json

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
