---
tags: [produto, aquisicao, dinheiro, fonte-unica]
atualizado: 2026-09-21
---

# Programa de influencers/afiliados

Implementado em 2026-09-21, em cima da infraestrutura de aquisição que já
existia — não foi construído do zero. Antes de mexer aqui, leia
[[economia-de-sparks]] (preço é regra dele, não daqui) e [[inviolaveis]]
(a régua ética de venda/gamificação vale para todo material gerado aqui).

## As três coisas que já existiam, e o que cada uma continuou sendo

O produto já tinha três peças de aquisição que pareciam candidatas a
reconstrução e não foram tocadas na estrutura:

- **`promo_codes`** (`promo_codes_routes.py`) — catálogo de cupons do admin,
  bônus de Sparks no cadastro em vez do padrão. O código de um influencer **é
  um `promo_codes`**, só com `influencer_id` preenchido — é assim que o
  `/login?convite=CODIGO` (que já pré-preenche o campo e já abre em "Criar
  conta") funciona para influencer sem nenhuma mudança no formulário.
- **`indicacoes.py`** — referral aluno-a-aluno: prêmio único em Sparks (metade
  da primeira compra), pago pela plataforma. **Continua existindo,
  inalterado**, e é conceitualmente diferente do programa de afiliados: ver
  a seção "As duas coisas que parecem a mesma e não são".
- **`promoter_routes.py` / `PromoterDashboard.jsx`** — painel de quem tem
  e-mail em `promo_codes.promoter_email`. Era só "quantos alunos usaram meu
  cupom e quanto gastaram" — **estendido**, não recriado, para mostrar
  comissão e o kit de divulicação quando o cupom pertence a um influencer
  (`eh_influencer: true` na resposta de `GET /promoter/dashboard`).

## As duas coisas que parecem a mesma e não são

| | `indicacoes.py` (referral de amigo) | Programa de afiliados (este nó) |
|---|---|---|
| Quem indica | Qualquer aluno | Um parceiro comercial cadastrado |
| Prêmio de quem chega | Metade da 1ª compra em Sparks | Sparks de boas-vindas maiores (300 > 100) |
| Prêmio de quem indicou | Metade da 1ª compra do indicado, em Sparks | % da receita de TODAS as compras, em dinheiro |
| Quando paga | Uma vez, na primeira compra | Toda compra, recorrente |
| Quem paga | A própria plataforma (Sparks) | A empresa, por fora (Pix manual) |
| Onde mora | `indicacoes` (Mongo) | `influencers` + `influencer_comissoes` (Mongo) |

Os dois resolvem pelo MESMO campo do cadastro (`payload.promo_code`), na
mesma ordem de precedência que já existia: cupom do catálogo (`promo_codes`)
sempre vence; se o cupom tem `influencer_id`, vira atribuição de afiliado
(`influencers.resolver_e_registrar_atribuicao`); só se não houver cupom
nenhum é que o código é tentado como indicação pessoal
(`auth._registrar_indicacao`). Um código nunca é as duas coisas.

## Modelo de dados

- **`influencers`** — um documento por parceiro, cobrindo o ciclo inteiro:
  `lead → qualificado → contato → respondeu → interessado → cadastrado →
  ativo` (ou `recusado`/`removido`, que também PARAM o follow-up automático).
  Só ganha `codigo`/`link`/`email_login` a partir de `ativo`. Percentual de
  comissão (padrão 30%) e Sparks de boas-vindas (padrão 300) são
  **configuráveis por influencer**, nunca hardcoded — pedido explícito de
  2026-09-21.
- **`influencer_comissoes`** — um documento por PAGAMENTO, `_id =
  mp_payment_id` (idempotência pela chave primária, ver [[dados]]). Nunca um
  contador mutável: `comissao_acumulada`/`paga` são sempre SOMA sobre
  lançamentos com `status == "acumulada"`/`"paga"`, calculada em
  `influencers.resumo`. Estorno de pagamento muda o `status` do MESMO
  lançamento para `"estornada"` — nunca subtrai de um total, nunca apaga.
- **`growth_events`** — funil de aquisição (clique, cadastro, compra,
  comissão), deliberadamente **separado** do schema canônico de
  `students/{uid}/behavior`. Ver o docstring de `growth_events.py`: a mesma
  decisão que `events_routes.py` já tinha tomado ("não existe contrato
  canônico para X, reinventar seria pior") se aplica aqui na direção oposta —
  clique de anúncio não é comportamento pedagógico, e misturar os dois
  quebraria os dois contratos.
- **`campaigns`** — UTM/orçamento/criativo de campanha paga ou orgânica.
  `custo_real_cents` é **digitado pelo admin**, olhando o painel de cada
  plataforma — **não existe integração com API de Meta Ads/Google Ads**, de
  propósito (ver "O que foi deliberadamente NÃO automatizado" abaixo).

## Atribuição — como o vínculo sobrevive ao tempo

`users.influenciado_por`/`influenciado_por_codigo` são gravados **uma vez**,
no cadastro, e nunca reescritos depois — mesma disciplina de
`indicado_por`/`indicado_por_codigo`. A parte nova é a JANELA de atribuição
pedida (clique hoje, cadastro daqui a duas semanas ainda deveria contar):
`lib/atribuicao.js` no frontend guarda `{codigo, bonus, expira_em}` no
`localStorage` por 30 dias quando alguém chega por `?convite=CODIGO`, e
`Login.jsx` usa esse valor como padrão do campo de cupom quando a URL não
tem o parâmetro. É best-effort (aba anônima, storage bloqueado = sem
memória) e nunca é a fonte de verdade — o que decide de fato é sempre o que
está no campo `promo_code` no momento do POST `/auth/signup`.

**Autoindicação é bloqueada na raiz**: se o e-mail da conta nova bate com o
`email_login` do influencer dono do código, a atribuição é ignorada (ver
`influencers.resolver_e_registrar_atribuicao`) — ninguém comissiona a
própria compra disfarçada de indicação.

## Comissão — o dinheiro nunca se move sozinho

`influencers.creditar_comissao` roda dentro do MESMO webhook de pagamento
que já credita Sparks e paga `indicacoes` (`sparks_payments_service.
process_payment_webhook`), com a mesma disciplina: nunca pode derrubar o
crédito do comprador, erro vira log, não exceção propagada. Roda em **toda**
compra do aluno atribuído, não só a primeira — é receita recorrente, e é a
diferença estrutural para `indicacoes`.

Reembolso/estorno: se um pagamento que já gerou comissão volta como
`refunded`/`charged_back` num webhook posterior, `influencers.
estornar_comissao` marca o lançamento como `estornado` — os Sparks que o
aluno já recebeu não são revogados (mesma filosofia de "entregamos mais do
que deveríamos é o lado seguro" já usada em `mentis_ilimitada`), mas a
comissão sobre dinheiro que voltou nunca fica de pé.

**Nada aqui transfere dinheiro de verdade.** `marcar_comissao_paga` é uma
ação do admin depois de um Pix manual — o sistema acumula e confirma, o
pagamento em si continua sendo humano.

## Kit de divulgação e mensagens — determinístico, zero IA (exceto o Pesquisador)

`influencers.gerar_kit`/`gerar_mensagem_prospeccao`/`gerar_followup` são
templates com placeholders preenchidos por dado REAL do influencer/lead
(nome, código, link, nicho quando existe) — nenhuma chamada a Gemini. Decisão
deliberada pelo pedido original ("priorize... regras determinísticas...
evite chamadas repetidas" e "o agente `cost` deve revisar qualquer fluxo que
possa gerar muitas chamadas de IA"): gerar 50 mensagens de prospecção não
custa nada além de CPU. `classificar_resposta` é a mesma disciplina — só
casa por palavra-chave, e devolve `None` (não "sem interesse") quando o
texto é ambíguo, porque o pedido original é explícito: nunca responder
automaticamente numa situação ambígua sem regra clara.

**Isso deixou de ser 100% verdade em 2026-09-21**, com o Pesquisador IA de
Aquisição (`acquisition_research.py`, ver [[aquisicao]]): a DESCOBERTA de
leads e a geração de MENSAGEM PERSONALIZADA por lead (`gerar_mensagem_
personalizada`, distinta de `gerar_mensagem_prospeccao`) chamam o Gemini de
verdade. A disciplina de custo não foi abandonada, foi movida: descoberta é
sempre em LOTE (uma chamada por plataforma×nicho, nunca por lead), e
mensagem personalizada é sempre SOB DEMANDA (uma chamada só quando o admin
clica em um lead específico, nunca disparada para os leads de uma rodada
inteira). O kit de divulgação de quem já é afiliado ATIVO continua 100%
template — isso não mudou.

## O que foi deliberadamente NÃO automatizado

O pedido original marcou linhas que este programa não cruza, e o código
respeita todas:

- **Nenhum envio de mensagem real.** Não existe integração de WhatsApp
  Business API/Instagram DM/e-mail em massa. `gerar_mensagem_prospeccao`
  produz o texto; o envio continua manual. Não há scraping de contatos nem
  automação clandestina em plataforma nenhuma.
- **Nenhum gasto automático de tráfego pago.** `campaigns.py` não chama
  Meta Ads nem Google Ads. `custo_real_cents` é preenchido à mão pelo admin.
- **Nenhuma exclusão automática de `influencers`.** Ver "LGPD" abaixo —
  fica pendente de revisão do agente `legal-privacy` antes de ativação
  pública, porque o titular típico aqui é um parceiro comercial, não um
  aluno, e a base legal de retenção é outra.

## LGPD (seção 18 do pedido — revisado por `legal-privacy` em 2026-09-21)

`growth_events` (quando tem `aluno_id`) entra em
`dados_pessoais.COLECOES_POR_USUARIO` e sai com a conta do aluno, igual a
qualquer outra coleção dele. `influencer_comissoes` é anonimizada pelo lado
do `aluno_id` na exclusão (mesma lógica de `sparks_payments` — registro
financeiro, art. 16 I, fica sem o vínculo com a pessoa).

Isto é leitura de LGPD feita por um agente — sinalização qualificada, **não
parecer jurídico definitivo**. Os pontos abaixo marcados "confirmar" seguem
precisando de humano/advogado antes de operar em escala; os demais são
decisão de produto tomada agora, com a razão explícita.

**Decisão: `influencers` continua em `COLECOES_TRATAMENTO_ESPECIAL`, nunca
entra em `COLECOES_POR_USUARIO`.** Não é preferência, é estrutural:
`COLECOES_POR_USUARIO` dispara na exclusão de uma CONTA DE ALUNO por
`user_id`; o titular típico de um lead (criador de conteúdo, admin de
comunidade, professor autônomo) normalmente não tem conta de aluno — o
gatilho nunca acionaria. A base legal também diverge: dado de aluno usa base
contratual/execução do serviço; um lead de prospecção B2B usa **legítimo
interesse** (art. 7º, IX) ou, quando o dado é só o que o próprio titular
tornou manifestamente público (perfil de Instagram público, link de convite
que ele mesmo divulgou), art. 7º, §4º. É diferente de dado de aluno por
definição, não por tolerância.

**Base legal é por CAMPO, não por lead inteiro.** Um lead pode ser pessoa
física (professor autônomo) ou pessoa jurídica/marca (cursinho, comunidade)
— LGPD só protege pessoa natural (art. 1º). `nome_admin`,
`contato_pessoal`, `@ pessoal` são dado pessoal e pedem legítimo interesse
documentado; `link_grupo`, `nome_da_marca/comunidade`,
`audiencia_aproximada` isolados não são dado pessoal — mas na prática o
registro quase sempre tem os dois juntos, então trate o documento inteiro
com o cuidado do campo mais sensível que ele contém. Link de convite público
por si só **não é dado pessoal** e não muda de base quando fica ao lado do
nome do admin — o nome é que carrega a exigência, não o link.

**Decisão: todo lead novo grava `base_legal` e `finalidade` no próprio
documento** (ex.: `"legitimo_interesse_prospeccao_b2b"`). Custo zero,
resolve accountability (art. 6º, X), e importa porque um lead muda de base
ao longo do funil — de "pessoa física encontrada por IA" (legítimo
interesse) para "afiliado com contrato assinado" (execução de contrato). O
campo reflete a base ATUAL, atualizado na transição de status, não só a de
criação. **Implementado em 2026-09-21**: `influencers.criar_lead` aplica
`BASE_LEGAL_PROSPECCAO`/`FINALIDADE_PROSPECCAO` por padrão sempre que o
payload não os traz — confirmado em código, não só planejado. Ver
[[aquisicao]].

**Decisão: retenção por tempo, além de por pedido.** Lead nunca contatado ou
marcado `recusado` sem atividade por 24 meses é candidato a
expurgo/anonimização automática — mesmo padrão de "anonimizar preservando o
agregado do funil" já usado em `influencer_comissoes`. **24 meses é
recomendação, não número testado nem confirmado pelo dono** — cobre um ciclo
de venda B2B razoável sem virar acúmulo indefinido (art. 15/16,
minimização), mas confirme com o dono antes de codificar o job agendado.
Pedido explícito de remoção do titular (art. 18, VI) sempre atende de
imediato, independente desse prazo — o `DELETE` manual do admin citado abaixo
precisa existir e funcionar antes de qualquer ativação pública, mesmo que o
job de 24 meses ainda não exista.

**Pesquisador IA de Aquisição (Gemini + busca web) — riscos que somam aos de
cima, específicos deste fluxo novo:**
- **Qualidade do dado (art. 6º, VI).** Campo estruturado (nicho, foco,
  tipo de audiência, justificativa) pode conter alucinação da IA atribuída a
  uma pessoa real — isso é dado pessoal de baixa qualidade, não só "resposta
  ruim". A regra já pedida para a MENSAGEM de abordagem ("só dado público
  encontrado, nunca inventando fato pessoal") precisa valer também para os
  CAMPOS do lead: reaproveitar o campo `confiança da identificação` (já
  previsto no pedido) para marcar qualquer campo inferido por IA, e nunca
  apresentar um campo de baixa confiança ao admin como se fosse fato
  verificado.
- **Nunca entrar em grupo/canal, nunca listar participante** — já é regra do
  pedido original; é o que mantém o tratamento fora de dado de terceiro
  não relacionado (quem participa de um grupo não é o titular da
  prospecção e não deveria aparecer em nenhum campo do lead).
- **Dado sensível incidental (art. 5º, II).** Se a busca trouxer sinal de
  religião, orientação política, saúde etc. ligado ao lead (comum em nicho
  tipo "cursinho confessional"), esse sinal não deve virar campo do lead —
  eleva a base legal exigida (legítimo interesse não cobre dado sensível) e
  não tem uso comercial legítimo aqui. **Confirmar com advogado** se algum
  nicho específico do produto (ex. cursinho religioso) precisa de tratamento
  à parte antes do lançamento.
- Legítimo interesse (art. 7º, IX) não pode ser base para fornecer dado a
  terceiro em troca de vantagem econômica (art. 10, §2º) — não é o caso aqui
  (o Sapiens usa o lead para prospecção própria, não vende a lista), mas
  qualquer integração futura que compartilhe esta base com terceiro precisa
  reavaliar a base legal, não presumir que a mesma continua valendo.
- **Canal de oposição/remoção é assimétrico (sinalizado em 2026-09-21).**
  `DELETE /admin/influencers/{id}` apaga de verdade quando ACIONADO (ver
  [[aquisicao]]), mas não existe formulário/endpoint de autoatendimento — um
  titular que peça "me tire dessa lista" só é atendido se a mensagem (DM,
  e-mail etc.) chegar a alguém do Sapiens que saiba operar esse botão. LGPD
  art. 18 exige atender o pedido em prazo razoável por qualquer canal, não
  exige formulário dedicado — mas isso só funciona na prática se o dono
  definir **quem** recebe esse tipo de pedido e **em quanto tempo** atende.
  Pendência operacional, não de código.

Status em 2026-09-21: (1) `base_legal`/`finalidade` gravados por
registro — **implementado**; (2) caminho manual de remoção do admin
funcionando de fato — **implementado** (`DELETE`, recusa se há comissão
lançada ou afiliado ativo); (3) confirmação humana do prazo de retenção, do
ponto de dado sensível, e do processo de atendimento a pedido de oposição
acima — **ainda pendente**. Não anunciar o Pesquisador IA publicamente em
escala sem resolver o item 3.

## Métricas (seção 12 do pedido)

`growth_events.resumo_funil` dá CTR (cliques → cadastro) e conversão
(cadastro → compra) por influencer OU por campanha.
`campaigns.resumo_comparativo` (`GET /admin/campaigns/comparativo`) compara
tráfego pago vs. influencer vs. orgânico, usando comissão acumulada como
"custo" do canal influencer — não existe CAC de influencer sem isso, porque
não há gasto de mídia ali. "Ativação" é **derivada** (aluno com ≥1 resposta
registrada), não um evento gravado à parte — decisão deliberada para não
duplicar telemetria que já existe em `students/{uid}/behavior`.

## Painéis (seção 5 do pedido — nenhuma aba nova)

- **Admin**: `/admin/influencers` (`AdminInfluencers.jsx`) — CRM de
  prospecção, ativação, comissão. `/admin/campaigns` só tem API por
  enquanto (`campaigns_routes.py`), sem tela própria — ver "Riscos e
  próximos passos" no relatório da implementação.
- **O próprio influencer**: continua sendo `/promoter/dashboard` — a MESMA
  rota que já existia para promoter comum, agora mostrando comissão e kit
  quando o cupom logado pertence a um influencer.

---
Relacionado: [[economia-de-sparks]] · [[dados]] · [[pagamentos]] · [[inviolaveis]] · [[engajamento]] · [[custo-de-leitura]] · [[custo-de-ia]]
