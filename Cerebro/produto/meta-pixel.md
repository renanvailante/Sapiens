---
tags: [produto, aquisicao, marketing, frontend, privacidade]
atualizado: 2026-09-22
---

# Meta Pixel

O rastreio de anúncio do Meta (Facebook/Instagram Ads), **ligado em 22/09/2026**
por decisão do dono. Até essa data o produto não tinha analytics de frontend
nenhum — a arquitetura existia em `lib/rastreio.js`, inerte, esperando um id.

Pixel `3603769776438017`, em `REACT_APP_META_PIXEL_ID` (`aluno/frontend/.env`).

## A regra que organiza tudo: uma porta só

**Nenhum componente chama `fbq`.** Os componentes chamam funções de
`aluno/frontend/src/lib/rastreio.js`, e é lá que se decide o que vai para onde.
No dia em que entrar Meta CAPI, GA4 ou outro destino, muda aquele arquivo e
mais nenhum — mesma disciplina de `lib/monitoring.reportarErro`.

A consequência prática: **para saber tudo que o Sapiens manda para a Meta,
basta ler um arquivo.** Isso é o que torna a pergunta "que dado sai daqui?"
respondível — e ela vai ser feita, porque o produto atende menor de idade.

## Onde o pixel carrega, e a linha que ele não atravessa

| Superfície | Carrega? | Quem dispara |
|---|---|---|
| `/ads/*` (6 landings) | sim | `landingView`, em `AdsLandingLayout` |
| `/` (landing da marca) | sim | `PixelDeRota` |
| `/login` | sim | `PixelDeRota` |
| **todo o resto do app** | **não** | — |

> [!danger] **O pixel não entra no app do aluno, e isso não é detalhe de
> implementação.**
> Depois do cadastro não há mais campanha a medir, e quem está ali é aluno —
> boa parte menor de idade — estudando. Carregar script de terceiro e cookie da
> Meta numa tela de estudo troca privacidade e peso por um dado que ninguém
> pediu. A fronteira é `ROTAS_PUBLICAS` em `lib/rastreio.js`: **lista fechada**,
> comparada por igualdade exata. Uma regra do tipo "tudo que não é protegido"
> faria a próxima tela pública nascer com pixel sem ninguém decidir.

**O snippet oficial do Meta não está no `index.html`, de propósito.** Ele
carregaria em toda página e dispararia `PageView` uma vez só — numa SPA isso é
o pior dos dois mundos: pixel na tela de estudo e funil cego a partir do
segundo clique. Quem cola aquele bloco no HTML desfaz as duas decisões acima de
uma vez, sem que nada na tela mude.

### O `PageView` numa SPA, e a duplicata que espreita

`PixelDeRota` (`components/PixelDeRota.jsx`) é montado **dentro do
`<BrowserRouter>` e fora do `<Routes>`** — dentro de uma rota ele desmontaria a
cada navegação e perderia a memória de onde a pessoa estava. Ele guarda o
último caminho contado num `ref`, porque o `useEffect` roda duas vezes no
StrictMode do desenvolvimento e sem isso toda visita nasceria dupla.

> **`/ads/*` fica FORA de `ROTAS_PUBLICAS`, e a ausência é a decisão.** Aquelas
> páginas já têm emissor próprio, que manda o `PageView` **com a variante
> junto**. Acrescentá-las à lista contaria toda visita de anúncio duas vezes —
> e o custo por visita da campanha apareceria pela metade no relatório, que é o
> tipo de erro que ninguém percebe porque o número fica bonito.
> `lib/rastreio.test.js` trava isso.

Medido no navegador em 22/09: `/` → clique em "Entrar" → `/login` dispara um
`PageView` novo sem recarregar a página; uma rota fora da lista dispara zero;
`/ads/diagnostico` dispara exatamente um `PageView` + um `landing_view`.

## O vocabulário de eventos

| evento | tipo | quando |
|---|---|---|
| `PageView` | padrão | cada tela pública vista (ver tabela acima) |
| `Lead` | padrão | **cadastro concluído** — a conta existe |
| `landing_view` | custom | a landing de anúncio abriu (com a variante) |
| `landing_demo_interaction` | custom | a pessoa tocou na demo (só `/ads/10-questoes`) |
| `landing_cta_click` | custom | clique no CTA, com a posição na página |

**Por que os três de landing são `trackCustom` e o `Lead` não.** `Lead`, no
vocabulário do Meta, significa cadastro CONCLUÍDO — é o evento que o
Gerenciador de Anúncios usa para otimizar campanha por cadastro. Usá-lo para um
CLIQUE inflaria a conversão com gente que só tocou no botão, e depois é o
algoritmo do Meta que otimiza em cima dessa mentira. Então clique é nome
customizado, e `Lead` só é disparado quando a conta nasceu de verdade.

### `conta_criada`: o botão do Google entra E cadastra pela mesma porta

`POST /auth/google` devolve `conta_criada` (`aluno/backend/auth.py`) porque o
`user` que ele retorna é **idêntico** nos dois casos — o frontend não tem como
distinguir um cadastro novo de um aluno antigo voltando. Sem essa flag, todo
retorno pelo Google viraria uma conversão nova no relatório, e a campanha
apareceria convertendo gente que já é cliente.

`Login.jsx` dispara `cadastroConcluido("google")` só quando a flag vem
verdadeira, e `cadastroConcluido("email")` quando o `signup` por e-mail
completa. **Degrada seguro:** se o backend em produção ainda não tiver a flag,
`contaCriada` é `false` e o `Lead` simplesmente não dispara — perde-se sinal,
nunca se inventa conversão.

> **Nada que identifique o aluno vai junto.** Nem e-mail, nem nome, nem
> telefone, nem `user_id` — o único parâmetro é `content_name: "email" |
> "google"`, que é dado do fluxo. O Meta aceitaria os campos de correspondência
> avançada (`em`, `ph` com hash) e é exatamente por isso que a recusa está
> escrita no código e travada em teste: mandar dado de contato de menor de
> idade para uma rede de anúncios não pode ser algo que alguém faz sem querer.

**`landing_signup_start` continua não existindo.** Ele aconteceria em `/login`,
e hoje é indistinguível de `landing_cta_click` — o CTA navega direto para o
cadastro, sem tela intermediária onde desistir. Quando houver etapa no meio,
ele entra em `rastreio.js` e é chamado de lá.

## O que ligar/desligar custa

Esvaziar `REACT_APP_META_PIXEL_ID` e buildar desliga **tudo**: zero script de
terceiro, zero requisição, zero cookie, sem caçar chamada nenhuma pelo código.
É por isso que o id é variável de ambiente e não constante no JS.

Como `.env` **não é versionado** e o deploy publica a árvore
([[deploy]]), o pixel só existe em produção se a variável estiver no `.env` da
máquina que builda. Um build feito de outro lugar sai sem pixel e sem erro
nenhum — o sintoma é "o Gerenciador de Eventos não recebe nada", nunca uma
falha visível.

## O que o pixel quebrou na Política de Privacidade (22/09/2026)

Ligar o pixel tornou **falsas** duas frases que já estavam publicadas:

- §9: *"não há rastreadores de terceiros no produto"*;
- §4 (adolescentes): *"não usamos os dados para publicidade dirigida, de
  nenhum tipo"*.

Nenhuma das duas apareceu no code review — elas moram em `pages/Privacidade.jsx`,
que nada no fluxo do pixel importa. **Toda mudança de rastreio tem de reler
aquele arquivo**, e esta é a lição mais cara desta entrada: a promessa pública
do produto é um arquivo de código como outro qualquer, e ele não quebra o build
quando vira mentira.

O texto foi corrigido no mesmo dia e declara em voz alta que afirmava o
contrário até ali. As seções 2, 3, 5 e 9 passaram a descrever o pixel, a base
legal (legítimo interesse, art. 7º IX) e o direito de oposição; a §4 diz o que
continua verdade — nenhum dado de estudo, contato ou pagamento vai para a Meta,
e o pixel não entra em tela nenhuma atrás do login.

A Privacidade ganhou **data própria** (`PRIVACIDADE_ATUALIZADA_EM`): antes uma
constante só servia Termos e Privacidade, e atualizar uma anunciaria que a
outra mudou. Data falsa em documento legal é pior que data velha — é por ela
que o titular sabe se leu a versão que vale.

> [!danger] **Duas decisões que continuam do dono, e que o código não resolve.**
> 1. **A promessa da §4 foi reescrita para caber no produto, não o contrário.**
>    O público é majoritariamente menor de idade. Se a promessa é que vale, o
>    caminho é limitar o pixel (esvaziar a variável, ou deixá-lo só em
>    `/ads/*`, onde a pessoa chegou por um anúncio) — não ajustar o texto.
> 2. **§10 promete avisar "por e-mail e dentro do produto ANTES de a mudança
>    valer".** O pixel passou a valer no dia da mudança, sem aviso. Mandar esse
>    aviso à base é ação do dono, e continua pendente.
>
> Não há tela de consentimento de cookies no produto. Ver [[contas-e-acesso]].

---
Relacionado: [[landings-de-anuncio]] · [[afiliados]] · [[analytics-de-produto]] · [[deploy]]
