#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "Hetzner API token check failed: $*" >&2
  exit 1
}

[[ -n "${HCLOUD_TOKEN:-}" ]] || fail "HCLOUD_TOKEN is not set in this shell."

command -v curl >/dev/null 2>&1 || fail "curl is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
command -v jq >/dev/null 2>&1 || fail "jq is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."

locations_json="$(curl -fsS -H "Authorization: Bearer ${HCLOUD_TOKEN}" https://api.hetzner.cloud/v1/locations)" \
  || fail "Hetzner API request failed. Check that the token was copied correctly."

location_name="$(jq -r '.locations[] | select(.name == "fsn1") | .name' <<< "$locations_json")" \
  || fail "Hetzner API returned unexpected JSON."

[[ "$location_name" == "fsn1" ]] || fail "Hetzner API token works, but location fsn1 was not found."

echo "Hetzner API token check ok"
echo "  HCLOUD_TOKEN is set in this shell"
echo "  Hetzner API is reachable"
echo "  location fsn1 is available"
