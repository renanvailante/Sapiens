<!-- SUPERSEDED — declaracao exigida por GOV-1.0 §8.1 (declaracao bidirecional)
estado: superseded
versao_arquivada: 1.0
superseded_by: BEH-1.1 (mesmo caminho, schema_version 1.1)
transacao_de_supersessao: TX-2026-08-17T174626Z-behavior-v1.1
transacao_de_arquivamento: TX-2026-08-21T000000Z-migracao-corpus-para-canonico
Este documento NAO pode ser citado como norma. Permanece citavel apenas
para proveniencia (GOV-1.0 §8.4). O conteudo abaixo esta INALTERADO.
-->

{
  "schema_version": "Versão do schema deste evento de behavior.",

  "event_id": "Identificador único e imutável deste evento de interação.",
  "attempt_id": "Identificador único da tentativa à qual este evento pertence.",

  "student_id": "Identificador único do aluno que realizou a interação.",
  "item_id": "Identificador único da questão/item respondido.",

  "item_schema_version": "Versão do schema utilizada pelo item no momento em que a interação ocorreu.",
  "item_hash": "Hash criptográfico do conteúdo canônico do item no momento da resposta, permitindo identificar exatamente a versão do item utilizada.",

  "timestamp": "Data e hora em que a interação foi finalizada, em formato ISO 8601 e com timezone.",

  "contexto": {
    "tipo": "Tipo de atividade em que o item foi respondido, conforme os valores definidos pelo contrato canônico do Sapiens.",
    "prova_id": "Identificador único da avaliação, prova ou atividade à qual o item pertence, quando aplicável.",
    "origem": "Origem ou fonte do item, conforme os valores definidos pelo contrato canônico do Sapiens."
  },

  "resposta": {
    "alternativa_escolhida": "Identificador da alternativa selecionada pelo aluno.",
    "acertou": "Resultado da correção da resposta, calculado exclusivamente pelo backend a partir do item e de seu gabarito canônicos."
  },

  "desempenho": {
    "tempo_resposta_segundos": "Tempo decorrido, em segundos, entre o início da interação e sua finalização.",
    "numero_tentativas": "Número ordinal da tentativa do aluno para responder este item dentro do contexto da atividade.",
    "mudou_resposta": "Indica se o aluno alterou a alternativa selecionada antes de finalizar a resposta."
  },

  "status": "Estado da interação no ciclo de resposta, utilizando exclusivamente os valores definidos pelo contrato canônico do Sapiens.",

  "metadados": {
    "dispositivo": "Tipo de dispositivo utilizado pelo aluno no momento da interação.",
    "versao_aplicacao": "Versão da aplicação responsável por registrar o evento."
  }
}