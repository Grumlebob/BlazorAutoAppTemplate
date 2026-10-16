#!/usr/bin/env bash
# Verify that every app server runs the exact released digest and image identity.
#
# usage: verify-release-identity.sh <app-image> <sha256-digest> <frontend-profile> <acceptance-profile> <source-sha> <manifest-schema> <ci-run-id> <ci-run-attempt> <source-repo-url>
# Exit codes: 0 every app node runs the digest, 1 mismatch or inspection
# failure, 2 usage error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

if [[ $# -ne 9 ]]; then
  echo "usage: verify-release-identity.sh <app-image> <sha256-digest> <frontend-profile> <acceptance-profile> <source-sha> <manifest-schema> <ci-run-id> <ci-run-attempt> <source-repo-url>" >&2
  exit 2
fi
APP_IMAGE="$1"
EXPECTED_DIGEST="$2"
EXPECTED_FRONTEND_PROFILE="$3"
EXPECTED_ACCEPTANCE_PROFILE="$4"
EXPECTED_SOURCE_SHA="$5"
EXPECTED_MANIFEST_SCHEMA="$6"
EXPECTED_CI_RUN_ID="$7"
EXPECTED_CI_RUN_ATTEMPT="$8"
EXPECTED_SOURCE_REPO="$9"
DEPLOY_ROOT="${DEPLOY_ROOT:-$(bash "$SCRIPT_DIR/read-deploy-setting.sh" deploy_root)}"

fail() { echo "release identity verification failed: $*" >&2; exit 1; }
shell_quote() { printf "'%s'" "${1//\'/\'\\\'\'}"; }
[[ "$APP_IMAGE" =~ ^[a-z0-9][a-z0-9_.-]*(/[a-z0-9][a-z0-9_.-]*)+$ ]] || fail "APP_IMAGE is not a valid image path: $APP_IMAGE"
[[ "$EXPECTED_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "expected digest must be a registry sha256 digest"
[[ "$EXPECTED_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "expected source SHA must be a full lowercase commit SHA"
[[ "$EXPECTED_CI_RUN_ID" =~ ^[0-9]+$ && "$EXPECTED_CI_RUN_ATTEMPT" =~ ^[1-9][0-9]*$ ]] || fail "expected CI run metadata is malformed"
[[ "$EXPECTED_SOURCE_REPO" =~ ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail "expected source repository URL is malformed"
case "${EXPECTED_FRONTEND_PROFILE}:${EXPECTED_ACCEPTANCE_PROFILE}" in
  BlazorAuto:BlazorAutoV1|React:ReactPublicV1) ;;
  *) fail "frontend and acceptance profiles do not match" ;;
esac
[[ "$EXPECTED_MANIFEST_SCHEMA" =~ ^[12]$ ]] || fail "manifest schema must be 1 or 2"
if [[ "$EXPECTED_MANIFEST_SCHEMA" == 1 && "$EXPECTED_FRONTEND_PROFILE:$EXPECTED_ACCEPTANCE_PROFILE" != "BlazorAuto:BlazorAutoV1" ]]; then
  fail "legacy manifest schema v1 is supported only for BlazorAuto"
fi
[[ -f "$INVENTORY" ]] || fail "missing inventory: $INVENTORY"

identity_root="$(mktemp -d "${RUNNER_TEMP:-/tmp}/release-identities.XXXXXX")"
chmod 0700 "$identity_root"
trap 'rm -rf "$identity_root"' EXIT

# Build Docker Go templates from brace tokens so Ansible does not interpret
# `{{...}}` before the remote shell runs. The image digest and baked release
# labels must match the verified artifact on every app server.
remote_command="set -eu; cd $(shell_quote "$DEPLOY_ROOT"); format_image=\$(printf '%s%s%s%s%s' '{' '{' '.Image' '}' '}'); format_repo_digests=\$(printf '%s%s%s%s%s' '{' '{' 'json .RepoDigests' '}' '}'); format_labels=\$(printf '%s%s%s%s%s' '{' '{' 'json .Config.Labels' '}' '}'); container=\$(docker compose --env-file .compose.env ps -q web | head -n 1); test -n \"\$container\"; image_id=\$(docker inspect --format \"\$format_image\" \"\$container\"); repo_digests=\$(docker image inspect --format \"\$format_repo_digests\" \"\$image_id\"); image_labels=\$(docker image inspect --format \"\$format_labels\" \"\$image_id\"); printf '%s\\t%s\\t%s\\t%s\\n' \"\$(hostname)\" \"\$image_id\" \"\$repo_digests\" \"\$image_labels\""

if ! ansible app_servers -i "$INVENTORY" -m ansible.builtin.shell -a "$remote_command" --tree "$identity_root" >/dev/null; then
  fail "could not inspect every app server"
fi

python3 - "$identity_root" "$APP_IMAGE" "$EXPECTED_DIGEST" "$EXPECTED_FRONTEND_PROFILE" "$EXPECTED_ACCEPTANCE_PROFILE" "$EXPECTED_SOURCE_SHA" "$EXPECTED_MANIFEST_SCHEMA" "$EXPECTED_CI_RUN_ID" "$EXPECTED_CI_RUN_ATTEMPT" "$EXPECTED_SOURCE_REPO" <<'PY'
import json
import os
import sys

root, app_image, expected_digest, frontend, acceptance, source_sha, schema, ci_run_id, ci_attempt, source_repo = sys.argv[1:]
expected = f"{app_image}@{expected_digest}"
expected_repository = source_repo.removeprefix("https://github.com/")
if frontend not in ("BlazorAuto", "React") or acceptance != {"BlazorAuto": "BlazorAutoV1", "React": "ReactPublicV1"}.get(frontend):
    raise SystemExit("release identity verification failed: frontend/acceptance pair is invalid")
if schema == "1" and (frontend, acceptance) != ("BlazorAuto", "BlazorAutoV1"):
    raise SystemExit("release identity verification failed: schema v1 is Blazor-only")
files = sorted(os.listdir(root))
if not files:
    raise SystemExit("release identity verification failed: no per-host identity records were written")
for name in files:
    with open(os.path.join(root, name), "r", encoding="utf-8") as source:
        result = json.load(source)
    if int(result.get("rc", 1)) != 0:
        raise SystemExit(f"release identity verification failed: inspection failed on {name}")
    fields = (result.get("stdout") or "").strip().split("\t", 3)
    if len(fields) != 4:
        raise SystemExit(f"release identity verification failed: malformed output from {name}")
    host, image_id, repo_digests_json, image_labels_json = fields
    try:
        repo_digests = json.loads(repo_digests_json)
        image_labels = json.loads(image_labels_json)
    except ValueError:
        raise SystemExit(f"release identity verification failed: malformed image metadata on {host}")
    if not isinstance(repo_digests, list) or expected not in repo_digests:
        raise SystemExit(f"release identity verification failed: {host} runs {image_id}, not {expected}")
    if not isinstance(image_labels, dict):
        raise SystemExit(f"release identity verification failed: image labels are missing on {host}")
    common_labels = {
        "org.opencontainers.image.source": source_repo,
        "localcluster.ci.repository": expected_repository,
        "localcluster.ci.run_id": ci_run_id,
        "localcluster.ci.run_attempt": ci_attempt,
    }
    for key, value in common_labels.items():
        if image_labels.get(key) != value:
            raise SystemExit(f"release identity verification failed: {host} label {key!r} differs")
    profile_labels = {
        "org.opencontainers.image.revision": source_sha,
        "com.blazorautoapp.frontend-profile": frontend,
        "com.blazorautoapp.acceptance-profile": acceptance,
    }
    for key, value in profile_labels.items():
        if schema == "2" and image_labels.get(key) != value:
            raise SystemExit(f"release identity verification failed: {host} label {key!r} differs")
        if schema == "1" and key in image_labels and image_labels[key] != value:
            raise SystemExit(f"release identity verification failed: {host} legacy image conflicts at {key!r}")
    print(f"{host}: {expected} {frontend}/{acceptance}")
PY

echo "release identity verified on every app server: ${APP_IMAGE}@${EXPECTED_DIGEST} ${EXPECTED_FRONTEND_PROFILE}/${EXPECTED_ACCEPTANCE_PROFILE}"
