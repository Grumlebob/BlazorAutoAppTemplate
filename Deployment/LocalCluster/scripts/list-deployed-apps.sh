#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

[[ -f "$INVENTORY" ]] || {
  echo "deployed app listing failed: missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
}

echo "Known LocalCluster app markers on node-main"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a '
set -eu
found=0
for marker in /etc/localcluster/apps/*.env; do
  [ -f "$marker" ] || continue
  found=1
  APP_NAME=""
  DEPLOY_ROOT=""
  PUBLIC_HOSTNAME=""
  APP_PORT=""
  POSTGRES_PORT=""
  REDIS_PORT=""
  RUNNER_LABEL=""
  CLOUDFLARE_TUNNEL_NAME=""
  . "$marker"
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$APP_NAME" "$DEPLOY_ROOT" "$PUBLIC_HOSTNAME" "$APP_PORT" "$POSTGRES_PORT" "$REDIS_PORT" "$RUNNER_LABEL" "$CLOUDFLARE_TUNNEL_NAME"
done
if [ "$found" -eq 0 ]; then
  echo "no app markers found on $(hostname)"
fi
'
