# TX-2026-08-25T153950Z-enem-canon-fidelity-v1.1

**Registrado em:** 2026-08-25
**Natureza:** registro de transação. Sob GOV-1.0 §1.1, `auditoria/` **não cria norma** — este documento descreve o que foi feito, não decide nada.
**Papel exercido:** Curador, por instrução explícita do usuário (identificação nomeada dos dois defeitos abaixo, com pedido de correção na fonte, durante implementação de `aluno/backend/redacao/canon.py`).
**Classes:** **II — Errata** (item 1) e **I — Correção de Fidelidade** (item 2), GOV-1.0 §3.3. Nenhuma decisão cognitiva ou de correção nova foi introduzida em nenhum dos dois casos.

**Escopo:** `pipeline/docs/enem-redacao/13 enem_regras_computaveis.json` (apoio_externo, membro do CNI com `12 ENEM 2025 - Matriz de Correcao Estruturada.md`, GOV-1.0 §4.2). Nenhum Domínio, Competência, Processo, Habilidade, Tipo de Erro ou Intervenção do catálogo C1–C5 do Sapiens foi tocado — este canon é apoio externo, não fonte de categorias (GOV-1.0 §1.1).

---

## 1. Errata — chave JSON `titulo` duplicada no nível de topo (Classe II)

**Defeito:** o objeto JSON de topo tinha duas chaves `"titulo"` — a string do título do documento (linha ~3, criada em `TX-2026-08-24T151820Z-enem-canon-v1`) e o objeto da regra `TITULO-01` (linha ~250, mesma transação de criação). Chave duplicada no mesmo objeto não é erro de sintaxe JSON; `json.load` (e qualquer parser padrão) mantém silenciosamente só a última ocorrência. Consequência: `data["titulo"]` sempre retornava o objeto `TITULO-01`; a string do título do documento era permanentemente inacessível por essa chave, sem qualquer sinal de erro.

**Correção:** a chave de topo (título do documento) foi renomeada para `"titulo_documento"`. A chave `"titulo"` da regra `TITULO-01` não foi tocada — continua sendo a autoridade sobre o nome usado internamente por essa regra.

**Por que é Classe II, não III/IV:** não introduz, remove nem redefine nenhum identificador ou regra de correção; apenas resolve uma colisão de nome que impedia acesso a um campo já existente. Nenhum consumidor de produção depende deste canon ainda (`declaracao_de_nao_normatividade`: "nenhuma regra aqui vincula um corretor de produção até que uma transação C4 explícita a adote"), então não há dado derivado a reconferir.

## 2. Correção de Fidelidade — `cap_por_tangenciamento` ausente em `COMP-II` (Classe I)

**Decisão de referência já registrada** (GOV-1.0 §4.3, passo 1):
- `13 enem_regras_computaveis.json.tema.tangenciamento.efeito` (presente desde a criação): *"cap de 40 pontos em COMP-II, COMP-III, COMP-V; efeito sobre COMP-I e COMP-IV indeterminado (AMB-07)"*.
- `12 ENEM 2025 - Matriz de Correcao Estruturada.md` §1, linhas 91-92: *"COMP-II → nível 0/40/80/120/160/200 ... + aplica TEMA-02 (cap de tangenciamento) se detectado"*.
- Mesmo documento, §3/AMB-07, linha 207: a leitura literal da fonte é descrita como "a fonte só menciona **II**, III e V".

**Divergência demonstrada** (passo 2): `competencias[COMP-II]` não portava a chave `cap_por_tangenciamento`, embora `COMP-III` e `COMP-V` a portassem (`{"pontos_maximos": 40, "origem": "TEMA-02", "fonte_pagina_fisica": 27}`) e `COMP-IV` portasse a variante `{"aplicavel": "indeterminado", "ambiguidade": "AMB-07"}`. A ausência não estava registrada em nenhuma das 9 entradas de `ambiguidades` — só `AMB-07` trata do tema, e restrita a Competências I e IV.

**Nenhuma decisão nova** (passo 3): o valor adicionado (`pontos_maximos: 40, origem: TEMA-02, fonte_pagina_fisica: 27`) é idêntico em forma ao já presente em `COMP-III`/`COMP-V` e não escolhe entre leituras — a fonte já nomeia II, III e V juntas.

**Aplicado a todos os membros do CNI na mesma transação** (passo 4): `13 enem_regras_computaveis.json` recebeu o campo; `12 ENEM 2025 - Matriz de Correcao Estruturada.md` não precisou de alteração de conteúdo (já correto) — recebeu apenas uma entrada de changelog para manter os dois changelogs do CNI sincronizados.

**Contagens derivadas reconferidas** (passo 5): `ambiguidades` permanece com 9 entradas, inalterado; `AMB-07` permanece restrita a I/IV, consistente com a correção (que não toca I/IV).

---

## 2. Artefatos alterados

| Artefato | Antes → Depois | Alteração de conteúdo? |
|---|---|---|
| `pipeline/docs/enem-redacao/13 enem_regras_computaveis.json` | `versao` 1.0.0 → **1.0.1** | Sim — ambos os itens acima |
| `pipeline/docs/enem-redacao/12 ENEM 2025 - Matriz de Correcao Estruturada.md` | `versao` permanece **1.0.0** | Não — apenas `atualizado_em` e changelog (registro de sincronização do CNI) |

## 3. Verificação de integridade

```
python3 -m json.load sobre 13 enem_regras_computaveis.json: OK
titulo_documento acessível e distinto de titulo.id == "TITULO-01": OK
COMP-II.cap_por_tangenciamento == {pontos_maximos: 40, origem: TEMA-02, fonte_pagina_fisica: 27}: OK
len(ambiguidades) == 9 (inalterado): OK
len(changelog) == 2: OK
```

## 4. Contexto de origem

Identificado pelo usuário durante a implementação de `aluno/backend/redacao/canon.py` (corretor de redação Enem), que já continha um contorno defensivo documentado para o item 2 (`_CAP_TANGENCIAMENTO_AUSENTE_NO_JSON = {"COMP-II": 40}` em `cap_tangenciamento()`). Esta transação corrige a fonte; o contorno no código de produção passa a ser redundante e pode ser removido em transação separada de código (fora do escopo desta transação, que toca apenas `pipeline/docs/`).
