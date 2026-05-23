#!/usr/bin/env bash
set -u

MODE="${1:-deploy}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
BOOTSTRAP_INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/bootstrap-hosts.yml"
MACHINES="$REPO_ROOT/Deployment/LocalCluster/machines.yml"
VAULT="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/vault.yml"

if [[ "$MODE" != "bootstrap" && "$MODE" != "deploy" ]]; then
  echo "usage: $0 [bootstrap|deploy]" >&2
  exit 1
fi

FAILURES=0
WARNINGS=0
NEXT_ACTION=""

ok() {
  printf 'OK    %s\n' "$*"
}

warn() {
  printf 'WARN  %s\n' "$*"
  WARNINGS=$((WARNINGS + 1))
}

fail() {
  printf 'FAIL  %s\n' "$*"
  FAILURES=$((FAILURES + 1))
  if [[ -z "$NEXT_ACTION" ]]; then
    NEXT_ACTION="$*"
  fi
}

check_command() {
  local command_name="$1"
  local required="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    ok "$command_name installed"
  elif [[ "$required" == "required" ]]; then
    fail "$command_name missing"
  else
    warn "$command_name missing"
  fi
}

has_placeholder() {
  local file="$1"
  [[ -f "$file" ]] && grep -R "REPLACE_WITH" "$file" >/dev/null 2>&1
}

run_check() {
  local label="$1"
  local output_file
  local error_file
  shift
  output_file="$(mktemp "${TMPDIR:-/tmp}/localcluster-doctor-check.XXXXXX.out")" || {
    fail "$label"
    return
  }
  error_file="$(mktemp "${TMPDIR:-/tmp}/localcluster-doctor-check.XXXXXX.err")" || {
    rm -f "$output_file"
    fail "$label"
    return
  }
  if "$@" >"$output_file" 2>"$error_file"; then
    ok "$label"
  else
    fail "$label"
    sed 's/^/      /' "$error_file" >&2
  fi
  rm -f "$output_file" "$error_file"
}

echo "LocalCluster doctor ($MODE)"
echo
bash "$SCRIPT_DIR/summary.sh" || fail "deployment summary could not be printed"
echo
echo "Local checks"

check_command python3 required
check_command ssh required
check_command ansible required
check_command ansible-inventory required
check_command ansible-playbook required
[[ "$MODE" == "deploy" ]] && check_command ansible-vault required || check_command ansible-vault optional

if [[ -f "$MACHINES" ]]; then
  ok "machines.yml exists"
  has_placeholder "$MACHINES" && fail "machines.yml still contains placeholders" || ok "machines.yml has no placeholders"
else
  warn "machines.yml missing"
fi

if python3 "$SCRIPT_DIR/lib/validate-deploy-settings.py" >/dev/null 2>&1; then
  ok "deployment settings are valid"
  APP_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" app_name)"
  SSH_KEY="$HOME/.ssh/${APP_NAME}_deploy"
  SSH_PUB="$SSH_KEY.pub"
else
  fail "deployment settings are invalid"
  APP_NAME=""
  SSH_KEY=""
  SSH_PUB=""
fi

if [[ -n "$APP_NAME" ]]; then
  [[ -f "$SSH_KEY" ]] && ok "SSH private key exists: $SSH_KEY" || fail "missing SSH private key: $SSH_KEY"
  [[ -f "$SSH_PUB" ]] && ok "SSH public key exists: $SSH_PUB" || fail "missing SSH public key: $SSH_PUB"
fi

if [[ -f "$INVENTORY" ]]; then
  ok "inventory exists"
  has_placeholder "$INVENTORY" && fail "inventory still contains placeholders" || ok "inventory has no placeholders"
  command -v ansible-inventory >/dev/null 2>&1 && run_check "inventory parses" ansible-inventory -i "$INVENTORY" --list
else
  fail "inventory missing"
fi

if [[ "$MODE" == "bootstrap" ]]; then
  if [[ -f "$BOOTSTRAP_INVENTORY" ]]; then
    ok "bootstrap inventory exists"
    has_placeholder "$BOOTSTRAP_INVENTORY" && fail "bootstrap inventory still contains placeholders" || ok "bootstrap inventory has no placeholders"
    command -v ansible-inventory >/dev/null 2>&1 && run_check "bootstrap inventory parses" ansible-inventory -i "$BOOTSTRAP_INVENTORY" --list
  else
    fail "bootstrap inventory missing"
  fi
fi

if [[ "$MODE" == "deploy" ]]; then
  if [[ -f "$VAULT" ]]; then
    ok "vault exists"
    if command -v ansible-vault >/dev/null 2>&1; then
      run_check "vault decrypts and validates" bash "$SCRIPT_DIR/check-vault.sh"
    fi
  else
    fail "vault missing"
  fi
fi

REMOTE_READY=0
if [[ -f "$INVENTORY" && -n "${SSH_KEY:-}" && -f "$SSH_KEY" ]] && ! has_placeholder "$INVENTORY" && command -v ansible >/dev/null 2>&1; then
  REMOTE_READY=1
fi

echo
echo "Remote checks"
if [[ "$REMOTE_READY" == "1" ]]; then
  run_check "all nodes respond to Ansible ping" ansible all -i "$INVENTORY" -m ping
  run_check "Docker Compose is available on prepared nodes" ansible all -i "$INVENTORY" -a "docker compose version"
  if [[ "$MODE" == "deploy" ]]; then
    run_check "side-by-side settings do not collide with known markers" bash "$SCRIPT_DIR/validate-side-by-side.sh"
  fi
else
  warn "remote checks skipped until inventory has real IPs and the deploy SSH key exists"
fi

echo
if [[ "$FAILURES" -gt 0 ]]; then
  echo "doctor failed with $FAILURES blocking issue(s) and $WARNINGS warning(s)"
  case "$NEXT_ACTION" in
    *"deployment settings"*) echo "Next likely action: edit Deployment/LocalCluster/inventory/prod/group_vars/all.yml." ;;
    *"machines.yml"*) echo "Next likely action: copy and fill Deployment/LocalCluster/machines.example.yml." ;;
    *"ansible"*|*"SSH private key"*|*"SSH public key"*) echo "Next likely action: run Deployment/LocalCluster/scripts/setup-control-machine.sh." ;;
    *"inventory"*) echo "Next likely action: run Deployment/LocalCluster/scripts/generate-inventory.sh after machines.yml is filled." ;;
    *"vault"*) echo "Next likely action: run Deployment/LocalCluster/scripts/setup-secrets.sh." ;;
    *) echo "Next likely action: fix the first FAIL line above, then rerun doctor.sh." ;;
  esac
  exit 1
fi

echo "doctor ok with $WARNINGS warning(s)"
if [[ "$MODE" == "bootstrap" ]]; then
  echo "Next likely action: run verify-bootstrap.sh or prepare-fresh-linux-machines.sh."
else
  echo "Next likely action: run preflight.sh deploy, then deploy from GitHub Actions or run acceptance-check.sh after deploy."
fi
