<!-- SUPERSEDED — declaracao exigida por GOV-1.0 §8.1 (declaracao bidirecional)
estado: superseded
versao_arquivada: 2.1
superseded_by: SCH-2.2 (mesmo caminho, schema_version 2.2)
transacao_de_supersessao: TX-2026-08-17T174625Z-schema-v2.2
transacao_de_arquivamento: TX-2026-08-21T000000Z-migracao-corpus-para-canonico
Este documento NAO pode ser citado como norma. Permanece citavel apenas
para proveniencia (GOV-1.0 §8.4). O conteudo abaixo esta INALTERADO.
-->

{
  "schema_version": "Versão semântica do contrato deste objeto, '2.1'. Não confundir com a versão da ontologia.",

  "item_id": "Identificador único e estável da questão. Deve permanecer invariável entre pipeline, Firestore, aluno e professor. Recomenda-se um formato determinístico baseado em fonte, ano, prova e número, por exemplo 'ITEM-ENEM-2024-CAD01-Q023'.",

  "item_hash": "Hash determinístico do conteúdo canônico do item usado para detectar alterações. Deve mudar quando o conteúdo estrutural relevante da questão mudar.",

  "fonte": {
    "banca": "Instituição responsável pela elaboração ou aplicação da prova, por exemplo 'INEP'.",
    "ano": "Ano de aplicação da prova, como número inteiro, por exemplo 2024.",
    "prova": "Identificador estável da prova ou caderno, incluindo versão quando necessário, por exemplo 'ENEM-CAD01'.",
    "numero": "Número original da questão na prova, como número inteiro.",
    "disciplina": "Disciplina ou área curricular associada à questão, conforme a taxonomia de origem.",
    "tema": "Tema principal explicitamente identificado na questão, quando disponível.",
    "conteudo": "Conteúdo curricular específico mobilizado pela questão, quando identificável.",
    "arquivo_origem": "Nome ou identificador do arquivo original utilizado como fonte da questão.",
    "pagina": "Número da página no arquivo original em que a questão aparece."
  },

  "questao": {
    "enunciado": "Texto integral e fiel da questão, preservando a informação necessária para sua resolução.",
    "alternativas": [
      {
        "letra": "Identificador textual da alternativa, por exemplo 'A', 'B', 'C', 'D' ou 'E'.",
        "texto": "Texto integral e fiel da alternativa.",
        "correta": "Booleano indicando se esta alternativa corresponde ao gabarito oficial. Deve ser preenchido apenas quando o gabarito for conhecido e validado."
      }
    ],
    "recursos": {
      "imagens": [
        {
          "id": "Identificador estável do recurso visual dentro do item, por exemplo 'IMG-01'.",
          "tipo": "Classificação do recurso visual, por exemplo fotografia, ilustração, mapa, diagrama, gráfico ou outro.",
          "descricao": "Descrição objetiva do conteúdo visual relevante para a interpretação da questão, sem inferir informações que não estejam presentes.",
          "arquivo": "Nome ou caminho lógico do arquivo do recurso visual armazenado.",
          "ocr": "Texto efetivamente extraído do recurso visual por OCR, quando houver; usar string vazia quando não houver texto."
        }
      ],
      "graficos": [
        {
          "id": "Identificador estável do gráfico dentro do item.",
          "descricao": "Descrição objetiva das variáveis, eixos, legendas, tendências ou relações apresentadas no gráfico."
        }
      ],
      "tabelas": [
        {
          "id": "Identificador estável da tabela dentro do item.",
          "descricao": "Descrição objetiva da estrutura e das informações relevantes apresentadas na tabela."
        }
      ],
      "formulas": [
        {
          "id": "Identificador estável da fórmula dentro do item.",
          "latex": "Representação da fórmula em LaTeX, preservando sua estrutura matemática original."
        }
      ]
    }
  },

  "estrutura_cognitiva": {
    "dominios": [
      {
        "id": "ID exato do domínio existente na ontologia canônica vigente.",
        "peso_no_item": "Peso relativo do domínio na interpretação cognitiva do item, normalizado conforme a regra definida pelo contrato.",
        "confianca": "Confiança da classificação do domínio, em escala e formato definidos pelo contrato."
      }
    ],

    "competencias": [
      {
        "id": "ID exato da competência existente na ontologia canônica vigente.",
        "peso_no_item": "Peso relativo da competência no item, segundo a regra de ponderação definida pelo contrato.",
        "confianca": "Confiança da classificação da competência, em escala e formato definidos pelo contrato."
      }
    ],

    "processos": [
      {
        "id": "ID exato do processo cognitivo existente na ontologia canônica vigente.",
        "papel": "Papel do processo no item, usando exclusivamente os valores permitidos pelo contrato, por exemplo 'nuclear' ou 'secundario'.",
        "peso_no_item": "Peso relativo do processo na resolução do item, conforme regra de normalização definida pelo contrato.",
        "confianca": "Confiança na identificação do processo cognitivo, em escala e formato definidos pelo contrato.",
        "dificuldade_local": "Dificuldade específica associada à mobilização deste processo neste item, distinguindo-a da dificuldade psicométrica global.",
        "habilidades": [
          {
            "id": "ID exato da habilidade existente na ontologia canônica vigente.",
            "peso_no_processo": "Peso relativo da habilidade dentro deste processo, conforme regra de ponderação definida pelo contrato.",
            "confianca": "Confiança na associação da habilidade ao processo e ao item."
          }
        ],
        "evidencias": {
          "trechos": [
            "Trecho literal e suficientemente específico do enunciado ou alternativa que sustenta a classificação cognitiva."
          ],
          "figuras": [
            "IDs dos recursos visuais que constituem evidência necessária para a classificação."
          ]
        },
        "justificativa": "Justificativa objetiva e curta explicando por que o processo foi classificado desta forma, fundamentada nas evidências registradas."
      }
    ]
  },

  "distratores": [
    {
      "alternativa": "Letra da alternativa incorreta analisada.",
      "erro": "ID exato do erro cognitivo existente na ontologia canônica vigente.",
      "plausibilidade": "Classificação da plausibilidade do distrator usando exclusivamente os valores permitidos pelo contrato.",
      "probabilidade_estimada": "Estimativa quantitativa da probabilidade de escolha do distrator, expressa em escala previamente definida e distinguindo estimativa do modelo de medida empírica.",
      "processos_afetados": [
        "IDs dos processos cognitivos canônicos cuja execução inadequada pode produzir este erro."
      ],
      "explicacao": "Explicação do mecanismo cognitivo que torna a alternativa incorreta atraente ou plausível."
    }
  ],

  "intervencoes": [
    {
      "id": "ID exato da intervenção existente na ontologia canônica vigente.",
      "gatilho": {
        "processo": "ID do processo cognitivo canônico associado ao gatilho.",
        "erro": "ID do erro cognitivo canônico associado ao gatilho."
      },
      "acao": "Descrição da estratégia pedagógica correspondente à intervenção canônica.",
      "prioridade": "Prioridade relativa da intervenção segundo regra definida pelo contrato."
    }
  ],

  "pedagogia": {
    "estrategia": "Estratégia geral e cognitivamente justificável para resolver a questão.",
    "passos": [
      "Sequência ordenada de operações necessárias para chegar à resposta, sem revelar informação além do necessário ao propósito pedagógico."
    ],
    "erros_comuns": [
      "Erros previsíveis que um aluno pode cometer durante a resolução, preferencialmente relacionados aos erros cognitivos da ontologia quando aplicável."
    ],
    "dicas": [
      "Orientações pedagógicas que ajudam o aluno a executar a estratégia sem simplesmente fornecer a resposta."
    ],
    "tempo_estimado_segundos": "Tempo estimado para resolução em segundos, acompanhado pela metodologia ou fonte da estimativa quando disponível.",
    "nivel_dificuldade": "Classificação qualitativa da dificuldade pedagógica estimada do item, usando exclusivamente os valores definidos pelo contrato."
  },

  "psicometria": {
    "dificuldade_empirica": "Índice de dificuldade calculado a partir de dados reais de resposta, com definição estatística explícita.",
    "discriminacao": "Índice de discriminação calculado a partir de dados reais de resposta, especificando o método utilizado.",
    "taxa_acerto": "Proporção ou percentual de respostas corretas observadas na população e janela temporal especificadas.",
    "tempo_medio": "Tempo médio observado para resolução, em segundos, calculado a partir de dados reais e acompanhado da população e janela temporal utilizadas."
  },

  "pipeline": {
    "modelo": "Identificador exato do modelo de IA utilizado na anotação, incluindo provedor e versão quando relevante.",
    "versao_prompt": "Versão identificável do prompt ou conjunto de prompts utilizado para produzir a anotação.",
    "versao_pipeline": "Versão do pipeline responsável pelo processamento do item.",
    "tokens_entrada": "Quantidade de tokens efetivamente processados como entrada pelo modelo, quando disponível.",
    "tokens_saida": "Quantidade de tokens efetivamente gerados pelo modelo, quando disponível.",
    "tempo_processamento_segundos": "Tempo total de processamento do item nesta execução, em segundos.",
    "necessita_revisao": "Booleano indicando se o item foi sinalizado para revisão humana."
  },

  "qualidade": {
    "confianca_global": "Confiança global atribuída à anotação, segundo escala definida pelo contrato.",
    "revisado": "Booleano indicando se houve revisão humana.",
    "revisor": "Identificador do responsável pela revisão humana, quando houver.",
    "observacoes": "Observações adicionais relevantes para auditoria, revisão ou interpretação da anotação."
  }
}