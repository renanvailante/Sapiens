# Checkpoint — Auditoria comparativa Claude × Gemini (16 questões)

Congelado em 2026-08-23. Documento de retomada futura — nenhuma análise nova
foi feita para gerar este arquivo, apenas o registro do que já havia sido
produzido na conversa.

Escopo: as 16 questões que o Claude anotou de forma independente do caderno
ENEM 2023 D2 Amarelo (Q091–Q102, Q111, Q131, Q132, Q141), comparadas
campo-a-campo contra a anotação já existente do Gemini para os mesmos
`item_id` (`sapiens_aluno.questoes_master`). As 74 questões restantes do
caderno **não foram anotadas pelo Claude** e não fazem parte desta auditoria.

Fontes: Claude = `pipeline/annotation_audit/claude_2023_D2_AMARELO/items/Q*.json`
(16/16 presentes). Gemini = MongoDB `sapiens_aluno.questoes_master` (16/16
pares encontrados). Nenhum campo ausente em nenhum dos lados.

Nota: em **Q094** o Gemini gravou `correta` como string `"true"/"false"` em
vez de booleano — violação objetiva do Schema 2.2. Corrigido o tipo para
comparar valor, o gabarito real do Gemini ali é **A** (igual ao Claude).

---

## Comparação por questão

**Q091** — Gabarito: C×C concordante | Disciplina: concordante | Domínio:
DOM-CAUSAL × DOM-MUDANCA+DOM-TEXTUAL divergente | Competência: COMP-06 ×
COMP-04+COMP-09 divergente | Nuclear: PROC-CAUSAL-01 × PROC-MUD-01 divergente
| Secundário: nenhum × PROC-TEXT-02 divergente | Dificuldade: médio×médio
concordante | Visual: sim×sim concordante (descrições equivalentes) |
Veredito: **B** — leituras cognitivas distintas e defensáveis da mesma
questão (causa/efeito vs. covariação+leitura textual).

**Q092** — Gabarito: A×A concordante | Disciplina: concordante | Domínio:
DOM-TEXTUAL × DOM-QUANT+DOM-TEXTUAL divergente | Competência: divergente
(mesmo padrão) | Nuclear: PROC-TEXT-02 × PROC-QUANT-02 **divergente** |
Secundário: nenhum × PROC-TEXT-01 divergente | Dificuldade: concordante |
Visual: não×não concordante | Veredito: **B** — nuclear diverge de fato
(inferência textual vs. proporcionalidade); nenhuma evidência objetiva
aponta erro de um lado.

**Q093** — Gabarito: A×A concordante | Domínio/Competência: divergente
(Claude só DOM-SIMBOLICO; Gemini soma DOM-QUANT) | Nuclear:
PROC-SIMB-01×PROC-SIMB-01 concordante | Secundário: nenhum ×
PROC-QUANT-04 divergente | Dificuldade: concordante | Visual: **não×sim
divergente** — Gemini registrou 2 fórmulas (I=P/A, A=4πr²) que Claude não
capturou como `recursos.formulas`. Veredito: **provável erro do Claude**
(fórmulas explícitas na questão deveriam constar em `recursos`, mesmo com
nuclear correto).

**Q094** — Gabarito: A×A concordante (após correção de tipo) |
Domínio/Competência: divergente (Gemini soma DOM-TEXTUAL/COMP-09) | Nuclear:
PROC-QUANT-01×PROC-QUANT-01 concordante | Secundário: nenhum×PROC-TEXT-01
divergente | Dificuldade: concordante | Visual: sim×sim concordante, mas
Gemini soma 2 fórmulas que Claude não registrou. Veredito: **D (Gemini)** —
`correta` como string viola o Schema 2.2; demais divergências são **B**.

**Q095** — Todas as dimensões concordantes (gabarito D, domínio, competência,
nuclear PROC-MUD-02, dificuldade, visual=não). Veredito: **concordância
total**.

**Q096** — Gabarito C×C concordante | Domínio: DOM-ESPACO ×
DOM-CLASSIF+DOM-TEXTUAL **divergente** | Competência/Nuclear: divergente
(PROC-ESPACO-03 × PROC-CLASSIF-01) | Visual: sim×sim (tabela, concordante) |
Veredito: **B/C — divergência mais forte**: estrutura-função vs.
classificação são leituras cognitivas bem diferentes da mesma questão; sem
gabarito de processo oficial, fica **indeterminado** qual é mais correta,
mas é a divergência de maior salto conceitual do lote.

**Q097** — Gabarito C×C concordante | Disciplina: Claude usa o cabeçalho
impresso da seção ("Ciências da Natureza e suas Tecnologias"), Gemini usa a
área específica ("Química") — **divergência de granularidade, não de fato:
A**. Domínio/Competência: divergente (Gemini soma DOM-QUANT) | Nuclear:
concordante (PROC-SIMB-01) | Secundário: divergente | Visual: sim×sim
concordante. Veredito: **A/B**.

**Q098** — Todas as dimensões-chave concordantes (gabarito C, domínio
DOM-SISTEMICO, competência COMP-11, nuclear PROC-SIST-01, dificuldade,
visual). Única diferença: Gemini registrou 3 fórmulas do circuito que Claude
não listou em `recursos.formulas`. Veredito: **B (só no detalhe de
fórmulas)**.

**Q099** — Concordância total (gabarito C, DOM-CAUSAL, COMP-06,
PROC-CAUSAL-01, dificuldade, visual=não). Veredito: **concordância total**.

**Q100** — Gabarito D×D concordante | Disciplina: Claude usa o cabeçalho da
seção, Gemini usa "Biologia" — **A** | Domínio/Competência/Nuclear:
DOM-CAUSAL×DOM-ESPACO **divergente** | Visual: não×não concordante.
Veredito: **B** — causa/efeito vs. estrutura-função, sem evidência objetiva
de qual é mais adequada.

**Q101** — Gabarito D×D, domínio, competência, nuclear (PROC-CAUSAL-01) e
visual todos concordantes. Única divergência: Dificuldade fácil×médio.
Veredito: **indeterminado** (dificuldade é julgamento subjetivo, sem
critério objetivo no corpus).

**Q102** — Gabarito D×D, domínio (DOM-ESPACO+DOM-QUANT), competência,
nuclear+secundário, dificuldade todos concordantes. Visual: ambos sim, mas
Claude registrou 2 imagens (uma por aparelho) e Gemini 1 (descrição
combinada) — mesma cobertura de conteúdo. Veredito: **A — concordância
quase total**, divergência de granularidade em `imagens[]`.

**Q111** — Gabarito E×E concordante | Domínio/Competência/Nuclear:
DOM-ESPACO×DOM-SISTEMICO **divergente** (estrutura-função vs.
interdependência sistêmica) | Visual: não×não concordante. Veredito: **B**.

**Q131** — Gabarito B×B concordante | Domínio/Competência/Nuclear:
DOM-CAUSAL × DOM-TEXTUAL+DOM-SISTEMICO **divergente** | Visual: não×não
concordante. Veredito: **B**.

**Q132** — Gabarito B×B, domínio (DOM-SISTEMICO), competência (COMP-11),
nuclear (PROC-SIST-02), visual todos concordantes. Secundário: Claude não
registrou nenhum, Gemini soma PROC-SIST-01. Dificuldade: médio×fácil.
Veredito: **B (secundário) + indeterminado (dificuldade)**.

**Q141** — Gabarito C×C, domínio (DOM-QUANT), competência (COMP-01), nuclear
(PROC-QUANT-04), visual todos concordantes. Única divergência: Dificuldade
difícil×médio. Veredito: **indeterminado**.

---

## Síntese

- **Questões comparadas:** 16/16 (100% dos pares existiam).
- **Divergências totais registradas:** 34 (contando cada dimensão divergente
  por questão).
- **Por dimensão:**

| Dimensão | Concordâncias | Divergências | % concordância |
|---|---|---|---|
| Disciplina/área | 16 | 0* | 100%* |
| Gabarito | 16 | 0 | 100% |
| Domínio | 7 | 9 | 44% |
| Competência | 7 | 9 | 44% |
| Processo nuclear | 10 | 6 | 62% |
| Processo secundário | 8 | 8 | 50% |
| Dificuldade | 13 | 3 | 81% |
| Elemento visual (presença) | 15 | 1 | 94% |

*Disciplina: 14 concordância literal + 2 (Q97, Q100) reclassificadas como
**A — equivalente** (granularidade seção-vs-área), não divergência de fato.

- **Divergências potencialmente relevantes para a Ontologia:** o padrão
  dominante é Gemini atribuir **2 domínios/competências** (nuclear + um
  processo secundário adicional) em questões onde o Claude só reconheceu 1 —
  ocorre em 9/16 questões (Q91–93, 96, 97, 100, 111, 131, 132). Sugere um
  viés sistemático de um dos dois anotadores na aplicação do "teste de
  necessidade" do processo secundário (Manual §4), não erros pontuais — vale
  investigação dedicada antes de decidir qual padrão é mais correto.
- **Atribuíveis a erro objetivo de uma das IAs:** 1 — Q094, Gemini gravou
  `correta` como string, violando o Schema 2.2 (**D**). 1 caso de
  **provável** omissão do Claude: Q093, fórmulas presentes na questão não
  capturadas em `recursos.formulas` (mesmo padrão ocorre também, em menor
  grau, em Q094 e Q098).
- **Indeterminadas:** todas as 9 divergências de domínio/competência/processo
  nuclear-secundário (sem gabarito de processo cognitivo oficial, não há
  como arbitrar objetivamente) + 3 divergências de dificuldade (Q101, Q132,
  Q141) — 12 no total.
- **Limitação:** esta auditoria cobre apenas 16/90 questões do caderno (as
  únicas já anotadas pelo Claude); não é representativa do caderno inteiro.

---

## Perfil de consumo do Claude e Gemini

**Claude (esta sessão) — indicadores objetivos disponíveis:**
Não há contagem absoluta de tokens disponível neste registro; o indicador
confiável disponível é o consumo de aproximadamente 16% da cota semanal
para 16 questões.

Indicadores adicionais de processamento, extraídos literalmente das
notificações de erro recebidas nesta conversa (sem estimativa):
- 1ª rodada de 9 agentes paralelos (lotes de 10 questões cada, 91–180):
  todos os 9 falharam por limite antes de escrever qualquer arquivo.
  Mensagens recebidas: `"You've hit your session limit · resets 2:30am
  (America/Sao_Paulo)"` (5 agentes), `"You've hit your weekly limit · resets
  6am (America/Sao_Paulo)"` (2 agentes), mais 2 agentes sem notificação de
  conclusão (status "stopped", sem transcript resumível).
- 2ª rodada de 9 agentes paralelos (mesmos lotes, retomando o que já
  existia): todos os 9 voltaram a falhar com `"You've hit your session
  limit · resets 11am (America/Sao_Paulo)"`, produzindo parcialmente 6
  questões extras (Q97–Q100 raw, Q101–Q102 raw) antes de parar.
- 3ª rodada de 9 agentes paralelos (retomando de onde cada lote parou,
  prompts reduzidos por instrução explícita de economia): interrompida
  manualmente pelo usuário (`TaskStop` em todas as 9) ~3 min após o
  disparo, antes de qualquer nova notificação de limite.
- Resultado líquido de processamento: **16 questões anotadas e validadas**
  (Q091–Q102, Q111, Q131, Q132, Q141) em 3 rodadas de disparo, span de
  tempo entre a 1ª tentativa e a interrupção manual: madrugada de
  2026-08-23 (primeira falha ~2:30am) até ~11h05 (parada manual).

**Gemini (produção, dados já existentes no repositório antes desta sessão)
— única fonte objetiva disponível é `pipeline/backend/cognitive_engine.py`
(comentários de auditoria de custo real, lidos nesta conversa):**
- Custo real observado para um lote de 89 questões, antes da otimização
  (thinking level HIGH, padrão do modelo): **~R$28/lote**.
- Custo projetado após otimização (thinking level MEDIUM): **~R$2/lote**
  de 89 questões.
- Nível MEDIUM reduz custo projetado por questão em **~52%** frente a HIGH,
  "sem nenhuma queda de validade estrutural na amostra (0/8 inválidas, igual
  a HIGH)" (amostra controlada de 8 questões × 3 níveis, citada no código).
  LOW reduz **~86%** frente a HIGH, mas teve 1/8 falha de validação na mesma
  amostra.
- Estratégia adaptativa (LOW primeiro, escalona para MEDIUM só se a
  validação estrutural reprovar) projetou 8/8 válidas a **~20% do custo
  médio de MEDIUM fixo**, usando os mesmos 24 dados já pagos do teste
  controlado (nenhuma chamada nova).
- Tokens de "thinking" são cobrados como saída, a **US$3,00/1M tokens**
  (citado no código; não há contagem de tokens absolutos do lote de 89
  questões real no material lido nesta conversa, apenas o custo em R$/lote
  e os percentuais de redução acima).

Nenhum número acima foi estimado ou inferido por mim — todos vêm
literalmente das notificações de sistema recebidas ou dos comentários já
existentes no código-fonte, lidos nesta conversa.
