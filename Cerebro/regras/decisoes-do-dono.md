---
tags: [regra, produto]
atualizado: 2026-10-10
---

# Decisões que são do dono, não minhas

Números e ordens que **parecem** ajustáveis e não são: foram escolhidos
explicitamente pelo dono do produto, às vezes contra a minha sugestão. Mexer sem
perguntar é desfazer uma decisão, não otimizar um parâmetro.

## Pesos de prioridade do ENEM

    Matemática, Redação            → 1.00
    Biologia, Química, Física      → 0.70
    Ciências Humanas, Linguagens   → 0.50

Enunciado literalmente: *"matemática e redação são o que mais gera pontos pro
Enem; depois bio/quím/fís; depois humanas e linguagens"*. Vive em
`prioridade_enem.py`. **Não reordene sem ele.** Ver [[motor-cognitivo]].

## A régua do mapa de habilidades é VOLUME DE ACERTOS

Mudou em 2026-09-15 a pedido explícito. Antes era **cobertura** (processos tocados
/ processos do domínio) — um domínio de três processos ficava "Dominado" com 3-5
questões respondidas. Hoje: `mastery_por_acertos(n)`, ancorada em
`ACERTOS_ANCORA = 40 → MASTERY_ANCORA = 0.80`, teto assintótico 0.92.
Ordens de grandeza: 5 ≈ 21%, 10 ≈ 37%, 20 ≈ 59%, 40 = 80%.

Se pedirem para o número subir mais rápido ou mais devagar, **mexa na âncora e no
teste, nunca na fórmula** — a constante da curva é derivada da âncora e reescala
tudo sozinha.

## A ordem e a composição da barra de navegação

São decisão de produto. Ver [[navegacao]] para a lista vigente e o orçamento de
largura. O que é regra e não gosto: **âmbar é recurso de uso único** — só "Aulas",
o único destino com hora marcada.

## O chat da Mentis cobra por sessão, não por abertura

70 Sparks abrem 24h; retomar dentro da janela é grátis. Escolhido entre "cobra a
cada abertura" e "desbloqueio permanente".

## A escada dos pacotes

**Pacote mais caro nunca concede menos direito que um mais barato.** Teste quebra
o build se inverter. O pedido original ("1.500 = só as lives, 4.000 = os cursos")
invertia a escada; o dono escolheu herdar as lives no de cima quando isso foi
apontado. Ver [[catalogo]].

## O guia abre só no primeiro acesso

Revisto em 2026-09-17. Entre 15 e 17/09 abria uma vez por sessão do navegador — na
prática todo dia, 21 balões na cara de quem só queria estudar. Um tutorial que
reaparece deixa de ser ajuda e vira pedágio.

## O mentor é sempre "Vitor Lara", nunca "o Vitor"

**Não existe `MENTOR.primeiroNome`, e a ausência é a regra.** O campo existiu, seis
telas o usavam, e tratar por primeiro nome desfazia exatamente o que o nome
completo constrói — a credencial pertence a uma pessoa pública e verificável.

## Preços que eu escolhi e ele não pediu

Declarados como meus na revisão de 2026-09-17, portanto os mais baratos de mudar:
remontagem do cronograma (10), existência e preço do OCR de redação (25), e o
preço inicial do e-book. Todos são uma constante só.

## A ofensiva de 5 dias vale 2 dias de Sapiens Plus — e o aluno sabe desde o início

Pedido de 2026-10-08: *"quero que o aluno saiba desde o início que, se manter a
ofensiva de cinco dias, ele vai obter dois dias como se fosse pago, como se fosse
do Sapiens Plus"*. Os dois números (`engajamento.PLUS_META_DIAS`,
`PLUS_PRESENTE_DIAS`) e o "desde o início" (etapa final do `/bem-vindo` e o card
no Hoje desde a conta nova) são dele. **O que é meu e foi declarado como meu**, e
portanto o mais barato de mudar: o prêmio ser **uma vez por aluno** e não a cada 5
dias; "Plus" ser Mentis ilimitada + cursos/e-books + sala VIP, **sem a live**; e
a conta que já tinha ≥ 5 dias no dia da entrada ganhar na primeira leitura.
Mecânica em [[engajamento]].

## O aluno nunca pensa "e agora?" — o Hoje é uma trilha (Duolingo)

Pedido de 2026-10-09: *"quero que o aluno saiba exatamente o que fazer sempre
(…) nunca ele pode ficar pensando 'e agora? onde tenho que ir?'. Você pode usar
a Mentis pra guiar (…) com muitas animações, e até mesmo uma voz"*. A régua
(um caminho, um nó aceso, a Mentis dizendo o próximo passo em toda tela) é
dele. **O que é meu e foi declarado como meu**, portanto o mais barato de
mudar: a ordem dos nós (revisão → blocos → missões → troféu → lição extra), a
voz **desligada** por padrão, a dica de cada área aparecer uma vez por
aparelho, e Matemática como área da prática quando não há gabarito. Mecânica
em [[padroes-de-tela]] e [[mentis]].

## O pipeline está CONGELADO

Aprovado em 2026-08-22 como baseline de custo. Instrução explícita: nenhuma
mudança estrutural em pipeline, Schema, Ontologia ou contratos cognitivos como
parte de trabalho de custo. **A próxima otimização tem de ser dirigida por
telemetria real** (`db.gemini_usage`), não por outra rodada de estimativa. Ver
[[pipeline-e-corpus]].

---
Relacionado: [[inviolaveis]] · [[economia-de-sparks]] · [[navegacao]]
