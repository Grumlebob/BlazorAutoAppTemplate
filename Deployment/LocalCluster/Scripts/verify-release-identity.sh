#!/usr/bin/env bash
# Verify that every app server runs the exact released image digest.
#
# usage: verify-release-identity.sh [<app-image> <sha256-digest>]
#   Defaults: APP_IMAGE (or the release setting) and RELEASE_IMAGE_DIGEST.
# Exit codes: 0 every app node runs the digest, 1 mismatch or inspection
# failure, 2 usage error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

if [[ $# -eq 2 ]]; then
  APP_IMAGE="$1"
  EXPECTED_DIGEST="$2"
elif [[ $# -eq 0 ]]; then
  APP_IMAGE="${APP_IMAGE:-$(bash "$REPO_ROOT/Deployment/Common/Scripts/read-release-setting.sh" app_image)}"
  EXPECTED_DIGEST="${RELEASE_IMAGE_DIGEST:-}"
else
  echo "usage: verify-release-identity.sh [<app-image> <sha256-digest>]" >&2
  exit 2
fi
DEPLOY_ROOT="${DEPLOY_ROOT:-$(bash "$SCRIPT_DIR/read-deploy-setting.sh" deploy_root)}"

fail() { echo "release identity verification failed: $*" >&2; exit 1; }
shell_quote() { printf "'%s'" "${1//\'/\'\\\'\'}"; }
[[ "$APP_IMAGE" =~ ^[a-z0-9][a-z0-9_.-]*(/[a-z0-9][a-z0-9_.-]*)+$ ]] || fail "APP_IMAGE is not a valid image path: $APP_IMAGE"
[[ "$EXPECTED_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "expected digest must be a registry sha256 digest"
[[ -f "$INVENTORY" ]] || fail "missing inventory: $INVENTORY"

identity_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/release-identities.XXXXXX")"
chmod 0700 "$identity_root"
trap 'rm -rf "$identity_root"' EXIT

# Build Docker Go templates from brace tokens so Ansible does not interpret
# `{{...}}` before the remote shell runs. The running web container's image
# must carry the expected registry digest.
remote_command="set -eu; cd $(shell_quote "$DEPLOY_ROOT"); format_image=\$(printf '%s%s%s%s%s' '{' '{' '.Image' '}' '}'); format_repo_digests=\$(printf '%s%s%s%s%s' '{' '{' 'json .RepoDigests' '}' '}'); container=\$(docker compose ps -q web | head -n 1); test -n \"\$container\"; image_id=\$(docker inspect --format \"\$format_image\" \"\$container\"); repo_digests=\$(docker image inspect --format \"\$format_repo_digests\" \"\$image_id\"); printf '%s\\t%s\\t%s\\n' \"\$(hostname)\" \"\$image_id\" \"\$repo_digests\""

if ! ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "$remote_command" --tree "$identity_root" >/dev/null; then
  fail "could not inspect every app server"
fi

python3 - "$identity_root" "$APP_IMAGE" "$EXPECTED_DIGEST" <<'PY'
import json
import os
import sys

root, app_image, expected_digest = sys.argv[1:]
expected = f"{app_image}@{expected_digest}"
files = sorted(os.listdir(root))
if not files:
    raise SystemExit("release identity verification failed: no per-host identity records were written")
for name in files:
    with open(os.path.join(root, name), "r", encoding="utf-8") as source:
        result = json.load(source)
    if int(result.get("rc", 1)) != 0:
        raise SystemExit(f"release identity verification failed: inspection failed on {name}")
    fields = (result.get("stdout") or "").strip().split("\t", 2)
    if len(fields) != 3:
        raise SystemExit(f"release identity verification failed: malformed output from {name}")
    host, image_id, repo_digests_json = fields
    try:
        repo_digests = json.loads(repo_digests_json)
    except ValueError:
        raise SystemExit(f"release identity verification failed: malformed RepoDigests on {host}")
    if not isinstance(repo_digests, list) or expected not in repo_digests:
        raise SystemExit(f"release identity verification failed: {host} runs {image_id}, not {expected}")
    print(f"{host}: {expected}")
PY

echo "release identity verified on every app server: ${APP_IMAGE}@${EXPECTED_DIGEST}"
