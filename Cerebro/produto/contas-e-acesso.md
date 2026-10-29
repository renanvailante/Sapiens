---
tags: [produto, auth, cadastro]
atualizado: 2026-10-28
---

# Contas, cadastro e acesso

## WhatsApp: dois campos, sempre juntos

`backend/whatsapp.py`, `models.User`:

- `whatsapp` — o que a pessoa digitou (ela reconhece);
- `whatsapp_e164` — só dígitos com DDI, o único que serve para montar `wa.me/...` e
  para comparar.

DDI 55 é implícito para 10–11 dígitos; 12–15 passam como internacional.

### Onde é pedido (desde 2026-10-22, nunca obrigatório)

De 15/09 a 22/10 o número era **obrigatório** no cadastro por e-mail e
`ProtectedRoute` mandava todo aluno sem ele para `/completar-cadastro` antes de
qualquer tela. Era o pedido mais caro do produto feito antes de qualquer valor
— e 28 de 43 contas nunca chegaram à primeira questão. Decisão em
[[decisoes-do-dono]] ("O cadastro abre no diagnóstico"). Hoje:

- **Cadastro (e-mail e Google):** não aparece. `SignupRequest.whatsapp` é
  opcional; se vier, um número inválido continua sendo 422 **antes** do
  `insert_one` — a pessoa digitou, e gravar outro número seria pior.
- **Fim do plano (`/bem-vindo`):** etapa `whatsapp` só para quem não tem
  número, com o motivo à vista e "Agora não". Grava por `POST /auth/whatsapp`
  (que, com `menor_de_idade` ausente, não mexe no responsável).
- **Compra da aula ao vivo:** campo opcional para quem não tem número;
  `POST /cursos/live/acesso` já gravava o `whatsapp` do corpo **antes** de
  cobrar. O link da sala aparece na própria tela, então o número é lembrete,
  não condição.
- **Lista de espera da mentoria:** já pedia e conferia o número antes de
  cobrar.

`/completar-cadastro` continua existindo como tela, sem ninguém empurrado para
ela. **Não reponha a guarda em `ProtectedRoute`** sem decisão do dono: é o
mesmo pedágio, uma tela depois.

O **responsável** de quem se declara menor **continua no cadastro** — é outra
regra, de [[inviolaveis]].

A fonte da verdade de "já tem" é `user.whatsapp`, **nunca** um "dispensei" no
`localStorage`.

No admin (`/admin/users`) o número vira chip verde clicável que abre a conversa —
`whatsapp_link` é montado no **backend**. Não reimplemente a normalização em JS.

## A tela branca do login com Google

**Sintoma:** clicar em "Continuar com Google", escolher a conta, e a janela virar uma
tela branca que não sai.

**Descartado com evidência** — não refaça a investigação:

- **Não** é domínio não autorizado: `sapiens-aluno.pages.dev` está na lista
  (`curl "https://identitytoolkit.googleapis.com/v1/projects?key=<apiKey>"` devolve
  `authorizedDomains`).
  **Mas atenção:** os subdomínios de **preview** do Cloudflare
  (`<hash>.sapiens-aluno.pages.dev`) **não** estão, e o Firebase não casa curinga —
  login com Google só funciona no domínio de produção.
- **Não** é a aplicação quebrando: o `ErrorBoundary` envolve todas as rotas, então
  um erro de render mostraria mensagem, não tela branca.

**Causa provável:** `authDomain` é `sapiens-dataset.firebaseapp.com`, **outra
origem**. O `signInWithPopup` abre o handler lá e ele precisa devolver o resultado
para a aba de origem; com o particionamento de armazenamento de terceiros do Chrome,
esse retorno trava.

### A cura está montada e DESLIGADA: o handler na mesma origem

`public/_worker.js` reencaminha `/__/auth/*` e `/__/firebase/*` para
`sapiens-dataset.firebaseapp.com`. Com `REACT_APP_FIREBASE_AUTH_DOMAIN` valendo
`sapiens-aluno.pages.dev`, o handler vira mesma origem e a partição de
armazenamento do navegador não tem mais o que bloquear. O `_worker.js` mora em
`public/` de propósito: o CRA copia tudo de lá para `build/`, então ele sobrevive a
todo rebuild.

**Hoje o `authDomain` é `sapiens-dataset.firebaseapp.com`, e o worker não é chamado
por ninguém.** A cura foi ligada em 2026-09-22 (`ed87b44`, com aprovação do dono) e
desligada em 2026-10-28, quando o dono relatou que não conseguia entrar com o
Google: o Google recusa o handler novo com `redirect_uri_mismatch` (seção abaixo),
e nesses 36 dias **todo** login com Google morreu num Erro 400. O preço, medido no
Mongo: antes, 17 de 30 cadastros vinham pelo Google; durante, zero. A tela branca
do popup cross-origin pega uma parte das pessoas — sobretudo no navegador embutido
do Instagram, por onde chega o tráfego de [[landings-de-anuncio]]; o Erro 400
pegava todas.

**Não religue trocando só o `.env`.** A ordem para religar está no fim da seção
seguinte.

> [!danger] Um `_worker.js` na raiz do build põe o Pages em MODO AVANÇADO
> A partir dele o Cloudflare para de servir arquivo estático sozinho e passa
> **todo** o tráfego pelo worker. Um erro nesse arquivo derruba o site inteiro,
> não só o login. A regra que o arquivo segue: todo caminho que não é do Firebase,
> e **toda falha do proxy**, terminam em `env.ASSETS.fetch(request)` — o caminho de
> exceção serve o site, nunca o contrário.
>
> E `redirect: "manual"` no proxy não é cautela: o handler responde 302 para
> `accounts.google.com`, e seguir esse salto no servidor devolveria o HTML do
> Google servido a partir do nosso domínio.
>
> **Valide num deploy de PREVIEW antes de publicar em `main`.** Foi assim que esta
> mudança entrou: 14 rotas e assets em 200, `/__/auth/*` devolvendo Firebase de
> verdade, e o app montando no navegador — tudo antes de tocar em produção.

> [!warning] O `.env` NÃO é versionado, e é ele que carrega o `authDomain`
> `REACT_APP_FIREBASE_AUTH_DOMAIN` vive no `.env` local, que o deploy copia à mão
> para o worktree ([[deploy]]). Um `.env` que não acompanhe o `.env.example`
> publica o outro domínio **sem nada acusar**: o build compila, o worker continua
> lá, e o defeito só aparece no clique. O valor correto está em `.env.example`.
>
> O grep que detecta, enquanto o URI não estiver no OAuth Client:
> `grep -c "sapiens-dataset.firebaseapp.com" build/static/js/main.*.js` **não** pode
> dar 0, e o mesmo grep com `sapiens-aluno.pages.dev` **tem** de dar 0 — o bundle só
> cita esse domínio pelo `authDomain`.

**Até onde dá para verificar sem conta:** o diagnóstico abaixo, apontado para o
handler do `authDomain` no ar, tem de chegar à tela de login do Google
(`accounts.google.com/v3/signin/identifier`) e não a um Erro 400. Escolher a conta e
voltar logado exige uma conta Google real, que é do dono — e o painel de navegador
do Claude bloqueia popup aberto por clique de agente, então nem o popup abre ali
(o bloqueio ao menos diz para qual domínio ele ia).

**Confirmado de ponta a ponta pelo dono em 2026-10-28:** com o `authDomain` do
Firebase, ele escolheu a conta no popup e voltou logado no app. O caminho no ar
funciona; o que continua sem prova é o navegador embutido do Instagram.

**O que foi aplicado:** em `Login.jsx`, fechar a janela travada deixou de ser
silêncio — abaixo de 25s continua sendo cancelamento deliberado (sem toast), acima
disso vira aviso com a saída.

### A conta que a mudança de `authDomain` deixou por pagar: `redirect_uri_mismatch`

Trocar o `authDomain` muda o `redirect_uri` que o Firebase manda para o Google. Ele
passa a ser `https://sapiens-aluno.pages.dev/__/auth/handler`, e **o Google recusa**
com `Erro 400: redirect_uri_mismatch` até esse URI ser adicionado à mão no OAuth
Client — a tela branca virou erro visível em 2026-09-23.

> [!danger] Autorizar o domínio no Firebase **não** autoriza o redirect no Google
> São duas listas, em dois consoles, e mexer numa não mexe na outra:
> - `authorizedDomains` (Firebase Auth / Identity Platform) — já tinha
>   `sapiens-aluno.pages.dev` e por isso não acusou nada.
> - **Authorized redirect URIs** do OAuth Client Web em Google Cloud → APIs e
>   serviços → Credenciais. Esse é o que o Google confere, e o que faltava.
>
> O client é `222338124837-gnvk54ceubpq9r6pj4t160cavp7dul3g.apps.googleusercontent.com`
> (o Firebase cria um por projeto e o reusa; não crie outro). Ele já trazia
> `https://sapiens-dataset.firebaseapp.com/__/auth/handler` de fábrica — o novo
> **soma**, não substitui: apagar o antigo quebra `localhost` e os dois domínios
> `firebaseapp.com`/`web.app`, que continuam válidos.

O diagnóstico não precisa de conta Google nem de navegador — dá para arrancar do
Google o erro cru, em três comandos:

```bash
K=<REACT_APP_FIREBASE_API_KEY>
curl -s "https://identitytoolkit.googleapis.com/v1/projects?key=$K"   # authorizedDomains
A=$(curl -s -X POST "https://identitytoolkit.googleapis.com/v1/accounts:createAuthUri?key=$K" \
  -H "Content-Type: application/json" \
  -d '{"providerId":"google.com","continueUri":"https://sapiens-aluno.pages.dev/__/auth/handler"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['authUri'])")
curl -s -L "$A" | grep -io "redirect_uri_mismatch\|Error 400"
```

`createAuthUri` devolve a URL exata que o popup abriria, com `client_id` e
`redirect_uri` visíveis na query — é a forma de ver **qual** URI está sendo pedido
antes de sair mexendo em console. O último comando calando é o sinal de curado.

**O que falta não é corrigível pelo repositório.** O código e o worker estão
prontos; a pendência mora no Google Cloud Console e exige a conta do dono.

**Para religar a cura, nesta ordem:**

1. Somar `https://sapiens-aluno.pages.dev/__/auth/handler` em *Authorized redirect
   URIs* do client acima (sem apagar nenhum dos que já estão).
2. Rodar o diagnóstico até o último comando calar para `sapiens-aluno.pages.dev`.
   O Google pode levar alguns minutos para propagar.
3. Só então trocar `REACT_APP_FIREBASE_AUTH_DOMAIN` para `sapiens-aluno.pages.dev`
   no `.env` **e** no `.env.example`, publicar, e inverter o grep do aviso acima.

## Menor de idade

Autodeclarado, revela nome + WhatsApp do responsável, obrigatórios no cadastro por
e-mail (LGPD art. 14). Quem se declara maior **nunca** guarda campo de responsável,
nem mandando um. `POST /auth/whatsapp` aceita `menor_de_idade` e o responsável, para
a tela ser uma chamada só.

## O aluno antigo que cai no cadastro

A landing tem "Entrar" no topo e **"Começar agora"** no meio, grande e roxo. Quem já
tem conta clica no grande — e ia para `/login?novo=1`, que abre em "Criar conta".
O cupom ainda nascia preenchido sozinho, de uma atribuição de campanha guardada por
30 dias no navegador (`lib/atribuicao.js`), o que reforçava a impressão de que a
tela era a certa. No fim: `Email already registered`, **em inglês**, numa tela que
nunca ia aceitá-lo.

Desde 2026-09-23 a tela se corrige sozinha: a recusa troca o modo para "Entrar",
preserva o e-mail e **limpa a senha** — a que a pessoa inventou para o cadastro
quase nunca é a da conta que já existe, e mantê-la só produziria um segundo erro
logo depois do aviso. A detecção é `emailJaTemConta` em `lib/api.js` (ao lado de
`errMsg`, mesma família, e testável sem arrastar o `react-router` da página).

> [!warning] A regra é uma comparação de texto contra a mensagem do backend
> `auth.py` responde 400 + `"Email already registered"`. Mudar essa frase quebra a
> tela **em silêncio** — nada falha, o aluno só volta a ver inglês. `api.test.js`
> é o alarme; se mexer na mensagem, mexa nos dois.

**O modo inicial do `/login` é decidido só por pedido explícito**
(`atribuicao.modoInicialDoLogin`): convite na URL ou `?novo=1`. A atribuição
GUARDADA de um anúncio (30 dias) preenche o cupom e **não** abre o cadastro — até
2026-10-02 ela abria, e o "Entrar" da página inicial caía em "Criar conta" com
ADS-RETA preenchido, para o próprio dono.

## Destravar à mão quando o e-mail não chega

`_entregar_link_de_reset` grava o link no log quando o envio falha ou não há
provedor (`[RESET DE SENHA] … Link …`). O caminho para destravar alguém:
`POST /api/auth/password/forgot` com o e-mail e
`flyctl logs -a sapiens-aluno --no-tail | grep "RESET DE SENHA"` — o link vale
30 minutos, e **cada pedido novo invalida o anterior** (pegue a última linha).
Quem diz se o envio funciona é o `/ready`: `ultimo_envio` com `detalhe: "HTTP
401"` é chave do Resend inválida ou revogada (gerar outra e `fly secrets set
RESEND_API_KEY=…`, trabalho do dono); `HTTP 403` é a conta do Resend em modo de
teste.

## Cupons e indicação

Um campo só no cadastro para os dois. Ver [[pagamentos]].

---
Relacionado: [[pagamentos]] · [[inviolaveis]] · [[engajamento]]
