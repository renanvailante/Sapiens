# Auditoria técnica — extração e representação de questões e elementos visuais

**Data:** 2026-08-25
**Escopo:** `pipeline/backend/figure_extractor.py`, `pipeline/scripts/extract_book_visuals.py`, `pipeline/scripts/apply_visual_assets.py`, `pipeline/scripts/ingest_manual_crops.py`, `pipeline/backend/cognitive_engine.py` (schema + prompts), `pipeline/backend/item_contract.py`, `pipeline/backend/ontology_validator.py`, `pipeline/backend/server.py` (rotas de caderno), `pipeline/backend/enem_service.py`, sincronização `pipeline → Firestore → aluno`, `aluno/backend/exam_images_routes.py`, `aluno/backend/admin_routes.py`, `aluno/backend/firestore_routes.py`, `aluno/frontend/src/pages/ExamSelect.jsx`.
**Ground truth:** `cadernos enem/revisao humana imagens cadernos/` (README com gabarito oficial + 46 recortes manuais, ENEM 2022 Amarelo D2 CD5, questões 136–180).
**Ações executadas:** somente leitura. Nenhuma escrita em Mongo/Firestore, nenhum deploy, nenhum arquivo de produção alterado.

---

## 0. Resumo executivo

A auditoria encontrou **dois problemas de gravidade diferente**, e o mais grave não é o visual.

**O mais grave: o gabarito do banco está errado em 36% do bloco 136–180.** 16 das 44 questões persistidas marcam como correta uma alternativa diferente do gabarito oficial do INEP. Como `POST /students/me/answer` calcula `acertou` exclusivamente a partir de `alternativas[].correta`, **um aluno que acerta essas questões é informado de que errou**, e o evento de behavior gravado no Firestore (permanente, alimenta a camada de crença) registra o erro invertido. Em 5 desses 16 casos, o próprio modelo escreveu a letra correta em prosa dentro de `qualidade.observacoes` e marcou outra letra em `correta` — ou seja, é falha de serialização, não de raciocínio, e nada no sistema compara os dois campos.

**O visual: taxa de entrega de 35%, e nenhum recorte entregue está limpo.** Contra o ground truth humano de 46 elementos visuais em 136–180, o sistema entregou 16. Dos 14 que inspecionei pixel a pixel, 3 estão aceitáveis e 11 têm defeito — vazamento de texto do enunciado dentro do recorte, faixa de marca d'água na borda, legenda ("Figura 1") perdida ou cortada ao meio, e um caso (Q148) em que o recorte **destruiu a cota "10 cm"**, sem a qual a questão é insolúvel.

**A causa-raiz estrutural comum aos dois:** o sistema não tem um modelo de layout do documento. Ele tem heurísticas que tentam adivinhar geometria a partir de sinais indiretos (contagem de imagens, lacunas de texto, clusters de vetor), e tem um LLM ao qual se pede simultaneamente transcrição, geometria implícita, gabarito e classificação cognitiva — sem nenhuma fonte independente contra a qual conferir qualquer um desses quatro.

---

## 1. Diagnóstico técnico completo

### 1.1 O corpus não é o que o extrator assume que ele é

Inventário direto dos três PDFs (PyMuPDF, contagem por página):

| Caderno | Páginas | Imagens raster embutidas | Sobreviventes aos filtros | Objetos vetoriais |
|---|---|---|---|---|
| 2022 D2 CD5 | 32 | **13** | **4** | **4 735** |
| 2023 D2 CD5 | 32 | 6 | 6 | 5 294 |
| 2024 D2 CD5 | 32 | 145 | 108 | 1 819 |

Nas páginas 17–31 do caderno de 2022 — exatamente o bloco 136–180 auditado — o número de imagens raster candidatas é **zero em todas as páginas**. Praticamente todo gráfico, tabela, diagrama e ilustração desse caderno é desenho vetorial.

`figure_extractor.py` só olha `page.get_images()`. Para este caderno ele é estruturalmente incapaz de produzir qualquer coisa. E a variação entre anos (4 vs. 108 candidatas) mostra que **qualquer heurística calibrada em um caderno não generaliza para o próximo** — não é um detalhe de tuning, é a premissa do módulo que está errada.

### 1.2 `figure_extractor.py` tem rendimento zero no corpus inteiro

Varredura dos 268 itens persistidos, campo `recursos.*[].arquivo`:

```
vazio              222
ALUCINADO           16   ← nome de arquivo inventado pelo modelo
blob válido (sha)    0
```

Nenhum item do banco aponta para um blob real produzido por `figure_extractor.py`. Existem 3 arquivos `.webp` no storage; nenhum é referenciado por nenhum item.

Os 16 "alucinados" são nomes que o Gemini escreveu no campo que o schema reserva para o servidor preencher:

```
ITEM-ENEM-2022-AMARELO-Q178  IMG-01  'screenshot_p31_q178_cubo.png'
ITEM-ENEM-2022-AMARELO-Q178  IMG-02  'screenshot_p31_q178_alternativas.png'
ITEM-ENEM-2023-AMARELO-Q091  IMG-01  'tirinha_monica_91.png'
ITEM-ENEM-2023-AMARELO-Q112  IMG-01  'questao_112_imagem.png'
... (16 no total)
```

Isso tem dois efeitos em cascata, ambos verificados:

1. `extract_book_visuals.py` filtra por `if not im.get("arquivo")` — trata o campo preenchido como "já resolvido" e **pula a questão inteira**. É por isso que Q178 (ENEM 2022, raciocínio espacial, figura + 5 alternativas gráficas) **não aparece sequer como caso no `manifest.json`**: nem extraída, nem marcada como pendente. Desapareceu em silêncio.
2. `exam_images_routes._first_figure_path()` devolve `'screenshot_p31_q178_cubo.png'` ao aluno; o proxy pede esse blob ao pipeline, recebe 404, devolve 502; o `onError` do `<img>` esconde o elemento. O aluno vê uma questão de visão espacial **sem figura e sem gabarito** (Q178 é uma das duas em que nenhuma alternativa tem `correta: true`).

O nota de rodapé do `AUDIT_REPORT.md` anterior — "16 imagens raster já tinham `arquivo` preenchido e já eram exibidas pelo Sapiens" — está incorreta. São exatamente esses 16 nomes alucinados; nenhum nunca foi exibido.

### 1.3 Detecção de duas colunas: o sinal escolhido é o que falta justamente quando é preciso

`_detect_column_split()` deriva a divisória das colunas exclusivamente da posição `x` dos marcadores "QUESTÃO N", e exige ≥2 marcadores com vão ≥60 pt. Diagnóstico rodado sobre o caderno de 2022:

```
pág 17  split=289.0   marcadores em x=31 (136,137,138) e x=289 (139,140)
pág 18  split=289.0
pág 19  split=289.0
...
pág 25  split=None    ← só Q163 na página inteira
pág 28  split=None    ← Q170 e Q171 ambas na coluna esquerda
pág 30  split=None    ← Q175, Q176, Q177 todas na coluna esquerda
pág 31  split=289.0
```

Quando `split=None`, `_ordered_words()` volta a ordenar a página inteira por `y` — e o texto das duas colunas passa a se intercalar linha a linha. Todo o resto (`_question_band`, `_band_geometry`, `_gap_bbox_for_visual`) opera sobre essa ordem corrompida.

Resultado direto e verificável no manifesto:
- pág 25 → Q163 (2 imagens, sequência de dobraduras): `NEEDS_MANUAL_REVIEW`.
- pág 30 → Q177 (tabela de 13 dias): `NEEDS_MANUAL_REVIEW`.
- pág 28 → Q171: `NEEDS_MANUAL_REVIEW` (e há um asset velho e sujo persistido no banco, ver §1.8).

A largura da página é 567 pt em todas as 32 páginas, e a divisória detectada é sempre exatamente **289.0** ≈ `width/2`. Ou seja: **o layout é rigidamente constante e trivialmente modelável**, e a heurística escolhida joga fora essa informação para reconstruí-la a partir de um sinal que some em 3 de 15 páginas.

Observação do seu README sobre a Q153 ("o sistema não identificou que esta questão tinha gráfico... a prova do ENEM é dividida em duas colunas") aponta exatamente para esse ponto. Nesse caso específico a coluna foi detectada e o recorte pegou o gráfico certo — mas pelo motivo errado (contagem que casou por sorte), e com contaminação (§1.5). Em páginas de coluna única o mesmo código atribui à questão a geometria da página inteira, e aí a figura da vizinha é candidata legítima.

### 1.4 Atribuição figura ↔ questão é por contagem, não por geometria

Os dois extratores decidem a quem pertence uma figura **contando**, não localizando:

- `figure_extractor._select_figures_for_question()`: se a página tem ≥2 questões com `tem_figura`, só atribui se `len(candidatas) == len(questões_com_figura)`, e então pareia por ordem vertical. Se as contagens não batem, devolve `[]` (perde tudo). Se **só uma** questão da página tem figura, devolve **todas** as candidatas para ela.
- `extract_book_visuals`: mesma lógica, trocando `manifest.tem_figura` por `recursos.imagens` não-vazio.

O ramo "só uma questão com figura → leva tudo" é o mais perigoso, porque falha silenciosamente e a favor da atribuição errada. Simulação sobre o caderno de 2024:

```
pág 19: 1 questão com tem_figura (Q146) mas 5 rasters candidatos → todas atribuídas a ela
pág 23: 1 questão com tem_figura (Q153) mas 6 rasters candidatos → todas atribuídas a ela
```

Essas 11 imagens pertencem, quase certamente, também à questão vizinha da outra coluna. Nenhuma verificação geométrica impede isso: a coluna nunca entra na decisão.

Seu requisito — *"elementos visuais precisam ser associados à questão correta, não simplesmente à região mais próxima"* — não está apenas mal implementado; a informação necessária (em que coluna/região está o objeto, em que região está a questão) **nunca é calculada** no caminho de atribuição.

### 1.5 O recorte por "lacuna de texto" produz recortes semanticamente destruídos

`_gap_bbox_for_visual()` alinha as palavras da página contra o texto já transcrito (enunciado + alternativas) com `difflib.SequenceMatcher` e assume que a maior lacuna não casada **é** a figura. É engenhoso, mas o bbox resultante é o retângulo das *palavras que sobraram*, e não o da figura. Comparação pixel a pixel dos 14 recortes que inspecionei contra os seus recortes manuais:

| Questão | Defeito observado |
|---|---|
| **Q148** | **Perdeu a cota "10 cm" e as linhas de chamada da altura do cone.** A questão pede o volume; sem a altura ela é insolúvel. Perda de conteúdo, não de estética. |
| Q158 IMG-01 | Legenda "Figura 1" fora do recorte. |
| Q158 IMG-02 | Legenda "Figura 2" cortada ao meio, na horizontal. |
| Q139 | Duas linhas de enunciado vazando (topo e base). |
| Q145 | Duas linhas de enunciado vazando na base + faixa de marca d'água. |
| Q171 | Uma linha vazando no topo, duas na base. |
| Q174 | Linha "mesma altura do seu recorde." vazando no topo. |
| Q179 | Enunciado vazando no topo **e** a própria pergunta ("A medida real da área da varanda...") vazando na base. |
| Q146, Q153, Q173 | Faixa vertical da marca d'água ladrilhada ("ENEM 2022") na borda do recorte. |
| Q141, Q165, Q168 | Aceitáveis. |

Duas causas distintas aqui:

- **Vazamento e truncamento** vêm de `_pad_bbox` (padding fixo de 10 pt) + `_expand_with_drawings` (teto fixo de 460 pt). Padding fixo em pontos não conhece a linha de base tipográfica: 10 pt tanto engolem meia linha de texto quanto deixam de fora um rótulo que está a 11 pt.
- **Marca d'água no pixel.** `_strip_watermark()` remove a marca d'água da *lista de palavras* (para não estragar o casamento), mas `_render_crop()` renderiza a página com `page.get_pixmap(clip=rect)` — a marca d'água continua desenhada. A limpeza acontece na análise e não na renderização.

### 1.6 Múltiplas figuras, figuras compostas e figuras nas alternativas

Três requisitos seus que o schema atual **não tem como representar**:

**(a) Figura composta.** Seu README, Q143: *"como os dois gráficos estavam pertos, preferi recortá-los juntos, também porque as dimensões não ficariam muito distintas"*. O modelo declarou `graficos: [GRA-01, GRA-02]`; `extract_book_visuals` viu 2 elementos, tentou `_try_vector_cluster_crop(n_expected=2)`, não achou exatamente 2 clusters e devolveu `NEEDS_MANUAL_REVIEW` para os dois. Não existe caminho no código que decida "juntar" — o único critério é contagem exata.

**(b) Ordem entre texto e figura.** Seu README, Q158, é explícito: TEXTO → FIGURA 1 → TEXTO → FIGURA 2 → ALTERNATIVAS. O contrato guarda `enunciado` como uma string única e `visual_assets` como uma lista com `position` — e o frontend (`ExamSelect.jsx`) renderiza **todo** o enunciado, depois **todos** os visuais, depois as alternativas. A intercalação é irrepresentável e irrenderizável hoje.

**(c) Alternativas que são imagens.** Você extraiu manualmente 20 imagens de alternativa (Q158 A–E, Q163 A–E, Q165 A–E, Q178 A–E). O schema não tem campo para isso: `alternativas[]` só aceita `{letra, texto, correta}`. O modelo contornou como pôde — em Q178 declarou `IMG-02 = "Cinco opções de projeção ortogonal (A a E)"`, ou seja, empacotou as cinco alternativas numa figura só. Não é erro do modelo; é o contrato que não tem o campo.

### 1.7 Fórmulas e LaTeX

- Onde há `recursos.formulas[].latex` (75 no corpus), o pipeline funciona: todos os 75 passam no parser `matplotlib.mathtext`. Mas o produto final é um **PNG**, servido como bloco `<img>` com borda, entre o enunciado e as alternativas.
- Dimensões reais dos PNGs gerados: de **131×93** (fórmula "1/2", da Q152 — um bloco de imagem inteiro para *meio*) a **1866×112** (uma fórmula longa do caderno de 2024, que num celular de 360 px vira uma tira de 21 px de altura, ilegível).
- **Matemática inline nunca vira LaTeX.** As alternativas da Q150 estão gravadas como ASCII cru: `'9 * (6! / ((6-2)! * 2!))'`. A Q162: `'1/46 + 8/(46 * 45)'`. O enunciado da Q176: `p(t) = −t² + 10t + 24` (Unicode, não LaTeX).
- **Não existe renderizador de LaTeX em nenhum frontend.** `grep -r "katex|mathjax|latex"` em `aluno/frontend` e `pipeline/frontend`: zero ocorrências, zero dependências. Mesmo que o modelo passasse a emitir LaTeX inline hoje, o aluno veria `\frac{1}{2}` literal na tela.

Seus pedidos de LaTeX (Q150, Q162, Q171, Q176, Q177) não são atendíveis por prompt: falta o campo no contrato **e** falta o renderizador no cliente.

### 1.8 Persistência e sincronização de `visual_assets`

O caminho `extract → apply → aluno` tem quatro pontos frágeis, todos verificados:

**(a) Manifesto e banco divergem, e ninguém reconcilia.** Q171 está classificada `NEEDS_MANUAL_REVIEW` no `manifest.json` atual (regravado em 24/08 18:33), mas tem um `visual_assets` persistido nas três coleções, apontando para um blob de uma execução anterior — o recorte sujo mostrado em §1.5. `apply_visual_assets.py` só faz `$set`; **nunca remove** um asset cujo caso foi rebaixado. Um asset errado, uma vez aplicado, é permanente.

**(b) `extract_book_visuals.py` regrava `manifest.json` inteiro.** Rodar `classify` de novo apaga as marcações `manual_humana` que `ingest_manual_crops.py` grava no mesmo arquivo. Os dois scripts compartilham um arquivo mutável como estado, sem versionamento — foi o que aconteceu aqui (não há nenhum `*_manual.png` nem `human_ground_truth.jsonl` em disco, embora o fluxo manual exista).

**(c) `apply_visual_assets.py` não re-espelha para o Firestore.** Ele escreve em `sapiens_pipeline.pipelines`, `sapiens_aluno.questoes_master` e `sapiens_aluno.questoes_public`, mas não chama `update_question_sync`. Enquanto isso, `aluno/backend/server.py::_auto_sync_loop` roda periodicamente `run_firestore_sync`, que faz `questoes_public.delete_many({})` e reconstrói tudo a partir do Firestore. Se esse loop disparar antes de alguém rodar `POST /api/firestore/sync-all` no pipeline, **os `visual_assets` somem da coleção que o aluno consome**. Hoje sobreviveram porque o re-espelhamento foi feito manualmente (há `_synced_at` de 20:36, depois do apply das 18:34) — mas o passo não está documentado no script e não é automático.

**(d) `item_hash` já está divergente.** `apply_visual_assets.py` recalcula `item_hash` porque `compute_item_hash` cobre todo o bloco `questao`, e `visual_assets` mora dentro dele. Efeito observado em `questoes_master` da Q171:

```
master.item_hash        = b90b6e19...   (do espelho Firestore)
master.item.item_hash   = 19032d6f...   (reescrito pelo apply)
```

O contrato diz que `item_hash` "deve mudar quando o conteúdo estrutural relevante da questão mudar". Recortar melhor uma figura não é mudança de conteúdo — mas invalida o hash. Não quebra a devolutiva (`annotation_service` tenta `item_id` antes de `item_hash`), mas torna o hash inútil como chave de "mesmo conteúdo respondido", que é a única função que ele tem.

### 1.9 Validação: o bloco `questao` não é validado por nada

`ontology_validator.py` valida ontologia, processos, habilidades, cadeia de erro, intervenções e a coerência dos distratores. **Não valida nada dentro de `questao`.** Não há verificação de:

- enunciado não vazio (Q180 está com `enunciado: ""` no banco);
- 5 alternativas com texto não vazio (Q137-C, Q140-D, Q161-D estão com `texto: None`; o frontend renderiza um botão vazio);
- exatamente uma alternativa com `correta: true` (Q178 e Q179 não têm nenhuma);
- `recursos.*[].arquivo` ser um blob SHA-256 ou vazio (daí os 16 alucinados);
- coerência entre `recursos` declarados e `visual_assets` entregues;
- coerência entre `correta` e a letra citada em `qualidade.observacoes`.

E a validação é registrada, nunca bloqueante — o que é a decisão certa segundo `EXT-WP1-1.0 L13`, **desde que** o portão `qualidade.apto_para_camada_de_crenca` funcione. Ele não funciona (§2.2).

### 1.10 Frontend do aluno

`ExamSelect.jsx`, bloco de renderização:

- Enunciado (`whitespace-pre-line`), depois **todos** os `visual_assets` ordenados por `position`, depois alternativas. Ordem semântica intercalada é impossível.
- `q.enunciado || "(Sem enunciado)"` — é exatamente o que você viu na Q180.
- `{alt.texto}` sem fallback → alternativa com `texto: null` vira um botão clicável em branco, que o aluno pode selecionar e responder.
- `<img className="mt-4 max-w-full rounded-lg border border-zinc-200">` — sem `width`/`height` intrínsecos (layout shift), sem política de tamanho por tipo, sem zoom/lightbox. Uma tabela recortada a 300 dpi (1522 px de largura) comprimida em ~340 px num celular é ilegível, e não há como ampliar. Uma fórmula de 131 px ganha a mesma moldura que um gráfico.
- O fallback legado (`recursos.imagens[].arquivo` → `/exam-images/{item_id}`) só serve **a primeira** imagem da questão, mesmo quando há duas.

---

## 2. Causas-raiz dos erros no conjunto 136–180

### 2.1 Gabarito errado em 36% do bloco — a falha mais grave

Comparação item a item entre `alternativas[].correta` no banco e o gabarito oficial do seu README:

| Questão | Oficial | Banco | |
|---|---|---|---|
| Q136 | D | E | ✗ |
| Q138 | A | E | ✗ |
| Q139 | A | C | ✗ |
| Q143 | B | A | ✗ |
| Q146 | A | E | ✗ |
| Q153 | D | B | ✗ |
| Q156 | C | E | ✗ |
| Q158 | D | C | ✗ |
| Q159 | C | E | ✗ |
| Q166 | A | E | ✗ |
| Q168 | D | E | ✗ |
| Q174 | D | C | ✗ |
| Q177 | B | E | ✗ |
| Q178 | A | *(nenhuma)* | ✗ |
| Q179 | A | *(nenhuma)* | ✗ |
| Q180 | C | E | ✗ |
| Q175 | Anulada | *(item inexistente)* | — |

**28 corretas, 16 erradas, 1 ausente.** Taxa de erro: **36,4%**.

Em **5 desses 16**, o próprio modelo escreveu a resposta certa em `qualidade.observacoes` e marcou outra em `correta`:

- **Q136** — `observacoes`: *"...A alternativa correta é D (30,0%)."* → `correta: E`. Oficial: **D**.
- **Q146** — *"Cálculos realizados: I=960, II=1080, III=1040, IV=1000, V=1100. O menor é o I. Corrigindo marcação de gabarito na análise interna: Alternativa A é a correta."* → `correta: E`. Oficial: **A**.
- **Q168** — *"...o cálculo direto (1235) coincide com a alternativa D..."* → `correta: E`. Oficial: **D**.
- **Q179** — *"A alternativa correta (A) resulta do cálculo: [(16×5)+(13,4×4)]×(50/100)² = 33,4 m²."* → **nenhuma** alternativa marcada. Oficial: **A**.
- **Q138** — cálculo `182,5/73 = 2,5` descrito corretamente (alternativa A é "2,5") → `correta: E`. Oficial: **A**.

Isto muda o diagnóstico: **não é (só) o modelo errando a questão. É a saída estruturada divergindo do raciocínio do próprio modelo, sem nenhum verificador.** Uma checagem interna trivial (regex por "alternativa correta é X" em `observacoes` vs. a letra marcada) pegaria 5 dos 16 casos hoje, sem gabarito nenhum. Com gabarito oficial, pega os 16.

Distribuição das respostas marcadas nos 268 itens do corpus: A=35, B=44, C=64, D=56, E=63, nenhuma=6. O ENEM distribui as cinco letras aproximadamente uniformemente (≈53,6 cada). O excesso em C/E e a escassez em A são consistentes com viés de saída do modelo, não com o gabarito real.

**Impacto operacional.** `aluno/backend/firestore_routes.py::register_answer` decide `acertou` só a partir de `alternativas[].correta` e grava o evento em `students/{uid}/behavior` com `item_hash` e `ontology_version`. Todo evento já registrado contra essas 16 questões está invertido, e alimenta a camada de crença.

### 2.2 O portão constitucional está aberto porque o modelo o abre

`item_contract.normalize_item()`:

```python
qual.setdefault("revisado", False)
qual["apto_para_camada_de_crenca"] = {"valor": bool(qual.get("revisado"))}
```

O comentário logo acima diz: *"O pipeline nunca marca isto como verdadeiro — só a revisão humana marca."* Mas `setdefault` **preserva o valor que o modelo mandou**. E o modelo manda `true`.

No corpus: **223 dos 268 itens têm `revisado: true`**, e portanto `apto_para_camada_de_crenca.valor: true`. Nenhuma linha de código em `pipeline/` ou `aluno/` jamais define `revisado = True`, e não existe UI de revisão humana em lugar nenhum (`pipeline/frontend/src/pages/ProcessedQuestions.jsx` só exibe `resposta_correta`; `AdminAnnotations.jsx` no aluno é leitura). Todos os 223 vieram do próprio modelo.

Q136 é o exemplo canônico: gabarito errado, `observacoes` contradizendo o gabarito que ela mesma gravou, e `apto_para_camada_de_crenca: true`.

### 2.3 Elementos visuais: 16 de 46 entregues

Contra os seus 46 recortes manuais para 136–180 (26 figuras principais + 20 imagens de alternativa):

**Entregues (16):** Q139, Q141, Q145, Q146, Q148, Q153, Q158 (×2), Q165, Q166, Q168, Q171, Q173, Q174, Q179.
**Perdidos (30):**
- Q143 (2 gráficos) — contagem de clusters não bateu; você os quis fundidos num só.
- Q151 (gráfico), Q164 (gráfico), Q180 (gráfico), Q177 (tabela) — sem lacuna de texto utilizável nem cluster isolado.
- Q162 (2 imagens), Q163 (2 imagens) — página de coluna única, ordem de leitura corrompida.
- Q159 (imagem) — **o modelo nunca declarou** `recursos.imagens`; declarou só 2 fórmulas. O manifesto diz `tem_figura: true` para a Q159, mas `extract_book_visuals` é dirigido por `recursos`, não pelo manifesto. Os dois sinais nunca são reconciliados, e o elemento desaparece sem virar nem sequer um `NEEDS_MANUAL_REVIEW`.
- Q178 (imagem + alternativas) — bloqueada pelo `arquivo` alucinado (§1.2).
- As 20 imagens de alternativa (Q158, Q163, Q165, Q178) — irrepresentáveis no schema.

### 2.4 Alternativas vazias e enunciado ausente

Confirmados no banco, exatamente como no seu README:

- **Q137-C** `texto: None`. Sequência correta: A 0,125 / B 0,200 / **C 4,800** / D 6,000 / E 12,000. O modelo pulou um token e deixou o buraco.
- **Q140-D** `texto: None`. Faltando "R$ 42,00 maior".
- **Q161-D** `texto: None`.
- **Q180** `enunciado: ""`.

Nada detecta isso. Não há validação estrutural do bloco `questao` (§1.9), e o frontend renderiza o vazio.

### 2.5 Placeholders textuais fabricados dentro do enunciado

O modelo, quando não consegue transcrever um elemento, inventa uma descrição entre colchetes e a costura no enunciado:

- **Q153**: `"...[Gráfico de barras comparativo entre Receitas e Despesas por mês]\n\nQual é a mediana..."`
- **Q177**: `"...[Tabela de 13 dias: 1º T1, 2º R, 3º R, 4º T2, 5º R, 6º R, 7º T3, 8º R, 9º T4, 10º R, 11º R, 12º T5, 13º R]..."`

Isso é ruim duas vezes: o aluno lê um marcador de sistema no meio do enunciado, **e** esses tokens fabricados entram em `_reference_tokens()` e envenenam o alinhamento `difflib` que decide onde está a figura. É um caso de retroalimentação: a alucinação textual piora a extração geométrica.

---

## 3. O que o sistema atual consegue e não consegue fazer

### Consegue, de forma confiável
- Enumerar o caderno: o manifesto do Gemini acertou **45/45** questões, páginas e `tem_figura` no bloco 136–180. `fonte.pagina` bate com o manifesto em **268/268** itens do corpus.
- Carimbar procedência: `banca`/`ano`/`prova` vêm do upload e sobrescrevem o modelo. `item_id` determinístico e estável.
- Transcrever enunciado em prosa. Fora Q180, os enunciados estão íntegros e completos (não há truncamento).
- Anotação cognitiva: 268 itens com processos/habilidades/erros derivados e validados contra a ontologia. É o pedaço maduro do sistema.
- Renderizar LaTeX simples offline (75/75 fórmulas passam no `mathtext`).
- Deduplicar por conteúdo (`put_object_deduped`) e detectar o mesmo elemento descrito em duas chaves de `recursos` (IoU > 0,4).
- Preferir `NEEDS_MANUAL_REVIEW` a chutar. **Essa disciplina existe e funciona** — 77 dos 222 casos. O problema é que a fração de "não sei" é alta demais e que o "sei" também erra.

### Não consegue, hoje, por construção
- Extrair qualquer figura de um PDF majoritariamente vetorial pela via `figure_extractor.py` (rendimento 0 em 268 itens).
- Saber em que **coluna** está uma questão ou um objeto. A informação nunca é calculada no caminho de atribuição.
- Produzir um recorte com limites tipográficos corretos: vaza texto ou corta cota.
- Representar figura composta, ordem texto↔figura, ou figura por alternativa.
- Emitir ou renderizar matemática inline em LaTeX.
- Detectar enunciado vazio, alternativa vazia, gabarito ausente ou gabarito duplicado.
- Distinguir gabarito correto de gabarito inventado. **Não existe nenhuma fonte de verdade independente no sistema.**
- Remover um asset errado já aplicado.
- Garantir que `visual_assets` sobreviva ao próximo `run_firestore_sync`.

### Existe mas está desligado
`pipeline/backend/enem_service.py` embrulha o pacote PyPI `enem-extractor` (já instalado no venv), que aceita `test_answer_key_path` e extrai questões, alternativas, imagens **e gabarito** de PDFs do ENEM. **Nenhum módulo importa esse arquivo.** É código morto que já resolve parte do problema do §5.

---

## 4. Proposta de arquitetura para um extrator robusto

O princípio único: **separar geometria de semântica, e nunca pedir as duas ao mesmo agente.** O PDF é a fonte de verdade da geometria; o LLM é a fonte de verdade da leitura; o gabarito oficial é a fonte de verdade da resposta. Hoje o LLM é (mal) as três.

### Estágio 0 — Modelo de documento (determinístico)
Por caderno, uma vez: dimensões de página, detecção da calha entre colunas por **projeção de densidade de glifos no eixo x** (não por marcadores de questão), validando que a calha está vazia em ≥80% da altura. Fallback: `width/2` quando o caderno é declaradamente de duas colunas. Produz `column_model: {n_colunas, divisorias:[x], margens}` por página. Isto sozinho corrige as páginas 25/28/30.

Identifica também, uma vez por caderno, os objetos de *chrome*: cabeçalho, rodapé, código de barras e — crucialmente — os glifos da marca d'água ladrilhada, guardados como lista de bboxes para redação na renderização.

### Estágio 1 — Regiões de questão
Uma questão passa a ser **uma lista ordenada de regiões** `(página, coluna, y0, y1)`, não uma faixa. Regiões são delimitadas por marcadores "QUESTÃO N" dentro da ordem de leitura por coluna, e uma questão pode atravessar coluna→coluna e página→página. Toda operação subsequente é escopada a uma região. **É esta estrutura que torna impossível atribuir a uma questão um objeto da coluna vizinha** — não por heurística, por construção.

### Estágio 2 — Segmentação em blocos tipográficos
Dentro de cada região, todo objeto do PDF (`get_text("rawdict")` + `get_drawings()` + `get_images()`) é classificado em blocos:
`paragrafo | figura | tabela | grafico | formula | legenda | alternativa | citacao_fonte`.

Regras de fronteira **tipográficas**, não de padding fixo:
- Um bloco de figura cresce por proximidade entre objetos não-textuais até encontrar uma linha de base cujo `x0` case com a indentação de corpo da coluna e cuja fonte case com a fonte de corpo. É isso que impede o vazamento da Q179 e o corte da cota da Q148 simultaneamente.
- Legenda ("Figura 1", "Fonte:") é absorvida pelo bloco de figura adjacente por proximidade + fonte menor.
- Tabela = grade vetorial fechada **ou** ≥3 linhas com ≥2 colunas de alinhamento consistente (pega tabela sem borda, hoje impossível).
- O bloco de alternativas começa na primeira linha que casa `^[A-E]\b` na indentação de alternativa da coluna.

### Estágio 3 — Papel e ordem
Cada bloco recebe `ordem` (índice na leitura da região) e `papel`. Uma figura dentro do bloco de alternativas recebe `papel: alternativa_figura` + `letra`. Isso entrega, de uma vez, os requisitos de **ordem preservada** (Q158) e **figura por alternativa** (Q158/163/165/178).

### Estágio 4 — Composição
Regra explícita, calcada no seu critério da Q143: funde blocos de figura irmãos quando (i) o vão entre eles não contém parágrafo de corpo, (ii) estão na mesma coluna, e (iii) a razão de aspecto do retângulo fundido fica em [0,4 ; 2,5]. Caso contrário, mantém separados. Determinístico e auditável.

### Estágio 5 — Renderização
Recorte por bbox de bloco, 300 dpi, com **redação da marca d'água** (`page.add_redact_annot` sobre os bboxes do Estágio 0) antes do `get_pixmap`. Duas saídas por asset: PNG 1× para thumbnail e 2× para zoom. Metadados intrínsecos (`width`, `height`, `aspect`) gravados no asset — o frontend precisa deles.

### Estágio 6 — O LLM lê, não mede
O prompt passa a receber, junto com a página, **a lista de blocos já identificados com seus ids**. O modelo devolve:
- transcrição de cada bloco de texto, com matemática em LaTeX inline (`$...$`);
- `descricao`/`ocr` de cada bloco visual, **referenciando o id do bloco**;
- a anotação cognitiva.

E **não** devolve: `arquivo`, `revisado`, geometria, nem gabarito. Campos que o servidor carimba nunca entram no schema oferecido ao modelo — é a mesma lição já aprendida com `banca`/`ano`/`prova`.

Verificação determinística depois: todo bloco visual precisa estar referenciado por exatamente uma entrada; toda referência precisa apontar para um bloco existente. Bloco órfão ou referência pendurada → `NEEDS_REVIEW` na questão inteira.

### Estágio 7 — Contrato
Substituir `recursos` + `visual_assets` por `questao.blocos[]`, mantendo `recursos` como **projeção derivada somente-leitura** para não quebrar `_build_public_doc` no aluno:

```jsonc
"questao": {
  "blocos": [
    {"id":"BLK-01","tipo":"texto","ordem":0,"texto":"Dentre as diversas planificações...","tem_latex":false},
    {"id":"BLK-02","tipo":"figura","subtipo":"diagrama","ordem":1,"legenda":"Figura 1",
     "ancora":{"pagina":23,"coluna":0,"bbox":[85,388,224,496]},
     "src":"<sha256>.png","render":{"w":1200,"h":930,"dpi":300},
     "descricao":"Planificação em cruz 1-4-1","ocr":"",
     "origem":"layout_deterministico","confianca":"alta"},
    {"id":"BLK-03","tipo":"texto","ordem":2,"texto":"Em um cubo, foram pintados..."},
    {"id":"BLK-04","tipo":"figura","ordem":3,"legenda":"Figura 2", "...": "..."},
    {"id":"BLK-05","tipo":"alternativas","ordem":4,
     "itens":[{"letra":"A","texto":null,"latex":null,
               "figura":{"src":"<sha256>.png","ancora":{"...":"..."}}}]}
  ],
  "revisao":{"status":"ok|needs_review","motivos":["bloco_orfao"]}
}
```

Decisão de contrato que precisa acompanhar: **`item_hash` deixa de cobrir apresentação.** Calcular sobre uma projeção canônica de *conteúdo* (texto do enunciado, letras+textos das alternativas, tipo e ordem dos blocos, hash do conteúdo de cada bloco) e criar um `render_hash` separado para os pixels. Recortar melhor uma figura passa a não invalidar o hash — que é o comportamento que o próprio contrato descreve.

---

## 5. Incorporação do gabarito ao fluxo

### Princípio
O gabarito é uma **entidade de procedência**, irmã de `banca`/`ano`/`prova` — não um campo do conteúdo extraído e **nunca** um arquivo no contexto do modelo. Isso importa concretamente: `POST /book/upload` hoje aceita `files: list[UploadFile]` e `_load_book_files` manda **todos** eles ao Gemini. Anexar o PDF do gabarito ali seria exatamente o erro que você quer evitar — o modelo passaria a "ler" a resposta em vez de resolver a questão, e a divergência (que é o sinal de qualidade mais valioso que temos) desapareceria.

### Schema — nova coleção `answer_keys` (1 doc por caderno)

```jsonc
{
  "answer_key_id": "uuid",
  "book_id": "uuid|null",
  "prova": {"banca":"ENEM","ano":2022,"aplicacao":1,"dia":2,"caderno":"CD5","cor":"AMARELO"},
  "origem": {
    "tipo": "pdf_oficial | csv | json | manual",
    "arquivo_path": "sapiens-cognitive/answer_keys/<id>/2022_GB_impresso_D2_CD5.pdf",
    "sha256": "...",
    "url_oficial": "https://download.inep.gov.br/..."
  },
  "entradas": [
    {"numero":136,"gabarito":"D","status":"valida"},
    {"numero":175,"gabarito":null,"status":"anulada"},
    {"numero":180,"gabarito":"C","status":"valida"}
  ],
  "cobertura": {"faixa":[136,180],"declaradas":45,"lacunas":[]},
  "confianca": "oficial | manual_humano",
  "registrado_por": "email", "registrado_em": "iso8601",
  "imutavel": true
}
```

`imutavel: true` é intencional: corrigir um gabarito cria uma **nova versão**, nunca edita a anterior. Um gabarito que muda em silêncio depois que eventos de behavior foram gravados contra ele é indepurável.

### Onde o gabarito toca o item

**Fora de `questao`**, num irmão — para que anexar o gabarito não mexa no `item_hash`:

```jsonc
"gabarito_oficial": {
  "letra": "D",
  "status": "valida | anulada",
  "answer_key_id": "uuid",
  "aplicado_em": "iso8601"
},
"divergencia_gabarito": {
  "modelo_marcou": "E",
  "oficial": "D",
  "modelo_citou_em_observacoes": "D",
  "detectada_em": "iso8601"
}
```

E `questao.alternativas[].correta` passa a ser **derivada** do gabarito oficial quando ele existe (mesmo padrão de `estrutura_cognitiva.dominios`: derivação, nunca atribuição pelo modelo). O valor que o modelo mandou é preservado em `correta_modelo` para telemetria.

### Fluxo

1. **`POST /book/upload`** ganha um campo opcional **separado** `answer_key_file`, gravado em `book.answer_key_file` — **fora de `book.files`**, portanto invisível para `_load_book_files` e para o Gemini. Uma asserção no teste garante isso para sempre.
2. **`POST /book/{id}/answer-key`** aceita três formas, todas com preview obrigatório antes de confirmar:
   - **PDF oficial do INEP** — parse determinístico. Já temos duas peças: `enem_service.extract_enem_pdf(answer_key_path=...)` (hoje código morto) e o parser `"QUESTÃO GABARITO"` em `aluno/backend/enem_seed.py`. Uma das duas serve; a segunda vira teste de conferência cruzada.
   - **CSV/JSON** — `numero,gabarito,status`.
   - **Entrada manual** — textarea aceitando exatamente o formato do seu README (`136 D`, `175 Anulado`), no anotador do pipeline. É o caminho que funciona para qualquer banca sem parser.
3. **Preview + confirmação**: a tela mostra as 45 entradas parseadas, faixa coberta, lacunas e anuladas, e exige confirmação humana. Só então grava, com `confianca: manual_humano` no caso 3.
4. **`POST /book/{id}/process`**: depois de `normalize_item`, aplica `gabarito_oficial`, deriva `correta`, e:
   - se o modelo divergiu → grava `divergencia_gabarito` e marca `questao.revisao.status = needs_review`;
   - se não há gabarito para o caderno → `apto_para_camada_de_crenca` **fica falso, sem exceção**.
5. **`revisado` sai do schema oferecido ao modelo** e vira `qual["revisado"] = False` incondicional no `normalize_item`, só alterável por uma rota de revisão humana autenticada. Isso fecha o §2.2 numa linha.

### Novas regras de validação (`GAB-*`), registradas e agora bloqueantes para o portão de crença

| Regra | Verificação |
|---|---|
| GAB-01 | O item tem `gabarito_oficial` (senão: `apto_para_camada_de_crenca = false`) |
| GAB-02 | Exatamente uma alternativa com `correta: true`, e ela é a do gabarito |
| GAB-03 | Questão anulada não entra em prova nem em cálculo de acerto |
| GAB-04 | Cobertura do gabarito × questões processadas do caderno (detecta a Q175 faltante) |
| GAB-05 | `divergencia_gabarito` presente ⇒ `status = needs_review` |
| EST-01..05 | Enunciado não vazio; 5 alternativas; nenhum `texto` vazio; letras A–E únicas; sem placeholder `[Gráfico...]` no enunciado |
| ARQ-01 | `arquivo`/`src` casa `^[0-9a-f]{64}\.(png\|webp)$` ou é vazio |

### O bônus: divergência como auditor grátis
A divergência modelo × gabarito é o sinal de qualidade mais barato disponível. Nos 16 erros de 136–180 ela sinaliza **todos**, e cruzada com o estado visual separa os dois modos de falha: Q143/Q159/Q177/Q178/Q180 divergem **e** têm visual perdido (falha de entrada); Q136/Q146/Q168/Q179 divergem com visual entregue e com a letra certa escrita em `observacoes` (falha de serialização). Dois defeitos diferentes, dois consertos diferentes — e a divergência é o que permite distingui-los sem revisão humana.

---

## 6. Estratégia para auditar automaticamente os cadernos já existentes

Um script `pipeline/scripts/audit_corpus.py`, **somente leitura, sem LLM**, que emite um boletim por item. Todas as checagens abaixo são executáveis hoje, sem nenhuma mudança de schema.

**Camada A — gabarito e estrutura** (roda já, precisa só dos 3 PDFs de gabarito do INEP)
- A1 `correta` × gabarito oficial.
- A2 exatamente uma `correta`; A3 enunciado não vazio; A4 nenhuma alternativa vazia; A5 letras A–E únicas.
- A6 **coerência interna**: regex `alternativa (correta|é)\s*\(?([A-E])\)?` em `qualidade.observacoes` e `pedagogia.*` × `correta`. Pega 5/16 dos erros de 136–180 **sem gabarito nenhum**.
- A7 cobertura: números do manifesto × itens persistidos (pega a Q175 ausente).

**Camada B — integridade de assets**
- B1 `arquivo`/`src` com formato de blob válido (pega os 16 alucinados).
- B2 blob referenciado existe no storage; B3 blob em storage sem referência (órfãos).
- B4 `recursos` declarado sem `visual_assets` correspondente, e vice-versa.
- B5 `manifest.tem_figura` × `recursos` não-vazio (pega a Q159, perdida entre os dois sinais).
- B6 **manifesto × banco**: caso classificado `NEEDS_MANUAL_REVIEW` cujo item tem asset persistido (pega a Q171 e todo asset obsoleto).
- B7 placeholder textual `\[(Gráfico|Tabela|Figura|Imagem|Quadro)[^\]]*\]` dentro do enunciado (pega Q153, Q177).

**Camada C — geometria (re-análise do PDF, sem re-extrair)**
Para cada `visual_assets[]` com `ancora`/`bbox`:
- C1 o bbox está inteiramente dentro da região da questão (mesma coluna, entre os marcadores)? Detecta atribuição cruzada de coluna.
- C2 o bbox invade a região de outra questão?
- C3 o bbox entra no bloco de alternativas?
- C4 **vazamento**: contar palavras dentro do bbox que casam com tokens do enunciado/alternativas conhecidos; acima de um limiar, o recorte está contaminado. Pegaria Q139, Q145, Q171, Q174, Q179.
- C5 **truncamento**: existe desenho vetorial ou glifo que cruza a borda do bbox e continua fora? Pegaria a cota "10 cm" da Q148 e a legenda cortada da Q158.
- C6 o bbox contém glifos da marca d'água? Pegaria Q146, Q153, Q173.

**Camada D — governança**
- D1 `revisado: true` sem registro de revisão humana (223 itens hoje).
- D2 `apto_para_camada_de_crenca: true` com qualquer achado de camada A aberto.
- D3 `item_hash` de topo × `item.item_hash` divergentes (pega a deriva da §1.8d).

**Camada E — contaminação já ocorrida**
Para cada questão reprovada em A1, listar os eventos de behavior já gravados no Firestore contra ela, com aluno, data e letra escolhida. Produz a lista exata do que precisa ser recalculado ou anulado. **Não corrige nada** — só levanta.

**Saída:** `audit_corpus.json` + um markdown com semáforo por item:
- 🔴 **BLOQUEADO** — dano ao aluno agora (gabarito errado, enunciado vazio, alternativa vazia, figura de outra questão). Deve sair de circulação até correção.
- 🟡 **DEGRADADO** — jogável mas incompleto (figura faltando, recorte com vazamento, fórmula em ASCII).
- 🟢 **OK**.

Estimativa a partir do que já medi: no bloco 136–180, ≥16 itens 🔴 só por gabarito, +3 por alternativa vazia, +1 por enunciado vazio; ≥10 🟡 por visual perdido e ≥11 🟡 por recorte contaminado.

---

## 7. Plano de implementação priorizado

Ordenado por dano evitado por unidade de mudança estrutural. Cada fase é entregável sozinha.

### Fase 0 — Parar o sangramento *(sem mudança de schema, sem re-extração)*
**Por que primeiro:** hoje, 36% das questões desse bloco dizem a um aluno que ele errou quando acertou, e gravam isso em definitivo.

1. `audit_corpus.py`, camadas A, B, D (§6). Somente leitura.
2. Marcar como fora de circulação, na consulta que monta a prova no aluno, todo item 🔴. Um filtro, não uma migração.
3. Corrigir `item_contract.normalize_item`: `qual["revisado"] = False` incondicional; remover `revisado` do schema entregue ao modelo. **Uma linha, fecha o §2.2.**
4. Validação estrutural `EST-01..05` + `ARQ-01` em `ontology_validator`, registrada (não bloqueante para armazenamento, bloqueante para `apto_para_camada_de_crenca`).
5. Levantamento da camada E: quais eventos de behavior já estão invertidos.

*Custo: baixo. Risco: baixo. Nenhuma re-extração, nenhuma chamada ao Gemini.*

### Fase 1 — Gabarito como fonte de verdade *(§5, estágios 1–5)*
6. Coleção `answer_keys` + `POST /book/{id}/answer-key` com as três entradas (PDF/CSV/manual) e preview obrigatório. Reaproveitar `enem_service.py` (já instalado, hoje morto) e o parser de `enem_seed.py`.
7. `answer_key_file` **fora** de `book.files`, com teste de regressão garantindo que ele nunca chega ao `_load_book_files`.
8. `gabarito_oficial` + `divergencia_gabarito` como irmãos de `questao`; `correta` derivada; `correta_modelo` preservada. **Não mexe em `item_hash`.**
9. Regras `GAB-01..05`; sem gabarito ⇒ `apto_para_camada_de_crenca = false`.
10. Backfill dos 3 cadernos já processados a partir dos gabaritos oficiais do INEP. Isso sozinho corrige os 16 erros de 136–180 sem reprocessar nada no Gemini.

*Custo: médio. Risco: baixo — aditivo, reversível, zero custo de LLM.*

### Fase 2 — Modelo de layout *(§4, estágios 0–1)*
11. `layout_model.py`: colunas por projeção de densidade de glifos, regiões de questão `(página, coluna, y0, y1)`, inventário de chrome e marca d'água.
12. Reescrever `_select_figures_for_question` e a atribuição de `extract_book_visuals` para usarem **contenção geométrica na região**, não contagem. Todo asset passa a carregar `ancora` completa.
13. Camada C do auditor (§6) sobre os assets existentes, usando o novo modelo — o boletim de contaminação dos recortes já aplicados.
14. Remoção segura: `apply_visual_assets` ganha `--reconcile`, que retira do banco assets cujo caso foi rebaixado (fecha a Q171).
15. `apply_visual_assets` passa a chamar `POST /api/firestore/sync-all` ao final (fecha §1.8c).

*Custo: médio-alto — mas é a mudança que torna tudo depois disso generalizável.*

### Fase 3 — Blocos tipográficos e recorte correto *(§4, estágios 2–5)*
16. Segmentação em blocos com fronteiras tipográficas; absorção de legenda; tabela sem borda.
17. Redação da marca d'água antes do `get_pixmap`.
18. Regra de composição da Q143.
19. Re-extração dos três cadernos com validação C4/C5/C6 no laço — nenhum asset entra se estiver contaminado ou truncado.

*Aqui é onde os 11 recortes defeituosos viram limpos e os 10 perdidos são recuperados.*

### Fase 4 — Contrato `blocos[]` e frontend
20. `questao.blocos[]` (§4, estágio 7), com `recursos` como projeção derivada — o aluno continua funcionando sem mudança.
21. `item_hash` sobre projeção de conteúdo; `render_hash` separado.
22. Prompt do Gemini recebe blocos pré-identificados e devolve transcrição referenciando ids; verificação de blocos órfãos/referências penduradas.
23. Aluno: renderizar `blocos[]` em ordem (intercalação texto↔figura), suporte a figura por alternativa, `width`/`height` intrínsecos, política de tamanho por tipo, lightbox no toque.
24. **KaTeX** no aluno + LaTeX inline no contrato (`$...$` em enunciado e alternativas). Sem isso, os pedidos de LaTeX das Q150/Q162/Q171/Q176/Q177 não têm como ser atendidos.

### Mínimo absoluto se for para escolher só um recorte
**Fases 0 e 1.** Elas não tocam em nenhuma estrutura, não custam nada de Gemini, e resolvem o problema que causa dano real ao aluno hoje. As fases 2–4 resolvem o problema que você levantou (visuais), e esse é grave para a experiência — mas é 🟡, não 🔴.

---

## Anexo — como cada número desta auditoria foi obtido

| Afirmação | Método |
|---|---|
| 16/44 gabaritos errados | `sapiens_pipeline.pipelines`, `alternativas[].correta` × README |
| 5/16 com letra certa em `observacoes` | leitura de `item.qualidade.observacoes` dos 16 |
| 223/268 com `revisado: true` | contagem sobre `pipelines` |
| 13 rasters / 4 735 vetores (2022) | `page.get_images()` / `page.get_drawings()` nas 32 páginas |
| 0 blobs válidos, 16 alucinados | regex `^[0-9a-f]{64}\.(webp\|png)$` sobre `recursos.*[].arquivo` |
| split=None nas pág. 25/28/30 | `extract_book_visuals._detect_column_split` executado sobre o PDF |
| 2 páginas de sobre-atribuição (2024) | manifesto × `_extract_page_raster_candidates` por página |
| 16/46 elementos entregues | `visual_assets` no banco × os 46 arquivos do ground truth |
| 11/14 recortes defeituosos | comparação visual lado a lado, assets gerados × recortes manuais |
| 75/75 fórmulas parseáveis | `matplotlib.mathtext.MathTextParser` sobre todo `formulas[].latex` |
| 131×93 a 1866×112 px | `PIL.Image.open().size` sobre os 142 assets gerados |
| `item_hash` divergente | `questoes_master.item_hash` × `questoes_master.item.item_hash` (Q171) |
| 268/268 `fonte.pagina` corretas | `item.fonte.pagina` × `book.manifest[].paginas` |
