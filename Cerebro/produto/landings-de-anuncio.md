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
| `/ads/diagnostico` | curiosidade | "Você sabe por que está errando no ENEM?" | Fazer diagnóstico gratuito |
| `/ads/mesmo-erro` | dor / repetição | "Você estuda, faz questões… e continua errando as mesmas coisas?" | Descobrir meus padrões de erro |
| `/ads/10-questoes` | desafio | "10 questões. Descubra onde você realmente está perdendo pontos." | Começar desafio |
| `/ads/como-voce-estuda` | diferenciação | "Você sabe quanto acertou. Mas sabe por que errou?" | Ver meu diagnóstico |

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

## Os componentes

`components/ads/` — `AdsLandingLayout` (a casca: origem, rastreio, CTA
grudente, rodapé mínimo), `Hero`, `CTA`, `DiagnosticPreview`,
`ErrorAnalysisPreview`, `QuestionProgress`, `FeatureFlow`, `contexto.js`.
As páginas ficam em `pages/ads/`.

**`DiagnosticPreview` monta `components/questao/Alternativas`** — a peça real
do produto, dentro de `.card-sapiens .leitura-clara` como em `Provas.jsx`. O
envelope claro não é estética: `.alternativa` tem papel branco próprio e o
texto dentro usa `text-zinc-700`, que a camada de tradução CLAREIA fora de
`.leitura-clara`. Sem o envelope, enunciado claro sobre papel branco — ver
[[sistema-visual]].

> **O que a landing mostra é o componente que a pessoa vai tocar depois de
> criar a conta.** Uma captura redesenhada à mão não prova nada, e é a coisa
> que quem chega de anúncio está tentando decidir.

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

**O que ainda NÃO existe, e precisa ser dito:** o backend **não grava UTM no
usuário** no cadastro. A atribuição hoje acontece por `promo_code` (cupom /
influencer) e por `campanha_id` no clique. Os `utm_*` chegam até a URL do
`/login` e param ali. Fechar essa ponta é mudança em `auth`/`models`, não em
landing.

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

`CliqueCTA` é evento customizado de propósito: `Lead` no Meta significa
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

## Duas armadilhas já pagas, medidas no navegador

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

## Como criar a quinta variante

1. Uma linha em `ROTAS` (`lib/rotas.js`) e uma `<Route>` no `App.js`, com
   título de aba que ecoe o que o anúncio prometeu.
2. Um arquivo em `pages/ads/`, montando `AdsLandingLayout` + `Hero` + as peças
   de demonstração que o ângulo pedir.
3. `variante` é a chave do rastreio: use o mesmo slug da rota.
4. Nada mais. Origem, clique, rastreio, CTA grudente, `noindex` e rodapé vêm
   da casca.

**Não crie aba, item de menu ou link de dentro do produto para elas.**

---
Relacionado: [[marca]] · [[afiliados]] · [[sistema-visual]] · [[mobile]] · [[navegacao]] · [[custo-de-leitura]] · [[contas-e-acesso]]
