#!/usr/bin/env bash
# Ponte de credenciais para o deploy do Sapiens — via Keychain do macOS.
#
# POR QUE ISTO EXISTE
# -------------------
# Variáveis exportadas no seu terminal não alcançam o processo das ferramentas
# do agente: são shells diferentes, e isso é isolamento de processo do SO, não
# permissão que se possa ajustar. Alguma ponte é necessária.
#
# O Keychain é a ponte de menor exposição disponível aqui:
#   * cifrado em repouso pelo próprio sistema;
#   * fora do repositório — nada a versionar, nada a ignorar, nada em auditoria;
#   * fora de ~/.zshrc e afins, onde ficaria em texto claro;
#   * os valores nunca passam pelo chat.
#
# As alternativas foram descartadas: arquivo no repo (mesmo ignorado) vaza no
# primeiro `git add -f` ou backup; dotfile de shell guarda em texto claro e
# vaza em qualquer `env`; colar no chat grava o segredo no transcript.
#
# USO
# ---
#   # 1. No SEU terminal, onde as variáveis já existem — nada é redigitado:
#   ./scripts/credenciais.sh salvar
#
#   # 2. Conferir (mostra presença e forma, nunca valor):
#   ./scripts/credenciais.sh status
#
#   # 3. O deploy carrega sozinho; para usar à mão numa sessão:
#   eval "$(./scripts/credenciais.sh exportar)"
#
#   # 4. Ao fim do piloto, se quiser remover do Keychain:
#   ./scripts/credenciais.sh apagar
set -euo pipefail

SERVICO="sapiens-deploy"
VARS=(FLY_API_TOKEN CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID
      MONGO_URL_ALUNO GEMINI_API_KEY_PROD ADMIN_EMAILS_PROD)

c_ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
c_erro() { printf '  \033[31m✗\033[0m %s\n' "$1"; }
c_av()   { printf '  \033[33m!\033[0m %s\n' "$1"; }

ler() { security find-generic-password -a "$USER" -s "$SERVICO-$1" -w 2>/dev/null || true; }

salvar() {
  echo "Gravando credenciais no Keychain (serviço: $SERVICO)"
  local faltando=0
  for v in "${VARS[@]}"; do
    local valor="${!v:-}"
    if [ -z "$valor" ]; then
      c_erro "$v não está definida neste shell"
      faltando=$((faltando + 1))
      continue
    fi
    # -U atualiza se já existir. O valor vai por -w, nunca ecoado.
    security add-generic-password -a "$USER" -s "$SERVICO-$v" -w "$valor" -U 2>/dev/null
    c_ok "$v gravada (${#valor} caracteres)"
  done
  echo
  if [ "$faltando" -gt 0 ]; then
    c_erro "$faltando variável(is) ausente(s) neste shell — exporte-as e rode de novo"
    return 1
  fi
  c_ok "todas as credenciais disponíveis para o deploy"
}

status() {
  echo "Credenciais no Keychain (presença e forma, nunca valor)"
  local faltando=0
  for v in "${VARS[@]}"; do
    local valor; valor="$(ler "$v")"
    if [ -z "$valor" ]; then
      c_erro "$v ausente"; faltando=$((faltando + 1)); continue
    fi
    local forma=""
    case "$v" in
      MONGO_URL_ALUNO)
        case "$valor" in
          *localhost*|*127.0.0.1*) forma=" · LOCAL — inválido para produção";;
          mongodb+srv://*)         forma=" · URI SRV do Atlas";;
          *)                       forma=" · não é mongodb+srv://";;
        esac;;
      ADMIN_EMAILS_PROD)
        forma=" · $(echo "$valor" | tr ',' '\n' | grep -c . ) e-mail(s)";;
    esac
    c_ok "$v presente · ${#valor} caracteres$forma"
  done
  echo
  [ "$faltando" -eq 0 ] && { c_ok "prontas"; return 0; }
  c_erro "$faltando ausente(s) — rode: ./scripts/credenciais.sh salvar"; return 1
}

exportar() {
  # Saída destinada a `eval`. Não imprima isto num terminal compartilhado.
  for v in "${VARS[@]}"; do
    local valor; valor="$(ler "$v")"
    [ -n "$valor" ] && printf 'export %s=%q\n' "$v" "$valor"
  done
}

apagar() {
  for v in "${VARS[@]}"; do
    if security delete-generic-password -a "$USER" -s "$SERVICO-$v" >/dev/null 2>&1; then
      c_ok "$v removida do Keychain"
    else
      c_av "$v não estava no Keychain"
    fi
  done
}

case "${1:-status}" in
  salvar)   salvar ;;
  status)   status ;;
  exportar) exportar ;;
  apagar)   apagar ;;
  *) sed -n '2,32p' "$0"; exit 1 ;;
esac
