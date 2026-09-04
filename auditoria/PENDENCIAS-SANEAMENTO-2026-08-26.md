# Pendências do saneamento — o que NÃO foi corrigido, e por quê

**Data:** 2026-08-26 (atualizado — incorporação dos recortes manuais de 2022 MT)
**Estado do saneamento:** fases 0–3 concluídas · fase 4 parcial · recortes
manuais de ENEM 2022 Matemática (136-180) incorporados como `visual_assets`.
**Regra que produziu esta lista:** quando não há evidência determinística para
corrigir um dado, ele é preservado e registrado aqui. Nada nesta lista foi
inferido, adivinhado ou "corrigido pelo melhor palpite".

## 0. Atualização — recortes manuais de ENEM 2022 Matemática

`pipeline/scripts/ingerir_recortes_manuais_2022mt.py` incorporou os 44 (de 45)
recortes manuais do usuário como `visual_assets` verificados, substituindo os
recortes automáticos anteriores (que tinham defeitos documentados: vazamento
de texto, marca d'água, cota destruída). Duas correções de mapeamento
aplicadas com evidência determinística, não invenção:

- **Q163 IMG-01/02** estavam dentro da pasta `Q163 .../` nomeados `Q162__IMG-
  01/02.png` por engano. O conteúdo (dobradura de papel) bate com a descrição
  do MODELO para Q163 no banco ("sequência de dobraduras"; "marcação do ponto
  R"), não com Q162 (cartela de bingo) — confirmado por inspeção visual das
  duas imagens contra as duas descrições. Remapeado para Q163.
- **Q163 alternativa B** era uma cópia byte-idêntica do arquivo da
  alternativa A (SHA-256 igual). Comparado contra a página 25 do PDF oficial
  do INEP: a alternativa A do recorte manual bate com a alternativa A real da
  página; B, não — B na página real é um círculo liso. Recortado diretamente
  do PDF oficial, no bbox do cluster vetorial ancorado no rótulo "B", e
  conferido visualmente antes de gravar.

**21 questões corrigidas, 1 sem evidência (Q177 — ver §1 abaixo, inalterado).**
Ver `auditoria/RESUMO-SANEAMENTO-2022MT-2026-08-26.md` para os detalhes por
questão e a explicação de por que a paridade total com o trabalho manual do
usuário (interlaçar texto↔figura, ordem exata dentro do enunciado) segue como
limitação de contrato, não deste script.

**Firestore `itens` pendente de sincronização** — cota diária de leitura/
escrita da Firebase (`ResourceExhausted 429`) esgotada durante a execução.
Os três stores Mongo (`pipelines`, `questoes_master`, `questoes_public`) já
refletem o estado final; falta replicar para o Firestore, que é a fonte de
onde produção puxa via `_auto_sync_loop`. Comando pronto, idempotente,
para rodar quando a cota resetar:

```bash
cd pipeline/backend && ./.venv/bin/python ../scripts/ingerir_recortes_manuais_2022mt.py --apply
```

(sem `--skip-firestore` desta vez — os stores Mongo já estão corretos e a
reexecução é um no-op para eles; só a etapa Firestore vai executar.)

---

## 1. Conteúdo textual ausente — 20 itens BLOQUEADOS

Exigem o texto real da prova. Nem o gabarito oficial nem o PDF via extração
determinística fornecem: o modelo pulou tokens na transcrição e não há como
recuperá-los sem reanotação (LLM) ou transcrição humana.

**EST-02 · alternativa sem texto (18 itens)**

| Caderno | Questões |
|---|---|
| ENEM 2022 | 111, 124, 126, 132, 133, 137, 140, 161 |
| ENEM 2023 | 101, 157 |
| ENEM 2024 | 104, 120, 124, 138, 140, 165, 174, 176 |

O `README.md` do ground truth manual traz a sequência correta de **duas** delas
— Q137 (C = `4,800`) e Q140 (D = `R$ 42,00 maior`). São transcrição humana, não
extração; entram quando houver uma via de ingestão de correção humana.

**EST-01 · enunciado vazio (2 itens):** ENEM 2022 Q125 e Q180.

**Efeito atual:** os 20 estão fora de circulação pelo cerco (`bloqueados.json`)
e o frontend passou a recusar a seleção de alternativa sem texto. Nenhum aluno
consegue respondê-los.

---

## 2. Questão anulada — 1 item, permanentemente bloqueado

**ENEM 2024 Q102.** Anulada pelo INEP (gabarito oficial `2024_GB_impresso_D2_CD5.pdf`).
Zero alternativas corretas, `resposta_correta = None`, `gabarito_oficial.status
= "anulada"`. Continua marcada BLOQUEADO no auditor **de propósito**: não é um
defeito a resolver, é um estado final correto.

---

## 3. Lacunas do corpus — 2 questões nunca persistidas

| Caderno | Questão | Status oficial |
|---|---|---|
| ENEM 2022 | 175 | anulada |
| ENEM 2023 | 177 | anulada |

Declaradas no manifesto do caderno (90 entradas), ausentes do banco (89 itens).
Ambas anuladas pelo INEP, então a lacuna não tem custo pedagógico.
**Não foram criadas** — inventar item é proibido. Reprocessá-las exigiria Gemini.

---

## 4. Elementos visuais — 108 assets INCERTOS (contagem original, corpus inteiro)

> **Nota (ver §0):** os assets automáticos das 21 questões de ENEM 2022 MT
> resolvidas em §0 foram SUBSTITUÍDOS por recortes verificados
> (`estado: "verificada_manual"`), saindo desta contagem. O número abaixo
> descreve o estado antes de §0 e continua valendo integralmente para 2023 e
> 2024, que não foram tocados nesta rodada (fora do escopo pedido: só 2022 MT).

Preservados, com `verificacao.estado = "incerta"` e o motivo registrado no
próprio asset. Nenhuma geometria foi inventada para eles.

| Motivo | Assets |
|---|---:|
| caso sem geometria registrada no manifesto | 75 |
| bbox cruza a calha entre colunas | 26 |
| questão sem região naquela página/coluna | 4 |
| bbox fora da região da questão | 2 |
| sem caso no manifesto congelado (ENEM 2022 Q171) | 1 |

**Por que não foram re-extraídos:** o modelo de layout determina a **região da
questão** (90/90 questões, validado por teste), mas não existe detector validado
de *figura dentro da região*. Escolher um bbox novo seria escolher
arbitrariamente entre reconstruções indistinguíveis — a regra de parada manda
preservar. Destravar isto exige um segmentador de blocos tipográficos
(auditoria §4, estágios 2–4), que é trabalho de construção, não de saneamento.

**ARQ-04 · 71 itens declaram recurso visual e não entregam nenhum.** Mesma
causa. O recurso declarado permanece no item; nenhum asset foi fabricado.

**3 blobs órfãos** no storage (`.webp`), sem referência. **Preservados** —
apagar arquivo sem necessidade está fora do escopo.

---

## 5. Sinais de qualidade que sobrevivem, e não são defeitos a corrigir

**GAB-06 · 7 itens** em que `qualidade.observacoes` cita uma letra diferente da
oficial. Depois da correção do gabarito, este achado mudou de significado: mede
"a prosa do anotador discorda do INEP", ou seja, qualidade da anotação. É
telemetria útil, não erro do item. Nenhuma ação.

**EST-05 · 26 itens** com placeholder fabricado no texto (`[Gráfico de barras…]`).
Removê-lo deixaria uma lacuna sem o elemento visual que deveria ocupá-la — pior
que o marcador. Resolve-se junto com a recuperação visual (item 4).

**GOV-03 · 105 itens** com `item_hash` de topo divergente de `item.item_hash`.
Herdado do `apply_visual_assets` de 24/08, que recalculava o hash ao aplicar
assets. **Não corrigido de propósito:** `item_hash` é a chave de junção dos 249
eventos de behavior já gravados; recalcular orfanaria o histórico. A correção
correta é a separação `item_hash` (conteúdo) × `render_hash` (pixels), que muda
o contrato — fase 4, fora do escopo de saneamento.

---

## 6. Ground truth manual — defeitos que exigem decisão humana

Nenhum arquivo foi renomeado ou apagado (proibido nesta execução).

1. **A pasta `ENEM 2023 Amarelo/` contém material de 2022.** O gabarito do
   `README.md` bate 45/45 com o oficial do INEP de **2022**, inclusive
   `175 Anulado`, e os enunciados citados só existem no caderno de 2022. Os
   nomes dos arquivos (`ITEM-ENEM-2022-…`) estão corretos; a pasta não.
2. **`Q163 ENEM 2022 Amarelo/` contém dois PNG nomeados `…Q162__IMG-01/02`**,
   com conteúdo diferente dos Q162 do nível de cima — são figuras da Q163 com
   nome errado, não duplicatas.
3. **`Q163__IMG-A.png` e `Q163__IMG-B.png` são byte-idênticos** — uma das cinco
   alternativas foi capturada duas vezes.
4. **Conflito interno no README:** a lista diz `167 B`; a observação em prosa diz
   *"Q167: Alternativa correta A"*. O oficial do INEP é **B** — a lista está
   certa. Único conflito em 45 entradas.

---

## 7. Revisão humana — 0 registros

A coleção `sapiens_pipeline.revisoes_humanas` existe e está vazia. Nenhum item
do corpus tem `apto_para_camada_de_crenca = true`, o que é o estado correto: o
portão só abre por registro humano explícito (`revisao_humana.registrar()`),
com revisor identificado e amarrado ao `item_hash` revisado.

**Consequência operacional:** enquanto não houver revisão registrada, nenhum
evento de behavior alimenta o agregado cognitivo. O modo do portão é `crenca`
(padrão): o aluno pratica normalmente, o mapa de habilidades não se move. Ligar
`PORTAO_CRENCA_MODO=circulacao` hoje esvaziaria a prova — é decisão de produto,
não de saneamento.

---

## 8. Produção

O cerco de circulação e o congelamento do auto-sync valem **apenas no ambiente
local**. Produção roda no Fly.io contra MongoDB Atlas; o Firestore é o mesmo
projeto (`sapiens-dataset`) e **já recebeu todas as correções**, então o
`_auto_sync_loop` de produção propaga gabarito, portão e assets para o Atlas
sozinho. O que **não** está em produção é o código: cerco, portão, validações
EST/ARQ e as correções de frontend exigem deploy.

## 9. Atualização 2026-08-27 — Q177 e reconstrução vetorial nos 3 cadernos

**Q177/2022 resolvida.** A tabela de 13 dias é composta por glifos vetoriais
(não texto real), e por isso nunca havia sido capturada. Recorte determinístico
direto do cluster vetorial (`pipeline/scripts/ingerir_recortes_manuais_2022mt.py`
absorveu a correção), conferido contra a imagem enviada pelo usuário.

**Novo motor: `pipeline/backend/vector_figure_finder.py`.** Localiza candidatos a
figura/tabela/gráfico por RESÍDUO — palavras e desenhos vetoriais da região da
questão que não casam com o enunciado/alternativas já transcritos — em vez de
depender de imagem raster embutida (que só existe em 2023/2024; 2022 é quase
100% vetorial). Cada candidato é uma HIPÓTESE; nenhum virou asset sem inspeção
visual direta por página renderizada.

Dois bugs de `layout_model.py` corrigidos no processo (cobertos por teste):
continuação de coluna que inflava regiões para páginas inteiras quando um
marcador "QUESTÃO N" não era detectado (`regioes_por_questao`), e janela de
indentação da margem de alternativa (`abs(x-col_x0)<12` não reconhecia o
recuo real de ~31pt e ~62 tabelas/figuras nunca eram varridas).

**80 novos assets aplicados** (Mongo; Firestore pendente — cota diária
excedida, comando pronto abaixo), verificados um a um por inspeção visual:

| Prova | Questões resolvidas | Figuras principais | Figuras de alternativa |
|---|---:|---:|---:|
| 2022 (CN, 91-135) | 14 | 18 | 10 |
| 2023 | 27 | 28 | 8 |
| 2024 | 10 | 12 | 4 |

Todas via `pipeline/scripts/aplicar_visuais_vetoriais.py`, invariantes
verificados: `item_hash` 0 alterações, enunciado/alternativas/gabarito 0
alterações, testes sem regressão.

**Ainda pendentes (sem candidato confiável, não inventado):** 2022 CN — Q96,
Q106, Q122; 2023 — Q144,168,172,178, e as letras D/E não rotuladas de Q119;
2024 — Q98,100,103,104,109,110,119,122,123,124,126,133,144,146,151,152,153,
161,162,168,175,178,179, e a letra E de Q135. A maioria é bloco de citação
bibliográfica ou gráfico sem rastro vetorial localizável pelo método atual —
exigem inspeção página-a-página adicional ou anotação manual.

**Firestore pendente** — mesmo comando de sincronização documentado em §0.
