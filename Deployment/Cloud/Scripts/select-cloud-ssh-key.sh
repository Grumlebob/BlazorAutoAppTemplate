#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DESTINATION="${CLOUD_SSH_PRIVATE_KEY_PATH:?CLOUD_SSH_PRIVATE_KEY_PATH is required}"
EXPECTED_PUBLIC_KEY_FILE="${CLOUD_EXPECTED_SSH_PUBLIC_KEY_FILE:-$REPO_ROOT/Deployment/Cloud/infra/opentofu/bookscloud_deploy.pub}"

fail() {
  echo "select Cloud SSH key failed: $*" >&2
  exit 1
}

public_key_core() {
  awk '{ print $1 " " $2 }' "$1"
}

fingerprint_public_key() {
  local public_key="$1"
  printf '%s\n' "$public_key" | ssh-keygen -lf - -E sha256 | awk '{ print $2 }'
}

private_key_public_core() {
  local private_key="$1"
  ssh-keygen -y -P "" -f "$private_key" 2>/dev/null | awk '{ print $1 " " $2 }'
}

add_candidate() {
  local candidate="$1"
  [[ -n "$candidate" ]] || return 0
  [[ -f "$candidate" ]] || return 0
  [[ "$candidate" != *.pub ]] || return 0
  [[ "$candidate" != */authorized_keys ]] || return 0
  [[ "$candidate" != */config ]] || return 0
  [[ "$candidate" != */known_hosts ]] || return 0
  CANDIDATES+=("$candidate")
}

[[ -f "$EXPECTED_PUBLIC_KEY_FILE" ]] || fail "expected public key file is missing: $EXPECTED_PUBLIC_KEY_FILE"
EXPECTED_PUBLIC_KEY="$(public_key_core "$EXPECTED_PUBLIC_KEY_FILE")"
EXPECTED_FINGERPRINT="$(fingerprint_public_key "$EXPECTED_PUBLIC_KEY")"

declare -a CANDIDATES=()
add_candidate "${CLOUD_RUNNER_SSH_PRIVATE_KEY_PATH:-}"
add_candidate "$HOME/.ssh/bookscloud_deploy"
add_candidate "/home/grumbo/.ssh/bookscloud_deploy"
add_candidate "/home/deploy/.ssh/bookscloud_deploy"
add_candidate "/home/runner/.ssh/bookscloud_deploy"

for directory in "$HOME/.ssh" "/home/grumbo/.ssh" "/home/deploy/.ssh" "/home/runner/.ssh"; do
  [[ -d "$directory" ]] || continue
  while IFS= read -r -d '' candidate; do
    add_candidate "$candidate"
  done < <(find "$directory" -maxdepth 1 -type f \( -name '*books*' -o -name '*cloud*deploy*' \) -print0 2>/dev/null)
done

selected_key=""
for candidate in "${CANDIDATES[@]}"; do
  candidate_public_key="$(private_key_public_core "$candidate" || true)"
  if [[ "$candidate_public_key" == "$EXPECTED_PUBLIC_KEY" ]]; then
    selected_key="$candidate"
    break
  fi
done

install -d -m 0700 "$(dirname "$DESTINATION")"
if [[ -n "$selected_key" ]]; then
  install -m 0600 "$selected_key" "$DESTINATION"
  key_source="runner-local:${selected_key}"
elif [[ -n "${CLOUD_SSH_PRIVATE_KEY:-}" ]]; then
  printf '%s\n' "$CLOUD_SSH_PRIVATE_KEY" > "$DESTINATION"
  chmod 0600 "$DESTINATION"
  configured_public_key="$(private_key_public_core "$DESTINATION" || true)"
  if [[ "$configured_public_key" != "$EXPECTED_PUBLIC_KEY" ]]; then
    configured_fingerprint="unreadable"
    if [[ -n "$configured_public_key" ]]; then
      configured_fingerprint="$(fingerprint_public_key "$configured_public_key")"
    fi
    fail "CLOUD_SSH_PRIVATE_KEY fingerprint ${configured_fingerprint} does not match expected ${EXPECTED_FINGERPRINT}"
  fi
  key_source="github-environment:CLOUD_SSH_PRIVATE_KEY"
else
  fail "no matching runner-local key was found and CLOUD_SSH_PRIVATE_KEY is empty"
fi

selected_public_key="$(private_key_public_core "$DESTINATION")"
selected_fingerprint="$(fingerprint_public_key "$selected_public_key")"
echo "Cloud SSH key source: ${key_source}"
echo "Cloud SSH public fingerprint: ${selected_fingerprint}"
