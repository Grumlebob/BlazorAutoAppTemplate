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
for host in ("node-app1", "node-app2"):
    selected = "sha256:" + "f" * 64 if host == wrong_host else digest
    result = {
        "rc": 1 if host == failed_host else 0,
        "stdout": "{}\tsha256:{}\t[\"example.io/owner/app@{}\"]".format(host, "a" * 64, selected),
    }
    (tree / host).write_text(json.dumps(result), encoding="utf-8")
sys.exit(2 if failed_host else 0)
PY
chmod +x "$TEST_ROOT/bin/ansible"

export PATH="$TEST_ROOT/bin:$PATH"
export DEPLOY_ROOT=/opt/app
export RUNNER_TEMP="$TEST_ROOT"
export EXPECTED_DIGEST="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
script="$REPO_ROOT/Deployment/LocalCluster/Scripts/verify-release-identity.sh"

bash "$script" example.io/owner/app "$EXPECTED_DIGEST" > "$TEST_ROOT/ok.txt"
grep -Fq "node-app1: example.io/owner/app@${EXPECTED_DIGEST}" "$TEST_ROOT/ok.txt"
grep -Fq "node-app2: example.io/owner/app@${EXPECTED_DIGEST}" "$TEST_ROOT/ok.txt"

if FAKE_WRONG_HOST=node-app2 bash "$script" example.io/owner/app "$EXPECTED_DIGEST" >/dev/null 2>&1; then
  echo "a node running another digest was accepted" >&2
  exit 1
fi
if FAKE_FAILED_HOST=node-app1 bash "$script" example.io/owner/app "$EXPECTED_DIGEST" >/dev/null 2>&1; then
  echo "a failed node inspection was accepted" >&2
  exit 1
fi
status=0
bash "$script" example.io/owner/app not-a-digest >/dev/null 2>&1 || status=$?
[[ "$status" == 1 ]] || { echo "malformed digest returned $status" >&2; exit 1; }
status=0
bash "$script" only-one-argument >/dev/null 2>&1 || status=$?
[[ "$status" == 2 ]] || { echo "usage error returned $status" >&2; exit 1; }
[[ -z "$(find "$TEST_ROOT" -maxdepth 1 -name 'release-identities.*' -print -quit)" ]] || {
  echo "identity temp directory leaked" >&2
  exit 1
}

echo "per-host release identity fixtures passed"
