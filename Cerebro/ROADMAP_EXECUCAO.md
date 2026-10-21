---
tags: [roadmap, auditoria, produto]
atualizado: 2026-09-20
---

# Roadmap de execução — auditoria completa do Sapiens (2026-09-20)

> Este nó é diferente dos demais do Cerebro: não é "por que é assim", é um
> **plano de trabalho datado**. Ele descreve o estado encontrado em 2026-09-20,
> não o presente contínuo. À medida que cada tarefa for implementada, risque-a
> ou mova-a para [[superado]] com a data — não deixe o roadmap divergir do
> código sem marcação, ou ele vira a mesma armadilha que a auditoria expôs em
> outros lugares (promessa que não bate com a entrega).

## 1. Resumo executivo

Auditoria conduzida por 8 agentes especializados (arquitetura, segurança,
performance, UX/onboarding, pedagogia, Mentis/IA, monetização, growth), cada um
lendo o código real do `aluno/` e o `Cerebro/` correspondente, sem alterar
nada. Objetivo: identificar o que impede o Sapiens de completar o funil —
aluno entra → entende o valor rápido → começa a estudar → sente experiência
claramente superior a um chatbot genérico → volta → entende os Sparks →
compra → tem motivo para continuar.

**53 achados**, classificados P0–P3. Os quatro P0 revelam um padrão: o produto
já construiu a coisa certa em cada frente (motor cognitivo real, gamificação
ética, direito de Mentis ilimitada genuinamente permanente, code-splitting
desenhado com cuidado) e depois **não entregou essa coisa certa no lugar que
mais importa** — o motor cognitivo não chega ao Treino (a aba mais visitada),
a promessa de "ilimitada" diverge entre duas telas, o bundle que foi
deliberadamente dividido voltou a se juntar, e a mecânica de retenção mais
honesta do produto não alcança quem não abriu o app sozinho.

Nenhum achado propõe aba, rota ou sistema novo — todas as soluções cabem nas
cinco áreas existentes (Hoje · Agenda · Estudar · Progresso · Comunidade),
confirmado explicitamente pelo agente de arquitetura. O que já está sólido
(autenticação, webhook do Mercado Pago, LGPD, ética de gamificação, leitura
O(1) do Firestore na quase totalidade das rotas) está listado no fim, para não
ser retrabalhado.

**Legenda de IDs:** `P{nível}-{sequência}`, na ordem em que aparecem no funil
(entrada → estudo → Mentis → monetização → retenção → infraestrutura). O
`[agente]` entre colchetes é quem descobriu o achado na auditoria — não é
necessariamente quem deve implementá-lo (ver coluna "Agente responsável" nas
seções 2–5).

---

## 2. P0 — Bloqueia funcionamento ou venda

### P0-1 — Divergência de promessa sobre "Mentis ilimitada" [monetization]

- **Evidência**: `aluno/backend/sparks_store.py:101` — `beneficios=(..., "Mentis ILIMITADA por um mês", ...)`. `aluno/frontend/src/pages/Comunidade.jsx:298` — *"o mesmo que deixa a Mentis ilimitada **para sempre**"*. O backend concede a flag **sem prazo** (permanente) — já era divergência conhecida (`Cerebro/produto/catalogo.md`), mas a auditoria achou a segunda tela com a versão certa e contraditória.
- **Impacto**: etapas 6-7 do funil. Duas telas do mesmo produto, mesma compra, prazos opostos — o tipo exato de contradição que gera reclamação e desconfiança em pagamento.
- **Solução concreta**: trocar `"Mentis ILIMITADA por um mês"` por `"Mentis ILIMITADA"` (sem prazo) em `sparks_store.py:101`, alinhando com `Comunidade.jsx` e com o que o backend já entrega. Troca de string — mas é promessa comercial, confirmar com o dono antes de publicar.
- **Arquivos**: `aluno/backend/sparks_store.py:101`, `aluno/frontend/src/pages/Comunidade.jsx:298`, `aluno/frontend/src/pages/SparksStore.jsx` (onde `beneficios` é renderizado).
- **Agente responsável**: backend + aprovação do dono (promessa comercial).
- **Dependências**: nenhuma técnica.
- **Status (2026-09-20)**: ✅ implementado. `sparks_store.py:101` corrigido para
  "Mentis ILIMITADA" (sem prazo); `SparksStore.jsx:845` tinha a mesma promessa
  errada e foi corrigida junto; `Cerebro/produto/catalogo.md` e
  `Cerebro/regras/inviolaveis.md` atualizados para descrever o presente (a
  divergência estava documentada como "aberta" — está fechada agora). Backend:
  136 testes relevantes + suíte inteira (1329) passando.

### P0-2 — `Estudar.jsx` quebra o code-splitting; KaTeX volta ao bundle principal [performance]

- **Evidência**: `aluno/frontend/src/pages/Estudar.jsx:4-5` importa `Cursos` e `Provas` de forma **estática** (`import Cursos from "./Cursos"`), embora `App.js:35,37` já declare ambos como `lazy()`. O import estático dentro de `Estudar.jsx` obriga o webpack a embutir a árvore inteira (`components/curso/Blocos.jsx` → `TextoRico.jsx` → `katex`) no chunk principal. Medido no build real: `main.4b27d998.js` — 1,1 MB raw / **324 KB gzip**, com 42 ocorrências do motor KaTeX minificado. Contradiz o próprio comentário de `App.js:31-34`, que descreve essa divisão como já resolvida.
- **Impacto**: etapas 2-3 do funil. TTI da primeira tela pós-login carrega ~300KB gzip a mais do que precisa, numa rede móvel que já é ponto sensível documentado (`Cerebro/ux/mobile.md`).
- **Solução concreta**: trocar os imports estáticos de `Estudar.jsx` por `React.lazy()` + `<Suspense>` locais, mesmo padrão já usado em `App.js`.
- **Arquivos**: `aluno/frontend/src/pages/Estudar.jsx`, `aluno/frontend/src/pages/Cursos.jsx`, `aluno/frontend/src/pages/Provas.jsx`.
- **Agente responsável**: frontend.
- **Dependências**: nenhuma — refatoração isolada de imports.
- **Status (2026-09-20)**: ✅ implementado. `Cursos`/`Provas` viraram
  `React.lazy()` dentro de `Estudar.jsx`, com `<Suspense>` local (fallback
  `Bloco` do próprio sistema de esqueleto, não o spinner de tela cheia). Build
  de produção confirmou: bundle principal caiu de 1,1MB/324KB gzip para
  745KB/225KB gzip, e `grep -c "katex" main.*.js` foi de 42 para **0**.

### P0-3 — Motor cognitivo (Error Trace, Professor Invisível, revisão espaçada) só dispara em Provas [pedagogy]

- **Evidência**: `aluno/backend/firestore_routes.py:247-289` (`POST /students/me/answer`, único caminho de `Provas.jsx:213`) calcula `causa_raiz`, chama `revisao_service.registrar_resposta` e `microdiagnostico.perguntar_por`. Já `aluno/backend/treino_routes.py:346-393` (`POST /treino/habilidade/{hab_id}/responder`, usado por `Treino.jsx:110`) e a rota irmã `/treino/questoes-geradas/{id}/responder` chamam só `th.checar_resposta` (`treino_habilidades.py:148-165`), que devolve apenas `acertou`/`gabarito`/`elucidacao`. `ProfessorInvisivel`, `Microdiagnostico` e `IntervencaoMentis` só são renderizados em `Provas.jsx:609-628` — nunca em `Treino.jsx` nem `QuestoesGeradas.jsx`.
- **Impacto**: etapas 3-4-8. Treino é a aba central gamificada (destino declarado de prática recorrente); nela, errar produz a experiência de qualquer quiz genérico. A fila de revisão espaçada (`FilaDeRevisao.jsx`) fica vazia para quem só usa o Treino, porque só `register_answer` alimenta `revisao_espacada`. É a tese central do produto ("por que você erra, não só quanto") ficando invisível na superfície mais usada.
- **Solução concreta**: `/treino/habilidade/{hab_id}/responder` e `/treino/questoes-geradas/{id}/responder` devem chamar `revisao_service.registrar_resposta`, calcular `causa_raiz` e devolver `professor_invisivel`/`microdiagnostico` no payload — os módulos já existem e funcionam em Provas, é fiação, não design novo. No frontend, `Treino.jsx` e `QuestoesGeradas.jsx` precisam importar e renderizar os mesmos três componentes que `Provas.jsx` já usa. Onde o banco de Treino não tiver anotação de distrator suficiente, o gatilho simplesmente não dispara (comportamento já gracioso).
- **Arquivos**: `aluno/backend/treino_routes.py`, `aluno/backend/treino_habilidades.py`, `aluno/frontend/src/pages/Treino.jsx`, `aluno/frontend/src/components/treino/QuestoesGeradas.jsx`.
- **Agente responsável**: backend (rota + integração), depois frontend (renderização).
- **Dependências**: nenhuma.

### P0-4 — Zero canal de reengajamento fora do app [growth]

**Status (2026-10-20)**: 🟡 em parte — Web Push ligado de ponta a ponta (ver [[engajamento]]); WhatsApp e e-mail continuam sem envio automático.

- **Evidência**: busca em todo `aluno/backend` por mecanismo de envio ativo (`sendgrid`, `smtplib`, `firebase_admin.messaging`, `pywebpush`, `onesignal`, `APScheduler`, `celery`) — nenhum resultado. `aluno/frontend/public/sw.js` não tem handler de `push`. `aluno/backend/whatsapp.py:68-77` (`link_conversa`) só monta um link `wa.me/...` para o **admin clicar manualmente** — não existe disparo automático ao aluno. O `agendamento` de `lembretes_revisao` (`lembretes_routes.py:203-214`) já foi projetado para isso ("nasce preparado e inerte") mas nunca foi ativado.
- **Impacto**: etapas 5 e 8. A ofensiva que quebra de verdade, a fila de lembretes e as missões diárias — todas as mecânicas de retorno genuinamente boas e éticas do produto — só aparecem depois que o aluno já abriu o app. Quem não abre não recebe nada.
- **Solução concreta**: job diário (cron no Fly.io) que lê `agregado.dias_ativos`/`engajamento_dia` e dispara **uma** mensagem de WhatsApp para quem está `em_risco=True` e ainda não estudou até certa hora, usando `whatsapp_e164` real e frase com número verdadeiro atrás (mesma disciplina de `venda.js`/`engajamento.py` — nunca inventar urgência). Depois, evoluir para push via PWA.
- **Arquivos**: novo módulo backend (`reengajamento_service.py` + rota de cron), `aluno/backend/whatsapp.py`, `aluno/backend/engajamento.py`, `aluno/backend/engajamento_service.py`.
- **Agente responsável**: backend (implementação) + growth (régua de quando disparar e texto).
- **Dependências**: provedor de envio de WhatsApp (hoje só há link manual, precisa API — Twilio/WhatsApp Business API); aprovação do dono (mensagem automática toca a régua ética).

---

## 3. P1 — Grande impacto em ativação/conversão/retenção

### P1-1 — `/api/feed` público, sem auth nem rate limit [security]
Evidência: `aluno/backend/feed_routes.py:40-65`, `async def get_feed(...)` sem `Depends(require_user)`. Comentário no próprio arquivo: "Public feed browsing (auth optional but recommended)" (linha 38). Contrasta com `/api/questoes`, fechado de propósito porque "um curl sem login baixava o banco inteiro" (comentário em `server.py:162-169`).
Impacto: scraping do acervo pedagógico (a IP do produto) sem fricção nem custo; superfície de custo/DoS gratuita.
Solução: `Depends(require_user)`, igual às demais rotas de conteúdo, ou `rate_limit.por_ip("feed")` se o produto quiser mesmo um funil sem login (confirmar com o dono — a inconsistência com `/questoes` sugere esquecimento, não decisão).
Arquivos: `aluno/backend/feed_routes.py`. Agente: backend. Dependências: nenhuma.
**Status (2026-09-20)**: ✅ implementado, mas **com a alternativa, não a
solução original**. Ao reler o código, o comentário "auth optional but
recommended" e o enquadramento de Folhear como "três minutos e nenhuma
intenção" (`Estudar.jsx`) sugerem que o acesso público é deliberado (degustação
sem login), não esquecimento — diferente do que a auditoria presumiu. Optei por
`Depends(rate_limit.por_ip("acervo"))` (120/min), que fecha o risco de scraping
em loop sem fechar um funil possivelmente intencional. Se a decisão do produto
for "não, isso não devia ser público", falta ainda trocar para `require_user`.
Testes: 136 + suíte inteira passando.

### P1-2 — Login com Google trava em tela branca [growth]
Evidência: `Cerebro/produto/contas-e-acesso.md` documenta a causa (particionamento de armazenamento de terceiros do Chrome + `authDomain` fora da origem) e confirma que a correção "ainda NÃO aplicada". `aluno/frontend/src/pages/Login.jsx:106` só mostra aviso depois de 25s (`setTimeout(() => setDicaPopup(true), 25_000)`).
Impacto: etapa 1. Google é o caminho de cadastro mais rápido e quebra silenciosamente para parte dos navegadores.
Solução: aplicar a correção já desenhada no Cerebro — `public/_worker.js` no Cloudflare Pages reencaminhando `/__/auth/*` e `/__/firebase/*`, e trocar `REACT_APP_FIREBASE_AUTH_DOMAIN` para `sapiens-aluno.pages.dev`.
Arquivos: `aluno/frontend/public/_worker.js` (novo), config do Firebase, `aluno/frontend/src/pages/Login.jsx`. Agente: backend/frontend (infra de auth). Dependências: muda autenticação de todo mundo — aprovação do dono.
**Status (2026-09-20)**: ⏸ **não implementado, de propósito.**
`Cerebro/produto/contas-e-acesso.md` já marcava esta correção como "ainda NÃO
aplicada (muda a autenticação de todo mundo e precisa de aprovação)" antes
desta rodada começar — uma trava mais forte que a nota deste roadmap. Muda
`REACT_APP_FIREBASE_AUTH_DOMAIN` em produção e depende de configuração externa
(Firebase Console) além do código. Fica bloqueado até o dono aprovar
explicitamente.

### P1-3 — Promessa do cadastro não bate com a entrega real [ux]
Evidência: `Login.jsx:41-47` promete "Responda 10 questões — Dez minutos" antes da conta existir. Entrega real: `BemVindo.jsx` (4 etapas, `minutos`/`meta` obrigatórios em `podeAvancar:175-179`) → tour de 5 passos (`Hoje.jsx:368-414`) → `ProvasGrid` (`Provas.jsx:855-985`), grade que o aluno tem que escolher manualmente, sem nada pré-selecionado.
Impacto: etapas 2→3. A primeira experiência concreta desmente a primeira promessa lida.
Solução: (a) mudar a copy do Login para descrever o fluxo real, ou (b) fazer `BemVindo` terminar dentro de um caderno pré-selecionado, cumprindo literalmente "responda 10 questões" no clique seguinte a "Entrar no Sapiens".
Arquivos: `Login.jsx`, `BemVindo.jsx`, `Provas.jsx`. Agente: ux/growth. Dependências: decisão do dono sobre qual das duas fica (copy ou fluxo).

### P1-4 — Dois botões, mesmo destino, na ação primária do dia 1 [ux]
Evidência: `ProximoPasso.escolherPasso` (`ProximoPasso.jsx:102-111`) devolve `/estudar/provas` como CTA "Descobrir agora"; três linhas abaixo, o botão "Provas do ENEM" (`:189-196`) aponta para a mesma rota — contradiz a doutrina do próprio cabeçalho do arquivo ("escolher entre dez coisas é o jeito mais confiável de não fazer nenhuma").
Impacto: etapa 3. Solução: remover o botão duplicado quando coincidir com `passo.rota`, ou apontá-lo para outro destino.
Arquivos: `aluno/frontend/src/components/ProximoPasso.jsx`. Agente: frontend/ux. Dependências: nenhuma.

### P1-5 — `ExplorarOSapiens` (10 portas) abre por padrão para quem tem 0 respostas [ux]

**Status (2026-10-20)**: ✅ implementado — fechado para todos; ver [[padroes-de-tela]].
Evidência: `Hoje.jsx:695` passa `abertoInicial={totalRespondidas === 0}` para `ExplorarOSapiens.jsx:53-61`, que renderiza 10 destinos (`PortaisDaJornada.jsx:120-207`). Somado ao resto da rolagem (`ProximoPasso` + `PainelDeProgresso` + chamadas de mentoria/live), um aluno de dia 1 vê **~19 destinos clicáveis simultâneos**. O comentário de `Hoje.jsx:30-35` já registra que essa disputa foi corrigida uma vez — a exceção a reintroduziu no público mais sensível.
Impacto: etapas 2-3. Solução: inverter a regra — abrir por padrão para quem já tem trajetória, fechado para quem não respondeu nada.
Arquivos: `Hoje.jsx:695`, possivelmente `ExplorarOSapiens.test.js`. Agente: ux/growth. Dependências: ler `Cerebro/ux/padroes-de-tela.md` antes — essa dobra já foi revertida 3 vezes sem registro de intenção.

### P1-6 — Cards de venda (mentoria + aula ao vivo) incondicionais no dia 1 [ux]

**Status (2026-10-20)**: ✅ implementado — a seção do mentor só aparece depois da primeira resposta.
Evidência: `Hoje.jsx:678-684` monta `<ChamadaDaMentoria />` e `<ChamadaDaLive />` sem condição sobre `totalRespondidas` ou tempo de conta.
Impacto: etapas 5→6 — o produto pede confiança antes de tê-la construído (não fere a regra ética, a argumentação é honesta; fere a ordem do funil).
Solução: esconder/reduzir os dois cards enquanto `totalRespondidas === 0`, mesmo padrão condicional que `abertoInicial` já usa.
Arquivos: `Hoje.jsx`. Agente: growth/monetization. Dependências: nenhuma.

### P1-7 — `ProvasGrid` exige escolha manual sem recomendação, onde o funil prometeu "descoberta guiada" [growth]
Evidência: `ProximoPasso.jsx:102-111` chama o CTA "Descobrir agora" para quem não tem dado, mas o destino (`Provas.jsx:855-985`) é uma grade de N cadernos por banca/ano/dia sem nenhum card marcado como "comece aqui" — mesmo padrão de excesso de escolha que o produto já corrigiu em `ExplorarOSapiens`.
Impacto: etapa 3. Solução: pré-selecionar/destacar um bloco (ex. ENEM mais recente) com botão primário "Comece por aqui" quando `respondidas === 0` em tudo.
Arquivos: `aluno/frontend/src/pages/Provas.jsx` (`ProvasGrid`). Agente: frontend/growth. Dependências: nenhuma — UI sobre dado já carregado (`GET /provas`). Relacionado a P1-3.

### P1-8 — Liga e Comunidade genuinamente vazias ("cidade fantasma") [growth]
Evidência: `ConquistasELiga.jsx:62-68,118-124` e `Comunidade.jsx:360-367` já tratam o vazio de forma honesta (sem bot, sem número inventado) — mas com base pequena, um aluno novo vê liga com 1-2 pessoas e mural sem perguntas.
Impacto: etapa 8. Solução: não é problema de código sem violar a regra ética — mitigação de produto/operação: agrupar liga por escola/turma, equipe real respondendo as primeiras dúvidas do mural, CTA de convite ligado ao programa de indicação já existente.
Arquivos: nenhum óbvio — decisão de produto/operação. Agente: growth (operação). Dependências: volume real de alunos ativos, fora do controle do código.

### P1-9 — Explicação de redação por competência já calculada, mas escondida atrás de paywall [pedagogy]
Evidência: `aluno/backend/redacao/pontuacao.py:34-49` (`_rastro`) monta `evidencias_presentes`, `evidencias_ausentes` e `motivo` por competência, determinístico, zero-LLM, já no dict devolvido por `montar_resultado:144-151` e no `AvaliacaoRedacao.competencias` (`models.py:398`, passthrough total). `BarraCompetencia` (`Redacao.jsx:32-62`) só lê `nivel_pontos`/`confirmado`/`cap_aplicado` — os três campos de evidência textual nunca são renderizados. O "porquê" só aparece pagando 90 Sparks na devolutiva da Mentis.
Impacto: etapa 4 — um chatbot genérico ao menos explica a nota na mesma resposta; aqui a explicação existe e é escondida, o que é pior que "genérico".
Solução: renderizar `evidencias_presentes`/`evidencias_ausentes` no card de cada competência, grátis, na tela de resultado — sem substituir a devolutiva paga (que vende prosa corrida, tom, "o que fazer na próxima").
Arquivos: `aluno/frontend/src/pages/Redacao.jsx` (`BarraCompetencia`). Agente: frontend. Dependências: nenhuma — dado já trafega na API.

### P1-10 — IDs reais da ontologia vazam no payload JSON da Mentis [ai]
Evidência: `annotation_service.py:751-757` (`_ranking_real`) e `:832-838` (`padroes_associados`) devolvem `id`/`processo_id`/`erro_id` crus. `mentis_routes.py:659-669` (`_montar_dossie`) copia `fracos_proc`/`fortes_proc`/`padroes` sem remover o campo `id`, e `_serializar_sessao:1028` devolve isso verbatim em `GET/POST /mentis/sessao`. O frontend só usa `f.id` como `key` do React, mas o valor está no corpo HTTP, visível via DevTools.
Impacto: viola diretamente `Cerebro/regras/inviolaveis.md` ("nomes reais da ontologia nunca aparecem para o aluno"). Etapa 6 fica mais frágil.
Solução: em `_montar_dossie`, projetar `resumo_ui` para `{nome, acertos, respondidas, percentual_acerto}` sem `id`/`processo_id`/`erro_id`.
Arquivos: `aluno/backend/mentis_routes.py` (`_montar_dossie`); checar se `/diagnostico` cru tem o mesmo problema. Agente: backend. Dependências: nenhuma.

### P1-11 — Zero telemetria de tokens/custo real das chamadas Gemini da Mentis [ai]
Evidência: `ai_service.py:126-180` (`_generate_json`) só lê `resp.text`, nunca `resp.usage_metadata`. `llm_telemetry.persist` (`llm_telemetry.py:18-48`) grava contexto/motivo/modelo/duração — nenhum token, nenhum custo. As 5 chamadas de `mentis_routes.py` (linhas 251-259, 460-468, 613-621, 1199-1207, 1359-1367) usam esse contrato.
Impacto: toda estimativa de margem da Mentis no app do aluno é projeção, nunca medição — contradiz a disciplina já aplicada na pipeline.
Solução: capturar `resp.usage_metadata.{prompt_token_count, candidates_token_count, thoughts_token_count}` em `_generate_json` e passar via o parâmetro `extra` que já existe em `llm_telemetry.persist`.
Arquivos: `aluno/backend/ai_service.py`, `aluno/backend/mentis_routes.py`, `aluno/backend/llm_telemetry.py`. Agente: ai/backend. Dependências: nenhuma.

### P1-12 — Preço escrito à mão no JSX em 6 lugares [monetization]
Evidência: `Hoje.jsx:144` ("200 Sparks"), `ComunidadeDuvida.jsx:241` ("30 Sparks"), `Mentoria.jsx:111,188` ("50"/"200 Sparks"), `Comunidade.jsx:298` ("4.000 Sparks (R$119,90)" — Sparks e reais hardcoded), `AdminCursos.jsx:862,864`.
Impacto: viola a regra "preço nunca é escrito à mão" (`Cerebro/regras/inviolaveis.md`). Batem com o catálogo por coincidência, não reagem a mudança futura.
Solução: passar o preço como prop a partir da mesma leitura que `Hoje.jsx` já faz de `inclusa`/catálogo; para telas sem essa leitura hoje (Mentoria, ComunidadeDuvida), adicionar endpoint leve de preços avulsos ou reaproveitar `precos_avulsos` de `SparksStore.jsx`.
Arquivos: os 6 listados. Agente: frontend. Dependências: endpoint de preços avulsos, se não cobrir essas telas ainda.
**Status (2026-09-20)**: ✅ implementado, back e front. Backend: `GET
/cursos/precos` novo (`custo_live` + `pacote_lives_inclusas`, mesmo contrato de
`mentoria_routes.precos`, que já existia e passou a ser reaproveitado);
`GET /comunidade/duvidas/{id}` passou a incluir `custo_destaque`; `GET
/comunidade/vip/acesso` passou a incluir `pacote` (label + price_cents), usado
tanto pela tela quanto pelo 403 de `_exigir_vip` (que também tinha o preço
hardcoded — achado não listado no roadmap original, corrigido junto por vir da
mesma fonte). Frontend: os 6 arquivos citados leem os valores reais agora, sem
literal. Testes: backend 125 relevantes + suíte inteira; frontend 182 testes +
build de produção, ambos passando.

### P1-13 — Fluxo de correção de redação cobra em 3 decisões separadas [monetization]
Evidência: `redacao_routes.py:69-76` — `DIGITALIZACAO_COST=25`, `CORRECAO_COST=120`, `FEEDBACK_COST=90`, cada etapa um clique de confirmação separado (`Redacao.jsx:571,756,797,828`).
Impacto: etapas 7-8. Total 235 Sparks fatiado em 3 decisões de "quero gastar?", cada uma chance de abandono.
Solução: oferecer "correção completa" (235 Sparks) como opção única, mantendo as etapas avulsas — reduz fricção de decisão sem mudar preço.
Arquivos: `Redacao.jsx` (fluxo), `redacao_routes.py` (endpoints já existem). Agente: frontend, com revisão de monetization. Dependências: nenhuma.

### P1-14 — Onboarding nunca explica o que é Spark [monetization]
Evidência: `OnboardingTour.jsx:20-29` — comentário confirma decisão deliberada de não explicar; Sparks só aparece de passagem no passo do menu (`:72`). A única explicação real (`"Você ganha praticando — e compra quando quiser acelerar..."`) mora em `SparksStore.jsx:742`, só vista se o aluno clicar no chip de saldo.
Impacto: etapa 6 diretamente — o objetivo é "entender antes de comprar às cegas", hoje isso só acontece por iniciativa do aluno.
Solução: não reabrir o tour de 5 passos (decisão do dono, já revertida uma vez); acrescentar um tooltip de uma frase (reaproveitando o texto de `SparksStore.jsx:742`) na primeira vez que `ChipDeSparks` anima um ganho (`Navegacao.jsx:120-127`, já tem lógica de "primeira leitura nunca anima").
Arquivos: `Navegacao.jsx` (ChipDeSparks), `SparksStore.jsx:742` (fonte do texto). Agente: frontend/ux. Dependências: aprovação do dono (onboarding é área sensível, já revertida uma vez).

### P1-15 — Saldo inicial grátis (100 Sparks) não alcança a nota de redação (120) [monetization]
Evidência: `firestore_service.py:216` — `SPARKS_INITIAL_BALANCE=100`; `redacao_routes.py:69` — `CORRECAO_COST=120`.
Impacto: etapa 6 — para um dos produtos mais centrais (Redação, prioridade 1.00 no ENEM), o saldo grátis fica 20 abaixo da própria nota.
Solução: confirmar com o dono se é calibrado; se não, considerar preço-degrau anunciado na primeira nota, ou garantir que `Redacao.jsx` oriente claramente "faltam N Sparks; ganhe respondendo Y exercícios" (como `MentisChat.jsx:484-488` já faz).
Arquivos: `firestore_service.py:216`, `redacao_routes.py:69`, `Redacao.jsx:571`. Agente: monetization (calibração) + backend. Dependências: decisão do dono.

### P1-16 — Reconstrução não-atômica de `questoes_public` [architecture]
Evidência: `admin_routes.py:349-353` — `delete_many({})` seguido de `insert_many(publics)`, sem transação. Chamado por clique manual e por `_auto_sync_loop` (a cada `FIRESTORE_AUTO_SYNC_SECONDS`, hoje 21600s/6h). Entre as duas chamadas, a coleção fica vazia para qualquer leitor concorrente.
Impacto: `GET /api/questoes` e `GET /api/provas` leem `questoes_public` sem fallback — um aluno que abrir a tela nesse instante recebe "nenhuma questão disponível", justo na etapa 3, e pode acontecer a cada 6h automaticamente.
Solução: trocar por escrita em coleção sombra + `renameCollection(dropTarget=True)`, ou `bulk_write` de upserts por `item_id` seguido de um único `delete_many` seletivo — nunca um estado "vazio".
Arquivos: `aluno/backend/admin_routes.py` (`run_firestore_sync`, ~329-359). Agente: backend. Dependências: nenhuma — troca isolada numa função já extraída.

### P1-17 — Backend roda numa única máquina (SPOF para o funil inteiro) [architecture]
Evidência: `fly.toml:78,83-84,96-97` — `min_machines_running=1`, sem `max_machines_running`/contagem declarada (fora do arquivo, via `fly scale count`).
Impacto: se a máquina cair (OOM em 512mb com firebase-admin+google-genai, crash, deploy ruim), as 8 etapas param ao mesmo tempo — inclusive crédito de Sparks e reconciliação de pagamentos (`_sparks_reconciliacao_loop` só existe nessa máquina).
Solução: confirmar contagem real (`fly scale show -a sapiens-aluno`); se for 1, `fly scale count 2`, validando antes que os três laços de fundo (`_auto_sync_loop`, `_perfil_cognitivo_loop`, `_sparks_reconciliacao_loop`) toleram paralelismo (a idempotência de dados por `mp_payment_id` já existe, mas vale teste de regressão explícito).
Arquivos: `fly.toml`; validação em `server.py` (`_startup`). Agente: performance/infra, com revisão de backend. Dependências: teste de idempotência multi-máquina antes de escalar.

### P1-18 — Cache do Error Trace é por processo, sem LRU, esvazia por inteiro [performance]
Evidência: `motor_cognitivo.py:377-378` (`_HISTORICO_MEMO`, `_HISTORICO_MEMO_MAX=256`). Em cache miss, `_ler_historico` (`:400-470`) faz `stream()` de toda a subcoleção `behavior` do aluno — sem teto — coberto pela memoização por `(uid, total_respostas)`, mas essa memoização (1) é em memória de processo, não compartilhada entre workers (diferente do padrão da casa, que usa Mongo); (2) ao estourar 256 entradas, faz `_HISTORICO_MEMO.clear()` (linha 468) — limpa **tudo**, não é LRU, sem log de aviso.
Impacto: chamado por `motor_cognitivo.perfil()`, que `/motor/perfil` serve — e `Hoje.jsx:289` chama isso em todo carregamento da tela inicial. Numa campanha de aquisição ou pico de alunos simultâneos, o produto pode voltar a pagar O(eventos) em massa sem aviso — mesma classe de suposição implícita que já causou o apagão de 04/09.
Solução: trocar o `clear()` total por eviction real (`OrderedDict` com `move_to_end`/`popitem`), ou mover o cache para o Mongo como os outros agregados caros; no mínimo, logar quando o `clear()` acontecer.
Arquivos: `aluno/backend/motor_cognitivo.py`. Agente: backend/database. Dependências: nenhuma; testar contra `tests/test_custo_firestore.py::TestMemoriaDoMotor`, já existente.

### P1-19 — `Hoje.jsx` dispara 13 requisições paralelas e bloqueia a tela até a mais lenta responder [performance]
Evidência: `Hoje.jsx:277-321` (`Promise.allSettled` com 13 chamadas: `/analyses`, `/sparks`, `/activity`, `/skills-map`, `/respondidas`, `/rounds`, `/motor/perfil`, `/treino/habilidades`, `/redacao`, `/revisao/fila`, `/cronograma`, `/onboarding`, `/engajamento/me`). Cada uma é O(1), mas `setLoaded(true)` só acontece depois que **todas** resolvem — sem renderização progressiva. Contrasta com `perfil_publico_routes.get_painel` (`perfil_publico_routes.py:84-115`), que já consolida "dez gráficos" numa chamada só, com o comentário explícito "dez requisições seria dez vezes o custo".
Impacto: a tela de maior tráfego do produto tem seu TTI definido pelo pior dos 13 round-trips, não pela média — pior ainda em 4G. Corroborado independentemente pelo agente de UX (achado #10 do relatório de UX).
Solução: consolidar num endpoint agregador (`GET /hoje`), seguindo o padrão de `/perfil/painel`; ou renderizar progressivamente no frontend (cada seção aparece assim que seu dado chega).
Arquivos: `Hoje.jsx`; se consolidar no backend, novo endpoint reaproveitando as funções existentes. Agente: frontend e/ou backend. Dependências: se endpoint agregador, checar `graft callers` de cada uma das 13 rotas antes de tocar.

---

## 4. P2 — Melhoria relevante

### P2-1 — `/exams` e `/exams/{id}` públicos, sem rate limit [security]
Evidência: `exam_routes.py:49-66`, sem `Depends`. Não vaza gabarito, mas expõe lista completa de simulados sem exigir conta.
Solução: `Depends(require_user)`. Arquivos: `exam_routes.py`. Agente: backend.

### P2-2 — `/ready` expõe configuração operacional interna [security]
Evidência: `server.py:385-475` devolve publicamente `portao_crenca.modo()`/`confianca_minima()` (descrito no próprio código como "quanta crença... sem revisão humana"), `auto_sync_segundos`, versão da ontologia, booleanos de integrações.
Solução: manter `mongo`/`status` públicos para o health check do Fly; mover `operacao`/`ontologia`/integrações para trás de `require_admin` (`/api/admin/ready-detalhado`).
Arquivos: `server.py:385-475`. Agente: backend. Dependências: decisão sobre o que o balanceador do Fly precisa ler sem auth.

### P2-3 — Dependências Python com `>=` em vez de `==` [security]
Evidência: `requirements.txt` — `python-multipart`, `pydantic`, `email-validator`, `firebase-admin`, `google-cloud-firestore`, `google-genai`, `python-dotenv`, `tzdata`, `pyjwt` em range aberto (libs core já corretamente pinadas com `==`).
Impacto: builds não reprodutíveis; `python-multipart` já teve CVE de DoS em versões antigas.
Solução: pinar com `==`, processo de bump deliberado (dependabot/renovate + `pip-audit`). Arquivos: `requirements.txt`. Agente: backend/infra.

### P2-4 — Widget da Mentis não comunica diferencial antes de um clique extra [ux]
Evidência: `mentis_routes.py:761-786` (`_texto_de_abertura`) monta a primeira fala a partir do dossiê real — mas só aparece depois de abrir o FAB e clicar "Abrir sessão" (`MentisWidget.jsx:181-188,273-283`); até ali, ícone `Sparkles` e `placeholder="Pergunte algo…"` idênticos a qualquer widget genérico.
Solução: prévia do dossiê no estado fechado do widget, ou adiantar a leitura para o primeiro clique de abertura do painel.
Arquivos: `MentisWidget.jsx`. Agente: frontend/ai. Dependências: nenhuma mudança de backend necessária (dado já existe em `_montar_dossie`).

### P2-5 — Onboarding empilhado: `BemVindo` + tour guiado, mesmo pulando tudo [ux]
Evidência: `BemVindo.jsx` promete "três passos" (linha 225) mas tem 4 etapas reais (`ETAPAS`, linha 38); mesmo quem clica "Pular tudo" (`pularTudo:160-166`) ainda recebe o tour completo de 5 passos em `Hoje.jsx:378-412`.
Solução: se o aluno usa "Pular tudo" no `BemVindo`, pular também o tour automático.
Arquivos: `BemVindo.jsx`, `Hoje.jsx` (`jaPassouPeloBemVindo`/`marcarVisto`). Agente: ux/frontend. Dependências: decidir se "pular tudo" grava `flags.guia_visto` no servidor.

### P2-6 — `ProvasGrid` exige escolha onde o Hoje prometeu ação já decidida [ux]
Mesma raiz de P1-7 — registrado como achado independente pelo agente de UX. Ver P1-7 para solução e arquivos.

### P2-7 — Hierarquia visual insuficiente entre "recomendado", "venda" e "descoberta livre" [ux]
Evidência: consequência agregada de P1-5 e P1-6 — quando ambos aparecem juntos no dia 1, a diferenciação depende só da ordem vertical (mesma classe `.superficie`/`.lift` para tudo, por desenho do sistema visual). Resolve-se automaticamente corrigindo P1-5/P1-6. Agente: ux.

### P2-8 — `elucidacao` do banco de Treino é texto fixo por questão, não por alternativa [pedagogy]
Evidência: `treino_habilidades.py:161-165` devolve `questao["elucidacao"]` — igual para quem errou A, B, C ou D, diferente do Error Trace (sempre cita a evidência específica).
Solução: fora de escopo de curto prazo mudar o banco (corpus autoral sem anotação por distrator); documentar como dívida, não tratar como equivalente ao Error Trace em comunicação de produto.
Arquivos: `pipeline/docs/treino-habilidades/` (congelado — não mexer agora), `treino_habilidades.py` (consumo). Agente: pedagogy (escopo) + ai (se anotação futura). Dependências: bloqueado por `pipeline/` congelado.

### P2-9 — Toda a Mentis paga roda sobre modelo "preview", sem contingência de múltiplos fallbacks [ai]
Evidência: `ai_service.py:43-44` — `DEFAULT_MODEL=DEFAULT_VISION_MODEL="gemini-3-flash-preview"`. Comentários no arquivo (`:222-226`) já registram que `gemini-2.5-flash` devolveu 404 de depreciação e `gemini-flash-latest` recusa `thinking_level=MINIMAL`. Só há 1 fallback fixo (`GEMINI_MODELO_FALLBACK="gemini-3.5-flash"`), só para erro de infra, não depreciação.
Solução: migrar para versão GA equivalente quando existir; manter lista de 2+ fallbacks verificados; logar/alertar toda vez que o fallback for acionado.
Arquivos: `ai_service.py`. Agente: ai/backend. Dependências: acompanhar catálogo de modelos do Gemini.

### P2-10 — Chat sem memória entre sessões [ai]
Evidência: `mentis_routes.py:1066-1137` (`abrir_sessao`) — ao expirar a janela de 24h, cria sessão nova só com a abertura determinística; nada da conversa anterior entra no dossiê. Nenhum caminho onde a Mentis inicia contato proativamente.
Solução: manter resumo curto e barato da última sessão, injetar no dossiê da abertura seguinte; considerar 1 gatilho proativo determinístico (sem LLM) tipo "a Mentis notou 3 dias sem estudo".
Arquivos: `mentis_routes.py` (`_montar_dossie`, `abrir_sessao`), possivelmente `engajamento.py`. Agente: ai/pedagogy. Dependências: decisão de produto sobre custo do resumo entre sessões.

### P2-11 — Falha do Gemini no chat devolve Sparks mas zero conteúdo (503 seco) [ai]
Evidência: `mentis_routes.py:1208-1217` reembolsa e devolve 503 puro. Contrasta com o cronograma, que "se falhar, devolve os Sparks e entrega a semana determinística assim mesmo, nunca 503 seco" (`Cerebro/produto/mentis.md`). Timeout de 10s (`_TIMEOUT_CHAT`).
Solução: devolver ao menos uma resposta mínima ancorada no dossiê determinístico ao falhar, preservando a regra "nunca 503 seco" já aplicada em outro lugar.
Arquivos: `mentis_routes.py` (`enviar_mensagem`). Agente: ai/backend. Dependências: decisão de produto sobre o texto do fallback.

### P2-12 — Widget flutuante da Mentis nunca mostra o custo por mensagem [ai]
Evidência: `MentisWidget.jsx` nunca renderiza `custoMensagem` (só mostra saldo); compare com `MentisChat.jsx:470-478`, que mostra o custo ao lado do botão de enviar.
Solução: replicar o indicador de custo do `MentisChat.jsx` no widget. Arquivos: `MentisWidget.jsx`. Agente: frontend/monetization.

### P2-13 — `mentis_ilimitada` é permanente e sem teto de uso cumulativo [ai]
Evidência: `sparks_store.py:84-94`, `mentis_routes.py:132-134` (atalho antes do débito), `rate_limit.py` LIMITES["mentis"]=(60,3600) — só teto por hora.
Impacto: um único pagamento concede chamadas ilimitadas ao Gemini para sempre, sem teto diário/vitalício — risco de custo de cauda longa numa conta abusada.
Solução: considerar teto diário adicional (ex. 200 msgs/dia) alto o bastante para nunca incomodar uso humano real, sem tocar a permanência do direito (regra inviolável).
Arquivos: `rate_limit.py`, `mentis_routes.py`. Agente: monetization/backend. Dependências: decisão do dono.

### P2-14 — Taxa de ganho fixa (1 Spark/acerto) nunca é instrumentada [monetization]
Evidência: `cursos_recompensa.py:53` — `SPARKS_POR_ACERTO=1`, mesmo valor em toda a base. Decisão deliberada e documentada (`Cerebro/produto/economia-de-sparks.md`), não é bug.
Solução: instrumentar quantos alunos abandonam entre "saldo zerado" e "primeira compra", para decidir com dado se a régua está calibrada. Nenhum código a mudar agora — é recomendação de análise. Agente: monetization/growth.

### P2-15 — Pacote de entrada entrega ~40% menos Sparks/Real, sem visualização clara [monetization]
Evidência: `sparks_store.py:53-72` — `spark_200` = 20,2 Sparks/R$ vs `spark_4000` = 33,4 Sparks/R$; diferença só em rótulo textual, sem número comparando.
Solução: mostrar "Sparks por real" ou "economize N%" calculado no servidor (nunca hardcoded), reforçando `economiaDoPacote` (`venda.js:159`).
Arquivos: `sparks_store.py`, `venda.js`, `SparksStore.jsx`. Agente: monetization/frontend.

### P2-16 — Nenhum incentivo estrutural na primeira compra de quem não veio por indicação [monetization]
Evidência: `indicacoes.py:185-240` (`creditar_primeira_compra`) só credita o indicador. Quem compra sem ter sido indicado não recebe nada extra.
Solução: considerar bônus estrutural fixo e anunciado (permanente, não gatilho de pressão — não viola a regra ética).
Arquivos: `sparks_payments_service.py`, `sparks_store.py`. Agente: monetization → decisão do dono. Dependências: mexe em economia real.

### P2-17 — Wiring manual de `set_db` em 32 módulos, sem verificação automática [architecture]
Evidência: `server.py:82-116` — 28 chamadas manuais `modulo.set_db(db)`, mais 4 recebidos transitivamente. Nenhuma injeção via `Depends`, nenhum teste que garanta que todo módulo registrado foi inicializado. Cadeia hoje completa (não é bug atual) — fragilidade estrutural.
Solução: um teste único que importa `server` (com `fake_db`) e itera todos os módulos wired, checando `modulo._db is not None` — mesmo espírito de `test_rotas_do_app.py`.
Arquivos: novo teste em `aluno/backend/tests/`. Agente: testing (com apoio de backend). Dependências: nenhuma.

### P2-18 — `mentis_routes.py` (1392 linhas) mistura prompt, cobrança de Sparks e rotas [architecture]
Evidência: cobrança/estorno (`_cobrar:123`, `_safe_reembolso:113`) convive com construção de prompt (`_montar_prompt_explicacao:184`, `_montar_prompt_intervencao:353`, `_montar_dossie:644`) e handlers de rota — maior arquivo de rota do backend.
Impacto: qualquer iteração de copy/prompt acontece no mesmo módulo que decide crédito e estorno de dinheiro, aumentando o raio de dano de merge concorrente.
Solução: extrair `mentis_billing.py` (cobrança, estorno, idempotência de desbloqueio) e `mentis_prompts.py` (montagem/validação de prompt), deixando `mentis_routes.py` como handlers finos — mesmo padrão que `cursos_estudo_routes.py` já usa delegando para `cursos_progresso`/`cursos_publicados`.
Arquivos: `mentis_routes.py` (split, nenhum contrato de rota muda). Agente: backend, coordenado com ai. Dependências: nenhuma — refactor de organização.

### P2-19 — Arquivos grandes concentram lógica dos fluxos mais críticos [architecture]
Evidência: `cursos_ingestao.py` 59.7K, `cronograma_routes.py` 44.8K, `cursos_estudo_routes.py` 49.7K, `firestore_service.py` 54.6K; frontend `Provas.jsx` 57.8K, `SparksStore.jsx` 53.5K, `Cursos.jsx` 44.3K, `Agenda.jsx` 46.3K. `cronograma_routes.py` (44.8K de rota) é desproporcional a `cronograma.py` (41.5K de lógica pura) — sinal de orquestração vazada para a camada de rota.
Solução: aplicar o mesmo padrão de extração que o projeto já usa em `cursos_*`, começando por `cronograma_routes.py`, um arquivo por vez com teste de regressão antes de cada extração.
Arquivos: os listados. Agente: backend e frontend (dividido por lado). Dependências: nenhuma bloqueante.

### P2-20 — `/ready` não falha com Firestore fora do ar, sem alerta ativo [architecture]
Evidência: `server.py:404-410` — checagem de Firestore loga erro mas não seta `ok=False` (decisão consciente, comentário nas linhas 389-393, coerente com "degradar, não falhar"). Efeito colateral: o Fly nunca marca a instância como não-saudável por isso.
Impacto: numa degradação prolongada, o app "parece no ar" enquanto o loop central (resposta → evento → Sparks) está quebrado silenciosamente.
Solução: manter `/ready` como está, mas adicionar contador de falhas consecutivas de `write_behavior_event` exposto em `/ready.checks` (sem derrubar `ok`) e log `ERROR` acima de N falhas.
Arquivos: `server.py` (`/ready`), `firestore_service.py` (`write_behavior_event`). Agente: performance/backend.

### P2-21 — Chat da Mentis sem streaming [performance]
Evidência: `mentis_routes.py:1165-1233` (`_TIMEOUT_CHAT=10.0`), resposta inteira esperada antes de aparecer texto — há indicador "pensando" (`MentisPensando`), mas sem streaming token-a-token.
Impacto: etapa 4 — latência percebida pior do que produtos de IA que o aluno já conhece, mesmo custo de IA.
Solução: avaliar streaming (SSE/chunked) separando o campo de texto livre (pode chegar em stream) dos campos estruturados (`sugestoes`/`acao`, que só fecham no final).
Arquivos: `mentis_routes.py`, `ai_service.py`, `MentisChat.jsx`, `MentisWidget.jsx`. Agente: ai/backend/frontend. Dependências: mudança de contrato de API — teste de regressão nos dois consumidores.

### P2-22 — Mapa 3D de missões (~336KB gzip de three.js) em destino provável do "próximo passo" [performance]
Evidência: `build/static/js/871.72dc93b2.chunk.js` — 1,24MB raw/336KB gzip, de `components/mapa3d/*` (`@react-three/fiber`, `@react-three/drei`). Já é `lazy()` corretamente (não é o mesmo bug de P0-2). Ponto de produto: `Hoje.jsx:40` lista "missão atual" como segunda prioridade da ação primária — destino plausível e cedo no funil.
Solução: medir tempo real em 4G simulado antes de agir; se confirmado, considerar fallback 2D/estático para primeira visita ou aparelho fraco.
Arquivos: `Treino.jsx`, `components/mapa3d/`. Agente: performance/frontend. Dependências: medição real antes de priorizar.

### P2-23 — `venda.js` já conectado a dado real, mas só vende a aula ao vivo [growth]
Evidência: `argumentosDaLive`/`argumentoDaLive` (`venda.js:47-146`) usados de verdade em `Hoje.jsx:517-527` e `AulaAoVivo.jsx`, com 16 testes travando a ética. Correto e funcionando — mas `pacoteComDireito`/`economiaDoPacote` (`venda.js:159-216`) não aparecem na loja de Sparks.
Solução: estender a mesma aritmética já testada para a tela de Sparks quando o aluno tiver consumo real que justifique.
Arquivos: `venda.js`, tela da loja de Sparks. Agente: growth/monetization. Dependências: nenhuma técnica — composição de funções já existentes.

### P2-24 — Onboarding 100% autodeclarado, sem triagem real [growth]
Evidência: `onboarding_routes.py:178-193` (`dificuldade_por_frente`) alimenta `prioridade_enem.ranking` só enquanto não há medida real (decisão correta — "opinião nunca sobrescreve contagem"). Mas o cronograma da primeira semana é montado só sobre autodeclaração.
Solução: inserir 3-5 questões reais de triagem dentro do próprio `BemVindo.jsx`, com resultado mostrado na etapa "meta" — resolve também P1-3/P1-7.
Arquivos: `BemVindo.jsx`, `onboarding_routes.py`. Agente: growth/frontend/backend (pedagogy valida as questões). Dependências: banco de questões já existe e é reusado, não é feature nova.

---

## 5. P3 — Baixa prioridade

### P3-1 — Rate limit ausente em 2 rotas de IA [security]
Evidência: `POST /habilidade/{id}/gerar` (`treino_routes.py:548-609`) e `POST /redacao` (`redacao_routes.py:354-389`) protegidas só por Sparks + idempotência, sem `Depends(rate_limit.por_usuario(...))` como a maioria das rotas de IA. Inconsistência, não brecha.
Solução: acrescentar `rate_limit.por_usuario("llm")` por consistência. Arquivos: `treino_routes.py`, `redacao_routes.py`. Agente: backend.

### P3-2 — Formulário de cadastro longo antes do botão do Google [ux]
Evidência: `Login.jsx:276-377` — WhatsApp, checkbox de menor de idade e cupom aparecem antes do "Continuar com Google". Cada campo é justificado no próprio arquivo (linhas 263-275).
Solução: mover WhatsApp/cupom para depois do botão do Google. Arquivos: `Login.jsx`. Agente: ux/growth. Dependências: reabrir decisão já tomada conscientemente — confirmar com o dono.

### P3-3 — Rate limit "llm" (20/hora) compartilhado entre 10 rotas pagas distintas [ai]
Evidência: `rate_limit.py` LIMITES["llm"]=(20,3600), usado por explicação/intervenção da Mentis + 8 outras rotas (`cursos_estudo_routes.py`, `exam_routes.py`, `redacao_routes.py`, `treino_routes.py` etc.) somando no mesmo contador.
Impacto: aluno engajado numa sessão intensa pode ser bloqueado com saldo de sobra.
Solução: elevar o teto (ex. 60-100/hora) ou separar em buckets por família de custo. Arquivos: `rate_limit.py`. Agente: backend/monetization.

### P3-4 — Cache hit cobra preço cheio sem sinalização ao aluno [ai]
Evidência: `mentis_routes.py:233-235,601-603` devolvem `"cache": True/False`, mas nenhum frontend usa esse campo. Decisão de preço deliberada (não reverter) — só falta transparência.
Solução: frase de rodapé opcional ("resposta já preparada para esta questão") quando `cache: true`, sem prometer desconto. Arquivos: `Provas.jsx`, `IntervencaoMentis.jsx`. Agente: monetization/frontend.

### P3-5 — Duplicação de priorização de área entre frontend estático e motor real [architecture]
Evidência: `lib/recomendacao.js:24` — `PRIORIDADE_DAS_AREAS` fixa, já documentada como fallback provisório (linhas 13-17), contra `prioridade_enem.py` (fonte real, ponderada). Baixo risco hoje, diverge se os pesos do backend mudarem.
Solução: quando `GET /api/prioridades` já tiver dado, usar o ranking real em vez da constante; manter a constante só como fallback de cold-start.
Arquivos: `recomendacao.js`, tela que o chama (confirmar `Estudar.jsx` ou `Cursos.jsx`). Agente: frontend, contrato revisado por backend.

### P3-6 — Congelador de ofensiva sem CTA visível no card de risco [growth]
Evidência: `PainelDeProgresso.jsx` mostra ofensiva/risco mas não achei botão de "usar congelador" no trecho lido (ícone importado, sem ação visível). **Não confirmado** — pode existir fora do trecho auditado.
Solução: confirmar primeiro; se ausente, adicionar "Congelar hoje · 50 Sparks" no azulejo de Ofensiva quando `em_risco===true`. Arquivos: `PainelDeProgresso.jsx`. Agente: frontend. Dependências: confirmar se o endpoint de congelamento já existe em `engajamento_routes.py` antes de implementar.

---

## 6. Fases de execução na ordem recomendada

**Fase 0 — Contradições e bugs já no ar** (dias, risco baixo, sem dependência de decisão de produto além de confirmação de texto)
P0-1, P0-2, P1-1, P1-2, P1-12.

> **Status em 2026-09-20**: P0-1, P0-2, P1-1 e P1-12 implementados e
> testados (backend 1329 testes, frontend 182 testes, build de produção
> validado). P1-2 **não** foi implementado — `Cerebro/produto/contas-e-acesso.md`
> já marcava a correção real como "muda a autenticação de todo mundo e
> precisa de aprovação", trava anterior a esta rodada. Ver notas por item
> abaixo (seções 2 e 3).

**Fase 1 — Onboarding cumpre a própria promessa** (maior massa de achados, converge pra uma única frente de trabalho)
P1-3, P1-4, P1-5, P1-6, P1-7, P1-14, P2-5, P2-6, P2-24. Uma única mudança de fundo (caderno pré-selecionado + triagem real dentro do `BemVindo`) resolve P1-3, P1-7 e P2-24 ao mesmo tempo; os demais são ajustes pontuais na mesma tela/rolagem.

**Fase 2 — Motor cognitivo em todo lugar** (o maior achado isolado da auditoria — paralelizável com a Fase 1, times diferentes)
P0-3, P1-9, P1-10, P2-8.

**Fase 3 — Mentis como diferencial visível** (depende parcialmente da Fase 2 estar no ar para não competir por atenção da mesma equipe de ai/backend)
P1-11, P2-4, P2-9, P2-10, P2-11, P2-12, P2-13, P2-21, P3-3, P3-4.

**Fase 4 — Monetização coerente** (fazer depois de Fase 1-2 — não adianta polir preço antes do aluno chegar lá)
P1-13, P1-15, P2-14, P2-15, P2-16, P2-23.

**Fase 5 — Retenção estrutural** (P0-4 é prioridade alta mas depende de decisão de provedor — iniciar a conversa já, não esperar as fases anteriores)
P0-4, P1-8.

**Fase 6 — Robustez de infraestrutura** (paralelizável o tempo todo, equipe separada, reduz risco de reincidência do apagão de 04/09)
P1-16, P1-17, P1-18, P1-19, P2-1, P2-2, P2-3, P2-17, P2-18, P2-19, P2-20, P2-22, P3-1, P3-5, P3-6, P3-2.

Nenhum item propõe aba, rota ou sistema novo — todas as soluções cabem nas cinco áreas existentes (confirmado pelo agente de arquitetura).

---

## 7. Dependências entre tarefas

- **P1-3, P1-7, P2-24** dependem da mesma decisão de produto (o que o `BemVindo` deve entregar) — implementar juntas, não em ordem sequencial.
- **P1-5** depende de reler `Cerebro/ux/padroes-de-tela.md` primeiro — a dobra já foi revertida 3 vezes sem registro de intenção; qualquer mudança nova precisa atualizar `ExplorarOSapiens.test.js` com a razão.
- **P2-7** é resolvido automaticamente por P1-5 + P1-6 — não implementar separadamente.
- **P2-6** é a mesma raiz de P1-7 — uma única implementação resolve as duas entradas do roadmap.
- **P1-2** (Login Google) muda autenticação de todo mundo — precisa aprovação do dono antes de mexer, independente de prioridade técnica.
- **P0-1** e **P1-14** tocam a mesma tela de loja de Sparks (`SparksStore.jsx`) — considerar implementar juntas para um único ciclo de revisão visual.
- **P1-9** e **P1-13** tocam o mesmo arquivo (`Redacao.jsx`) — mesmo motivo, agrupar.
- **P1-16** (fix de `questoes_public`) deveria vir antes de qualquer aumento de tráfego de aquisição — uma campanha bem-sucedida aumenta a frequência com que a janela de 6h expõe o bug.
- **P1-17** (escalar para 2+ máquinas) depende de validar idempotência dos três laços de fundo — não escalar sem esse teste.
- **P2-9** (modelo preview) não é bloqueante hoje, mas deveria ser resolvido antes de qualquer expansão de volume da Mentis (Fase 3), para não empilhar risco de depreciação sobre uma superfície que estará recebendo mais investimento.
- **P2-17** (teste de `set_db`) deveria vir **antes** da Fase 1 e Fase 2, não depois — são exatamente as fases que mais tocam módulos de backend novos, e o teste existe para pegar regressão nelas.
- **P3-6** depende de confirmar se o endpoint de congelamento já existe antes de qualquer implementação.

---

## 8. Agente responsável por tarefa

| Agente | Tarefas |
|---|---|
| **backend** | P0-1, P0-3, P0-4, P1-1, P1-2, P1-10, P1-11, P1-16, P1-18, P2-1, P2-2, P2-3, P2-9, P2-10, P2-11, P2-13, P2-17, P2-18, P2-20, P3-1, P3-3 |
| **frontend** | P0-2, P1-4, P1-7, P1-9, P1-12, P1-13, P1-14, P1-19, P2-4, P2-5, P2-6, P2-12, P2-15, P2-19, P2-24, P3-2, P3-4, P3-5, P3-6 |
| **ux** | P1-3, P1-4, P1-5, P1-6, P1-7, P2-4, P2-5, P2-6, P2-7, P3-2 |
| **growth** | P0-4, P1-2, P1-3, P1-6, P1-7, P1-8, P2-16, P2-23, P2-24, P3-6 |
| **pedagogy** | P0-3, P1-9, P2-8 |
| **ai** | P1-10, P1-11, P2-4, P2-9, P2-10, P2-11, P2-12, P2-13, P2-21, P3-3, P3-4 |
| **monetization** | P0-1, P1-12, P1-13, P1-14, P1-15, P2-14, P2-15, P2-16, P2-23 |
| **architecture** | P1-16, P1-17, P2-17, P2-18, P2-19, P2-20, P3-5 |
| **performance** | P0-2, P1-17, P1-18, P1-19, P2-20, P2-21, P2-22 |
| **security** | P1-1, P2-1, P2-2, P2-3, P3-1 |
| **testing** | P2-17 |
| **backend/infra** | P1-17, P2-3 |
| **decisão do dono (sem agente técnico até decidir)** | P0-1 (texto), P1-2 (aprovação), P1-3 (copy vs. fluxo), P1-14 (onboarding sensível), P1-15 (calibração), P2-13, P2-16, P3-2 |

Vários itens têm mais de um agente porque a solução cruza back/front (ex. P1-9 é "dado já existe, falta renderizar" — ai/backend não precisam agir, só frontend).

---

## 9. Arquivos afetados (visão consolidada)

**Backend — arquivos com mais de um achado**: `mentis_routes.py` (P1-10, P1-11, P2-4, P2-9\*, P2-10, P2-11, P2-12\*, P2-13, P2-18, P2-21), `sparks_store.py` (P0-1, P1-12\*, P2-15, P2-16\*), `redacao_routes.py` (P1-9\*, P1-13, P1-15, P3-1), `server.py` (P1-1\*, P1-17, P2-2, P2-17, P2-20), `treino_routes.py`/`treino_habilidades.py` (P0-3, P2-8, P3-1), `admin_routes.py` (P1-16), `ai_service.py` (P1-11, P2-9, P2-21).

**Frontend — arquivos com mais de um achado**: `Hoje.jsx` (P1-5, P1-6, P1-19, P2-22\*), `Redacao.jsx` (P1-9, P1-13, P1-15\*), `Provas.jsx` (P0-2, P1-7, P2-6, P3-4\*), `MentisWidget.jsx`/`MentisChat.jsx` (P2-4, P2-10\*, P2-11\*, P2-12, P2-21), `Login.jsx` (P1-2, P1-3, P3-2), `BemVindo.jsx` (P1-3\*, P2-5, P2-24), `ProximoPasso.jsx` (P1-4, P1-7\*), `SparksStore.jsx` (P0-1\*, P1-12\*, P1-14, P2-15\*, P2-19), `Estudar.jsx` (P0-2).

**Arquivos novos a criar**: `reengajamento_service.py` + rota de cron (P0-4), `mentis_billing.py` + `mentis_prompts.py` (P2-18, extração), teste de wiring de `set_db` em `aluno/backend/tests/` (P2-17), `public/_worker.js` no frontend (P1-2).

*(\* = arquivo tocado indiretamente ou só como referência de padrão a seguir, não necessariamente editado)*

---

## 10. Critérios de conclusão / validação

| ID | Critério de validação |
|---|---|
| P0-1 | `sparks_store.py:101` não contém mais "por um mês"; texto bate com `Comunidade.jsx:298` e com o comportamento real do backend (flag sem `_ate`). |
| P0-2 | `grep -c "katex" main.*.js` no build de produção volta a 0 (ou ao nível anterior à regressão); bundle principal gzip cai de volta para perto de 300KB a menos. |
| P0-3 | `POST /treino/habilidade/{id}/responder` e `/treino/questoes-geradas/{id}/responder` passam a chamar `revisao_service.registrar_resposta`; `FilaDeRevisao` deixa de ficar vazia para um aluno que só usou o Treino (teste manual ou automatizado com fixture); `ProfessorInvisivel`/`Microdiagnostico` renderizam em `Treino.jsx`/`QuestoesGeradas.jsx`. |
| P0-4 | Existe job agendado que consulta `em_risco` diariamente e envia mensagem real via WhatsApp Business API/Twilio para pelo menos uma conta de teste marcada em risco; log de envio auditável. |
| P1-1 | `curl` sem cookie de sessão para `/api/feed` devolve 401/403. |
| P1-2 | Login com Google completa sem tela branca em teste manual no Chrome com particionamento de storage de terceiros ativado (o cenário documentado no Cerebro). |
| P1-3/P1-7/P2-24 | Um aluno novo, do clique em "Entrar no Sapiens" até a primeira questão real respondida, não passa pela grade de escolha manual de caderno; onboarding inclui pelo menos 1 questão real antes da tela "meta". |
| P1-4 | Os dois botões da seção não apontam mais para a mesma rota quando `passo.rota === "/estudar/provas"`. |
| P1-5 | `ExplorarOSapiens` fechado por padrão para `totalRespondidas === 0`; `ExplorarOSapiens.test.js` atualizado e passando com a nova regra documentada. |
| P1-6 | Cards de mentoria/live não renderizam (ou renderizam reduzidos) quando `totalRespondidas === 0`. |
| P1-8 | Decisão de operação registrada (não é item de código) — critério é ter uma decisão do dono documentada, não uma métrica de código. |
| P1-9 | `evidencias_presentes`/`evidencias_ausentes` aparecem no card de cada competência na tela de resultado de redação, sem exigir a devolutiva paga. |
| P1-10 | `GET/POST /mentis/sessao` não devolve mais `id`/`processo_id`/`erro_id` no `resumo_ui` (checar payload real, não só código). |
| P1-11 | `llm_telemetry.persist` grava `prompt_token_count`/`candidates_token_count` em pelo menos uma chamada real da Mentis em produção; dashboard/consulta simples confirma dado não-nulo. |
| P1-12 | `grep -rn "Sparks" aluno/frontend/src/pages/*.jsx` não retorna mais número literal nos 6 arquivos listados — todos leem de prop/API. |
| P1-13 | Existe opção "correção completa" no fluxo de redação, testada ponta a ponta debitando 235 Sparks numa única confirmação. |
| P1-14 | Tooltip explicativo aparece na primeira animação de ganho de Sparks para uma conta nova (teste manual com conta zerada). |
| P1-15 | Decisão do dono registrada (subir saldo inicial, criar preço-degrau, ou apenas melhorar a orientação de saldo insuficiente) — não é uma correção de código sozinha. |
| P1-16 | Teste de carga/concorrência confirma que `GET /api/questoes` nunca devolve lista vazia durante um `run_firestore_sync` real. |
| P1-17 | `fly scale show -a sapiens-aluno` confirma ≥2 máquinas; teste de regressão dos 3 laços de fundo passando com duas instâncias simuladas. |
| P1-18 | `_HISTORICO_MEMO` nunca mais dá `clear()` total (checar via log/métrica); `tests/test_custo_firestore.py::TestMemoriaDoMotor` continua passando. |
| P1-19 | `Hoje.jsx` renderiza pelo menos a seção de "Próximo Passo" antes de todas as 13 chamadas resolverem (renderização progressiva), OU existe endpoint agregador `GET /hoje` com tempo de resposta medido menor que o pior caso atual. |
| P2-1 a P2-24, P3-1 a P3-6 | Critério padrão: reproduzir a evidência original (endpoint/tela/arquivo citado) e confirmar que o comportamento descrito na "Solução concreta" do item passou a valer — a maioria são correções pontuais e testáveis manualmente contra a evidência já registrada acima; onde o item já pede "confirmar antes" (P1-17, P2-13, P3-6), o primeiro critério é a própria confirmação, não a implementação. |

---

## O que já está sólido (não é achado — não retrabalhar)

Autenticação/sessão (bcrypt, cookie `httponly`+`Secure`/`SameSite`, reset de senha com token único hasheado, defesa contra pre-account-hijacking no Google), autorização por rota (`require_admin`/`require_user` com filtro por `user_id`, sem IDOR encontrado), webhook do Mercado Pago (HMAC-SHA256 constant-time, sempre rebusca `GET /v1/payments/{id}`, nunca confia no corpo), CORS sem wildcard, rate limit de força bruta com `Fly-Client-IP` (não forjável), ausência de secrets versionados, XSS (os únicos `dangerouslySetInnerHTML` são saída do KaTeX sobre conteúdo curado, nunca texto de aluno), LGPD (exportação/exclusão com dono checado, rate limit dedicado, campo de responsável correto para menor), leitura O(1) do Firestore na quase totalidade das rotas (`/diagnostico`, `/prioridades`, `/perfil/painel`, `_agregado_com_cache`), code-splitting por rota em `App.js` (exceto P0-2), `/prioridades` genuinamente ponderado por evidência (não cosmético), dossiê da Mentis genuinamente stateful e transparente ao aluno, ação da Mentis validada contra listas fechadas (nunca URL/id livre), regra ética de gamificação e venda codificada e testada (`TestLinhaEtica`, testes de `venda.js`), estados vazios do produto (`Agenda`, `Comunidade`, `OQueMudou`) já tratados com CTA em vez de card fantasma.

---
Relacionado: [[ecossistema]] · [[inviolaveis]] · [[economia-de-sparks]] · [[mentis]] · [[motor-cognitivo]] · [[navegacao]] · [[custo-de-leitura]] · [[superado]]
