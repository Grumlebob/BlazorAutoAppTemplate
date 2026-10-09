#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$(cd "$SCRIPT_DIR/.." && pwd)"
COMMON_SOURCE="$(cd "$SOURCE/../../Common/Scripts" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$TMP_ROOT/Deployment/Common/Scripts/Component" "$TMP_ROOT/Deployment/LocalCluster/Scripts/Component" "$TMP_ROOT/bin" "$TMP_ROOT/runner/_work/repo/repo"
export GITHUB_WORKSPACE="$TMP_ROOT/runner/_work/repo/repo"
export LOCALCLUSTER_DEPLOY_LOCK_DIR="$TMP_ROOT/operation.lock"
export LOCALCLUSTER_DEPLOY_LOCK_TIMEOUT_SECONDS=0
export CALLS="$TMP_ROOT/calls"
export PATH="$TMP_ROOT/bin:$PATH"
cp "$SOURCE/run-localcluster-maintenance.sh" "$SOURCE/localcluster-capacity-thresholds.sh" "$SOURCE/check-node-main-capacity.sh" "$TMP_ROOT/Deployment/LocalCluster/Scripts/"
cp "$COMMON_SOURCE/with-deploy-lock.sh" "$TMP_ROOT/Deployment/Common/Scripts/"
cp "$COMMON_SOURCE/Component/with-deploy-lock.sh" "$TMP_ROOT/Deployment/Common/Scripts/Component/"
cat > "$TMP_ROOT/Deployment/LocalCluster/Scripts/prune-ci-residue.py" <<'PY'
import os
from pathlib import Path
if __name__ == "__main__":
    lock_dir = Path(os.environ["LOCALCLUSTER_DEPLOY_LOCK_DIR"])
    assert (lock_dir / "token").read_text().strip() == os.environ["LOCALCLUSTER_DEPLOY_LOCK_TOKEN"]
    with open(os.environ["CALLS"], "a") as stream:
        stream.write("ci-residue\n")
    raise SystemExit(int(os.environ.get("CI_STATUS", "0")))
PY
for filename in prune-actions-runner-residue.sh prune-docker-residue.sh prune-cluster-docker-residue.sh; do
  destination="$TMP_ROOT/Deployment/LocalCluster/Scripts"
  [[ "$filename" != prune-actions-runner-residue.sh ]] || destination="$TMP_ROOT/Deployment/Common/Scripts"
  cat > "$destination/$filename" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
test -f "$LOCALCLUSTER_DEPLOY_LOCK_DIR/token"
case "$(basename "$0")" in
  prune-actions-runner-residue.sh) echo runner >> "$CALLS"; exit "${RUNNER_STATUS:-0}" ;;
  prune-docker-residue.sh) echo docker >> "$CALLS"; exit "${DOCKER_STATUS:-0}" ;;
  *) echo remote >> "$CALLS"; exit "${REMOTE_STATUS:-0}" ;;
esac
SH
done
cat > "$TMP_ROOT/bin/df" <<'SH'
#!/usr/bin/env bash
available="${FREE_MB:-80000}"
[[ "$1" != -Pi ]] || available="${FREE_INODES:-80000}"
printf '%s\n' 'Filesystem blocks used available percent mount' "/dev/test 90000 10000 $available 10% /opt"
if [[ "$1" == -Pi ]]; then exit "${INODE_QUERY_STATUS:-0}"; fi
exit "${DISK_QUERY_STATUS:-0}"
SH
cat > "$TMP_ROOT/bin/docker" <<'SH'
#!/usr/bin/env bash
# Maintenance itself may only list volumes; every mutation goes through a stage script.
[[ "$1 $2" == "volume ls" ]] || { echo "unexpected docker call: $*" >> "$CALLS"; exit 1; }
exit "${VOLUME_QUERY_STATUS:-0}"
SH
chmod +x "$TMP_ROOT/bin/"*
run_case() {
  local expected="$1" status=0
  shift
  : > "$CALLS"
  bash "$TMP_ROOT/Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh" "$@" > "$TMP_ROOT/output" 2>&1 || status=$?
  [[ "$status" == "$expected" ]] || { cat "$TMP_ROOT/output" >&2; echo "expected $expected, got $status" >&2; exit 1; }
  [[ ! -e "$LOCALCLUSTER_DEPLOY_LOCK_DIR" ]] || { echo "lock leaked" >&2; exit 1; }
}
run_case 0
[[ "$(paste -sd, "$CALLS")" == runner,ci-residue,docker,remote ]]
run_case 0 --capacity-only
[[ "$(paste -sd, "$CALLS")" == runner,docker ]]
CI_STATUS=75 run_case 75
grep -Fxq remote "$CALLS"
CI_STATUS=1 run_case 1
grep -Fxq remote "$CALLS"
REMOTE_STATUS=2 run_case 1
DOCKER_STATUS=2 run_case 2
DOCKER_STATUS=2 REMOTE_STATUS=1 run_case 1
CI_STATUS=75 FREE_MB=100 run_case 2
VOLUME_QUERY_STATUS=1 run_case 1
grep -Fq '/opt capacity:' "$TMP_ROOT/output"
RUNNER_STATUS=75 run_case 0 --capacity-only
FREE_MB=100 run_case 2 --capacity-only
FREE_MB=invalid run_case 1 --capacity-only
FREE_INODES=100 run_case 2 --capacity-only
FREE_INODES=invalid run_case 1 --capacity-only
INODE_QUERY_STATUS=1 run_case 1 --capacity-only
DISK_QUERY_STATUS=1 run_case 1 --capacity-only
# Test the capacity gate directly.
for variable in INODE_QUERY_STATUS DISK_QUERY_STATUS; do
  status=0
  env "$variable=1" bash "$TMP_ROOT/Deployment/LocalCluster/Scripts/check-node-main-capacity.sh" > "$TMP_ROOT/capacity" 2>&1 || status=$?
  [[ "$status" == 1 ]] || { echo "capacity gate hid $variable" >&2; exit 1; }
done
RUNNER_STATUS=1 run_case 1 --capacity-only
run_case 1 --under-lock
[[ ! -s "$CALLS" ]]
mkdir "$LOCALCLUSTER_DEPLOY_LOCK_DIR"
printf foreign > "$LOCALCLUSTER_DEPLOY_LOCK_DIR/token"
status=0
bash "$TMP_ROOT/Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh" > "$TMP_ROOT/blocked" 2>&1 || status=$?
[[ "$status" == 1 && "$(cat "$LOCALCLUSTER_DEPLOY_LOCK_DIR/token")" == foreign && ! -s "$CALLS" ]]
echo "maintenance coordination, stage outcomes, pressure-only mode, and capacity fixtures passed"
