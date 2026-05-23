#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

fail() {
  echo "runner setup failed: $*" >&2
  exit 1
}

command -v gh >/dev/null 2>&1 || fail "gh is missing. Install GitHub CLI and run gh auth login."
command -v ssh >/dev/null 2>&1 || fail "ssh is missing."
command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
gh auth status >/dev/null 2>&1 || fail "gh is not authenticated. Run gh auth login."
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"

APP_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" app_name)"
RUNNER_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" runner_name)"
RUNNER_LABEL="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" runner_label)"
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
REMOTE_ARCH="$(ssh -i "$SSH_KEY" "deploy@$NODE_MAIN_IP" 'uname -m')"
RUNNER_DIR="/opt/actions-runner-${APP_NAME}"
RUNNER_LABELS="localcluster,${RUNNER_LABEL}"

case "$REMOTE_ARCH" in
  x86_64|amd64) ;;
  *) fail "this deployment supports only x86_64/amd64 node-main machines; got $REMOTE_ARCH" ;;
esac

RUNNER_CONFIGURED="$(ssh -i "$SSH_KEY" "deploy@$NODE_MAIN_IP" "[[ -f '$RUNNER_DIR/.runner' ]] && echo yes || echo no")"
RUNNER_TOKEN=""
RUNNER_DOWNLOAD_URL=""
if [[ "$RUNNER_CONFIGURED" != "yes" ]]; then
  RUNNER_TOKEN="$(gh api -X POST "repos/$REPO_NAME/actions/runners/registration-token" --jq .token)"
  RUNNER_TAG="$(gh release view --repo actions/runner --json tagName --jq .tagName)"
  RUNNER_VERSION="${RUNNER_TAG#v}"
  RUNNER_DOWNLOAD_URL="https://github.com/actions/runner/releases/download/${RUNNER_TAG}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
fi

REPO_URL_Q="$(printf '%q' "$REPO_URL")"
RUNNER_DIR_Q="$(printf '%q' "$RUNNER_DIR")"
RUNNER_NAME_Q="$(printf '%q' "$RUNNER_NAME")"
RUNNER_LABELS_Q="$(printf '%q' "$RUNNER_LABELS")"
RUNNER_DOWNLOAD_URL_Q="$(printf '%q' "$RUNNER_DOWNLOAD_URL")"
RUNNER_TOKEN_Q="$(printf '%q' "$RUNNER_TOKEN")"
RUNNER_CONFIGURED_Q="$(printf '%q' "$RUNNER_CONFIGURED")"

ssh -i "$SSH_KEY" "deploy@$NODE_MAIN_IP" \
  "REPO_URL=$REPO_URL_Q RUNNER_DIR=$RUNNER_DIR_Q RUNNER_NAME=$RUNNER_NAME_Q RUNNER_LABELS=$RUNNER_LABELS_Q RUNNER_DOWNLOAD_URL=$RUNNER_DOWNLOAD_URL_Q RUNNER_CONFIGURED=$RUNNER_CONFIGURED_Q bash -s" <<REMOTE
set -euo pipefail
RUNNER_TOKEN=$RUNNER_TOKEN_Q

sudo apt update
sudo apt install -y curl git tar
sudo mkdir -p "$RUNNER_DIR"
sudo chown deploy:deploy "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [[ "$RUNNER_CONFIGURED" == "yes" && -f .runner ]]; then
  CONFIGURED_RUNNER_NAME="\$(python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

try:
    payload = json.loads(Path(".runner").read_text(encoding="utf-8"))
except Exception:
    print("")
else:
    print(payload.get("agentName", ""))
PY
)"
  if [[ "\$CONFIGURED_RUNNER_NAME" != "$RUNNER_NAME" ]]; then
    echo "runner in $RUNNER_DIR is named '\$CONFIGURED_RUNNER_NAME', expected '$RUNNER_NAME'; remove or reconfigure it manually" >&2
    exit 1
  fi
  if ! grep -Fq "$REPO_URL" .runner; then
    echo "runner in $RUNNER_DIR is configured for another repository; remove or reconfigure it manually" >&2
    exit 1
  fi
  echo "GitHub Actions runner is already configured in $RUNNER_DIR; reusing existing registration"
else
  [[ -n "$RUNNER_TOKEN" ]] || {
    echo "missing runner registration token for first-time configuration" >&2
    exit 1
  }
  curl -fsSL -o actions-runner-linux.tar.gz "$RUNNER_DOWNLOAD_URL"
  tar xzf actions-runner-linux.tar.gz
  rm -f actions-runner-linux.tar.gz
  ./config.sh \
    --url "$REPO_URL" \
    --token "$RUNNER_TOKEN" \
    --name "$RUNNER_NAME" \
    --labels "$RUNNER_LABELS" \
    --replace \
    --unattended
fi
unset RUNNER_TOKEN

if ! compgen -G "/etc/systemd/system/actions.runner.*.${RUNNER_NAME}.service" >/dev/null; then
  echo "Installing GitHub Actions runner systemd service"
  sudo ./svc.sh install deploy
else
  echo "GitHub Actions runner systemd service already installed for $RUNNER_NAME"
fi
sudo ./svc.sh start
sudo ./svc.sh status
REMOTE

RUNNERS_JSON="$(gh api "repos/$REPO_NAME/actions/runners?per_page=100")"
RUNNER_ID="$(RUNNERS_JSON="$RUNNERS_JSON" python3 - "$RUNNER_NAME" <<'PY'
from __future__ import annotations

import json
import os
import sys

runner_name = sys.argv[1]
payload = json.loads(os.environ["RUNNERS_JSON"])
for runner in payload.get("runners", []):
    if isinstance(runner, dict) and runner.get("name") == runner_name:
        print(runner.get("id", ""))
        raise SystemExit(0)
raise SystemExit(f"runner not found in GitHub after setup: {runner_name}")
PY
)"

python3 - "$RUNNER_LABEL" <<'PY' | gh api -X PUT "repos/$REPO_NAME/actions/runners/$RUNNER_ID/labels" --input - >/dev/null
from __future__ import annotations

import json
import sys

runner_label = sys.argv[1]
print(json.dumps({"labels": ["localcluster", runner_label]}))
PY

bash "$SCRIPT_DIR/check-github-runner.sh"

echo "GitHub Actions runner ready on node-main ($NODE_MAIN_IP): $RUNNER_NAME [$RUNNER_LABELS]"
