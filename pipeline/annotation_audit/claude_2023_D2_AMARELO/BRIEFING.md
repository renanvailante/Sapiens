# Anotação independente (Claude) — ENEM 2023, 2º Dia, Caderno 5 Amarelo

## O que é este trabalho

Você vai anotar cognitivamente um subconjunto de questões (91 a 180) do caderno
`cadernos enem/2023_PV_impresso_D2_CD5.pdf`, seguindo **exatamente** o Schema
Sapiens 2.2 e a Ontologia Cognitiva Sapiens v1.4.1 já existentes no
repositório — os mesmos que o pipeline de produção usa para instruir o
Gemini. Esta é uma anotação **independente**: você não vai consultar, copiar
ou se inspirar nas anotações que o Gemini já produziu para este mesmo
caderno (armazenadas em MongoDB, coleção `questoes_master`/`questoes_public`
do banco `sapiens_pipeline`/`sapiens_aluno`, ou nos arquivos de
`pipeline/backend/_storage/`). **Não rode `mongosh`, não leia nada dessas
coleções ou pastas, não abra o Firestore.** Sua única fonte de conteúdo da
prova é o PDF (via os recortes/imagens gerados abaixo). Isso será auditado
depois por comparação — o valor deste trabalho está exatamente em ser
independente.

## Fontes obrigatórias de regras (leia antes de anotar)

1. `pipeline/backend/cognitive_engine.py` — leia principalmente:
   - a constante `DEFAULT_PIPELINE_SCHEMA` (o formato de saída exato, campo a
     campo);
   - a string `_SYSTEM_PROMPT_TEMPLATE` (as regras de classificação
     vinculantes — ordem obrigatória de decisão, processo dominante, papel e
     peso, habilidades, tipos de erro, cadeia de erro ordenada, confiança
     obrigatória, mecanismo opcional, intervenções, regra de `fonte`, proibição
     de anotar domínio/competência diretamente, proibição de inventar ID).
   Essas regras são vinculantes para você exatamente como são para o motor
   Gemini — é o mesmo contrato.
2. `pipeline/docs/ontology/ontology_v1.4.json` — **única fonte autorizada de
   IDs**: 11 domínios, 25 processos cognitivos, 12 competências, 56
   habilidades observáveis, 13 tipos de erro, 11 intervenções pedagógicas.
   NUNCA invente um ID. Se nada couber com exatidão, use lista vazia ou a
   sentinela apropriada.
3. `pipeline/docs/error-trace/10 Especificacao do Error Trace v1.0.md` —
   tabela do vocabulário `MEC-01`..`MEC-13` (mecanismo, campo opcional em
   `erros_esperados[].mecanismo`).
4. `pipeline/backend/item_contract.py` e `pipeline/backend/ontology_validator.py`
   — o normalizador e o validador determinístico REAIS de produção. Você vai
   rodar seu item através deles (script pronto abaixo) — não precisa (e não
   deve) calcular `item_id`, `item_hash`, `ontology_version`, nem
   `estrutura_cognitiva.dominios`/`.competencias` manualmente: esse código
   deriva tudo isso a partir do que você produzir em `estrutura_cognitiva.processos`.

## O que você PRODUZ por questão (o que o normalizador NÃO calcula sozinho)

Um dict Python/JSON com estas chaves (ver `DEFAULT_PIPELINE_SCHEMA` para a
forma exata de cada uma):

- `fonte`: `banca`, `ano`, `prova`, `numero`, `disciplina`, `tema`,
  `conteudo`, `arquivo_origem`, `pagina`. Copie SOMENTE o que está
  literalmente impresso na página (Manual, regra de `fonte`) — banca=ENEM
  (a página de rosto imprime por extenso "Exame Nacional do Ensino Médio"),
  ano=2023, prova=AMARELO (impresso no rodapé e no código de barras), esses
  três são seguros de preencher. `disciplina` é o cabeçalho de bloco impresso
  na página (ex.: "Ciências da Natureza e suas Tecnologias" ou "Matemática e
  suas Tecnologias" — CONFIRA na imagem da sua questão, não assuma).
  `arquivo_origem` = `"2023_PV_impresso_D2_CD5.pdf"`. `pagina` = o campo
  `pagina` do manifesto (1-based). `tema`/`conteudo` são sua síntese do
  assunto da questão (ex.: tema="Ondulatória", conteudo="Velocidade de
  propagação de ondas mecânicas").
- `questao.enunciado`: texto integral e fiel. Transcreva lendo a IMAGEM do
  recorte (fonte de verdade visual) — pode usar `raw_text` do manifesto como
  apoio para não errar palavra, mas a imagem manda em caso de conflito,
  ordem, ou se o texto extraído parecer cortado/embaralhado.
- `questao.alternativas`: lista de 5 (`A`..`E`) com `letra`, `texto`,
  `correta`. Determine `correta` RESOLVENDO a questão você mesmo (é isso que
  o motor Gemini também faz — não há gabarito oficial impresso no PDF). Se
  genuinamente não conseguir determinar com segurança, marque as 5 como
  `null` e registre isso no arquivo de limitações (seção abaixo) — nunca
  chute só para preencher.
- `questao.recursos`: `imagens[]`, `graficos[]`, `tabelas[]`, `formulas[]`.
  **Preste atenção especial aqui.** Se a questão tem gráfico, tabela, mapa,
  diagrama, tirinha, fórmula estrutural, foto — registre em
  `imagens[]`/`graficos[]`/`tabelas[]`/`formulas[]` com `id` (`IMG-01`,
  `GRA-01`, `TAB-01`, `FOR-01`), `tipo`, `descricao` fiel do que a imagem
  mostra (não apenas "gráfico"), e para `imagens[]` também `arquivo` = o
  caminho relativo do recorte que você usou (ex.:
  `"crops/Q114.png"` — path relativo à raiz deste diretório de auditoria,
  para preservar a relação item_id → página → imagem/asset) e `ocr` = texto
  visível DENTRO da própria figura (rótulos de eixo, valores, legendas — não
  o enunciado). Uma questão com elemento visual que participa do raciocínio
  NUNCA deve ficar registrada como se fosse só texto.
- `estrutura_cognitiva.processos[]`: 1 ou 2 processos (nunca mais — se um 3º
  genuinamente passar no teste de necessidade, registre os 2 mais fortes e
  acrescente `"tres-ou-mais-processos-necessarios"` em
  `incerteza.marcadores`). Cada processo: `id`, `papel`
  (`nuclear`|`secundario`), `peso_no_item` (1.0 solo; 0.7/0.3 se dois),
  `confianca` (`alta`|`media`|`baixa`), `habilidades[]` (só do catálogo do
  processo, com `peso_no_processo`, `confianca`, `aproximado`),
  `evidencias.trechos[]` (trecho literal do enunciado/alternativa),
  `evidencias.figuras[]` (IDs de `IMG-*` relevantes, se houver),
  `justificativa` (obrigatória no nuclear, 1-2 frases reproduzíveis por outro
  anotador). **NÃO preencha `estrutura_cognitiva.dominios` nem
  `.competencias`** — o script de validação deriva isso.
- `incerteza`: `marcadores[]` (vocabulário fechado — ver lista no
  `ontology_validator.py`, `MARCADORES_INCERTEZA`), `detalhe`,
  `requer_arbitragem` (bool).
- `distratores[]`: uma entrada por alternativa INCORRETA (4 por questão, ou
  todas as 5 sem correção se `correta` ficou `null` em todas — nesse caso não
  há "alternativa correta" definida; ainda assim analise as 4 mais plausíveis
  como distratoras candidatas, ou registre a limitação). Cada uma:
  `alternativa`, `erros_esperados[]` (1 a 3 elos ORDENADOS, `ordem` contígua
  desde 1, `erro` = ID do catálogo VINCULADO ao `processo_afetado` [use
  `erro-nao-catalogado-nesta-versao` se o processo não tem erro catalogado, ou
  `sem-mecanismo-cognitivo-identificavel` se é descuido/digitação — NUNCA
  empreste erro de outro processo], `processo_afetado` = ID de processo,
  `confianca` OBRIGATÓRIA em cada elo, `mecanismo` opcional `MEC-01..13`),
  `plausibilidade.valor` (`alta`|`media`|`baixa`), `probabilidade_estimada`
  (pode ser `null`), `explicacao`.
- `intervencoes[]`: selecionada a partir do elo de `ordem: 1` de cada cadeia
  de erro (nunca do último elo), `id` = INT do catálogo, `gatilho.processo`,
  `gatilho.erro`, `acao`, `prioridade` (pode ser `null`).
- `pedagogia`: `estrategia`, `passos[]`, `erros_comuns[]`, `dicas[]`,
  `tempo_estimado_segundos` (pode ser `null`), `nivel_dificuldade`
  (`facil`|`medio`|`dificil`).
- `qualidade`: `confianca_global` (`alta`|`media`|`baixa`), `revisado`:
  sempre `false` (nenhuma revisão humana ocorreu), `observacoes` (notas sobre
  limites de leitura — NUNCA usar para registrar incerteza cognitiva, isso é
  o bloco `incerteza`).

## Como validar (rode antes de considerar uma questão pronta)

Um item já normalizado por você deve passar por:

```bash
cd /Users/renanvailante/Documents/Projetos/Sapiens/pipeline/backend
source .venv/bin/activate
python3 /Users/renanvailante/Documents/Projetos/Sapiens/pipeline/annotation_audit/claude_2023_D2_AMARELO/validar_item.py <numero_da_questao>
```

Esse script lê `items/Q<numero>_raw.json` (o que VOCÊ escreve — só os campos
da seção anterior, SEM `item_id`/`item_hash`/`schema_version`/
`ontology_version`/dominios/competencias derivados), roda `normalize_item` +
`validate_item_annotation` (o código REAL de produção, sem alteração), e
escreve o resultado NORMALIZADO E VALIDADO em `items/Q<numero>.json` — esse é
o arquivo final. Se `valid: false`, o script imprime os erros: corrija
`Q<numero>_raw.json` e rode de novo. NÃO edite manualmente o `.json` final
(sem sufixo `_raw`) — ele é sempre gerado pelo script.

## Verificação visual obrigatória

Para CADA questão do seu lote, abra (via Read, é uma imagem) o recorte em
`crops/Q<numero>.png` listado no manifesto
(`manifest_extracao.json` — filtre pelo campo `numero`). Se o recorte
parecer cortado, sem alguma alternativa, ou com uma figura pela metade,
abra também `pages_full/page_<pagina>.png` (a página inteira) para conferir
o contexto — o recorte pode ter perdido algo por causa de layout em coluna.
Nunca finalize uma questão sem ter olhado a imagem.

## O que registrar como limitação (não corrija silenciosamente)

Se uma questão não puder ser anotada com segurança — enunciado ilegível,
figura essencial não recuperável do PDF, ambiguidade irresolúvel sobre qual
processo é nuclear, gabarito genuinamente indeterminável — **não invente uma
resposta plausível para preencher a lacuna**. Registre em
`NOTAS_LIMITACOES_<primeiro>_<ultimo>.md` (nome com o range do seu lote, ex.
`NOTAS_LIMITACOES_91_100.md`) uma entrada por questão problemática: número,
o que não pôde ser determinado, e por quê. A questão ainda deve ser
salva (com os campos que PUDEREM ser preenchidos com segurança e `null`/lista
vazia onde não puder), passando pela validação estrutural mesmo assim.

## Saída esperada do seu lote

- `items/Q<numero>.json` para cada questão do seu range (gerado pelo script
  de validação, um por questão).
- `NOTAS_LIMITACOES_<primeiro>_<ultimo>.md` (pode ficar vazio/só o
  cabeçalho se nenhuma limitação ocorreu).

Não toque em nenhum outro arquivo do repositório. Não faça `git add`/`commit`.
Não escreva em nenhuma coleção do MongoDB nem no Firestore.
