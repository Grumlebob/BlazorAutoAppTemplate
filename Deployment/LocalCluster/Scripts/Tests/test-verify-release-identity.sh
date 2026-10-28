#!/usr/bin/env bash
# Fixture test for verify-release-identity.sh with Ansible stubbed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/release-identity-test.XXXXXX")"
trap 'rm -rf "$TEST_ROOT"' EXIT
mkdir -p "$TEST_ROOT/bin"

cat > "$TEST_ROOT/bin/ansible" <<'PY'
#!/usr/bin/env python3
import json
import os
import pathlib
import sys

args = sys.argv[1:]
assert args[0] == "app_servers", args
command = args[args.index("-a") + 1]
assert "{{" not in command, "Go templates must not reach Ansible templating"
tree = pathlib.Path(args[args.index("--tree") + 1])
digest = os.environ["EXPECTED_DIGEST"]
wrong_host = os.environ.get("FAKE_WRONG_HOST")
failed_host = os.environ.get("FAKE_FAILED_HOST")
wrong_profile_host = os.environ.get("FAKE_WRONG_PROFILE_HOST")
wrong_acceptance_host = os.environ.get("FAKE_WRONG_ACCEPTANCE_HOST")
wrong_revision_host = os.environ.get("FAKE_WRONG_REVISION_HOST")
source_repo = os.environ["EXPECTED_SOURCE_REPO"]
frontend = os.environ["EXPECTED_FRONTEND_PROFILE"]
acceptance = os.environ["EXPECTED_ACCEPTANCE_PROFILE"]
source_sha = os.environ["EXPECTED_SOURCE_SHA"]
run_id = os.environ["EXPECTED_CI_RUN_ID"]
run_attempt = os.environ["EXPECTED_CI_RUN_ATTEMPT"]
legacy = os.environ.get("FAKE_LEGACY_IMAGE") == "1"
for host in ("node-app1", "node-app2"):
    selected = "sha256:" + "f" * 64 if host == wrong_host else digest
    selected_profile = "React" if host == wrong_profile_host else frontend
    selected_acceptance = "ReactPublicV1" if host == wrong_acceptance_host else acceptance
    selected_revision = "2" * 40 if host == wrong_revision_host else source_sha
    labels = {
        "org.opencontainers.image.source": source_repo,
        "localcluster.ci.repository": source_repo.removeprefix("https://github.com/"),
        "localcluster.ci.run_id": run_id,
        "localcluster.ci.run_attempt": run_attempt,
    }
    if not legacy:
        labels.update({
            "org.opencontainers.image.revision": selected_revision,
            "com.grumplates.frontend-profile": selected_profile,
            "com.grumplates.acceptance-profile": selected_acceptance,
        })
    result = {
        "rc": 1 if host == failed_host else 0,
        "stdout": "{}\tsha256:{}\t{}\t{}".format(
            host,
            "a" * 64,
            json.dumps(["example.io/owner/app@" + selected]),
            json.dumps(labels),
        ),
    }
    (tree / host).write_text(json.dumps(result), encoding="utf-8")
sys.exit(2 if failed_host else 0)
PY
chmod +x "$TEST_ROOT/bin/ansible"

export PATH="$TEST_ROOT/bin:$PATH"
export DEPLOY_ROOT=/opt/app
export RUNNER_TEMP="$TEST_ROOT"
export EXPECTED_DIGEST="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
export EXPECTED_FRONTEND_PROFILE=BlazorAuto
export EXPECTED_ACCEPTANCE_PROFILE=BlazorAutoV1
export EXPECTED_SOURCE_SHA="1111111111111111111111111111111111111111"
export EXPECTED_MANIFEST_SCHEMA=2
export EXPECTED_CI_RUN_ID=123
export EXPECTED_CI_RUN_ATTEMPT=1
export EXPECTED_SOURCE_REPO=https://github.com/example/repo
script="$REPO_ROOT/Deployment/LocalCluster/Scripts/verify-release-identity.sh"

run_identity() {
  bash "$script" example.io/owner/app "$EXPECTED_DIGEST" "$EXPECTED_FRONTEND_PROFILE" "$EXPECTED_ACCEPTANCE_PROFILE" "$EXPECTED_SOURCE_SHA" "$EXPECTED_MANIFEST_SCHEMA" "$EXPECTED_CI_RUN_ID" "$EXPECTED_CI_RUN_ATTEMPT" "$EXPECTED_SOURCE_REPO"
}
run_identity > "$TEST_ROOT/ok.txt"
grep -Fq "node-app1: example.io/owner/app@${EXPECTED_DIGEST} BlazorAuto/BlazorAutoV1" "$TEST_ROOT/ok.txt"
grep -Fq "node-app2: example.io/owner/app@${EXPECTED_DIGEST} BlazorAuto/BlazorAutoV1" "$TEST_ROOT/ok.txt"

if FAKE_WRONG_HOST=node-app2 run_identity >/dev/null 2>&1; then
  echo "a node running another digest was accepted" >&2
  exit 1
fi
if FAKE_FAILED_HOST=node-app1 run_identity >/dev/null 2>&1; then
  echo "a failed node inspection was accepted" >&2
  exit 1
fi
if FAKE_WRONG_PROFILE_HOST=node-app2 run_identity >/dev/null 2>&1; then
  echo "a node with another baked frontend profile was accepted" >&2
  exit 1
fi
if FAKE_WRONG_ACCEPTANCE_HOST=node-app2 run_identity >/dev/null 2>&1; then
  echo "a node with another baked acceptance profile was accepted" >&2
  exit 1
fi
if FAKE_WRONG_REVISION_HOST=node-app2 run_identity >/dev/null 2>&1; then
  echo "a node with another baked source SHA was accepted" >&2
  exit 1
fi
EXPECTED_MANIFEST_SCHEMA=1 FAKE_LEGACY_IMAGE=1 run_identity > "$TEST_ROOT/legacy.txt"
grep -Fq "BlazorAuto/BlazorAutoV1" "$TEST_ROOT/legacy.txt"
status=0
EXPECTED_MANIFEST_SCHEMA=1 EXPECTED_FRONTEND_PROFILE=React EXPECTED_ACCEPTANCE_PROFILE=ReactPublicV1 run_identity >/dev/null 2>&1 || status=$?
[[ "$status" == 1 ]] || { echo "legacy schema v1 accepted React or returned $status" >&2; exit 1; }
status=0
bash "$script" example.io/owner/app not-a-digest "$EXPECTED_FRONTEND_PROFILE" "$EXPECTED_ACCEPTANCE_PROFILE" "$EXPECTED_SOURCE_SHA" "$EXPECTED_MANIFEST_SCHEMA" "$EXPECTED_CI_RUN_ID" "$EXPECTED_CI_RUN_ATTEMPT" "$EXPECTED_SOURCE_REPO" >/dev/null 2>&1 || status=$?
[[ "$status" == 1 ]] || { echo "malformed digest returned $status" >&2; exit 1; }
status=0
bash "$script" only-one-argument >/dev/null 2>&1 || status=$?
[[ "$status" == 2 ]] || { echo "usage error returned $status" >&2; exit 1; }
[[ -z "$(find "$TEST_ROOT" -maxdepth 1 -name 'release-identities.*' -print -quit)" ]] || {
  echo "identity temp directory leaked" >&2
  exit 1
}

echo "per-host release identity fixtures passed"
