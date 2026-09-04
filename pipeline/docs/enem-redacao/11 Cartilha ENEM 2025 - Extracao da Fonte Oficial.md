# 11 cartilha enem 2025 - extracao da fonte oficial · MD

### Id

ENEM-FONTE-1.0

### Titulo

Extração Estruturada da Fonte Oficial — A Redação do Enem 2025: Cartilha do(a) Participante

### Versao

1.0.0

### Estado

apoio_externo

### Declaracao_de_nao_normatividade

Este documento **não é fonte de categorias cognitivas do Sapiens** e **não governa** nenhum
Domínio, Competência, Processo, Habilidade ou Tipo de Erro do catálogo C1–C5. Sob
`00 Governanca e Versionamento Sapiens v1.0.md` §1.1, material externo (e o próprio GOV-1.0
cita nominalmente "a Matriz de Referência do Enem" como exemplo) é **apoio, nunca fonte de
categorias**. Este documento reside em `pipeline/docs/` com `estado: apoio_externo` exatamente
pela via que o §1.1 autoriza, e não pelo caminho `rascunho → ativo → congelado`. Nenhuma
regra aqui vincula o corretor automatizado até que uma transação C4 explícita a adote.

### Criado_em

2026-08-24T15:18:20Z

### Atualizado_em

2026-08-24T15:18:20Z

### Camada

apoio_externo

### Origem_da_demanda

Pedido direto do usuário em 2026-08-24: transformar a Cartilha do Participante (Enem 2025) em
canon documental para futura correção automatizada de redações.

### Cni_membros

- `12 ENEM 2025 - Matriz de Correcao Estruturada.md` (ENEM-MATRIZ-1.0) — não é membro do
  mesmo CNI que este documento; **cita** este documento como fonte primária de cada regra que
  reorganiza. Ver §4.2 de GOV-1.0: este documento é o artefato **primário** em prosa; o doc 12 é
  **interpretação derivada**, não duplicata (declara `deriva_de:` em seu cabeçalho).

### Compativel_com

Não aplicável (apoio_externo; não é contrato C4).

### Remissoes_pendentes

Nenhuma.

---

## 0. Natureza deste documento

Este é o **artefato de extração fiel**: reproduz, de forma estruturada e rastreável por página,
apenas o conteúdo normativo e explicativo da Cartilha oficial do Inep/MEC necessário para uma
futura correção automatizada de redações do Enem. Não reproduz a cartilha integralmente, não
transcreve elementos gráficos decorativos, e não completa lacunas com conhecimento externo.

**Toda cláusula abaixo recebe um identificador estável** (ex.: `ZERO-03`) usado por
`12 ENEM 2025 - Matriz de Correcao Estruturada.md` e por `13 enem_regras_computaveis.json`
para citar esta fonte sem duplicá-la.

### 0.1 Proveniência do documento-fonte

```yaml
fonte:
  arquivo_original: a_redacao_no_enem_2025_cartilha_do_participante.pdf
  titulo: "A Redação do Enem 2025 — Cartilha do(a) Participante"
  editora: INEP/MEC — Diretoria de Avaliação da Educação Básica (DAEB)
  publicado_em: "setembro de 2025"
  paginas_totais: 78
  sha256: d8ab44dcbf5af808829d9dee89d23e7efa4f59df022b99102fac87489b870288
  tamanho_bytes: 1661327
  licenca_declarada_na_fonte: >
    "É permitida a reprodução total ou parcial desta publicação, desde que citada a fonte."
    (folha de rosto, física p.4)
  metodo_de_extracao:
    - "poppler-utils (pdftotext -layout) — descartado como fonte primária: a fonte
       embutida no PDF (Adobe Illustrator/PDF-X1) usa cmap customizado que corrompe
       acentuação e ligaduras ('ção' etc.) em texto de corpo."
    - "poppler-utils (pdftoppm -r 300 -png) + tesseract 5.5.3 (idioma 'por'), OCR local,
       sem API externa nem serviço pago, conforme exigido pela tarefa."
    - "Tabelas de níveis de desempenho (Competências I–V) conferidas visualmente,
       página a página, contra a imagem renderizada — não apenas contra o OCR — porque
       o OCR (psm 6) omitiu linhas de tabela em várias páginas."
  numeracao_de_pagina:
    convencao_usada_neste_documento: "página física do PDF (1–78), a mesma reportada por
      pdfinfo e por qualquer leitor de PDF padrão."
    nota: >
      A cartilha também imprime sua própria numeração de rodapé, que é igual à página
      física menos 2 a partir da página física 7 (ex.: física 16 → rodapé 14). Este
      documento cita sempre a página física; quando útil, o rodapé aparece entre
      parênteses.
```

### 0.2 O que foi deliberadamente NÃO extraído

- Elementos gráficos decorativos (capa, ilustrações Storyset, ícones, textura de fundo).
- Ficha técnica/expediente (créditos de equipe, física pp.1–4) — sem função normativa.
- Sumário interativo (física p.5) — índice, não conteúdo.
- **Seção 2 "Amostra de Redações" (física pp.42–72)**: 10 redações de estudantes com nota alta,
  cada uma com comentário qualitativo por competência. **Nenhuma nota numérica por
  competência é atribuída explicitamente no texto** — os comentários são qualitativos
  ("excelente domínio", "poucos desvios"). Como não há valor numérico a extrair e a tarefa
  veda cópia integral do PDF, esta seção **não foi transcrita**. Fica registrada como
  `AMOSTRA-REF` (§9) — um ponteiro de página para uso manual futuro (ex.: calibração humana
  de um modelo de correção), não como regra computável.
- **Seção "Leia Mais, Seja Mais" (física pp.73–75)**: recomendações de leitura para o(a)
  participante. Não contém critério de correção; registrada como `LEIAMAIS-REF` (§9),
  não extraída.
- "Leitura guiada da proposta" (física pp.40–41): anotações numeradas 1–6 sobre uma proposta
  de redação específica (tema 2024). É reafirmação das regras já extraídas em §2–§8 aplicadas a
  um exemplo concreto — não introduz regra nova. Não replicada; ver `LEITURA-GUIADA-REF` (§9).

---

## 1. Quem avalia e como a nota é composta

### GERAL-01 — Avaliadores

> "O texto produzido por você será avaliado por, no mínimo, duas pessoas graduadas em Letras
> ou Linguística, de forma independente, sem que uma conheça a nota atribuída pela outra."

Fonte: física p.7.

### GERAL-02 — Escala de notas

- Cada competência (I–V): nota entre **0 e 200 pontos**, em **múltiplos de 40**
  (0, 40, 80, 120, 160, 200) — confirmado pelas 5 tabelas de níveis de desempenho (§4).
- Nota total da redação: soma das 5 competências, entre **0 e 1.000 pontos**.
- Nota final do(a) participante: **média aritmética** das notas totais dos(as) dois(duas)
  avaliadores(as) independentes.

Fonte: física p.8.

### GERAL-03 — O que é discrepância

Considera-se discrepância entre os(as) dois(duas) avaliadores(as) quando:

- as notas totais diferem em **mais de 100 pontos**; OU
- a diferença em **qualquer competência** é **superior a 80 pontos**.

Fonte: física p.8.

### GERAL-04 — Fluxo de resolução de discrepância

1. Se há discrepância entre as duas primeiras avaliações: um(a) **terceiro(a) avaliador(a)**
   avalia de forma independente; a nota final é a **média aritmética das duas notas totais que
   mais se aproximarem** entre as três produzidas.
2. Se a discrepância **persistir** após a terceira avaliação: uma **banca de três avaliadores(as)**
   atribui a nota final.

Fonte: física p.9.

---

## 2. Motivos de nota 0 (zero) / anulação da redação inteira

### ZERO-01 — Fuga total ao tema

> "fuga total ao tema"

### ZERO-02 — Não atendimento ao tipo dissertativo-argumentativo

> "não obediência ao tipo dissertativo-argumentativo"

### ZERO-03 — Texto em branco

> "ausência de texto escrito na Folha de Redação, que será considerada 'Em Branco'"

### ZERO-04 — Texto insuficiente

> "extensão de até 7 (sete) linhas manuscritas, qualquer que seja o conteúdo, ou extensão de
> até 10 (dez) linhas escritas no sistema Braille, situações que configurarão 'Texto
> insuficiente'"

Nota: o limite manuscrito é "até 7 linhas" — ou seja, **7 linhas ou menos** é insuficiente; o
mínimo aceitável não é dado como "8 linhas" de forma explícita nesta cartilha, apenas o limite
superior da faixa "insuficiente". Registrado como ambiguidade `AMB-01` no doc 12.

### ZERO-05 — Anulação por conteúdo impróprio

> "impropérios, desenhos e outras formas propositais de anulação, o que configurará
> 'Anulada'"

### ZERO-06 — Parte deliberadamente desconectada do tema proposto

> "parte deliberadamente desconectada do tema proposto"

Ver definição detalhada em `DESCONECTADA-01` (§3).

### ZERO-07 — Identificação fora do local permitido

> "nome, assinatura, rubrica ou qualquer outra forma de identificação fora do espaço destinado
> exclusivamente para isso, em qualquer parte da folha de redação, o que configurará
> 'Anulada'"

### ZERO-08 — Predominância de língua estrangeira

> "texto escrito predominantemente ou integralmente em língua estrangeira"

### ZERO-09 — Texto ilegível

> "texto ilegível, que impossibilite sua leitura por dois(duas) avaliadores(as) independentes, o
> que configurará 'Anulada'"

Fonte de ZERO-01 a ZERO-09: física pp.9–10.

### ZERO-10 — Não atendimento ao tipo textual (reafirmação com efeito explícito)

> "Será atribuída nota 0 (zero) à redação que apresentar predominância de características de
> outro tipo textual, mesmo que atenda às exigências dos outros critérios de avaliação."

Fonte: física p.28 (quadro ATENÇÃO). Esta é a mesma regra de `ZERO-02`, reafirmada com a
consequência explícita: zero **mesmo que** as demais competências estivessem, isoladamente,
bem atendidas.

### ZERO-EFEITO-01 — Efeito de ZERO-01/ZERO-02 sobre a nota final

> "Se a sua redação apresentar fuga ao tema ou não atender ao tipo dissertativo-argumentativo,
> ela não será avaliada em nenhuma das competências e a sua nota final na prova de redação
> será 0 (zero)."

Fonte: física p.29 (quadro ATENÇÃO). **Cláusula crítica para o corretor**: fuga total e
não-atendimento ao tipo textual não são "zero na Competência II" — são zero na **redação
inteira**, sem avaliação de I, III, IV e V.

### ZERO-11 — Título anulável

O título é opcional e não é avaliado por nenhuma competência, mas **pode**, isoladamente,
levar a redação inteira à nota 0 se contiver elemento anulável (desenho, sinal gráfico sem
função evidente, impropério etc.).

Fonte: física p.11. Ver `TITULO-01`.

### ZERO-12 — Trechos de cópia não contam como texto, mas não anulam por si

> "cópia de texto(s) da Prova de Redação e/ou do Caderno de Questões terá a quantidade de
> linhas copiadas desconsiderada para a contagem da quantidade mínima de linhas."

Fonte: física p.10. Isto é uma regra de **contagem** (pode levar a `ZERO-04` indiretamente, se
o texto restante ficar em 7 linhas ou menos), não uma anulação direta por si só. Ver `COPIA-01`.

---

## 3. Partes deliberadamente desconectadas do tema (detalhe de ZERO-06)

### DESCONECTADA-01 — Definição

Consideram-se partes deliberadamente desconectadas do tema proposto:

- reflexões do(a) participante sobre o próprio processo de escrita, sobre a prova ou sobre o
  próprio desempenho no exame;
- bilhetes destinados à banca avaliadora;
- mensagens políticas ou de protesto, orações, mensagens religiosas;
- frases desconectadas do corpo do texto sem relação com o tema ou a argumentação;
- trechos de música, hino, poema ou qualquer texto **desde que desarticulados da
  argumentação** da redação.

Fonte: física pp.10–11.

### DESCONECTADA-02 — Exceção: quando NÃO configura desconexão

> "a presença de uma mensagem de protesto em um texto, por exemplo, não é,
> automaticamente, avaliada como parte desconectada. Isso vai depender do fato de a
> mensagem estar, ou não, devidamente articulada à argumentação construída ao longo da
> redação."

Condição para anulação por este critério: o elemento precisa ser inserido de forma
"**proposital, pontual e desarticulada**", como elemento estranho ao tema/projeto de texto,
e/ou atentar contra a seriedade do exame.

Fonte: física p.11. **Esta regra não é mecanicamente decidível por palavra-chave** — exige
julgamento sobre articulação argumentativa. Registrada como ambiguidade `AMB-02` no doc 12.

---

## 4. As cinco competências — definição e níveis de desempenho

Cada competência é avaliada em 6 níveis fixos: **0, 40, 80, 120, 160, 200 pontos**. As
descrições abaixo são citação literal das tabelas oficiais (física pp.16, 28, 32, 35, 39),
conferidas visualmente contra a imagem renderizada da página.

### COMP-I — Domínio da modalidade escrita formal da língua portuguesa

Enunciado oficial: *"Demonstrar domínio da modalidade escrita formal da língua
portuguesa."* (física p.7)

Aspectos avaliados, conforme física pp.12–13:

- **convenções da escrita** — acentuação, ortografia, uso de hífen, emprego de letras
  maiúsculas/minúsculas, separação silábica (translineação);
- **gramaticais** — regência verbal e nominal, concordância verbal e nominal, tempos e modos
  verbais, pontuação, paralelismos sintático/morfológico/semântico, emprego de pronomes e
  crase;
- **escolha de registro** — adequação à escrita formal, ausência de registro informal/marcas de
  oralidade;
- **escolha vocabular** — vocabulário preciso, usado em sentido correto e apropriado ao
  contexto;
- **estrutura sintática** — períodos bem estruturados e completos; para nota máxima,
  espera-se complexidade (orações subordinadas e intercaladas). Falhas típicas: truncamento
  (ponto final separando o que deveria ser uma só oração) e justaposição (vírgula no lugar de
  ponto final).

Tabela de níveis (física p.16, rodapé 14):

| Pontos | Descrição oficial |
|---|---|
| 200 | Demonstra excelente domínio da modalidade escrita formal da língua portuguesa e de escolha de registro. Desvios gramaticais ou de convenções da escrita serão aceitos somente como excepcionalidade e quando não caracterizarem reincidência. |
| 160 | Demonstra bom domínio da modalidade escrita formal da língua portuguesa e de escolha de registro, com poucos desvios gramaticais e de convenções da escrita. |
| 120 | Demonstra domínio mediano da modalidade escrita formal da língua portuguesa e de escolha de registro, com alguns desvios gramaticais e de convenções da escrita. |
| 80 | Demonstra domínio insuficiente da modalidade escrita formal da língua portuguesa, com muitos desvios gramaticais, de escolha de registro e de convenções da escrita. |
| 40 | Demonstra domínio precário da modalidade escrita formal da língua portuguesa, de forma sistemática, com diversificados e frequentes desvios gramaticais, de escolha de registro e de convenções da escrita. |
| 0 | Demonstra desconhecimento da modalidade escrita formal da língua portuguesa. |

### COMP-II — Compreensão da proposta e aplicação de conceitos das áreas de conhecimento

Enunciado oficial: *"Compreender a proposta de redação e aplicar conceitos das várias áreas
de conhecimento para desenvolver o tema dentro dos limites estruturais do texto
dissertativo-argumentativo em prosa."* (física p.7)

Conceitos-chave, física pp.14–17:

- Exige texto **dissertativo-argumentativo**: defesa de um ponto de vista por meio de
  argumentação, não mera exposição de ideias.
- **Tema**: recorte específico dentro do assunto mais amplo; tangenciar (abordar parcialmente)
  ou fugir totalmente ao tema são falhas distintas (ver `TEMA-01`, `TEMA-02`).
- **Repertório sociocultural**: informação, fato, citação ou experiência vivida relacionada ao
  tema, que funcione como argumento para a discussão — não decorada, mecânica ou "de bolso"
  (ver `REPERTORIO-01`).

Tabela de níveis (física p.28, rodapé 26; a cartilha rotula esta tabela "nas redações do Enem
2024" — provável resíduo de atualização incompleta do texto-base, sinalizado em `AMB-03`):

| Pontos | Descrição oficial |
|---|---|
| 200 | Desenvolve o tema por meio de argumentação consistente, a partir de um repertório sociocultural produtivo, e apresenta excelente domínio do texto dissertativo-argumentativo. |
| 160 | Desenvolve o tema por meio de argumentação consistente e apresenta bom domínio do texto dissertativo-argumentativo, com proposição, argumentação e conclusão. |
| 120 | Desenvolve o tema por meio de argumentação previsível e apresenta domínio mediano do texto dissertativo-argumentativo, com proposição, argumentação e conclusão. |
| 80 | Desenvolve o tema recorrendo à cópia de trechos dos textos motivadores ou apresenta domínio insuficiente do texto dissertativo-argumentativo, não atendendo à estrutura com proposição, argumentação e conclusão. |
| 40 | Apresenta o assunto, tangenciando o tema, ou demonstra domínio precário do texto dissertativo-argumentativo, com traços constantes de outros tipos textuais. |
| 0 | Fuga ao tema/não atendimento à estrutura dissertativo-argumentativa. Nestes casos a redação recebe nota 0 (zero) e é anulada. |

> Nota sobre a linha de 0 pontos desta tabela: por `ZERO-EFEITO-01` (física p.29), fuga ao tema
> e não atendimento ao tipo textual não zeram **apenas** a Competência II — zeram a redação
> inteira. A linha "0 ponto" desta tabela é, portanto, consistente com — não uma exceção a —
> `ZERO-EFEITO-01`.

#### REPERTORIO-01 — "Repertório de bolso" (não é regra de pontuação direta, é heurística de avaliação)

Repertório de bolso = referência pronta, memorizada, usada de forma genérica, decorada ou
forçada, sem conexão genuína com o tema. Prejudica a nota da Competência II quando o(a)
avaliador(a) perceber que o repertório não é produtivo. Critérios de repertório produtivo,
física p.18:

- pertinente ao assunto tratado;
- bem contextualizado e articulado com os argumentos;
- usado de modo que evidencie que o(a) participante entende o conteúdo citado e sabe
  relacioná-lo ao problema discutido.

Fonte: física pp.18–23. **Não decidível por lista fechada de referências proibidas** — a mesma
obra citada pode ser produtiva ou decorativa dependendo da articulação no texto. Registrado
como ambiguidade `AMB-04` no doc 12.

### COMP-III — Seleção, relação, organização e interpretação de informações em defesa de um ponto de vista

Enunciado oficial: *"Selecionar, relacionar, organizar e interpretar informações, fatos,
opiniões e argumentos em defesa de um ponto de vista."* (física p.7)

Conceitos-chave, física pp.29–31:

- **Projeto de texto**: planejamento prévio à escrita; organização estratégica dos argumentos.
- **Desenvolvimento**: fundamentação dos argumentos (exemplos, definições, comparações,
  analogias, estatísticas etc.), sempre relacionado ao ponto de vista.
- Fatores de inteligibilidade: seleção de argumentos; relação de sentido entre as partes;
  progressão adequada; desenvolvimento dos argumentos sem lacunas de sentido.

Tabela de níveis (física p.32, rodapé 30):

| Pontos | Descrição oficial |
|---|---|
| 200 | Apresenta informações, fatos e opiniões relacionados ao tema proposto, de forma consistente e organizada, configurando autoria, em defesa de um ponto de vista. |
| 160 | Apresenta informações, fatos e opiniões relacionados ao tema, de forma organizada, com indícios de autoria, em defesa de um ponto de vista. |
| 120 | Apresenta informações, fatos e opiniões relacionados ao tema, limitados aos argumentos dos textos motivadores e pouco organizados, em defesa de um ponto de vista. |
| 80 | Apresenta informações, fatos e opiniões relacionados ao tema, mas desorganizados ou contraditórios e limitados aos argumentos dos textos motivadores, em defesa de um ponto de vista. |
| 40 | Apresenta informações, fatos e opiniões pouco relacionados ao tema ou incoerentes e sem defesa de um ponto de vista. |
| 0 | Apresenta informações, fatos e opiniões não relacionados ao tema e sem defesa de um ponto de vista. |

### COMP-IV — Mecanismos linguísticos (coesão) necessários à construção da argumentação

Enunciado oficial: *"Demonstrar conhecimento dos mecanismos linguísticos necessários para a
construção da argumentação."* (física p.7)

Conceitos-chave, física pp.32–35:

- Diferença em relação à Competência III: III avalia a estrutura profunda (seleção/organização
  de ideias); IV avalia a superfície textual (marcas linguísticas de coesão).
- Mecanismos: operadores argumentativos (igualdade, adversidade, causa/consequência,
  conclusão); estruturação de parágrafos e períodos; **referenciação** (retomada de
  pessoas/coisas/lugares/fatos via pronomes, advérbios, artigos, sinônimos, hipônimos,
  hiperônimos, expressões resumitivas/metafóricas/metadiscursivas).
- A cartilha adverte explicitamente contra uso artificial/excessivo de conectivos apenas para
  parecer bem escrito (física p.35) — quantidade não substitui adequação lógica.

Tabela de níveis (física p.35, rodapé 33):

| Pontos | Descrição oficial |
|---|---|
| 200 | Articula bem as partes do texto e apresenta repertório diversificado de recursos coesivos. |
| 160 | Articula as partes do texto, com poucas inadequações, e apresenta repertório diversificado de recursos coesivos. |
| 120 | Articula as partes do texto, de forma mediana, com inadequações, e apresenta repertório pouco diversificado de recursos coesivos. |
| 80 | Articula as partes do texto, de forma insuficiente, com muitas inadequações, e apresenta repertório limitado de recursos coesivos. |
| 40 | Articula as partes do texto de forma precária. |
| 0 | Não articula as informações. |

### COMP-V — Proposta de intervenção respeitando os direitos humanos

Enunciado oficial: *"Elaborar proposta de intervenção para o problema abordado, respeitando
os direitos humanos."* (física p.7)

Conceitos-chave, física pp.35–38:

- A proposta precisa estar relacionada ao tema e articulada ao projeto de texto (Competência
  III).
- Elementos de uma proposta muito bem elaborada: **ação interventiva concreta** + **agente**
  (individual, familiar, comunitário, social, político, governamental) + **meio de execução** +
  **efeito/finalidade** + **detalhamento adicional**.
- Perguntas-guia oficiais: o que é possível apresentar como solução? que ação deve ser
  tomada? quem deve executá-la? como viabilizar? qual efeito ela pode alcançar? que outro
  detalhamento pode ser acrescentado?
- **Não configura proposta**: apenas constatar a falta de algo ("faltam investimentos em X")
  sem indicar ação; estruturas condicionais vagas ("se X for feito, o resultado poderá ser Y").

#### DH-01 — Princípios norteadores gerais dos direitos humanos (não específicos de tema)

Baseados no artigo 3º da Resolução nº 1 de 30/05/2012 (Diretrizes Nacionais para a Educação em
Direitos Humanos), física pp.37–38:

- dignidade humana;
- igualdade de direitos;
- reconhecimento e valorização das diferenças e diversidades;
- laicidade do Estado;
- democracia na educação;
- transversalidade, vivência e globalidade;
- sustentabilidade socioambiental.

#### DH-02 — Ideias/ações sempre avaliadas como contrárias aos direitos humanos (gerais, válidas para qualquer tema)

> "defesa de tortura, mutilação, execução sumária e qualquer forma de 'justiça com as próprias
> mãos'; incitação a qualquer tipo de violência motivada por questões de raça, etnia, gênero,
> credo, opinião política, condição física, origem geográfica ou socioeconômica; explicitação de
> qualquer forma de discurso de ódio (voltado contra grupos sociais específicos)."

Fonte: física p.37.

#### DH-03 — Aplicações específicas ao tema de 2024 (NÃO generalizáveis a outros temas)

A cartilha lista violações de direitos humanos específicas ao tema de 2024 ("Desafios para a
valorização da herança africana no Brasil"), física p.38 — ex.: negar o direito de comunidades
afro-brasileiras a professar fé de matriz africana; juízo de valor racista sobre fenótipos negros;
etc. **Estas são instanciações de `DH-01`/`DH-02` aplicadas a um tema específico, não regras
portáteis para temas futuros.** Um futuro corretor não deve tratar `DH-03` como lista fechada
geral — apenas como exemplo do padrão de raciocínio (aplicar `DH-01`/`DH-02` ao recorte
temático da prova em avaliação). Ver `AMB-05` no doc 12.

Tabela de níveis (física p.39, rodapé 37):

| Pontos | Descrição oficial |
|---|---|
| 200 | Elabora muito bem proposta de intervenção, detalhada, relacionada ao tema e articulada à discussão desenvolvida no texto. |
| 160 | Elabora bem proposta de intervenção relacionada ao tema e articulada à discussão desenvolvida no texto. |
| 120 | Elabora, de forma mediana, proposta de intervenção relacionada ao tema e articulada à discussão desenvolvida no texto. |
| 80 | Elabora, de forma insuficiente, proposta de intervenção relacionada ao tema, ou não articulada com a discussão desenvolvida no texto. |
| 40 | Apresenta proposta de intervenção vaga, precária ou relacionada apenas ao assunto. |
| 0 | Não apresenta proposta de intervenção ou apresenta proposta não relacionada ao tema ou ao assunto. |

### DH-ZERO-01 — Nota zero na Competência V por desrespeito aos direitos humanos

> "Propostas que desrespeitem os direitos humanos receberão nota 0 (zero) na Competência V."

Fonte: física p.39 (quadro ATENÇÃO). **Escopo: zera apenas a Competência V**, não a redação
inteira — diferente de `ZERO-EFEITO-01`. Confirmado também em física p.37: "as redações que
apresentarem propostas de intervenção que desrespeitem os direitos humanos serão
penalizadas na Competência V".

---

## 5. Tipo textual, fuga e tangenciamento

### TIPO-01 — Definição de texto dissertativo-argumentativo

> "aquele que se organiza com base na defesa de um ponto de vista sobre determinado
> assunto. É fundamentado com argumentos, a fim de influenciar a opinião da pessoa que lê...
> é argumentativo porque defende um ponto de vista... e é dissertativo porque utiliza
> explicações para justificá-lo."

Fonte: física pp.27–28.

### TIPO-02 — Não atendimento ao tipo textual: zero total vs. penalização parcial

> "Será atribuída nota 0 (zero) à redação que apresentar **predominância** de características
> de outro tipo textual, mesmo que atenda às exigências dos outros critérios de avaliação. Já
> redações que apresentem **muitas** características de outro tipo textual em meio a um texto
> **predominantemente** dissertativo-argumentativo não receberão a nota zero total, mas serão
> penalizadas na Competência II."

Fonte: física p.28. **Distinção central e não trivialmente decidível**: "predominância de outro
tipo" (zero total, `ZERO-10`) vs. "muitas características, mas ainda predominantemente
dissertativo-argumentativo" (penalização parcial em COMP-II, refletida na linha de 40 pontos
da tabela: "traços constantes de outros tipos textuais"). Registrado como ambiguidade `AMB-06`.

### TEMA-01 — Fuga total ao tema (definição geral + instância 2024)

Definição geral, física p.26:

> "Considera-se que uma redação tenha fugido ao tema quando nem o assunto mais amplo nem
> o tema específico proposto são desenvolvidos."

Instância 2024 (exemplo de aplicação, não regra geral portátil): tema decomposto em 4
elementos obrigatórios — Desafios + Valorização + Herança africana + Brasil; fuga = nenhum
desses elementos é abordado. Padrão de decomposição do tema em elementos é reutilizável
metodologicamente (ver `12`, §2), mas os elementos concretos mudam a cada edição.

### TEMA-02 — Tangenciamento ao tema (definição geral + instância 2024 + efeito de cap)

Definição geral, física p.27:

> "Considera-se tangenciamento ao tema uma abordagem parcial baseada somente no assunto
> mais amplo a que o tema está vinculado."

Efeito explícito sobre a nota (física p.27, quadro ATENÇÃO):

> "o tangenciamento ao tema, avaliado na Competência II, afeta também a avaliação das
> Competências III e V, impedindo que a redação receba nota acima de 40 pontos em todas
> essas competências."

**Nota**: a cláusula cita III e V; **é omissa quanto a I e IV** — não diz se o tangenciamento
também limita essas duas. Registrado como ambiguidade `AMB-07`.

---

## 6. Regras de cópia

### COPIA-01 — Desconsideração de linhas copiadas

> "Para efeito de avaliação e de contagem do mínimo de linhas escritas, os trechos que
> apresentarem cópia de texto(s) da Prova de Redação e/ou do Caderno de Questões serão
> desconsiderados em relação ao total de linhas escritas, sendo contabilizadas apenas as que
> foram produzidas pelo(a) participante. São consideradas linhas com cópia aquelas compostas,
> integral ou parcialmente, por trechos de cópia da Prova de Redação e/ou do Caderno de
> Questões."

Fonte: física p.10. Interage com `ZERO-04`: se, após desconsiderar linhas copiadas, restarem 7
linhas ou menos de produção própria, aplica-se `ZERO-04`.

### COPIA-02 — Cópia dos textos motivadores penaliza Competência II (não anula por si)

> "Não copie trechos dos textos motivadores. A recorrência de cópia é avaliada negativamente e
> fará com que sua redação tenha uma pontuação mais baixa ou, até mesmo, seja anulada como
> cópia."

Fonte: física p.17. Refletido também na tabela de COMP-II, nível 80: "Desenvolve o tema
recorrendo à cópia de trechos dos textos motivadores". A frase "seja anulada como cópia"
sugere um patamar de cópia que leva a zero, mas a cartilha não define esse patamar
numericamente. Registrado como ambiguidade `AMB-08`.

---

## 7. Título

### TITULO-01 — Regra do título

- O título é **opcional**.
- Conta como linha escrita (para fins de `ZERO-04`), mas **não é avaliado por nenhuma
  competência** da Matriz de Referência.
- **Pode**, isoladamente, levar a nota 0 (zero) à redação inteira se apresentar característica
  passível de anulação (desenhos, sinais gráficos sem função evidente, impropérios etc.) — ver
  `ZERO-11`.

Fonte: física p.11.

---

## 8. Atendimento especializado

### ATEND-01 — Participantes surdos(as) ou com deficiência auditiva

Mecanismos de avaliação coerentes com singularidades linguísticas no domínio da modalidade
escrita, conforme inciso VI do art. 30 da Lei nº 13.146/2015. Documento específico dedicado a
este público é disponibilizado separadamente pelo Inep (não incluído nesta extração — fora do
escopo do PDF fonte). Fonte: física pp.11–12.

### ATEND-02 — Participantes com dislexia

Mesma base legal; critérios que consideram características linguísticas específicas à dislexia.
Documento específico dedicado disponibilizado separadamente pelo Inep. Fonte: física p.12.

### ATEND-03 — Participantes com Transtorno do Espectro Autista (TEA)

Desde 2020, avaliadas por banca especializada; mesma base legal (Lei nº 13.146/2015, art. 30,
inciso VI). Documento específico dedicado disponibilizado separadamente pelo Inep. Fonte:
física p.12.

### ATEND-04 — Condição de aplicação

Estes três regimes só se aplicam quando "o documento, declaração ou parecer que motivou a
solicitação de atendimento especializado tenha sido aprovado" — ou seja, dependem de
aprovação prévia fora do momento de correção da redação em si. Fonte: física p.11.

---

## 9. Seções referenciadas, não extraídas (ponteiros)

| Id | Seção da cartilha | Páginas físicas | Por que não foi extraída |
|---|---|---|---|
| `LEITURA-GUIADA-REF` | Leitura guiada da proposta 2024 | 40–41 | Aplica regras já extraídas (§2–§8) a um exemplo concreto; não introduz regra nova. |
| `AMOSTRA-REF` | Amostra de Redações (10 textos com comentário) | 42–72 | Comentários qualitativos, sem nota numérica por competência atribuída no texto; não computável sem trabalho adicional de anotação humana. |
| `LEIAMAIS-REF` | Leia Mais, Seja Mais | 73–75 | Recomendação de leitura; não é critério de correção. |

---

## 10. Changelog

| TX | Timestamp | Classe | Alteração | Autoriza | Co-alterados |
|---|---|---|---|---|---|
| `TX-2026-08-24T151820Z-enem-canon-v1` | 2026-08-24T15:18:20Z | — (criação) | Criação do documento, extração OCR local conferida visualmente para as 5 tabelas de competência | Pedido do usuário, 2026-08-24 | `12 ENEM 2025 - Matriz de Correcao Estruturada.md`, `13 enem_regras_computaveis.json`, `README.md` (mesmo diretório) |

_Pendência registrada:_ nenhuma Transação Documental foi aberta em `pipeline/docs/auditoria/`
porque esse diretório ainda não existe no corpus (mesma lacuna já registrada para os nove
documentos legados sob `G-CONF-01` em GOV-1.0 §13.2). O changelog acima é, por ora, o único
registro da transação.
