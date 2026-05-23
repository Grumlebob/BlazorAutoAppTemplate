#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

fail() {
  echo "side-by-side validation failed: $*" >&2
  exit 1
}

[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"
command -v ansible >/dev/null 2>&1 || fail "ansible is missing"

APP_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" app_name)"
APP_PORT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" app_port)"
POSTGRES_PORT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" postgres_port)"
REDIS_PORT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" redis_port)"
DEPLOY_ROOT="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" deploy_root)"
PUBLIC_HOSTNAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" public_hostname)"
CLOUDFLARE_TUNNEL_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" cloudflare_tunnel_name)"
RUNNER_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" runner_name)"
RUNNER_LABEL="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" runner_label)"

ansible all -i "$INVENTORY" -m ansible.builtin.shell -a \
  "CURRENT_APP_NAME=$APP_NAME CURRENT_APP_PORT=$APP_PORT CURRENT_POSTGRES_PORT=$POSTGRES_PORT CURRENT_REDIS_PORT=$REDIS_PORT CURRENT_DEPLOY_ROOT=$DEPLOY_ROOT CURRENT_PUBLIC_HOSTNAME=$PUBLIC_HOSTNAME CURRENT_TUNNEL=$CLOUDFLARE_TUNNEL_NAME CURRENT_RUNNER_NAME=$RUNNER_NAME CURRENT_RUNNER_LABEL=$RUNNER_LABEL bash -lc 'set -eu; failures=0; warnings=0; for marker in /etc/localcluster/apps/*.env; do [ -f \"\$marker\" ] || continue; APP_NAME=\"\" APP_PORT=\"\" POSTGRES_PORT=\"\" REDIS_PORT=\"\" DEPLOY_ROOT=\"\" PUBLIC_HOSTNAME=\"\" CLOUDFLARE_TUNNEL_NAME=\"\" RUNNER_NAME=\"\" RUNNER_LABEL=\"\"; . \"\$marker\"; if [ \"\$APP_NAME\" = \"\$CURRENT_APP_NAME\" ] && [ \"\$DEPLOY_ROOT\" = \"\$CURRENT_DEPLOY_ROOT\" ]; then continue; fi; check_conflict() { local field=\"\$1\" existing=\"\$2\" current=\"\$3\"; if [ -n \"\$existing\" ] && [ \"\$existing\" = \"\$current\" ]; then echo \"conflict: \$field \$current is already used by \$APP_NAME (\$marker)\" >&2; failures=\$((failures + 1)); fi; }; check_conflict app_name \"\$APP_NAME\" \"\$CURRENT_APP_NAME\"; check_conflict app_port \"\$APP_PORT\" \"\$CURRENT_APP_PORT\"; check_conflict postgres_port \"\$POSTGRES_PORT\" \"\$CURRENT_POSTGRES_PORT\"; check_conflict redis_port \"\$REDIS_PORT\" \"\$CURRENT_REDIS_PORT\"; check_conflict deploy_root \"\$DEPLOY_ROOT\" \"\$CURRENT_DEPLOY_ROOT\"; check_conflict public_hostname \"\$PUBLIC_HOSTNAME\" \"\$CURRENT_PUBLIC_HOSTNAME\"; check_conflict runner_name \"\$RUNNER_NAME\" \"\$CURRENT_RUNNER_NAME\"; check_conflict runner_label \"\$RUNNER_LABEL\" \"\$CURRENT_RUNNER_LABEL\"; if [ -n \"\$CLOUDFLARE_TUNNEL_NAME\" ] && [ \"\$CLOUDFLARE_TUNNEL_NAME\" != \"\$CURRENT_TUNNEL\" ]; then echo \"warning: \$APP_NAME uses tunnel \$CLOUDFLARE_TUNNEL_NAME; shared tunnel default is \$CURRENT_TUNNEL\" >&2; warnings=\$((warnings + 1)); fi; done; if [ \"\$failures\" -gt 0 ]; then exit 1; fi; echo \"marker validation ok (warnings=\$warnings)\"'"

echo "side-by-side validation ok"
