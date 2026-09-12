# Proposta de evolução — do diagnóstico ao ciclo adaptativo

**Status:** aprovada e **implementada** em 2026-09-09. **Alvo:** app `aluno`.

> O que foi construído, e onde o desenho final divergiu deste documento (com o
> motivo de cada divergência), está em
> [`ciclo-adaptativo-implementacao.md`](./ciclo-adaptativo-implementacao.md).
> Este documento fica como está: ele é a decisão, não o registro da obra.

## Como ler este documento

Cada fase declara **problema → o que já existe → o que construir → mecanismo →
restrições → critérios de aceite**. A seção "o que já existe" é normativa: se
ela cita um módulo, esse módulo **não deve ser reescrito**, apenas estendido.

O §1 lista quatro restrições que valem para todas as fases. Uma fase que
precise violar qualquer uma delas não é uma fase difícil — é uma fase que
precisa ser reprojetada.

---

## 0. A tese

O Sapiens já produz o objeto caro: o **Error Trace** — a cadeia ordenada que
explica *uma* resposta errada de *um* aluno a *um* item, cuja raiz seleciona a
intervenção catalogada (`aluno/backend/motor_cognitivo.py`).

O que ele ainda não faz é **fechar o laço**. O traço é produzido, agregado e
exibido; nada no sistema volta a testar se a intervenção funcionou. O produto
observa, mas não age nem verifica.

A proposta é fechar esse laço:

```
observar → interpretar → intervir → reter → retestar → estabilizar → transferir
```

Cinco fases, nesta ordem. Não são cinco funcionalidades: são cinco camadas do
mesmo ciclo, e cada uma só faz sentido sobre a anterior.

**A mudança de paradigma:** a unidade de planejamento deixa de ser *"o aluno
estuda Biologia hoje"* e passa a ser *"este é o conjunto de intervenções mais
útil para o estado observado deste aluno hoje"*. O `StudyPlan` deixa de ser um
documento e passa a ser uma consequência.

---

## 1. Restrições que governam todas as fases

### 1.1 O portão de crença está aberto, e por isso tudo é provisório

`aluno/backend/portao_crenca.py` implementa Error Trace §6 / EXT-WP1-1.0 L13b:

> um item pode ser ARMAZENADO sem revisão humana; não pode INFLUENCIAR o
> estado de um estudante real sem ela.

Desde 2026-09-04, produção roda com `PORTAO_CRENCA_MODO=desligado`, porque o
corpus inteiro está sem revisão humana e o Motor Cognitivo ficava vazio para
todo aluno. O bloqueio saiu; a regra não. Todo traço entra marcado como
`provisorio`, e `motor_cognitivo.perfil()` declara o perfil inteiro provisório
com um aviso textual ao aluno.

**Consequência direta para esta proposta:** as cinco fases consomem o mesmo
perfil provisório. Construir as cinco sobre um corpus não revisado significa
multiplicar por cinco as superfícies em que o produto afirma causalidade sobre
o aluno sem evidência revisada. Isso é risco de produto *e* violação de
governança.

Por isso existe a **Fase 0** (§2), e por isso **toda tela nova das Fases 1–4
herda a obrigação de rotular hipótese como hipótese** — não é decisão de
copy, é requisito.

### 1.2 Nada pode custar O(eventos) por requisição

Escrito em sangue: em 2026-09-04 a cota diária de 50 mil leituras do Firestore
foi esgotada por um laço de background e **toda rota autenticada** passou a
falhar. `aluno/backend/tests/test_custo_firestore.py` existe para travar as
ordens de grandeza.

O padrão estabelecido é agregado incremental no documento `students/{uid}`,
mantido no ato da escrita com `Increment`/`ArrayUnion` e lido em 1 leitura —
ver `firestore_service._atualizar_agregado` e `increment_treino_stats`.

`motor_cognitivo._ler_historico` é a exceção deliberada: varre a subcoleção
`behavior` inteira, memorizada por `total_respostas`. Isso significa **uma
varredura completa a cada resposta nova**. Nenhuma fase pode adicionar uma
segunda varredura, e nenhuma fase pode chamar `perfil()` a cada resposta.

**Regra:** todo estado novo destas fases é mantido incrementalmente na escrita
e lido em O(1). Se o desenho pede recomputar, o desenho está errado.

### 1.3 As regras do Error Trace não são negociáveis

De `motor_cognitivo.py`, "Fronteiras que este módulo NÃO cruza":

| Regra | O que proíbe | Onde ameaça esta proposta |
|---|---|---|
| **R-1** | inventar vínculo Erro→Processo fora do catálogo | Fase 3 (autorrelato) |
| **R-3** | determinizar causa; toda atribuição carrega `confianca` | Fase 5 ("padrão confirmado") |
| **§1.1** | tratar manifestação (`ordem >= 2`) como causa | Fases 1 e 2 |
| **§4.2** | usar `mecanismo` (`MEC-*`) para escolher intervenção ou exibir | todas |
| **R-7** | alterar a ontologia automaticamente | Fase 5 |

### 1.4 Medida pedagógica é gratuita

`motor_routes.py` é explícito: o motor não chama LLM, logo não cobra Sparks.
O que custa Spark é **geração de conteúdo** (Mentis, mapa cosmético), não
medida.

**Fases 1, 2 e 4 são gratuitas** — são agregação sobre dados que o próprio
aluno gerou. A Fase 3 é gratuita por construção (§5). A Fase 5 não é
voltada ao aluno (§7). Se alguma fase precisar cobrar, isso é sinal de que ela
está gerando conteúdo onde deveria estar medindo.

---

## 2. Fase 0 — Destravar a evidência

**Não é uma funcionalidade. É o pré-requisito das outras cinco.**

### Problema

Duas escassezes silenciosas bloqueiam o ciclo:

1. **Revisão humana.** Zero itens revisados ⇒ portão desligado ⇒ perfil
   provisório para todos (§1.1).
2. **Oferta de itens.** As Fases 1, 2 e 5 consomem itens de reteste por
   processo. Se o acervo tem 3 itens ancorados em `PROC-x`, a "fila de
   revisão" repete as mesmas questões e o reteste mede memória do item, não
   estabilização da habilidade. Ninguém mediu essa oferta ainda.

### O que construir

1. **Fluxo de revisão no admin.** Uma tela que lista traços por par
   (`erro`, `processo_afetado`), mostra o item e o distrator, e permite ao
   revisor confirmar ou rejeitar o elo de ordem 1. Confirmar grava
   `qualidade.apto_para_camada_de_crenca` no item. É o único caminho legítimo
   para religar o portão.
2. **Relatório de oferta.** Script/rota admin que responde, por processo do
   catálogo: quantos itens existem, quantos estão anotados com
   `distratores[].erros_esperados`, quantos têm bloco `intervencoes[]`. Ele
   define quais processos podem entrar nas Fases 1/2 e quais não.

### Critério de aceite

- É possível revisar um item e ver `portao.tracos_no_perfil` subir com
  `PORTAO_CRENCA_MODO=crenca`.
- O relatório de oferta existe e está anexado à decisão de escopo da Fase 1.
- Nenhuma fase seguinte é iniciada para um processo cuja oferta o relatório
  reprove.

---

## 3. Fase 1 — Fila de revisão espaçada

### Problema

`/plan/:analysisId` (`frontend/src/pages/StudyPlan.jsx`, 81 linhas) é um
snapshot preso a uma análise: lê `study_plan` de um documento antigo e o
renderiza. Ele não reage ao que o aluno demonstrou ontem, não sabe o que já
foi trabalhado e não tem noção de tempo.

Anki e Quizlet resolvem espaçamento sem saber **por que** o aluno errou. O
Sapiens sabe — e não usa essa informação para agendar nada.

### O que já existe (não reconstruir)

`motor_cognitivo._priorizar()` **já produz a fila** — por processo, com
`origem` (`error_trace` | `desempenho`), `peso_raiz` (soma de confiança,
que é a grandeza calibrada exigida pela Constituição §4.4), `ocorrencias_raiz`,
`erro_dominante` e `intervencao` catalogada. Já separa raiz de manifestação e
já ordena prescritíveis antes de sentinelas.

**O que falta não é a fila. É o eixo do tempo.**

### O que construir

Uma camada temporal sobre `_priorizar()`, com três estados que hoje não
existem:

| Estado | Definição operacional |
|---|---|
| **em consolidação** | processo com raiz recente e reteste ainda não vencido |
| **erro recorrente** | ≥ N raízes do mesmo par (erro, processo) em janelas distintas |
| **em deterioração** | acerto da janela recente abaixo do acerto da janela anterior no mesmo processo |

A tela entrega uma fila diária fechada e curta:

```
Revisões de hoje · 8 questões
  3 habilidades em consolidação
  2 erros recorrentes
  2 conceitos em deterioração
  1 transferência recomendada
```

"Transferência" = item do mesmo processo ancorado em **contexto/domínio
diferente** do item que originou a raiz. Se o relatório da Fase 0 disser que
não há item assim para aquele processo, a linha simplesmente não aparece —
nunca se degrada para "mais um item igual".

### Mecanismo (e o orçamento de leitura)

Nada disso pode nascer de varrer `behavior`. Novo bloco no documento
`students/{uid}`, mantido na escrita da resposta
(`firestore_routes.register_answer` → `firestore_service`):

```
students/{uid}.revisao = {
  "PROC-xx": {
    janela_atual:   {respondidas, acertos, inicio},
    janela_anterior:{respondidas, acertos},
    raizes_recentes: [{erro, ts}, ...],   # LIMITADO, ver risco §8
    proximo_reteste: "2026-09-12",
    ultimo_reteste:  {ts, acertou}
  }
}
```

Escrita: um `set(merge=True)` a mais por resposta, no mesmo documento que
`agregado` e `treino_agregado` já usam. Leitura da fila: **1 leitura**.

O agendamento é uma função pura sobre esse bloco — intervalo cresce a cada
reteste acertado, colapsa para o mínimo a cada raiz nova do mesmo par. Sem IA,
sem Firestore extra, testável isoladamente.

### Restrições

- Só elos de `ordem: 1` agendam reteste. Manifestação não agenda nada (§1.1).
- Processo cuja raiz dominante é sentinela (`SENTINELAS`) entra na fila **sem
  prescrição**, depois dos prescritíveis — igual `_priorizar()` já faz.
- Enquanto o perfil for provisório, a fila diz "com base em uma leitura ainda
  não revisada" (§1.1).

### Critérios de aceite

- Teste em `test_custo_firestore.py`: montar a fila diária custa **1 leitura**,
  independente do número de eventos do aluno.
- Teste: uma raiz nova do mesmo par colapsa `proximo_reteste` para o mínimo.
- Teste: reteste acertado expande o intervalo; reteste errado não expande.
- Teste: nenhum elo de `ordem >= 2` produz agendamento.
- `StudyPlan.jsx` passa a consumir a fila e o link `/plan/:analysisId` continua
  funcionando (histórico não pode quebrar).

---

## 4. Fase 2 — Professor Invisível

### Problema

Hoje o aluno precisa **descobrir sozinho** que tem um padrão. O motor já
detectou; a informação espera um clique que talvez nunca venha.

### O que já existe (não reconstruir)

Mais do que a proposta original supõe. **A intervenção já é montada
localmente, sem IA:**

- `intervencoes.montar(processo_id, tracos, itens_respondidos)` compõe o plano:
  nome vindo do catálogo (`INT-01..INT-11`), **ação concreta vinda do bloco
  `intervencoes[]` do próprio item que o aluno errou**, passos de
  `pedagogia.passos`, e enquadramento autoral declaradamente não normativo.
- `intervencoes.sugerir_pratica()` já sugere itens de prática por processo, com
  `_SEGURANCA` impedindo vazamento de gabarito de item não respondido.
- `CardDeMelhora.jsx`, `IntervencaoMentis.jsx` e `MentisPedido.jsx` já são a
  superfície — e já carregam a regra de 2026-09-09 de que nenhum card de erro é
  beco sem saída, e de que mensagem pré-pronta nunca é enviada sozinha.

**O que falta é só o gatilho.** Isto é *push* sobre uma máquina de *pull* que
já funciona — não um subsistema novo.

### O que construir

Um avaliador de gatilho que roda **na escrita da resposta**, sobre o bloco
`revisao` da Fase 1, e decide se há evidência suficiente para interromper.

Limiares: reusar os que já existem — `MIN_TRACOS_RAIZ = 2`, `MIN_RESPOSTAS`.
Inventar limiares novos criaria duas noções divergentes de "evidência
suficiente" no mesmo produto.

Gatilhos, em ordem de confiança:

1. **recorrência** — mesmo par (erro, processo) atinge `MIN_TRACOS_RAIZ` em
   janelas distintas;
2. **deterioração** — processo antes estável cai de janela para janela;
3. **reteste falho** — o aluno errou o item de reteste agendado.

Os demais gatilhos da proposta original (inconsistência entre contextos,
falha de transferência, discrepância conhecimento×desempenho) dependem de
metadado de contexto por item que o relatório da Fase 0 talvez não confirme.
**Ficam fora da v1** e voltam quando houver dado que os sustente.

Disciplina de interrupção — obrigatória, senão o professor invisível vira
pop-up:

- no máximo **uma** intervenção ativa por vez;
- cooldown por par (erro, processo): disparado, não redispara antes do reteste;
- o aluno pode dispensar, e dispensar conta como sinal.

### Restrições

- O gatilho **seleciona** intervenção pela raiz catalogada — nunca por
  semelhança de tema, e nunca por `MEC-*` (§4.2).
- Texto vem de `intervencoes.montar()`. Nenhuma chamada a LLM nesta fase.
- Perfil provisório ⇒ a intervenção se apresenta como hipótese, com o mesmo
  rigor do aviso de `perfil()`.

### Critérios de aceite

- Teste: avaliar o gatilho custa **0 leituras adicionais** no caminho de
  `register_answer`.
- Teste: uma única raiz não dispara (`MIN_TRACOS_RAIZ`).
- Teste: cooldown impede redisparo do mesmo par antes do reteste.
- Teste: nunca há duas intervenções ativas simultâneas.

---

## 5. Fase 3 — Microdiagnóstico ("por que você escolheu isso?")

Esta é a fase mais valiosa da proposta — é a única que adiciona **evidência
nova**, em vez de reorganizar a que já existe. Também é a mais perigosa, e o
desenho abaixo diverge deliberadamente da proposta original.

### Problema

Dois alunos marcam a alternativa C pelo mesmo motivo aparente e por processos
completamente diferentes. Hoje o motor infere a causa a partir de
`distratores[].erros_esperados[]` — a hipótese **do anotador** sobre quem marca
aquele distrator. Ninguém pergunta ao aluno.

### O que construir

Depois de uma resposta selecionada, uma micropergunta opcional de **um toque**,
com alternativas fechadas:

> **O que te levou a essa alternativa?**
> · Eu não sabia o conteúdo
> · Entendi o enunciado de outro jeito
> · Sabia, mas errei a conta / o passo
> · Fiquei entre duas e chutei
> · Chutei sem ideia

### A correção mais importante desta proposta

O autorrelato **não pode entrar na mesma escala de confiança do Error Trace.**

O traço tem `produtor: "regra"` e é derivado de catálogo. O autorrelato é outro
produtor — proposta: `autorrelato` — e outra epistemologia: aluno
pós-racionaliza, e ele frequentemente não sabe por que errou. Fundi-lo ao
`peso_raiz` seria exatamente o "inventar vínculo Erro→Processo" que **R-1**
proíbe, e o "determinizar causa" que **R-3** proíbe.

Portanto:

1. Grava-se no evento de `behavior`, em campo próprio, **sem** virar elo de
   cadeia.
2. Ele **corrobora ou contradiz** uma raiz já atribuída pelo catálogo. Nunca
   cria raiz.
3. Alternativas fechadas, **não** texto livre. Texto livre exigiria um LLM
   para classificar — custo recorrente, e um classificador produzindo vínculo
   causal fora do catálogo é R-1 por outra porta.
4. O valor de curto prazo é **interno**: contradição sistemática entre o
   autorrelato e a hipótese do anotador é o melhor detector de anotação ruim
   que o sistema pode ter — e alimenta a revisão humana da Fase 0. O laço se
   fecha.

### Quando perguntar

Não em toda questão — a proposta original está certa nisso, e o critério pode
ser barato: pergunte quando o distrator marcado tem cadeia anotada **e** o par
ainda tem poucas confirmações. Onde o valor diagnóstico é alto e a amostra é
baixa.

### Critérios de aceite

- Nenhum autorrelato altera `peso_raiz`, `ocorrencias_raiz` ou
  `mapa_de_erros`. Teste explícito para isso.
- O evento continua válido sob o contrato 1.1 de behavior.
- Pular a pergunta é indistinguível, para o aluno, de não tê-la recebido.
- Existe relatório admin de concordância autorrelato × raiz atribuída, por par.

---

## 6. Fase 4 — Trajetória Cognitiva

### Problema

O aluno vê um estado. Não vê uma mudança. E mudança é a única evidência de que
o produto funcionou.

### O que construir

Uma linha do tempo por habilidade, em linguagem que não expõe a ontologia:

```
Interpretar gráficos
  12/08  erro recorrente
  14/08  intervenção
  15/08  treino específico
  18/08  desempenho estabilizado
  22/08  aplicou em contexto novo
```

Para o aluno: *"Você tinha dificuldade com isto. Trabalhamos. Agora você aplica
em situações diferentes."*

### Mecanismo

Derivar isso varrendo `behavior` é proibido (§1.2). A trajetória é um **log
compacto e limitado**, escrito no mesmo bloco `revisao` da Fase 1, com um
registro por *marco* — não por resposta:

```
marcos: [{tipo: "raiz"|"intervencao"|"reteste_ok"|"transferencia", ts}, ...]
```

Marcos são raros por definição, o que mantém o documento pequeno. Limite duro
por processo, descartando o mais antigo.

### Restrição — a mais delicada de todas

Esta é a tela que **narra causalidade** ("trabalhamos isso, e você melhorou").
É a afirmação mais forte que o produto faz sobre o aluno, e hoje ela se apoiaria
em anotação não revisada (§1.1).

Enquanto o perfil for provisório, a trajetória descreve **o que aconteceu**
("você errou isto, praticou aquilo, acertou depois") e não **por que**
("porque tratamos sua dificuldade em X"). A segunda formulação exige o portão
em `crenca`. Isso não é conservadorismo: é a diferença entre relatar e alegar.

### Critérios de aceite

- Montar a trajetória custa 1 leitura.
- O log é limitado e não cresce sem teto.
- Nenhum `MEC-*` e nenhum ID de ontologia aparece na tela (§4.2).
- Com perfil provisório, a tela não afirma nexo causal. Teste de contrato.

---

## 7. Fase 5 — Sapiens Lab, como instrumento interno

**Recomendação: não construir como funcionalidade do aluno.** Três razões:

1. **Mecanicamente, já é a Fase 2.** "Hipótese → teste → resultado → próximo
   teste" é gatilho → reteste → resultado → reagendamento, com vocabulário de
   laboratório por cima.
2. **A oferta de itens não sustenta.** Cinco situações variadas por hipótese,
   por aluno, sem repetir item — o relatório da Fase 0 provavelmente mostra que
   o acervo não tem isso para a maioria dos processos. Repetir item transforma
   o experimento em teste de memória.
3. **"Padrão confirmado" em 5 itens viola R-3.** Cinco observações não
   confirmam nada, e imprimir "confirmado" para o aluno é exatamente a
   determinização de causa que o motor foi construído para não fazer.

### O que fazer em vez disso

Construir o Lab como **instrumento de investigação da equipe**, que é a função
que ele de fato tem. Alvo: não o aluno, mas o **par (erro, processo) do
catálogo**, agregado sobre todos os alunos.

- Hipótese: *"o par ERR-08 × PROC-12 está mal anotado — os alunos que marcam
  esse distrator relatam outra coisa"*.
- Evidência: agregação sobre traços + autorrelatos da Fase 3.
- Resultado: entra na fila de revisão humana da Fase 0.

Isso reposiciona o Lab de "a camada mais experimental" para **o motor que
destrava o portão de crença** — que é o gargalo real do produto inteiro. E
respeita R-7: o Lab **propõe** revisão; nunca altera a ontologia sozinho.

---

## 8. O ciclo, montado

```
                 RESPOSTA
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
 ERROR TRACE   AGREGADO INCR.   MICRODIAGNÓSTICO
  (existe)       (Fase 1)          (Fase 3)
      │              │              │
      └──────┬───────┘              │
             ▼                      │
      ESTADO DE REVISÃO             │
        (1 leitura)                 │
             │                      │
      ┌──────┴──────┐               │
      ▼             ▼               │
 FILA DIÁRIA   GATILHO              │
   (Fase 1)    (Fase 2)             │
      └──────┬──────┘               │
             ▼                      │
        INTERVENÇÃO                 │
    (intervencoes.montar,           │
        já existe)                  │
             ▼                      │
          RETESTE                   │
             ▼                      │
        TRAJETÓRIA ◄────────────────┘
         (Fase 4)                   │
                                    ▼
                            SAPIENS LAB (interno)
                                    │
                                    ▼
                            REVISÃO HUMANA (Fase 0)
                                    │
                                    ▼
                          PORTÃO DE CRENÇA ABRE
                                    │
                    └──── deixa de ser provisório ────┘
```

O laço externo é o que importa: o autorrelato do aluno alimenta a revisão
humana, a revisão humana abre o portão, e o portão aberto é o que autoriza o
produto a afirmar causalidade em vez de hipótese.

---

## 9. Não-objetivos

- Não alterar a ontologia automaticamente (R-7).
- Não introduzir LLM nas Fases 1, 2 e 4. O motor é gratuito, e continua.
- Não reescrever `motor_cognitivo`, `intervencoes` ou `portao_crenca`.
- Não expor IDs de catálogo (`ERR-*`, `PROC-*`, `MEC-*`) ao aluno.
- Não substituir `/plan/:analysisId`; o histórico do aluno não pode quebrar.

## 10. Riscos conhecidos

| Risco | Consequência | Mitigação |
|---|---|---|
| Documento `students/{uid}` inflando | `agregado.item_ids_respondidos` já é `ArrayUnion` sem teto; +5 blocos aproxima o limite de 1 MB | limitar `raizes_recentes` e `marcos`; medir o documento antes da Fase 1 |
| Oferta de itens insuficiente | reteste vira teste de memória; fila repete questões | relatório da Fase 0 é bloqueante |
| Portão fica desligado indefinidamente | cinco superfícies afirmando causalidade sobre anotação não revisada | Fase 0 antes da Fase 1; rótulo provisório é requisito, não copy |
| Gatilho ruidoso | Professor Invisível vira pop-up e é ignorado | uma intervenção por vez, cooldown por par, dispensa conta como sinal |
| Autorrelato tratado como causa | R-1/R-3 violadas; diagnóstico degrada em silêncio | produtor separado, teste travando que não altera `peso_raiz` |

## 11. Ordem de execução

| Fase | Entrega | Bloqueia |
|---|---|---|
| **0** | revisão humana + relatório de oferta | tudo |
| **1** | estado de revisão + fila diária | 2, 4 |
| **2** | gatilho sobre `intervencoes.montar` | — |
| **3** | microdiagnóstico + relatório de concordância | 5 |
| **4** | trajetória sobre os marcos da Fase 1 | — |
| **5** | Lab interno alimentando a Fase 0 | — |

Fases 1 e 2 dividem o mesmo estado e podem ser feitas juntas. A Fase 3 é
independente das outras e pode correr em paralelo. A Fase 4 é a única
puramente de interface.

## 12. Hipótese a validar

> Se o Sapiens já identifica padrões no comportamento observável do estudante,
> o próximo salto não é gerar mais conteúdo, é transformar esses padrões em
> decisões adaptativas.

O teste dessa hipótese não é a fila existir. É: **o reteste agendado tem taxa
de acerto maior que a resposta original, e a diferença sobrevive à
transferência de contexto.** Se não sobreviver, o ciclo está ensinando o item,
não a habilidade — e a Fase 1 precisa ser reprojetada antes de qualquer outra.

Esse número deve ser instrumentado junto com a Fase 1, não depois.
