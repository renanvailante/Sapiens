# Lote inicial de questões reais — ENEM 2023, 2º dia, Caderno 11 (Laranja)

**Registrado em:** 2026-08-22
**Natureza:** registro de execução. Sob GOV-1.0 §1.1, `auditoria/` não cria norma.
**Fonte:** [prova oficial do INEP](https://download.inep.gov.br/enem/provas_e_gabaritos/2023_Dia_2_P1_MT_Caderno_11_Laranja_NVDA.pdf) (63 páginas, 45 questões, 136–180) + [gabarito oficial do mesmo caderno](https://download.inep.gov.br/enem/provas_e_gabaritos/2023_GB_impresso_D2_CD11.pdf).

Selecionadas as 8 primeiras questões não anuladas (a 138 foi anulada pelo INEP e ficou de fora). Interrompido por esgotamento de cota da Gemini.

---

## 1. Situação por questão

| Questão | Estado | `item_id` | Gabarito oficial | Extraído | Validação |
|---|---|---|---|---|---|
| **136** | ⏸️ pendente — **429/cota** | — | E | — | — |
| **137** | ✅ processada | `ITEM-INEP-2023-ENEM2023D2CD11-Q137` | B | **B** ✓ | válida |
| 138 | — anulada pelo INEP, fora do lote | — | Anulado | — | — |
| **139** | ✅ processada | `ITEM-INEP-2023-ENEM2023D2CD11-Q139` | E | **E** ✓ | válida |
| **140** | ✅ processada | `ITEM-INEP-2023-ENEM2023D2CD11-Q140` | E | **E** ✓ | válida |
| **141** | ⏸️ pendente — **429/cota** | — | B | — | — |
| **142** | ⏸️ pendente — **429/cota** | — | D | — | — |
| **143** | ⏸️ pendente — **429/cota** | — | A | — | — |
| **144** | ⏸️ pendente — **429/cota** | — | D | — | — |

**3 processadas · 3 válidas contra o Schema 2.2 · 3/3 com gabarito conferindo o oficial.**

**5 pendentes, todas exclusivamente por `429 RESOURCE_EXHAUSTED`** da Gemini API — nenhuma falhou por erro de conteúdo, contrato ou código. As tentativas de retomada bateram na mesma cota.

### Classificação cognitiva das processadas

| Questão | Assunto | Processos | Domínios |
|---|---|---|---|
| 137 | Tíquetes de metrô, duas colorações | `PROC-SIMB-01`, `PROC-QUANT-02` | DOM-SIMBOLICO, DOM-QUANT |
| 139 | Escada de concreto, três degraus | `PROC-ESPACO-02`, `PROC-ESPACO-01` | DOM-ESPACO |
| 140 | Cinco caixas de supermercado | `PROC-QUANT-02`, `PROC-TEXT-01` | DOM-QUANT, DOM-TEXTUAL |

Onde estão: Mongo local `sapiens_pipeline.pipelines` (3 documentos) e espelho `firestore/itens` (3 documentos). **Não sincronizadas para a produção do aluno** — o `questoes_public` do Atlas segue em 0.

---

## 2. Verificação do fluxo pedido

Pedido: `ENEMExtractor → LOTUS → anotação Sapiens → Schema 2.2 → validação → sync`.

| Estágio | Estado real |
|---|---|
| **ENEMExtractor** | `pipeline/backend/enem_service.py` existe e envolve o pacote `enem` v1.0.4 (disponível no PyPI), mas **não está instalado nem conectado a rota alguma** — `grep enem_service pipeline/backend/server.py` → 0 ocorrências. Módulo órfão. |
| **LOTUS** | **Não existe.** Zero ocorrências em código nos três apps. Aparece apenas em `auditoria/ESPECIFICACAO-MIGRACAO-SCHEMA-2.1-E-PIPELINE.md`, que já o registrava como *"arquitetura pretendida fornecida externamente, não rastreável a `pipeline/docs/`"*. |
| **Anotação → Schema 2.2** | ✅ Funciona. |
| **Validação** | ✅ Funciona — e pegou defeitos reais neste lote (§3). |
| **Sync** | ✅ Funciona (Mongo → espelho Firestore). |

**Fluxo realmente implementado hoje:**

```
PDF/imagem → UMA chamada multimodal ao Gemini (extração + classificação juntas)
           → normalize_item (Schema 2.2) → validate → Mongo + espelho Firestore
```

Não há estágio de extração determinística separado nem camada de orquestração. Nada disso foi construído nesta rodada: implementar LOTUS ou conectar o `enem-extractor` seria camada arquitetural nova, explicitamente fora de escopo.

---

## 3. Defeitos encontrados e corrigidos

Todos apareceram ao processar questões **reais** — nenhum aparecia com a questão sintética usada nos testes anteriores.

### 3.1 O modelo alucinava a procedência (`fonte`)

Numa prova de **2023**, o modelo devolveu `ano: 2010` na Q137 e `ano: 2016` na Q144, além de inventar `prova` diferente a cada questão. Como `banca/ano/prova/numero` compõem o `item_id` determinístico, o efeito era:

```
ITEM-INEP-2023-ENEM-Q136
ITEM-INEP-2010-ENEMCADERNOAZUL-Q137        ← ano errado
ITEM-ENEM-2023-MATEMTICAESUASTECNOLOGIAS-Q139
ITEM-7e6e3c25e7f047fd98ad9f54a8ddcca6      ← caiu no id opaco
ITEM-ENEM-2016-CADERNOAZUL-Q144            ← ano errado
```

Cinco formatos para questões do mesmo caderno, dois com ano factualmente errado.

**Correção.** `/pipeline/generate` passa a aceitar `?fonte={json}` com a procedência já conhecida, que **sobrescreve** a inferida pelo modelo. É o mesmo mecanismo que `book/process` já usava para injetar `fonte.numero`. O Manual §8 sustenta: `disciplina` e afins são metadado de manifestação, não algo a inferir do conteúdo. O prompt também passou a exigir cópia literal do que está impresso, com `null` quando ausente — *"um ano errado é pior que um ausente"*.

Resultado: os 8 itens passaram a produzir `ITEM-INEP-2023-ENEM2023D2CD11-QNNN`, estável e determinístico.

### 3.2 Caixa da letra da alternativa

O modelo alternava entre `'A'` e `'a'`. A letra é comparada com o gabarito oficial **e com a resposta do aluno** — divergir por caixa marcaria errado quem acertou, sem erro visível. Ocorreu em 5 das 8 questões.

**Correção.** `normalize_item` padroniza para maiúscula. Com isso, **8/8 passaram a conferir com o gabarito oficial do INEP**.

**Erro que cometi ao corrigir, e o que ele ensina:** normalizei só `questao.alternativas[].letra` e esqueci `distratores[].alternativa`. Os dois referenciam a mesma coisa; normalizar um lado fez o distrator deixar de casar com a alternativa que descreve, e a validação passou a acusar `"'a' não é uma alternativa incorreta do item"` em 21 ocorrências — a validade caiu de 7/8 para 1/8. Corrigido normalizando os dois lados juntos, com teste que cobre o par.

### 3.3 `mecanismo` em texto livre

Na Q142 o modelo escreveu `"Falha em localizar dado explicito"` no campo `mecanismo`, que só aceita `MEC-01`..`MEC-13`. A validação rejeitou o item inteiro.

**Correção.** `normalize_item` descarta valor de `mecanismo` fora do vocabulário. A justificativa é do próprio contrato: o campo é **opcional e provisório** (Error Trace §4.2 — *"nenhuma anotação é inválida por omiti-lo"*). Invalidar a anotação toda por um campo que poderia simplesmente não existir joga fora a classificação cognitiva por nada.

A regra de contrato continua valendo no validador, para quem grave o item por outro caminho — os dois comportamentos são corretos em camadas diferentes, e há um teste para cada.

---

## 4. Observação registrada, não corrigida

**`arquivo_origem` também é alucinado.** Das 3 questões processadas, duas trazem `"Screenshot for page 1"` e `"screenshot_page_1.png"` — nomes que o modelo inventou. O servidor só preenche o campo quando o modelo não o preencheu (`if arquivo_origem and not fonte.get("arquivo_origem")`), então o valor real é descartado em favor do inventado.

É a mesma família do defeito §3.1 e a correção seria análoga (deixar o servidor sobrescrever). **Não aplicada**: o pipeline foi congelado a pedido, e o campo não entra em `item_id`, `item_hash` nem em decisão pedagógica — o dano é de rastreabilidade, não de correção.

---

## 5. Como retomar as 5 pendentes

Nenhuma mudança de código é necessária. Com a cota da Gemini renovada:

1. Subir o pipeline local (`uvicorn server:app` em `pipeline/backend`).
2. Para cada questão pendente (136, 141, 142, 143, 144), `POST /api/pipeline/generate` com o PDF de uma página e `?fonte={"banca":"INEP","ano":2023,"prova":"ENEM-2023-D2-CD11","numero":<N>,"disciplina":"Matemática e suas Tecnologias"}`.
3. Conferir o gabarito extraído contra o oficial do Caderno 11.
4. Sincronizar para a produção do aluno com `POST /api/admin/firestore/sync` no backend público.

Os PDFs por questão e o manifesto com o gabarito ficaram em `/tmp/enem/` — diretório temporário, que não sobrevive a um reinício da máquina. Reproduzir é baixar a prova e o gabarito do INEP de novo.

---

## 6. Fora de escopo, não implementado

`enem-extractor` conectado ao fluxo · LOTUS · Error Trace Producer · Ontologia v1.6 · publicação do pipeline.
