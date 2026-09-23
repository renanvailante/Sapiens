---
tags: [operacao, deploy, runbook]
atualizado: 2026-09-18
---

# Deploy — runbook

> [!danger] As cinco armadilhas deste repo falham em SILÊNCIO e no mesmo sentido
> Todas fazem parecer que o que está em produção é o que você escreveu.
> **Valide produção sempre por evidência do alvo, nunca pela saída do comando.**

## Autorização permanente

Depois de **qualquer** mudança em `aluno/frontend`, buildar e publicar é
pré-autorizado — não precisa perguntar. O dono disse "SEMPRE faça isso". Continue
usando juízo: não publique trabalho pela metade. As demais superfícies (backend do
aluno, professor) não têm essa autorização automática.

## Receita completa (frontend do aluno)

```bash
git commit                                   # 1. commite ANTES
git worktree add --detach /tmp/wt HEAD       # 2. isole do trabalho alheio
cp aluno/frontend/.env /tmp/wt/aluno/frontend/.env   # 3. o .env NÃO é versionado
cd /tmp/wt/aluno/frontend && yarn build
grep -c "sapiens-aluno.fly.dev" build/static/js/main.*.js    # deve ser > 0
grep -c "undefined/api" build/static/js/*.js                 # deve ser 0
npx wrangler pages deploy build --project-name sapiens-aluno --branch main
npx wrangler pages deployment list           # Environment=Production, Branch=main
```

## Receita completa (backend do aluno)

```bash
# DA RAIZ do repositório (ou do worktree). NUNCA de dentro de aluno/backend.
flyctl deploy --config aluno/backend/fly.toml --dockerfile aluno/backend/Dockerfile
```

> [!warning] **Sessão do `flyctl` expira, e o agente não pode renovar.**
> Quando expira, o deploy morre em `Error: no access token available` — e a cura
> é `flyctl auth login`, que é autenticação com a conta do dono. **Digitar
> credencial é ação vedada a agente**, então o agente para aqui e pede; o dono
> roda uma vez e o deploy segue normal. Aconteceu em 22/09/2026 e foi resolvido
> assim.
>
> Pior: o erro sai em **segundos**, e naquele dia um wrapper devolveu 0 por cima
> dele — a armadilha 2 deste runbook, de novo, agora num comando que nem chegou
> a começar. **Leia o log, não o código de saída.**

## As cinco armadilhas

**1. `fly deploy` empacota a ÁRVORE DE TRABALHO, não o commit.** Várias sessões
dividem este repo ([[sessoes-concorrentes]]), então um deploy seu publica o
trabalho em curso de outra pessoa. Já aconteceu: produção rodou ~1h um
`motor_cognitivo.py` que não estava em commit nenhum. → **Commite primeiro e
publique de um worktree em HEAD.**

**2. `| tail` esconde a falha.** O exit code do pipeline é o do `tail`, sempre 0.
Um deploy que falhou por DNS foi lido como sucesso e a correção da cota do
Firestore ficou fora do ar enquanto eu afirmava o contrário. → `set -o pipefail`,
redirecionar para arquivo, imprimir `$?`.

**3. O worktree não traz o `.env`.** Ele isola exatamente o que deveria (a árvore
suja) e também o que não deveria (qualquer arquivo gitignored que o build precise).
Sem `.env`, o CRA embute a string literal `"undefined/api"`, o Cloudflare devolve
`index.html` para toda chamada de API e **o site inteiro quebra** — não só a tela
nova. O build compila sem erro nenhum. Dois deploys seguidos saíram assim porque
repeti o processo achando que o problema era o código. → `cp` o `.env` antes do
build e rode os dois greps.

**4. `wrangler` a partir de worktree publica em PREVIEW.** O worktree destacado tem
branch `HEAD`; o wrangler usa o branch para escolher o ambiente e publica em
`head.sapiens-aluno.pages.dev` enquanto produção continua servindo o bundle antigo.
Termina com "✨ Deployment complete!". → **`--branch main` é obrigatório.**

**5. O backend do aluno não builda de dentro de `aluno/backend`.** O contexto do
build é a raiz do repo: o Dockerfile copia `pipeline/docs/ontology/`, os
validadores e o canon da redação. Rodar lá dentro falha no meio do build com "not
found" num `COPY` — parece arquivo faltando e é diretório de contexto errado.

## Como provar que subiu

Hash de bundle **não basta** — outra sessão pode ter republicado no meio
([[sessoes-concorrentes]]). Prove funcionalmente:

- Rota nova responde **401 e não 404** (existe, só exige auth).
- `flyctl status` (versão) + `printenv` via `fly ssh console` (env) + `md5sum` dos
  arquivos em `/app` contra `git show HEAD:...`.
- Frontend com `React.lazy`: a string pode estar num `*.chunk.js`, não no
  `main.js`. Busque em **todos** os arquivos de `/asset-manifest.json`, com
  `User-Agent` (o Cloudflare devolve 403 sem ele).
- **Cuidado:** o Cloudflare Pages responde **200 com o `index.html`** para arquivo
  ausente (fallback de SPA). `curl -w "%{http_code}"` mente — confira o
  `content-type`.
- Deploy em background pode promover uma imagem velha ~1h depois e sobrescrever uma
  versão boa. Confira se não há deploy pendente antes de declarar validado.

## Dependência de dado do `pipeline/`

**Toda dependência de dado em `pipeline/` precisa de uma linha `COPY` no
Dockerfile e de um teste que leia o Dockerfile.** A suíte passando na árvore do
repo não diz nada sobre a imagem. O corretor de redação nunca funcionou em
produção desde que foi construído por causa disso, e ninguém sabia porque `/ready`
não checava o canon. Testes em `tests/test_prontidao_producao.py`.

Exceção: o conteúdo dos cursos entra pelo `COPY aluno/backend/ /app/` que já
existe — não precisa de linha própria (há nota no Dockerfile).

## Endereços

| Superfície | Onde | Comando |
|---|---|---|
| aluno · backend | `sapiens-aluno.fly.dev` | `flyctl deploy --config aluno/backend/fly.toml --dockerfile aluno/backend/Dockerfile` (da raiz) |
| aluno · frontend | `sapiens-aluno.pages.dev` | `npx wrangler pages deploy build --project-name sapiens-aluno` |
| professor · backend | `sapiens-professor.fly.dev` | `fly deploy --config professor/backend/fly.toml` (de dentro de `professor/backend/`) |
| professor · frontend | `sapiens-professor.pages.dev` | `npx wrangler pages deploy build --project-name sapiens-professor` |

O Dockerfile do professor **não** depende de `pipeline/docs/`, por isso ele
deploya de dentro da própria pasta.

---
Relacionado: [[sessoes-concorrentes]] · [[ambiente-local]] · [[incidentes]]
