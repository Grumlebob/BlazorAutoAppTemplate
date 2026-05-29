#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/Cloud/inventory/prod/hosts.yml"
ATTEMPTS="${CLOUD_SSH_WAIT_ATTEMPTS:-30}"
DELAY_SECONDS="${CLOUD_SSH_WAIT_DELAY_SECONDS:-10}"
DEBUG="${CLOUD_SSH_WAIT_DEBUG:-0}"

fail() {
  echo "Cloud SSH reachability check failed: $*" >&2
  exit 1
}

summarize_failure() {
  local output="$1"

  if [[ "$DEBUG" == "1" ]]; then
    echo "$output" | sed 's/^/  /'
    return
  fi

  if grep -qi "REMOTE HOST IDENTIFICATION HAS CHANGED" <<<"$output"; then
    cat <<'EOF'
  SSH host key changed. If Cloud servers were just replaced, run:
    bash ./Deployment/Cloud/Scripts/reset-cloud-known-hosts.sh
EOF
    return
  fi

  if grep -qi "Permission denied" <<<"$output"; then
    echo "  SSH authentication failed. Check ~/.ssh/bookscloud_deploy and the deploy key installed by OpenTofu."
    return
  fi

  if grep -qi "timed out during banner exchange" <<<"$output"; then
    echo "  SSH is reachable but not fully ready yet; banner exchange timed out."
    return
  fi

  if grep -qi "UNKNOWN port 65535" <<<"$output"; then
    echo "  Bastion SSH is up, but a private node is not reachable through ProxyCommand yet."
    return
  fi

  if grep -qiE "Connection timed out|No route to host|Connection refused|Connection closed" <<<"$output"; then
    grep -iE "Connection timed out|No route to host|Connection refused|Connection closed" <<<"$output" \
      | tail -n 2 \
      | sed -E 's/^\s*\[ERROR\]: Task failed: //' \
      | sed 's/^/  last cause: /'
    return
  fi

  grep -iE "FAILED|Permission denied|Host key|Connection|No route|Could not" <<<"$output" \
    | tail -n 2 \
    | sed 's/^/  last cause: /' || true
}

command -v ansible >/dev/null 2>&1 || fail "ansible is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/Cloud/inventory/prod/hosts.yml. Run Step 8 first."

export ANSIBLE_CONFIG="$REPO_ROOT/Deployment/Cloud/ansible/ansible.cfg"
export ANSIBLE_ROLES_PATH="$REPO_ROOT/Deployment/Cloud/ansible/roles"

last_output=""
for attempt in $(seq 1 "$ATTEMPTS"); do
  if last_output="$(ansible cloud -i "$INVENTORY" -m ansible.builtin.ping 2>&1)"; then
    echo "Cloud SSH reachability check ok"
    echo "$last_output"
    exit 0
  fi

  if ((attempt < ATTEMPTS)); then
    echo "Cloud SSH still warming up (${attempt}/${ATTEMPTS}); retrying in ${DELAY_SECONDS}s..."
    summarize_failure "$last_output"
    sleep "$DELAY_SECONDS"
  fi
done

echo "$last_output" >&2
cat >&2 <<'EOF'

Could not reach all Cloud nodes over SSH.

For full Ansible output while debugging, rerun with:
  CLOUD_SSH_WAIT_DEBUG=1 bash ./Deployment/Cloud/Scripts/check-ssh-reachability.sh

If cloud-main is reachable but cloud-app1/cloud-app2/cloud-db fail at 10.10.0.x
through ProxyJump, the private network is not usable from the bastion yet.
If this happened during quick recreate, rerun the same quick recreate command after
a minute; OpenTofu should keep the existing servers and continue from provisioning.
EOF
exit 1
