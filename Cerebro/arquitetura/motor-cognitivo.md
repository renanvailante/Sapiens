---
tags: [arquitetura, pedagogia, motor]
atualizado: 2026-09-18
---

# O motor cognitivo — medir, explicar, intervir

Quatro camadas que respondem perguntas **diferentes** sobre o mesmo aluno. Confundi-las
é o erro clássico aqui.

| Camada | Pergunta | Custo | IA? |
|---|---|---|---|
| `/skills-map` | (cosmético — metáfora visual) | 20 Sparks | não |
| `/diagnostico` | **onde** ele vai mal | grátis | não |
| `/motor/*` | **por quê** ele erra (Error Trace) | grátis | **não** |
| `/prioridades` | **o que fazer agora** | grátis | não |

Nenhuma delas chama LLM. Esse é o ponto: a medida é determinística, e só a
*narração* dela custa ([[mentis]]).

## `/diagnostico` — desempenho medido, nomes reais

`annotation_service.compute_diagnostico_real(user_id)` agrega
`students/{uid}/behavior` × Firestore `itens` por domínio/competência/processo, com
**amostra mínima** (`_DIAGNOSTICO_MIN_AMOSTRA = 3`) antes de declarar ponto forte
ou fraco.

`padroes_associados` é modesto de propósito: quando um processo tem desempenho
fraco **medido** e tem **exatamente um** Tipo de Erro catalogado (nunca escolhido
por chute entre vários candidatos), mostra o fato geral do catálogo + a intervenção
sugerida. **Nunca atribui causa a uma resposta individual.**

## `/motor/*` — o Error Trace

`motor_cognitivo.py` + `intervencoes.py` + `motor_routes.py`. Gratuito, zero LLM.

O insumo **já existia no corpus e ninguém lia**: `distratores[].erros_esperados[]`
(cadeia ordenada), `intervencoes[]` com `gatilho {processo, erro}` + `acao` escrita
por item, e `pedagogia.passos`. O motor só faz a junção evento × item × catálogo.

> **A única regra do Error Trace v1.0 que muda comportamento pedagógico:** a
> intervenção sai **sempre** do elo `ordem: 1` (a raiz), nunca da manifestação.

Validado com aluno real (2026-09-06): 88 eventos, 59 erros, 47 traços, 79,7% de
cobertura.

## O portão de crença

`PORTAO_CRENCA_MODO` está **`desligado`** em produção. Todo traço sem revisão
humana volta marcado `provisorio` — no perfil, na linha da habilidade e no traço —
e a tela declara **"leitura provisória"** (requisito testado, não copy).

> [!danger] Virar o portão para `crenca` antes de revisar esvazia o perfil de todo
> aluno. Foi exatamente o incidente de 2026-09-04.

**O gargalo real não é código.** A Fase 0 do ciclo adaptativo foi construída e
publicada, **não executada**: ninguém rodou o relatório de oferta contra o acervo
real e nenhum item foi revisado por humano em `/admin/curadoria`. É trabalho
humano; nenhuma sessão futura resolve isso sozinha.

Estado da primeira execução (2026-09-12): 268 itens, **0 revisados**, 25 processos,
18 aprovados. O conjunto mínimo de revisão humana é **188 itens únicos**; os 3
maiores pares cobrem 56%. Metade dos 36 pares é sentinela
(`erro-nao-catalogado-nesta-versao`) e não prescreve intervenção — revisar esses
não é prioridade.

## O ciclo adaptativo (Fases 0–5)

`observar → intervir → retestar`. Em produção desde 2026-09-12 (commit `222e838`).
Módulos: `revisao_espacada.py` (máquina de estados **pura**, zero I/O),
`revisao_service.py`, `microdiagnostico.py`, `curadoria.py`, `sapiens_lab.py`.
Telas: `/revisoes` e `/admin/curadoria`.

Decisões que divergem da proposta escrita (motivo em
`aluno/docs/ciclo-adaptativo-implementacao.md`):

- o bloco `revisao` é **materializado** em `students/{uid}` com teto em toda lista
  (1 leitura + 1 escrita por resposta, memorizada por sessão) em vez de escrita
  cega;
- "janelas distintas" virou "**dias** distintos", e janelas contam **respostas**,
  não dias;
- a Fase 3 não inventa mapa ERR→classe de relato, só mede a fração de "chutei";
- a interrupção da Fase 2 carrega `intervencoes.previa()` (custo zero) em vez do
  plano completo, que é O(eventos).

Duas correções saíram da primeira execução real: o contexto de transferência passou
de domínio para `fonte.disciplina` (domínio é derivado do processo por §4.4, logo
tautológico — reprovava 7 processos), e a fila parou de truncar em silêncio.

## `/prioridades` — onde a próxima hora rende mais ponto

`prioridade_enem.py` é a **resposta única** do produto a "o que estudar agora".
Antes disto cada tela respondia sozinha, todas por "onde você erra mais", que **não
é a mesma pergunta**: errar muito numa área que vale pouco rende menos ponto.

    rendimento = peso × lacuna_medida × confiança

Os pesos são [[decisoes-do-dono]]. **Piso de confiança 0.60**: amostra curta torna
a estimativa menos certa, não a área menos valiosa — sem o piso, começar a medir
*rebaixava* a área e o produto punia quem respondeu. Frente nunca medida entra com
lacuna neutra 0.50 e estado `sem_medida`, que é o que faz o recém-cadastrado
receber uma semana de Matemática e Redação em vez de tela vazia.

Consomem: `/api/prioridades`, o cronograma, o dossiê da Mentis e o Painel.

## O cronograma

**O modelo nunca decide horário nem prioridade.** `slots_livres` subtrai os
compromissos da janela do dia, `alocar` distribui por `prioridade_enem.ranking`
(maior resto, teto de 40% por frente), e só então a Mentis — se o aluno pagar —
reescreve `titulo` e `detalhe`. `aplicar_enriquecimento` **ignora**
dia/horário/tipo/rota vindos do modelo (`test_mentis_nao_consegue_mover_bloco`).
Consequência: montar a semana é grátis e funciona com o Gemini fora do ar.

Quatro portas para os compromissos, e **nenhuma pode ser a única**: falar/escrever
(Sparks), Google Agenda por OAuth **no navegador** (o backend nunca vê token do
Google), endereço `.ics` (`_HOSTS_ICS` é a trava anti-SSRF, com teste) e formulário
(grátis, nunca falha). O ditado usa a Web Speech API — **nenhum áudio sai do
aparelho**, nenhuma API de transcrição na conta.

## O painel do perfil

`GET /perfil/painel` serve **17 gráficos numa chamada**, grátis, sem LLM
(`perfil_painel.py`, função pura `montar(...)`).

**A régua do que pode virar número:** o que o aluno **fez** (frente, dia, hora,
tempo, volume, constância, nota de redação) → percentual, tabela e gráfico. O que a
**ontologia sabe** → só `rotulo` + `explicacao`, sem número ao lado.

A telemetria descritiva pega carona na varredura que já existia — **zero leitura
nova**. Ela sai numa chave própria que `compute_diagnostico_real` não lê, porque
coletar não é inferir (ver [[inviolaveis]]).

As leituras da Mentis no painel são montadas **no servidor** a partir dos mesmos
números do gráfico ao lado: determinísticas, grátis, sem modelo. Toda leitura exige
amostra mínima — sem amostra, ela se cala.

Contrato travado dos dois lados: `gerar_fixture_do_painel.py` gera
`__fixtures__/painel.json` a partir do código real, `painel.test.js` monta os 17
cartões contra ele, e `TestFixtureDoFrontendContinuaEmDia` acusa quando o formato
muda e o arquivo não é regerado.

---
Relacionado: [[custo-de-leitura]] · [[mentis]] · [[canon-pedagogico]] · [[decisoes-do-dono]]
