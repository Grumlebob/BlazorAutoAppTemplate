#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TFVARS="$REPO_ROOT/Deployment/Cloud/infra/opentofu/terraform.tfvars"
EXAMPLE="$REPO_ROOT/Deployment/Cloud/infra/opentofu/terraform.tfvars.example"

fail() {
  echo "prepare OpenTofu tfvars failed: $*" >&2
  exit 1
}

command -v curl >/dev/null 2>&1 || fail "curl is missing."
command -v python3 >/dev/null 2>&1 || fail "python3 is missing."
[[ -f "$EXAMPLE" ]] || fail "missing example file: Deployment/Cloud/infra/opentofu/terraform.tfvars.example"

if [[ ! -f "$TFVARS" ]]; then
  cp "$EXAMPLE" "$TFVARS"
fi

CURRENT_PUBLIC_IPV4="${CURRENT_PUBLIC_IPV4:-$(curl -fsS4 https://checkip.amazonaws.com | tr -d '[:space:]')}"
[[ -n "$CURRENT_PUBLIC_IPV4" ]] || fail "could not detect current public IPv4"

python3 - "$TFVARS" "$CURRENT_PUBLIC_IPV4" <<'PY'
from __future__ import annotations

import ipaddress
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
current_ip = sys.argv[2].strip()

try:
    ipaddress.IPv4Address(current_ip)
except ValueError as exc:
    raise SystemExit(f"detected public IP is not IPv4: {exc}")

content = path.read_text(encoding="utf-8")
replacement = f'admin_ssh_cidrs = ["{current_ip}/32"]'
updated, count = re.subn(r'^admin_ssh_cidrs\s*=\s*\[[^\n]*\]', replacement, content, flags=re.MULTILINE)
if count != 1:
    raise SystemExit("expected exactly one admin_ssh_cidrs assignment in terraform.tfvars")

path.write_text(updated, encoding="utf-8")
PY

chmod 600 "$TFVARS"
echo "prepared Deployment/Cloud/infra/opentofu/terraform.tfvars"
echo "admin_ssh_cidrs = [\"${CURRENT_PUBLIC_IPV4}/32\"]"
