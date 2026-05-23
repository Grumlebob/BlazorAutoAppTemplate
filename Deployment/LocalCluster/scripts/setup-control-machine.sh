#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/support/install-ansible.sh"
python3 "$SCRIPT_DIR/lib/validate-deploy-settings.py"

APP_NAME="$(python3 "$SCRIPT_DIR/lib/read-deploy-setting.py" app_name)"
SSH_KEY="$HOME/.ssh/${APP_NAME}_deploy"
SSH_PUB="$SSH_KEY.pub"

mkdir -p "$(dirname "$SSH_KEY")"
chmod 700 "$(dirname "$SSH_KEY")"

if [[ -f "$SSH_KEY" ]]; then
  echo "deploy SSH key already exists: $SSH_KEY"
else
  ssh-keygen -t ed25519 -f "$SSH_KEY" -C "$APP_NAME deploy" -N ""
fi

if [[ ! -f "$SSH_PUB" ]]; then
  ssh-keygen -y -f "$SSH_KEY" > "$SSH_PUB"
fi

chmod 600 "$SSH_KEY"
chmod 644 "$SSH_PUB"

echo
echo "control machine setup complete"
echo "app name: $APP_NAME"
echo "deploy SSH key: $SSH_KEY"
echo "deploy SSH public key: $SSH_PUB"
