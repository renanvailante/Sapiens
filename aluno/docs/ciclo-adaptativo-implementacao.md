# Ciclo adaptativo — registro de implementação

**Data:** 2026-09-09. **Alvo:** app `aluno`. Companheiro de
[`proposta-ciclo-adaptativo.md`](./proposta-ciclo-adaptativo.md), que continua
sendo a decisão; este é o registro da obra.

O laço fechou:

```
observar → interpretar → intervir → reter → retestar → estabilizar → transferir
```

---

## O que existe agora

| Fase | Entrega | Onde |
|---|---|---|
| 0 | Relatório de oferta + revisão humana do elo raiz | `curadoria.py`, `curadoria_routes.py`, `/admin/curadoria` |
| 1 | Estado de revisão + fila diária | `revisao_espacada.py`, `revisao_service.py`, `/revisoes` |
| 2 | Professor Invisível (gatilho sobre `intervencoes.montar`) | `revisao_espacada.avaliar_gatilho`, `ProfessorInvisivel.jsx` |
| 3 | Microdiagnóstico + relatório de concordância | `microdiagnostico.py`, `Microdiagnostico.jsx` |
| 4 | Trajetória sobre os marcos da Fase 1 | `revisao_service.trajetoria`, `Trajetoria.jsx` |
| 5 | Sapiens Lab, interno, alimentando a Fase 0 | `sapiens_lab.py`, aba "Sapiens Lab" |

Nada de `motor_cognitivo`, `intervencoes` ou `portao_crenca` foi reescrito. Os
três foram estendidos por fora, e há teste travando que os nomes públicos deles
continuam existindo (`test_ciclo_adaptativo.py::TestNaoObjetivos`).

---

## Onde o desenho final divergiu da proposta

Cinco divergências, todas deliberadas. Cada uma existe porque seguir o
documento à risca teria violado uma das restrições do próprio documento.

### 1. O bloco `revisao` é materializado, não reconstruído

**A proposta** descrevia o agendamento como "uma função pura sobre esse bloco".
Ela é — `revisao_espacada` não faz I/O nenhum. O que mudou é **quando** ela
roda: no caminho da escrita, com o bloco anterior em mãos.

A alternativa considerada era escrita cega (`Increment`/`ArrayUnion`, zero
leituras) derivando tudo na leitura. Foi descartada: derivar reteste e
rotação de janela exige guardar a série de respostas por processo, e uma série
não tem teto. O risco número 1 do §10 é o documento `students/{uid}` inflar até
o limite de 1 MB — e um documento estourado não degrada, para de aceitar
escrita. O bloco materializado tem teto declarado em cada lista (`_MAX_RAIZES`,
`_MAX_MARCOS`, `_MAX_CONTEXTOS`, `_MAX_PROCESSOS`), e há teste para cada um.

**Custo real:** 1 leitura + 1 escrita por resposta, ambas O(1) — mais uma
memória de processo que faz uma sessão de prova inteira custar **uma** leitura
só (`revisao_service._MEMO`, mesma forma do `_HISTORICO_MEMO` do motor). O
critério de aceite da Fase 2 continua valendo literalmente: o gatilho roda
sobre o bloco que a atualização acabou de produzir e **não custa nenhuma
leitura adicional** — `test_custo_firestore.py::TestCustoDaRevisao` compara o
caminho com e sem gatilho e exige o mesmo número de leituras.

### 2. "Janelas distintas" virou "dias distintos"

Para a recorrência (Fase 1 e gatilho da Fase 2), o critério implementado é
`>= MIN_TRACOS_RAIZ ocorrências do mesmo par em >= 2 dias distintos`.

Duas marcações do mesmo distrator na mesma sessão, cinco minutos uma da outra,
são um lapso — não um padrão, e padrão é o que autoriza interromper o aluno.
Exigir o retorno noutro dia separa as duas coisas com o dado que existe, sem
depender de onde caiu a fronteira de uma janela.

### 3. As janelas são contadas em respostas, não em dias

`JANELA_TAMANHO = 8` respostas ao mesmo processo. A comparação entre janelas só
significa alguma coisa com denominadores parecidos: um aluno que responde 30
questões numa terça e 2 na quarta não "deteriorou" na quarta.

### 4. A Fase 3 não inventa taxonomia de relato

A proposta pedia "relatório de concordância autorrelato × raiz atribuída". Mapear
cada `ERR-*` a uma classe de relato ("conteúdo", "interpretação", "execução")
seria texto autoral produzindo vínculo causal — o mesmo modo de falha que fez
`feedback_templates` divergir do catálogo em 2026-08-21.

O que foi implementado: a distribuição bruta por par, mais **um** sinal
declarado — a fração de "chutei sem ideia", que contradiz *qualquer* cadeia
causal, porque descreve um raciocínio que o aluno não relata ter feito. Um par
com 9 de 12 relatos de chute entra na fila de revisão humana. Nenhuma outra
opção é lida como confirmação de nada.

### 5. O Professor Invisível mostra a prévia, não o plano completo

`intervencoes.montar()` precisa dos traços do aluno, e obtê-los é O(eventos).
Interromper alguém no meio de uma prova não pode custar uma varredura de
histórico.

Então a interrupção carrega `intervencoes.previa(erro_id)` — o enquadramento
autoral da intervenção **catalogada** do erro raiz, custo zero, sem IA — e o
plano completo (ações escritas para os itens que ELE errou, resoluções,
prática dirigida) continua onde já estava: um clique adiante, em
`/cognitive-profile`, que paga a varredura uma vez e memoriza.

---

## As restrições do §1, e como cada uma é sustentada

**§1.1 — o portão está aberto, tudo é provisório.** `revisao_service.raiz_do_evento`
espelha `_particionar_pelo_portao`: com o portão em `crenca`, item não revisado
não registra raiz nem agenda reteste (agendar É mover o estado do aluno); com o
portão `desligado`, a raiz entra marcada `provisorio`, e o rótulo atravessa até
a fila, a intervenção e a trajetória. A tela da Fase 4 é a mais sensível e tem
contrato próprio: `nexo_causal: false` obriga a narrativa descritiva ("você
errou isto, praticou, acertou depois") em vez da causal ("trabalhamos sua
dificuldade em X"). Testado em `TestTrajetoriaNaoAlega`.

**§1.2 — nada O(eventos) por requisição.** Fila: 1 leitura. Trajetória: 1
leitura. Resposta: 1 leitura + 1 escrita. Lab: O(alunos), admin. Travado em
`test_custo_firestore.py::TestCustoDaRevisao`.

**§1.3 — as regras do Error Trace.** R-1 e a validação de cadeia continuam
onde sempre estiveram (`motor_cognitivo._validar_cadeia`), chamadas sem cópia
nem variante. R-3: nada imprime "confirmado" — o Lab entrega fila de leitura
humana, e o mínimo de amostra dele é maior que o do aluno, porque afirmar algo
sobre a ANOTAÇÃO exige mais evidência do que apontar onde um aluno olha
primeiro. §1.1 (manifestação ≠ causa): só o elo `ordem: 1` agenda, com teste.
§4.2: `MEC-*` não aparece em nenhum dos sete módulos novos — teste varre o
código sem docstrings.

**§1.4 — medida é gratuita.** Nenhum dos módulos novos importa `ai_service` nem
chama `deduct_sparks`. Teste parametrizado.

---

## §12 — a hipótese, instrumentada junto e não depois

`revisao_espacada.instrumentacao()` devolve, por aluno:

* `retestes.taxa` — acerto nos retestes agendados;
* `transferencia.taxa` — acerto do mesmo processo em contexto que **não** é o
  da raiz.

O segundo é o que decide a hipótese. Se a diferença não sobreviver à troca de
contexto, o ciclo está ensinando o item e não a habilidade, e a Fase 1 precisa
ser reprojetada antes de qualquer outra. Taxa `null` quando não há amostra —
"ainda não medimos" e "zero por cento" são coisas diferentes.

O aluno vê os dois números em `/revisoes`, com a frase que explica por que o
segundo importa mais. O agregado da base sai pelo Lab.

---

## O que ainda está bloqueado (e é o próximo passo real)

A Fase 0 está **construída**, não **executada**. Enquanto ninguém abrir
`/admin/curadoria` e confirmar elos raiz, item a item:

* o corpus continua sem revisão humana;
* `PORTAO_CRENCA_MODO` continua em `desligado`;
* todo perfil sai provisório e as cinco superfícies novas só levantam hipótese.

E antes disso: **rodar o relatório de oferta**. Ele é bloqueante por decisão da
proposta — nenhum processo cuja oferta ele reprove deve entrar em escopo de
fase, porque reteste sobre acervo raso mede memória do item, não estabilização
da habilidade. O relatório está em `/admin/curadoria` → aba "Oferta de itens",
e nunca foi rodado contra o acervo real.
