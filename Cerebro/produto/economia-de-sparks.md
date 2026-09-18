---
tags: [produto, preco, aluno, fonte-unica]
atualizado: 2026-09-18
---

# Economia de Sparks

Spark é a moeda do app aluno. Esta é a **única tabela de preços do Cerebro** —
qualquer outro nó que precise citar preço linka para cá em vez de repetir o
número. Preço repetido em dois lugares diverge em uma semana.

> [!warning] O código é a fonte da verdade, não esta tabela
> Toda linha abaixo é uma constante de módulo. Antes de **afirmar** um preço ao
> usuário, confira a constante. Esta tabela existe para você saber **onde
> procurar** e **por que aquele número é aquele**, não para ser citada de cor.
>
> ```bash
> grep -rnE "^[A-Z_]*(COST|CUSTO)[A-Z_]*\s*=" aluno/backend/*.py
> ```

## O que custa (verificado no código em 2026-09-18)

| Sparks | O quê | Onde mora |
|---:|---|---|
| 350 | Curso (uma vez, acesso vitalício) | `cursos.CURSO_CUSTO_SPARKS` |
| 200 | E-book | `cursos.EBOOK_CUSTO_SPARKS` |
| 200 | Aula ao vivo — **por edição** | `cursos.LIVE_CUSTO_SPARKS` |
| 120 | Nota da redação (5 competências + geral) | `redacao_routes.CORRECAO_COST` |
| 90 | Devolutiva da Mentis sobre a redação | `redacao_routes.FEEDBACK_COST` |
| 70 | Abrir sessão de chat da Mentis (24h) | `mentis_routes.SESSAO_COST` |
| 50 | Entrar na fila da mentoria (uma vez) | `mentoria_routes.ENTRADA_COST` |
| 50 | Mentis reescrever os blocos da semana | `cronograma_routes.MENTIS_COST` |
| 50 | Congelador de ofensiva (teto 2) | `engajamento.CUSTO_CONGELADOR` |
| 40 | Diagnóstico de simulado | `exam_routes.DIAGNOSTICO_SIMULADO_COST` |
| 30 | Destacar dúvida no mural | `comunidade.CUSTO_DESTAQUE` |
| 25 | OCR da foto de uma redação manuscrita | `redacao_routes.DIGITALIZACAO_COST` |
| 25 | OCR do cartão-resposta | `exam_routes.OCR_CARTAO_COST` |
| 20 | Gerar/atualizar o mapa de habilidades | `skills_map_routes.SKILLS_MAP_COST` |
| 20 | Corrigir uma dissertativa de curso | `mentis_routes.DISSERTATIVA_COST` |
| 15 | Resumo da sessão | `firestore_routes.RESUMO_SESSAO_COST` |
| 10 | Cada mensagem no chat da Mentis | `mentis_routes.MENSAGEM_COST` |
| 10 | "Explicar melhor" um trecho de curso/e-book | `mentis_routes.EXPLICACAO_CONTEUDO_COST` |
| 10 | Intervenção da Mentis num card de erro | `mentis_routes.INTERVENCAO_COST` |
| 10 | Explicação de conceito no treino | `treino_routes.CONCEITO_EXPLICACAO_COST` |
| 10 | Guardar um trecho na fila de revisões | `lembretes_routes.LEMBRETE_COST` |
| 10 | Remontar a semana | `cronograma_routes.REMONTAGEM_COST` |
| 10 | Ditar compromissos em texto solto | `cronograma_routes.TEXTO_COST` |
| 7 | "Saiba mais" numa questão | `mentis_routes.EXPLICACAO_COST` |
| 5 | Questão nova gerada por IA | `treino_habilidades.CUSTO_POR_QUESTAO_NOVA` |

## O que é de graça, e por quê

Gratuidade aqui é decisão de produto, não economia esquecida. Não "conserte"
cobrando:

- **Montar a semana** — o horário e a prioridade são determinísticos
  ([[motor-cognitivo]]); só o texto é da Mentis. Funciona com o Gemini fora do ar.
- **Navegar** — os chips de destino da Mentis (`MentisAtalhos`) são grátis mesmo
  com a sessão fechada. Navegar não pode custar Spark.
- **Ler diagnóstico, perfil e painel** (`/diagnostico`, `/perfil/painel`,
  `/prioridades`) — é leitura e agregação, não geração.
- **Reclamar** (`/sugestoes`) — cobrar para reclamar cala quem tem menos saldo, e
  remunerar reclamação vira ruído. Não confundir com a bandeira de questão
  (`question_reports_routes`), que **paga** 5 Sparks quando aprovada.
- **Corrigir o pedido da mentoria** — cobrar por correção faria o aluno preferir
  deixar o telefone errado, que é o dado pelo qual a fila existe.
- **Reler** qualquer coisa já paga (devolutiva de redação, correção de
  dissertativa com o mesmo texto).

## O que o aluno GANHA

- **+1 Spark por exercício de curso acertado**, uma vez por exercício, e **só no
  acerto de primeira**. A regra não é anunciada — decisão do dono ("ele descobre
  jogando"). É defensável porque aqui Spark se *ganha*; nada que o aluno *pague*
  está escondido. Com tentativa livre e 4 alternativas, pagar o acerto eventual
  seria pagar persistência de clique.
- Sparks por rodada de prática concluída (`grant_question_sparks`).
- 5 Sparks por bandeira de questão aprovada.

## As quatro regras que sustentam a economia

1. **Preço nunca é escrito no JavaScript.** O frontend lê de `GET /sparks/packages`
   / `GET /cursos`, que leem as constantes do backend. Quem decide parcelamento é
   o Mercado Pago. Um número digitado no JSX é uma promessa de preço publicada sem
   decisão de produto.
2. **Preço nunca entra em arquivo de conteúdo.** `cursos_conteudo.py` derruba o
   arquivo se achar chave `custo`/`preco`/`sparks`/`desconto` em qualquer nível —
   um lote gerado por IA inventaria um preço. Ver [[cursos-conteudo]].
3. **Uma ação, uma cobrança.** `_custo_da_montagem` do cronograma é a única função
   que decide preço e nunca soma dois.
4. **Cobrança é sempre débito → try → reembolso**, e idempotente por chave
   determinística. Ver [[pagamentos]] para o padrão claim-then-debit.

## Cache hit ainda cobra

`/mentis/explicacao` (7) e "explicar melhor" (10) cobram mesmo quando a resposta
sai do cache. É decisão de produto deliberada, não bug: o cache é economia nossa,
não desconto do aluno. Não "corrija" isso.

## Direitos dispensam cobrança

Quem tem `mentis_ilimitada` não paga **nenhuma** das quatro cobranças da Mentis —
o atalho vive em `mentis_routes._cobrar`, **antes** do débito. "Ilimitada" tem de
significar que o saldo nem é tocado, não um desconto aplicado depois. Ver
[[catalogo]].

---
Relacionado: [[catalogo]] · [[pagamentos]] · [[mentis]] · [[inviolaveis]]
