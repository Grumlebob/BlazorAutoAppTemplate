#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/inventory/prod/hosts.yml"

fail() {
  echo "runner setup failed: $*" >&2
  exit 1
}

command -v gh >/dev/null 2>&1 || fail "gh is missing. Install GitHub CLI and run gh auth login."
command -v ssh >/dev/null 2>&1 || fail "ssh is missing."
command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
gh auth status >/dev/null 2>&1 || fail "gh is not authenticated. Run gh auth login."
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/inventory/prod/hosts.yml"

APP_NAME="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" app_name)"
SSH_KEY="$HOME/.ssh/${APP_NAME}_deploy"
[[ -f "$SSH_KEY" ]] || fail "missing SSH key: $SSH_KEY"

NODE_MAIN_IP="$(python3 - "$INVENTORY" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig").splitlines()
in_node_main = False
for line in text:
    if re.match(r"^\s*node-main:\s*$", line):
        in_node_main = True
        continue
    if in_node_main:
        match = re.match(r"^\s*ansible_host:\s*(\S+)\s*$", line)
        if match:
            print(match.group(1))
            raise SystemExit(0)
        if re.match(r"^\s*[A-Za-z0-9_-]+:\s*$", line):
            break
raise SystemExit("node-main ansible_host not found")
PY
)"

[[ "$NODE_MAIN_IP" != REPLACE_WITH* ]] || fail "replace node-main IP in generated inventory first"

REPO_NAME="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
REPO_URL="$(gh repo view --json url --jq .url)"
RUNNER_TOKEN="$(gh api -X POST "repos/$REPO_NAME/actions/runners/registration-token" --jq .token)"
RUNNER_TAG="$(gh release view --repo actions/runner --json tagName --jq .tagName)"
RUNNER_VERSION="${RUNNER_TAG#v}"
REMOTE_ARCH="$(ssh -i "$SSH_KEY" "deploy@$NODE_MAIN_IP" 'uname -m')"

case "$REMOTE_ARCH" in
  x86_64|amd64) ;;
  *) fail "this deployment supports only x86_64/amd64 node-main machines; got $REMOTE_ARCH" ;;
esac

RUNNER_DOWNLOAD_URL="https://github.com/actions/runner/releases/download/${RUNNER_TAG}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
REPO_URL_Q="$(printf '%q' "$REPO_URL")"
RUNNER_DOWNLOAD_URL_Q="$(printf '%q' "$RUNNER_DOWNLOAD_URL")"
RUNNER_TOKEN_Q="$(printf '%q' "$RUNNER_TOKEN")"

ssh -i "$SSH_KEY" "deploy@$NODE_MAIN_IP" \
  "REPO_URL=$REPO_URL_Q RUNNER_DOWNLOAD_URL=$RUNNER_DOWNLOAD_URL_Q bash -s" <<REMOTE
set -euo pipefail
RUNNER_TOKEN=$RUNNER_TOKEN_Q

sudo apt update
sudo apt install -y curl git tar
sudo mkdir -p /opt/actions-runner
sudo chown deploy:deploy /opt/actions-runner
cd /opt/actions-runner

if [[ -f .runner ]]; then
  echo "GitHub Actions runner is already configured in /opt/actions-runner"
else
  curl -fsSL -o actions-runner-linux.tar.gz "$RUNNER_DOWNLOAD_URL"
  tar xzf actions-runner-linux.tar.gz
  rm -f actions-runner-linux.tar.gz
  ./config.sh \
    --url "$REPO_URL" \
    --token "$RUNNER_TOKEN" \
    --name node-main \
    --labels homelab \
    --replace \
    --unattended
fi
unset RUNNER_TOKEN

if ! compgen -G "/etc/systemd/system/actions.runner.*.service" >/dev/null; then
  sudo ./svc.sh install deploy
fi
sudo ./svc.sh start
sudo ./svc.sh status
REMOTE

echo "GitHub Actions runner ready on node-main ($NODE_MAIN_IP)"
