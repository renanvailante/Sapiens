---
tags: [produto, ia, mentis]
atualizado: 2026-10-06
---

# Mentis — a IA e o mascote

Em 2026-09-03 o "Zinho" virou **Mentis**: a Entidade Cognitiva escolhida no
moodboard de identidade — **núcleo de luz com dois olhos, não um animal**. Tudo que
fala como Mentis mora em `mentis_routes.py` (`/api/mentis/*`); a rota antiga
`/api/firestore/students/me/zinho` **deixou de existir**.

## A regra de arte, que vale mais que qualquer detalhe

> **Mentor, não bichinho.** Sem emoji, sem euforia, olhos em cápsula estreita —
> ponto redondo lê como companion de robô.

`components/Mentis.jsx` tem `variante="icone"` porque em 16–24px a órbita vira
borrão; só núcleo + olhos sobrevive.

Na narrativa da marca ela é **o guia, nunca o herói** ([[marca]]). O bloco "você é
o guia" está nos prompts `CHAT_SYSTEM` e `INTERVENCAO_SYSTEM`.

## As superfícies pagas

Preços em [[economia-de-sparks]]. O que importa aqui é **o que cada uma é**:

- **"Saiba mais" numa questão** — explicação genérica por item, cacheada em
  `mentis_explicacoes` (prefixo `mentis-v1`). **Cache hit ainda cobra.**
- **O chat** (`/mentis/sessao*`) — 70 abrem 24h, cada mensagem custa 10. Retomar
  dentro da janela é grátis.
- **"Explicar melhor"** um trecho de curso/e-book — ver [[cursos-conteudo]].
- **Intervenção** a partir de um card de erro.
- **Corrigir dissertativa** — veredito é do servidor, não do modelo.
- **Reescrever os blocos da semana** — e se ela falhar, devolve os Sparks **e
  entrega a semana determinística assim mesmo**, nunca 503 seco.

**Todo caminho pago segue o mesmo esqueleto: débito → try → reembolso** — e o
reembolso é do que foi COBRADO (`_cobrar_com_recibo` devolve o recibo), nunca o
preço de tabela: a ilimitada não paga e por isso não recebe estorno. A leitura
da rodada (`/students/me/sessao/diagnostico`) também passa por aqui. Ver
[[economia-de-sparks]].

## As cinco decisões de economia de tokens

O pedido foi literal: *"economize o máximo possível"*.

1. O **dossiê é montado uma vez** na abertura e reusado em toda mensagem.
2. **A abertura não chama o modelo** — a mensagem de boas-vindas é template com os
   números reais do aluno (`_texto_de_abertura`).
3. **O dossiê tem teto** (5 fracos / 3 fortes / 3 padrões, evidência em 160 chars):
   aluno com 2 anos de histórico manda o mesmo contexto que um de 2 semanas.
4. **Só as últimas 3 trocas** acompanham a pergunta (`_HISTORICO_TURNOS`).
5. `thinking_level="MINIMAL"` + resposta limitada a ~120 palavras por contrato de
   prompt. Mensagem do aluno limitada a 600 chars pelo pydantic.

> **Ao estender o chat, não acrescente contexto por mensagem — acrescente ao dossiê
> da abertura**, ou o custo por turno volta a crescer.

## O dossiê é determinístico

Sai de `annotation_service.compute_diagnostico_real` — a **mesma** medida de
`/diagnostico`, sem IA ([[motor-cognitivo]]). Desde 17/09 inclui também o progresso
em cursos (`cursos_progresso.resumo_para_mentis`, reusando a consulta bounded que já
existia — **nunca** lê `cursos_eventos`). Antes disso ela sabia tudo sobre treino de
ENEM e nada sobre curso: quem passava a tarde numa estação e abria o chat encontrava
uma tutora sem memória daquilo.

**O painel lateral mostra ao aluno o mesmo dado que o modelo recebeu, de propósito:
a conversa não pode parecer mágica.**

## Mentis como camada de navegação

Ação `{"tipo":"ir","destino":"<chave>"}` validada contra a lista **fechada**
`mentis_routes.DESTINOS`. **O modelo escolhe uma chave, nunca uma URL.**
`MentisAtalhos` mostra os mesmos destinos como chips **grátis**, inclusive com a
sessão fechada — navegar não pode custar Spark.

## Onde a Mentis NÃO decide

Padrão recorrente e deliberado — o modelo escreve, a aritmética decide:

| Superfície | O modelo faz | Quem decide |
|---|---|---|
| Cronograma | reescreve título e detalhe | `alocar` + `prioridade_enem` |
| Dissertativa | `atendido: bool` por critério | 70% dos critérios, no servidor |
| Redação | evidência para itens ambíguos | `decision_gate.classificar()` |
| Painel do perfil | nada — as frases são do servidor | `perfil_painel._leituras` |

## Cards de erro → pedido pronto, nunca enviado sozinho

Todo card que aponta um erro é clicável e tem saída (`CardDeMelhora.jsx`): ou a
missão específica do Treino (`/treino?hab=HAB-xx`) ou `MentisPedido.jsx`, uma janela
com a mensagem **já escrita** sobre aquele ponto.

> **A mensagem nunca é enviada sozinha.** Sem sessão o botão é "Abrir chat · 70
> Sparks" (abrir não envia); com sessão vira "Enviar · 10 Sparks". Quem cobra é
> `mentis_routes.py`; a origem chega como `origem: "card"`.

## Lembrar-me com a Mentis

O aluno seleciona **qualquer** trecho em **qualquer** tela e um botão flutuante
guarda aquilo na fila de Revisões por 10 Sparks. Camada global montada uma vez em
`App.js` — tela nova não precisa fazer nada.

> **Nada nesse caminho chama LLM, e isso é regra, não estado atual.** Há teste que
> falha se alguém chamar `ai_service` aí. Aqui o texto **vem** do cliente, então os
> 10 Sparks pagam **o lugar na fila**, não geração — o inverso da regra de
> `explicar_trecho`.

A identidade do conteúdo é a chave de idempotência (ver [[dados]]). Objeto
não-textual é opt-in por `data-lembrar` + `data-lembrar-ref` (marcados hoje: tabela
e exemplo resolvido em `curso/Blocos.jsx`). `CardDeMelhora` **não** foi marcado de
propósito — é um card clicável, e o toque longo terminaria em navegação.

**A revisão programada existe desde 2026-10-01.** O trecho guardado volta no dia
seguinte e sobe a escada de `revisao_espacada.INTERVALOS_DIAS` (1, 3, 7, 16, 35) a
cada "Revisei" (`POST /lembretes/:id/revisei`, só no dia da volta); no último
degrau o ciclo se completa e ele sai como revisado. Lembrete antigo, sem data,
vence no dia seguinte ao que foi guardado — calculado na leitura, sem migração,
que é o que o campo nascer pronto comprou. Rever é de graça, e nada disso chama
modelo. O Hoje avisa os que voltaram (`vencidos`, no "O que mudou").

---
Relacionado: [[economia-de-sparks]] · [[motor-cognitivo]] · [[marca]] · [[cursos-conteudo]]
