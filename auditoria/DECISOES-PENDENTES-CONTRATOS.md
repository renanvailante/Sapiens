# Decisões pendentes de contrato — Schema 2.1, escalas, LOTUS e pipeline

**Registrado em:** 2026-08-17T23:38:43Z
**Base exclusiva:** os 14 documentos hoje em `pipeline/docs/` (13 já auditados + o próprio Schema 2.1) + auditorias anteriores em `auditoria/`.
**Escopo:** aprofunda `auditoria/ESPECIFICACAO-MIGRACAO-SCHEMA-2.1-E-PIPELINE.md` (2026-08-17T03:48:27Z) nos cinco pontos pedidos. Nenhum código, dado ou documento canônico foi alterado. Nenhum contrato intermediário foi criado. Nenhuma escala, enum, ID ou comportamento foi inventado.

**Correção sobre a auditoria anterior:** a leitura completa do Manual de Anotação (feita nesta rodada, não na anterior) mostra que a §8(b) de `ESPECIFICACAO-MIGRACAO-SCHEMA-2.1-E-PIPELINE.md` estava **parcialmente errada** ao classificar `processos[].peso_no_item` como "escala não definida". Existe, sim, uma convenção definida para peso de **processo** (Manual §5). O mapeamento abaixo substitui aquela seção com precisão campo a campo. Nota de correção também deixada no arquivo original.

---

## 1. Mapeamento exaustivo de escalas/valores permitidos

Convenção de status:
- ✅ **DEFINIDO** — escala/enum existe em `pipeline/docs/`, com citação exata.
- 🟡 **PARCIAL** — algo relacionado existe, mas não cobre o campo por completo, ou há conflito entre documentos.
- 🔴 **AUSENTE** — nenhum documento define. Quando um documento *nomeia explicitamente* quem deveria definir (a "Especificação Técnica"), isso é indicado — esse documento **não existe** no repositório.

### `estrutura_cognitiva`

| Campo | Status | Onde está (ou deveria estar) definido |
|---|---|---|
| `dominios[].peso_no_item` | 🔴 AUSENTE | Nenhuma menção em nenhum dos 13 documentos. A Constituição (§4.5) só fala de peso para relações "diagnósticas/evidenciais" (Processo↔Habilidade, Processo↔Processo, Resposta→Erro); relações de "classificação/organização" como Processo↔Domínio são explicitamente ditas como tendo "peso opcional... nunca obrigatório" — o que sugere que peso de domínio pode nem ser um conceito pretendido, mas isso não está confirmado, só sugerido. |
| `dominios[].confianca` | 🔴 AUSENTE | Idem — nenhuma menção. |
| `competencias[].peso_no_item` | 🔴 AUSENTE | Nenhuma menção. Agravante: a Constituição (§3, linha ~63) declara que "Competência é tratada como agrupamento derivado, não como entidade ontológica fundamental... não é, portanto, rastreada pelo motor de crença como unidade independente de estado". Isso está em tensão conceitual com o Schema 2.1 pedir peso/confiança de competência como se fosse uma unidade rastreada independentemente — **não é uma contradição resolvida por mim**, é uma tensão entre dois documentos que precisa ser decidida por quem mantém `pipeline/docs/`. |
| `competencias[].confianca` | 🔴 AUSENTE | Mesma tensão acima. |
| `processos[].peso_no_item` | ✅ DEFINIDO (parcialmente — convenção provisória) | **Manual de Anotação §5**: bins categóricos — processo único = 1.0 (implícito); dois processos candidatos = Central **0.7** / Secundário Necessário **0.3**; soma sempre 1.0; **máximo 2 processos com peso** por item (3+ candidatos → registrar como ambiguidade, não distribuir peso). O próprio Manual diz que isso é "convenção provisória de bins categóricos, não um modelo matemático final" — a fórmula definitiva é, por texto explícito da Constituição (§4.5) e do Manual (§5), matéria de um documento chamado **"Especificação Técnica"**, citado 5x na Constituição e 2x na Ontologia v1.4, que **não existe em `pipeline/docs/`**. |
| `processos[].papel` | 🟡 PARCIAL — **conflito de nomenclatura entre documentos canônicos** | O Schema 2.1 dá como exemplo ilustrativo (não enumeração fechada) "por exemplo 'nuclear' ou 'secundario'". O Manual de Anotação §5 e a Constituição §4.5 usam, para o mesmo conceito, os termos **"Central"** e **"Secundário Necessário"** — strings diferentes. Além disso, o Manual exclui explicitamente uma terceira categoria: um processo que "apenas facilita" **não deve ser registrado** (§5, última linha da tabela) — o que entra em tensão com o Formato A antigo (`nuclear\|secundario\|facilitador`, com 3 valores) e não confirma se "facilitador" seria um valor válido de `papel` no Schema 2.1. **Decisão pendente**: qual literal exato deve ir no campo `papel` — o exemplo do Schema 2.1 ou a terminologia do Manual/Constituição? Os dois documentos não usam o mesmo vocabulário para o mesmo conceito. |
| `processos[].confianca` | 🔴 AUSENTE (numericamente) | Nenhuma escala numérica definida. Existe, sim, um vocabulário **qualitativo** de incerteza no Manual §12.2: `candidato-secundário: incerto`, `aproximado`, `erro não catalogado nesta versão`, `ambiguidade — ver Seção 11` — mas isso é uma notação textual de exceção, não um score de confiança contínuo ou categórico equivalente ao que `confianca` no Schema 2.1 parece pedir. Não presumi que um é o outro. |
| `processos[].dificuldade_local` | 🔴 AUSENTE | Nenhuma menção em nenhum documento. |
| `processos[].habilidades[].peso_no_processo` | 🔴 AUSENTE (numericamente) | O Manual §6 dá critérios de **seleção** de habilidade (lista fechada de 56, teste de formato de estímulo, marcação "aproximado" quando não há encaixe exato) — mas não define peso numérico. |
| `processos[].habilidades[].confianca` | 🔴 AUSENTE | Nenhuma menção. |
| `processos[].evidencias.trechos/figuras` | ✅ Sem gap de escala | São campos estruturais (citações/IDs), não numéricos — sem escala a definir. |
| `processos[].justificativa` | ✅ Sem gap — e bem coberto operacionalmente | O Manual (§12.4) já exige "justificativa breve (1-2 frases)... escrita de forma que um segundo anotador, sem acesso ao raciocínio do primeiro, consiga entender a decisão" — isso é uma regra de qualidade textual, diretamente aplicável ao campo `justificativa` do Schema 2.1, sem gap. |

**Restrição estrutural adicional confirmada (Manual §4)**: no máximo 2 processos podem ter peso atribuído por item; um terceiro candidato genuíno deve virar registro de ambiguidade, não uma terceira entrada em `processos[]` com peso. Isso é uma regra de validação de tamanho de array que pode ser aplicada sem inventar nada.

### `distratores[]`

| Campo | Status | Onde está (ou deveria estar) definido |
|---|---|---|
| `alternativa` | ✅ Sem gap | Identificação simples. |
| `erro` | 🟡 PARCIAL — regra operacional existe, mas com valores especiais não-ID | O Manual §7 define que `erro` deve ser um ID do catálogo **vinculado ao processo dominante do item** — mas também define dois valores textuais válidos que **não são IDs da ontologia**: `"erro não catalogado nesta versão"` (usar quando o processo dominante é um dos 13 de 25 sem Tipo de Erro catalogado — lista exata dada no Manual §11) e `"sem mecanismo cognitivo identificável"` (quando a alternativa errada não reflete um mecanismo cognitivo real). Qualquer validação de `erro` contra a ontologia precisa aceitar essas duas strings como válidas, não só IDs `ERR-*`. |
| `plausibilidade` | 🔴 AUSENTE | Nenhuma enumeração em nenhum documento. |
| `probabilidade_estimada` | 🔴 AUSENTE | A Constituição (§4.4, relação Resposta→Tipo de Erro) diz explicitamente que essa relação "é produzida em tempo de execução pelo motor diagnóstico; sua especificação de schema pertence à Especificação Técnica, não a este documento" — de novo, deferido nominalmente a um documento inexistente. |
| `processos_afetados` | ✅ Sem gap | IDs de processo, lista aberta. |
| `explicacao` | ✅ Sem gap | Texto livre. |

### `intervencoes[]`

| Campo | Status | Onde está (ou deveria estar) definido |
|---|---|---|
| `id`, `gatilho.processo`, `gatilho.erro` | ✅ Sem gap | IDs do catálogo. |
| `acao` | ✅ Sem gap | Texto livre, com restrição qualitativa já dada pela Constituição (§3.6: intervenção "não é um plano de aula... não é definida por disciplina"). |
| `prioridade` | 🔴 AUSENTE | Nenhuma escala/ranking definido em nenhum documento. |

### `pedagogia`

| Campo | Status |
|---|---|
| `estrategia`, `passos`, `erros_comuns`, `dicas` | ✅ Sem gap — texto livre |
| `tempo_estimado_segundos` | 🟡 PARCIAL — o Schema 2.1 já exige "acompanhado pela metodologia ou fonte da estimativa quando disponível", o que é suficiente como regra de processo (não precisa de escala numérica nova), mas nenhum documento define QUAL metodologia usar |
| `nivel_dificuldade` | 🔴 AUSENTE | Nenhuma enumeração ("fácil/médio/difícil"? escala 1–5?) em nenhum documento. |

### `qualidade`

| Campo | Status |
|---|---|
| `confianca_global` | 🔴 AUSENTE | Sem escala numérica definida em lugar nenhum. |
| `revisado`, `revisor`, `observacoes` | ✅ Sem gap de escala (gap diferente: são preenchíveis só após revisão humana real — ver `AUDITORIA-MIGRACAO-ITEM-2.1.md` / `ESPECIFICACAO-MIGRACAO-SCHEMA-2.1-E-PIPELINE.md §8c`) |

### `pipeline{}` (metadados de execução)

| Campo | Status |
|---|---|
| `modelo`, `versao_prompt`, `versao_pipeline`, `tokens_entrada`, `tokens_saida`, `tempo_processamento_segundos` | ✅ Sem gap de escala — são fatos objetivos de execução, não julgamentos a calibrar |
| `necessita_revisao` | 🔴 AUSENTE o CRITÉRIO — é um booleano, mas nenhum documento define a condição/limiar que dispara `true` (ex.: `confianca_global` abaixo de quê? presença de ambiguidade registrada?) |

### Achado transversal (o mais importante desta seção)

O White Paper 2.0 (§4, "Axioma da Crença Calibrada", linha 48) declara **explicitamente e deliberadamente** que o sistema **não exige nenhuma família matemática específica** para representar confiança/incerteza: *"Bayesiano, frequentista com intervalo de confiança, lógica fuzzy/possibilística e conformal prediction satisfazem igualmente"* os critérios do axioma. Isso significa que a ausência de escala para `confianca`/`probabilidade_estimada` em todo o Schema 2.1 **não é uma lacuna acidental** — é uma decisão arquitetural ainda em aberto por design, reconhecida pelo próprio White Paper como pertencente a uma camada de especificação posterior (a "Especificação Técnica" citada repetidamente na Constituição). Definir essa escala unilateralmente aqui seria decidir, de fato, uma questão que o White Paper identifica como estruturalmente não resolvida no nível teórico do projeto.

---

## 2. LOTUS — o que existe de fato

> **Correção do usuário — 2026-08-17T23:56:34Z**: LOTUS é uma ferramenta **externa ao repositório Sapiens**. Faz parte da arquitetura pretendida do pipeline, mas ainda não foi integrada ao GitHub/repositório — por isso não há implementação, dependência ou ocorrência dela no código hoje. A ausência confirmada pela busca abaixo é **esperada** e **não deve ser interpretada como evidência de que LOTUS nunca fez parte da arquitetura pretendida** — é evidência apenas de que a integração ainda não foi feita. A tabela e a busca originais desta seção são mantidas abaixo (a busca em si continua factualmente correta — zero ocorrências no repositório); só a interpretação da célula "Premissa externa" muda, conforme reflete a linha atualizada da tabela.

**Busca repetida nesta rodada, no repositório inteiro (não só `pipeline/`), case-insensitive:** zero ocorrências de "LOTUS" em qualquer arquivo de código, configuração, dependência (`requirements.txt` dos 3 apps), documentação (`README.md`, `memory/PRD.md`, `pipeline/memory/ontology_framework.md`) ou nos 13 documentos de `pipeline/docs/`. A única ocorrência da palavra em todo o repositório está no próprio documento de auditoria anterior (`ESPECIFICACAO-MIGRACAO-SCHEMA-2.1-E-PIPELINE.md`), ao registrar essa mesma ausência.

Também verificado: nenhuma dependência de orquestração LLM equivalente está instalada além de `litellm` (já documentado em auditorias anteriores como dependência morta do proxy da Emergent, não usada por `cognitive_engine.py`, que chama o Gemini direto via `google-genai`).

| Categoria | Estado |
|---|---|
| **LOTUS é** | Ferramenta externa ao repositório Sapiens — não um módulo, biblioteca ou serviço que já viva (ou devesse viver) dentro deste código. |
| **Status atual** | Não integrada ao sistema/repositório. Nenhum vestígio de integração (código, config, dependência, chamada de API) existe hoje nos 3 apps. |
| **Função arquitetural pretendida** | Etapa intermediária do pipeline de processamento/anotação — orquestra a passagem do item extraído (`enem-extractor`) para o LLM, sem tomar decisões de ontologia/schema (papel descrito nesta tarefa; não documentado em `pipeline/docs/`). |
| **Implementação no GitHub** | Inexistente atualmente. Confirmado por busca exaustiva no repositório inteiro (ver acima). |
| **Interpretação correta da ausência** | Esperada — decorre de a integração nunca ter sido concluída, não de LOTUS ter sido descartada da arquitetura. Não deve ser lida como "LOTUS não faz parte do plano". |
| **Decisão pendente** | Como e onde integrar LOTUS futuramente, caso seja tecnicamente viável — ver D7 revisado no quadro final. |

**Conclusão desta seção**: a ausência de LOTUS no repositório é um estado de integração pendente, não uma lacuna de especificação a ser preenchida do zero — o "o que ele é" já está decidido fora deste repositório; o que falta é "como conectá-lo a ele".

---

## 3. Separação entre contrato conceitual e JSON Schema formal

`pipeline/docs/Schema anotador de questoes/06 Schema Sapiens 2.1.json.md` é, estruturalmente, um objeto JSON onde cada valor-folha é uma **string descritiva em português**, não uma definição de tipo/enum/obrigatoriedade em JSON Schema (`type`, `enum`, `required`, `minimum`/`maximum`, etc.). É um contrato conceitual, legível por humanos, não um artefato validável por máquina.

**Nesta auditoria, nenhum JSON Schema formal foi redigido**, porque sua estrutura depende diretamente das decisões ainda pendentes mapeadas na §1 — especificamente:
- o `enum` de `processos[].papel` não pode ser escrito até resolver o conflito Schema-2.1-exemplo vs. Manual/Constituição (§1);
- os `type`/`minimum`/`maximum` de todos os campos `peso_no_item`, `confianca`, `dificuldade_local`, `plausibilidade`, `probabilidade_estimada`, `nivel_dificuldade`, `confianca_global` não podem ser escritos até uma escala ser formalmente adotada (§1, e o achado transversal sobre o Axioma da Crença Calibrada);
- o `pattern`/formato de `erro` precisa aceitar tanto IDs `ERR-*` quanto os dois literais especiais do Manual §7 (`"erro não catalogado nesta versão"`, `"sem mecanismo cognitivo identificável"`) — decisão de representação (string livre com valores especiais? enum estendido?) ainda não tomada;
- o limite de tamanho de `processos[]` (máximo 2 com peso, terceiro vira ambiguidade) precisa de uma decisão sobre como isso é representado estruturalmente (validação de array vs. campo de status de ambiguidade separado).

Redigir o JSON Schema agora, antes dessas decisões, exigiria inventar exatamente os elementos listados acima — por isso esta seção documenta *o que falta para poder escrevê-lo*, não o schema em si.

---

## 4. Separação entre anotação do item e dados psicométricos

Os dois grupos de campos do Schema 2.1 têm ciclos de vida fundamentalmente diferentes e **não devem ser preenchidos pelo mesmo processo, no mesmo momento**:

| | Anotação do item (`estrutura_cognitiva`, `distratores`, `intervencoes`, `pedagogia`, `qualidade`, `pipeline{}`) | Dados psicométricos (`psicometria{}`) |
|---|---|---|
| **Quando é preenchido** | No momento da geração/anotação do item — antes de qualquer aluno responder | Só depois de existir volume suficiente de respostas reais de alunos a esse item específico |
| **Quem preenche** | `enem-extractor` (partes determinísticas de `fonte`/`questao`) + LLM/LOTUS (partes de julgamento cognitivo) + código do pipeline (metadados de `pipeline{}`) | Um processo de agregação sobre eventos de resposta reais — **não o pipeline de anotação** |
| **Fonte de dado** | O conteúdo do próprio item (PDF, ontologia) | O event store de behavior (`students/{uid}/behavior`), já consolidado como contrato canônico em `auditoria/ESTADO-CONSOLIDACAO.md` (schema de `pipeline/docs/behavior/07 behavior student 1.4.md`) |
| **Natureza do dado** | Julgamento qualificado (humano ou LLM) sobre o que o item *deveria* mobilizar cognitivamente | Fato observado (o que alunos *de fato* fizeram ao responder) — `dificuldade_empirica`, `discriminacao`, `taxa_acerto`, `tempo_medio`, tudo com definição estatística exigida pelo próprio Schema 2.1 |
| **Pode ser recalculado?** | Só reanotando (nova versão do item) | Sim, e deveria ser — atualiza conforme mais respostas chegam; é dado vivo, não um snapshot único |
| **Existe hoje?** | Não, no Schema 2.1 (existe no Formato A, pré-canônico) | Não — nenhum processo de agregação psicométrica existe em nenhum dos 3 apps hoje |

**Implicação de implementação** (sem propor a implementação em si, só a separação de responsabilidade): o processo que gera/anota o item **nunca** deveria escrever em `psicometria{}` — esse objeto some ou fica nulo na criação, e um processo **separado**, que ainda não existe, seria responsável por lê-lo e atualizá-lo a partir do event store de behavior. Misturar os dois processos no mesmo código violaria a distinção que o próprio Schema 2.1 estabelece entre "dados calculados a partir de dados reais de resposta" e o resto do documento.

---

## 5. Mapeamento completo do pipeline: PDF → armazenamento

| # | Etapa | Artefato | Ferramenta | Entrada | Saída | Contrato aplicável | Status hoje |
|---|---|---|---|---|---|---|---|
| 1 | Upload | Bytes brutos do arquivo | `POST /api/pipeline/generate` (`server.py`) | PDF/imagem enviado pelo usuário | Bytes em memória | Nenhum (binário, sem schema) | ✅ Existe |
| 2 | Extração determinística | JSON próprio do pacote `enem` (não canônico) | `enem-extractor` via `enem_service.extract_enem_pdf` | PDF de questões + (opcional) PDF de gabarito | `{numero, enunciado, enunciado_blocos, imagens[path], alternativas[{index,label,content,correct}]}` | Nenhum documento canônico define esta forma intermediária — é nativa do pacote `enem` | 🔴 Código existe (`enem_service.py`), **não é chamado por nenhuma rota** |
| 3 | Reshape para pré-Schema-2.1 | Objeto parcial no formato do Schema 2.1, só com campos determinísticos preenchidos (`fonte.*`, `questao.enunciado`, `alternativas[].letra/texto/correta`, `recursos.imagens[].arquivo`) | Função de reshape (mapeamento mecânico, ver `ESPECIFICACAO-MIGRACAO-SCHEMA-2.1-E-PIPELINE.md §7`) | Saída da etapa 2 | Item parcial, campos qualitativos ainda vazios | Schema 2.1 (`pipeline/docs/`) — só a parte determinística | 🔴 Não existe |
| 4 | Anotação cognitiva | `estrutura_cognitiva`, `distratores`, `intervencoes`, `pedagogia` (parcial), `qualidade.confianca_global`/`observacoes` | LOTUS (indefinido, §2) + LLM (hoje: Gemini via `google-genai`, chamado direto em `cognitive_engine.py`) | Item parcial da etapa 3 + ontologia ativa (`ontology_v1.4.json`) + (quando existirem) as regras operacionais do Manual (§1–12) | Item quase-completo — falta `psicometria{}` e revisão humana | Schema 2.1 + `ontology_v1.4.json` + Manual de Anotação (regras operacionais, §1) | 🟡 Existe uma versão **fundida** com a etapa 2 em `cognitive_engine.py` (extrai E classifica na mesma chamada) — não a versão separada da arquitetura pretendida |
| 5 | Validação | Relatório pass/fail + violações | Validador (não existe) | Item quase-completo da etapa 4 | Item aprovado ou rejeitado | Schema 2.1 (estrutura/tipos) + `ontology_v1.4.json` (IDs) — mas só cobre o que está definido (não os campos 🔴 da §1) | 🔴 Não existe |
| 6 | Armazenamento | Documento persistido, `item_id` determinístico | Mongo `pipelines` + espelho Firestore `itens` via `firestore_sync.py` | Item validado da etapa 5 | Registro com `item_id`/`item_hash` | Schema 2.1 | 🟡 Mecanismo de persistência existe, mas grava Formato A (não-canônico) com `item_id` aleatório, não determinístico |
| 7 | Atualização psicométrica (fase posterior, processo distinto — ver §4) | `psicometria{}` preenchido/atualizado | Processo de agregação sobre eventos reais (não existe) | Eventos de `students/{uid}/behavior` (Firestore, já canônico) correlacionados por `item_id` | Item atualizado (`update`, não `create`) | Schema 2.1 (`psicometria{}`) + `pipeline/docs/behavior/07 behavior student 1.4.md` | 🔴 Não existe — nenhum dos 3 apps calcula métricas psicométricas hoje |

---

## Quadro de decisões pendentes, priorizado por dependência

Nada abaixo foi decidido por mim. São exatamente os pontos onde a implementação pararia por falta de contrato — na ordem em que precisam ser resolvidos, porque cada um condiciona o seguinte.

| # | Decisão pendente | Por que bloqueia o resto | Quem/o quê precisaria resolver |
|---|---|---|---|
| **D1** | Existe (ou deve existir) um documento "Especificação Técnica"? | Citado por nome 7x em 3 documentos diferentes (`Constituição` 5x, `Ontologia v1.4` 2x, `Manual` 1x) como a autoridade prevista para fórmulas exatas de peso/confiança/plausibilidade. Sem essa decisão, não se sabe se as escalas da §1 devem ser criadas *nesse* documento (a criar) ou em outro lugar. | Mantenedor de `pipeline/docs/` |
| **D2** | Qual literal usar em `processos[].papel`: o exemplo do Schema 2.1 ("nuclear"/"secundario") ou a terminologia do Manual/Constituição ("Central"/"Secundário Necessário")? "Facilitador" é um valor válido ou proibido (Manual §5 diz para não registrar)? | Bloqueia qualquer prompt de LLM ou validador que precise emitir/checar este campo — é usado em praticamente todo item anotado | Mantenedor de `pipeline/docs/` — resolve editando o Schema 2.1 ou o Manual para usar vocabulário único |
| **D3** | Qual família matemática/escala para `confianca` (todos os níveis) e `probabilidade_estimada`? | O White Paper diz explicitamente que isso é uma escolha ainda em aberto por design (Bayesiano/frequentista/fuzzy/conformal todos satisfazem o axioma) — mas o Schema 2.1 pressupõe que uma escolha já foi feita ("escala definida pelo contrato") | Decisão arquitetural de produto, historicamente adiada para a "Especificação Técnica" (D1) |
| **D4** | Escala/bins para `peso_no_item` de `dominios`/`competencias`/`habilidades` (só `processos` está definido, Manual §5) — e se aplica a decisão da Constituição de que Competência "não é rastreada como unidade independente de estado" | Sem isso, `estrutura_cognitiva.dominios[]`/`competencias[]`/`processos[].habilidades[]` não podem ser preenchidos com peso sem inventar | Mantenedor de `pipeline/docs/` — possivelmente resolvendo se `peso_no_item` deveria sequer existir para domínio/competência, dada a posição da Constituição |
| **D5** | Enum/escala para `distratores[].plausibilidade`, `pedagogia.nivel_dificuldade`, `intervencoes[].prioridade`, `qualidade.confianca_global` | Nenhum tem qualquer definição em `pipeline/docs/` hoje — bloqueiam o preenchimento desses campos específicos, mas não bloqueiam os demais | Mantenedor de `pipeline/docs/` |
| **D6** | Representação de `distratores[].erro` quando não há ID de ontologia aplicável — os dois literais do Manual §7 (`"erro não catalogado nesta versão"`, `"sem mecanismo cognitivo identificável"`) fazem parte do domínio de valores do campo, ou deveriam ser um campo/flag separado? | Afeta o desenho do validador (§9 da auditoria anterior) e de qualquer JSON Schema formal (§3) | Mantenedor de `pipeline/docs/` |
| **D7** *(revisado 2026-08-17T23:56:34Z)* | LOTUS é ferramenta externa ao repositório, já definida fora dele — a decisão pendente não é "o que LOTUS é", e sim **como e onde integrá-la** ao pipeline Sapiens (protocolo de chamada, formato de entrada/saída trocado com `enem_service`/`cognitive_engine.py`, credenciais/config necessárias), caso a integração seja tecnicamente viável | Bloqueia toda a etapa 4 da §5 (Anotação cognitiva) da forma separada pretendida; hoje essa etapa está fundida com a etapa 2, sem nenhum ponto de integração para uma ferramenta externa | Você/equipe do produto, junto com quem detém a especificação de LOTUS fora deste repositório — `pipeline/docs/` não define nem precisa definir a ferramenta em si, só o contrato de dados na fronteira (o que entra e o que sai dela) |
| **D8** | Mecanismo para o pipeline receber um PDF de gabarito junto ao PDF de questões (viabiliza `alternativas[].correta` automatizado via `enem_service`, já com suporte técnico existente no pacote) | Sem isso, `correta` não pode ser preenchido de forma confiável no momento da extração | Decisão de produto/UX (como o usuário fornece o gabarito na tela de geração) — não depende de D1–D7 |
| **D9** | Critério/limiar que dispara `pipeline.necessita_revisao = true` | Campo booleano sem regra de disparo definida | Depende parcialmente de D3 (se baseado em `confianca_global`) |

**D1 é o bloqueio-raiz**: D2, D3, D4, D5 e D6 são, na prática, subconjuntos da mesma pergunta — "onde/como a Especificação Técnica que os documentos já preveem vai ser escrita". D7 e D8 são independentes disso (são decisões de infraestrutura/produto, não de conteúdo ontológico). D9 depende de D3.

Nenhuma implementação foi iniciada. Este documento é o fechamento do levantamento pedido — próximo passo, por instrução explícita, é aguardar decisão sobre D1–D9 antes de qualquer alteração em código ou em `pipeline/docs/`.
