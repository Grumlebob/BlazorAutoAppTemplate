#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: prepare-existing-localcluster-app.sh --existing-key <path>

Use this for a second LocalCluster app on nodes that were already prepared by
another LocalCluster app. The existing key must already be authorized for the
deploy user on all nodes, for example ~/.ssh/firstapp_deploy.
EOF
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

EXISTING_KEY="${LOCALCLUSTER_EXISTING_DEPLOY_KEY:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --existing-key)
      [[ $# -ge 2 ]] || usage
      EXISTING_KEY="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$EXISTING_KEY" ]] || usage
EXISTING_KEY="${EXISTING_KEY/#\~/$HOME}"

command -v ansible-playbook >/dev/null 2>&1 || {
  echo "ansible-playbook is missing. Run Deployment/LocalCluster/scripts/setup-control-machine.sh first." >&2
  exit 1
}
command -v ansible >/dev/null 2>&1 || {
  echo "ansible is missing. Run Deployment/LocalCluster/scripts/setup-control-machine.sh first." >&2
  exit 1
}
command -v ansible-inventory >/dev/null 2>&1 || {
  echo "ansible-inventory is missing. Run Deployment/LocalCluster/scripts/setup-control-machine.sh first." >&2
  exit 1
}
[[ -f "$INVENTORY" ]] || {
  echo "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
}
[[ -f "$EXISTING_KEY" ]] || {
  echo "existing deploy key not found: $EXISTING_KEY" >&2
  exit 1
}

python3 "$SCRIPT_DIR/lib/validate-deploy-settings.py" >/dev/null
APP_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" app_name)"
PRIVATE_KEY="$HOME/.ssh/${APP_NAME}_deploy"
PUBLIC_KEY="$PRIVATE_KEY.pub"

[[ -f "$PRIVATE_KEY" ]] || {
  echo "this app's private key is missing: $PRIVATE_KEY" >&2
  echo "run Deployment/LocalCluster/scripts/setup-control-machine.sh first" >&2
  exit 1
}
[[ -f "$PUBLIC_KEY" ]] || {
  echo "this app's public key is missing: $PUBLIC_KEY" >&2
  echo "run Deployment/LocalCluster/scripts/setup-control-machine.sh first" >&2
  exit 1
}

if grep -R "REPLACE_WITH" "$INVENTORY" >/dev/null; then
  echo "replace all REPLACE_WITH values in Deployment/LocalCluster/inventory/prod/hosts.yml" >&2
  exit 1
fi

ansible-inventory -i "$INVENTORY" --list >/dev/null
export ANSIBLE_HOST_KEY_CHECKING=False
ansible all -i "$INVENTORY" -e "ansible_ssh_private_key_file=$EXISTING_KEY" -m ping

cd "$REPO_ROOT/Deployment/LocalCluster/ansible"
ansible-playbook \
  -i ../inventory/prod/hosts.yml \
  playbooks/PrepareExistingLocalClusterApp.yml \
  -e "ansible_ssh_private_key_file=$EXISTING_KEY" \
  -e "deploy_public_key_file=$PUBLIC_KEY" \
  -e "deploy_private_key_file=$PRIVATE_KEY"

ansible all -i ../inventory/prod/hosts.yml -m ping

echo
echo "existing LocalCluster nodes are ready for app: $APP_NAME"
echo "new deploy key installed: $PRIVATE_KEY"
