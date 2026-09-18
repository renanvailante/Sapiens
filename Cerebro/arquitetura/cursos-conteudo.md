---
tags: [arquitetura, cursos, conteudo]
atualizado: 2026-09-18
---

# Cursos — o sistema que recebe conteúdo

A área Cursos deixou de ser "quatro cards de pré-venda" e virou um sistema que
**recebe conteúdo produzido fora** (o dono escreve no DeepSeek/ChatGPT e cola).
A arquitetura nasceu **sem nenhuma linha de conteúdo de propósito** — pedido
explícito de não preencher com conteúdo fictício.

## Quem é dono de quê

- `cursos.py` = **vitrine** (título, preço, status, pré-venda).
- `conteudo/cursos/<id>/` = **pedagogia**. `curso.json` (manifesto de trilhas) +
  `estacoes/<id>.json`. Trilha → estação (10–20 min, a menor coisa que se conclui)
  → bloco (`texto`, `tabela`, `exemplo`, `video`, `exercicio`, `desafio`).
- `conteudo/cursos/README.md` = **o contrato de autoria**. É ele que se entrega à
  IA que vai escrever o curso, não o código.

## O validador existe para impedir quatro coisas

`cursos_conteudo.py`:

1. **Preço nunca em conteúdo.** Chave `custo`/`preco`/`sparks`/`desconto` em
   qualquer nível derruba o arquivo. (O *enunciado* pode falar de preço à vontade —
   é o arquivo que não pode declarar um.)
2. **`nivel` dos exercícios não retrocede** dentro da estação, e desafio é o teto.
   "Do simples ao avançado" vira invariante verificável.
3. Gabarito existe e resolve; pré-requisito existe e não faz ciclo; id não se
   repete; estação órfã e estação sem exercício que conte são erro.
4. **Curso com qualquer problema sai do ar inteiro** e aparece em
   `/admin/cursos/conteudo` com o motivo arquivo a arquivo. Meia trilha ensina
   sequência quebrada e trava o pré-requisito seguinte.

## Dois caminhos de publicação, e o do painel vence

- **Arquivo** — o caminho de um curso inteiro (revisão, diff, rollback).
- **Painel** (`/admin/cursos` → *Criar conteúdo a partir de texto*) — cola-se o
  texto da aula, o servidor compila, valida com o **mesmo** `cursos_conteudo` e
  grava em `cursos_publicados` (Mongo, um documento por curso). A biblioteca em
  memória é `disco + publicados`, com o publicado por cima; o arquivo nunca é
  reescrito, e **despublicar devolve o curso ao que o repositório diz**.

Mongo e não disco porque o disco do Fly é efêmero e há mais de uma máquina. A
propagação entre processos é `garantir_atual()` — ver [[custo-de-leitura]].

**Um parser só:** `cursos_ingestao.py` (puro, sobre **texto**, não sobre caminho de
arquivo); `scripts/ingerir_curso_markdown.py` o chama.

**Compilar ≠ publicar, e são dois botões.** A prévia mostra o gabarito e o feedback
já repartido, porque o compilador embaralha alternativas e deduz nível — publicar
sem ver isso é publicar no escuro.

**O painel não cria curso no catálogo.** `curso_id` tem de existir em
`cursos.CURSOS`; título, preço e status são decisão de produto.

**A especificação do formato é UI**, não ajuda de leitura: `AdminCursos.jsx` →
`ESPECIFICACAO` é um texto pronto para ser **colado no gerador**, com botão de
copiar. Mudou regra no `cursos_ingestao`? Muda essa constante **no mesmo commit**.

## A tolerância do compilador é regra, não gentileza

Uma questão quebrada **não derruba mais a aula inteira**: vira aviso nominal e o
resto vai ao ar. Antes, um `**Resposta:**` esquecido descartava tudo. Idem desafio
em prosa e `## Objetivo` ausente. **O limite é ZERO exercícios compilados** — aí a
estação não tem como ser concluída e é recusada.

Aceito hoje: seção numerada (`## 2. Conteúdo`), título sem marcação (`QUESTÃO 1`),
alternativa com traço/negrito, título de seção repetido (**soma**, não sobrescreve
— era perda silenciosa de metade das questões) e dezenas de sinônimos de seção.

> **Os dois-pontos são obrigatórios** em `Resposta:`, `Feedback:`, `dificuldade:`.
> Com eles opcionais, o enunciado "Por que um gráfico que começa em 90 distorce a
> leitura?" era lido como a linha de `Feedback:` e a questão ia ao ar sem enunciado.

## Quatro transformações da ingestão que não são cópia

1. Tabela do markdown vira bloco `tabela` (tipo novo — o subconjunto não tinha).
2. O feedback-parágrafo é **repartido por alternativa**: a explicação vira
   `solucao`, cada "B soma primeiro" vira o feedback daquela alternativa, sem a
   letra.
3. **As alternativas são embaralhadas** com semente no `question_id`. No markdown
   original **231 das 233 respostas certas eram a letra A** — publicar assim
   ensinaria a clicar na primeira.
4. Conclusão = **70%** dos exercícios, não 100% (dez obrigatórios viraria muro).

> **O id da alternativa é a POSIÇÃO exibida** (a, b, c, d pela ordem na tela). Antes
> era a letra original do markdown — e com 231/233 em `a`, **o gabarito do curso
> inteiro estava legível no HTML**. Regerar o conteúdo é obrigatório depois de
> mexer no embaralhamento.

## O ritmo: etapas, não uma página longa

A estação é **paginada no cliente** (`lib/etapas.js`, pura e testada):
explicação → exemplos resolvidos → exercícios de 5 em 5. O contrato de conteúdo
continua sendo uma lista de blocos. "Continuar" numa tela de exercícios só libera
com **todas** respondidas, certas ou erradas — o muro é a escada de devolutiva, não
o botão. Quem volta cai na etapa onde parou.

**A escada didática é do servidor:** 1º erro = dica, 2º = comentário da alternativa
escolhida, 3º = resolução; acerto = comentário + resolução. Nada disso (nem o
gabarito) vai no GET da estação.

**Todo o progresso mora num trilho à direita** (`curso/TrilhoDeProgresso.jsx`),
fixo ao lado da aula. Antes estava espalhado em quatro lugares fora do campo de
visão de quem responde — e por isso "acertar não movia nada". **Não espalhe
progresso de novo**: `lib/etapas.progressoDasEtapas` é a única contabilidade.

## Seis estados, e `pulada` ≠ `concluida`

A sondagem de domínio ("já domino isto") pergunta 3 dos exercícios mais difíceis e
exige acerto de primeira nos três. Quem passa fica `pulada_em` **com a evidência
gravada** e **nunca** `concluida_em` — ver [[inviolaveis]]. Vale uma vez por
estação. `dominada` é outra coisa: concluída acertando tudo de primeira.

**"Pular até aqui"** (`POST /cursos/{c}/saltos/{estacao}`): 20 questões sorteadas
de todas as estações anteriores, sorteio do **servidor** e **gravado** (F5 não
redesenha a prova). 80% pula todas de uma vez. Uma tentativa por destino. **Nenhum
Spark no salto** — não é estudo, é prova. **Sem devolutiva entre as questões**:
explicar no meio da prova entregaria o método das seguintes. A prova grava no
documento do **destino**, e `_escrever` ganhou `abre_estacao=False` por isso.

## A estação conclui SOZINHA

Na resposta que cumpre o critério. Um botão de "concluir" que o aluno não visse
deixaria a seguinte trancada para sempre — trava que ninguém reporta e todo mundo
abandona.

## Dissertativa

`formato: "dissertativo"` tem `criterios` (a régua, que o aluno **vê** antes de
escrever) e `referencia` (a resposta do autor, que sai em `sanitizar_bloco`). **Sem
critério a questão não compila** — "a Mentis que se vire" publicaria uma nota que
ninguém sabe explicar.

`cc.corrigir` **levanta** no dissertativo, de propósito, e a rota comum devolve 409.
Quem corrige é `mentis_routes.corrigir_dissertativa` (20 Sparks).
**O veredito é do servidor, não do modelo**: a Mentis responde só `atendido: bool`
+ comentário por critério; quem soma e decide é a aritmética (70% dos critérios).
Critério que o modelo esqueceu conta como **não** atendido. Mesmo desenho do
Decision Gate da [[redacao]].

## E-books

`ebooks_conteudo.py` é o irmão pequeno: mesma disciplina, estrutura achatada
(ebook → página → bloco) e só os **três** tipos de bloco de leitura
(`texto`, `tabela`, `exemplo`) — quem quer praticar vai para um curso. **Nenhum
conteúdo real foi escrito**; a infraestrutura entrou vazia de propósito.

O leitor (`pages/EbookLeitor.jsx`) reaproveita **o mesmo** `curso/Blocos.jsx`. O
`<a href={pdf} download>` foi removido — ver [[inviolaveis]].

## "Explicar melhor" — uma função, dois chamadores

`mentis_routes.explicar_trecho` (10 Sparks), chamada de
`cursos_estudo_routes.explicar_bloco` e `cursos_routes.explicar_bloco_do_ebook`.

> **O texto NUNCA vem do cliente.** O chamador resolve o bloco de dentro do
> conteúdo publicado **depois** de confirmar acesso. Aceitar texto livre a 10
> Sparks seria um chat genérico disfarçado de botão.

Cache por `(origem, ref_id)`, onde `ref_id` inclui a **versão** do conteúdo. Botão
só em blocos de leitura — exercício e desafio têm a devolutiva da resposta.

## Recompensa

`cursos_recompensa.py` é o **único** lugar que sabe quanto vale um exercício. XP com
`chave_unica` em `tentou:` **e** `acertou:` — sem as duas guardas, errar em laço
fabricaria XP. Ver [[economia-de-sparks]].

## Detalhes de render já pagos

- O parser de markdown do frontend (`lib/conteudoMarkdown.js`) é subconjunto fechado
  e testado: `3 * 4 * 5` **não** vira itálico (o marcador não pode encostar em
  espaço). Bug real, achado por teste, que teria estragado meio curso de Matemática.
- **Vídeo com `ref: null`** é pendência declarada: não vai para a tela e conta como
  "a gravar" no inventário.
- **O exercício acertado ficava travado para sempre** (`travado` era
  `jaAcertou && !resultado`, e "Responder de novo" só limpava `resultado`, que já
  era nulo). Hoje há estado `refazendo` próprio.
- O caminho serpenteado usa ciclo de offsets de **quatro** (`[0, 96, 0, -96]`), não
  de oito — com oito, as cinco primeiras posições caíam todas do lado positivo. A
  coluna do grid precisa ter a largura **exata** de `LARGURA`, senão o serpenteio é
  recortado.

## Matemática Básica

Publicado: 24 estações, 240 exercícios, 24 desafios, 5 trilhas, por ingestão de
`cursos/matemática básica/*.md`. **O nome do arquivo não diz nada** — `mat basica
4.md` é a estação 06; número e título saem do frontmatter. A estação 12 chegou
truncada (572 bytes) e foi reescrita ao lado, em
`mat basica 12 - estacao completa.md`; o ingestor escolhe a fonte mais completa e
anuncia a escolha.

---
Relacionado: [[catalogo]] · [[economia-de-sparks]] · [[mentis]] · [[sistema-visual]]
