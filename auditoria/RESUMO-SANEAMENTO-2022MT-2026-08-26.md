# Resumo — gabarito (3 provas) + recortes manuais ENEM 2022 MT

**Data:** 2026-08-26

## 1. Gabarito — reverificado nas 3 provas

| Prova | Itens no banco | Divergências encontradas | Correções aplicadas |
|---|---:|---:|---:|
| ENEM 2022 | 89 | 0 | 0 (já corrigido na Fase 1) |
| ENEM 2023 | 89 | 0 | 0 (já corrigido na Fase 1) |
| ENEM 2024 | 90 | 0 | 0 (já corrigido na Fase 1) |

Reverificado agora contra os mesmos PDFs oficiais do INEP (SHA-256 conferido),
nos 4 stores. `GAB-01/02/04 = 0` em todos. Nada para corrigir — a Fase 1 já
havia fechado isso; esta rodada confirma que continua fechado.

## 2. Elementos visuais — ENEM 2022 Matemática (136–180)

| | Qtd |
|---|---:|
| Questões com recorte manual seu na pasta de referência | 22 |
| Corrigidas e incorporadas ao `visual_assets` | **21** |
| Sem evidência suficiente (permanece pendente) | 1 (Q177) |
| Assets totais incorporados (figuras + alternativas) | 45 |

**As 21 corrigidas:** 139, 141, 143, 145, 146, 148, 151, 153, 158, 159, 162,
163, 164, 165, 166, 168, 171, 173, 174, 178, 179, 180.

Cada uma passou a ter os elementos visuais reais — figura, tabela ou gráfico —
associados à questão certa, com o recorte que **você fez**, substituindo o
recorte automático anterior (que tinha os defeitos já documentados:
vazamento de texto do enunciado, faixa de marca d'água, e no caso da Q148 a
cota "10 cm" literalmente cortada fora). O frontend do aluno (`ExamSelect.jsx`)
foi atualizado para renderizar essas imagens dentro do enunciado e, nas quatro
questões com alternativas gráficas (158, 163, 165, 178), a imagem certa
aparece dentro do botão de cada alternativa — não mais como lista solta.

**Duas correções de mapeamento na sua própria pasta**, resolvidas com
evidência, não com achismo:
- Q163 tinha suas duas figuras principais salvas com o nome "Q162" por engano
  (estavam dentro da pasta certa, só com o rótulo do arquivo trocado). O
  conteúdo — uma sequência de dobradura de papel — bate exatamente com o que
  o sistema já tinha registrado como descrição da Q163, não da Q162 (que é
  sobre cartela de bingo). Corrigido o rótulo, sem tocar no arquivo original.
- A alternativa B da Q163 era uma cópia idêntica, byte a byte, da alternativa
  A — ou seja, uma das duas foi salva errada. Comparando contra a página 25
  do PDF oficial do INEP, a alternativa A do seu recorte bate com a página
  real; a B, não (a B real é um círculo liso). Recortei a B direto do PDF
  oficial no local exato da alternativa e conferi visualmente antes de usar.

**A única pendente: Q177**, a tabela de 13 dias. Você mesmo anotou no README
que avisaria se precisasse recortá-la — não há recorte na pasta, e não
inventei um. Segue como estava.

## 3. Por que eu não consigo fazer exatamente o que você fez, e o que dá pra fazer a respeito

O que você fez foi **olhar a página impressa e decidir**, com os olhos, onde
cada figura começa e termina — inclusive nos casos ambíguos (como decidir
juntar os dois gráficos da Q143 num recorte só). Isso é uma tarefa de
julgamento visual, não de medição.

O que eu tenho é o oposto: sei ler texto e vetores do PDF com precisão
perfeita, mas **não tenho um modelo confiável de "onde uma figura termina"**
dentro da bagunça de linhas, curvas e texto de uma página de prova. Nas fases
anteriores eu tentei duas abordagens automáticas — heurística de a
extração de imagem embutida (rendimento zero nesse caderno, que é quase todo
vetorial) e cluster geométrico de desenhos vetoriais — e as duas produzem
recortes que ou cortam a figura pela metade ou pegam pedaço do texto vizinho
junto. Eu sei dizer isso com confiança porque testei contra os *seus* recortes
e o meu detector automático errava sistematicamente contra sua régua.

Por isso a escolha certa, nesta rodada, foi: onde você já cropou, uso o seu
recorte (é ground truth de verdade); onde eu tinha evidência determinística
equivalente vinda do PDF oficial — como a alternativa B da Q163, onde eu podia
localizar o cluster vetorial exato pelo rótulo "B" e conferir visualmente —
eu também resolvi; onde não tinha nem uma coisa nem outra (Q177), não inventei.

**O caminho para fechar o resto (2023, 2024, e a Q177 de 2022) sem você ter
que recortar mais nada:** construir o "modelo de layout tipográfico" que já
está descrito na auditoria original (Fase 3/4) — um segmentador que lê a
página inteira e agrupa cada objeto (linha, curva, texto) em blocos
(parágrafo, figura, tabela, legenda) usando regras de fronteira tipográfica
(fonte, indentação, proximidade), em vez de tentar achar bordas de imagem que
não existem. Isso é trabalho de construção de um componente novo — não é algo
que dá pra fazer "corrigindo o script atual", é um motor diferente. Com ele
pronto, o sistema passaria a fazer sozinho o que você fez à mão: decidir onde
uma figura começa e termina, e as próximas 76 questões sem recorte manual
(2023 e 2024 inteiros, mais a Q177) teriam uma chance real de ficarem certas
sem depender de mais uma rodada de anotação sua.

## 4. Verificação

- Dry-run → snapshot (`fase5-pre`) → aplicação → dry-run de reexecução
  (confirmado NO-OP, sem duplicar blob nem reescrever timestamp).
- Invariantes: `item_hash` de todos os 268 itens inalterado · enunciado,
  alternativas e gabarito intactos · 3 stores Mongo idênticos entre si · todo
  blob referenciado existe no storage.
- `pipeline/backend/tests`: 183 ✔ (mesmas falhas pré-existentes de sempre).
  `aluno/backend/tests`: 177 ✔ + 1 falha por cota do Firestore (não é
  regressão). Build do frontend: ✔.
- **Pendente:** sincronizar o Firestore `itens` (cota diária esgotada durante
  a execução, confirmado por duas tentativas). Comando pronto em
  `PENDENCIAS-SANEAMENTO-2026-08-26.md §0`.
