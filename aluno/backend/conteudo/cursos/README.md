# Conteúdo dos cursos — contrato de autoria (schema 1.0)

Esta pasta é **a única entrada de conteúdo pedagógico** do Sapiens. Quem
escreve um curso escreve arquivos JSON aqui; nada mais precisa mudar no
código para o curso aparecer no produto.

Quem lê estes arquivos é [`cursos_conteudo.py`](../../cursos_conteudo.py).
Quem os serve é [`cursos_estudo_routes.py`](../../cursos_estudo_routes.py).
Este documento é o contrato entre os dois e quem produz o texto.

> **Este arquivo é documentação.** Os trechos de JSON abaixo são a forma, não
> conteúdo do produto — `…` marca onde entra texto real.

> **Existem dois caminhos para publicar, e este documento descreve o primeiro.**
> O arquivo JSON, que entra por commit, é o caminho de quem escreve um curso
> inteiro: dá revisão antes de publicar, diff do que mudou e rollback.
> O segundo é o painel do admin (`/admin/cursos` → *Criar conteúdo a partir de
> texto*): cola-se o TEXTO da aula, o servidor compila em blocos
> ([`cursos_ingestao.py`](../../cursos_ingestao.py)), valida **com este mesmo
> contrato** e grava no Mongo ([`cursos_publicados.py`](../../cursos_publicados.py)).
> É o caminho de quem escreveu uma estação e quer vê-la no ar hoje. Os dois
> convivem: o que o painel publica entra POR CIMA do arquivo, o arquivo nunca é
> reescrito, e tirar a publicação do ar devolve o curso ao que está aqui.

---

## 1. A hierarquia

```
curso      → o produto. Vive em cursos.py (título, preço, status). NÃO se declara aqui.
  trilha   → um caminho dentro do curso. Tem estações EM ORDEM.
    estação → a unidade de estudo: 10 a 20 minutos, a menor coisa que se conclui.
      bloco → a menor coisa que se lê, assiste ou responde.
```

Uma estação é a peça que se valida sozinha. Comece publicando **duas ou três**
e olhe os dados antes de produzir o curso inteiro — é para isso que o sistema
foi desenhado.

## 2. Os arquivos

```
conteudo/cursos/<curso_id>/
├── curso.json                    manifesto: quais trilhas, que estações, em que ordem
└── estacoes/
    ├── <estacao_id>.json
    └── <estacao_id>.json
```

Três regras de endereço, todas verificadas na carga:

* `<curso_id>` (nome da pasta) **precisa existir** em `cursos.CURSOS`.
* `curso_id` dentro do `curso.json` é igual ao nome da pasta.
* `estacao_id` dentro do arquivo é igual ao nome do arquivo (sem `.json`).

Ids são *slugs*: minúsculas, números e hífen (`fracoes-01`, `regra-de-tres`).

## 3. `curso.json`

```jsonc
{
  "schema_version": "1.0",
  "curso_id": "matematica-basica",
  "versao": "2026-09-16",          // muda a cada publicação; fica gravado nos dados do aluno
  "trilhas": [
    {
      "trilha_id": "fracoes",
      "titulo": "…",
      "resumo": "…",               // opcional, uma linha
      "estacoes": ["fracoes-01", "fracoes-02"]   // a ORDEM aqui é a ordem do aluno
    }
  ]
}
```

Uma estação aparece **em uma trilha só**. Repetir a mesma estação em duas
trilhas daria a ela dois progressos e um id só.

## 4. `estacoes/<id>.json`

```jsonc
{
  "schema_version": "1.0",
  "estacao_id": "fracoes-01",
  "titulo": "…",
  "objetivo": "Ao fim desta estação você consegue …",   // OBRIGATÓRIO
  "versao": "2026-09-16",
  "duracao_minutos": 12,                  // opcional
  "numero": 7,                            // opcional: "Estação 07" no material
  "habilidades": ["HAB-07"],              // opcional, formato HAB-NN
  "conceitos": ["ordem-de-operacoes"],    // opcional, slugs livres do curso
  "pre_requisitos": ["fracoes-00"],       // opcional; além da ordem da trilha
  "conclusao": {"tipo": "todos_os_exercicios"},   // opcional (é o padrão)
  "blocos": [ … ]
}
```

**`objetivo` é obrigatório e não é enfeite.** É a frase que diz o que o aluno
sai sabendo *fazer*, e é ela que justifica a ordem das estações. Uma estação
cujo objetivo não dá para escrever em uma frase está grande demais: divida.

**`habilidades` e `conceitos` são coisas diferentes.** `habilidades` são
códigos do catálogo compartilhado (`HAB-01..HAB-56`, o mesmo do Treino e da
prova) — é por eles que o desempenho no curso se soma ao que o aluno mostra no
ENEM, então só entram quando o casamento é defensável. `conceitos` é o
vocabulário do próprio curso, livre, e serve para a análise por assunto dentro
dele. **Nenhum dos dois aparece para o aluno**: a tela traduz para linguagem
pedagógica (ver a regra de privacidade da ontologia).

**`conclusao`** aceita dois critérios, e só dois:

| `tipo` | significa |
|---|---|
| `todos_os_exercicios` | acertar, ao menos uma vez, todos os exercícios que contam |
| `minimo_de_acertos` + `"minimo": N` | acertar N deles |

Desafio nunca conta. Exercício com `"opcional": true` nunca conta. Vídeo nunca
conta.

## 5. Os seis tipos de bloco

A ordem dos blocos é a ordem da aula. O padrão que funciona é
**texto → exemplo → exercícios do fácil ao difícil → desafio**, mas nada
obriga: alterne quantas vezes o assunto pedir.

### `texto`

```jsonc
{
  "tipo": "texto",
  "bloco_id": "b1",
  "titulo": "…",                      // opcional
  "variante": "padrao",               // padrao | destaque | atencao
  "markdown": "…"
}
```

O `markdown` aceita um subconjunto deliberadamente pequeno, o mesmo que a tela
sabe renderizar:

| escreva | vira |
|---|---|
| `## Título` | subtítulo |
| `**forte**` | negrito |
| `*ênfase*` | itálico |
| `` `código` `` | monoespaçado |
| `- item` / `1. item` | lista |
| `> nota` | citação |
| `$x^2+1$` | fórmula (KaTeX) |
| linha em branco | parágrafo novo |

Três detalhes que economizam revisão:

* **Asterisco de multiplicação é seguro.** `3 * 4 = 12` fica como está — o
  marcador de ênfase precisa estar colado ao texto (`*assim*`), nunca com
  espaço ao lado. Dentro de `$…$` o asterisco também é sempre LaTeX.
* **Negrito com itálico dentro** escreve-se `**muito *mesmo* aqui**`.
  `***assim***` não faz parte do subconjunto.
* **Um bloco é homogêneo.** `veja:` seguido de `- item` na mesma linha em
  branco vira um parágrafo só. Deixe uma linha em branco antes da lista.

Não existe HTML, imagem nem link neste subconjunto. Se o conteúdo precisar de
algo além disso, é um tipo de bloco novo — não um `markdown` mais esperto.

### `tabela` — o que não cabe em parágrafo

```jsonc
{
  "tipo": "tabela",
  "bloco_id": "b2",
  "titulo": "…",                        // opcional
  "colunas": ["Propriedade", "Exemplo"],
  "linhas": [
    ["`aⁿ × aᵐ = aⁿ⁺ᵐ`", "`2³ × 2² = 2⁵`"]
  ]
}
```

Existe porque o subconjunto de markdown acima **não tem tabela**, e a regra da
seção 8 é clara: o que passa do subconjunto vira um tipo de bloco, não um
`markdown` mais esperto. Toda linha tem exatamente o número de células do
cabeçalho — tabela torta é recusada na carga, porque uma célula a menos
desloca a linha inteira e o aluno lê o dado errado.

O texto de cada célula aceita o mesmo subconjunto inline (`**forte**`,
`` `código` ``, `$fórmula$`).

### `exemplo` — o modelo resolvido

```jsonc
{
  "tipo": "exemplo",
  "bloco_id": "b2",
  "enunciado": "…",
  "passos": [
    {"texto": "…", "comentario": "…"}   // `comentario` é o "por que este passo", opcional
  ],
  "fecho": "…"                          // opcional: o que generalizar do exemplo
}
```

### `video` — opcional, sempre

```jsonc
{
  "tipo": "video",
  "bloco_id": "b3",
  "titulo": "…",
  "provedor": "youtube",          // youtube | vimeo | arquivo
  "ref": null,                    // id/URL — ou null enquanto não existe
  "duracao_segundos": 420,        // opcional
  "resumo": "…"                   // opcional
}
```

`"ref": null` é **pendência declarada**: o lugar do vídeo já está no roteiro,
a gravação ainda não existe. O bloco não é mostrado ao aluno e aparece como
"vídeo pendente" no painel do admin. É assim que se escreve a estação hoje e
se grava o vídeo depois, sem mexer em nada.

### `exercicio` — o que faz a estação progredir

```jsonc
{
  "tipo": "exercicio",
  "bloco_id": "b4",
  "nivel": 1,                     // 1 a 5 — NÃO PODE RETROCEDER dentro da estação
  "formato": "multipla_escolha",
  "enunciado": "…",
  "alternativas": [
    {"id": "a", "texto": "…"},
    {"id": "b", "texto": "…"}
  ],
  "gabarito": "a",
  "dica": "…",                    // mostrada no 1º erro
  "feedback": {                   // por alternativa: o erro DESTA pessoa
    "a": "…",
    "b": "…"
  },
  "solucao": "…",                 // resolução completa: 3º erro, ou depois de acertar
  "opcional": false               // true = prática extra, não conta para concluir
}
```

Outros dois formatos:

```jsonc
{"formato": "numerico",     "gabarito": {"valor": 12.5, "tolerancia": 0.01},
 "feedback": {"correto": "…", "incorreto": "…"}}

{"formato": "texto_curto",  "gabarito": {"aceitos": ["…", "…"]},
 "feedback": {"correto": "…", "incorreto": "…"}}
```

`texto_curto` compara ignorando acento, caixa e espaço repetido.

### `desafio` — o teto da estação

Mesmos campos do exercício. Nunca conta para concluir, e seu `nivel` não pode
ser menor que o do exercício mais difícil da estação.

## 6. As regras que a carga recusa

Um curso com **qualquer** problema sai do ar inteiro e aparece no painel do
admin com a lista exata. Não existe "metade publicada": uma trilha com buraco
ensina uma sequência quebrada e trava o pré-requisito seguinte.

1. **Nenhum arquivo declara preço.** Chave chamada `custo`, `preco`, `sparks`,
   `valor_sparks` ou `desconto` é recusada em qualquer nível. Preço é decisão
   de produto: mora em `cursos.py` e em `sparks_store.py`, e quem cobra é o
   servidor. (O *enunciado* pode falar de preço à vontade — é o arquivo que
   não pode declarar um.)
2. **A progressão não retrocede.** `nivel` dos exercícios é não decrescente ao
   longo da estação.
3. **Gabarito existe e resolve.** Alternativa apontada existe; numérico tem
   tolerância; texto curto tem ao menos uma resposta aceita.
4. **Pré-requisito existe e não faz ciclo.**
5. **Id não se repete.** `estacao_id` único no curso, `bloco_id` único na
   estação — os dois são chave de progresso e de analytics.
6. **Estação alcançável.** Arquivo que nenhuma trilha cita é erro, não sobra.
7. **Estação concluível.** Com `todos_os_exercicios`, uma estação sem
   exercício nenhum seria concluída sem o aluno responder nada.

## 7. Como publicar

Quando o curso é escrito em markdown (um arquivo por estação, fora daqui), o
JSON não é digitado à mão — é gerado:

```bash
cd aluno/backend
python scripts/ingerir_curso_markdown.py --verificar   # nada é escrito
python scripts/ingerir_curso_markdown.py               # escreve o JSON
```

O script está documentado no próprio arquivo, inclusive as quatro
transformações que ele faz e que **não são cópia** (tabela vira bloco, o
feedback é repartido por alternativa, as alternativas são embaralhadas com
semente fixa e a conclusão vira 70% dos exercícios). Depois dele, sempre:

```bash
cd aluno/backend && python -m pytest tests/test_cursos_conteudo.py -q
```

A suíte valida **a pasta inteira**, então conteúdo quebrado derruba o build
antes de chegar a aluno nenhum. Em produção, o painel `/admin/cursos` mostra o
inventário (estações, exercícios por nível, vídeos pendentes) e os problemas
de carga, e recarrega do disco sem reiniciar o processo.

## 8. O que este contrato deliberadamente não tem

* **Preço, desconto, cupom ou Spark.** Ver regra 1.
* **Correção dissertativa.** Quando entrar, é um `formato` novo em
  `cursos_conteudo.FORMATOS` + um ramo em `corrigir()`. O resto da pilha não
  muda.
* **Conteúdo condicional por aluno.** A estação é a mesma para todo mundo; o
  que varia é o caminho até ela.
* **HTML.** Ver o subconjunto de markdown acima.
