---
tags: [arquitetura, redacao, llm]
atualizado: 2026-09-18
---

# Corretor de redação — local primeiro, LLM por exceção

`aluno/backend/redacao/` + quatro componentes transversais no topo de
`aluno/backend/` (`decision_gate.py`, `llm_escalation.py`, `llm_cache.py`,
`llm_telemetry.py`), feitos para reúso por outras features.

## O desenho, e por que ele é assim

O primeiro rascunho tinha **uma** chamada de LLM decidindo tudo, com o Decision
Gate acoplado ao formato da resposta. O dono rejeitou explicitamente e exigiu cinco
coisas — elas continuam sendo o contrato:

1. **LLM nunca é obrigatório por competência.** Tenta local/determinístico/
   heurístico primeiro, escala só o que ficar semanticamente indeterminado.
2. **Detecção objetiva separada de interpretação semântica** — nenhuma função
   concentrando todos os gatilhos.
3. **O Decision Gate é totalmente independente de LLM**, usando evidência
   observável / concordância / conflito / margem — **nunca** confiança
   auto-relatada. `decision_gate.py` literalmente não importa nada de Gemini.
4. **Nenhum score artificial de confiança** — só os 4 estados operacionais
   (`DETERMINADO` / `AMBIGUO` / `CONFLITANTE` / `INSUFICIENTE`) até existir
   calibração empírica real.
5. **Nenhuma chamada só para confirmar** algo já determinado. Toda chamada resolve
   um subproblema nomeado e é auditável.

## Como roda

`avaliador_local.py` produz evidência mecânica (`elegibilidade.py`) + heurística
(`heuristicas.py`) para **19 itens** (11 gatilhos de zero-redação-inteira + 1
localizado `DH-ZERO-01` + 5 competências + `TEMA-02` tangenciamento e `COPIA-02`
cópia) e passa por `decision_gate.classificar()` — Python puro, testável só com
evidência sintética.

Só o que sai **não-`DETERMINADO`** vai para `escalonamento_redacao.py`: um lote em
**uma** chamada Gemini a `thinking_level=LOW`, citando apenas o trecho de regra
relevante por item (**nunca o canon inteiro**), com `judge()` estrutural (nunca
semântico) decidindo quais itens precisam de uma 2ª chamada `MEDIUM`. Teto de 2
tentativas por item — padrão portado de `pipeline/backend/cognitive_engine.py` via
`llm_escalation.run_adaptive`.

A resposta do LLM **não carrega nem usa campo de confiança**: vira outra
`Evidencia(metodo="llm")` e volta pelo **mesmo** `decision_gate.classificar()`.
Local e LLM concordam → confirmado. Discordam → `CONFLITANTE`, marcado para revisão
humana, **nunca resolvido em silêncio para a leitura mais severa**.

Numa redação limpa e no tema, 15–17 dos 19 itens resolvem 100% localmente.

## Em produção o LLM está DESLIGADO

- `POST /api/redacao` — **120 Sparks**, nota das 5 competências + geral, **zero
  chamada de API paga**. O escalonamento virou opt-in (`REDACAO_ESCALONAR_LLM`,
  desligado): `redacao/tema_local.py` decompõe a frase temática localmente e
  resolve os três itens (ZERO-01, TEMA-02, COMP-II) que antes iam ao modelo em
  **toda** submissão porque `tema_elementos_obrigatorios` nunca era preenchido por
  tela nenhuma.
- `POST /api/redacao/{id}/feedback` — **90 Sparks**, 1 chamada MINIMAL, a única API
  paga. Fica salva por `redacao_id`; reler é grátis para sempre.

Prioridade declarada pelo dono: **funcionar gastando o mínimo de API paga.**

## A soma da nota mudou de semântica — não "restaure o rigor"

Era `nivel if confirmado else 0`, o que transformava competência `AMBIGUA` em zero
(redação boa saía 560/1000). Hoje soma o **melhor candidato disponível**; o único
zero respeitado é zero **DECIDIDO**. A incerteza vai em `nota_pontos_estimados`.

> Se alguém for "restaurar o rigor" aqui, é isto que quebra de novo.

## Idempotência

`redacao_cobrancas` (`_id = user:idempotency_key` do cliente) e `redacao_feedbacks`
(`_id = redacao_id`). Reivindica → cobra → entrega; falha depois do débito
reembolsa **e** libera a chave; processo morto entre débito e entrega é retomado
sem cobrar de novo (campo `cobrado`).

## O bug que vale re-checar se mexerem no escalonamento

Uma submissão **em branco** ainda disparava 2 chamadas de LLM: `service.py`
computava a lista de escalonamento inteira **antes** de checar se um gatilho
mecânico (`ZERO-03`, texto vazio) já tinha curto-circuitado a redação.
`_ja_anulada_localmente()` é a guarda. **A propriedade
curto-circuito-antes-do-escalonamento é fácil de perder em silêncio.**

## Não construído, de propósito

Detecção de cópia por textos motivadores só se o chamador os fornecer — senão
`COPIA-02` fica `INSUFICIENTE`, nunca adivinhado. As ambiguidades declaradas pelo
próprio canon (AMB-01, AMB-07…) têm convenção de engenharia documentada inline em
`redacao/canon.py` e `redacao/elegibilidade.py`, cada uma citando o id AMB-xx.

O OCR de foto manuscrita existe (`DIGITALIZACAO_COST = 25`, `ai_service.ocr_redacao`,
1 chamada de visão) e **reembolsa em todo caminho que não entrega texto**,
inclusive foto ilegível.

---
Relacionado: [[canon-pedagogico]] · [[economia-de-sparks]] · [[incidentes]] · [[mentis]]
