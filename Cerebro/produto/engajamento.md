---
tags: [produto, gamificacao, comunidade]
atualizado: 2026-10-09
---

# Engajamento, comunidade e conversão

Construído a pedido de "retenção, recorrência e conversão em Sparks":
`engajamento.py` (regras puras) + `engajamento_service.py` + `engajamento_routes.py`,
e `comunidade.py` + `comunidade_routes.py`. No frontend: `PainelDeProgresso` no topo
do Painel, `/comunidade`, `/liga`, `/admin/comunidade`.

## A decisão de arquitetura: tudo no Mongo

Todo o estado de engajamento e o mural inteiro vivem no **Mongo**, não no Firestore.
Uma liga semanal e um feed são, por natureza, leitura de O(alunos) várias vezes por
dia — em Firestore isso é a cota gratuita do dia num almoço. **O Firestore só é
tocado para pagar Sparks.** Ver [[custo-de-leitura]].

## A ofensiva deriva de `agregado.dias_ativos`

De propósito — **não** de um contador que o próprio motor incrementa. É o que
garante que sequência mede **estudo real** e não chamada de API.

O congelador (50 Sparks, teto 2) liga a corrente **sem contar como dia estudado**, e
só é consumido quando de fato salva a sequência.

## Sapiens Plus pela ofensiva

Decisão do dono em [[decisoes-do-dono]]. Como ela é cumprida, e por quê:

- **O Plus é um prazo, não um pacote.** `students/{uid}.plus_ate` (Firestore) e
  `firestore_service._aplicar_plus`, chamado dentro de `ler_direitos` e
  `ler_saldo_e_direitos`. Toda porta paga já passava por ali, então nenhuma rota
  precisou saber que o Plus existe — e ele **só liga**, nunca desliga: vencido o
  prazo, o que o aluno comprou continua, o que não comprou volta a ser cobrado.
  Não grave `True` nos campos do pacote para "dar Plus": isso viraria direito
  permanente e se misturaria com compra.
- **Fica sem a live, de propósito** (`sparks_store.DIREITOS_DO_PLUS`). Ler
  `GET /cursos` com `lives_inclusas` INSCREVE o aluno na edição da quinta — uma
  vaga com gente de verdade do outro lado, que sobreviveria às 48h.
- **Concedido na leitura de `/engajamento/me`**, o único ponto que já tem a
  ofensiva calculada. Guarda de uma vez em `engajamento_perfil.ja_premiado`
  (`plus:ofensiva:5`), a mesma lista de `chave_unica`; se o Firestore falhar, a
  chave sai e a próxima leitura tenta de novo — prêmio anunciado marcado como pago
  sem ter chegado seria a pior falha possível. Agregado indisponível não concede.
- **Uma vez por aluno.** 2 a cada 5 dias daria Plus a quem estuda todo dia em 40%
  do tempo, e a Mentis ilimitada é o que mais custa rodar. `MARCOS_PLUS` é tabela
  para que outro marco (30, 100 dias) seja uma linha.
- **48h a partir da concessão**, não "até o fim de amanhã": o "2 dias" da tela é o
  que o relógio entrega a qualquer hora em que o 5º dia vire.
- Congelador liga a corrente sem somar dia — **Sparks não compram o Plus**.

## A camada de comemoração (Duolingo)

Pedido de 2026-10-08: "inspire-se totalmente no Duolingo, com muito mais
animação". Peças em `components/celebracao/` e `lib/{som,confete,reacao,celebracao}.js`:
a tela da chama na primeira vez do dia em que o aluno estuda (uma vez por dia, por
aparelho), o presente abrindo no dia do Plus, o placar XP · precisão · tempo no
fim da série, o combo a partir de 3 seguidas, e o som sintetizado (Web Audio, zero
arquivo, mudo na tela de questão). **A regra que segura tudo: só se comemora
número que o servidor contou** — a mesma régua de `recompensaDaSerie`. A tela da
chama abre só com `estudou_hoje`; o XP do placar some sem a diferença real.

## A linha ética

Está no cabeçalho de `engajamento.py` e tem teste — ver [[inviolaveis]] para as
cinco regras. A régua ao mexer: *"isto seria verdade se o aluno visse o código?"*

**Conquistas ficaram só no `Dashboard.jsx`** (o backend teve as dele removidas) para
não existirem dois sistemas divergindo. **Conquista não paga Sparks nem XP** — quem
paga são as missões diárias; o detalhe não inventa recompensa.

## Os motivos para voltar são do próprio aluno

Desde 2026-09-28 os eventos do Hoje e as missões falam do que ESTE aluno fez,
não de metas genéricas (detalhes em [[padroes-de-tela]]):

- **Missões de prática levam ao padrão de erro.** "Responda 5 questões" conta
  resposta em qualquer tela; quando o motor aponta um padrão, o botão leva à
  prática dirigida dele (`destinoDaMissao`). Missão, alvo e prêmio não mudam —
  a linha ética continua intacta; muda o lugar onde as cinco questões rendem.
- **Microvitória real:** revisão acertada ou acerto em contexto novo, da
  trajetória.
- **Trechos guardados que voltaram** (revisão programada, ver [[mentis]]).
- **Conquista só no dia em que aparece.** O catálogo não guarda data, então
  "a última desbloqueada" era a mesma todo dia; `conquistasDoDia` lembra, por
  aparelho, o dia em que cada uma foi vista primeiro, e na primeira visita não
  anuncia nada (não há como saber o que é novo).

## XP

`engajamento.XP_POR_ACAO`, sempre com `chave_unica`. `estacao_concluida` = 50, uma
vez por estação. Exercício de curso paga por dificuldade, com guarda em `tentou:`
**e** `acertou:` — sem as duas, errar em laço fabricaria XP.

## Mural de dúvidas

Sala aberta + sala VIP (`?sala=vip`, um direito de pacote — ver [[catalogo]]).
Uma única implementação: voto, melhor resposta, moderação e exclusão por LGPD valem
nas duas.

> A consulta da sala aberta é `{"sala": {"$ne": "vip"}}` e **nunca** `== "geral"` —
> ver a armadilha do campo ausente em [[dados]].

## Indicação de amigo

Código pessoal por aluno; o indicador recebe metade dos Sparks na **primeira compra**
do indicado. Mecânica e garantias em [[pagamentos]].

## Venda personalizada da live

`lib/venda.js` — puro, sem requisição, com a **primeira suíte de testes de JS do
repositório** (`venda.test.js`, 16 testes). Pedido: *"quero que você venda muito,
tendo em vista o comportamento de cada um dos alunos"*.

`argumentosDaLive(sinais)` devolve as frases **verdadeiras** para aquele aluno,
ordenadas por força:

| Força | id | De onde vem |
|---:|---|---|
| 100 | `causa-raiz` | `erro_dominante` do Motor Cognitivo |
| 80 | `ponto-fraco` | `focos` do Painel |
| 70 | `quintas-restantes` | só quando ≤ 6 quintas até a prova |
| 40 | `rotina` | ofensiva ≥ 3 ou 3+ dias ativos na semana |
| 10 | `generico` | aluno sem dado nenhum |

As quatro regras travadas por teste (mexer nelas é mexer na **ética**, não na copy)
estão em [[inviolaveis]].

Onde aparece: Painel (`ChamadaDaLive`, custo zero — os sinais já estão carregados),
aba Cursos (uma chamada a `/motor/perfil`, memorizada por `total_respostas`) e loja.

## Canal de reclamações e sugestões

`/sugestoes` (aluno) + `/admin/sugestoes` (equipe). **Não confundir com a bandeira
de questão** (`question_reports_routes.py`), que fala de UMA questão e paga 5 Sparks
quando aprovada.

Este canal é sobre o **produto** e **não paga nada, de propósito**: reclamação
remunerada vira ruído, e cobrar para reclamar calaria quem tem menos saldo.

Quatro tipos fechados (reclamação/sugestão/problema/elogio) porque a fila do admin
ordena por eles. Estados: nova → lida → **respondida**, e **responder é o único
caminho para o estado final** — a resposta volta para a lista do aluno. Um canal sem
resposta visível deixa de ser usado na segunda vez.

O `contexto` da mensagem é a rota anterior, passada por `state.de` na navegação —
**nunca `document.referrer`**, que numa SPA aponta para fora do site.

## Painel do admin

`/admin/users` é a lista completa (saldo, questões respondidas, cupom); o clique
abre a ficha; `/admin/transacoes` mostra toda cobrança. Uso de cupons em
`/admin/promo-codes`.

**Duas colunas nascem vazias para o passado, e isso é correto** — `saldo_antes`/
`saldo_apos` e `users.promo_code` só existem a partir de 2026-09-15. A tela mostra
"—", nunca "0". O contador global `promo_codes.usos` diz *quantos* e nunca *quem*,
daí o campo `usos_sem_vinculo`.

---
Relacionado: [[inviolaveis]] · [[catalogo]] · [[custo-de-leitura]] · [[pagamentos]]
