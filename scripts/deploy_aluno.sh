#!/usr/bin/env bash
# Deploy do app do aluno — staging público v0.1.
#
#   Backend  : Fly.io          (aluno/backend)
#   Frontend : Cloudflare Pages (aluno/frontend)
#
# `pipeline` e `professor` NÃO são publicados nesta versão.
#
# Uso:
#   scripts/deploy_aluno.sh preflight    # valida credenciais e configuração
#   scripts/deploy_aluno.sh backend      # publica o backend no Fly.io
#   scripts/deploy_aluno.sh frontend     # publica o frontend no Cloudflare Pages
#   scripts/deploy_aluno.sh verify       # health, readiness e ausência de segredo
#   scripts/deploy_aluno.sh e2e          # E2E completo contra a URL pública
#   scripts/deploy_aluno.sh all          # tudo, em ordem
#
# Variáveis esperadas no ambiente (nunca versionadas):
#   MONGO_URL_ALUNO   ATLAS_SRV      GEMINI_API_KEY_PROD
#   ADMIN_EMAILS_PROD FIREBASE_SA_JSON_PATH
#   FLY_APP           CF_PAGES_PROJECT
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

# Credenciais vêm do Keychain (ver scripts/credenciais.sh). Nada de segredo em
# arquivo do repositório, em dotfile de shell ou no ambiente do processo pai.
# Variáveis já exportadas na sessão têm precedência.
if [ -x "$RAIZ/scripts/credenciais.sh" ]; then
  eval "$("$RAIZ/scripts/credenciais.sh" exportar 2>/dev/null || true)"
fi

# `fly` usa FLY_API_TOKEN se presente; sem ele cairia no login interativo.
export FLY_ACCESS_TOKEN="${FLY_ACCESS_TOKEN:-${FLY_API_TOKEN:-}}"

FLY_APP="${FLY_APP:-sapiens-aluno}"
CF_PAGES_PROJECT="${CF_PAGES_PROJECT:-sapiens-aluno}"
FIREBASE_SA_JSON_PATH="${FIREBASE_SA_JSON_PATH:-.secrets/firebase-service-account.json}"

c_ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
c_erro() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
c_aviso(){ printf '  \033[33m!\033[0m %s\n' "$1"; }

# ---------------------------------------------------------------------------
preflight() {
  echo "═══ Preflight ═══"
  local falhas=0

  for cli in fly npx; do
    if command -v "$cli" >/dev/null 2>&1; then c_ok "$cli disponível"
    else c_erro "$cli AUSENTE"; falhas=$((falhas+1)); fi
  done

  if command -v fly >/dev/null 2>&1 && fly auth whoami >/dev/null 2>&1; then
    c_ok "Fly.io autenticado como $(fly auth whoami 2>/dev/null)"
  else
    c_erro "Fly.io não autenticado — grave FLY_API_TOKEN (scripts/credenciais.sh salvar)"
    falhas=$((falhas+1))
  fi

  for v in CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID; do
    if [ -n "${!v:-}" ]; then c_ok "$v presente"
    else c_erro "$v ausente"; falhas=$((falhas+1)); fi
  done

  for v in MONGO_URL_ALUNO GEMINI_API_KEY_PROD ADMIN_EMAILS_PROD; do
    if [ -n "${!v:-}" ]; then c_ok "$v definida"
    else c_erro "$v ausente"; falhas=$((falhas+1)); fi
  done

  if [ -f "$FIREBASE_SA_JSON_PATH" ]; then c_ok "service account do Firebase encontrada"
  else c_erro "service account não encontrada em $FIREBASE_SA_JSON_PATH"; falhas=$((falhas+1)); fi

  # Atlas, não Mongo local: um deploy apontando para localhost sobe e falha
  # na primeira requisição, com o /ready acusando mongo fora.
  if [ -n "${MONGO_URL_ALUNO:-}" ]; then
    case "$MONGO_URL_ALUNO" in
      *localhost*|*127.0.0.1*) c_erro "MONGO_URL_ALUNO aponta para Mongo LOCAL — use a URI do Atlas"; falhas=$((falhas+1));;
      mongodb+srv://*) c_ok "MONGO_URL_ALUNO é uma URI SRV do Atlas";;
      *) c_aviso "MONGO_URL_ALUNO não é mongodb+srv:// — confirme que é o Atlas";;
    esac
  fi

  echo
  [ "$falhas" -eq 0 ] && { c_ok "preflight OK"; return 0; }
  c_erro "$falhas pendência(s) — resolva antes de publicar"; return 1
}

# ---------------------------------------------------------------------------
backend() {
  echo "═══ Backend → Fly.io ($FLY_APP) ═══"
  preflight

  if fly status --app "$FLY_APP" >/dev/null 2>&1; then
    c_ok "app $FLY_APP já existe"
  else
    echo "  criando app $FLY_APP..."
    if ! fly apps create "$FLY_APP" --org "${FLY_ORG:-personal}" 2>/tmp/fly_create.err; then
      if grep -qi "taken\|already been\|unavailable" /tmp/fly_create.err; then
        c_erro "o nome '$FLY_APP' já está em uso no Fly (nomes são globais)."
        c_erro "rode de novo com outro: FLY_APP=sapiens-aluno-<sufixo> $0 backend"
      else
        c_erro "falha ao criar o app:"; sed 's/^/    /' /tmp/fly_create.err
      fi
      rm -f /tmp/fly_create.err; return 1
    fi
    rm -f /tmp/fly_create.err
    c_ok "app $FLY_APP criado"
  fi

  # Segredos: `fly secrets set` os grava cifrados e os injeta como env na VM.
  # Nunca entram na imagem nem no repositório.
  fly secrets set --app "$FLY_APP" --stage \
    MONGO_URL="$MONGO_URL_ALUNO" \
    DB_NAME="sapiens_aluno" \
    GEMINI_API_KEY="$GEMINI_API_KEY_PROD" \
    ADMIN_EMAILS="$ADMIN_EMAILS_PROD" \
    FIREBASE_SERVICE_ACCOUNT_JSON="$(cat "$FIREBASE_SA_JSON_PATH")" \
    FIREBASE_PROJECT_ID="$(python3 -c "import json,sys;print(json.load(open('$FIREBASE_SA_JSON_PATH'))['project_id'])")"

  # CORS só é conhecido depois que o frontend existe. Na primeira passagem fica
  # a URL prevista do Pages; `frontend()` corrige se a URL real diferir.
  # Sem --stage aqui: este é o último `secrets set`, e é ele que efetiva todos
  # os anteriores antes do deploy.
  fly secrets set --app "$FLY_APP" \
    CORS_ORIGINS="https://${CF_PAGES_PROJECT}.pages.dev"
  c_ok "segredos publicados no Fly (cifrados, fora da imagem e do repositório)"

  fly deploy --config aluno/backend/fly.toml --dockerfile aluno/backend/Dockerfile \
             --app "$FLY_APP" --remote-only

  echo
  c_ok "backend em https://${FLY_APP}.fly.dev"
}

# ---------------------------------------------------------------------------
frontend() {
  echo "═══ Frontend → Cloudflare Pages ($CF_PAGES_PROJECT) ═══"
  local backend_url="${BACKEND_URL:-https://${FLY_APP}.fly.dev}"

  # REACT_APP_* é substituída no bundle em tempo de build e fica publicamente
  # legível. Só entram aqui a URL do backend e a config do Firebase Web — esta
  # última é identificador público de projeto, não credencial (quem protege é a
  # lista de domínios autorizados). A service account nunca chega ao frontend.
  ( cd aluno/frontend
    REACT_APP_BACKEND_URL="$backend_url" GENERATE_SOURCEMAP=false yarn build )

  # Rede de segurança: o bundle não pode conter credencial de servidor.
  # A apiKey do Firebase Web (AIza…) é esperada e legítima aqui — é
  # identificador público. O que NÃO pode aparecer: URI do Mongo com senha,
  # chave privada da service account, tokens de plataforma.
  if grep -rqE "mongodb\+srv://|BEGIN [A-Z ]*PRIVATE KEY|\b(fo1_|fm2_)[A-Za-z0-9_-]{10,}" \
       aluno/frontend/build/static/js/*.js 2>/dev/null; then
    c_erro "SEGREDO DE SERVIDOR ENCONTRADO NO BUNDLE — deploy abortado"; exit 1
  fi
  # A service account tem um client_email inconfundível; se ele aparecer, algo
  # do backend vazou para o build.
  if [ -f "$FIREBASE_SA_JSON_PATH" ] && grep -rqF \
       "$(python3 -c "import json;print(json.load(open('$FIREBASE_SA_JSON_PATH'))['client_email'])")" \
       aluno/frontend/build/static/js/*.js 2>/dev/null; then
    c_erro "SERVICE ACCOUNT ENCONTRADA NO BUNDLE — deploy abortado"; exit 1
  fi
  c_ok "bundle sem credencial de servidor"

  # O projeto precisa existir antes do primeiro deploy; criar é idempotente
  # o suficiente (falha benigna se já existir).
  npx --yes wrangler@latest pages project create "$CF_PAGES_PROJECT" \
      --production-branch main 2>/dev/null || true

  npx --yes wrangler@latest pages deploy aluno/frontend/build \
    --project-name "$CF_PAGES_PROJECT" --branch main --commit-dirty=true

  local url_real="https://${CF_PAGES_PROJECT}.pages.dev"

  # Reconcilia o CORS do backend com a URL efetiva do Pages. Sem isto, um nome
  # de projeto diferente do previsto faria toda requisição do frontend ser
  # bloqueada pelo navegador — com o backend saudável, o que é difícil de ler.
  local cors_atual
  cors_atual="$(fly ssh console --app "$FLY_APP" -C 'printenv CORS_ORIGINS' 2>/dev/null | tr -d '\r' || true)"
  if [ "$cors_atual" != "$url_real" ]; then
    echo "  ajustando CORS_ORIGINS para $url_real"
    fly secrets set --app "$FLY_APP" CORS_ORIGINS="$url_real"
  else
    c_ok "CORS_ORIGINS já corresponde à URL do Pages"
  fi

  echo
  c_ok "frontend em $url_real"
}

# ---------------------------------------------------------------------------
verify() {
  local backend_url="${BACKEND_URL:-https://${FLY_APP}.fly.dev}"
  local frontend_url="${FRONTEND_URL:-https://${CF_PAGES_PROJECT}.pages.dev}"
  echo "═══ Verificação ═══"

  printf '  /health  → '; curl -fsS -o /dev/null -w '%{http_code}\n' "$backend_url/health"
  printf '  /ready   → '; curl -fsS "$backend_url/ready" | python3 -m json.tool

  # Uma origem não declarada não pode receber Access-Control-Allow-Origin.
  printf '  CORS (origem estranha) → '
  curl -fsS -o /dev/null -D - -H "Origin: https://origem-nao-autorizada.example" \
       "$backend_url/api/" 2>/dev/null | grep -ci "access-control-allow-origin" \
    | sed 's/^0$/bloqueada (correto)/; s/^[1-9].*/PERMITIDA — REVISAR/'

  printf '  frontend → '; curl -fsS -o /dev/null -w '%{http_code}\n' "$frontend_url"

  echo "  logs (últimas linhas, procurando segredo):"
  fly logs --app "$FLY_APP" --no-tail 2>/dev/null | tail -40 \
    | grep -ciE "AIza[0-9A-Za-z_-]{20,}|mongodb\+srv://|BEGIN PRIVATE KEY" \
    | sed 's/^0$/    nenhum segredo nos logs/; s/^[1-9].*/    SEGREDO NOS LOGS — REVISAR/'
}

case "${1:-}" in
  preflight) preflight ;;
  backend)   backend ;;
  frontend)  frontend ;;
  verify)    verify ;;
  e2e)
    python3 scripts/e2e_aluno.py \
      --base-url "${BACKEND_URL:-https://${FLY_APP}.fly.dev}" ;;
  all)
    preflight && backend && frontend && verify
    echo
    echo "═══ E2E contra as URLs públicas ═══"
    python3 scripts/e2e_aluno.py --base-url "https://${FLY_APP}.fly.dev" ;;
  *) sed -n '2,20p' "$0"; exit 1 ;;
esac
