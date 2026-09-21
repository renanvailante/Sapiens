---
tags: [arquitetura, dados, firestore, mongo]
atualizado: 2026-09-18
---

# Onde mora o dado, e quem é a fonte da verdade

Três bancos, e confundi-los custa trabalho perdido.

## O acervo de questões: Firestore manda

O **Firestore `itens`** (projeto `sapiens-dataset`) é a fonte da verdade do app
aluno — **não o Mongo**. `_auto_sync_loop` faz `questoes_public.delete_many({})` e
reconstrói tudo a partir dele.

> [!warning] Correção feita só no Mongo é destruída no próximo ciclo de sync.

O Firestore é **compartilhado entre local e produção**. O Mongo local
(`127.0.0.1`) **não é** o Mongo de produção (Atlas, via Fly).

## A divisão de trabalho

| Vive no **Firestore** | Vive no **Mongo** |
|---|---|
| `itens` (acervo) | engajamento, liga, missões |
| `students/{uid}` — saldo, direitos, agregado, flags | mural / comunidade |
| `students/{uid}/behavior` — os eventos | cronograma, onboarding |
| idempotência de crédito de Sparks | progresso e eventos de curso |
| | redações, avaliações, caches de LLM |
| | pagamentos, cupons, indicações |
| | influencers, comissões, eventos de growth, campanhas |
| | caches derivados dos agregados |

O critério é [[custo-de-leitura]]: o Firestore tem cota e o Mongo não. **O
Firestore só é tocado para pagar Sparks e para ler o agregado.**

## O contrato de comportamento (BEH-1.1)

É governado e **não foi estendido**. Resposta de curso escreve no **mesmo** contrato
canônico do ENEM (`cursos_comportamento.py`): `item_id` =
`CURSO:{curso}:{estacao}:{bloco}`, `contexto.tipo` = `curso`, `prova_id` =
`{curso}:{estacao}`. O que é mais rico (nível, conceitos, tentativa) mora em
`cursos_eventos`, fora do contrato.

O `item_hash` é calculado sobre o **bloco sanitizado**. Preço não entra em
`sanitizar_bloco` — mudar um preço reescreveria o histórico de todo mundo. Ele vai
em `_para_a_tela`, só na rota que abre a estação.

## LGPD

`dados_pessoais.COLECOES_POR_USUARIO` é o inventário: toda coleção por usuário
entra lá e sai com a conta. **Há teste de inventário que pega quem esquecer.** Ver
[[inviolaveis]].

## Idempotência — os três padrões da casa

1. **Claim-then-debit.** Grava um documento de `_id` determinístico **antes** de
   debitar e desfaz a reivindicação se o débito falhar. Duplo clique nunca cobra
   duas vezes. Usado em cursos (`"{uid}:{curso_id}"`), live (`"{uid}:{edicao}"`) e
   redação (`redacao_cobrancas`, `_id = user:idempotency_key`).
2. **A digital do conteúdo é a chave.** `sha256` do texto normalizado:
   `lembretes_revisao` (`{uid}:{sha256(texto + rota)}`) e `cursos_dissertativas`.
   Cobra uma vez por trecho **para sempre** — cobre duplo toque, retry, F5 e o
   aluno que volta semanas depois, sem precisar de `idempotency_key`. Na rota do
   lembrete a rota entra **sem query nem hash**, senão a mesma tela por outro
   caminho viraria linha nova paga.
3. **Reivindicação atômica** com `find_one_and_update`, não contagem.
   `indicacoes` carimba `premio_mp_payment_id` com filtro
   `{"$in": [None, mp_payment_id]}` — vazio (primeira compra) ou este mesmo
   pagamento (reenvio de webhook). **Contar compras anteriores é ler-e-escrever, e
   dois webhooks juntos leem o mesmo zero.**
   `influencer_comissoes` ([[afiliados]]) usa a forma mais simples do mesmo
   princípio: `_id = mp_payment_id` direto no `insert_one`. Não precisa de
   `find_one_and_update` porque a comissão não é "uma vez na primeira
   compra", é "uma vez por pagamento" — a chave primária já garante isso, e
   um reenvio de webhook esbarra em `DuplicateKeyError` em vez de duplicar.

Do lado do cliente: `lib/idempotencia.js` (`criarPortao`). A lição que motivou o
arquivo — **a chave sozinha não resolve o toque duplo**: um `novaChave()` dentro do
`onClick` gera duas chaves e o servidor, corretamente, cobra duas vezes. E
`setState` não serve de trava porque não é síncrono. A `ref` barra no mesmo
instante; a chave só troca em `concluir()`, para o retry pós-erro-de-rede ser o
mesmo pedido.

## Armadilhas de consulta já pagas

- **Campo que não existia antes de uma data.** A consulta da sala aberta do mural é
  `{"sala": {"$ne": "vip"}}` e **nunca** `== "geral"`: `$ne` casa com o documento em
  que o campo não existe. Com igualdade, o mural inteiro sumiria no dia do deploy,
  sem erro na tela. Mesma classe: `saldo_antes`/`promo_code` nascem vazios para o
  passado e a tela mostra "—".
- **Upsert precisa de `$setOnInsert` de identidade.** Sem isso, responder sem abrir
  a estação criava documento sem `uid`/`curso_id` e o mapa da trilha não o
  encontrava. E `blocos_vistos`/`respostas` **não nascem vazios**: o Mongo real
  recusa `$setOnInsert` + `$addToSet` no mesmo campo.
- **Não carimbe data junto de `$addToSet`** se você usa `modified_count` para
  decidir algo — ele seria 1 sempre, e o evento sairia a cada rolagem da tela.
- **`manifest.page_used` é 1-based**, os índices do PyMuPDF são 0-based. Medido:
  com `page_used`, 0/66 assets ficam contidos na região da questão; com
  `page_used - 1`, 34/66. Qualquer auditoria geométrica que ignore isso compara
  contra a página seguinte.

---
Relacionado: [[custo-de-leitura]] · [[pagamentos]] · [[pipeline-e-corpus]]
