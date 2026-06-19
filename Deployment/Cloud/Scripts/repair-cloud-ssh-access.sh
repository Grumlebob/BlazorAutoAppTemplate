#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SSH_KEY="${CLOUD_SSH_PRIVATE_KEY_PATH:?CLOUD_SSH_PRIVATE_KEY_PATH is required}"
BASTION_HOST="${CLOUD_BASTION_HOST:?CLOUD_BASTION_HOST is required}"
KNOWN_HOSTS="${CLOUD_KNOWN_HOSTS_FILE:-$HOME/.ssh/known_hosts}"
PUBLIC_KEY_FILE="${CLOUD_EXPECTED_SSH_PUBLIC_KEY_FILE:-$REPO_ROOT/Deployment/Cloud/infra/opentofu/bookscloud_deploy.pub}"

fail() {
  echo "repair Cloud SSH access failed: $*" >&2
  exit 1
}

setting() {
  bash "$SCRIPT_DIR/read-cloud-setting.sh" "$1"
}

[[ -f "$SSH_KEY" ]] || fail "missing private key: $SSH_KEY"
[[ -f "$PUBLIC_KEY_FILE" ]] || fail "missing public key reference: $PUBLIC_KEY_FILE"

PUBLIC_KEY="$(awk '{ print $1 " " $2 " " ($3 ? $3 : "bookscloud-deploy") }' "$PUBLIC_KEY_FILE")"
SSH_BASE=(
  -i "$SSH_KEY"
  -o IdentitiesOnly=yes
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o UserKnownHostsFile="$KNOWN_HOSTS"
  -o ConnectTimeout=8
)

ssh_ok() {
  local user="$1"
  local host="$2"
  shift 2
  ssh "${SSH_BASE[@]}" "$@" "${user}@${host}" true >/dev/null 2>&1
}

install_deploy_key() {
  local user="$1"
  local host="$2"
  local public_key_b64
  shift 2

  public_key_b64="$(printf '%s' "$PUBLIC_KEY" | base64 | tr -d '\n')"
  ssh "${SSH_BASE[@]}" "$@" "${user}@${host}" "if command -v sudo >/dev/null 2>&1; then sudo env PUBLIC_KEY_B64='$public_key_b64' sh -s; else PUBLIC_KEY_B64='$public_key_b64' sh -s; fi" <<'EOF'
set -eu
PUBLIC_KEY="$(printf '%s' "$PUBLIC_KEY_B64" | base64 -d)"
if ! id deploy >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash --groups sudo deploy
fi
usermod -aG sudo deploy >/dev/null 2>&1 || true
deploy_home="$(getent passwd deploy | cut -d: -f6)"
if [ -z "$deploy_home" ]; then
  deploy_home=/home/deploy
fi
install -d -m 0700 -o deploy -g deploy "$deploy_home/.ssh"
touch "$deploy_home/.ssh/authorized_keys"
if ! grep -qxF "$PUBLIC_KEY" "$deploy_home/.ssh/authorized_keys"; then
  printf '%s\n' "$PUBLIC_KEY" >> "$deploy_home/.ssh/authorized_keys"
fi
chown deploy:deploy "$deploy_home/.ssh/authorized_keys"
chmod 0600 "$deploy_home/.ssh/authorized_keys"
printf '%s\n' 'deploy ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/90-deploy-user
chmod 0440 /etc/sudoers.d/90-deploy-user
EOF
}

repair_host() {
  local name="$1"
  local host="$2"
  shift 2

  if ssh_ok deploy "$host" "$@"; then
    echo "${name}: deploy SSH access ok"
    return 0
  fi

  for bootstrap_user in root ubuntu; do
    if ssh_ok "$bootstrap_user" "$host" "$@"; then
      echo "${name}: repairing deploy SSH access through ${bootstrap_user}"
      install_deploy_key "$bootstrap_user" "$host" "$@"
      if ssh_ok deploy "$host" "$@"; then
        echo "${name}: deploy SSH access repaired"
        return 0
      fi
      fail "${name}: ${bootstrap_user} was reachable but deploy still cannot authenticate after repair"
    fi
  done

  fail "${name}: deploy, root, and ubuntu SSH authentication all failed"
}

repair_host "cloud-main" "$BASTION_HOST"

PROXY_ARGS=(
  -o "ProxyCommand=ssh -W %h:%p -i $SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KNOWN_HOSTS deploy@$BASTION_HOST"
)

repair_host "cloud-app1" "$(setting cloud_app1_private_ip)" "${PROXY_ARGS[@]}"
repair_host "cloud-app2" "$(setting cloud_app2_private_ip)" "${PROXY_ARGS[@]}"
repair_host "cloud-db" "$(setting cloud_db_private_ip)" "${PROXY_ARGS[@]}"
