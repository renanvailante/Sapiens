---

id: MAP-IDS-1.0 titulo: Mapa de Rastreabilidade de IDs versao: 1.0 estado: ativo camada: C5 criado_em: 2026-08-17T04:11:33Z atualizado_em: 2026-08-17T04:11:33Z supersedes: [] superseded_by: null derivado_de: null governado_por: GOV-1.0 origem_da_demanda: AUD-2026-08-17T03:42:31Z, Fase 1, passo 3 remissoes_pendentes:

- "Ontologia Cognitiva Sapiens v1.3 — ausente do corpus canônico (G-CONF-09)"
- "Especificação Técnica — citada pela Constituição §4.3, inexistente (G-CONF-04)"

---

# Mapa de Rastreabilidade de IDs

## 0. Função, método e regra de decisão

### 0.1 Função

Este documento é o **registro de identidade** do corpus Sapiens. Ele determina, para cada identificador que aparece em qualquer documento canônico, a qual objeto ele se refere, em qual geração, e se existe equivalente em outra geração.

Sem ele, nenhuma correção de artefato é segura: corrigir `ERR-13` exige saber o que `ERR-13` significa em cada documento que o menciona, e a resposta não é a mesma em todos.

### 0.2 Regra de decisão — vinculante

> **Nenhum identificador é considerado equivalente a outro por semelhança nominal, por proximidade de numeração, ou por afinidade conceitual aparente.**

Três verdictos, e apenas três:

|Verdicto|Critério|
|---|---|
|**DOCUMENTADA**|Existe registro textual explícito, em documento do corpus, afirmando a correspondência|
|**EQUIVALÊNCIA NÃO ESTABELECIDA**|Não existe tal registro. Independe de quão óbvia a correspondência pareça|
|**SEM EQUIVALENTE**|Demonstra-se que não há objeto correspondente na geração de destino|

Onde uma hipótese de equivalência é plausível, ela aparece em coluna própria, marcada **não vinculante**. Uma hipótese não vinculante **não autoriza** remapeamento, migração de dado, nem citação cruzada.

### 0.3 Gerações de identificador

|Geração|Fonte|Esquema|Presente no corpus?|
|---|---|---|---|
|**G0**|White Paper 1.0, Cap. 2|Mnemônico por área: `RQ-PROP-003`, `LEIT-INF-002`, `HIST-CAUSAL-002`, `ARGUM-CONSTR-003`|Sim|
|**G1**|White Paper 1.0, Cap. 4|`PROC-<AREA>-NNN` (três dígitos), `COMP-<AREA>-NN`, `DOM-<AREA>`|Sim|
|**G2**|Ontologia v1.3|Plano: `PROC-NN` (01–50), `COMP-NN` (01–26), `HAB-NN` (01–85), `ERR-NN` (01–13), `INT-NN` (01–07), `DOM-<NOME>`|**NÃO — documento ausente**|
|**G3**|Ontologia v1.4|`PROC-<AREA>-NN` (dois dígitos), `COMP-NN` (01–12), `HAB-NN` (01–56), `ERR-NN` (01–13), `INT-NN` (01–11), `DOM-<NOME>`|Sim|
|**GX**|White Paper 2.0|**Mistura G0 e G1**, sem declaração de geração|Sim|
|**GE**|Matriz de Referência ENEM|`H1`–`H30` por área, mais "Competência de área N"|Apoio externo|

### 0.4 Achado estrutural que condiciona todo o resto

**A geração G2 está ausente do corpus canônico.**

Os 25 processos da Ontologia v1.4 portam `origem_v1_3` apontando para identificadores G2. A Constituição cita G2 em pelo menos seis passagens. O mapa de mudanças da Ontologia v1.4 §9 descreve fusões e remoções inteiramente em termos G2.

Como a v1.3 não está em `pipeline/docs/` em nenhum estado — nem sequer `superseded` —, **toda referência de proveniência da v1.4 é uma remissão pendente** sob GOV-1.0 §1.4, e a cadeia de proveniência está rompida sob GOV-1.0 §9.4.

Consequência prática, registrada aqui de forma vinculante: **nenhuma equivalência entre G0/G1 e G3 pode ser estabelecida por via documental**, porque o único caminho documental entre elas passa por G2. Toda equivalência G1↔G3 neste documento é, necessariamente, `EQUIVALÊNCIA NÃO ESTABELECIDA`.

Isto não é pessimismo de método. É a consequência lógica de um elo faltante, e é precisamente o que o mapa existe para tornar visível em vez de contornar.

---

## 1. Domínios Cognitivos

### 1.1 G1 (WP 1.0, Cap. 4) → G3 (Ontologia v1.4)

|ID|Nome em G1|Nome em G3|Extensão coincide?|Verdicto|
|---|---|---|---|---|
|`DOM-QUANT`|Raciocínio sobre Quantidade e Número|Quantificação e Raciocínio Numérico|**Não.** Em G1, escala e semelhança geométrica ficam em `DOM-ESPACO`; em G3, unidades e consistência dimensional entram em `DOM-QUANT`|**NÃO ESTABELECIDA**|
|`DOM-ESPACO`|Raciocínio Espacial e sobre Forma|Representação e Raciocínio Espacial|**Não.** G3 absorve estrutura→função, ausente da definição G1|**NÃO ESTABELECIDA**|
|`DOM-MUDANCA`|Raciocínio sobre Mudança, Relações e Modelagem Funcional|Mudança e Covariação|**Não.** G1 inclui modelagem/tradução verbal→matemática; G3 move isso para `DOM-SIMBOLICO`|**NÃO ESTABELECIDA**|
|`DOM-INCERTEZA`|Raciocínio sobre Incerteza, Dados e Probabilidade|Incerteza e Raciocínio sobre Dados|**Não.** G1 inclui combinatória como competência própria; G3 a funde em processo probabilístico|**NÃO ESTABELECIDA**|
|`DOM-CAUSAL`|Raciocínio Causal-Mecanístico|Raciocínio Causal|**Não.** G1 inclui equilíbrio e perturbação (`COMP-CAUSAL-02`); G3 move para `DOM-SISTEMICO`|**NÃO ESTABELECIDA**|
|`DOM-SISTEMICO`|Raciocínio Sistêmico|Raciocínio Sistêmico|**Não.** G1 inclui conservação de massa/energia; G3 move para `DOM-MUDANCA`|**NÃO ESTABELECIDA**|
|`DOM-EXPERIMENTAL`|Raciocínio Experimental e Investigativo|Raciocínio Experimental e Metodológico|**Parcialmente.** G1 inclui leitura crítica de dados com incerteza; G3 exclui explicitamente ("não inclui interpretação de dado já coletado sem componente de desenho metodológico")|**NÃO ESTABELECIDA**|
|`DOM-ESTRUTURA`|Raciocínio sobre Padrão, Escala e Estrutura-Função|—|—|**SEM EQUIVALENTE em G3**|

**Este é o padrão de colisão mais perigoso do corpus: sete identificadores idênticos com extensão comprovadamente divergente.** Nenhum sistema, humano ou automático, detectaria a diferença por inspeção do identificador. O nome coincide, a definição de uma linha coincide aproximadamente, e o conjunto de processos que cada um contém é diferente.

### 1.2 Domínios de G3 sem correspondente em G1

|ID (G3)|Nome|Observação|
|---|---|---|
|`DOM-LOGICO`|Raciocínio Lógico-Argumentativo|**SEM EQUIVALENTE em G1.** Criado pela divisão de `DOM-CAUSAL` registrada nas decisões de fronteira da v1.4 — divisão referida a G2, não a G1|
|`DOM-SIMBOLICO`|Representação e Notação Formal|**SEM EQUIVALENTE em G1.** Declarado pela v1.4 como resultado da divisão de "DOM-ESTRUTURA" — mas de um `DOM-ESTRUTURA` **G2**, cuja extensão é desconhecida e cujo nome coincide com o de G1 (ver §1.3)|
|`DOM-TEXTUAL`|Compreensão e Integração Textual|Idem|
|`DOM-CLASSIF`|Classificação e Sistematização|Ver §1.4 — caso de reutilização de identificador condenado|

### 1.3 `DOM-ESTRUTURA`: colisão entre G1 e G2 com consequência não resolvível

A Ontologia v1.4, em suas decisões de fronteira, declara: _"DOM-ESTRUTURA dividido em DOM-SIMBOLICO (tradução/decodificação de notação formal) + DOM-TEXTUAL (compreensão de texto e representação visual-estruturada)."_

O `DOM-ESTRUTURA` de G1 é _"Raciocínio sobre Padrão, Escala e Estrutura-Função"_, ancorado nos crosscutting concepts do NRC (2012). **Uma divisão dele em "notação formal" e "compreensão textual" não é interpretável** — os conteúdos não se correspondem.

Duas leituras possíveis, e o corpus não permite escolher entre elas:

- **(a)** o `DOM-ESTRUTURA` de G2 já era um objeto diferente do de G1, e a divisão faz sentido em relação a G2;
- **(b)** houve deriva não registrada entre G1 e G2.

Sem a v1.3, a questão é indecidível. **Verdicto: EQUIVALÊNCIA NÃO ESTABELECIDA, com impossibilidade de estabelecimento declarada.**

Consequência material: o conteúdo real do `DOM-ESTRUTURA` de G1 — padrão recorrente e estrutura-função — **não foi para `DOM-SIMBOLICO` nem para `DOM-TEXTUAL`**. Estrutura-função aparece em `PROC-ESPACO-03` (G3); padrão recorrente **desapareceu** (ver §3.4).

### 1.4 `DOM-CLASSIF`: identificador condenado e reutilizado

A Constituição §3.1 cita nominalmente `DOM-CLASSIF` como caso de falha: _"dois domínios (DOM-MATERIA, DOM-CLASSIF) descreviam o que se pensa (matéria, energia, categorias taxonômicas), não como se pensa."_

A Ontologia v1.4 removeu `DOM-MATERIA` e **manteve `DOM-CLASSIF`**, redefinindo-o como _"Operações de agrupar entidades em categorias por critério de propriedade compartilhada"_ — que é, de fato, uma operação, e responde à crítica em substância.

Mas o identificador foi reutilizado após ter tido outro significado, o que contraria GOV-1.0 §5.3 (_"um identificador nunca muda de significado; se o significado muda, é aposentado e um novo é criado; identificadores aposentados não são reutilizados"_).

**Registrado como incidente `MAP-INC-01`.** O corpus contém hoje uma crítica nominal a `DOM-CLASSIF` (Constituição, vigente) e um `DOM-CLASSIF` que não incorre nela (Ontologia v1.4, vigente). Um leitor que cruze os dois documentos conclui, erroneamente, que a Ontologia v1.4 mantém um domínio que a Constituição reprova.

---

## 2. Competências

### 2.1 G1 → G3

|G1 (16 IDs)|G3 (12 IDs)|Verdicto|
|---|---|---|
|`COMP-QUANT-01`, `COMP-QUANT-02`, `COMP-ESPACO-01`, `COMP-ESPACO-02`, `COMP-MUD-01`, `COMP-MUD-02`, `COMP-INC-01`, `COMP-INC-02`, `COMP-CAUSAL-01`, `COMP-CAUSAL-02`, `COMP-SIST-01`, `COMP-SIST-02`, `COMP-EXP-01`, `COMP-EXP-02`, `COMP-ESTR-01`, `COMP-ESTR-02`|`COMP-01` … `COMP-12`|**EQUIVALÊNCIA NÃO ESTABELECIDA para todos os 16**|

Esquemas incompatíveis (mnemônico por área vs. numeração plana), sem qualquer mapa de correspondência em documento algum. Não há sequer coincidência de cardinalidade.

Circunstância atenuante quanto ao risco: os formatos são **visivelmente distintos**, o que torna uma confusão acidental improvável. Este é o único bloco de identificadores do corpus em que a divergência de esquema é, na prática, uma proteção.

### 2.2 Colisão G2 ↔ G3 — direta e perigosa

A v1.3 tinha **26** competências; a v1.4 tem **12**. Ambas usam o formato `COMP-NN`.

Prova de que G2 usava esse formato: `ontology_v1.4.json` registra, em `PROC-ESPACO-03`, `origem_v1_3: ["COMP-19", "COMP-21", ...]`, e em `PROC-CLASSIF-01`, `origem_v1_3: [..., "COMP-20"]`. A Constituição §1.1 e §2.4 citam `COMP-19`, `COMP-20` e `COMP-21` como objetos da v1.3.

Portanto:

> **`COMP-01` … `COMP-12` existem em G2 e em G3, com significados que não se pode presumir iguais.**

**Verdicto: EQUIVALÊNCIA NÃO ESTABELECIDA para `COMP-01` a `COMP-12` entre G2 e G3.** Qualquer anotação, planilha ou referência produzida sob a v1.3 e que cite `COMP-07` é hoje **ambígua e não resolvível**.

`COMP-19`, `COMP-20` e `COMP-21` (G2) têm destino documentado: a Ontologia v1.4 §9 e o JSON registram que foram absorvidas em `PROC-ESPACO-03` (as duas primeiras) e `PROC-CLASSIF-01` (a terceira). **Verdicto: DOCUMENTADA — referente irresolúvel** (o mapeamento está registrado; o objeto de origem não é inspecionável).

---

## 3. Processos Cognitivos

### 3.1 Inventário G0 e G1

**G0 — WP 1.0, Cap. 2** (exemplares completos, com ficha):

|ID|Nome|Nível declarado|
|---|---|---|
|`RQ-PROP-003`|Inferência Proporcional Direta|Processo Cognitivo|
|`LEIT-INF-002`|Inferência de Ideia Implícita a partir de Coesão Textual|Processo Cognitivo|
|`HIST-CAUSAL-002`|Diferenciação entre Causa Estrutural e Causa Conjuntural|Processo Cognitivo|
|`ARGUM-CONSTR-003`|Construção de Argumento com Articulação Causal Não Simplista|**Competência**|

**G1 — WP 1.0, Cap. 4** (29 blocos declarados; ver §3.5 quanto à contagem):

`PROC-QUANT-001`, `PROC-QUANT-002`, `RQ-PROP-003` (declarado com ID G0 dentro de G1), `PROC-QUANT-004`, `PROC-QUANT-005`, `PROC-ESPACO-001`…`004`, `PROC-MUD-001`…`004`, `PROC-INC-001`…`004`, `PROC-CAUSAL-001`…`003`, `PROC-SIST-001`…`003`, `PROC-EXP-001`…`004`, `PROC-ESTR-001`, `PROC-ESTR-002`.

### 3.2 G1 → G3: tabela de verdictos

Todas as linhas são `EQUIVALÊNCIA NÃO ESTABELECIDA` pela razão estrutural do §0.4. A coluna de hipótese é **não vinculante** e existe para orientar a arbitragem futura do Curador.

|ID G1|Nome G1|Hipótese em G3 _(não vinculante)_|Nota de risco|
|---|---|---|---|
|`PROC-QUANT-001`|Estimativa de Magnitude Aproximada|`PROC-QUANT-03` (Estimar ordem de grandeza)|**Truncamento perigoso**: `001`→`01` levaria a `PROC-QUANT-01` (Comparar e ordenar grandezas), que é objeto diferente|
|`PROC-QUANT-002`|Comparação entre Representações Numéricas|`PROC-QUANT-01`|Truncamento levaria a `PROC-QUANT-02` (proporcional) — objeto diferente|
|`RQ-PROP-003`|Inferência Proporcional Direta|`PROC-QUANT-02`|Sem risco de truncamento (esquema G0)|
|`PROC-QUANT-004`|Estrutura Multiplicativa vs. Aditiva|—|Nenhum processo G3 nomeia esta distinção. Possível **SEM EQUIVALENTE**|
|`PROC-QUANT-005`|Relação Não Proporcional|—|Idem. Coberto apenas indiretamente por `ERR-05`|
|`PROC-ESPACO-001`|Rotação e Reflexão Mental|—|Nenhum processo G3 cobre rotação mental. Possível **SEM EQUIVALENTE**|
|`PROC-ESPACO-002`|Decomposição de Figuras Compostas|`PROC-ESPACO-02`|Truncamento **coincide** com a hipótese — coincidência, não evidência|
|`PROC-ESPACO-003`|Inferência por Semelhança/Escala|—|**Colisão de truncamento mais grave do corpus**: `003`→`03` leva a `PROC-ESPACO-03` (Relacionar estrutura a função), conceitualmente não relacionado|
|`PROC-ESPACO-004`|Estimativa de Medidas via Decomposição|`PROC-ESPACO-02`|Dois IDs G1 mapeariam ao mesmo G3|
|`PROC-MUD-001`|Tradução Verbal → Representação Matemática|`PROC-SIMB-01`|**Muda de domínio** entre gerações|
|`PROC-MUD-002`|Interpretação de Taxa de Variação|`PROC-MUD-01`|—|
|`PROC-MUD-003`|Reconhecimento de Padrão de Covariação|`PROC-MUD-01`|Dois IDs G1 mapeariam ao mesmo G3|
|`PROC-MUD-004`|Extrapolação/Interpolação|—|Possível **SEM EQUIVALENTE**|
|`PROC-INC-001`|Arranjo/Combinação/Permutação|`PROC-INC-04`|O WP2 §13.4 marca este nó como conflação reconhecida|
|`PROC-INC-002`|Probabilidade Condicional|`PROC-INC-01`|—|
|`PROC-INC-003`|Tendência Central e Dispersão|`PROC-INC-02` **e** `PROC-INC-03`|Um ID G1 mapearia a **dois** G3|
|`PROC-INC-004`|Julgamento sob Incerteza e Heurísticas|—|**Colisão de truncamento**: `004`→`04` leva a `PROC-INC-04` (combinatório-probabilístico), objeto diferente. Possível **SEM EQUIVALENTE**|
|`PROC-CAUSAL-001`|Variável Causal vs. Correlacional|`PROC-CAUSAL-01`|—|
|`PROC-CAUSAL-002`|Encadeamento de Etapas Causais|`PROC-CAUSAL-01`|Dois IDs G1 ao mesmo G3|
|`PROC-CAUSAL-003`|Resposta de Sistema a Perturbação|`PROC-SIST-01`|**Muda de domínio**|
|`PROC-SIST-001`|Retroalimentação Positiva/Negativa|—|Possível **SEM EQUIVALENTE**|
|`PROC-SIST-002`|Efeito em Cascata|`PROC-SIST-02`|Truncamento coincide com a hipótese|
|`PROC-SIST-003`|Conservação de Massa/Energia|`PROC-MUD-02`|**Muda de domínio**|
|`PROC-EXP-001`|Variável Independente/Dependente/Controle|`PROC-EXP-02`|**Colisão de truncamento**: `001`→`01` leva a `PROC-EXP-01` (Formular hipótese testável), objeto diferente|
|`PROC-EXP-002`|Validade de Conclusão Experimental|—|Possível **SEM EQUIVALENTE**|
|`PROC-EXP-003`|Leitura Crítica de Dados com Incerteza|`PROC-INC-03`|**Muda de domínio**|
|`PROC-EXP-004`|Suficiência de Evidência|—|Possível **SEM EQUIVALENTE**|
|`PROC-ESTR-001`|Padrão Estrutural Recorrente|—|**SEM EQUIVALENTE — confirmado.** Ver §3.4|
|`PROC-ESTR-002`|Função a partir de Estrutura|`PROC-ESPACO-03`|**Muda de domínio**|

### 3.3 G2 → G3: as únicas equivalências documentadas do corpus

A Ontologia v1.4 §9 e o campo `origem_v1_3` do JSON registram explicitamente o mapeamento G2→G3 para os 25 processos. Este é o único bloco com verdicto `DOCUMENTADA` — com a ressalva permanente de que o referente G2 não é inspecionável.

Fusões registradas: `PROC-26+34+49 → PROC-MUD-02`; `PROC-39+41+46+COMP-19+COMP-21 → PROC-ESPACO-03`; `PROC-47+48+COMP-20 → PROC-CLASSIF-01`; `PROC-22+30+43 → PROC-CAUSAL-01`; `PROC-44+45 → PROC-SIST-02`; `PROC-03+04 → PROC-SIMB-01`; `PROC-25+40 → PROC-SIMB-02`; `PROC-05+06 → PROC-QUANT-02`; `PROC-20 → PROC-INC-02`.

Remoções registradas: `PROC-08, 17, 24, 28, 31, 32, 33, 35, 36, 37`.

**Verdicto para todo o bloco: DOCUMENTADA — referente irresolúvel.**

**Lacuna registrada:** o mapa da v1.4 §9 é declarado "lista completa, não exaustiva de habilidades em cascata" e cobre ~10 remoções e ~9 fusões. A v1.3 tinha 50 processos e a v1.4 tem 25. **A soma dos mapeamentos registrados não fecha os 50.** Registrado como incidente `MAP-INC-02`: existem processos G2 cujo destino não está registrado em documento algum.

### 3.4 `PROC-ESTR-001` — ativo declarado preservado, ausente do catálogo

O White Paper 2.0 §14.3 declara, entre as duas arestas cross-domínio preservadas da derivação original: _"(ii) reconhecimento de padrão como mecanismo de transferência, ligando PROC-MUD-003 a PROC-ESTR-001 — padrão matemático (linear, exponencial, quadrático) e padrão científico (estrutura recorrente entre fenômenos)."_

Verificação exaustiva sobre os 25 processos da Ontologia v1.4: **não existe processo cujo objeto seja o reconhecimento de padrão estrutural recorrente entre fenômenos de superfície distinta.** O candidato mais próximo, `PROC-ESPACO-03`, é estrutura→função, que em G1 é `PROC-ESTR-002` — o outro nó.

**Verdicto: SEM EQUIVALENTE em G3, com contradição ativa em documento vigente.** Registrado como incidente `MAP-INC-03`.

Observação de relevância, registrada sem decidir: `PROC-ESTR-001` é o nó cuja função declarada é a **transferência estrutural** — precisamente o mecanismo que a Constituição §2.3 usa para definir a admissibilidade de um Processo Cognitivo. Sua ausência tem consequência potencial sobre a expansão para novas áreas, onde reconhecimento de padrão análogo é operação central. A decisão pertence à etapa de construção da próxima versão da ontologia, não a este documento.

### 3.5 Referência pendente interna ao WP 1.0

Sob GOV-1.0 §1.4, registrada como pendência do documento fonte:

- **`PROC-QUANT-003`** é declarado membro de `COMP-QUANT-02` (_"processos: [PROC-QUANT-003, PROC-QUANT-004, PROC-QUANT-005]"_), mas o bloco correspondente é declarado com `id: RQ-PROP-003`. E `PROC-QUANT-004` declara `pre_requisitos: [RQ-PROP-003]`, e `PROC-QUANT-005` idem. **`PROC-QUANT-003` é referenciado uma vez e nunca definido.**
- O inventário do WP1 §4.5 registra o problema implicitamente — lista _"PROC-QUANT-001/002/004/005, RQ-PROP-003"_ — sem corrigir a referência da competência.
- O mesmo inventário declara **28** processos e enumera **29**. Incidente aritmético `MAP-INC-04`.

---

## 4. Habilidades Observáveis

|Geração|Esquema|Cardinalidade|
|---|---|---|
|G0/G1|**Nenhum ID.** Habilidades aparecem como texto de exemplo em tabelas|—|
|G2|`HAB-NN`|85|
|G3|`HAB-NN`|56|

**Colisão G2 ↔ G3: `HAB-01` a `HAB-56` existem em ambas as gerações.** A v1.4 §9 declara a redução de 85 para 56 _"por remoção em cascata e fusão de pares redundantes"_ — sem mapa item a item. Não há como determinar se `HAB-14` da v1.4 é a `HAB-14` da v1.3.

**Verdicto: EQUIVALÊNCIA NÃO ESTABELECIDA para todas as 56.** Registrado como incidente `MAP-INC-05`.

**Colisão com a Matriz do ENEM (GE):** o INEP usa `H1`–`H30` por área. O prefixo difere (`H` vs. `HAB`), mas a proximidade é suficiente para erro humano em planilha ou anotação. Recomendação registrada: qualquer referência a habilidade do ENEM usa prefixo qualificado por área — `ENEM-LC-H23`, `ENEM-CH-H14` — nunca `H23`.

---

## 5. Tipos de Erro

Este é o bloco de maior risco operacional imediato do corpus.

### 5.1 As duas taxonomias, lado a lado por número

|Nº|**G0/G1 — WP 1.0 §2.5.2**|**G3 — Ontologia v1.4 §6**|
|---|---|---|
|1|Erro conceitual (misconception sistemática)|`ERR-01` Leitura literal deficiente|
|2|Erro procedimental (buggy algorithm)|`ERR-02` Inferência indevida|
|3|Erro atencional (slip)|`ERR-03` Erro de modelagem/tradução|
|4|Erro de interpretação (do enunciado)|`ERR-04` Inconsistência dimensional/de escala|
|5|Erro de leitura (decodificação linguística)|`ERR-05` Confusão de direção em relação proporcional|
|6|Erro de cálculo|`ERR-06` Leitura equivocada de representação gráfica/tabular|
|7|Erro de estratégia|`ERR-07` Confusão causa/correlação|
|8|Erro metacognitivo|`ERR-08` Generalização indevida|
|9|Erro de memória|`ERR-09` Ignorar variável de controle|
|10|Erro por sobrecarga cognitiva|`ERR-10` Erro de decodificação de notação simbólica|
|11|Erro por transferência inadequada|`ERR-11` Erro de estimativa/ordem de grandeza|
|12|Erro por viés cognitivo|`ERR-12` Falha de validade lógica/falácia|
|13|Erro por automatização incorreta|`ERR-13` Classificação por critério superficial|

**Verdicto: EQUIVALÊNCIA NÃO ESTABELECIDA para todos os treze pares. Os conjuntos são disjuntos.** Não se trata de duas versões da mesma taxonomia: são dois eixos ortogonais — mecanismo psicológico versus operação cognitiva falha — com a mesma cardinalidade e o mesmo intervalo de numeração.

**Prova documental da colisão em uso real:** o exemplo de JSON do WP 1.0 §3.4 registra `{"alternativa": "A", "erro_esperado": {"error_type_id": 7, "nome": "erro de estratégia"}}`. Sob a Ontologia v1.4, `ERR-07` é "confusão causa/correlação". Um pipeline que lesse aquele JSON contra o catálogo atual atribuiria um erro conceitualmente não relacionado, **sem levantar exceção**.

### 5.2 Armadilhas nominais confirmadas

Casos em que a semelhança de nome sugere equivalência e a definição a refuta:

|Par|Por que não é equivalente|
|---|---|
|WP1 #5 "erro de leitura" × `ERR-01` "leitura literal deficiente"|WP1 #5 é falha de **decodificação linguística** (Perfetti & Stafura), explicitamente distinta de erro de interpretação. `ERR-01` é falha em **localizar dado explícito** no enunciado. Camadas diferentes|
|WP1 #4 "erro de interpretação" × `ERR-02` "inferência indevida"|WP1 #4 é má compreensão do **comando da questão**, anterior a qualquer processamento de conteúdo. `ERR-02` é **extrapolar além do texto**. Direções opostas|
|WP1 #12 "erro por viés cognitivo" × `ERR-08` "generalização indevida"|WP1 #12 é desvio heurístico de julgamento (Kahneman & Tversky). `ERR-08` é estender conclusão de amostra não representativa. Sobreposição parcial, definições distintas|
|WP1 #1 "erro conceitual" × `ERR-13` "classificação por critério superficial"|WP1 #1 é aplicação coerente de concepção prévia equivocada (diSessa). `ERR-13` é agrupar por aparência. Um é causa possível do outro, não o mesmo objeto|

### 5.3 Colisão G2 ↔ G3 — mesma família, significados trocados

A Ontologia v1.4 §9 documenta que a v1.3 tinha 13 tipos de erro e registra duas mudanças nominais:

- **`ERR-13` em G2** = "distrator plausível" — removido por ser propriedade do item, não do aluno (Constituição §3.5).
- **`ERR-13` em G3** = "Classificação por critério superficial" — tipo **novo**.
- **`ERR-05` em G2** = erro algébrico — removido junto com o processo-base.
- **`ERR-05` em G3** = "Confusão de direção em relação proporcional".

> **`ERR-05` e `ERR-13` significam coisas diferentes em versões adjacentes da mesma ontologia, sob o mesmo esquema de identificador.**

Isto é a violação exata de GOV-1.0 §5.3 (identificador aposentado não é reutilizado). Registrado como incidente `MAP-INC-06`, e é o caso que melhor justifica a existência daquela regra.

Para os demais onze identificadores `ERR-NN`, a Ontologia v1.4 §9 declara a contagem estável (13→13) mas não fornece mapa item a item. **Verdicto: EQUIVALÊNCIA NÃO ESTABELECIDA para `ERR-01`…`ERR-04` e `ERR-06`…`ERR-12` entre G2 e G3.**

Registro adicional: a mesma linha da tabela v1.4 §9 é aritmeticamente inconsistente — "13 → 13" com descrição "1 removido, 1 realocado, 1 novo" resulta em 12. Já registrado pela auditoria como C9.

### 5.4 O vínculo `ERR-13` divergente entre artefatos do mesmo CNI

Situação atual, verificada campo a campo:

|Artefato|O que declara|
|---|---|
|Ontologia v1.4, §3 (`PROC-ESPACO-03`)|_"Erro: ERR-14 (nota: renumerado ERR-13 na tabela final)"_|
|Ontologia v1.4, §6 (nota após a tabela)|O erro dedicado a `PROC-ESPACO-03` **não foi incluído** nesta versão|
|Ontologia v1.4, §10.3|`PROC-ESPACO-03` está entre os processos **sem** Tipo de Erro dedicado|
|Manual, nota de correção|Declara ter **corrigido no JSON** o vínculo indevido, antes da redação do Manual|
|`ontology_v1.4.json`|`PROC-ESPACO-03` → `tipos_erro: ["ERR-13"]` — **vínculo presente**|
|`04 Ontologia … JSON.md`|Idêntico ao anterior — **vínculo presente**|
|`ERR-13` (ambos os JSONs)|`processos_cognitivos: ["PROC-CLASSIF-01"]` — **não menciona `PROC-ESPACO-03`**|

O vínculo é, portanto, **unidirecional e assimétrico**: existe do processo para o erro, não do erro para o processo.

Verificação aritmética independente: processos com `tipos_erro: []` no JSON = **12**. Manual §11 e Ontologia §10.3 declaram **13**. A diferença é exatamente `PROC-ESPACO-03`.

**Conclusão registrada: os dois artefatos JSON do corpus são as versões NÃO corrigidas.** A correção que o Manual declara ter aplicado não está presente em nenhum artefato do corpus.

Também registrado: `ERR-14` é citado uma vez na Ontologia v1.4 §3 e **não existe em nenhum catálogo**. É referência pendente.

---

## 6. Intervenções Pedagógicas

|Geração|Esquema|Cardinalidade|
|---|---|---|
|G0/G1|Entidade `PedagogicalIntervention` sem catálogo de IDs|—|
|G2|`INT-NN`|7|
|G3|`INT-NN`|11|

A v1.4 §9 declara _"4 novas, para fechar lacunas de cobertura erro→intervenção"_, sem dizer quais das onze são as quatro novas nem se as sete antigas mantiveram identificador.

**Verdicto: EQUIVALÊNCIA NÃO ESTABELECIDA para `INT-01`…`INT-07` entre G2 e G3.** Incidente `MAP-INC-07`.

---

## 7. Identificadores citados pelo White Paper 2.0 (GX)

O White Paper 2.0 é documento de camada C1, o de maior autoridade do corpus. Todos os identificadores que ele cita pertencem a G0 ou G1, **sem declaração de geração**, e nenhum é resolvível contra a Ontologia v1.4.

|ID citado|Onde|Geração|Resolve em G3?|
|---|---|---|---|
|`DOM-QUANT`, `DOM-ESPACO`, `DOM-MUDANCA`, `DOM-INCERTEZA`|§13.2|G1|ID existe; extensão divergente (§1.1)|
|`DOM-CAUSAL`, `DOM-SISTEMICO`, `DOM-EXPERIMENTAL`, `DOM-ESTRUTURA`|§14.1|G1|Idem; `DOM-ESTRUTURA` **não existe**|
|`RQ-PROP-003`|§13.3|G0|**Não**|
|`PROC-MUD-003`, `PROC-MUD-004`, `PROC-INC-004`|§13.3|G1|**Não**|
|`PROC-EXP-001`, `PROC-CAUSAL-002`, `PROC-SIST-003`|§14.2|G1|**Não**|
|`PROC-ESTR-001`|§14.3|G1|**Não — sem equivalente** (§3.4)|

**Consequência registrada:** o documento de maior autoridade do corpus é hoje inteiramente não resolvível contra o catálogo vigente. Cada uma dessas citações é uma remissão pendente sob GOV-1.0 §1.4.

O próprio WP 2.0 §14.4 declara que a derivação original produziu _"8 domínios, 16 competências e 28 processos"_ — exatamente o inventário do WP 1.0 §4.5, sem citar a fonte, e reproduzindo a contagem de 28 que o §3.5 deste mapa demonstra ser 29.

---

## 8. Identificadores citados pela Constituição

A Constituição é camada C2 e cita exclusivamente G2 — a geração ausente.

|ID citado|Onde|Papel na argumentação|
|---|---|---|
|`COMP-19`, `COMP-21`, `PROC-41`, `PROC-46`|§1.1|Exemplo do padrão estrutura→função fragmentado em quatro lugares|
|`PROC-29` a `PROC-50`|§1.1|Faixa em que o campo `categoria` muda de natureza|
|`PROC-17`|§2.2|Exemplo de nó tecnicamente correto que não pertence à ontologia|
|`PROC-47`, `PROC-48`, `COMP-20`|§2.4|Três nomeações da mesma operação|
|`DOM-MATERIA`, `DOM-CLASSIF`|§3.1|Domínios que descreviam "o que se pensa"|
|`DOM-SISTEMICO`|§3.1|Domínio sem operação unificadora|

**Todas são remissões pendentes.** A argumentação da Constituição permanece válida em substância — os exemplos ilustram princípios, e os princípios não dependem da inspeção dos exemplos — mas **nenhum leitor pode verificá-los**, e dois dos identificadores (`DOM-CLASSIF`, `DOM-SISTEMICO`) existem também em G3 com outro significado, o que produz leitura ativamente enganosa (§1.4).

---

## 9. Referências pendentes — inventário consolidado

|#|Referência|Origem|Alvo|Existe?|
|---|---|---|---|---|
|**D1**|`PROC-QUANT-003`|WP1 §4.2, `COMP-QUANT-02.processos`|—|**Não.** Nó declarado como `RQ-PROP-003`|
|**D2**|`ARITM-FRAC-001`, `ARITM-RAZAO-002`, `ALG-FUNC-LIN-004`, `QUIM-ESTEQ-002`, `LEITURA-GRAF-001`, `RQ-NAOPROP-004`, `FIS-MRU-001`, `QUIM-CONC-001`|WP1 §2.7.1|—|**Não.** Nenhum definido|
|**D3**|`LEIT-DECOD-001`, `LEXICO-001`, `METACOG-MONIT-001`, `LEIT-LOC-001`, `MAT-PROB-VERBAL-001`|WP1 §2.7.2|—|**Não**|
|**D4**|`RACIOCINIO-CAUSAL-GERAL-001`, `HIST-PERIODIZACAO-001`, `HIST-CRONOLOGIA-001`, `REDACAO-PROPOSTA-INTERV-001`|WP1 §2.7.3|—|**Não**|
|**D5**|`REDACAO-COESAO-001`, `REDACAO-REPERTORIO-SOCIOCULT-001`, `REDACAO-ENUMERACAO-001`|WP1 §2.7.4|—|**Não**|
|**D6**|`LEITURA-GRAF-001` como pré-requisito|WP1 §4.2, `PROC-MUD-002`|—|**Não.** O próprio texto o marca como _"nó a ser formalizado"_|
|**D7**|`origem_v1_3` de todos os 25 processos|`ontology_v1.4.json`|Ontologia v1.3|**Não.** Documento ausente do corpus|
|**D8**|`ERR-14`|Ontologia v1.4 §3|Catálogo de erros|**Não**|
|**D9**|Capítulos 5, 7, 11, 12|Constituição §§2.3, 3.4, 3.7.2, 4.3|Constituição|**Não**|
|**D10**|"Especificação Técnica"|Constituição §4.3, §3.4|`pipeline/docs/`|**Não**|
|**D11**|`sapiens_ontologia_v1.4.json`|Ontologia v1.4, encerramento|Arquivo|**Não.** O arquivo é `ontology_v1.4.json`|
|**D12**|8 identificadores G0/G1|WP 2.0 §§13.3, 14.2, 14.3|Ontologia v1.4|**Não** (§7)|

---

## 10. Colisões de namespace — inventário consolidado

|#|Colisão|Gerações|Severidade|Por quê|
|---|---|---|---|---|
|**NS-1**|Tipos de erro: inteiros `1`–`13` × `ERR-01`–`ERR-13`|G0/G1 × G3|**BLOQUEANTE**|Conjuntos disjuntos, mesma cardinalidade, mesmo intervalo. Falha silenciosa comprovada (§5.1)|
|**NS-2**|`ERR-05`, `ERR-13`|G2 × G3|**BLOQUEANTE**|Mesmo identificador, mesmo esquema, significados diferentes em versões adjacentes|
|**NS-3**|`PROC-<AREA>-NNN` × `PROC-<AREA>-NN`|G1 × G3|**BLOQUEANTE**|Truncar o zero à esquerda produz identificador válido e errado. Casos confirmados: `PROC-ESPACO-003`→`PROC-ESPACO-03`; `PROC-EXP-001`→`PROC-EXP-01`; `PROC-INC-004`→`PROC-INC-04`; `PROC-QUANT-001`→`PROC-QUANT-01`|
|**NS-4**|`DOM-<NOME>`|G1 × G3|**BLOQUEANTE**|Sete identificadores idênticos com extensão divergente (§1.1). Nenhum sinal sintático de diferença|
|**NS-5**|`COMP-01`–`COMP-12`|G2 × G3|**ESTRUTURAL**|Mesmo esquema, conjuntos renumerados (26→12)|
|**NS-6**|`HAB-01`–`HAB-56`|G2 × G3|**ESTRUTURAL**|Mesmo esquema, conjuntos renumerados (85→56), sem mapa|
|**NS-7**|`INT-01`–`INT-07`|G2 × G3|**ESTRUTURAL**|Mesmo esquema, 7→11, sem mapa|
|**NS-8**|`H1`–`H30` (ENEM) × `HAB-NN`|GE × G3|**MENOR**|Prefixos distintos, proximidade suficiente para erro humano|
|**NS-9**|`DOM-CLASSIF`, `DOM-SISTEMICO`|G2 × G3|**ESTRUTURAL**|A Constituição critica nominalmente objetos G2 cujos identificadores foram reutilizados em G3 com outro significado (§1.4, §8)|

---

## 11. Incidentes registrados

|ID|Incidente|Severidade|Encaminhamento|
|---|---|---|---|
|`MAP-INC-01`|`DOM-CLASSIF` reutilizado após condenação nominal na Constituição|ESTRUTURAL|Nota de esclarecimento na Constituição (etapa 12)|
|`MAP-INC-02`|O mapa de mudanças v1.3→v1.4 não fecha os 50 processos de origem|ESTRUTURAL|Depende de recuperar a v1.3|
|`MAP-INC-03`|`PROC-ESTR-001` declarado preservado pelo WP2, ausente da v1.4|**BLOQUEANTE** para a próxima versão|Errata ao WP2 (etapa 11); decisão de conteúdo na versão seguinte da ontologia|
|`MAP-INC-04`|WP1 §4.5 declara 28 processos e enumera 29|MENOR|Registro apenas — documento a ser superseded|
|`MAP-INC-05`|56 habilidades sem mapa de origem item a item|ESTRUTURAL|Depende de recuperar a v1.3|
|`MAP-INC-06`|`ERR-05` e `ERR-13` com significados trocados entre versões adjacentes|**BLOQUEANTE**|Nota de aposentadoria de identificador, a registrar no patch v1.4.1|
|`MAP-INC-07`|11 intervenções sem mapa de origem|ESTRUTURAL|Depende de recuperar a v1.3|

---

## 12. Regras de uso deste mapa — vinculantes

1. **Nenhum remapeamento automático.** Nenhuma ferramenta, script ou prompt pode converter identificadores entre gerações com base nas hipóteses não vinculantes deste documento.
2. **Truncamento é proibido.** Converter `PROC-XXX-001` em `PROC-XXX-01` por normalização de formato é a falha mais provável e a mais silenciosa. Está registrada como NS-3 e é vedada.
3. **Toda citação de identificador declara a geração.** A partir deste documento, qualquer referência a um identificador em documento canônico ou registro de auditoria indica de qual geração se trata.
4. **Identificadores aposentados não retornam.** Sob GOV-1.0 §5.3, e à luz de NS-2, nenhuma versão futura reutiliza um identificador que já teve outro significado — inclusive os que este mapa registra como reutilizados.
5. **Recuperação de conteúdo do WP 1.0 não transporta identificadores.** Conforme o Registro de Extração, o conteúdo recuperável de G0/G1 volta sob identificadores novos, nunca sob os originais.

---

## 13. Efeito sobre a árvore de dependências

Este mapa **desbloqueia** a etapa 4 (correção do `ontology_v1.4.json`), ao estabelecer que:

- o `ERR-13` a ser removido de `PROC-ESPACO-03` é o `ERR-13` de **G3** ("Classificação por critério superficial"), não o de G2 ("distrator plausível") nem o item 13 de G0/G1 ("automatização incorreta");
- a correção é **Classe I — Correção de Fidelidade** sob GOV-1.0 §3.3, porque alinha o artefato a uma decisão já registrada em três lugares da própria Ontologia v1.4 e no Manual;
- o passo 5 do procedimento de GOV-1.0 §4.3 exige, na mesma transação, reconciliar a contagem 12/13 que o Manual e a Ontologia §10.3 afirmam;
- a mesma transação deve registrar a aposentadoria de `ERR-05` e `ERR-13` como identificadores reutilizados (`MAP-INC-06`).

Este mapa **não desbloqueia** nenhuma decisão de conteúdo. Toda equivalência G1↔G3 permanece não estabelecida, e assim permanecerá enquanto a v1.3 estiver ausente.

---

## 14. Changelog

|TX|Timestamp|Classe|Alteração|Autoriza|Co-alterados|
|---|---|---|---|---|---|
|`TX-2026-08-17T041133Z-map-ids`|2026-08-17T04:11:33Z|— (criação)|Criação do mapa em estado `ativo`|AUD-2026-08-17T03:42:31Z, Fase 1, passo 3|nenhum|

---

_Fim do documento. Nenhum JSON foi alterado. Nenhuma equivalência foi estabelecida por semelhança nominal._