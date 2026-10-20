---
tags: [produto, ia, mentis]
atualizado: 2026-10-19
---

# Mentis — a IA e o mascote

Em 2026-09-03 o "Zinho" virou **Mentis**: a Entidade Cognitiva escolhida no
moodboard de identidade — **núcleo de luz com dois olhos, não um animal**. Tudo que
fala como Mentis mora em `mentis_routes.py` (`/api/mentis/*`); a rota antiga
`/api/firestore/students/me/zinho` **deixou de existir**.

## A regra de arte, que vale mais que qualquer detalhe

> **Mentor, não bichinho.** Sem emoji, sem euforia, olhos em cápsula estreita —
> ponto redondo lê como companion de robô. **A forma não muda**: núcleo de luz,
> sem animal, sem boca.

**Revisto em 2026-10-09: a regra passou a valer para a FALA, não para o
movimento.** O dono pediu a Mentis conduzindo o aluno "com muitas animações, e
até mesmo uma voz". Ela ganhou estados em `Mentis.jsx`: `falando` (o núcleo
respira no ritmo e duas ondas saem do lado — é como ela fala sem boca),
`feliz` (olhos em arco e um salto; **só** quando há o que celebrar, contado pelo
servidor), `surpresa`, e as props `olhar` (-1 a 1, ela olha para o que aponta)
e `flutuar`. O que **não** mudou: o texto dela continua sem emoji e sem
euforia — `trilhaDoDia.test.js` falha se uma fala da trilha tiver emoji.

`components/Mentis.jsx` tem `variante="icone"` porque em 16–24px a órbita vira
borrão; só núcleo + olhos sobrevive.

Na narrativa da marca ela é **o guia, nunca o herói** ([[marca]]). O bloco "você é
o guia" está nos prompts `CHAT_SYSTEM` e `INTERVENCAO_SYSTEM`.

## A guia do produto (2026-10-09)

Ela deixou de ser só a porta do chat e virou **quem diz o que fazer**, como o
personagem do Duolingo — de graça, sem chamar modelo:

- **No Hoje, no conteúdo:** o balão (`caminho/BalaoDaMentis`) com saudação, a
  ofensiva e o nó aceso da trilha numa frase, e UM botão. As frases são
  template sobre dado real (`trilhaDoDia.falaDaMentis`), como a abertura do chat.
  O mesmo balão conduz o `/bem-vindo`.
- **Em toda tela, flutuando:** o botão é a própria personagem (não mais um
  ícone de brilho). Na primeira visita a cada área ela diz, num balão, o que se
  faz ali (`lib/dicasDaMentis.js` — uma vez por área por aparelho, nunca por
  cima de questão, nunca no Hoje). O painel abre com **"Seu próximo passo"**
  antes da conversa paga: o nó que o Hoje publicou. Navegar nunca custa Spark.
- **A voz** (`lib/vozDaMentis.js`) é **gravada**: um catálogo fixo de frases
  (`lib/falasGravadas.json`) gravado UMA vez numa voz brasileira neural do
  Gemini e publicado como MP3 estático (`public/voz/`). Tocar é baixar arquivo
  do Cloudflare — **nenhuma API, nenhum custo por fala**. O balão continua
  escrevendo o que é do aluno (nome, números, títulos); a voz diz a mesma
  ideia em frases inteiras emendadas com 0,3 s de fôlego (`falaDaMentis` devolve
  `voz`, a lista de ids). **Desligada por padrão** — frase falada sem aviso no
  ônibus é constrangimento — com o alto-falante sempre no balão; quem liga fica
  com ela ligada (por aparelho). Sem gesto do aluno o navegador não toca som:
  a fala fica pendente e sai no primeiro toque. Sem Web Audio ou com arquivo
  que não veio, a reserva é a síntese do aparelho (`speechSynthesis`) lendo o
  balão.

### Mudar ou acrescentar uma frase da voz

Edite `falasGravadas.json` e rode `scripts/gravar_falas_da_mentis.py` com o
Python do backend (ele lê a `GEMINI_API_KEY` de `aluno/backend/.env`).
`vozDaMentis.test.js` **falha enquanto o áudio não acompanhar o texto** (o hash
de voz+modelo+estilo+texto está no nome do arquivo). Três coisas que já
custaram tempo:

- **A cota grátis é de 10 pedidos por dia POR MODELO de voz** (medido em
  2026-10-19, "limit: 10 requests per day on Free Tier"). Por isso o script
  grava as falas de um mesmo tom num pedido só, separadas por `<long pause>`,
  e corta o áudio alinhando as pausas ao tamanho de cada texto. Frase nova que
  não coube na cota do dia declara `"reserva"` (uma frase vizinha já gravada)
  e o app usa a reserva até ela ser gravada.
- **Quem grava não consegue ouvir.** `--conferir` transcreve todos os MP3 num
  modelo de texto e compara com o catálogo; frases muito curtas lado a lado
  ("Bom dia!", "Boa tarde!") o transcritor junta — confira essas uma a uma.
- **O modelo de voz fala, não lê:** troca "está" por "tá" e "para" por "pra".
  É naturalidade, não erro de corte.

### Por que não gerar a voz na hora, por API

Foi construído e descartado em 2026-10-19. Gerar cada fala no servidor
(`gemini-3.8-flash-tts`, streaming) dizia o nome e os números do aluno, mas:
**(1)** a chave do projeto é Free Tier — 10 falas novas por dia para o produto
INTEIRO, depois disso nada; **(2)** com faturamento, ~270 tokens de áudio por
fala de 11 s ≈ US$ 0,0025 por fala (US$ 0,005 a partir de 2027, quando a tabela
dobra), e um aluno ativo gera umas 6 falas novas por dia — ~R$ 2,50 por mês
por aluno com a voz ligada, ~R$ 5 em 2027. O dono não quis pagar nem cobrar
por isso ([[decisoes-do-dono]]).

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
