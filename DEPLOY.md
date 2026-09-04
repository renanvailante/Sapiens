# Deployment — Sapiens

Instruções mínimas para colocar a plataforma no ar. Três backends FastAPI, três
frontends React (CRA/craco), MongoDB, Firestore, Firebase Storage e Gemini API.

**Sem Emergent.** A remoção está registrada em
[`auditoria/AUDITORIA-SERVICOS-EXTERNOS.md`](auditoria/AUDITORIA-SERVICOS-EXTERNOS.md).

---

## 1. Arquitetura recomendada

Priorizando plano gratuito ou de baixo custo, e compatível com o que já existe —
nada aqui exige reescrever persistência ou trocar fornecedor.

| Componente | Onde | Custo | Por quê |
|---|---|---|---|
| **3 backends** (FastAPI) | **Fly.io** (`shared-cpu-1x`, 256–512 MB) | Gratuito no free allowance; ~US$2/mês/app depois | Roda Docker sem adaptação, aceita `$PORT`, e — o ponto decisivo — **não hiberna**. Render free hiberna após 15 min e o primeiro acesso leva ~50 s, o que num app de estudante parece "fora do ar". |
| **3 frontends** (build estático) | **Cloudflare Pages** | Gratuito, sem teto prático | Build estático + CDN. Vercel/Netlify servem igualmente bem. |
| **MongoDB** | **MongoDB Atlas M0** | Gratuito (512 MB) | **Mantido por decisão de arquitetura.** Redundância deliberada; não migrar para Firestore. |
| **Firestore** | Firebase (plano Spark) | Gratuito até 50k leituras/dia | Já em uso: espelho dos itens e eventos de behavior. |
| **Firebase Storage** | Firebase (**exige plano Blaze**) | Centavos no volume inicial | Artefatos binários. Ver §4 — é o único item que obriga cartão. |
| **Gemini API** | Google AI Studio | Free tier generoso; pago por uso | Anotação, OCR, diagnóstico. |

### Topologia

```
Cloudflare Pages                 Fly.io                     Serviços
─────────────────                ──────                     ────────
aluno.<dominio>      ──────►  sapiens-aluno      ──┬──►  MongoDB Atlas M0
professor.<dominio>  ──────►  sapiens-professor  ──┤
                                                   ├──►  Firestore
[pipeline: NÃO público]  ──►  sapiens-pipeline   ──┼──►  Firebase Storage
   (ver §3)                                        └──►  Gemini API
```

### Ordem de subida

1. MongoDB Atlas (M0, allowlist de IP `0.0.0.0/0` — Fly.io não tem IP fixo no plano básico; a proteção é a senha da connection string).
2. Firebase: Firestore + Storage + baixar a service account.
3. Gemini: gerar a API key.
4. Backends no Fly.io (`pipeline` primeiro — é quem semeia a ontologia).
5. Frontends no Cloudflare Pages, apontando `REACT_APP_BACKEND_URL` para os backends.
6. Preencher `CORS_ORIGINS` nos backends com as URLs reais dos frontends e redeploy.

O passo 6 é circular por natureza: o backend precisa saber a URL do frontend e
vice-versa. Suba os backends com um `CORS_ORIGINS` provisório, publique os
frontends, depois corrija e redeploy.

---

## 2. Secrets e serviços — configuração manual

Nada abaixo pode ser gerado automaticamente. Todos os `.env.example` estão
versionados e documentam cada variável.

### Você precisa criar

| # | Serviço | O que obter | Onde usar |
|---|---|---|---|
| 1 | **MongoDB Atlas** | 3 connection strings (um DB por app, mesmo cluster) | `MONGO_URL` + `DB_NAME` nos 3 backends |
| 2 | **Firebase** | Service account JSON (Configurações → Contas de serviço) | `pipeline` e `aluno` |
| 3 | **Firebase Storage** | Nome do bucket (`projeto.firebasestorage.app`) | `FIREBASE_STORAGE_BUCKET` no `pipeline` |
| 4 | **Gemini API** | API key ([AI Studio](https://aistudio.google.com/apikey)) | `pipeline` e `aluno` |
| 5 | **Segredos gerados** | `PIPELINE_API_KEY` e `JWT_SECRET` | ver abaixo |

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Gere **um valor diferente para cada** — reutilizar faz um comprometimento
alcançar os dois serviços.

### Variáveis por serviço

Os defaults inseguros foram removidos: com `APP_ENV=production`, **o processo
recusa subir** se algo obrigatório faltar, e a mensagem diz exatamente o quê.

#### `sapiens-pipeline` (backend)
```
APP_ENV=production
MONGO_URL=            DB_NAME=sapiens_pipeline
PIPELINE_API_KEY=     # gerado; mínimo 32 caracteres
GEMINI_API_KEY=       GEMINI_MODEL=gemini-3-flash-preview
CORS_ORIGINS=         # origens exatas; '*' é recusado
FIRESTORE_MODE=admin  FIRESTORE_COLLECTION=itens
FIREBASE_SERVICE_ACCOUNT_JSON=   # JSON inline (Fly.io não monta arquivo)
STORAGE_MODE=firebase            # 'local' é recusado em produção
FIREBASE_STORAGE_BUCKET=
SEED_DEMO_DATA=false
```

#### `sapiens-aluno` (backend)
```
APP_ENV=production
MONGO_URL=            DB_NAME=sapiens_aluno
CORS_ORIGINS=
COOKIE_SECURE=true    COOKIE_SAMESITE=none
GEMINI_API_KEY=
FIREBASE_SERVICE_ACCOUNT_JSON=   FIREBASE_PROJECT_ID=
ADMIN_EMAILS=         # quem acessa as telas administrativas
SEED_DEMO_DATA=false
```

#### `sapiens-professor` (backend)
```
APP_ENV=production
MONGO_URL=            DB_NAME=sapiens_professor
JWT_SECRET=           # gerado; mínimo 32 caracteres
FRONTEND_URL=         # ou CORS_ORIGINS
COOKIE_SECURE=true    COOKIE_SAMESITE=none
ADMIN_EMAIL=          ADMIN_PASSWORD=   # mínimo 12; senhas triviais recusadas
SEED_DEMO_DATA=false
```

#### Frontends
```
REACT_APP_BACKEND_URL=https://sapiens-<app>.fly.dev
GENERATE_SOURCEMAP=false
```

> **`REACT_APP_*` é embutida no bundle em tempo de build e fica publicamente
> legível.** Nunca coloque segredo aí.

---

## 3. O pipeline não vai para a internet pública

O painel do pipeline autentica com `X-API-Key`, e a chave viria de
`REACT_APP_PIPELINE_API_KEY` — que o CRA substitui no bundle. Publicar o painel
publicaria **o segredo que protege todas as rotas do backend**: qualquer
visitante abriria o `.js`, leria a chave e teria acesso total ao anotador —
gerar, editar e apagar itens.

`pipeline/frontend/craco.config.js` **recusa a build de produção** se a chave
estiver definida. Três formas de operar hoje:

1. **Rodar o painel localmente** contra o backend publicado (recomendado para a
   primeira fase). `yarn start` com `REACT_APP_BACKEND_URL` apontando para o
   Fly.io e a chave no `.env` local.
2. **Publicar atrás de autenticação de plataforma** — Cloudflare Access na
   frente do Pages, por exemplo. A chave continua no bundle, mas o bundle só é
   servido a quem já autenticou.
3. **`PIPELINE_UI_PUBLICA=true`** libera a build. Só faça isso se o **backend**
   do pipeline não estiver acessível pela internet.

Publicar o painel abertamente exige uma camada de autenticação própria (sessão
por usuário), que ainda não existe. Isso é decisão de arquitetura, não parte
desta passagem de prontidão.

---

## 4. Firebase Storage exige plano Blaze

O Storage não está no plano gratuito Spark. O plano Blaze é pago por uso e o
volume inicial custa centavos, mas **exige cartão**.

Enquanto o Blaze não estiver ativo, o `pipeline` não sobe com
`APP_ENV=production` — `STORAGE_MODE=local` é recusado de propósito: no
filesystem efêmero de um container, os PDFs originais desaparecem no primeiro
redeploy e a regeneração de qualquer item passa a falhar silenciosamente.

Se preferir adiar o Blaze: mantenha o `pipeline` rodando localmente (onde
`STORAGE_MODE=local` é válido) e publique apenas `aluno` e `professor`. O
`aluno` só precisa do Firestore, que está no plano gratuito.

---

## 5. Comandos

### Backends (Fly.io)

O contexto de build é a **raiz do repositório** para `pipeline` e `aluno` — eles
leem o corpus canônico de `pipeline/docs/`.

```bash
fly launch --no-deploy --name sapiens-pipeline --dockerfile pipeline/backend/Dockerfile
fly secrets set APP_ENV=production MONGO_URL="..." DB_NAME=sapiens_pipeline \
   PIPELINE_API_KEY="..." GEMINI_API_KEY="..." CORS_ORIGINS="https://..." \
   FIRESTORE_MODE=admin STORAGE_MODE=firebase FIREBASE_STORAGE_BUCKET="..." \
   FIREBASE_SERVICE_ACCOUNT_JSON="$(cat .secrets/firebase-service-account.json)" \
   SEED_DEMO_DATA=false
fly deploy
```

Repita para `aluno` e `professor` com as variáveis da §2.

### Frontends (Cloudflare Pages)

| Campo | Valor |
|---|---|
| Build command | `yarn build` |
| Output directory | `build` |
| Root directory | `aluno/frontend` (ou `professor/frontend`) |
| Node version | 20 |

### Verificação pós-deploy

```bash
curl https://sapiens-aluno.fly.dev/health   # liveness — 200
curl https://sapiens-aluno.fly.dev/ready    # dependências — 200 ou 503 com detalhe
```

`/ready` devolve **503 enquanto alguma dependência estiver fora**, com o nome de
cada uma. Configure-o como health check da plataforma.

---

## 6. O que já está tratado no código

| Item | Estado |
|---|---|
| CORS curinga com credenciais | Recusado em produção |
| Cookies `Secure`/`SameSite` | Dirigidos por env; `SameSite=None` sem `Secure` é recusado |
| Filesystem efêmero | `STORAGE_MODE=local` recusado em produção |
| Dados de demonstração | `SEED_DEMO_DATA` desligado por padrão; recusado em produção |
| Segredos fracos | Comprimento mínimo; senhas triviais recusadas |
| `/docs`, `/redoc`, `/openapi.json` | Desligados em produção |
| Comparação da API key | Tempo constante (`hmac.compare_digest`) |
| Uploads | Limite de tamanho e de quantidade (`MAX_UPLOAD_MB`) |
| Erros não tratados | Id de incidente ao cliente, traceback só no log |
| Source maps | Desligados na build |
| Containers | Usuário sem privilégios, `$PORT` da plataforma, `--proxy-headers` |
| Segredos em log | `settings.resumo()` reporta booleanos, nunca valores |

---

## 7. Fora de escopo desta fase

- Integração `enem-extractor` + LOTUS.
- Produtor de Error Trace — o contrato e a validação existem; a produção aguarda
  evidência longitudinal e especificação estatística.
- Ontologia v1.6.
- Login social (removido junto com a Emergent; Firebase Auth é o caminho).
- Domínio próprio — os subdomínios `.fly.dev` e `.pages.dev` bastam para começar.
