#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC_HOSTNAME="$(python3 "$SCRIPT_DIR/read-deploy-setting.py" public_hostname)"

curl -fsS "https://$PUBLIC_HOSTNAME/health/ready"
