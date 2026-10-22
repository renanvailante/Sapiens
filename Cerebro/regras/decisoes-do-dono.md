---
tags: [regra, produto]
atualizado: 2026-10-22
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

## O guia não abre sozinho (2026-10-22)

Duas revisões. Em 2026-09-17: de "uma vez por sessão do navegador" (na prática
todo dia, 21 balões na cara de quem só queria estudar) para "só no primeiro
acesso" — um tutorial que reaparece deixa de ser ajuda e vira pedágio. Em
2026-10-22, aprovado pelo dono junto com a ativação (abaixo): **nem no primeiro
acesso**. Os cinco balões ficavam entre o cadastro e a primeira questão; o que
eles ensinavam as dicas da Mentis por área já dizem na hora em que importam.
O guia só abre pedido ("Guia" no Hoje, "Rever o guia" no Menu).

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

## A voz da Mentis é de graça e não chama API

Pedido de 2026-10-19: *"idealmente, a voz seria de graça e sem usar nenhuma
api (…) assim, não precisaríamos cobrar do cliente"*. A alternativa que ele
considerou e deixou de lado foi cobrar 50 Sparks pelo acesso à voz gerada por
API. **O que é meu e foi declarado como meu**, portanto o mais barato de
mudar: a voz `pt-br-podcaster-4` (escolhida entre cinco ouvindo a mesma frase),
o modelo `lite` da gravação (o principal estourou a cota do dia), a redação de
cada frase falada, e a voz NÃO dizer o nome do aluno. Mecânica em [[mentis]].

## Simples como o Duolingo, e o importante em cima (2026-10-19)

Pedido, com cinco prints do Duolingo: *"o site atual do sapiens está muito poluído
e pouco intuitivo, principalmente a aba agenda (…) quero que o cronograma seja a
primeira coisa que o aluno veja (…) tudo que é mais importante precisa estar lá
em cima e tudo que for menos importante embaixo"*, e *"os gráficos bem evidentes
lá em cima"* no Progresso — inspirado no Duolingo **sem copiar a identidade**. A
régua (simplicidade, poucos botões, hierarquia de cima para baixo, cronograma
primeiro na Agenda, gráficos primeiro no Progresso) é dele.

**O que é meu e foi declarado como meu**, portanto o mais barato de mudar: a
Nunito, os valores da paleta, o trilho lateral no desktop, as cores de endereço
das áreas, a semana como quadro de colunas (em vez da grade de horas), a aula ao
vivo como item do dia, "Ajustar a semana" fechado por padrão, e o balão de
sugestões do Progresso nascer recolhido. Mecânica em [[sistema-visual]],
[[navegacao]] e [[padroes-de-tela]].

## A loja de Sparks abre nos pacotes (2026-10-19)

Pedido, com print da loja quebrada: *"melhore essa tela. Deixa ela bem atraente
porque é aí que o pessoal vai comprar e eu quero que ela fica no topo da
página"*. A ordem — **pacotes logo abaixo do título**, e só depois a oferta do
pacote de cima, indicar, recarga e histórico — é dele. Isso desfaz a regra antiga
de pôr "Indique um amigo" antes da grade.

**O que é meu e foi declarado como meu**, portanto o mais barato de mudar: o
selo "Economize X%" (quanto mais barato sai cada Spark contra o pacote de pior
preço por Spark, arredondado para baixo, a partir de 5%), o "Dá para N
correções de redação ou M explicações de questão" (divisão inteira pelos preços
de `/redacao/precos` e `/mentis/precos`), a pilha de moedas por quantidade, o
Pix cheio só no pacote em destaque e a fileira de garantias. Tudo é aritmética
sobre números do servidor — nenhum preço no JS. Mecânica em [[padroes-de-tela]].

## O primeiro dia enxuto e as metas do cadastro (2026-10-20)

Pedido, depois da análise de engajamento (28 de 43 alunos nunca tinham
respondido uma questão): *"enxugar o primeiro dia, deixar a 3ª missão possível
de cumprir e ajustar as metas do cadastro"*. O pedido é dele.

**O que é meu e foi declarado como meu**, portanto o mais barato de mudar: o que
saiu do dia 1 (a seção do mentor até a primeira resposta, e o Explorar fechado
para todos), o Treino como reserva da 3ª missão, e as faixas de meta — 70–100,
100–130 e 130–160 acertos, uma tabela só em `onboarding_routes.METAS`. O tour de
5 balões depois do `/bem-vindo` **ficou**, porque "o guia abre só no primeiro
acesso" é decisão dele (acima); é o próximo candidato a sair do dia 1, se ele
quiser.

## O cadastro abre no diagnóstico (2026-10-22)

Pedido, depois da análise de UX e retenção (28 de 43 contas nunca tinham
respondido uma questão): *"comece pela ativação: primeira questão em menos de 1
minuto depois do cadastro"*, aprovando três itens — o plano (`/bem-vindo`)
depois das primeiras questões, o WhatsApp fora do cadastro e o tour fora do
dia 1. **O pedido e os três itens são dele.**

**O que é meu e foi declarado como meu**, portanto o mais barato de mudar: o
diagnóstico ser de **10** questões (o número da landing), só texto, as mais
curtas de cada área, sem língua estrangeira e intercaladas abrindo por
Linguagens (`backend/diagnostico_inicial.py`); a ordem do plano (objetivo e
tempo → meta → dificuldades → WhatsApp → desafio do Plus); o **vídeo do mentor
fora** do primeiro acesso (segue na landing, na aula ao vivo e na mentoria); o
WhatsApp pedido no fim do plano e na compra da live, sempre **opcional**; e o
padrão de erro subir para logo abaixo do placar no fim do diagnóstico. O
desafio do Plus continua sendo a última etapa do plano e o card do Hoje
continua desde a conta nova — o "desde o início" de 2026-10-08 está de pé.

**O que NÃO mudou, de propósito:** o responsável de quem se declara menor
continua no cadastro. É regra de [[inviolaveis]] (LGPD art. 14); levá-lo para a
primeira compra foi sugerido na análise e depende de decisão do dono com
parecer jurídico.

## O pipeline está CONGELADO

Aprovado em 2026-08-22 como baseline de custo. Instrução explícita: nenhuma
mudança estrutural em pipeline, Schema, Ontologia ou contratos cognitivos como
parte de trabalho de custo. **A próxima otimização tem de ser dirigida por
telemetria real** (`db.gemini_usage`), não por outra rodada de estimativa. Ver
[[pipeline-e-corpus]].

---
Relacionado: [[inviolaveis]] · [[economia-de-sparks]] · [[navegacao]]
