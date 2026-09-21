---
tags: [operacao, incidente, historico]
atualizado: 2026-09-21
---

# Incidentes — causa raiz e o que ficou

Cinco apagões reais. Cada um deixou uma regra; a regra vale mais que a história.

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

## 2026-09-21 · Nenhuma conta nova podia ser criada

**Sintoma:** "Não foi possível entrar." ao criar conta — pelos dois caminhos,
e-mail e Google. Chegou como relato de uma influencer, com print de story, e a
primeira leitura (rede da usuária, navegador do Instagram) estava **errada**.

**Causa:** o índice `users.referral_code` era `unique + sparse`, e o comentário
dizia que o esparso existia justamente para não tratar os `None` como
duplicata. **`sparse` pula só o campo AUSENTE** — presente valendo `null` é
indexado como qualquer valor. `User.model_dump()` grava `referral_code: None`
em toda conta nova, então o primeiro cadastro depois de o campo existir ficou
com o valor nulo e todos os seguintes morriam com `DuplicateKeyError` dentro de
`auth.signup`. Produção confirmou: 30 contas, 29 com o campo ausente, 1 com
`null`, nenhuma com código de verdade. Cura: `partialFilterExpression` por
`$type: "string"`.

**Duas coisas em volta fizeram a falha durar, e valem mais que a causa:**

> **`create_index` NUNCA redefine um índice que já existe.** Mudar as opções de
> um índice neste repo não conserta banco nenhum que já rodou — o Mongo recusa,
> e recusa de novo em todo boot. Pior: o conflito caía no ramo de "já existe sob
> outro nome" (mesmas chaves, mesmo `unique`) e era contado como SUCESSO.
> `criar_indices` agora derruba e recria quando o mesmo nome tem as mesmas
> chaves e opções diferentes.

> **Um 500 sem CORS é um erro que ninguém lê.** O handler de `Exception` é
> servido pelo `ServerErrorMiddleware`, a camada mais EXTERNA do Starlette —
> fora do `CORSMiddleware`. A resposta saía sem `Access-Control-Allow-Origin`,
> o navegador bloqueava, o axios levantava erro sem `response` e o `errMsg` do
> frontend caía no texto genérico. O servidor dizia qual era o incidente e
> ninguém do outro lado conseguia ler — foi o que transformou um 500 objetivo
> em "problema de rede da usuária" por horas.

**O que ficou:** `tests/test_indices.py` trava a declaração do índice e a
recriação sob o mesmo nome; `tests/test_erro_nao_tratado.py` trava o CORS do
500. E a regra de diagnóstico: **reproduza contra produção com `curl` antes de
teorizar sobre o cliente** — um `-i` mostrou o 500 e a ausência do cabeçalho em
uma chamada.

> O `fake_db` dos testes não tem índice nenhum. **Toda garantia que mora num
> índice único é invisível para a suíte** e só existe contra um Mongo de
> verdade — teste a DECLARAÇÃO quando não puder testar o efeito.

## Padrão comum aos cinco

Nenhum deles apareceu em teste, em revisão de código ou na saída de um comando.
Quatro apareceram como **o produto parando** e um como **silêncio** (o pagamento
preso). O que os teria pego: fazer a conta antes (custo de laço de background),
provar no alvo (deploy), e ter um endpoint de diagnóstico
(`GET /api/admin/sparks/pendentes`).

O de 2026-09-21 acrescenta um padrão próprio: os outros quatro foram
descobertos por quem opera o produto, e este chegou por um **usuário**, com uma
explicação plausível e errada embutida no relato. Nada no sistema avisou que
100% dos cadastros falhavam.

---
Relacionado: [[custo-de-leitura]] · [[pagamentos]] · [[deploy]] · [[redacao]]
