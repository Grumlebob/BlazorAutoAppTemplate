#!/usr/bin/env bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../.." 2>/dev/null && pwd || echo "$SCRIPT_DIR")"

DRY_RUN="false"
FORCE="false"
MIN_FREE_MB="20480"
OPT_ROOT="/opt"
ALL_LOCALCLUSTER_RUNNERS="false"
STALE_VERSION_UNTIL="168h"
UPDATE_UNTIL="24h"
TEMP_UNTIL="24h"
DIAG_UNTIL="336h"
RUNNER_ROOT_ARGS=()
RUNNER_ROOTS=()
PROTECTED_PATHS=()
REMOVED_COUNT=0
SKIPPED_COUNT=0
DEFERRED_COUNT=0
DEFER_IF_SKIPPED="false"

usage() {
  cat >&2 <<'USAGE'
usage: prune-actions-runner-residue.sh [options]

Safely prunes stale self-hosted GitHub Actions runner residue on node-main.

Options:
  --dry-run                         Print commands without deleting files.
  --force                           Run retention cleanup even when /opt already has enough free space.
  --min-free-mb <mb>                Required free /opt space after cleanup. Default: 20480.
  --runner-root <path>              Add one explicit runner root to inspect.
  --all-localcluster-runners        Inspect /opt/actions-runner-* roots.
  --opt-root <path>                 Test fixture root for runner discovery. Default: /opt.
  --stale-version-until <duration>  Retention for inactive bin.* and externals.* dirs. Default: 168h.
  --update-until <duration>         Retention for _work/_update dirs. Default: 24h.
  --temp-until <duration>           Retention for _work/_temp entries. Default: 24h.
  --diag-until <duration>           Retention for diagnostic log files. Default: 336h.
  --defer-if-skipped                Return 75 when ownership/activity prevents a safe removal.
  --help, -h                        Show this help.
USAGE
}

fail() {
  echo "error: $*" >&2
  exit 1
}

array_contains() {
  local value="$1"
  shift

  local item
  for item in "$@"; do
    [[ "$item" != "$value" ]] || return 0
  done

  return 1
}

add_unique() {
  local -n target_array="$1"
  local value="${2:-}"
  [[ -n "$value" ]] || return 0
  array_contains "$value" "${target_array[@]}" && return 0

  target_array+=("$value")
}

quote_arg() {
  printf "'%s'" "${1//\'/\'\\\'\'}"
}

print_command() {
  local first="true"
  local arg
  for arg in "$@"; do
    if [[ "$first" == "true" ]]; then
      first="false"
    else
      printf ' '
    fi
    quote_arg "$arg"
  done
  printf '\n'
}

run_or_print() {
  printf '+ '
  print_command "$@"
  if [[ "$DRY_RUN" == "true" ]]; then
    return 0
  fi

  "$@"
}

duration_seconds() {
  local value="$1"
  if [[ "$value" =~ ^([0-9]+)([smhdw])$ ]]; then
    local amount="${BASH_REMATCH[1]}"
    local unit="${BASH_REMATCH[2]}"
    case "$unit" in
      s) printf '%s\n' "$amount" ;;
      m) printf '%s\n' "$((amount * 60))" ;;
      h) printf '%s\n' "$((amount * 60 * 60))" ;;
      d) printf '%s\n' "$((amount * 24 * 60 * 60))" ;;
      w) printf '%s\n' "$((amount * 7 * 24 * 60 * 60))" ;;
      *) return 1 ;;
    esac
    return 0
  fi

  return 1
}

free_opt_mb() {
  local disk_root="$OPT_ROOT"
  [[ -d "$disk_root" ]] || disk_root="/opt"
  df -Pm "$disk_root" | awk 'NR == 2 { print $4 }'
}

print_heading() {
  printf '\n== %s ==\n' "$1"
}

print_report() {
  local label="$1"
  print_heading "$label"
  printf 'mode: %s\n' "$([[ "$DRY_RUN" == "true" ]] && echo "dry-run" || echo "apply")"
  printf 'force: %s\n' "$FORCE"
  printf 'repository root: %s\n' "$REPO_ROOT"
  printf 'opt root: %s\n' "$OPT_ROOT"
  printf 'hostname: %s\n' "$(hostname)"
  printf 'whoami: %s\n' "$(whoami)"

  if [[ -d "$OPT_ROOT" ]]; then
    df -h / "$OPT_ROOT"
    df -Pi / "$OPT_ROOT"
  elif [[ -d /opt ]]; then
    df -h / /opt
    df -Pi / /opt
  else
    df -h /
    df -Pi /
  fi

  if [[ "${#RUNNER_ROOTS[@]}" -eq 0 ]]; then
    echo "no runner roots discovered"
    return 0
  fi

  local runner_root
  for runner_root in "${RUNNER_ROOTS[@]}"; do
    if [[ -d "$runner_root" ]]; then
      du -sh "$runner_root" || true
    fi
  done
}

path_inside() {
  local root="$1"
  local target="$2"
  [[ "$target" == "$root"/* ]]
}

is_protected_path() {
  local target="$1"
  local protected
  for protected in "${PROTECTED_PATHS[@]}"; do
    [[ "$target" != "$protected" ]] || return 0
  done

  return 1
}

is_older_than() {
  local target="$1"
  local duration="$2"
  local retention_seconds modified_epoch cutoff_epoch
  retention_seconds="$(duration_seconds "$duration")" || fail "unsupported duration: $duration"
  modified_epoch="$(stat -c %Y "$target" 2>/dev/null || true)"
  [[ -n "$modified_epoch" ]] || return 1
  cutoff_epoch=$(( $(date -u +%s) - retention_seconds ))
  [[ "$modified_epoch" -lt "$cutoff_epoch" ]]
}

is_path_active() {
  local target="$1"
  [[ -d /proc ]] || return 1

  local proc_entry fd_path resolved cmdline
  for proc_entry in /proc/[0-9]*; do
    [[ -d "$proc_entry" ]] || continue

    for fd_path in "$proc_entry/cwd" "$proc_entry/root" "$proc_entry/exe"; do
      resolved="$(readlink -f "$fd_path" 2>/dev/null || true)"
      if [[ -n "$resolved" && ( "$resolved" == "$target" || "$resolved" == "$target"/* ) ]]; then
        return 0
      fi
    done

    if [[ -r "$proc_entry/cmdline" ]]; then
      cmdline="$(tr '\0' ' ' < "$proc_entry/cmdline" 2>/dev/null || true)"
      if [[ "$cmdline" == *"$target"* ]]; then
        return 0
      fi
    fi
  done

  return 1
}

skip_candidate() {
  local message="$1"
  SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
  echo "skip: $message"
}

defer_candidate() {
  DEFERRED_COUNT=$((DEFERRED_COUNT + 1))
  skip_candidate "$1"
}

skip_candidate_quiet() {
  SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
}

remove_candidate() {
  local runner_root="$1"
  local target="$2"
  local reason="$3"
  local resolved_root resolved_target size

  [[ -n "$runner_root" && -n "$target" ]] || fail "internal error: empty deletion candidate"
  [[ -e "$target" ]] || {
    skip_candidate "missing candidate: $target"
    return 0
  }
  [[ ! -L "$target" ]] || {
    defer_candidate "symlink candidate refused: $target"
    return 0
  }

  resolved_root="$(readlink -f "$runner_root" 2>/dev/null || true)"
  resolved_target="$(readlink -f "$target" 2>/dev/null || true)"
  [[ -n "$resolved_root" && -n "$resolved_target" ]] || fail "could not resolve candidate: $target"
  [[ "$resolved_target" != "/" && "$resolved_target" != "/opt" ]] || fail "refusing unsafe target: $resolved_target"
  [[ "$resolved_target" != "$resolved_root" ]] || fail "refusing to remove runner root: $resolved_target"
  path_inside "$resolved_root" "$resolved_target" || fail "refusing target outside runner root: $target -> $resolved_target"

  if is_protected_path "$resolved_target"; then
    # The current runner is intentionally retained, not unfinished cleanup.
    skip_candidate "protected current runner path: $target"
    return 0
  fi

  if [[ -d "$resolved_target" ]] && is_path_active "$resolved_target"; then
    defer_candidate "active path: $target"
    return 0
  fi

  size="$(du -sh "$target" 2>/dev/null | awk '{ print $1 }' || true)"
  printf 'candidate: %s reason=%s size=%s\n' "$target" "$reason" "${size:-unknown}"
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "would remove: $target"
  fi

  run_or_print rm -rf --one-file-system -- "$target"
  if [[ "$DRY_RUN" != "true" ]]; then
    echo "removed: $target"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
  fi
}

consider_candidate() {
  local runner_root="$1"
  local target="$2"
  local retention="$3"
  local reason="$4"

  [[ -e "$target" ]] || return 0
  if ! is_older_than "$target" "$retention"; then
    skip_candidate_quiet
    return 0
  fi

  remove_candidate "$runner_root" "$target" "$reason"
}

discover_runner_roots() {
  local candidates=()
  local candidate app_name resolved

  if [[ "${#RUNNER_ROOT_ARGS[@]}" -gt 0 ]]; then
    candidates=("${RUNNER_ROOT_ARGS[@]}")
  elif [[ "$ALL_LOCALCLUSTER_RUNNERS" == "true" ]]; then
    shopt -s nullglob
    candidates=("$OPT_ROOT"/actions-runner-*)
    shopt -u nullglob
  else
    app_name="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_name 2>/dev/null || true)"
    if [[ -n "$app_name" ]]; then
      candidates=("$OPT_ROOT/actions-runner-$app_name")
    fi
  fi

  for candidate in "${candidates[@]}"; do
    if [[ ! -d "$candidate" ]]; then
      echo "runner root absent: $candidate"
      continue
    fi

    if [[ "$(basename "$candidate")" != actions-runner-* ]]; then
      fail "runner root basename must start with actions-runner-: $candidate"
    fi

    resolved="$(readlink -f "$candidate" 2>/dev/null || true)"
    [[ -n "$resolved" ]] || fail "could not resolve runner root: $candidate"
    add_unique RUNNER_ROOTS "$resolved"
  done
}

discover_protected_paths() {
  local runner_root target resolved

  for runner_root in "${RUNNER_ROOTS[@]}"; do
    for target in "$runner_root/bin" "$runner_root/externals"; do
      resolved="$(readlink -f "$target" 2>/dev/null || true)"
      if [[ -n "$resolved" && -e "$resolved" ]]; then
        add_unique PROTECTED_PATHS "$resolved"
      fi
    done
  done
}

print_protected_paths() {
  print_heading "Protected runner paths"
  if [[ "${#PROTECTED_PATHS[@]}" -eq 0 ]]; then
    echo "  no protected runner paths discovered"
    return 0
  fi

  local protected
  for protected in "${PROTECTED_PATHS[@]}"; do
    printf '  - %s\n' "$protected"
  done
}

prune_runner_root() {
  local runner_root="$1"
  local candidate

  print_heading "Inspecting runner root"
  echo "$runner_root"
  if [[ -L "$runner_root/bin" ]]; then
    printf 'current bin: %s\n' "$(readlink -f "$runner_root/bin" 2>/dev/null || echo unavailable)"
  fi
  if [[ -L "$runner_root/externals" ]]; then
    printf 'current externals: %s\n' "$(readlink -f "$runner_root/externals" 2>/dev/null || echo unavailable)"
  fi
  du -sh "$runner_root" || true

  shopt -s nullglob
  for candidate in "$runner_root"/bin.* "$runner_root"/externals.*; do
    [[ -d "$candidate" ]] || continue
    consider_candidate "$runner_root" "$candidate" "$STALE_VERSION_UNTIL" "stale runner version"
  done
  shopt -u nullglob

  consider_candidate "$runner_root" "$runner_root/_work/_update" "$UPDATE_UNTIL" "old runner update staging"

  if [[ -d "$runner_root/_work/_temp" ]]; then
    shopt -s nullglob dotglob
    for candidate in "$runner_root"/_work/_temp/*; do
      [[ -e "$candidate" ]] || continue
      consider_candidate "$runner_root" "$candidate" "$TEMP_UNTIL" "old runner temp entry"
    done
    shopt -u nullglob dotglob
  fi

  if [[ -d "$runner_root/_diag" ]]; then
    while IFS= read -r -d '' candidate; do
      consider_candidate "$runner_root" "$candidate" "$DIAG_UNTIL" "old runner diagnostic log"
    done < <(find "$runner_root/_diag" -type f \( -name '*.log' -o -name '*.log.*' \) -print0)
  fi
}

assert_min_free_space() {
  [[ "$MIN_FREE_MB" =~ ^[0-9]+$ ]] || fail "--min-free-mb must be an integer"
  [[ "$MIN_FREE_MB" -gt 0 ]] || return 0

  local free_mb
  free_mb="$(free_opt_mb)"
  [[ "$free_mb" =~ ^[0-9]+$ ]] || fail "could not measure free /opt space"
  if [[ "$free_mb" -ge "$MIN_FREE_MB" ]]; then
    echo "/opt free disk is ${free_mb}MiB; required minimum is ${MIN_FREE_MB}MiB."
    return 0
  fi

  echo "Actions runner cleanup completed, but /opt is still below threshold; investigate non-runner disk usage." >&2
  echo "/opt free disk is ${free_mb}MiB; required minimum is ${MIN_FREE_MB}MiB." >&2
  echo "Suggested read-only checks:" >&2
  echo "  du -xh --max-depth=1 /opt | sort -h" >&2
  echo "  du -xh --max-depth=2 /opt/actions-runner-* 2>/dev/null | sort -h | tail -n 80" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    --min-free-mb)
      [[ $# -ge 2 ]] || fail "--min-free-mb requires a value"
      MIN_FREE_MB="$2"
      shift 2
      ;;
    --runner-root)
      [[ $# -ge 2 ]] || fail "--runner-root requires a value"
      RUNNER_ROOT_ARGS+=("$2")
      shift 2
      ;;
    --all-localcluster-runners)
      ALL_LOCALCLUSTER_RUNNERS="true"
      shift
      ;;
    --opt-root)
      [[ $# -ge 2 ]] || fail "--opt-root requires a value"
      OPT_ROOT="$2"
      shift 2
      ;;
    --stale-version-until)
      [[ $# -ge 2 ]] || fail "--stale-version-until requires a value"
      STALE_VERSION_UNTIL="$2"
      shift 2
      ;;
    --update-until)
      [[ $# -ge 2 ]] || fail "--update-until requires a value"
      UPDATE_UNTIL="$2"
      shift 2
      ;;
    --temp-until)
      [[ $# -ge 2 ]] || fail "--temp-until requires a value"
      TEMP_UNTIL="$2"
      shift 2
      ;;
    --diag-until)
      [[ $# -ge 2 ]] || fail "--diag-until requires a value"
      DIAG_UNTIL="$2"
      shift 2
      ;;
    --defer-if-skipped)
      DEFER_IF_SKIPPED="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

for duration in "$STALE_VERSION_UNTIL" "$UPDATE_UNTIL" "$TEMP_UNTIL" "$DIAG_UNTIL"; do
  duration_seconds "$duration" >/dev/null || fail "unsupported duration: $duration"
done
[[ "$MIN_FREE_MB" =~ ^[0-9]+$ ]] || fail "--min-free-mb must be an integer"

print_heading "LocalCluster Actions runner residue cleanup"
discover_runner_roots
discover_protected_paths
print_report "Before cleanup"
print_protected_paths

FREE_BEFORE_MB="$(free_opt_mb)"
[[ "$FREE_BEFORE_MB" =~ ^[0-9]+$ ]] || fail "could not measure free /opt space before cleanup"
SHOULD_RUN_RETENTION="$FORCE"
if [[ "$FREE_BEFORE_MB" -lt "$MIN_FREE_MB" ]]; then
  SHOULD_RUN_RETENTION="true"
fi

if [[ "$SHOULD_RUN_RETENTION" == "true" ]]; then
  if [[ "${#RUNNER_ROOTS[@]}" -eq 0 ]]; then
    echo "no runner roots available for retention cleanup"
  else
    for runner_root in "${RUNNER_ROOTS[@]}"; do
      prune_runner_root "$runner_root"
    done
  fi
else
  echo "/opt has ${FREE_BEFORE_MB}MiB free; runner retention cleanup skipped. Use --force for routine scheduled maintenance."
fi

print_report "After cleanup"
printf 'Actions runner cleanup summary: removed=%s skipped=%s\n' "$REMOVED_COUNT" "$SKIPPED_COUNT"
assert_min_free_space

if [[ "$DEFER_IF_SKIPPED" == "true" && "$DEFERRED_COUNT" -gt 0 ]]; then
  echo "Actions runner cleanup deferred ${DEFERRED_COUNT} candidate(s) because ownership/activity prevented safe removal." >&2
  exit 75
fi

echo "LocalCluster Actions runner residue cleanup complete."
