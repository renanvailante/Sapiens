# `pipeline/docs/enem-redacao/` — canon de apoio externo (Enem, correção de redação)

> **Índice de navegação, não norma.** Este README não decide nada; em qualquer divergência
> entre ele e os documentos que lista, prevalece o documento.

## Por que este diretório existe e por que não é normativo

`00 Governanca e Versionamento Sapiens v1.0.md` (GOV-1.0) §1.1 declara, nomeando literalmente
o Enem como exemplo:

> "Material externo (por exemplo, a Matriz de Referência do ENEM) é **apoio**, nunca fonte de
> categorias. Deve residir fora de `pipeline/docs/` ou, se residir dentro, portar
> `estado: apoio_externo` e uma declaração explícita de não-normatividade."

Este diretório é exatamente essa segunda opção. Nenhum documento aqui define, altera ou
influencia qualquer Domínio, Competência, Processo, Habilidade ou Tipo de Erro do catálogo
C1–C5 do Sapiens (Ontologia Cognitiva, White Paper, Constituição, Manual, Schema, Behavior,
Error Trace). São dois sistemas de avaliação completamente distintos: o Sapiens categoriza
cognição sobre **questões objetivas**; este canon organiza os critérios oficiais do Inep/MEC
para correção de **redação dissertativo-argumentativa**.

## O que existe aqui

| Documento | Papel | Camada GOV-1.0 |
|---|---|---|
| [`11 Cartilha ENEM 2025 - Extracao da Fonte Oficial.md`](11%20Cartilha%20ENEM%202025%20-%20Extracao%20da%20Fonte%20Oficial.md) | **Fonte oficial** — extração estruturada e rastreável (página física do PDF) do conteúdo normativo da cartilha do Inep. Nenhuma regra nova; apenas organização do que a cartilha já diz. | apoio_externo |
| [`12 ENEM 2025 - Matriz de Correcao Estruturada.md`](12%20ENEM%202025%20-%20Matriz%20de%20Correcao%20Estruturada.md) | **Interpretação documental** — organiza a fonte em um pipeline de decisão (elegibilidade → pontuação por competência) e registra 9 ambiguidades da fonte oficial, sem resolvê-las por conta própria. | apoio_externo |
| [`13 enem_regras_computaveis.json`](13%20enem_regras_computaveis.json) | **Regras computáveis** — mesmo conteúdo do doc 12 em formato de máquina, pronto para um futuro corretor consumir sem reparsing de Markdown. Forma um **Conjunto Normativo Indivisível (CNI)** com o doc 12 (GOV-1.0 §4.2): prosa é autoridade sobre critério/justificativa, JSON é autoridade sobre estrutura/valores. | apoio_externo |

**Cadeia de precedência dentro deste diretório**: 11 (fonte) → 12+13 (interpretação, CNI). Em
qualquer divergência entre 12/13 e 11, prevalece 11. Isso espelha a regra geral de
`pipeline/docs/README.md`: "em qualquer divergência entre esta página e o documento que ela
lista, prevalece o documento".

## Proveniência da fonte

```
Arquivo:  a_redacao_no_enem_2025_cartilha_do_participante.pdf
Editora:  INEP/MEC — Diretoria de Avaliação da Educação Básica (DAEB)
Publicado: setembro de 2025
Páginas:  78
SHA-256:  d8ab44dcbf5af808829d9dee89d23e7efa4f59df022b99102fac87489b870288
Licença declarada na fonte: "É permitida a reprodução total ou parcial desta publicação,
                              desde que citada a fonte."
```

## Como foi extraído (100% local, sem API paga)

O PDF usa uma fonte embutida (Adobe Illustrator, PDF/X-1) com cmap customizado que corrompe
acentuação e ligaduras quando extraído por `pdftotext` puro. Para não comprometer a fidelidade
do canon, a extração usou:

1. `poppler-utils` (`pdftoppm -r 300 -png`) — renderização local das 78 páginas em imagem.
2. `tesseract` 5.5.3, idioma `por` — OCR local, sem serviço externo nem chamada paga.
3. **Conferência visual manual** das 5 tabelas de níveis de desempenho (Competências I–V)
   diretamente contra a imagem renderizada — porque o OCR (modo psm 6) omitiu linhas de
   tabela em várias páginas, e essas tabelas são o núcleo das regras computáveis.

Nenhum modelo de linguagem externo, API paga ou serviço de terceiros foi usado nesta etapa,
conforme exigido pela tarefa.

## Principais regras extraídas (resumo — ver doc 11/12/13 para o texto completo)

- **Escala**: 5 competências × 0–200 pontos (múltiplos de 40) = nota total 0–1.000.
- **Dois avaliadores independentes**; discrepância = diferença total > 100 ou diferença em
  qualquer competência > 80; resolução por 3º avaliador e, se persistir, banca de 3.
- **11 gatilhos de nota zero na redação inteira** (fuga ao tema, não-atendimento ao tipo
  textual, texto em branco, texto insuficiente, anulação por conteúdo impróprio, parte
  desconectada do tema, identificação fora do local, língua estrangeira predominante, texto
  ilegível, predominância de outro tipo textual, título anulável) — todos zeram a prova
  inteira, não uma competência isolada.
- **1 gatilho de zero localizado**: proposta de intervenção que desrespeita direitos humanos
  zera apenas a Competência V.
- **Tangenciamento ao tema** limita Competências II, III e V a no máximo 40 pontos (efeito
  sobre I e IV não é explicitado pela fonte — ambiguidade registrada).

## Lacunas e ambiguidades encontradas (não resolvidas por este canon)

9 ambiguidades registradas em `12 ENEM 2025 - Matriz de Correcao Estruturada.md` §3 e
espelhadas em `13 enem_regras_computaveis.json.ambiguidades`, entre elas:

- limite exato de "texto insuficiente";
- fronteira entre "predominância de outro tipo textual" (zero total) e "traços" (penalização
  parcial) sem limiar quantitativo;
- silêncio da fonte sobre se o cap de tangenciamento se aplica às Competências I e IV;
- a seção "Amostra de Redações" (10 textos comentados, física pp.42–72) **não contém nota
  numérica por competência** — só comentário qualitativo — logo não gera dados de calibração
  para um modelo de correção;
- exemplos de violação de direitos humanos e de decomposição temática da cartilha são
  específicos ao tema de 2024 e **não são portáteis** para futuras edições do Enem — o método
  é reutilizável, os elementos concretos não são.

Nenhuma ambiguidade foi resolvida por inferência silenciosa. Uma implementação futura que
precisar de uma decisão operacional deve declarar essa decisão explicitamente como convenção
de engenharia, citando o `AMB-xx` correspondente.

## Testes e validações realizados nesta rodada

- `pdfinfo` confirmou 78 páginas físicas no PDF fonte, consistentes com a extração.
- As 5 tabelas de níveis de desempenho (Competências I–V) foram lidas visualmente da imagem
  renderizada (não apenas do OCR) e cada uma confirmada com exatamente 6 níveis
  (0/40/80/120/160/200 pontos), batendo com a "escala de 6 níveis" que o texto da cartilha
  anuncia antes de cada tabela.
- `13 enem_regras_computaveis.json` foi validado sintaticamente (`python3 -m json.load`) e
  verificado estruturalmente: 5 competências, 6 níveis cada, 9 ambiguidades, 11 gatilhos de
  zero-redação-inteira + 1 gatilho de zero-localizado.
- Checksum SHA-256 do PDF fonte registrado nos três documentos para permitir detectar, no
  futuro, se uma nova edição da cartilha substituiu o arquivo sem atualização deste canon.

## Como este canon deve ser consumido por um futuro corretor

1. Ler `13 enem_regras_computaveis.json` para estrutura/valores; ler
   `12 ENEM 2025 - Matriz de Correcao Estruturada.md` para o raciocínio por trás de cada regra
   e para a lista de ambiguidades a resolver antes de produção.
2. Implementar a Etapa 0 (elegibilidade) como curto-circuito **antes** de qualquer pontuação
   por competência — não como pós-processamento.
3. Fornecer, a cada correção, o tema/proposta específico daquela edição do Enem — este canon
   não contém e não pode conter os elementos temáticos de edições futuras.
4. Tratar cada `AMB-xx` não resolvido como uma decisão de produto pendente, não como algo que
   a IA de correção deve inferir silenciosamente.
5. Buscar fonte adicional (gabaritos oficiais do Inep com nota publicada, ou anotação humana
   especializada) se for necessário treinar/calibrar um modelo numericamente — este canon não
   contém pares texto→nota.

**Este canon não implementa correção alguma.** É a base documental sobre a qual uma etapa
futura, fora do escopo desta tarefa, poderia construir um corretor assistido por IA.
