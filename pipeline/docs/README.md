# `pipeline/docs/` — espaço canônico do Sapiens

> **Índice de navegação.** Artefato **derivado**: não cria norma, não decide nada e
> não é fonte de conteúdo. Sob GOV-1.0 §7.4, um índice existe apenas para orientar
> leitura; em qualquer divergência entre esta página e o documento que ela lista,
> **prevalece o documento**.

**Regra de espaço (GOV-1.0 §1.1).** Um documento existe normativamente se, e somente
se, está neste diretório e seu `estado` é `ativo` ou `congelado`. `auditoria/` é
espaço de **registro**, não de norma: nada ali vincula, mesmo quando descreve
corretamente o que o código faz.

---

## Precedência de conteúdo (GOV-1.0 §1.2)

| Camada | Documento | Estado | Versão |
|---|---|---|---|
| **procedimental** | [`00 Governanca e Versionamento Sapiens v1.0.md`](00%20Governanca%20e%20Versionamento%20Sapiens%20v1.0.md) | ativo | GOV-1.0 |
| **C1 — Axiomática** | [`white-paper/03 White Paper v2.0.md`](white-paper/) | congelado | **2.0.1** |
| **C2 — Constitucional** | [`constitution/02 Constituicao Sapiens.md`](constitution/) | ativo | CON-1.1 |
| **C3 — Ontológica** | [`ontology/ontology_v1.4.json`](ontology/ontology_v1.4.json) + [`ontology/05 Ontologia … v1.4.md`](ontology/) | congelado | **1.4.1** |
| **C4 — Operacional** | [`Schema anotador de questoes/06 Schema Sapiens 2.1.json.md`](Schema%20anotador%20de%20questoes/) | ativo | **2.2** |
| **C4 — Operacional** | [`behavior/07 behavior student 1.4.md`](behavior/) | ativo | **1.1** |
| **C4 — Operacional** | [`error-trace/10 Especificacao do Error Trace v1.0.md`](error-trace/) | ativo | ETRACE-1.0 |
| **C4 — Operacional** | [`annotation/01 Manual Oficial de Anotação Cognitiva Sapiens.md`](annotation/) | congelado | MAN-1.2 |
| **C5 — Registro** | [`traceability/09 Mapa de Rastreabilidade de IDs.md`](traceability/) | ativo | MAP-IDS-1.0 |
| **C5 — Registro** | [`traceability/08 Registro de Extracao do WP 1.0.md`](traceability/) | ativo | EXT-WP1-1.0 |

**Parte V do White Paper — supersessão parcial em vigor.** Os Capítulos 13 e 14
estão `[SUPERSEDED por ONT-1.4.1]` quanto ao **inventário** de domínios,
competências e processos: eles descrevem a derivação-piloto original (8 domínios,
16 competências, 28 processos), não o catálogo vigente (11/12/25). A seção
superada **deixa de ter força normativa imediatamente**, mesmo permanecendo no
texto (GOV-1.0 §8.3). Leia o inventário **sempre pelo catálogo C3**.

Atenção especial: **sete identificadores `DOM-*` são idênticos nos dois com
extensão comprovadamente divergente** — colisão `NS-4`, classificada
**BLOQUEANTE**. Um `DOM-QUANT` lido da Parte V não é o `DOM-QUANT` do catálogo.

Permanece vigente na Parte V: a nota metodológica do §13.1, a advertência do
§13.4, as limitações do §14.2 e todo o Capítulo 15 (Ativos Protegidos).

---

## Por que os nomes de arquivo não batem com as versões

Decisão declarada pelos próprios documentos, sob GOV-1.0 §6.1 — **a versão vive no
campo, não no nome** — para não quebrar citação já existente:

| Arquivo | Versão real declarada dentro |
|---|---|
| `06 Schema Sapiens 2.1.json.md` | `schema_version: "2.2"` |
| `07 behavior student 1.4.md` | `schema_version: "1.1"` (o "1.4" é resíduo de nomeação, nunca foi versão deste contrato) |
| `ontology_v1.4.json` | `version: "1.4.1"` |
| `05 Ontologia … v1.4.md` | `versao: 1.4.1` |

**Sempre leia a versão do campo.** Nunca infira versão de nome de arquivo.

---

## Regras que atravessam todos os contratos

1. **`ontology_version` é obrigatório** em todo objeto persistido — item anotado,
   evento de behavior e error trace. Nenhum artefato pode referir-se a "a ontologia
   vigente" (GOV-1.0 §6.1). Sem esse campo o dado é indatável e não pode ser
   remapeado quando a ontologia mudar de versão MAIOR.
2. **`distratores[].erro` (ID único) não existe mais.** Virou `erros_esperados[]`,
   lista **ordenada** (1..3) com `confianca` obrigatória em cada elo (Schema 2.2;
   Constituição §4.4).
3. **Vocabulário de papel: `nuclear` | `secundario`.** "Central"/"Secundário
   Necessário" era prosa do Manual e foi reconciliado (Error Trace §7). Rótulo
   mudou, semântica e limiares 0.7/0.3 não.
4. **Domínios e competências são derivados** por união a partir dos processos —
   nunca anotados de forma independente (Constituição §4.4; Schema 2.2).
5. **No máximo 2 processos com peso** por item; um terceiro candidato genuíno vira
   registro de ambiguidade (Manual §4/§5).
6. **Geração de IDs G3.** Os tipos de erro do White Paper 1.0 são inteiros `1..13` e
   formam conjunto **disjunto** dos `ERR-01..ERR-13` deste catálogo — colisão NS-1,
   classificada **BLOQUEANTE**. Ver `traceability/09 Mapa de Rastreabilidade de IDs.md`.

---

## `_superseded/`

Versões anteriores, preservadas para proveniência (GOV-1.0 §8.4, §9.3: silêncio não
remove). Cada arquivo carrega banner de supersessão declarando por quem foi
substituído. **Nenhum deles pode ser citado como norma.**

---

## Material de apoio externo (GOV-1.0 §1.1)

Material que não é fonte de categorias cognitivas do Sapiens, mas reside em `pipeline/docs/`
com `estado: apoio_externo` e declaração explícita de não-normatividade, conforme autorizado
pelo §1.1 (que cita nominalmente a Matriz de Referência do Enem como exemplo desse caso):

- [`enem-redacao/`](enem-redacao/) — canon documental dos critérios oficiais de correção de
  redação do Enem 2025 (Inep/MEC), extraído e estruturado para uso futuro por um corretor
  assistido por IA. Ver `enem-redacao/README.md` para proveniência, metodologia de extração e
  lacunas registradas.

---

## Lacunas conhecidas — nada aqui as define

Registradas para que ninguém as preencha por conta própria:

- **Arquitetura dos 3 apps** (`aluno`, `professor`, `pipeline`): escopo, fronteira e
  quem consome o quê. `architecture/README.md` está vazio.
- **Camada de decisão pedagógica**: como escolher o próximo conteúdo. Declarada
  "slot vazio" pelo White Paper §12.4. A aresta Processo↔Processo não está populada,
  então nem pré-requisitos existem.
- **Turma, matrícula e vínculo professor↔aluno**: não há menção em nenhum documento.
- **Evento de intervenção pedagógica aplicada** (professor→aluno, com timestamp e
  autor): a Intervenção existe apenas como nó de catálogo.
- **Protocolo de Piloto**: amostra por processo, número de anotadores e limiar de
  kappa — três decisões pendentes do Curador. Bloqueiam a Ontologia v1.6.
