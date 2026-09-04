# Plano de reset seguro — itens/seeds pré-Schema 2.1

**Registrado em:** 2026-08-17T03:39:56Z
**Status:** PLANO APENAS — nada foi executado. Nenhum código, dado ou documento foi alterado.
**Gatilho:** usuário confirmou que os 20 documentos da coleção Firestore `itens` são exclusivamente dados de teste/seed, sem necessidade de preservação. Este plano estende essa decisão a todo o restante do estado de item/questão pré-Schema-2.1, e identifica precisamente o que pode ser removido antes da primeira geração real usando o contrato canônico (`pipeline/docs/Schema anotador de questoes/06 Schema Sapiens 2.1.json.md`).

Referências: `auditoria/AUDITORIA-MIGRACAO-ITEM-2.1.md` (mapa completo de leitura/escrita/formatos), `auditoria/AUDITORIA-SCHEMA-ITEM-2.1.md`, `auditoria/ESTADO-CONSOLIDACAO.md`.

---

## Princípio do reset

Tudo que existe hoje como item/questão foi gerado no **Formato A** (`DEFAULT_PIPELINE_SCHEMA`, pré-canônico) ou é conteúdo autoral solto (Feed). Nenhum documento em nenhuma coleção listada abaixo foi gerado usando o Schema 2.1. Como o objetivo é começar a gerar com o contrato canônico, e o conteúdo atual não é reaproveitável estruturalmente (§3 da auditoria de migração), a opção mais limpa é **zerar o estado de item antes da primeira geração real**, em vez de tentar migrar/remendar dado incompleto.

O reset é restrito a **itens/anotações/artefatos e seeds diretamente relacionados**. Não inclui: contas de usuário, sessões, ontologia (já consolidada para v1.4 numa rodada anterior), dados de `professor` (`imports`), ou qualquer coleção fora do escopo de item/questão.

---

## 1. O que PODE ser removido (itens/anotações pré-2.1)

| # | Onde | Documentos | Conteúdo | Ação recomendada |
|---|---|---|---|---|
| 1 | Mongo `sapiens_pipeline.pipelines` | 1 doc (`id: b912a1b8-aefd-44ca-83ed-2399181aa8a5`) | Item de teste gerado nesta sessão de auditoria (upload de imagem em branco — "Nenhuma questão detectada"). Formato A. | `db.pipelines.deleteMany({})` — coleção inteira, é só esse 1 doc de teste. |
| 2 | Firestore `itens` (projeto `sapiens-dataset`) | 20 docs | Espelho do Mongo `pipelines` via `firestore_sync.py`. Confirmado pelo usuário: dado de teste/seed. Formato A, nenhum no Schema 2.1. | Apagar a coleção inteira (todos os 20 IDs, listados no Apêndice A). |
| 3 | Object Storage da Emergent (`sapiens-cognitive/questions/{question_id}/...`) | Artefatos (PDF/imagem original, extração, `pipeline.json`) do item `b912a1b8-...` gerado nesta sessão | Binários do único item que passou pelo Mongo local. Os outros 19 itens do Firestore não têm registro correspondente neste Mongo local — seus artefatos, se existirem, estão órfãos na infraestrutura da Emergent, fora do alcance desta auditoria local. | Remover via API de storage (`DELETE` nos paths listados no Apêndice B) **quando/se** a limpeza de object storage entrar em escopo — não é urgente porque não bloqueia a adoção do Schema 2.1 (o schema não rege nomes de arquivo binário). |
| 4 | Mongo `sapiens_aluno.questoes_master` | 0 docs | Formato B (réplica editável do Firestore `itens`). Já vazia. | Nenhuma ação necessária — só confirmar que segue vazia após o passo 2. |
| 5 | Mongo `sapiens_aluno.questoes_public` | 0 docs | Formato B (versão pública). Já vazia. | Nenhuma ação necessária. |
| 6 | Mongo `sapiens_aluno.question_annotations` | 0 docs | Formato C (`/admin/annotations`, ingestão manual). Já vazia. | Nenhuma ação necessária. |
| 7 | `pipeline/backend/tests/*`, `pipeline/*_test.py`, `pipeline/manual_*.py` | fixtures com `"ontology_version": "1.0.0-seed"` | Não são itens em si, mas fixtures de teste que assumem o mundo pré-consolidação. Já documentado em `ESTADO-CONSOLIDACAO.md` como pendência não crítica. | Fora do escopo deste reset de dados — é código de teste, tratar separadamente se algum dia esses testes forem reativados. |

**Total a remover para zerar item/questão: 1 doc Mongo + 20 docs Firestore = 21 registros de item, todos confirmados como teste/seed.**

---

## 2. O que NÃO deve ser tocado por este reset (fora de escopo)

| Onde | Documentos | Por quê fica de fora |
|---|---|---|
| Mongo `sapiens_aluno.feed_items` | 15 | Formato E — conteúdo autoral/demo do Feed, **não deriva do pipeline nem do Schema 2.1**. Resetar itens do pipeline não afeta essa coleção; decisão sobre o Feed é independente (levantada na auditoria de migração, §4, ainda sem contrato canônico associado). |
| Mongo `sapiens_aluno.feed_interactions` | 2 | Depende de `feed_items` acima — mesma lógica, fora de escopo. |
| Mongo `sapiens_aluno.exams` / `answer_keys` | 2 / 3 | Gabaritos oficiais ENEM (número+letra), não representam item/questão completo — não colidem com o Schema 2.1 e não são afetados pelo reset. |
| Mongo `sapiens_aluno.analyses` | 1 | Histórico de tentativas de prova de usuário real (conta `auditoria.teste@gmail.com` criada durante os testes desta sessão). Referencia `exam_id`/`number`, não `item_id` — não é dado de item, é dado de usuário. **Não remover** sem instrução explícita separada. |
| Mongo `sapiens_pipeline.ontologies` | 2 (v1.4 ativa + 1.0.0-seed arquivada) | Já consolidado numa rodada anterior (`ESTADO-CONSOLIDACAO.md`). Não é item/questão — é ontologia. Fora de escopo aqui. |
| Mongo `sapiens_pipeline.pipeline_schemas` | 0 | Já vazia (nenhum schema custom foi importado). Nada a remover. |
| Contas de usuário (`sapiens_aluno.users`, `sapiens_professor.users`) e sessões | — | Dado de identidade, não de item. Fora de escopo. |
| `sapiens_professor.imports` | — | Dados de turma/aluno agregados, sem vínculo com item/questão. Fora de escopo (já tratado em `ESTADO-CONSOLIDACAO.md`). |

---

## 3. Ordem de execução recomendada (quando autorizado)

1. Apagar Firestore `itens` (os 20 documentos, Apêndice A) — é a cópia "pública" espelhada, remover primeiro evita qualquer sync acidental recriar o Mongo a partir dela.
2. Apagar Mongo `sapiens_pipeline.pipelines` (o 1 doc de teste).
3. Confirmar que `questoes_master`/`questoes_public`/`question_annotations` continuam vazias (nenhuma ação, só verificação).
4. (Opcional, não bloqueante) Limpar os artefatos binários órfãos no object storage da Emergent — pode ficar para depois, não impede a primeira geração real com o Schema 2.1.
5. Gerar o primeiro item real via `pipeline` **somente depois** que `cognitive_engine.py:DEFAULT_PIPELINE_SCHEMA` for atualizado para o Schema 2.1 (mudança de código, fora do escopo deste plano — ver `auditoria/AUDITORIA-MIGRACAO-ITEM-2.1.md §4`). Gerar antes disso recriaria o Formato A antigo dentro de coleções recém-zeradas, desperdiçando o reset.

**Nenhum desses passos foi executado.** Este documento é o plano; a execução requer autorização e instrução explícitas em uma próxima etapa.

---

## Apêndice A — IDs Firestore `itens` a remover (20)

```
08746adf-8f97-4b56-bddb-14fe4c4db274
116e4dfa-1990-44fe-b9da-973fd867ae3d
1e688330-0b97-4baa-be7f-27cd732cde60
2312117e-d0cf-4e03-83c1-38dac86f5bca
2e079764-e6ef-469e-bce8-93bf592ee862
3960026c-0183-4a1f-a6b3-d0c81a25b8c1
4221aac5-8fc2-4253-820a-cc1bd64ef4c7
583e6a59-5b4e-4b11-8e6f-2cdc60dcd881
6542647b-09ea-4421-9a4f-a61b9d027bb1
75b07dab-58d4-47b7-895b-a95f4d13ca9b
7f397330-1686-4f8b-8fe6-129889f863c2
84cae0c0-707e-47cb-95eb-0cbb1d9982eb
89dc8093-5dd4-47e1-a7d6-4ebabe5dd466
92fc3f6b-98c3-47c5-a7ac-4ef6ac78f919
93c88b1a-0069-40ad-a86f-3111645f1572
9b537bef-835a-433a-b2c6-f91c0d914770
b912a1b8-aefd-44ca-83ed-2399181aa8a5   ← mesmo ID do doc de teste no Mongo pipelines
caa40f02-4aeb-408b-a5d9-db4d0689aee7
d09ec013-3971-4837-a6ad-8c9bd95edb9f
d5cf9dff-2ea5-4239-ba9c-060d92956d1e
```

## Apêndice B — path de object storage do item de teste local

```
sapiens-cognitive/questions/b912a1b8-aefd-44ca-83ed-2399181aa8a5/original/...
sapiens-cognitive/questions/b912a1b8-aefd-44ca-83ed-2399181aa8a5/extraction/extraction.json
sapiens-cognitive/questions/b912a1b8-aefd-44ca-83ed-2399181aa8a5/pipeline/pipeline.json
```
(Padrão de path definido em `pipeline/backend/storage.py:build_path`. Os outros 19 itens do Firestore não têm `question_id` correspondente neste Mongo local, então seus eventuais artefatos não puderam ser localizados a partir daqui.)
