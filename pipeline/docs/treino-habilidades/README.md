# `pipeline/docs/treino-habilidades/` — banco canônico de questões de treino

`banco_treino_habilidades_v1.json` contém as questões de treino autorais, uma
base de 4–5 questões por habilidade observável (`HAB-01`..`HAB-56`,
`ontology_v1.4.json`), gerado a partir dos 56 arquivos-fonte em markdown do
autor do produto (fora deste repositório) pelo script
[`pipeline/scripts/gerar_banco_treino_habilidades.py`](../../scripts/gerar_banco_treino_habilidades.py).

Diferente do canon de `enem-redacao/`, este arquivo **não é apoio externo** —
é conteúdo autoral do Sapiens, indexado 1:1 pelos códigos HAB reais da
ontologia cognitiva (`habilidades_observaveis` em `ontology_v1.4.json`).
Não redefine nem deriva nenhuma categoria da ontologia; só referencia os
`hab_id` já existentes.

Consumido por `aluno/backend/treino_habilidades.py`. O código HAB, o nome da
habilidade e o conteúdo das questões (enunciado, alternativas, gabarito,
elucidação) nunca são alterados por código — só re-estruturados do markdown
de origem para JSON. `HAB-38` tem 4 questões-base em vez de 5 (lacuna
conhecida no arquivo-fonte).

Para regenerar após correção no arquivo-fonte:

```bash
python3 pipeline/scripts/gerar_banco_treino_habilidades.py "<pasta com os 56 .md>" \
  pipeline/docs/treino-habilidades/banco_treino_habilidades_v1.json
```
