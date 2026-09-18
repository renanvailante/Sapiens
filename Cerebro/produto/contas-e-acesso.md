---
tags: [produto, auth, cadastro]
atualizado: 2026-09-18
---

# Contas, cadastro e acesso

## WhatsApp: dois campos, sempre juntos

`backend/whatsapp.py`, `models.User`:

- `whatsapp` — o que a pessoa digitou (ela reconhece);
- `whatsapp_e164` — só dígitos com DDI, o único que serve para montar `wa.me/...` e
  para comparar.

DDI 55 é implícito para 10–11 dígitos; 12–15 passam como internacional.

### Onde é obrigatório, e a pegadinha

- **Cadastro por e-mail:** obrigatório, validado **antes** do `insert_one` para não
  deixar conta pela metade.
- **Login com Google:** opcional, e um número inválido é **ignorado** em vez de
  barrar a entrada — o botão do Google também cria conta a partir da tela de
  **login**, onde não existe formulário. Recusar ali trocaria um dado que falta por
  uma pessoa que não consegue entrar.
- **Contas anteriores a 2026-09-15** entram sem número.

Quem tem sessão e **não** tem `whatsapp` é mandado para `/completar-cadastro` antes
de qualquer tela (guarda em `ProtectedRoute`). É o único jeito de o telefone entrar
pelo caminho do Google.

> **`/completar-cadastro` é ela mesma protegida** — a guarda precisa do
> `pathname !== "/completar-cadastro"` ou o redirecionamento entra em laço.

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

**A cura de verdade, ainda NÃO aplicada** (muda a autenticação de todo mundo e
precisa de aprovação): servir o handler no próprio domínio — `public/_worker.js` no
Cloudflare Pages reencaminhando `/__/auth/*` e `/__/firebase/*` para
`sapiens-dataset.firebaseapp.com`, e `REACT_APP_FIREBASE_AUTH_DOMAIN` passando a ser
`sapiens-aluno.pages.dev`. O `_worker.js` mora em `public/` de propósito: o CRA copia
tudo de lá para `build/`, então ele sobrevive a todo rebuild.

**O que foi aplicado:** em `Login.jsx`, fechar a janela travada deixou de ser
silêncio — abaixo de 25s continua sendo cancelamento deliberado (sem toast), acima
disso vira aviso com a saída.

## Menor de idade

Autodeclarado, revela nome + WhatsApp do responsável, obrigatórios no cadastro por
e-mail (LGPD art. 14). Quem se declara maior **nunca** guarda campo de responsável,
nem mandando um. `POST /auth/whatsapp` aceita `menor_de_idade` e o responsável, para
a tela ser uma chamada só.

## Cupons e indicação

Um campo só no cadastro para os dois. Ver [[pagamentos]].

---
Relacionado: [[pagamentos]] · [[inviolaveis]] · [[engajamento]]
