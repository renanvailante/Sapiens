---
tags: [operacao, incidente, historico]
atualizado: 2026-09-18
---

# Incidentes — causa raiz e o que ficou

Quatro apagões reais. Cada um deixou uma regra; a regra vale mais que a história.

## 2026-09-04 · A cota do Firestore derrubou o app inteiro

**Sintoma:** responder questão, Sparks, diagnóstico e Mentis — tudo quebrado.
`429 Quota exceeded` subindo por `ensure_student_profile` e `ler_agregado`, que
estão no caminho de quase toda rota autenticada.

**Não foram os alunos.** Era `_auto_sync_loop` (`server.py`) chamando
`_read_all_firestore("itens")`, que lia o acervo **inteiro** sem detectar mudança:
268 docs × 288 ciclos/dia = **77.184 leituras/dia = 154% da cota gratuita**, antes
de qualquer aluno abrir o site. O comentário no `fly.toml` afirmava que 300s era
"raro o bastante para não pressionar a cota" — a conta nunca tinha sido feita.

**Correção:** `FIRESTORE_AUTO_SYNC_SECONDS` 300 → 21600 (6h), 1.072 leituras/dia,
com a conta registrada no `fly.toml`. O acervo passa semanas sem mudar, e existe
`POST /admin/firestore/sync` para publicar na hora.

**O que ficou:** [[custo-de-leitura]] inteiro, e o hábito de sondar com `limit(1)`
antes de varrer.

> **Quando o app "parar inteiro" sem erro de deploy**, olhe
> `flyctl logs -a sapiens-aluno` por `ResourceExhausted` **antes** de suspeitar de
> código novo. A cota vira à meia-noite do Pacífico (~07:00 UTC, 04:00 de Brasília).

## 2026-09-07 · Pix pago, Sparks nunca creditados

Um Pix real de R$1,00 foi pago, o dinheiro entrou no Mercado Pago e o crédito nunca
saiu: a notificação não chegou e **nada no sistema perguntava de novo**. O
pagamento ficou `credited: false` para sempre, sem ninguém saber.

**O que ficou:** o laço de reconciliação de 60s, e a regra de que o webhook é só o
caminho rápido. Ver [[pagamentos]].

## 2026-09-06 · O corretor de redação nunca tinha funcionado em produção

Desde que foi construído. Ninguém sabia porque `/ready` não checava o canon e nada
logava. Duas causas, **as duas de empacotamento, nenhuma de lógica**:

- `13 enem_regras_computaveis.json` não era copiado pelo Dockerfile, e
  `canon._caminho_canon()` fazia `parents[3]` num caminho com três ancestrais →
  `IndexError` cru → HTTP 500 em toda submissão;
- `pyspellchecker` não estava em `requirements.txt` (a memória antiga afirmava que
  estava — não estava): o import falhava, o `except` engolia, e a Competência I
  ficava sem candidato.

**O que ficou:** `tests/test_prontidao_producao.py` e a regra do `COPY` em
[[deploy]].

## 2026-09-06/07 · Dois deploys seguidos quebraram o site inteiro

Build feito de dentro de um worktree sem o `.env`. Ver a armadilha 3 em [[deploy]].

## Padrão comum aos quatro

Nenhum deles apareceu em teste, em revisão de código ou na saída de um comando.
Três apareceram como **o produto parando** e um como **silêncio** (o pagamento
preso). O que os teria pego: fazer a conta antes (custo de laço de background),
provar no alvo (deploy), e ter um endpoint de diagnóstico
(`GET /api/admin/sparks/pendentes`).

---
Relacionado: [[custo-de-leitura]] · [[pagamentos]] · [[deploy]] · [[redacao]]
