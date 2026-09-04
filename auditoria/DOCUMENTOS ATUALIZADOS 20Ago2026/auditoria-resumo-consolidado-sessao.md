## id: RES-2026-08-17T19:00:00Z titulo: Resumo Consolidado da Sessão de Correção Documental timestamp_utc: 2026-08-17T19:00:00Z tipo: registro_consolidado autoridade: registro apenas — não cria norma (GOV-1.0 §1.1)

# Resumo Consolidado — Sessão de 2026-08-17

## 1. Documentos CRIADOS (5)

|Documento|ID|Camada|O que é|
|---|---|---|---|
|`pipeline/docs/00 Governança e Versionamento Sapiens v1.0.md`|GOV-1.0|procedimental|Precedência, estados, transações, versionamento, supersessão, anti-duplicação|
|`pipeline/docs/08 Registro de Extração do WP 1.0.md`|EXT-WP1-1.0|C5|Os 14 elementos perdidos na transição WP1→WP2 (L1–L14), com recomendação por item|
|`pipeline/docs/09 Mapa de Rastreabilidade de IDs.md`|MAP-IDS-1.0|C5|6 gerações de ID, 9 colisões de namespace, 12 grupos de referência pendente|
|`pipeline/docs/10 Especificação do Error Trace v1.0.md`|ETRACE-1.0|C4|Contrato do objeto diagnóstico. Restaura a cadeia causal ordenada|
|`pipeline/docs/01 Manual Oficial de Anotação Cognitiva Sapiens.md`|MAN-1.2|C4|Manual migrado para o espaço canônico (v1.0 da raiz foi removida pelo Curador)|

## 2. Documentos SUBSTITUÍDOS (6)

|Documento|De → Para|Mudança principal|
|---|---|---|
|`ontology_v1.4.json`|1.4 → **1.4.1**|Removido `PROC-ESPACO-03 → ERR-13`; metadados de governança|
|`05 Ontologia Cognitiva Sapiens — v1.4.md`|1.4 → **1.4.1**|Mesma correção na prosa; aritmética do §9; remissões; nome de arquivo|
|`06 Schema Sapiens 2.1.json.md`|2.1 → **2.2**|`ontology_version` obrigatório; `erro` único → `erros_esperados[]` ponderado; bloco `incerteza`; campos provisórios marcados|
|`07 behavior student 1.4.md`|1.0 → **1.1**|`ontology_version`; estatuto do Indicador Comportamental declarado|
|`03 White Paper v2.0.md`|2.0 → **2.0.1**|3 afirmações de fato corrigidas; supersessão parcial da Parte V; aparato de referências|
|`02 Constituicao Sapiens.md`|— → **1.1**|Capítulos 5, 7, 11 e 12 criados (consolidação + deferimentos + registro)|

## 3. Documento APOSENTADO (1)

`04 Ontologia Cognitiva Sapiens — v1.4 JSON.md` → `superseded` por `ontology_v1.4.json`. Duplicata; conteúdo de catálogo removido, stub de proveniência mantido.

## 4. Registros de auditoria (12 arquivos em `auditoria/`)

1 auditoria integral, 2 registros de conflito, 8 registros de transação, 1 este resumo.

## 5. Estado final

- Catálogo: **128 IDs, ontologia 1.4.1**, inalterado em conteúdo. CNI (prosa + JSON) consistente.
- Conflitos fechados: G-CONF-02, 04, 05, 07, 10. Parciais: 06, 08.
- Abertos: G-CONF-01/12 (migração), 03 (numeração 1.6 vs 2.0), 09 (v1.3 ausente), 13 (Plano de Validação).
- **Nenhuma categoria cognitiva criada, alterada ou removida. Nenhum Grau de Liberdade fechado. Ontologia v1.6 NÃO autorizada.**

## 6. Próxima etapa

**13 — Protocolo de Piloto.** Desbloqueada, mas exige decisões de projeto não presentes em nenhum documento: amostra por processo, número de anotadores, limiar de kappa. Aguarda o Curador.