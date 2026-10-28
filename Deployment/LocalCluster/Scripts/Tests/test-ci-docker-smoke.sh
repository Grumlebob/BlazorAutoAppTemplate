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
export APP_IMAGE=example/app APP_VERSION=test APP_NAME=sample GITHUB_REPOSITORY=example/repo GITHUB_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
cat > "$TMP_ROOT/bin/docker" <<'PY'
#!/usr/bin/env python3
import json
import os
import re
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
if args[:2] == ["image", "inspect"]:
    profile = os.environ.get("FRONTEND_PROFILE", "BlazorAuto")
    acceptance = os.environ.get("FRONTEND_ACCEPTANCE_PROFILE", "BlazorAutoV1" if profile == "BlazorAuto" else "ReactPublicV1")
    if os.environ.get("FAIL_IMAGE_LABEL") == "1":
        profile = "React" if profile == "BlazorAuto" else "BlazorAuto"
    if os.environ.get("FAIL_ACCEPTANCE_LABEL") == "1":
        acceptance = "ReactPublicV1" if acceptance == "BlazorAutoV1" else "BlazorAutoV1"
    print(json.dumps({
        "com.grumplates.frontend-profile": profile,
        "com.grumplates.acceptance-profile": acceptance,
        "org.opencontainers.image.revision": os.environ["GITHUB_SHA"],
    }))
elif args[:2] == ["network", "create"] or args[0] == "run":
    name = args[-1] if args[0] == "network" else args[args.index("--name") + 1]
    if state(name).exists():
        raise SystemExit(125)
    if "redis" in name and os.environ.get("FAIL_REDIS") == "1":
        raise SystemExit(17)
    metadata = labels()
    metadata["ports"] = {}
    if "--network-alias" in args and "ci-postgres" in args:
        password = os.environ.get("POSTGRES_PASSWORD", "")
        if not re.fullmatch(r"[0-9a-f]{48}", password):
            raise SystemExit("The database fixture requires a generated password.")
        metadata["database_password"] = password
    for argument in args:
        if argument.startswith("ConnectionStrings__DefaultConnection="):
            passwords = [json.loads(item.read_text()).get("database_password") for item in root.iterdir()]
            if not any(password and f"Password={password};" in argument for password in passwords):
                raise SystemExit("The application did not receive the fixture database password.")
    if args[0] == "run":
        for index, value in enumerate(args[:-1]):
            if value in ("-p", "--publish"):
                mapping = args[index + 1].split(":")
                if len(mapping) == 3 and mapping[-1] in ("5432", "8080", "8443"):
                    metadata["ports"][mapping[-1] + "/tcp"] = mapping[1] or "34567"
                elif len(mapping) == 4 and mapping[-1] in ("5432", "8080", "8443"):
                    metadata["ports"][mapping[-1] + "/tcp"] = mapping[2]
    state(name).write_text(json.dumps(metadata))
    if "web-enabled" in name and os.environ.get("SMOKE_REMOVE_CALLER"):
        caller = Path(os.environ["SMOKE_REMOVE_CALLER"])
        assert caller.name == "caller" and caller.parent.resolve() == root.parent.resolve()
        caller.rmdir()
elif args[:2] == ["network", "inspect"] and "--format" in args and "Gateway" in args[args.index("--format") + 1]:
    print("172.20.0.1")
elif args[0] == "inspect" or args[:2] == ["network", "inspect"]:
    name = args[-1]
    if not state(name).exists():
        raise SystemExit(1)
    item = json.loads(state(name).read_text())
    print(" ".join(item.get("localcluster.ci." + key, "") for key in ("repository", "owner", "run_id", "run_attempt")))
elif args[0] == "rm" or args[:2] == ["network", "rm"]:
    state(args[-1]).unlink()
elif args[0] == "port":
    name = args[1]
    protocol = args[2]
    item = json.loads(state(name).read_text())
    print("127.0.0.1:" + item.get("ports", {}).get(protocol, "34567"))
elif args[0] == "exec":
    print("PONG" if "redis-cli" in args else "accepting connections")
elif args[0] == "logs":
    if "smtp" in args[-1]:
        print("READY 2525")
else:
    raise SystemExit("unexpected fake Docker command")
PY
cat > "$TMP_ROOT/bin/curl" <<'SH'
#!/usr/bin/env bash
url="${*: -1}"
if [[ "${FRONTEND_PROFILE:-BlazorAuto}" == "React" ]]; then
  if [[ "$url" == */api/client-config ]]; then
    enabled="false"
    [[ "$url" != https://* ]] || enabled="true"
    printf 'HTTP/1.1 200 OK\r\nCache-Control: no-store\r\nContent-Type: application/json\r\n\r\n{"schemaVersion":1,"accountsEnabled":%s,"applicationId":"1234567890abcdef1234567890abcdef"}' "$enabled"
    exit
  fi
  if [[ "$url" == */ && "$*" == *"--dump-header"* ]]; then
    printf 'HTTP/1.1 200 OK\r\nCache-Control: no-cache\r\nContent-Security-Policy: default-src '\''self'\''; script-src '\''self'\'' '\''sha256-abcd'\''\r\n\r\n'
    exit
  fi
  case "$url" in
    */health/ready) printf '200' ;;
    */) printf '<!DOCTYPE html><script type="module" src="/assets/app-abcdef123456.js"></script>\n200' ;;
    */api/author-books) printf '{"books":[{}]}' ;;
    */api/books)
      printf 'HTTP/1.1 401 Unauthorized\r\nCache-Control: private, no-store\r\n\r\n'
      ;;
    */index.html)
      printf 'HTTP/1.1 200 OK\r\nCache-Control: no-cache\r\n\r\n'
      ;;
    */assets/app-abcdef123456.js)
      printf 'HTTP/1.1 200 OK\r\nCache-Control: public,max-age=31536000,immutable\r\n\r\n'
      ;;
    */api/auth/login)
      if [[ "$url" == https://* ]]; then
        printf 'HTTP/1.1 405 Method Not Allowed\r\nAllow: POST\r\n\r\n'
      else
        printf '\n404'
      fi
      ;;
    */api/auth|*/api/auth/session|*/api/auth/not-a-real-operation|*/Account|*/assets/missing.js) printf '\n404' ;;
    */books|*/books/author/example)
      if [[ " $* " == *" --head "* ]]; then
        printf 'HTTP/1.1 200 OK\r\nContent-Length: 123\r\n\r\n'
      else
        printf '<!DOCTYPE html><script type="module" src="/assets/app-abcdef123456.js"></script>'
      fi
      ;;
    *) exit 22 ;;
  esac
  exit
fi
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
if [[ "$(basename "$0")" == pwsh && "$*" == *Test-DeployedSite.ps1* ]]; then
  profile="$(printenv FRONTEND_PROFILE || printf BlazorAuto)"
  case "$profile" in
    BlazorAuto) acceptance="BlazorAutoV1" ;;
    React) acceptance="ReactPublicV1" ;;
    *) exit 35 ;;
  esac
  [[ " $* " == *" -FrontendProfile $profile "* ]] || exit 36
  [[ " $* " == *" -AcceptanceProfile $acceptance "* ]] || exit 37
  exit "$(printenv FAIL_HTTP_ACCEPTANCE || printf 0)"
fi
if [[ "$(basename "$0")" == dotnet ]]; then
  # The real CLI cannot initialize its parser from a removed working directory.
  pwd -P >/dev/null 2>&1 || exit 38
  if [[ "${FRONTEND_PROFILE:-BlazorAuto}" == "React" ]]; then
    case "$*" in
      *"Category=ReactPackagedDisabled"*) result_name="react-disabled-browser.trx"; failure="${FAIL_REACT_DISABLED_BROWSER:-0}" ;;
      *"Category=ReactPackagedEnabled"*) result_name="react-enabled-browser.trx"; failure="${FAIL_REACT_ENABLED_BROWSER:-0}" ;;
      *) exit 34 ;;
    esac
    results_dir=""
    previous=""
    for argument in "$@"; do
      if [[ "$previous" == "--results-directory" ]]; then results_dir="$argument"; fi
      previous="$argument"
    done
    [[ "$results_dir" == */test-results/123-2/${GITHUB_JOB:-validate}/docker-smoke/* || "$results_dir" == */test-results/local-*/${GITHUB_JOB:-validate}/docker-smoke/* ]] || exit 39
    [[ -n "$results_dir" ]] || exit 5
    mkdir -p "$results_dir"
    cat > "$results_dir/$result_name" <<'XML'
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results><UnitTestResult testName="react-browser-journey" outcome="Passed"/></Results></TestRun>
XML
    exit "$failure"
  fi
  [[ "$*" == *"RenderModeE2ETests"*"PreHydrationControlsE2ETests"* ]] || exit 3
  [[ "${E2E_CLEANUP_CONNECTION_STRING:-}" == *"Host=127.0.0.1;Port=34567;"* ]] || exit 4
  results_dir=""
  previous=""
  for argument in "$@"; do
    if [[ "$previous" == "--results-directory" ]]; then results_dir="$argument"; fi
    previous="$argument"
  done
  [[ "$results_dir" == */test-results/123-2/${GITHUB_JOB:-validate}/docker-smoke/* || "$results_dir" == */test-results/local-*/${GITHUB_JOB:-validate}/docker-smoke/* ]] || exit 39
  [[ -n "$results_dir" ]] || exit 5
  mkdir -p "$results_dir"
  cat > "$results_dir/blazor-browser-smoke.trx" <<'XML'
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results><UnitTestResult testName="first" outcome="Passed"/><UnitTestResult testName="second" outcome="Passed"/></Results></TestRun>
XML
  exit "${FAIL_BROWSER:-0}"
fi
exit 0
SH
done
chmod +x "$TMP_ROOT/bin/"*
run_case() {
  local expected="$1" status=0
  mkdir -p "$TMP_ROOT/runner-temp"
  if [[ "${REMOVE_CALLER_DIRECTORY:-0}" == 1 ]]; then
    mkdir -p "$TMP_ROOT/caller"
    (cd "$TMP_ROOT/caller" && SMOKE_REMOVE_CALLER="$TMP_ROOT/caller" RUNNER_TEMP="$TMP_ROOT/runner-temp" GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT=2 bash "$SCRIPT") > "$TMP_ROOT/output" 2>&1 || status=$?
  else
    RUNNER_TEMP="$TMP_ROOT/runner-temp" GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT=2 bash "$SCRIPT" > "$TMP_ROOT/output" 2>&1 || status=$?
  fi
  [[ "$status" == "$expected" ]] || { cat "$TMP_ROOT/output" >&2; echo "expected $expected, got $status" >&2; exit 1; }
  [[ -z "$(find "$SMOKE_STATE" -type f -print)" ]] || { echo "owned resources leaked" >&2; exit 1; }
}
run_case 0
FRONTEND_PROFILE=React run_case 0
GITHUB_JOB=publish-main FRONTEND_PROFILE=React run_case 0
FRONTEND_PROFILE=React REMOVE_CALLER_DIRECTORY=1 run_case 0
FRONTEND_PROFILE=React FRONTEND_ACCEPTANCE_PROFILE=BlazorAutoV1 run_case 2
FAIL_IMAGE_LABEL=1 run_case 1
FAIL_ACCEPTANCE_LABEL=1 run_case 1
FAIL_REDIS=1 run_case 17
FAIL_API=1 run_case 1
FAIL_BROWSER=19 run_case 19
FRONTEND_PROFILE=React FAIL_REACT_DISABLED_BROWSER=20 run_case 20
FRONTEND_PROFILE=React FAIL_REACT_ENABLED_BROWSER=21 run_case 21
FAIL_HTTP_ACCEPTANCE=23 run_case 23
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
            assert args[args.index("--network-alias") + 1] == "ci-postgres"
            assert "/var/lib/postgresql:rw,size=1073741824" in args
            assert "127.0.0.1::5432" in args, "postgres must publish only on loopback"
        if "redis" in name:
            assert args[args.index("--network-alias") + 1] == "ci-redis"
            assert "/data:rw,size=67108864" in args
            assert "--appendonly" in args
        if "web" in name:
            assert any(value.startswith("ConnectionStrings__DefaultConnection=Host=ci-postgres;") for value in args)
            assert "Redis__Configuration=ci-redis:6379,abortConnect=false" in args
            assert "RateLimiting__Api__PermitLimit=1000" in args
            assert "LocalAccounts__Enabled=false" in args
            if "web-enabled" in name:
                assert "Accounts__Enabled=true" in args
                assert "Accounts__RegistrationEnabled=true" in args
                assert "Accounts__Email__Security=StartTls" in args
                assert "ASPNETCORE_URLS=http://+:8080;https://+:8443" in args
                assert any(value.endswith(":8443") for value in args if value.startswith("127.0.0.1:"))
                assert any(value.endswith(":ro") for value in args if "/run/react-auth-fixture" in value)
        elif "smtp" in name:
            assert "node:26.12.1-bookworm-slim" in args
            assert "--read-only" in args
            assert args[args.index("--network-alias") + 1] == "ci-smtp"
            assert not any(value in ("-p", "--publish") for value in args)
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
# A fresh always-run step recovers owned leftovers after the prior process was killed.
export SMOKE_CLEANUP_OFFSET
SMOKE_CLEANUP_OFFSET="$(wc -l < "$SMOKE_CALLS")"
python3 - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['SMOKE_STATE'])
labels = {'localcluster.ci.repository': 'example/repo', 'localcluster.ci.owner': 'ci-smoke', 'localcluster.ci.run_id': '123', 'localcluster.ci.run_attempt': '2'}
for name in ('sample-ci-postgres-123-2', 'sample-ci-redis-123-2', 'sample-ci-web-enabled-123-2', 'sample-ci-smtp-123-2', 'sample-ci-123-2'):
    (root / name).write_text(json.dumps(labels))
(root / 'sample-ci-postgres-456-1').write_text(json.dumps({**labels, 'localcluster.ci.run_id': '456', 'localcluster.ci.run_attempt': '1'}))
PY
GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT=2 bash "$SCRIPT" --cleanup-only
GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT=2 bash "$SCRIPT" --cleanup-only
[[ -f "$SMOKE_STATE/sample-ci-web-123-2" && -f "$SMOKE_STATE/sample-ci-postgres-456-1" ]]
[[ "$(find "$SMOKE_STATE" -type f | wc -l)" == 2 ]]
status=0
env -u GITHUB_RUN_ID bash "$SCRIPT" --cleanup-only > "$TMP_ROOT/missing-cleanup-identity" 2>&1 || status=$?
[[ "$status" == 2 ]]
python3 - <<'PY'
import json, os
from pathlib import Path
calls = [json.loads(line) for line in Path(os.environ['SMOKE_CALLS']).read_text().splitlines()][int(os.environ['SMOKE_CLEANUP_OFFSET']):]
assert all(args[0] in ('inspect', 'rm', 'network') for args in calls)
assert not any(args[:2] == ['network', 'create'] for args in calls)
assert not any('456-1' in value for args in calls for value in args), 'another run was touched'
assert not any('prune' in args or 'volume' in args for args in calls)
PY
echo "smoke success/failure, interruption recovery, HTTP checks, bounded storage, local uniqueness, and foreign sentinel fixtures passed"
