#!/usr/bin/env bash
set -euo pipefail

usage() {
  local exit_code="${1:-1}"
  cat >&2 <<'EOF'
usage: cleanup-renamed-localcluster-app.sh --old-app-name <name> --confirm-cleanup [options]

Clean up local cluster leftovers after a renamed app has deployed and passed
acceptance. Run this on the control machine from the renamed app checkout.

Required:
  --old-app-name <name>       Previous app_name, for example oldapp.
  --confirm-cleanup           Required before removing old runtime files/services.

Options:
  --old-deploy-root <path>    Previous deploy root. Defaults to /opt/<old-app-name>.
  --old-runner-name <name>    Previous runner name. Defaults to node-main-<old-app-name>.
  --skip-acceptance-check     Do not run acceptance-check.sh before cleanup.
  --remove-old-deploy-key     Also remove the old deploy SSH key from authorized_keys,
                              node-main, and the control machine.
  -h, --help                  Show this help.

Example:
  bash ./Deployment/LocalCluster/Scripts/cleanup-renamed-localcluster-app.sh \
    --old-app-name ship \
    --confirm-cleanup
EOF
  exit "$exit_code"
}

fail() {
  echo "renamed app cleanup failed: $*" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"
export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/LocalCluster/ansible/ansible.cfg"

OLD_APP_NAME=""
OLD_DEPLOY_ROOT=""
OLD_RUNNER_NAME=""
CONFIRM_CLEANUP="no"
SKIP_ACCEPTANCE_CHECK="no"
REMOVE_OLD_DEPLOY_KEY="no"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --old-app-name)
      [[ $# -ge 2 ]] || usage
      OLD_APP_NAME="$2"
      shift 2
      ;;
    --old-deploy-root)
      [[ $# -ge 2 ]] || usage
      OLD_DEPLOY_ROOT="$2"
      shift 2
      ;;
    --old-runner-name)
      [[ $# -ge 2 ]] || usage
      OLD_RUNNER_NAME="$2"
      shift 2
      ;;
    --confirm-cleanup)
      CONFIRM_CLEANUP="yes"
      shift
      ;;
    --skip-acceptance-check)
      SKIP_ACCEPTANCE_CHECK="yes"
      shift
      ;;
    --remove-old-deploy-key)
      REMOVE_OLD_DEPLOY_KEY="yes"
      shift
      ;;
    -h|--help)
      usage 0
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$OLD_APP_NAME" ]] || usage
[[ "$CONFIRM_CLEANUP" == "yes" ]] || fail "--confirm-cleanup is required"
[[ "$OLD_APP_NAME" =~ ^[a-z][a-z0-9-]{0,31}$ ]] || fail "old app name must be lowercase and app-name shaped"

if [[ -z "$OLD_DEPLOY_ROOT" ]]; then
  OLD_DEPLOY_ROOT="/opt/$OLD_APP_NAME"
fi

if [[ -z "$OLD_RUNNER_NAME" ]]; then
  OLD_RUNNER_NAME="node-main-$OLD_APP_NAME"
fi

[[ "$OLD_DEPLOY_ROOT" == /opt/* ]] || fail "old deploy root must be under /opt"
[[ "$OLD_DEPLOY_ROOT" != "/opt/" ]] || fail "old deploy root must not be /opt/"
[[ ! "$OLD_DEPLOY_ROOT" =~ [[:space:]] ]] || fail "old deploy root must not contain whitespace"
[[ "$OLD_DEPLOY_ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]] || fail "old deploy root contains unsupported characters"
[[ "$OLD_RUNNER_NAME" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || fail "old runner name contains unsupported characters"

command -v ansible >/dev/null 2>&1 || fail "ansible is missing"
command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"

APP_NAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_name)"
DEPLOY_ROOT="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" deploy_root)"
PUBLIC_HOSTNAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" public_hostname)"
RUNNER_NAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" runner_name)"

[[ "$APP_NAME" != "$OLD_APP_NAME" ]] || fail "current app_name is still $OLD_APP_NAME"
[[ "$DEPLOY_ROOT" != "$OLD_DEPLOY_ROOT" ]] || fail "current deploy_root equals old deploy root"

cat <<EOF
Renamed LocalCluster cleanup

Current app:
  app_name:        $APP_NAME
  public_hostname: $PUBLIC_HOSTNAME
  deploy_root:     $DEPLOY_ROOT
  runner_name:     $RUNNER_NAME

Old app:
  old_app_name:    $OLD_APP_NAME
  old_deploy_root: $OLD_DEPLOY_ROOT
  old_runner_name: $OLD_RUNNER_NAME

Cleanup:
  remove old deploy key: $REMOVE_OLD_DEPLOY_KEY
EOF

if [[ "$SKIP_ACCEPTANCE_CHECK" != "yes" ]]; then
  bash "$SCRIPT_DIR/acceptance-check.sh"
fi

echo "Removing old Caddy site and reloading Caddy if needed."
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
  "OLD_APP_NAME=$(printf '%q' "$OLD_APP_NAME") bash -lc 'set -euo pipefail
site=\"/etc/caddy/sites/\${OLD_APP_NAME}.caddy\"
if [ -f \"\$site\" ]; then
  rm -f \"\$site\"
  caddy validate --config /etc/caddy/Caddyfile
  systemctl reload caddy
  echo \"removed old Caddy site: \$site\"
else
  echo \"old Caddy site absent: \$site\"
fi'" \
  --become

echo "Removing old app markers."
ansible all -i "$INVENTORY" -m ansible.builtin.shell -a \
  "OLD_APP_NAME=$(printf '%q' "$OLD_APP_NAME") bash -lc 'set -euo pipefail
marker=\"/etc/localcluster/apps/\${OLD_APP_NAME}.env\"
if [ -f \"\$marker\" ]; then
  APP_NAME=\"\"
  . \"\$marker\"
  if [ \"\$APP_NAME\" != \"\$OLD_APP_NAME\" ]; then
    echo \"refusing to remove \$marker; marker APP_NAME=\$APP_NAME\" >&2
    exit 1
  fi
  rm -f \"\$marker\"
  echo \"removed old marker: \$marker\"
else
  echo \"old marker absent: \$marker\"
fi'" \
  --become

echo "Removing old firewall service and script."
ansible all -i "$INVENTORY" -m ansible.builtin.shell -a \
  "OLD_APP_NAME=$(printf '%q' "$OLD_APP_NAME") bash -lc 'set -euo pipefail
systemctl disable --now \"\${OLD_APP_NAME}-docker-user-firewall.service\" >/dev/null 2>&1 || true
rm -f \"/etc/systemd/system/\${OLD_APP_NAME}-docker-user-firewall.service\"
rm -f \"/usr/local/sbin/\${OLD_APP_NAME}-docker-user-firewall\"
systemctl daemon-reload
echo \"removed old firewall service/script for \$OLD_APP_NAME\"'" \
  --become

echo "Removing old runtime root and Docker Compose resources."
OLD_APP_NAME_Q="$(printf '%q' "$OLD_APP_NAME")"
OLD_DEPLOY_ROOT_Q="$(printf '%q' "$OLD_DEPLOY_ROOT")"
ansible app_servers:node_db -i "$INVENTORY" -m ansible.builtin.shell -a \
  "OLD_APP_NAME=$OLD_APP_NAME_Q OLD_DEPLOY_ROOT=$OLD_DEPLOY_ROOT_Q bash -lc 'set -euo pipefail
if [ ! -d \"\$OLD_DEPLOY_ROOT\" ]; then
  echo \"old deploy root absent: \$OLD_DEPLOY_ROOT\"
  exit 0
fi
if [ -f \"\$OLD_DEPLOY_ROOT/.env\" ]; then
  root_app=\"\$(sed -n \"s/^APP_NAME=//p\" \"\$OLD_DEPLOY_ROOT/.env\" | tail -n 1)\"
  if [ -n \"\$root_app\" ] && [ \"\$root_app\" != \"\$OLD_APP_NAME\" ]; then
    echo \"refusing to remove \$OLD_DEPLOY_ROOT; .env says APP_NAME=\$root_app\" >&2
    exit 1
  fi
fi
if [ -f \"\$OLD_DEPLOY_ROOT/docker-compose.yml\" ]; then
  cd \"\$OLD_DEPLOY_ROOT\"
  docker compose down -v --remove-orphans || true
fi
rm -rf \"\$OLD_DEPLOY_ROOT\"
echo \"removed old deploy root: \$OLD_DEPLOY_ROOT\"'" \
  --become

echo "Removing old GitHub runner from node-main."
OLD_RUNNER_NAME_Q="$(printf '%q' "$OLD_RUNNER_NAME")"
OLD_RUNNER_DIR_Q="$(printf '%q' "/opt/actions-runner-$OLD_APP_NAME")"
ansible load_balancer -i "$INVENTORY" -m ansible.builtin.shell -a \
  "OLD_RUNNER_NAME=$OLD_RUNNER_NAME_Q OLD_RUNNER_DIR=$OLD_RUNNER_DIR_Q bash -lc 'set -euo pipefail
if [ ! -d \"\$OLD_RUNNER_DIR\" ]; then
  echo \"old runner directory absent: \$OLD_RUNNER_DIR\"
  exit 0
fi
cd \"\$OLD_RUNNER_DIR\"
if [ -f ./svc.sh ]; then
  ./svc.sh stop || true
  ./svc.sh uninstall || true
fi
cd /
rm -rf \"\$OLD_RUNNER_DIR\"
echo \"removed old runner directory: \$OLD_RUNNER_DIR\"'" \
  --become

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  REPO_NAME="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
  RUNNERS_JSON="$(gh api "repos/$REPO_NAME/actions/runners?per_page=100")"
  RUNNER_ID="$(RUNNERS_JSON="$RUNNERS_JSON" python3 - "$OLD_RUNNER_NAME" <<'PY'
from __future__ import annotations

import json
import os
import sys

old_runner_name = sys.argv[1]
payload = json.loads(os.environ["RUNNERS_JSON"])
for runner in payload.get("runners", []):
    if isinstance(runner, dict) and runner.get("name") == old_runner_name:
        print(runner.get("id", ""))
        raise SystemExit(0)
print("")
PY
)"
  if [[ -n "$RUNNER_ID" ]]; then
    gh api -X DELETE "repos/$REPO_NAME/actions/runners/$RUNNER_ID" >/dev/null
    echo "removed old GitHub runner registration: $OLD_RUNNER_NAME"
  else
    echo "old GitHub runner registration absent: $OLD_RUNNER_NAME"
  fi
else
  echo "gh is missing or unauthenticated; remove GitHub runner registration manually if it remains: $OLD_RUNNER_NAME"
fi

if [[ "$REMOVE_OLD_DEPLOY_KEY" == "yes" ]]; then
  OLD_KEY="$HOME/.ssh/${OLD_APP_NAME}_deploy"
  OLD_PUB="$OLD_KEY.pub"
  if [[ -f "$OLD_PUB" ]]; then
    OLD_PUBLIC_KEY="$(cat "$OLD_PUB")"
    OLD_PUBLIC_KEY_Q="$(printf '%q' "$OLD_PUBLIC_KEY")"
    ansible all -i "$INVENTORY" -m ansible.builtin.shell -a \
      "OLD_PUBLIC_KEY=$OLD_PUBLIC_KEY_Q bash -lc 'set -euo pipefail
auth=/home/deploy/.ssh/authorized_keys
if [ -f \"\$auth\" ]; then
  tmp=\"\$(mktemp)\"
  grep -Fvx \"\$OLD_PUBLIC_KEY\" \"\$auth\" > \"\$tmp\" || true
  cat \"\$tmp\" > \"\$auth\"
  rm -f \"\$tmp\"
  chown deploy:deploy \"\$auth\"
  chmod 0600 \"\$auth\"
  echo \"removed old deploy public key from \$auth\"
else
  echo \"authorized_keys absent: \$auth\"
fi'" \
      --become
  else
    echo "old deploy public key absent on control machine: $OLD_PUB"
  fi

  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.file -a \
    "path=/home/deploy/.ssh/${OLD_APP_NAME}_deploy state=absent" \
    --become
  ansible load_balancer -i "$INVENTORY" -m ansible.builtin.file -a \
    "path=/home/deploy/.ssh/${OLD_APP_NAME}_deploy.pub state=absent" \
    --become
  rm -f "$OLD_KEY" "$OLD_PUB"
  echo "removed old deploy key from control machine: $OLD_KEY"
fi

echo
echo "renamed app cleanup complete"
