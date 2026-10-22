---
tags: [arquitetura, canon, governanca, ponte]
atualizado: 2026-09-18
---

# O canon pedagógico — ponte para `pipeline/docs/`

> [!important] Este nó **não** reproduz o canon. Ele diz onde ele está e como não
> violá-lo. O canon é grande (centenas de KB), versionado e governado; copiá-lo
> para cá criaria duas verdades.

## GOV-1.0 governa tudo

`pipeline/docs/00 Governanca e Versionamento Sapiens v1.0.md` é um sistema de
governança **estrito e pré-existente** para o corpus em camadas C1–C5. Ele define
front-matter, formato de changelog e o padrão **CNI** (prosa = autoridade de
critério, JSON = autoridade de estrutura).

## O corpus (C1–C5)

| Documento | Onde |
|---|---|
| Constituição Sapiens | `pipeline/docs/constitution/` |
| White Paper v2.0 | `pipeline/docs/white-paper/` |
| Ontologia Cognitiva v1.4 (+ JSON) | `pipeline/docs/ontology/` |
| Schema Sapiens 2.1 | `pipeline/docs/` |
| Manual de Anotação Cognitiva | `pipeline/docs/annotation/` |
| Error Trace v1.0 (`ETRACE-1.0`) | `pipeline/docs/error-trace/` |
| Behavior student 1.4 (`BEH-1.1`) | `pipeline/docs/behavior/` |
| Rastreabilidade de IDs | `pipeline/docs/traceability/` |

O `_superseded/` guarda versões antigas — **não leia de lá** achando que é atual.

## O White Paper 1.0 não está no repo

O WP 2.0.1 §21.1 declara que **todo o aparato de referências** dele é o do White
Paper 1.0 (blocos de Referências dos Capítulos 1, 2 e 4, ~150 entradas), e o
`traceability/08 Registro de Extracao do WP 1.0.md` o cita como fonte. Mas o
arquivo **não existe em `pipeline/docs/`**. Ele vive só no cofre Obsidian do dono,
no iCloud: `medicina/00 - Sapiens/White Paper/00 - Criticas ao White Paper 1.0/0 -
White Paper 1.0.md` (cópia idêntica em `…/Pipeline/Schemas/…/DOCS OFICIAIS/00 WHITE
PAPER 1.0 (ANTIGO).md`). Na mesma pasta está a crítica integral ao WP 1.0, capítulo
por capítulo. Quem precisar da bibliografia ou da fundamentação teórica (Cap. 1 é a
revisão das teorias de aprendizagem) vai lá, não ao repo.

## `apoio_externo` não é ontologia

`pipeline/docs/enem-redacao/` é um canon documental extraído da cartilha oficial do
INEP/MEC ("A Redação do Enem 2025", 78 páginas, SHA-256 `d8ab44dc...b870288`). Três
documentos:

- `11 … Extracao da Fonte Oficial.md` — extração fiel, rastreável por página;
- `12 … Matriz de Correcao Estruturada.md` — interpretação + **9 ambiguidades
  registradas** (ex.: AMB-07, se o teto de 40 pts por tangenciamento vale para as
  Competências I/IV);
- `13 enem_regras_computaveis.json` — regras legíveis por máquina, par CNI com o
  doc 12.

Os três carregam `estado: apoio_externo` por GOV-1.0 §1.1, que nomeia a matriz do
Enem como o exemplo canônico de material externo **não normativo**.

> [!danger] Isto **não** faz parte da ontologia cognitiva Sapiens (C1–C5) e nunca
> deve ser tratado como tal.

## Dois defeitos conhecidos em `13 enem_regras_computaveis.json`

O código de `aluno/backend/redacao/` **contorna os dois defensivamente**. Não são
bugs do nosso lado:

1. A chave de topo `"titulo"` aparece **duas vezes** no mesmo objeto JSON — uma
   como título do documento, outra como a regra `TITULO-01`. `json.load` mantém
   só a segunda, e o título do documento fica inalcançável por essa chave.
2. `COMP-II` não tem o campo `cap_por_tangenciamento` que `COMP-III`/`COMP-V` têm,
   embora a prosa do doc 12 §1 afirme que o teto de 40 pontos vale para II, III e
   V. Parece omissão de digitação, **não** uma das 9 ambiguidades registradas.

## Extrair do PDF, se precisar de novo

100% local, sem API paga. `pdftotext` é **inútil** aqui: a fonte embutida tem cmap
quebrado e corrompe texto acentuado no corpo. O caminho que funciona é
`pdftoppm` (poppler) → `tesseract` (pacote `por`). **As 5 tabelas de nível
(Competências I–V) precisam de conferência visual** nas imagens renderizadas — o
OCR em `psm 6` descarta linhas de tabela em silêncio.

## O Error Trace de verdade ainda não é possível por alternativa

Os distratores **não têm `tipo_erro` (ERR-NN) atribuído por alternativa** — só
`explicacao` em texto livre. Um produtor automático por alternativa específica
exige anotação nova no pipeline primeiro. `DEPLOY.md` §7 já registra isso como fora
de escopo até haver evidência longitudinal e especificação estatística. O que
existe hoje é a junção em [[motor-cognitivo]].

---
Relacionado: [[redacao]] · [[motor-cognitivo]] · [[pipeline-e-corpus]]
