---
tags: [arquitetura, custo, firestore, regra]
atualizado: 2026-09-18
---

# A disciplina de leitura do Firestore

> **Nenhuma requisição pode custar O(eventos do aluno) em leituras do Firestore.**

Regra nascida do apagão de 2026-09-04 ([[incidentes]]). Custo de leitura **não
aparece em teste nem em code review comum** — só aparece como apagão no fim da
tarde.

## O padrão da casa: invalidação por `total_respostas`

`firestore_service.ler_agregado` devolve `agregado.total_respostas` em **1 leitura**
e o número sobe a cada resposta. Respondeu algo novo → a chave muda → recalcula.
É a chave de cache de tudo que é caro.

## Onde isso está aplicado

- `annotation_service._agregado_com_cache` — cache no **Mongo** (que não tem cota)
  dos dois agregados caros, chaveado por `(escopo, uid, total_respostas,
  ontology_version)`, TTL 6h. Cobre `/diagnostico`, `/cognitive-profile`,
  `/skills-map` e a abertura de sessão da Mentis. Medido: 41ms → 1ms.
- `motor_cognitivo._HISTORICO_MEMO` — memória de processo para `_ler_historico`.
  Sem ela, `/motor/panorama` custava ~60.000 leituras num clique (200 alunos ×
  ~300 eventos). **Não existe segunda camada de cache aqui**, de propósito: um TTL
  na frente da memória por `total_respostas` só a deixaria velha.
- `firestore_service._PROVISIONADO_PROFILE` / `_BEHAVIOR` — `ensure_student_*` são
  checagens de existência monotônica; custavam 1 leitura por **requisição**.
- `fs.ler_saldo_e_direitos()` — saldo + direitos em uma leitura só do
  `students/{uid}`, não duas.
- `fs.resumo_dos_alunos()` — UMA varredura de `students`. Ela **não reconstrói
  agregado ausente**: `questoes_respondidas` vem `None` e a tela mostra "—", nunca
  "0".

## O truncamento silencioso

`list_students_with_behavior` usava `collection_group("behavior").limit(5000)`.
Além do custo, o `limit` **truncava em silêncio**: passando de 5.000 eventos
somados, alunos sumiam da lista e paravam de ter perfil recalculado, sem erro
nenhum. Passou a ler o agregado por aluno.

Mesmo defeito, mesma família: a fila de revisão também truncava em silêncio até
2026-09-12.

## O que mora no Mongo por causa da cota

Coisas que são, por natureza, leitura de O(alunos) várias vezes por dia — em
Firestore isso é a cota gratuita do dia num almoço:

- todo o estado de **engajamento** e o **mural** inteiro (`engajamento_service`,
  `comunidade`);
- o **cronograma** (`cronogramas`, `_id = user_id`, 1 `find_one` por leitura);
- o **onboarding** (`onboarding_perfil`);
- o **progresso e os eventos de curso** (`cursos_progresso`, `cursos_eventos`);
- os **caches derivados** de agregado.

**O Firestore só é tocado para pagar Sparks e para ler o agregado.**
`estado()` do engajamento custa 1 leitura de Firestore (um agregado que outras
telas já leem) + 3 consultas indexadas no Mongo.

## Coisas que parecem baratas e não são

- **Um laço de background é O(ciclos × coleção).** Foi o que derrubou o app.
  Faça a conta e escreva-a no `fly.toml`.
- **Uma leitura por abertura de painel** só para exibir anúncio já foi recusada: o
  Painel **não chama `/cursos`** para anunciar a live — `lib/live.js` recalcula a
  próxima quinta no navegador, de graça.
- **Ler dentro de uma transação.** `_conceder_sparks_atomico(registrar_saldo=True)`
  é opt-in justamente por isso: barato numa compra (poucas por aluno na vida),
  ruinoso em `grant_question_sparks`, que roda a cada questão respondida da
  plataforma.
- **Propagação entre processos.** `cursos_publicados.garantir_atual()` faz no
  máximo **uma** projeção `{_id, revisao}` por minuto por processo, na porta da
  estação e na vitrine. Nada por requisição.

## Como aplicar

Ao escrever qualquer leitura nova, **pergunte de que ordem ela é**. Se for
O(eventos) ou O(alunos × eventos), passe pelo cache. Endpoint novo que varre
coleção precisa de teto explícito (`/api/motor/panorama`: 1.500 padrão, 5.000 máx;
leitura de `cursos_eventos` pelo admin: teto de 20.000).

`tests/test_custo_firestore.py` existe **só** para travar essas ordens de grandeza.
Se um teste de lá quebrar, foi custo que voltou, não feature.

## Degradar, não falhar

Falha de leitura do Firestore não pode virar "aluno sem dados" nem, pior, presente:

- `_historico()` acrescenta `falha_de_leitura → indisponivel`;
- `ler_direitos(uid)` devolve tudo `False` numa falha — **na dúvida cobra-se o
  Spark**; o inverso daria de presente o produto mais caro do catálogo para a base
  inteira durante um incidente;
- a lista de permissões do admin degrada com campos nulos + aviso em vez de falhar
   — é ela que revoga um admin.

---
Relacionado: [[dados]] · [[incidentes]] · [[motor-cognitivo]]
