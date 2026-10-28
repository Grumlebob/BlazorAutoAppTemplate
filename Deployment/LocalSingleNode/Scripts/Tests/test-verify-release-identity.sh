#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/single-node-release-identity-test.XXXXXX")"
trap 'rm -rf "$TEST_ROOT"' EXIT
mkdir -p "$TEST_ROOT/bin"

cat > "$TEST_ROOT/bin/docker" <<'PY'
#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
if args[:1] == ["compose"]:
    print("web-container")
elif args[:1] == ["inspect"]:
    print(json.dumps([{"State": {"Status": "running"}, "Image": "sha256:" + "a" * 64}]))
elif args[:2] == ["image", "inspect"]:
    digest = "sha256:" + ("f" if os.environ.get("FAKE_WRONG_DIGEST") else "b") * 64
    labels = {
        "org.opencontainers.image.source": os.environ["EXPECTED_SOURCE_REPO"],
        "localcluster.ci.repository": "example/repo",
        "localcluster.ci.run_id": os.environ["EXPECTED_CI_RUN_ID"],
        "localcluster.ci.run_attempt": os.environ["EXPECTED_CI_RUN_ATTEMPT"],
    }
    if os.environ.get("FAKE_LEGACY_IMAGE") != "1":
        labels.update({
            "org.opencontainers.image.revision": os.environ["EXPECTED_SOURCE_SHA"],
            "com.grumplates.frontend-profile": os.environ["EXPECTED_FRONTEND_PROFILE"],
            "com.grumplates.acceptance-profile": os.environ["EXPECTED_ACCEPTANCE_PROFILE"],
        })
    if os.environ.get("FAKE_WRONG_PROFILE") == "1":
        labels["com.grumplates.frontend-profile"] = "React"
    if os.environ.get("FAKE_WRONG_ACCEPTANCE") == "1":
        labels["com.grumplates.acceptance-profile"] = "ReactPublicV1"
    if os.environ.get("FAKE_WRONG_REVISION") == "1":
        labels["org.opencontainers.image.revision"] = "2" * 40
    print(json.dumps([{"RepoDigests": ["example.io/owner/app@" + digest], "Config": {"Labels": labels}}]))
else:
    raise SystemExit("unexpected docker invocation: " + repr(args))
PY
chmod +x "$TEST_ROOT/bin/docker"

export PATH="$TEST_ROOT/bin:$PATH"
export RUNNER_TEMP="$TEST_ROOT"
export EXPECTED_DIGEST="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
export EXPECTED_FRONTEND_PROFILE=BlazorAuto
export EXPECTED_ACCEPTANCE_PROFILE=BlazorAutoV1
export EXPECTED_SOURCE_SHA="1111111111111111111111111111111111111111"
export EXPECTED_CI_RUN_ID=123
export EXPECTED_CI_RUN_ATTEMPT=1
export EXPECTED_SOURCE_REPO=https://github.com/example/repo
script="$REPO_ROOT/Deployment/LocalSingleNode/Scripts/verify-release-identity.sh"

run_identity() {
  bash "$script" example.io/owner/app "$EXPECTED_DIGEST" "$EXPECTED_FRONTEND_PROFILE" "$EXPECTED_ACCEPTANCE_PROFILE" "$EXPECTED_SOURCE_SHA" "${EXPECTED_MANIFEST_SCHEMA:-2}" "$EXPECTED_CI_RUN_ID" "$EXPECTED_CI_RUN_ATTEMPT" "$EXPECTED_SOURCE_REPO"
}

run_identity > "$TEST_ROOT/verified.txt"
grep -Fq "BlazorAuto/BlazorAutoV1" "$TEST_ROOT/verified.txt"

if FAKE_WRONG_DIGEST=1 run_identity >/dev/null 2>&1; then
  echo "a running image with another digest was accepted" >&2
  exit 1
fi
if FAKE_WRONG_PROFILE=1 run_identity >/dev/null 2>&1; then
  echo "an image with another baked frontend profile was accepted" >&2
  exit 1
fi
if FAKE_WRONG_ACCEPTANCE=1 run_identity >/dev/null 2>&1; then
  echo "an image with another baked acceptance profile was accepted" >&2
  exit 1
fi
if FAKE_WRONG_REVISION=1 run_identity >/dev/null 2>&1; then
  echo "an image with another baked source SHA was accepted" >&2
  exit 1
fi

EXPECTED_MANIFEST_SCHEMA=1 FAKE_LEGACY_IMAGE=1 run_identity > "$TEST_ROOT/legacy.txt"
grep -Fq "BlazorAuto/BlazorAutoV1" "$TEST_ROOT/legacy.txt"
status=0
EXPECTED_MANIFEST_SCHEMA=1 EXPECTED_FRONTEND_PROFILE=React EXPECTED_ACCEPTANCE_PROFILE=ReactPublicV1 run_identity >/dev/null 2>&1 || status=$?
[[ "$status" == 1 ]] || { echo "legacy schema v1 accepted React or returned $status" >&2; exit 1; }

status=0
bash "$script" example.io/owner/app bad-digest "$EXPECTED_FRONTEND_PROFILE" "$EXPECTED_ACCEPTANCE_PROFILE" "$EXPECTED_SOURCE_SHA" 2 "$EXPECTED_CI_RUN_ID" "$EXPECTED_CI_RUN_ATTEMPT" "$EXPECTED_SOURCE_REPO" >/dev/null 2>&1 || status=$?
[[ "$status" == 1 ]] || { echo "malformed digest returned $status" >&2; exit 1; }
status=0
bash "$script" only-one-argument >/dev/null 2>&1 || status=$?
[[ "$status" == 2 ]] || { echo "usage error returned $status" >&2; exit 1; }
[[ -z "$(find "$TEST_ROOT" -maxdepth 1 -name 'release-identities.*' -print -quit)" ]] || {
  echo "identity temp directory leaked" >&2
  exit 1
}

echo "single-node release identity fixtures passed"
