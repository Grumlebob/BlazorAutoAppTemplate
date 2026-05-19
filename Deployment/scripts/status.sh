#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-bootstrap}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCAL_ENV="$REPO_ROOT/Deployment/.deploy.local.env"
MACHINES="$REPO_ROOT/Deployment/machines.yml"
INVENTORY="$REPO_ROOT/Deployment/inventory/prod/hosts.yml"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/inventory/prod/bootstrap-hosts.yml"
VAULT="$REPO_ROOT/Deployment/inventory/prod/vault.yml"
ALL_VARS="$REPO_ROOT/Deployment/inventory/prod/group_vars/all.yml"

if [[ "$MODE" != "bootstrap" && "$MODE" != "deploy" ]]; then
  echo "usage: $0 [bootstrap|deploy]" >&2
  exit 1
fi

if [[ -f "$LOCAL_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$LOCAL_ENV"
  set +a
fi

APP_NAME="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" app_name)"
SSH_KEY="$HOME/.ssh/${APP_NAME}_deploy"
SSH_PUB="$SSH_KEY.pub"
FAILURES=0

ok() {
  printf 'OK    %s\n' "$*"
}

warn() {
  printf 'WARN  %s\n' "$*"
}

fail() {
  printf 'FAIL  %s\n' "$*"
  FAILURES=$((FAILURES + 1))
}

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 installed"
  else
    fail "$1 missing"
  fi
}

has_placeholder() {
  local file="$1"
  [[ -f "$file" ]] && grep -R "REPLACE_WITH" "$file" >/dev/null
}

echo "deployment status phase: $MODE"
echo

check_command python3
check_command ssh
check_command ansible
check_command ansible-inventory
check_command ansible-playbook

if [[ "$MODE" == "deploy" ]]; then
  check_command ansible-vault
else
  command -v ansible-vault >/dev/null 2>&1 && ok "ansible-vault installed" || warn "ansible-vault missing; required before vault/deploy phase"
fi

[[ -f "$LOCAL_ENV" ]] && ok "Deployment/.deploy.local.env exists" || warn "Deployment/.deploy.local.env missing; copy Deployment/.deploy.local.env.example if you want saved local defaults"
[[ -n "${LINUX_MINT_INSTALL_USER:-}" ]] && ok "LINUX_MINT_INSTALL_USER set to $LINUX_MINT_INSTALL_USER" || warn "LINUX_MINT_INSTALL_USER not set"

if [[ -f "$MACHINES" ]]; then
  ok "Deployment/machines.yml exists"
  if has_placeholder "$MACHINES"; then
    fail "Deployment/machines.yml still contains REPLACE_WITH placeholders"
  else
    ok "Deployment/machines.yml has no REPLACE_WITH placeholders"
  fi
else
  warn "Deployment/machines.yml missing; copy Deployment/machines.example.yml if you want one machine source file"
fi

[[ -f "$SSH_KEY" ]] && ok "SSH private key exists: $SSH_KEY" || fail "missing SSH private key: $SSH_KEY"
[[ -f "$SSH_PUB" ]] && ok "SSH public key exists: $SSH_PUB" || fail "missing SSH public key: $SSH_PUB"
[[ -f "$INVENTORY" ]] && ok "inventory exists" || fail "missing inventory: Deployment/inventory/prod/hosts.yml"
[[ -f "$BOOTSTRAP_INVENTORY" ]] && ok "bootstrap inventory exists" || warn "bootstrap inventory missing; run Deployment/scripts/generate-inventory.sh after filling Deployment/machines.yml"

if [[ -f "$INVENTORY" ]]; then
  if has_placeholder "$INVENTORY"; then
    fail "inventory still contains REPLACE_WITH placeholders"
  else
    ok "inventory has no REPLACE_WITH placeholders"
  fi
  if command -v ansible-inventory >/dev/null 2>&1; then
    if ansible-inventory -i "$INVENTORY" --list >/dev/null 2>&1; then
      ok "inventory parses"
    else
      fail "inventory does not parse"
    fi
  fi
fi

if [[ -f "$BOOTSTRAP_INVENTORY" ]]; then
  if has_placeholder "$BOOTSTRAP_INVENTORY"; then
    fail "bootstrap inventory still contains REPLACE_WITH placeholders"
  else
    ok "bootstrap inventory has no REPLACE_WITH placeholders"
  fi
  if command -v ansible-inventory >/dev/null 2>&1; then
    if ansible-inventory -i "$BOOTSTRAP_INVENTORY" --list >/dev/null 2>&1; then
      ok "bootstrap inventory parses"
    else
      fail "bootstrap inventory does not parse"
    fi
  fi
fi

if [[ -f "$ALL_VARS" ]]; then
  if grep -Eq '^cloudflared_version:\s*latest\s*$' "$ALL_VARS"; then
    fail "cloudflared_version must not be latest"
  elif grep -Eq '^cloudflared_version:\s*[0-9]' "$ALL_VARS"; then
    ok "cloudflared_version is pinned"
  else
    fail "cloudflared_version missing or not pinned"
  fi
else
  fail "missing Deployment/inventory/prod/group_vars/all.yml"
fi

if [[ "$MODE" == "deploy" ]]; then
  if [[ -f "$VAULT" ]]; then
    ok "encrypted vault exists"
    if command -v ansible-vault >/dev/null 2>&1; then
      if bash "$SCRIPT_DIR/check-vault.sh"; then
        ok "encrypted vault contents are usable"
      else
        fail "encrypted vault contents are not usable"
      fi
    fi
  else
    fail "vault missing; run Deployment/scripts/setup-secrets.sh"
  fi
else
  [[ -f "$VAULT" ]] && ok "encrypted vault exists" || warn "vault missing; create it before deploy phase"
fi

if [[ "$FAILURES" -gt 0 ]]; then
  echo
  echo "$MODE status failed with $FAILURES blocking issue(s)"
  exit 1
fi

echo
echo "$MODE status ok"
