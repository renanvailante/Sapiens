Nada foi alterado.

## Leitura obrigatória (6)

| #   | Documento                                                   | Por quê                                                                                                                                |
| --- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `00 Governança e Versionamento v1.0`                        | Define precedência entre documentos, estados e versionamento — sem isso o Claude Code não sabe qual arquivo manda quando dois divergem |
| 2   | 11 `ontology_v1.4.json`                                     | O catálogo executável: 128 IDs. É o seed data de qualquer banco                                                                        |
| 3   | `06 Schema Sapiens 2.1.json.md` (v**2.2**)                  | Contrato do item anotado — a estrutura de dados central do app de anotação                                                             |
| 4   | `07 behavior student 1.4.md` (v**1.1**)                     | Contrato do evento de resposta — a estrutura de dados do app do aluno                                                                  |
| 5   | `10 Especificação do Error Trace v1.0`                      | Contrato do objeto diagnóstico, produzido em runtime; não está em nenhum dos dois acima                                                |
| 6   | `auditoria/2026-08-17T190000Z_resumo-consolidado-sessao.md` | O que mudou nesta sessão e qual é a versão vigente de cada artefato                                                                    |

**Regra crítica que o Claude Code precisa absorver dos itens 3–5:** `ontology_version` é obrigatório em todo objeto persistido, e `distratores[].erro` (ID único) **não existe mais** — virou `erros_esperados[]` ordenado com confiança obrigatória.

## Leitura recomendada (4)

| #   | Documento                                   | Por quê                                                                                                                                   |
| --- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 7   | `05 Ontologia … v1.4.md`                    | O catálogo em prosa, com o critério de cada nó — necessário para escrever prompts de anotação por IA                                      |
| 8   | `01 Manual … v1.2` (em `pipeline/docs/`)    | Regras de anotação: ordem de decisão, pesos 0.7/0.3, máx. 2 processos, vocabulário de incerteza. É a lógica de negócio do app de anotação |
| 9   | `09 Mapa de Rastreabilidade de IDs`         | 9 colisões de namespace. Impede migração automática errada de dados legados                                                               |
| 10  | `02 Constituicao Sapiens v1.1`, Caps. 4 e 5 | Relações permitidas e proibidas — o modelo relacional do banco                                                                            |

## Leitura apenas se necessário (3)

| #   | Documento                                         | Quando                                                              |
| --- | ------------------------------------------------- | ------------------------------------------------------------------- |
| 11  | `03 White Paper v2.0.1`                           | Só para entender _por que_ o sistema é assim. Não contém contrato   |
| 12  | `auditoria/…auditoria-integral-corpus-sapiens.md` | Se aparecer inconsistência não explicada                            |
| 13  | `matriz_referencia.pdf`                           | Só se for mapear cobertura ENEM. **Nunca** como fonte de categorias |

## NÃO tratar como fonte de verdade

|Documento|Motivo|
|---|---|
|`00 WHITE PAPER 1.0 (ANTIGO)`|**Perigoso.** Contém entidades de banco, algoritmos e IDs de gerações antigas que **colidem** com os atuais. Se o Claude Code ler isso, vai implementar `MasteryEstimate`, `BehavioralIndicator` e `ItemCognitiveMapping`, que não existem na arquitetura vigente|
|`04 Ontologia … JSON.md`|`superseded`. Stub sem conteúdo|
|`03 White Paper v2.0.1`, Parte V (Caps. 13–14)|Inventário **superseded**. 8 domínios contra os 11 vigentes|
|Os 8 registros `TX-*` em `auditoria/`|Histórico de transação. Ruído para quem vai codar|

## Contexto que precisa ser transferido fora dos documentos

Isto é o mais importante da lista — **nada disso está documentado**:

1. **Os 3 apps.** Não existe documento algum sobre eles. Nem nome, nem escopo, nem fronteira, nem quem consome o quê. Zero.
2. **O que já está implementado.** Nenhum documento descreve código existente. Não sei se há repositório, stack, ou linha escrita.
3. **Pipeline técnico e ferramentas.** O Schema cita `Firestore` de passagem e tem um bloco `pipeline` com `modelo`/`versao_prompt` — é a única pista. Não há documento de arquitetura técnica, deploy, ou ingestão.
4. **Banco de itens.** Não há indicação de quantos itens existem, se há algum anotado, ou onde estão.
5. **Camada de decisão pedagógica.** Formalmente vazia no corpus. Se um app precisa recomendar próximo conteúdo, **não há especificação** — e a aresta `Processo↔Processo` não está populada, então nem pré-requisitos existem.
6. **Os três números do piloto** (amostra, nº de anotadores, limiar de kappa) — pendentes de decisão sua.

**Recomendação:** antes de passar para o Claude Code, produza um documento de arquitetura dos 3 apps. Os itens 1–3 são a maior lacuna do handoff — o corpus atual descreve muito bem _o que_ modelar e quase nada sobre _o que construir_.

Se quiser, escrevo o esqueleto desse documento com as perguntas que você precisa responder.