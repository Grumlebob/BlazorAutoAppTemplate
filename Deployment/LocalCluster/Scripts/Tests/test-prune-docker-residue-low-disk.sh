#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../../.." && pwd)"
SCRIPT="$REPO_ROOT/Deployment/LocalCluster/Scripts/prune-docker-residue.sh"
TMP_ROOT="$(mktemp -d)"
FAKE_BIN="$TMP_ROOT/bin"
MARKER="$TMP_ROOT/low-disk-builder-pruned"
IMAGE_MARKER="$TMP_ROOT/low-disk-image-pruned"
COMMAND_LOG="$TMP_ROOT/docker-commands.log"
# Old tags of the configured release image are the cleanup candidates.
TEST_IMAGE="$(bash "$REPO_ROOT/Deployment/Common/Scripts/read-release-setting.sh" app_image)"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

fail() {
  echo "test failed: $*" >&2
  exit 1
}

mkdir -p "$FAKE_BIN"

cat > "$FAKE_BIN/df" <<EOF
#!/usr/bin/env bash
set -euo pipefail

marker="$MARKER"
if [[ "\${1:-}" == "-Pm" ]]; then
  if [[ -f "\$marker" ]]; then
    available=40960
  else
    available=1024
  fi
  echo "Filesystem 1048576-blocks Used Available Capacity Mounted on"
  echo "/dev/fake 100000 50000 \${available} 50% /opt"
  exit 0
fi

echo "Filesystem      Size  Used Avail Use% Mounted on"
echo "/dev/fake       100G   50G   1G  99% /"
echo "/dev/fake       100G   50G   1G  99% /opt"
EOF
chmod +x "$FAKE_BIN/df"

cat > "$FAKE_BIN/docker" <<EOF
#!/usr/bin/env bash
set -euo pipefail

marker="$MARKER"
image_marker="$IMAGE_MARKER"
command_log="$COMMAND_LOG"
old_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
protected_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
printf '%s\n' "\$*" >> "\$command_log"

case "\${1:-}" in
  info)
    exit 0
    ;;
  system)
    if [[ "\${2:-}" == "df" ]]; then
      echo "TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE"
      echo "Build Cache     1         0         1GB       1GB"
      exit 0
    fi
    ;;
  ps)
    if [[ "\$*" == *"ancestor="* ]]; then exit 0; fi
    if [[ "\$*" == *"{{.Image}}"* ]]; then
      echo "${TEST_IMAGE}:protected"
    else
      echo "NAMES IMAGE STATUS"
    fi
    exit 0
    ;;
  image)
    case "\${2:-}" in
      inspect)
        if [[ "\$*" != *--format* ]]; then
          label=example/repo
          digests='[]'
          [[ "\${DANGLING_FIXTURE:-}" != foreign ]] || label=foreign/repo
          [[ "\${DANGLING_FIXTURE:-}" != payload ]] || digests='["ghcr.io/fixture-owner/app-release-payload@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"]'
          printf '[{"Id":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","Created":"2020-01-01T00:00:00Z","RepoTags":[],"RepoDigests":%s,"Config":{"Labels":{"localcluster.ci.repository":"%s","localcluster.ci.owner":"ci-build"}}}]\n' "\$digests" "\$label"
          exit 0
        fi
        target="\${5:-}"
        if [[ "\$*" == *"{{.Created}}"* ]]; then
          date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ'
        elif [[ "\$target" == "${TEST_IMAGE}:old" ]]; then
          echo "sha256:\$old_id"
        else
          echo "sha256:\$protected_id"
        fi
        exit 0
        ;;
      ls)
        if [[ "\$*" == *"dangling=true"* ]]; then
          case "\${DANGLING_FIXTURE:-}" in
            owned|foreign|payload) echo sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc ;;
            protected) echo "sha256:\$protected_id" ;;
          esac
          exit 0
        fi
        printf '%s\t${TEST_IMAGE}\told\n' "\${old_id:0:12}"
        exit "\${IMAGE_LIST_STATUS:-0}"
        ;;
      rm)
        if [[ "\$*" == *"${TEST_IMAGE}:old"* ]]; then
          touch "\$image_marker"
        fi
        exit 0
        ;;
      prune)
        exit 0
        ;;
    esac
    ;;
  container|network)
    if [[ "\${2:-}" == "prune" ]]; then
      exit 0
    fi
    ;;
  builder)
    if [[ "\${2:-}" == "prune" ]]; then
      if [[ "\$*" == *"until=0h"* ]]; then
        touch "\$marker"
      fi
      exit 0
    fi
    ;;
esac

echo "unexpected fake docker command: \$*" >&2
exit 1
EOF
chmod +x "$FAKE_BIN/docker"

PATH="$FAKE_BIN:$PATH" bash "$SCRIPT" \
  --release-protection-verified \
  --force \
  --min-free-mb 20480 \
  --dangling-image-until 168h \
  --localcluster-image-until 168h \
  --low-disk-localcluster-image-until 0h \
  --builder-until 48h \
  --low-disk-builder-until 0h \
  --allow-shared-builder-prune >"$TMP_ROOT/output.log"

[[ -f "$IMAGE_MARKER" ]] || fail "expected low-disk LocalCluster image fallback to run"
[[ -f "$MARKER" ]] || fail "expected low-disk builder cache fallback to run"
grep -Fq "image rm ${TEST_IMAGE}:old" "$COMMAND_LOG" \
  || fail "expected low-disk app image removal"
grep -Fq "builder prune -af --filter until=48h" "$COMMAND_LOG" \
  || fail "expected routine builder prune"
grep -Fq "builder prune -af --filter until=0h" "$COMMAND_LOG" \
  || fail "expected low-disk builder prune"
grep -Fq "/opt free disk is 40960MiB; required minimum is 20480MiB." "$TMP_ROOT/output.log" \
  || fail "expected final free-space success message"

set +e
PATH="$FAKE_BIN:$PATH" bash "$SCRIPT" \
  --release-protection-verified \
  --force \
  --defer-if-skipped \
  --remove-image ${TEST_IMAGE}:protected \
  --min-free-mb 20480 \
  --dangling-image-until 168h \
  --localcluster-image-until 168h \
  --builder-until 48h \
  >"$TMP_ROOT/deferred.log" 2>&1
deferred_status=$?
set -e
[[ "$deferred_status" -eq 75 ]] || { cat "$TMP_ROOT/deferred.log" >&2; fail "expected protected image deferral to return 75, got $deferred_status"; }
grep -Fq "skip protected image: ${TEST_IMAGE}:protected" "$TMP_ROOT/deferred.log" \
  || fail "expected protected image to remain untouched"

: > "$COMMAND_LOG"
inventory_status=0
PATH="$FAKE_BIN:$PATH" IMAGE_LIST_STATUS=1 bash "$SCRIPT" \
  --release-protection-verified \
  --force --min-free-mb 0 --localcluster-image-until 0h \
  > "$TMP_ROOT/inventory-failure.log" 2>&1 || inventory_status=$?
[[ "$inventory_status" -eq 1 ]] || fail "partial inventory failure was hidden"
if grep -Fq 'image rm ' "$COMMAND_LOG"; then
  fail "images removed from a partial/failed inventory"
fi
grep -Fq 'could not inventory Docker images' "$TMP_ROOT/inventory-failure.log" \
  || fail "inventory failure lacked an actionable diagnostic"

# Routine maintenance: only this repository's labelled CI images, no host-wide prunes.
: > "$COMMAND_LOG"
PATH="$FAKE_BIN:$PATH" GITHUB_REPOSITORY=example/repo bash "$SCRIPT" \
  --release-protection-verified \
  --force --min-free-mb 0 > "$TMP_ROOT/routine.log" 2>&1
grep -Fq "image ls --no-trunc --filter dangling=true --filter label=localcluster.ci.repository=example/repo" "$COMMAND_LOG" \
  || fail "expected individual labelled CI image inspection for this repository"
if grep -Eq "^(container|network) prune|builder prune|^image prune -f --filter until=" "$COMMAND_LOG"; then
  fail "routine maintenance ran a host-wide prune"
fi
if grep -Eq "volume|system prune" "$COMMAND_LOG"; then
  fail "Docker volumes or the whole system were pruned"
fi

# Host-wide prunes only with the explicit opt-in.
: > "$COMMAND_LOG"
PATH="$FAKE_BIN:$PATH" bash "$SCRIPT" \
  --release-protection-verified \
  --force --min-free-mb 0 --include-unlabelled-host-residue > "$TMP_ROOT/host-wide.log" 2>&1
for expected in "container prune -f --filter until=24h" "network prune -f --filter until=24h"; do
  grep -Fq "$expected" "$COMMAND_LOG" || fail "expected opt-in host-wide prune: $expected"
done
if grep -Fq 'image prune' "$COMMAND_LOG"; then fail "host-wide image prune bypassed release protection"; fi

# Standalone calls without the existing release authority must never remove images.
: > "$COMMAND_LOG"
status=0
PATH="$FAKE_BIN:$PATH" bash "$SCRIPT" --force --min-free-mb 0 --defer-if-skipped \
  --localcluster-image-until 0h --remove-image "${TEST_IMAGE}:old" > "$TMP_ROOT/no-protection.log" 2>&1 || status=$?
[[ "$status" == 75 ]] || fail "missing release protection did not defer"
if grep -Eq 'image (rm|prune)' "$COMMAND_LOG"; then fail "image mutation without release protection"; fi

# Recovery references protect the same image ID even through another old tag.
: > "$COMMAND_LOG"
PATH="$FAKE_BIN:$PATH" bash "$SCRIPT" --release-protection-verified \
  --protect-image "${TEST_IMAGE}:old" --force --min-free-mb 0 --localcluster-image-until 0h > "$TMP_ROOT/recovery-protected.log" 2>&1
if grep -Fq 'image rm' "$COMMAND_LOG"; then fail "recovery image was removed"; fi
for fixture in owned foreign payload protected; do
  : > "$COMMAND_LOG"
  PATH="$FAKE_BIN:$PATH" GITHUB_REPOSITORY=example/repo DANGLING_FIXTURE="$fixture" bash "$SCRIPT" --release-protection-verified \
    --force --min-free-mb 0 > "$TMP_ROOT/dangling-$fixture.log" 2>&1 \
    || { cat "$TMP_ROOT/dangling-$fixture.log" >&2; fail "dangling fixture failed: $fixture"; }
  if [[ "$fixture" == owned ]]; then
    grep -Fq 'image rm sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc' "$COMMAND_LOG" || fail "eligible owned dangling image was not removed"
  elif grep -Fq 'image rm' "$COMMAND_LOG"; then
    fail "foreign, payload or protected dangling image was removed"
  fi
done
grep -Fq "Docker volumes are protected" "$TMP_ROOT/host-wide.log" || fail "expected the volume protection statement"

echo "prune-docker-residue low-disk fixture test passed"
