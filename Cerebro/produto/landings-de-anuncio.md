---
tags: [produto, aquisicao, marketing, frontend]
atualizado: 2026-09-21
---

# Landings de anúncio (`/ads/*`)

Quatro páginas que recebem tráfego pago do Meta Ads e levam a **uma** ação: o
cadastro. Não são tela do produto, não entram na navegação e não são
alcançáveis de dentro do Sapiens. Antes de mexer aqui leia [[marca]] (a copy
do produto é StoryBrand, e estas páginas seguem a mesma régua) e [[afiliados]]
(o funil de aquisição que já existia e que estas páginas reaproveitam).

## As quatro rotas, e por que são quatro

| Rota | Ângulo | Manchete | CTA |
|---|---|---|---|
| `/ads/diagnostico` | curiosidade | "Você sabe por que está errando no ENEM?" | Fazer diagnóstico grátis |
| `/ads/mesmo-erro` | dor / repetição | "Você continua errando a mesma coisa?" | Descobrir meus padrões |
| `/ads/10-questoes` | desafio | "10 questões podem revelar onde você está perdendo pontos." | Começar diagnóstico |
| `/ads/como-voce-estuda` | diferenciação | "Você sabe quanto acerta. Mas sabe por que erra?" | Descobrir meu perfil |

São variantes da **mesma oferta** para ângulos de criativo diferentes — não
quatro produtos. Elas dividem a casca, o sistema visual e o destino; mudam
copy e composição. Quem acrescentar seção a uma delas pergunte primeiro se a
seção pertence às quatro: se pertencer, ela é da casca.

## O fluxo de conversão, e a única coisa que ele NÃO pode prometer

```
anúncio → /ads/<variante> → /login?…&novo=1 → cadastro → /bem-vindo → /hoje
```

> [!warning] **Não existe diagnóstico anônimo no Sapiens, e não é descuido.**
> Responder questão grava evento em `students/{uid}/behavior`, e não há perfil
> sem conta: `GET /diagnostico` exige `require_user`, e todo fluxo de resposta
> vive atrás de `ProtectedRoute`. Então o CTA leva ao **cadastro**, e a linha
> sob o botão diz isso ("criar conta leva menos de um minuto e não pede
> cartão"). Esconder o cadastro compraria o clique e perderia a pessoa na tela
> seguinte — o pior lugar possível para perdê-la, porque a mídia já foi paga.

**"10 questões" é verdade medida, não arredondamento de anúncio.**
`RODADA_TAMANHO = 10` existe nos dois lados (`pages/Provas.jsx` e
`backend/firestore_routes.py`), e a rodada de dez fecha com devolutiva
determinística — acertos, evolução sobre a rodada anterior e padrões de erro,
sem IA e sem custo. Se esse número mudar no produto, muda aqui também: a
página inteira do ângulo "desafio" está pendurada nele.

Duas regras de conteúdo que estas páginas herdam e não podem relaxar:

- **Nada de resultado, número, depoimento ou estatística inventada.** A
  questão de exemplo é escrita para a landing, e a página declara isso em
  texto visível (`ads-aviso-ilustrativo`). "4 erros → 3 padrões" é a
  aritmética do próprio exemplo desenhado ao lado, não uso real.
- **Os nomes da ontologia não aparecem.** O último degrau da análise fala a
  língua do vestibulando ("dificuldade em interpretar informações de um
  gráfico"), igual o produto já fala.

## As quatro demonstrações (2026-09-21, 2ª passada)

A primeira versão era estática e parecia quatro páginas institucionais com um
botão. Hoje **cada página tem um mecanismo visual próprio**, e o mecanismo é o
argumento — quem não ler uma linha de texto entendeu o produto:

| Página | Mecanismo | Peça |
|---|---|---|
| `/ads/diagnostico` | questão → marca errada → **analisando** → erro → habilidade → próximo passo | `DemoAnaliseDoErro` |
| `/ads/mesmo-erro` | 3 erros de matérias distantes → 3 linhas **convergem** → 1 padrão → habilidade | `DemoPadraoComum` |
| `/ads/10-questoes` | a pessoa **responde** de verdade → leitura do que aquela escolha indica | `DemoQuestao` |
| `/ads/como-voce-estuda` | 72% **vira** 28% → 4 naturezas → padrões → habilidades → próxima semana | `DemoDecomposicao` |

**O passo do meio é sempre o produto inteiro.** Um corretor comum vai de
"marcou C" para "errado" num quadro; o Sapiens põe uma etapa entre os dois, e
é essa etapa que a landing precisa deixar VER acontecendo. Numa demo que pula
direto para o veredito, o que se demonstra é um gabarito.

### As primitivas compartilhadas

`components/ads/`:

- **`movimento.js`** — `useNaTela` (apareceu na tela?) e `useRoteiro` (o passo
  de uma sequência temporizada). **Uma primitiva, quatro demos**: escrever o
  relógio quatro vezes é como se ganham quatro comportamentos diferentes para
  a mesma coisa. Durações são um ARRAY por passo, não um número — "analisando"
  respira, um achado quer ser lido, o último segura antes do laço.
- **`Demo.jsx`** — a moldura: selo, trilho de passos, botão de rever,
  `FaixaDeAnalise`, `Achado`, `LinhaRevelada`.
- **`CadeiaDoErro`** (Questão → … → Próximo estudo), **`ComoFunciona`** (01/02/03),
  **`CtaFinal`** — as três seções que as quatro páginas dividem.
- `AdsLandingLayout`, `Hero`, `CTA`, `contexto.js` — a casca, inalterada.

Substituíram `DiagnosticPreview`, `ErrorAnalysisPreview`, `QuestionProgress` e
`FeatureFlow`, que foram **apagados** — peça superada que fica no repo é a
próxima pessoa importando a errada.

### A questão é desenhada pelo produto de verdade

Duas das quatro demos montam `components/questao/Alternativas` — a MESMA peça
das provas do ENEM, do treino e dos cursos: mesmo verde, mesmo vermelho, mesmo
pé sólido, mesma letra que vira ícone. Basta mudar `selecionada`/`resultado`
conforme o passo.

> **`.leitura-clara` em volta é obrigatório.** `.alternativa` tem papel branco
> próprio e o texto usa `text-zinc-*`, que a camada de tradução CLAREIA fora
> desse envelope. Sem ele: texto claro sobre papel branco. Ver
> [[sistema-visual]].

> **O que a landing mostra é o componente que a pessoa vai tocar depois de
> criar a conta.** Uma captura redesenhada à mão não prova nada, e é
> exatamente o que quem chega de anúncio está tentando decidir.

### A demo interativa não toca em nada do produto

`/ads/10-questoes` é a única em que o visitante responde. Tudo local, e cada
"não" é deliberado: **não** chama API, **não** grava em `behavior`, **não**
chama Gemini, **não** consome Sparks, **não** lê o Firestore. Verificado no
navegador: zero requisição para `/api/` durante a interação. O que a pessoa
responde ali morre no navegador dela.

O CTA muda de verbo depois da interação ("Continuar com meu diagnóstico"),
porque quem respondeu já começou.

## Tracking — o que foi reaproveitado e o que ainda não existe

**Reaproveitado.** `POST /track/click` (público, com rate limit por IP) já
existia para o link de influencer; a casca o chama com `{campanha_id,
utm_source}` e o evento cai em `growth_events` como `campaign_click`, que é o
que `campaigns.resumo_comparativo` já sabe ler.

> **Só com `campanha_id` na URL.** Sem ele, `registrar_clique` grava
> `referral_click` sem código e sem campanha — uma linha no Mongo que nenhum
> relatório consegue atribuir a nada. O `campanha_id` sai de
> `campaigns.criar` (`camp_<hex>`) e é o admin quem cola na URL do anúncio.

**A origem viaja inteira.** `lib/campanha.js` lê a query, guarda 30 dias no
`localStorage` (mesma janela e mesma degradação silenciosa de
`lib/atribuicao.js`) e cola tudo no destino do CTA, com `novo=1` por último —
é ele que faz `Login.jsx` abrir em "Criar conta" e não em "Entrar". A query da
URL vence a guardada; a guardada só preenche o que falta.

> A lista branca de "só o que o produto lê hoje" foi recusada de propósito.
> No dia em que o cadastro passar a gravar UTM, o parâmetro já teria sido
> jogado fora três telas antes. O que ninguém lê não custa nada; o que foi
> descartado custa uma campanha. `lib/campanha.test.js` trava isso.

**O UTM passa a ser gravado no usuário no cadastro (2026-09-21).** Até aqui os
`utm_*` chegavam até a URL do `/login` e paravam ali — esta era a pendência
mais concreta do doc, e agora está fechada:

- `models.PARAMS_DE_ORIGEM` é a MESMA lista de `lib/campanha.js`
  (`PARAMS_DE_ORIGEM`) — as duas têm de continuar idênticas, ou um lado
  descarta o que o outro grava.
- `Login.jsx` lê a origem com `lib/campanha.origemParaEnvio(params)` (URL
  vence, guardado de 30 dias preenche o resto — mesma regra de
  `destinoComOrigem`) e manda em `signup()`/`loginGoogle()` via `extras.origem`.
- No backend, `auth._registrar_origem` faz um `$set` separado, DEPOIS do
  `insert_one`, mesmo padrão de `_registrar_cupom`. No cadastro por e-mail os
  campos vêm tipados em `SignupRequest` (Pydantic valida); no login por Google
  chegam como `dict` solto no `Body`, e `auth._origem_filtrada` é quem garante
  que só as chaves de `PARAMS_DE_ORIGEM` entram no Mongo.
- Atribuição continua tendo TRÊS fontes independentes, que não se substituem:
  `promo_code` (cupom/influencer/indicação), `campanha_id` via `POST
  /track/click` (o clique) e agora os campos de `User` (o cadastro). Cruzar
  as três é o que fecha clique → cadastro → compra por campanha.

**Meta Pixel: a arquitetura existe, o pixel não está ligado.**
`lib/rastreio.js` é a porta única — **nenhum componente chama `fbq`**. Sem
`REACT_APP_META_PIXEL_ID` configurado ele é inerte: zero script de terceiro,
zero requisição, zero cookie. Com o id, injeta o `fbevents.js` **depois da
primeira pintura** e só em `/ads/*`, nunca dentro do app do aluno. Eventos:
`PageView` (uma vez por variante, com trava contra o duplo `useEffect` do
StrictMode) e o custom `CliqueCTA` com `{variante, posicao}` — `posicao` é o
que diz se a página converte na primeira dobra ou depois da demonstração.

> [!danger] Preencher `REACT_APP_META_PIXEL_ID` é decisão do dono, com
> revisão jurídica — não efeito colateral de um deploy.
> O Sapiens atende menor de idade e tem política de privacidade publicada;
> rastreio de terceiro sem consentimento é exatamente o ponto que
> `legal-privacy` precisa olhar antes. A variável não existe em nenhum `.env`
> hoje, e esse é o estado esperado.

O vocabulário são três nomes, em `lib/rastreio.js`: `landing_view` (uma vez
por variante), `landing_demo_interaction` (só `/ads/10-questoes` tem emissor —
é a única com algo a tocar) e `landing_cta_click` (com a `posicao` na página).

**`landing_signup_start` não existe, e a ausência é decisão.** Ele aconteceria
em `/login`, que é tela do produto e não landing; instrumentá-lo exigiria
importar o rastreio dentro de `Login.jsx` — espalhar analytics pelo app por um
sinal que hoje é indistinguível de `landing_cta_click`, já que o CTA navega
direto para o cadastro sem tela intermediária onde desistir. Quando houver
etapa no meio, ele entra em `rastreio.js` e é chamado de lá.

Evento customizado de propósito: `Lead` no Meta significa
cadastro concluído, e usá-lo para um clique infla a conversão do anúncio com
gente que só tocou no botão. "Início do diagnóstico" não tem evento porque ele
acontece dentro do app, atrás da sessão — instrumentá-lo espalharia analytics
pelas telas de estudo e carregaria script de terceiro em todas elas.

## As decisões de arquitetura que custam caro para desfazer

**As rotas vivem só em `lib/rotas.js`, não em `rotas_do_app.py`.** Aquele
arquivo existe porque o BACKEND emite endereço de tela como dado (o bloco do
cronograma, o destino da Mentis); nenhum backend tem o que fazer mandando um
aluno para uma landing de anúncio. `test_rotas_do_app.py` compara uma lista
explícita de chaves e não quebra com chaves só do frontend.

**`/ads/` entra em `SEM_NAVEGACAO_PREFIXO`.** A barra não é desenhada para
quem não tem sessão, mas um aluno logado que caísse num anúncio veria a moldura
do app em volta de uma peça de aquisição.

**`noindex, nofollow`, editando a tag do `index.html` e devolvendo ao sair.**
Quatro variantes da mesma oferta indexadas competem com `/` pelas mesmas
palavras e mostram no Google um texto que só faz sentido depois de um
criativo. Devolver o valor no `unmount` importa numa SPA: sem isso o
`/login` — e todo o app depois dele — herdaria o `noindex`.

**Nenhuma chamada de API no render.** Diferente da `Landing.jsx` da marca (que
busca o catálogo de preços), aqui não há preço a dizer e nada pode demorar por
causa da rede. Consequência direta: **zero leitura do Firestore por visitante
de anúncio** — ver [[custo-de-leitura]].

**Preguiçosas, uma por variante.** Não porque o aluno raramente abra, mas
porque quem abre uma nunca abre as outras três. Medido no build: 1,5–3,2 kB
gzip por variante, mais ~3,1 kB do pedaço compartilhado.

## As armadilhas já pagas, todas medidas no navegador

Nenhuma destas apareceu lendo código. Todas custaram uma medição, e todas
falham em silêncio — a página continua abrindo.

**`space-y-*` conta filhos pelo DOM, não pelo fluxo.** Ele é
`& > * + * { margin-top }`, então um filho `absolute` — que não ocupa altura
nenhuma — mesmo assim faz o irmão seguinte ganhar a margem. A linha
"Aguardando a resposta…" estava dentro do `space-y-2.5` e o cartão oscilava
exatos 10px ao longo do roteiro. A cura são dois contêineres: um posiciona, o
outro espaça.

**Duas classes com a mesma especificidade: vence a de baixo.** Aconteceu
DUAS vezes no mesmo arquivo. (1) `.ads-erro-cartao { opacity: 0 }` declarado
depois de `.ads-revela-on` anulava a revelação, e os três cartões de erro
ficavam invisíveis a demo inteira — a página abria com um cartão vazio. (2) A
media query `md` da seta da cadeia estava ANTES da regra base, e a seta do
desktop apontava para baixo. Regra: **uma classe pinta, outra anima, e elas
nunca disputam a mesma propriedade**; e bloco de celular sempre antes do `md`.
É o mesmo mecanismo de [[mobile]].

**Altura reservada é medida por peça, não arredondada.** A faixa de análise
reserva a altura do estado mais cheio DAQUELA demo (140px nas automáticas,
204px na interativa, que tem um parágrafo de fecho a mais). E o **cabeçalho**
reserva 30px: a demo interativa só oferece "rever" depois da resposta, e sem a
reserva o cabeçalho pulava de 15 para 30px no instante do toque, empurrando a
questão bem quando o olho estava na alternativa recém-marcada. Só apareceu
medindo uma peça e não as quatro.

**`pathLength="1"` é o que faz as linhas convergentes funcionarem.** Ele
normaliza o comprimento da curva, e só então `stroke-dasharray: 1` é um traço
do tamanho da linha inteira. Sem ele, "1" é uma unidade do viewBox e as curvas
aparecem pontilhadas — e as três têm comprimentos diferentes, então nenhum
valor fixo serviria para as três.

**O texto da alternativa tem orçamento de ~26 caracteres a 390px.**
`.alternativa` gasta 32px de respiro, 30px de letra e 12px de vão, dentro de
três contêineres com respiro próprio. Com alternativas de duas linhas o cartão
media 481px e empurrava a análise 164px abaixo da dobra: quem não rolasse via
um quiz — o produto que o Sapiens justamente não é.

**Duas armadilhas da primeira passada, que continuam valendo**

**O grudente estava cobrindo o CTA final.** A primeira versão observava só o
botão do herói, então a página terminava com dois botões idênticos empilhados
— o "múltiplos CTAs concorrentes" que estas páginas existem para não ter.
Hoje um observador só recebe TODOS os `[data-cta-inline]` e o grudente aparece
apenas quando nenhum deles está na tela.

**`IntersectionObserver` pode não entregar o primeiro aviso.** A primeira
notificação só chega numa oportunidade de renderização; numa aba segurada pelo
navegador ela não chega. Medido: o contador de `QuestionProgress` ficou em
**0/10 por seis segundos** com o cartão inteiro visível, e só andou quando uma
rolagem forçou um quadro. A cura é a rede de 1,4s em `QuestionProgress` — num
navegador de verdade ela nunca roda, e existe porque um demo congelado em zero
não é uma animação que faltou: é a landing afirmando que o produto trava.

## Os códigos de campanha, e a pegadinha que anula o rastreio

As URLs de anúncio em uso carregam `&convite=` além dos UTM:

| Página | Código |
|---|---|
| `/ads/diagnostico` | `ADS-DIAG` |
| `/ads/mesmo-erro` | `ADS-ERRO` |
| `/ads/10-questoes` | `ADS-10Q` |
| `/ads/como-voce-estuda` | `ADS-DIF` |

Desde 2026-09-21 a casca guarda esse código **na chegada** (`salvarAtribuicao`,
reusando `lib/atribuicao.js`), e não só quando a pessoa alcança `/login`: quem
clica no anúncio, lê a landing, fecha a aba e volta dias depois pelo link sem
parâmetro perdia a atribuição em silêncio.

> [!danger] O código precisa EXISTIR em `/admin/promo-codes`, senão nada é
> atribuído e nada avisa.
> `_bonus_de_cadastro` chama `validar_e_registrar_uso`; código inexistente ou
> desativado devolve `None`, o cadastro segue normal com o bônus padrão e
> `users.promo_code` fica vazio. Nenhum erro, nenhum log — só um relatório
> vazio três semanas depois.
>
> **Crie com `sparks_amount: 100`, nunca menos.** O cupom **substitui** o
> bônus de boas-vindas, não soma a ele, e o padrão é
> `firestore_service.SPARKS_INITIAL_BALANCE = 100`. Com 100 o cupom é puro
> rastreio, custo zero, e quem veio do anúncio recebe o mesmo que um cadastro
> orgânico. Abaixo disso, quem custou dinheiro para trazer recebe MENOS.

Com o cupom de pé, `/admin/promo-codes` mostra por código quantas e QUAIS
contas vieram dali (nome, e-mail, data), e o vínculo fica na conta para
sempre. Cruzando com `/admin/transacoes` fecha até a compra.

## O funil pós-clique — o que a auditoria de 2026-09-21 consertou

Uma auditoria adversarial (cinco lentes independentes, cada achado entregue a
um refutador) rodou contra as quatro landings antes da primeira verba. **Dos
achados que chegaram a ser verificados, nenhum sobreviveu como bloqueador** —
os refutadores acharam mecanismo correto e severidade inflada em todos. O que
segue é o que sobrou depois da refutação, e foi consertado.

### O aluno novo não chegava à rodada que o anúncio promete

`/treino/habilidades` devolve as 56 habilidades SEMPRE, inclusive para a conta
criada há dez segundos, com `respondidas: 0` e `classificacao: "sem_dados"`.
`missaoAtual` procura a primeira que não seja `"forte"` — e `"sem_dados"`
passa. Ela devolvia **HAB-01, nunca `null`**.

Consequência: o degrau "praticar" de `ProximoPasso` era **inalcançável**, e
quem acabava de se cadastrar pelo anúncio abria o Painel em *"Território novo
— Ordenar valores numéricos em sequência crescente/decrescente"*, com botão
para o mapa 3D (chunk de 1,25 MB / 335 kB gzip, mais pesado que o `main.js`).
O anúncio prometia 10 questões; a primeira tela oferecia uma habilidade
sorteada por ordem alfanumérica de id.

> A intenção já estava escrita e não estava implementada — o próprio
> comentário do degrau dizia "quem ainda não tem medida nenhuma não tem lacuna
> conhecida". O teste é sobre DADO, não sobre a lista: 56 habilidades
> intocadas são 56 linhas de catálogo, não uma medida do aluno.
> `ProximoPasso.test.js` trava isso.

### A origem já era gravada e ninguém lia

`auth._registrar_origem` carimba os sete campos de `models.PARAMS_DE_ORIGEM`
no documento do usuário, nos **dois** caminhos de cadastro (`auth.py:339`
e-mail, `auth.py:475` Google). O dado existia desde sempre e **não havia uma
única tela lendo**.

`components/PainelDeAquisicao.jsx` (montado em `/admin/users`) agrega por
`utm_content` e mostra cadastros, quantos responderam, questões e dias ativos
por ângulo. É **frontend puro**: `GET /admin/users` já devolve o documento
inteiro do aluno (`admin_routes.py:76`), então não há endpoint novo, nem
segunda fonte para a mesma verdade, nem deploy de backend.

> **Isso torna os cupons `ADS-*` opcionais.** A atribuição por `utm_content`
> não depende deles. O cupom continua útil (dá a tela de
> `/admin/promo-codes`), mas já não é o que separa "gastou e aprendeu" de
> "só gastou".

> [!danger] Não invente coluna que o payload não tem.
> A primeira versão do painel tinha "Compraram", lendo `total_gasto_cents` e
> `compras` — campos que `/admin/users` **não devolve**. A coluna teria
> marcado zero em toda linha para sempre, sem nenhum sinal de que o campo não
> existia. Medida falsa é pior que medida ausente: a ausente você vai
> procurar. Compra mora em `/admin/transacoes`.

### As páginas legais se declaravam inacabadas — em produção

`/termos` e `/privacidade` são os **dois únicos links** do rodapé das
landings, e estampavam *"Documento em finalização. Faltam os dados de
identificação do responsável."* O comentário de `lib/operador.js` dizia "AÇÃO
NECESSÁRIA ANTES DO BETA PÚBLICO" — **comprar tráfego é cruzar essa linha**,
e o Sapiens fala com menor de idade.

O defeito não era falta de preenchimento, era o MODELO: ele pressupunha
pessoa jurídica, e quem opera como pessoa física não tem razão social nem
CNPJ — o aviso ficaria aceso para sempre, sem nunca haver o que preencher.
Hoje `OPERADOR.tipo` é explícito e cada tipo tem a sua lista de obrigatórios;
`identificacaoDoOperador()` é o que as páginas legais imprimem, em vez de
`razaoSocial || nomeFantasia`, que dizia "o controlador é Sapiens" — uma
marca, não alguém a quem o titular possa se dirigir (LGPD art. 9º).

> Endereço não é obrigatório em nenhum dos dois tipos, de propósito: em pessoa
> física ele é o endereço residencial de alguém, e publicá-lo cria para o
> operador o risco que a LGPD existe para reduzir. **Virar pessoa jurídica é
> trocar `tipo` e preencher dois campos.**

### O login com Google morre calado no navegador do Instagram

100% do tráfego pago abre a página no navegador embutido do aplicativo.
`signInWithPopup` (`lib/firebase.js:54`) depende de armazenamento de terceiro
para devolver o resultado, e é isso que esses navegadores particionam. No
Android o Firebase falha rápido e há erro tratável; **no iOS a janela abre, a
pessoa escolhe a conta e a tela fica branca** — sem exceção, sem nada para o
`catch` pegar, com o botão ainda escrito "Abrindo o Google…".

`lib/navegador.js` detecta o navegador embutido por `userAgent` e faz duas
coisas: avisa **antes** do clique que o caminho mais garantido é o cadastro
por e-mail, e encurta de 25s para 8s a espera até o aviso de popup travado.

> **A detecção informa, nunca bloqueia.** `userAgent` é palpite: falso
> positivo custa um aviso a mais, falso negativo devolve o comportamento
> anterior. Nenhum dos dois quebra o cadastro. A cura de verdade continua
> sendo o `_worker.js` reencaminhando `/__/auth/*` — ver [[contas-e-acesso]],
> que muda a autenticação de todo mundo e segue pendente de aprovação.

## Como criar a quinta variante

1. Uma linha em `ROTAS` (`lib/rotas.js`) e uma `<Route>` no `App.js`, com
   título de aba que ecoe o que o anúncio prometeu.
2. Um arquivo em `pages/ads/`, montando `AdsLandingLayout` + `Hero` + a demo
   do ângulo + `CadeiaDoErro` + `ComoFunciona` + `CtaFinal`.
3. A demo nova usa `useRoteiro` e a moldura `Demo` — **não invente um segundo
   relógio**.
4. `variante` é a chave do rastreio: use o mesmo slug da rota.
5. Origem, convite, clique, rastreio, CTA grudente, `noindex` e rodapé vêm da
   casca. Nada disso se repete.

**Não crie aba, item de menu ou link de dentro do produto para elas.**

## Como testar

```bash
CI=true npx craco test --watchAll=false   # em aluno/frontend
yarn build
```

`lib/campanha.test.js` trava a preservação de query; `components/ads/
movimento.test.js` trava a decisão de `prefers-reduced-motion` — e ele existe
porque **o painel do navegador não emula essa preferência** e o
`javascript_tool` roda em mundo isolado, então sobrescrever `matchMedia` de
fora não é visto pelo React da página. O que não dá para conferir no navegador
tem de virar teste.

No navegador, as medições que valem: altura do cartão de demo ao longo do
roteiro inteiro (tem de ser constante), `scrollWidth - clientWidth` a 320/375/
390/430px (tem de ser 0), e o detector de texto espremido de [[mobile]].

---
Relacionado: [[marca]] · [[afiliados]] · [[sistema-visual]] · [[mobile]] · [[navegacao]] · [[custo-de-leitura]] · [[contas-e-acesso]]
