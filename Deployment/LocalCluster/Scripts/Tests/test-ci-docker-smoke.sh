#!/usr/bin/env bash
# Resource lifecycle test for ci-docker-smoke.sh with Docker, curl and the
# .NET/Playwright tools stubbed. It proves owned resources are removed on
# success and failure, storage stays on tmpfs, and foreign objects survive.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/../ci-docker-smoke.sh"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$TMP_ROOT/bin" "$TMP_ROOT/state"
export SMOKE_STATE="$TMP_ROOT/state"
export SMOKE_CALLS="$TMP_ROOT/calls.jsonl"
export PATH="$TMP_ROOT/bin:$PATH"
export APP_IMAGE=example/app APP_VERSION=test APP_NAME=sample GITHUB_REPOSITORY=example/repo
cat > "$TMP_ROOT/bin/docker" <<'PY'
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
args = sys.argv[1:]
root = Path(os.environ["SMOKE_STATE"])
with open(os.environ["SMOKE_CALLS"], "a") as stream:
    stream.write(json.dumps(args) + "\n")
def state(name):
    return root / name
def labels():
    return dict(args[i + 1].split("=", 1) for i, value in enumerate(args) if value == "--label")
if args[:2] == ["network", "create"] or args[0] == "run":
    name = args[-1] if args[0] == "network" else args[args.index("--name") + 1]
    if state(name).exists():
        raise SystemExit(125)
    if "redis" in name and os.environ.get("FAIL_REDIS") == "1":
        raise SystemExit(17)
    state(name).write_text(json.dumps(labels()))
elif args[0] == "inspect" or args[:2] == ["network", "inspect"]:
    name = args[-1]
    if not state(name).exists():
        raise SystemExit(1)
    item = json.loads(state(name).read_text())
    print(" ".join(item.get("localcluster.ci." + key, "") for key in ("repository", "owner", "run_id", "run_attempt")))
elif args[0] == "rm" or args[:2] == ["network", "rm"]:
    state(args[-1]).unlink()
elif args[0] == "port":
    print("127.0.0.1:34567")
elif args[0] == "exec":
    print("PONG" if "redis-cli" in args else "accepting connections")
elif args[0] != "logs":
    raise SystemExit("unexpected fake Docker command")
PY
cat > "$TMP_ROOT/bin/curl" <<'SH'
#!/usr/bin/env bash
url="${*: -1}"
case "$url" in
  */health/ready) printf '200' ;;
  */api/books)
    if [[ "${FAIL_API:-0}" == "1" ]]; then
      printf 'HTTP/1.1 302 Found\r\nLocation: /Account/Login\r\n\r\n'
    else
      printf 'HTTP/1.1 401 Unauthorized\r\nCache-Control: no-store\r\n\r\n'
    fi
    ;;
  */) printf '<!DOCTYPE html><script src="_framework/blazor.web.js"></script>' ;;
  *) exit 22 ;;
esac
SH
for name in sleep pwsh dotnet; do
  cat > "$TMP_ROOT/bin/$name" <<'SH'
#!/usr/bin/env bash
if [[ "$(basename "$0")" == dotnet ]]; then
  [[ "$*" == *"RenderModeE2ETests"*"PreHydrationControlsE2ETests"* ]] || exit 3
  [[ "${E2E_CLEANUP_CONNECTION_STRING:-}" == *"Host=127.0.0.1;Port=34567;"* ]] || exit 4
  exit "${FAIL_BROWSER:-0}"
fi
exit 0
SH
done
chmod +x "$TMP_ROOT/bin/"*
run_case() {
  local expected="$1" status=0
  GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT=2 bash "$SCRIPT" > "$TMP_ROOT/output" 2>&1 || status=$?
  [[ "$status" == "$expected" ]] || { cat "$TMP_ROOT/output" >&2; echo "expected $expected, got $status" >&2; exit 1; }
  [[ -z "$(find "$SMOKE_STATE" -type f -print)" ]] || { echo "owned resources leaked" >&2; exit 1; }
}
run_case 0
FAIL_REDIS=1 run_case 17
FAIL_API=1 run_case 1
FAIL_BROWSER=19 run_case 19
env -u GITHUB_RUN_ID -u GITHUB_RUN_ATTEMPT bash "$SCRIPT" > "$TMP_ROOT/local-one"
env -u GITHUB_RUN_ID -u GITHUB_RUN_ATTEMPT bash "$SCRIPT" > "$TMP_ROOT/local-two"
python3 - <<'PY'
import json
import os
from pathlib import Path
calls = [json.loads(line) for line in Path(os.environ["SMOKE_CALLS"]).read_text().splitlines()]
networks = [args[-1] for args in calls if args[:2] == ["network", "create"] and "local-" in args[-1]]
assert len(networks) == 2 and len(set(networks)) == 2
assert all(name.startswith("sample-ci-") for name in networks)
for args in calls:
    if args[0] == "run":
        name = args[args.index("--name") + 1]
        assert name.startswith("sample-ci-"), name
        if "postgres" in name:
            assert "/var/lib/postgresql:rw,size=1073741824" in args
            assert "127.0.0.1::5432" in args, "postgres must publish only on loopback"
        if "redis" in name:
            assert "/data:rw,size=67108864" in args
            assert "--appendonly" in args
        if "web" in name:
            assert "RateLimiting__Api__PermitLimit=1000" in args
            assert "LocalAccounts__Enabled=false" in args
        else:
            assert not any(value.startswith("RateLimiting__") for value in args)
        assert "localcluster.ci.repository=example/repo" in args
        assert "localcluster.ci.purpose=smoke" in args
        assert any(value.startswith("localcluster.ci.session=") for value in args)
    assert "prune" not in args and "volume" not in args
PY
# A foreign object with a colliding name must survive failed creation/cleanup.
printf '{"localcluster.ci.repository":"other/repo"}' > "$SMOKE_STATE/sample-ci-web-123-2"
status=0
GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT=2 bash "$SCRIPT" > "$TMP_ROOT/collision" 2>&1 || status=$?
[[ "$status" == 125 && -f "$SMOKE_STATE/sample-ci-web-123-2" ]]
[[ "$(find "$SMOKE_STATE" -type f | wc -l)" == 1 ]]
echo "smoke success/failure, HTTP checks, bounded storage, local uniqueness, and foreign sentinel fixtures passed"
