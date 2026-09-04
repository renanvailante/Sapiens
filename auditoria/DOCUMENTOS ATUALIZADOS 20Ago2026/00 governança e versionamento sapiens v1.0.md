# 00 governança e versionamento sapiens v1.0 · MD

### Id

GOV-1.0

### Titulo

Governança e Versionamento Sapiens

### Versao

1

### Estado

ativo

### Criado_em

2026-08-17T04:11:33Z

### Atualizado_em

2026-08-17T04:11:33Z

### Eixo

procedimental

### Origem_da_demanda

AUD-2026-08-17T03:42:31Z (Auditoria Integral do Corpus Sapiens), Fase 0, passo 1

### Governa

todos os documentos de pipeline/docs/

### Nao_governa

conteúdo cognitivo, categorias, decisões científicas

# Governança e Versionamento Sapiens — v1.0

## 0. Natureza, escopo e limites deste documento

### 0.1 O que este documento é

Este é um documento **meta-normativo**: ele governa o _processo_ pelo qual os documentos canônicos do Sapiens são criados, corrigidos, versionados, substituídos e aposentados. Ele não contém, e não pode conter, conteúdo cognitivo.

Ele existe por uma razão específica e documentada. A Auditoria Integral do Corpus (AUD-2026-08-17T03:42:31Z) identificou um mecanismo recorrente de falha: **um documento declara preservar algo que o documento seguinte já havia removido, e nada no processo detecta a divergência.** Três instâncias confirmadas: o Error Trace perdeu sua estrutura de cadeia ordenada em dois saltos sucessivos, embora seja declarado ativo protegido; `PROC-ESTR-001` é citado pelo White Paper 2.0 como aresta preservada e não existe na Ontologia v1.4; a camada de decisão pedagógica é declarada vazia por falta de evidência, quando a evidência estava no capítulo 2 do documento anterior.

Esse é o mesmo mecanismo que a Constituição §1.1 identifica como o defeito original da v1.3 — redundância e perda silenciosas por ausência de detecção estrutural — operando um nível acima: entre documentos, em vez de entre nós.

Este documento é o mecanismo de detecção que faltava.

### 0.2 O que este documento explicitamente NÃO faz

Registrado aqui de forma vinculante, para que nenhuma leitura futura o interprete de outro modo:

1. **Não define categorias cognitivas.** Nenhum Domínio, Competência, Processo, Habilidade, Tipo de Erro ou Intervenção é criado, alterado ou removido aqui.
2. **Não altera a Ontologia v1.4**, em nenhum de seus artefatos.
3. **Não altera o Schema Sapiens 2.1** nem o contrato de behavior.
4. **Não toma decisões científicas.** Nenhuma questão em aberto do White Paper 2.0 (os nove Graus de Liberdade do programa de pesquisa) é resolvida, fechada ou reponderada aqui.
5. **Não descongela nada por si.** O congelamento declarado no Manual §12.8 permanece em vigor. Este documento define _como_ um descongelamento pode ocorrer; não o executa.
6. **Não autoriza a Ontologia v1.6.** As condições de entrada declaradas pelo White Paper 2.0 (Cap. 16 — piloto, anotação dupla cega, kappa, ajuste; Cap. 20 — resolução de GL-12b) permanecem integralmente em vigor e são reafirmadas no §11.

### 0.3 Posição no eixo de precedência

Este documento ocupa o **eixo procedimental**, que é ortogonal ao eixo de conteúdo definido no §1.

- Em qualquer questão sobre **como** alterar, versionar, substituir ou registrar um documento, este documento tem precedência sobre todos os demais.
- Em qualquer questão sobre **o que** é verdadeiro, válido ou permitido no domínio cognitivo, este documento é silente e não tem autoridade alguma.

Um conflito entre este documento e um documento de conteúdo é sempre resolvível: se for procedimental, prevalece este; se for de conteúdo, este documento não tem opinião e o conflito é aparente, não real. Se um conflito não puder ser classificado em um dos dois eixos, ele é registrado como **conflito de eixo indeterminado** e escalado ao Curador (§3.1), nunca resolvido por interpretação silenciosa.

---

## 1. Hierarquia e precedência entre documentos canônicos

### 1.1 Espaço canônico

**`pipeline/docs/` é o único espaço canônico.** Um documento existe normativamente se, e somente se, está em `pipeline/docs/` e seu estado (§2) é `ativo` ou `congelado`.

Consequências:

- Nenhum contrato, especificação, ontologia, manual ou schema pode ser criado fora de `pipeline/docs/`.
- `auditoria/` é o espaço de **registro**, não de norma. Auditorias, registros de transação e registros de conflito vivem ali e **nunca** carregam autoridade normativa. Um registro de auditoria descreve; não decide.
- Material externo (por exemplo, a Matriz de Referência do ENEM) é **apoio**, nunca fonte de categorias. Deve residir fora de `pipeline/docs/` ou, se residir dentro, portar `estado: apoio_externo` e uma declaração explícita de não-normatividade.

**Pendência registrada (G-CONF-01, §13.2):** os nove documentos legados do corpus residem atualmente na raiz do Project, não em `pipeline/docs/`. Sua migração é uma transação pendente, não executada nesta rodada.

### 1.2 Camadas e precedência de conteúdo

Da maior para a menor autoridade:

|Camada|Documentos|Autoridade|
|---|---|---|
|**C1 — Axiomática**|White Paper Sapiens (versão ativa)|Define axiomas, pressupostos, graus de liberdade e limites declarados. Nenhum documento inferior pode contradizê-lo nem fechar um Grau de Liberdade que ele mantém aberto|
|**C2 — Constitucional**|Constituição da Ontologia Sapiens|Traduz C1 em regra de engenharia: tipos de nó, critérios de admissibilidade, relações permitidas e proibidas|
|**C3 — Ontológica**|Ontologia Cognitiva Sapiens (versão ativa), em seus artefatos primários|Instancia C2 em um catálogo nomeado e versionado|
|**C4 — Operacional**|Manual de Anotação; Schema Sapiens; contrato de behavior; Especificação do Error Trace|Consome C3. Não cria, remove nem reorganiza nada de C3|
|**C5 — Registro**|Registros de extração, mapas de rastreabilidade, changelogs|Preserva proveniência. Não decide|

### 1.3 Regra de não-inversão

**Um documento de camada inferior não pode resolver uma questão que um documento de camada superior deixou explicitamente em aberto. Pode apenas registrá-la e adotar uma convenção provisória, declarada como tal.**

Uma convenção provisória adotada em C4 precisa satisfazer três condições cumulativas:

1. declarar-se explicitamente provisória e nomear a questão aberta de C1/C2/C3 que a motiva;
2. declarar que não vincula a camada superior;
3. estar registrada no changelog do documento superior como **pendência de arbitragem**.

_Instância conhecida:_ a Ontologia v1.4 §10.7 delega ao Manual a regra de prioridade da fronteira `DOM-CAUSAL` × `DOM-EXPERIMENTAL`, e o Manual §11 a resolve. Isso é uma inversão de hierarquia normativa sob esta regra. Registrado como **G-CONF-06** (§13.2); a correção pertence às etapas 7 e 12 da árvore de dependências, não a este documento.

### 1.4 Regra de remissão

Um documento canônico só pode remeter normativamente a conteúdo que (a) exista, (b) esteja em `pipeline/docs/`, e (c) esteja em estado `ativo` ou `congelado`.

Uma remissão a conteúdo inexistente é uma **remissão pendente** e deve ser registrada como tal no changelog do documento que a contém. Uma remissão pendente **não confere autoridade**: uma regra que se resolve "conforme o Capítulo X" onde X não existe é, para todos os efeitos, uma regra sem conteúdo, e não pode ser invocada para autorizar nem para proibir nada.

_Instâncias conhecidas:_ Constituição §§2.3, 3.4, 3.7.2 e 4.3 remetem aos Capítulos 5, 7, 11 e 12, ausentes; §4.3 remete a uma "Especificação Técnica" que não existe no corpus. Registrado como **G-CONF-04** e **G-CONF-05**.

---

## 2. Estados de um documento

### 2.1 Os quatro estados

|Estado|Significado|Pode ser citado como norma?|Pode ser editado?|
|---|---|---|---|
|**rascunho**|Em elaboração. Existe, mas não vincula|**Não**|Livremente, sem transação|
|**ativo**|Norma vigente e aberta a emenda|Sim|Somente por transação (§3)|
|**congelado**|Norma vigente, fechada a emenda de conteúdo|Sim|Somente por Correção de Fidelidade (§4.3) ou após descongelamento formal (§3.4)|
|**superseded**|Substituído. Preservado para proveniência|**Não**|**Nunca**. Terminal|

### 2.2 Transições permitidas

```
rascunho ──promulgação──> ativo ──congelamento──> congelado
                            │                        │
                            │                   descongelamento
                            │                        │
                            │<───────────────────────┘
                            │
                            └──supersessão──> superseded ──> (terminal)
congelado ──supersessão──> superseded
```

Nenhuma outra transição é válida. Em particular:

- `superseded` é **terminal e irreversível**. Reabilitar conteúdo de um documento superseded exige criar conteúdo novo em um documento ativo, citando o superseded como proveniência (§9) — nunca reviver o documento.
- `rascunho → congelado` é proibido: um documento precisa passar por `ativo` para que suas remissões e conflitos sejam validados.

### 2.3 Estado é obrigatório e explícito

Todo documento canônico porta `estado:` em seu cabeçalho (§7.1). **Ausência de estado declarado = `rascunho`**, portanto sem força normativa.

_Consequência imediata, registrada como **G-CONF-08**:_ os nove documentos legados não portam cabeçalho canônico. Até a transação de retrofit, seu estado é determinado por declaração interna (o Manual §12.8 declara a si e à Ontologia v1.4 como congelados) ou, na ausência dela, presumido `ativo` por uso corrente — presunção que a transação de retrofit deve substituir por declaração explícita.

### 2.4 Duplicatas não têm estado próprio

Uma cópia manual do conteúdo de outro artefato **não é um documento** e não pode receber estado. Ela é resolvida sob o §12 (duplicação silenciosa): ou é declarada artefato derivado regenerável, ou é marcada `superseded` apontando para o artefato primário.

---

## 3. Procedimento formal de emenda

### 3.1 Papéis

Definidos por função, não por pessoa. Uma mesma pessoa pode acumular papéis, mas os atos são distintos e registrados separadamente.

|Papel|Pode|Não pode|
|---|---|---|
|**Curador**|Abrir, aprovar e encerrar transações; promulgar; congelar; descongelar; declarar supersessão|Alterar um documento fora de transação|
|**Auditor**|Registrar conflitos, pendências e divergências em `auditoria/`|Emendar qualquer documento canônico|
|**Anotador**|Produzir anotações sob o Manual vigente; registrar observação de campo|Emendar qualquer documento canônico (reafirma Manual §12.8)|

Um agente de IA operando neste projeto exerce o papel de **Auditor** por padrão, e o de **Curador** apenas sob instrução explícita e por transação nomeada.

### 3.2 Transação Documental

**Toda alteração de documento canônico ocorre dentro de uma Transação Documental.** Uma transação é a unidade atômica de mudança.

Propriedades obrigatórias:

- **Identificador**: `TX-<ISO8601 básico UTC>-<slug>` — por exemplo `TX-2026-08-17T041133Z-patch-err13`.
- **Atomicidade**: se a transação toca N artefatos, ou os N são atualizados, ou nenhum é. Aplicação parcial é inválida e deve ser revertida.
- **Registro**: cada transação gera exatamente um registro em `auditoria/`, que é o artefato **primário** do ato. O changelog dentro de cada documento é **derivado** e cita o `TX-`.
- **Escopo declarado antes da execução**: quais artefatos, qual classe (§3.3), qual justificativa, qual documento de camada superior a autoriza.

### 3.3 Classes de alteração

|Classe|Nome|Definição|Requer descongelamento?|Requer evidência empírica?|
|---|---|---|---|---|
|**I**|**Correção de Fidelidade**|Alinha um artefato a uma decisão **já registrada** em documento de camada igual ou superior. Não introduz decisão nova|**Não**|Não|
|**II**|**Errata**|Corrige erro material sem consequência de dado: aritmética, remissão interna, nome de arquivo, ortografia de rótulo|Não|Não|
|**III**|**Emenda Aditiva**|Acrescenta conteúdo que não invalida nada existente (campo opcional, registro, nota de escopo)|Sim|Conforme §11|
|**IV**|**Emenda Substantiva**|Remove, funde, divide ou redefine conteúdo existente; altera fronteira; altera obrigatoriedade|Sim|Sim (§11)|

**A Classe I é o mecanismo que torna a higiene possível sem reabrir a arquitetura.** Exemplo canônico: o vínculo `PROC-ESPACO-03 → ERR-13` presente nos JSONs contradiz a Ontologia v1.4 §6 e §10.3 e o Manual, que já declarou a correção. Removê-lo é Classe I — não é decisão nova, é alinhamento a decisão registrada. Não requer descongelamento.

**Regra de classificação em caso de dúvida:** classifique na classe **mais alta** plausível. Classificar para baixo é o modo de falha que este documento existe para impedir.

### 3.4 Descongelamento

Um documento `congelado` só volta a `ativo` mediante ato de descongelamento do Curador, que deve declarar, no registro da transação:

1. qual documento é descongelado e por quê;
2. qual classe de alteração se pretende (III ou IV);
3. qual documento de camada superior autoriza a mudança;
4. se Classe IV, qual evidência satisfaz o §11;
5. o escopo fechado da alteração — o que **não** será tocado;
6. o compromisso de recongelamento ao fim da transação.

Descongelamento **não é** autorização genérica de edição. Fora do escopo declarado, o documento permanece congelado.

### 3.5 O que uma transação não pode fazer

- Não pode alterar simultaneamente documentos de camadas não adjacentes (por exemplo, C1 e C4 na mesma transação) sem uma transação intermediária que atualize a camada do meio. Isso impede que uma mudança teórica desça direto ao contrato sem passar pela Constituição e pela Ontologia.
- Não pode marcar um documento como `superseded` sem satisfazer o §8.
- Não pode remover conteúdo sem satisfazer o §9.3.

---

## 4. Correção de erros sem criar divergência entre artefatos

Esta seção existe porque o corpus já contém a falha que ela previne: a mesma decisão registrada em quatro estados diferentes em quatro lugares.

### 4.1 Artefato primário e artefato derivado

Para cada unidade de conteúdo canônico existe **exatamente um artefato primário**. Todos os demais são **derivados** e portam `derivado_de:` em seu cabeçalho.

- Um artefato derivado **nunca** é editado à mão. É regenerado a partir do primário.
- Um artefato sem `derivado_de:` e que replica conteúdo de outro é uma **duplicata**, tratada sob o §12.

### 4.2 Conjunto Normativo Indivisível

Algumas unidades de conteúdo exigem legitimamente mais de um artefato primário — tipicamente uma expressão em prosa (que carrega a justificativa e é auditável por humano) e uma expressão de máquina (que é executável).

Nesses casos, os artefatos formam um **Conjunto Normativo Indivisível (CNI)**, sujeito a:

1. **Declaração mútua**: cada membro nomeia os demais no cabeçalho (`cni_membros:`).
2. **Atualização na mesma transação**: alterar um sem o outro é aplicação parcial, portanto inválida (§3.2).
3. **Divisão de responsabilidade declarada**: qual membro é autoridade sobre quê. Prosa é autoridade sobre justificativa, critério e fronteira; artefato de máquina é autoridade sobre estrutura, cardinalidade e valores.
4. **Ponto de verificação**: a transação só se encerra após verificação explícita de que os membros concordam nos elementos que ambos expressam.

_Aplicação registrada, a executar na etapa 4/5 da árvore de dependências:_ a Ontologia v1.4 em prosa e o `ontology_v1.4.json` constituem um CNI. Um terceiro artefato replicando o JSON em Markdown não é membro do CNI — é duplicata (§12).

### 4.3 Correção de Fidelidade

Procedimento de Classe I (§3.3), aplicável quando um artefato diverge de uma decisão já registrada:

1. **Identificar a decisão de referência** — citar documento, seção e texto exato que a registra.
2. **Demonstrar a divergência** — mostrar o estado atual do artefato e o estado que a decisão exige.
3. **Verificar que nenhuma decisão nova é introduzida** — se a correção exigir escolher entre duas leituras possíveis da decisão de referência, **não é Classe I**; escale para Classe IV.
4. **Aplicar a todos os membros do CNI na mesma transação.**
5. **Verificar contagens derivadas** — qualquer número declarado em qualquer documento que dependa do valor corrigido deve ser reconferido e, se necessário, corrigido na mesma transação ou registrado como pendência nomeada.
6. **Registrar** a transação em `auditoria/` e o changelog derivado em cada artefato tocado.

O passo 5 é o que impede a correção de gerar uma nova divergência — que é exatamente o que aconteceria ao corrigir o JSON sem reconciliar a contagem "13 dos 25 processos" citada pelo Manual.

### 4.4 Proibição de correção silenciosa

Nenhuma correção, por menor que seja, ocorre sem registro. **Uma correção não registrada é indistinguível de uma perda**, e a auditoria demonstrou que o corpus já não consegue distinguir uma da outra retrospectivamente.

---

## 5. Política de versionamento

### 5.1 Escopo

Cada documento canônico tem sua própria linha de versão. Versões de documentos diferentes **não** se sincronizam por número: a Ontologia v1.4 e o Schema 2.1 não têm relação numérica alguma, e o Schema declara isso corretamente. A relação entre eles é expressa por compatibilidade declarada (§6), nunca por coincidência de número.

### 5.2 Semântica `MAIOR.MENOR.CORREÇÃO`

|Incremento|Quando|Efeito sobre artefatos já produzidos|
|---|---|---|
|**CORREÇÃO** (1.4 → 1.4.1)|Classes I e II. Nenhum identificador é criado, removido ou redefinido|Nenhum. Anotações permanecem válidas|
|**MENOR** (1.4 → 1.5)|Classe III. Acréscimos que não invalidam nada|Anotações permanecem válidas; podem ficar incompletas|
|**MAIOR** (1.4 → 2.0)|Classe IV. Remoção, fusão, divisão ou redefinição de identificador existente; mudança de fronteira|Anotações produzidas na versão anterior **exigem remapeamento** antes de serem reutilizadas|

### 5.3 Regra do identificador

**Um identificador nunca muda de significado dentro de uma linha de versão MAIOR.** Se o significado muda, o identificador é aposentado e um novo é criado. Identificadores aposentados **não são reutilizados**, nunca.

Esta regra é uma resposta direta a duas falhas confirmadas pela auditoria: `ERR-05` e `ERR-13` significam coisas diferentes na v1.3 e na v1.4, e o esquema numérico de tipo de erro do White Paper 1.0 colide integralmente com o da v1.4.

### 5.4 Numeração não contígua

Números de versão podem ser saltados, desde que o salto seja registrado com justificativa no changelog. Um número saltado é **queimado**: não pode ser usado depois.

**Pendência registrada (G-CONF-03, §13.2):** a numeração planejada 1.4 → 1.6 salta 1.5 sem justificativa registrada; e a mudança pretendida (expansão para Ciências Humanas e Linguagens, com provável revisão de fronteiras de domínio) tem características de Classe IV, o que sob o §5.2 corresponderia a **2.0**, não a 1.6. Este documento **registra** a divergência e **não a decide** — a decisão pertence ao Curador, na transação que abrir a próxima versão da ontologia.

### 5.5 Versão de artefato derivado

Um artefato derivado não tem versão própria: herda a do primário e declara `derivado_de: <id>@<versao>`.

---

## 6. Relação entre versões de ontologia, schema, manual e demais contratos

### 6.1 Regra de referência versionada

**Nenhum artefato canônico pode referir-se a "a ontologia canônica vigente", "a versão atual" ou equivalente. Toda referência nomeia uma versão.**

Esta é a regra que torna a transição entre versões de ontologia auditável. Sem ela, uma anotação produzida hoje é indatável, e nenhum remapeamento posterior é possível.

_Aplicação pendente:_ o Schema Sapiens 2.1 refere-se repetidamente à "ontologia canônica vigente" e não possui campo de versão de ontologia. A correção pertence à etapa 9 da árvore de dependências; este documento apenas estabelece a regra que a exige.

### 6.2 Matriz de compatibilidade declarada

Todo documento de camada C4 declara, em seu cabeçalho, o intervalo de versões de C3 que suporta:

```
compativel_com:
  ontologia: ">=1.4.1, <2.0"
```

E toda instância de dado produzida sob um contrato C4 carrega, em si, a versão da ontologia contra a qual foi produzida. Contrato e dado declaram a mesma coisa em níveis diferentes: o contrato declara o que aceita; o dado declara o que usou.

### 6.3 Ordem de propagação

Uma mudança em C3 propaga para C4 **nesta ordem**, cada etapa em sua própria transação:

```
C3 (ontologia) → Especificação do Error Trace → Schema → behavior → Manual
```

O Manual vem por último porque é o único documento C4 que cita contagens e listas derivadas do catálogo; atualizá-lo antes garante que ele afirme números que ainda não são verdadeiros.

### 6.4 Regra de não-antecipação

**Um contrato C4 não pode conter campo cuja semântica não esteja definida em C1, C2 ou C3.** Se um campo é necessário antes de a teoria o definir, ele é marcado `provisorio: true` com remissão à questão aberta que o justifica — nunca inserido silenciosamente.

_Instância registrada:_ `processos[].dificuldade_local` e o bloco `psicometria` do Schema 2.1 não têm definição em nenhum documento de camada superior. Registrado como pendência a resolver na etapa 9, não aqui.

---

## 7. Identificação por timestamp e changelog

### 7.1 Cabeçalho canônico obrigatório

Todo documento em `pipeline/docs/` porta front-matter YAML com, no mínimo:

yaml

```yaml
id:              # identificador estável, imutável por toda a vida do documento
titulo:
versao:
estado:          # rascunho | ativo | congelado | superseded
criado_em:       # ISO-8601 UTC, com Z
atualizado_em:   # ISO-8601 UTC, com Z
camada:          # C1 | C2 | C3 | C4 | C5 | procedimental | apoio_externo
supersedes: []
superseded_by:   # null, ou id do documento que o substituiu
derivado_de:     # null, ou <id>@<versao>
cni_membros: []  # se pertence a um Conjunto Normativo Indivisível
compativel_com: {}
remissoes_pendentes: []
```

### 7.2 Formato de tempo

**ISO-8601, UTC, com sufixo `Z`.** Formato estendido (`2026-08-17T04:11:33Z`) no conteúdo; formato básico (`2026-08-17T041133Z`) em nomes de arquivo e identificadores de transação, por compatibilidade de sistema de arquivos. Horário local pode acompanhar, nunca substituir.

### 7.3 Changelog

Cada documento carrega, ao final, um changelog **append-only**. Uma entrada nunca é editada nem removida.

Formato mínimo por entrada: `TX-`, timestamp, classe (§3.3), o que mudou, decisão de referência que autoriza, artefatos co-alterados na mesma transação.

O changelog do documento é **derivado**; o registro em `auditoria/` é o primário (§3.2). Em caso de divergência entre os dois, prevalece o registro de auditoria, e a divergência é ela mesma um incidente a registrar.

### 7.4 Sem índice central editado à mão

Não existe changelog central mantido manualmente. Um índice consolidado, se desejado, é gerado a partir dos registros de `auditoria/` e porta `derivado_de:`. Um índice mantido à mão seria uma duplicata (§12).

---

## 8. Como um documento declara que outro foi superseded

### 8.1 Declaração bidirecional obrigatória

A supersessão só é válida quando **ambos** os documentos a declaram:

- o documento novo declara `supersedes: [<id do antigo>]`;
- o documento antigo declara `superseded_by: <id do novo>` e muda `estado:` para `superseded`.

Uma declaração unilateral é **inválida** e o documento antigo permanece com sua autoridade anterior. Isso impede a supersessão silenciosa, em que um documento novo assume o lugar de outro sem que o antigo saiba, e leitores continuam citando o antigo como norma.

### 8.2 Registro de Extração prévio — regra central

> **Nenhum documento pode ser marcado como `superseded` antes que exista um Registro de Extração aprovado, listando o conteúdo que ele contém e que não foi transportado para o documento sucessor.**

Esta é a codificação direta da lição central da auditoria. A transição do White Paper 1.0 para o 2.0 ocorreu sem registro de extração, e o resultado documentado foi a perda de quatorze elementos, três deles declarados ativos protegidos pelo próprio documento sucessor.

O Registro de Extração deve, para cada elemento não transportado, dizer: o que era, onde estava, se foi substituído, removido ou contradito, e se deve ser recuperado. Um elemento que ninguém examinou não pode ser declarado descartado — apenas "não examinado", o que impede a supersessão.

### 8.3 Supersessão parcial

Um documento pode ser superado **em parte**. Nesse caso:

- o documento superado permanece `ativo` ou `congelado`;
- a seção superada é marcada em linha com `[SUPERSEDED por <id> — TX-...]`;
- o changelog registra a supersessão parcial;
- a seção superada **deixa de ter força normativa imediatamente**, mesmo permanecendo no texto.

_Aplicação pendente:_ o White Paper 2.0, Parte V (Capítulos 13 e 14) é superado pela Ontologia v1.4 em seu inventário de domínios, competências e processos. A marcação pertence à etapa 11 da árvore de dependências.

### 8.4 Efeito sobre citações

A partir da supersessão, citar o documento superseded como norma é erro. Ele permanece citável para **proveniência** — sempre com a marcação explícita de que é fonte histórica.

---

## 9. Rastreabilidade de decisões herdadas

### 9.1 Bloco de proveniência

Todo elemento que atravessa uma versão carrega proveniência explícita. A Ontologia v1.4 já estabelece o precedente correto com `origem_v1_3` em cada processo; esta seção generaliza a prática:

yaml

```yaml
proveniencia:
  origem: [<ids na versão anterior>]
  versao_origem: <versão>
  transacao: TX-...
  status_herdado: preservado | modificado | rebaixado | removido | contradito
  justificativa: <texto curto>
```

### 9.2 Os cinco status

|Status|Significado|
|---|---|
|**preservado**|Idêntico em conteúdo e obrigatoriedade|
|**modificado**|Mesma identidade, conteúdo alterado. Exige registro do que mudou|
|**rebaixado**|Deixou de ser norma e passou a ser hipótese, proposta ou decisão de engenharia. **Não é remoção**|
|**removido**|Deixou de existir. Exige registro de remoção (§9.3)|
|**contradito**|Um documento posterior afirma o oposto. **Estado de exceção**: exige arbitragem do Curador antes do encerramento da transação|

A categoria **rebaixado** é necessária e foi o que faltou na transição 1.0 → 2.0: a camada de decisão pedagógica não foi removida nem preservada — deveria ter sido rebaixada de especificação a proposta de engenharia não derivada dos axiomas, e foi tratada como inexistente.

### 9.3 Remoção exige registro; silêncio não remove

**Um elemento presente em uma versão e ausente na seguinte, sem registro de remoção, é uma perda, não uma decisão.** Ao ser detectado, é tratado como incidente: registrado em `auditoria/`, e o Curador decide entre restaurar ou remover formalmente.

### 9.4 Cadeia de proveniência contínua

A cadeia de proveniência não pode ter elos ausentes. Se a versão N cita a versão N−1 e a N−1 não está no espaço canônico em nenhum estado — inclusive `superseded` — a cadeia está rompida e **todas as referências de proveniência que a atravessam são pendentes**.

_Instância confirmada:_ os 25 processos da Ontologia v1.4 portam `origem_v1_3` apontando para identificadores de uma versão 1.3 que não existe no corpus. Toda a proveniência da v1.4 é, hoje, uma remissão pendente. Registrado como **G-CONF-09** (§13.2); documentado em detalhe no Mapa de Rastreabilidade de IDs.

---

## 10. Preservação e rastreamento de [EC], [IT] e [DE]

### 10.1 As três categorias, tal como já estabelecidas

Este documento **não redefine** a disciplina categorial; ela pertence ao White Paper e é ativo protegido. Reproduz-se aqui apenas o necessário para governá-la:

- **[EC]** — Evidência Científica Consolidada
- **[IT]** — Interpretação Teórica
- **[DE]** — Decisão de Engenharia Sapiens

### 10.2 Regras de governança

1. **A etiqueta acompanha a afirmação.** Ao ser transportada, citada ou reformulada em outro documento, a afirmação leva sua etiqueta. Transporte sem etiqueta é perda de proveniência.
2. **Etiqueta só muda por transação registrada.** Nunca por reescrita editorial.
3. **Rebaixamento é livre; promoção é restrita.** [EC]→[IT], [IT]→[DE] e [DE]→hipótese podem ocorrer por decisão registrada. [DE]→[IT] e [IT]→[EC] exigem citação nova e resolvível, e são Classe IV.
4. **[EC] exige citação resolvível.** Uma afirmação [EC] sem referência recuperável é rebaixada automaticamente a [IT] até que a referência seja restaurada. _Consequência registrada:_ o White Paper 2.0 cita autores sem seção de referências; a restauração pertence à etapa 11.
5. **Grau de confiança é ortogonal à etiqueta.** O percentual de confiança do White Paper 2.0 e a etiqueta EC/IT/DE são dois eixos independentes. Ambos viajam juntos; nenhum substitui o outro.
6. **Nenhuma etiqueta é atribuída por inferência.** Se a proveniência de uma afirmação não for determinável, ela é marcada `[?]` e registrada como pendência — nunca classificada por plausibilidade.

### 10.3 Aplicação a conteúdo recuperado de documento superseded

Conteúdo recuperado de um documento `superseded` entra no documento novo com sua etiqueta original **e** com proveniência (§9.1). Se o documento sucessor já havia rebaixado essa afirmação, prevalece o rebaixamento, e a etiqueta original permanece registrada como histórico.

---

## 11. Vinculação de mudanças de ontologia ao protocolo de piloto

### 11.1 Reafirmação da condição de entrada

O White Paper 2.0, Cap. 16, declara que a sequência **banco-piloto → anotação dupla e independente → medição de concordância interavaliador (kappa) → ajuste da ontologia** é _"condição de entrada para qualquer expansão de escopo, não uma recomendação entre outras"_, e o Cap. 20 condiciona a expansão para Ciências Humanas e Linguagens à resolução de GL-12b.

**Este documento não altera, flexibiliza nem interpreta essa condição.** Ele apenas define quais classes de mudança a acionam.

### 11.2 Classes de mudança ontológica quanto à exigência de evidência

|Classe|Exemplos|Evidência exigida|
|---|---|---|
|**A — Fidelidade e forma**|Corrigir vínculo divergente entre artefatos do CNI; corrigir aritmética; acrescentar campo de proveniência ou versionamento|**Nenhuma.** Corresponde às Classes I e II do §3.3|
|**B — Estrutura interna**|Fundir, dividir, criar ou remover nó; alterar fronteira entre domínios; alterar cardinalidade de relação|**Piloto concluído** com dados de concordância sobre os nós afetados|
|**C — Expansão de escopo**|Incluir nova área do conhecimento; ativar heterarquia; introduzir novo tipo de nó|**Piloto concluído + resolução registrada do Grau de Liberdade específico** que o White Paper mantém aberto para aquela expansão|

### 11.3 Regra da ausência de evidência

Na ausência de evidência empírica, a Constituição §2.4 já fixa a direção: **a fusão é o estado padrão; a separação é que precisa ser justificada.** Este documento não altera essa regra — apenas registra que ela é o critério a aplicar quando uma mudança de Classe B for proposta antes do piloto, e que a resposta correta nesse caso é adiar a mudança, não decidi-la por conveniência.

### 11.4 O que este documento explicitamente não autoriza

A Ontologia v1.6 permanece **não autorizada**. Ela é mudança de Classe C. As condições do §11.2 não estão satisfeitas: não há piloto executado, não há medição de kappa, e GL-12b permanece aberto.

Este documento torna a v1.6 _construível_ — porque agora existe um procedimento pelo qual ela poderia ser legitimamente autorizada. Não a autoriza.

---

## 12. Regra contra duplicação silenciosa de contratos

### 12.1 Regra

**Para cada unidade de conteúdo canônico existe exatamente um artefato primário, ou um Conjunto Normativo Indivisível declarado. Qualquer outro artefato que expresse o mesmo conteúdo é derivado e deve declará-lo, ou é duplicata e deve ser eliminado.**

### 12.2 Teste de duplicação

Dois artefatos são duplicatas quando expressam o mesmo conjunto de identificadores ou o mesmo contrato de campos, e **nenhuma** das condições abaixo se verifica:

1. são membros declarados de um mesmo CNI (§4.2);
2. um declara `derivado_de:` o outro e é regenerável sem intervenção manual;
3. um está em estado `superseded` apontando para o outro.

### 12.3 Procedimento ao detectar duplicata

1. Determinar qual artefato é primário — critério: aquele que os demais documentos citam normativamente; em empate, o de formato executável.
2. Verificar se os conteúdos divergem. **Se divergirem, isso é um incidente**, registrado antes de qualquer eliminação, porque a divergência pode conter uma decisão real que ninguém registrou.
3. Marcar o não-primário como `superseded`, apontando para o primário.
4. Corrigir toda citação que apontava para o artefato eliminado.

_Aplicação pendente:_ a Ontologia v1.4 possui um terceiro artefato que replica o JSON em Markdown, sem declaração de derivação. É duplicata sob o §12.2. A comparação campo a campo já executada pela auditoria não encontrou divergência de conteúdo, o que torna o passo 2 satisfeito. A supersessão pertence à etapa 6 da árvore de dependências.

### 12.4 Proibição prospectiva

Nenhuma transação futura pode criar um artefato que replique conteúdo canônico sem declarar `derivado_de:`. Colar o conteúdo de um artefato dentro de outro documento, para conveniência de leitura, cria uma duplicata — independentemente da intenção.

---

## 13. Autovalidação

### 13.1 Coerência interna

Verificações executadas sobre este documento:

|#|Verificação|Resultado|
|---|---|---|
|1|Todo estado do §2.1 aparece no diagrama de transições do §2.2|OK|
|2|Toda transição do §2.2 tem procedimento definido no §3 ou §8|OK — promulgação e congelamento §3.1/§3.4; descongelamento §3.4; supersessão §8|
|3|As classes de alteração do §3.3 mapeiam 1:1 nos incrementos de versão do §5.2|OK — I/II→CORREÇÃO, III→MENOR, IV→MAIOR|
|4|As classes de alteração do §3.3 mapeiam nas classes de evidência do §11.2|OK — I/II→A, III/IV→B ou C conforme escopo|
|5|Nenhuma seção define categoria cognitiva|OK|
|6|Nenhuma seção altera ontologia, schema ou behavior|OK — todas as menções são registro de pendência com etapa atribuída|
|7|Nenhuma seção fecha Grau de Liberdade do White Paper 2.0|OK — §11.1 e §11.3 os reafirmam como abertos|
|8|Nenhuma remissão deste documento a conteúdo inexistente|OK — todas as remissões externas são a documentos presentes no corpus ou a pendências explicitamente nomeadas como tais|
|9|O documento satisfaz sua própria regra de cabeçalho (§7.1)|OK|
|10|O documento satisfaz sua própria regra de não-duplicação (§12)|OK — não replica conteúdo de nenhum documento canônico; as citações são referenciais e nomeadas|

### 13.2 Conflitos com documentos canônicos existentes

Registrados aqui e no registro de conflitos correspondente em `auditoria/`. **Nenhum foi corrigido nesta transação.**

|ID|Conflito|Natureza|Etapa de resolução|
|---|---|---|---|
|**G-CONF-01**|Os nove documentos canônicos residem na raiz do Project; este documento declara `pipeline/docs/` como espaço canônico único (§1.1)|Divergência de namespace canônico. Enquanto durar, há duas leituras possíveis de onde vive a norma|Transação de migração, a agendar. Não bloqueia as etapas 2–3|
|**G-CONF-02**|Manual §12.8 declara Manual e Ontologia congelados sem prever caminho de descongelamento|Aparente, não real: o §3.4 fornece o caminho ausente, e a Classe I (§3.3) torna a higiene possível sem descongelar. Mas o Manual continuará afirmando um congelamento sem saída até ser atualizado|Etapa 7 (Manual v1.1)|
|**G-CONF-03**|Numeração 1.4 → 1.6 salta 1.5 sem justificativa; a mudança pretendida tem características de Classe IV, que sob o §5.2 corresponderia a 2.0|Divergência de política. **Registrada, não decidida**|Decisão do Curador na transação que abrir a próxima versão da ontologia|
|**G-CONF-04**|Constituição §4.3 remete a uma "Especificação Técnica" inexistente|Remissão pendente (§1.4). A regra que dela depende está sem conteúdo|Etapa 8 (Especificação do Error Trace) e etapa 12|
|**G-CONF-05**|Constituição cita os Capítulos 5, 7, 11 e 12, ausentes do documento|Remissão pendente (§1.4), em pontos decisivos: critérios de inclusão, granularidade, protocolo de teste, questões diferidas|Etapa 12|
|**G-CONF-06**|Ontologia v1.4 §10.7 delega ao Manual a fronteira `DOM-CAUSAL` × `DOM-EXPERIMENTAL`; o Manual §11 a resolve|Inversão de hierarquia normativa (§1.3). A convenção do Manual não satisfaz as três condições do §1.3|Etapas 7 e 12|
|**G-CONF-07**|Schema Sapiens 2.1 refere-se à "ontologia canônica vigente" sem nomear versão, contrariando o §6.1|Impossibilita datar e remapear anotações|Etapa 9|
|**G-CONF-08**|Nenhum dos nove documentos legados porta cabeçalho canônico (§7.1); seu estado é presumido, não declarado|Sob o §2.3, ausência de estado declarado equivale a `rascunho`, o que retiraria força normativa de todo o corpus. **Resolvido provisoriamente** pela presunção do §2.3 (declaração interna ou uso corrente), até o retrofit|Transação de retrofit de cabeçalho, a agendar junto com G-CONF-01|
|**G-CONF-09**|Toda a proveniência da Ontologia v1.4 (`origem_v1_3`) aponta para uma versão 1.3 ausente do corpus|Cadeia de proveniência rompida (§9.4). Todas as referências de origem da v1.4 são pendentes|Registrado em detalhe no Mapa de Rastreabilidade de IDs. Resolução exige localizar a v1.3 e incorporá-la como `superseded`, ou declarar formalmente a cadeia como irrecuperável|
|**G-CONF-10**|Schema 2.1 contém campos (`dificuldade_local`, bloco `psicometria`) sem definição em camada superior, contrariando o §6.4|Contrato à frente da teoria|Etapa 9|

**Nenhum conflito acima impede a execução das etapas 2 e 3 da Fase 0** (Registro de Extração e Mapa de Rastreabilidade), que são documentos de camada C5 e não alteram norma.

---

## 14. Changelog

|TX|Timestamp|Classe|Alteração|Autoriza|Co-alterados|
|---|---|---|---|---|---|
|`TX-2026-08-17T041133Z-gov-v1`|2026-08-17T04:11:33Z|— (criação)|Criação do documento em estado `ativo`|AUD-2026-08-17T03:42:31Z, Fase 0, passo 1|nenhum|

_Fim do documento. Nenhum documento canônico preexistente foi alterado por esta transação._

## Não foi possível abrir o arquivo. (×2)