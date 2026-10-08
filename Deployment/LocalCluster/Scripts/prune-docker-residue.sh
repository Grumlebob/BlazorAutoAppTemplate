#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../.." && pwd)"

DRY_RUN="false"
FORCE="false"
MIN_FREE_MB="20480"
CONTAINER_UNTIL="24h"
DANGLING_IMAGE_UNTIL="168h"
LOCALCLUSTER_IMAGE_UNTIL="168h"
LOW_DISK_LOCALCLUSTER_IMAGE_UNTIL="0h"
BUILDER_UNTIL="48h"
LOW_DISK_BUILDER_UNTIL="0h"
ALLOW_SHARED_BUILDER_PRUNE="false"
NETWORK_UNTIL="24h"
INCLUDE_UNLABELLED_HOST_RESIDUE="false"
# Dangling images labelled by this repository's CI are always safe to prune.
CI_REPOSITORY="${LOCALCLUSTER_CI_REPOSITORY:-${GITHUB_REPOSITORY:-}}"
REMOVE_IMAGES=()
PROTECT_IMAGES=()
PROTECTED_DATA_PATHS=()
PROTECTED_IMAGE_REFS=()
PROTECTED_IMAGE_IDS=()
DATA_RUNNER_IMAGE_REFS=()
CANDIDATE_IMAGE_REPOSITORIES=()
DEFERRED_COUNT=0
DEFER_IF_SKIPPED="false"

usage() {
  cat >&2 <<'USAGE'
usage: prune-docker-residue.sh [options]

Safely prunes routine LocalCluster Docker residue on LocalCluster nodes.

Options:
  --dry-run                         Print commands without mutating Docker state.
  --force                           Run retention cleanup even when /opt already has enough free space.
  --min-free-mb <mb>                Required free /opt space after cleanup. Default: 20480.
  --dangling-image-until <duration> Dangling image retention. Default: 168h.
  --localcluster-image-until <duration>
                                    Old unprotected LocalCluster app-image retention. Default: 168h.
  --low-disk-localcluster-image-until <duration>
                                    Extra app-image retention when still below --min-free-mb.
                                    Default: 0h.
  --builder-until <duration>        Build cache retention. Default: 48h.
  --low-disk-builder-until <duration>
                                    Extra build cache retention when still below --min-free-mb.
                                    Default: 0h.
  --allow-shared-builder-prune     Permit mutation of the host-wide BuildKit cache. Default: off.
  --defer-if-skipped                Return 75 when ownership prevents a requested safe removal.
  --include-unlabelled-host-residue Also run host-wide prunes of stopped containers, dangling
                                    images, build cache and unused networks. These affect every
                                    app on this Docker daemon; use only in reviewed maintenance.
  --container-until <duration>      Stopped container retention for host-wide prunes. Default: 24h.
  --network-until <duration>        Unused network retention for host-wide prunes. Default: 24h.
  --remove-image <image:tag>        Remove a specific image tag unless it is protected.
  --protect-image <image:tag>       Add an image tag to the protected set.
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
  local -n target="$1"
  local value="${2:-}"
  [[ -n "$value" ]] || return 0
  array_contains "$value" "${target[@]}" && return 0

  target+=("$value")
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

read_env_value() {
  local env_file="$1"
  local key="$2"
  [[ -f "$env_file" ]] || return 0

  awk -F= -v key="$key" '
    $1 == key {
      value = substr($0, length(key) + 2)
      sub(/\r$/, "", value)
      print value
      found = 1
      exit
    }
    END { if (!found) exit 1 }
  ' "$env_file" 2>/dev/null || true
}

setting_value() {
  local script="$1"
  local key="$2"
  if [[ -x "$script" || -f "$script" ]]; then
    bash "$script" "$key" 2>/dev/null || true
  fi
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
  df -Pm /opt | awk 'NR == 2 { print $4 }'
}

print_heading() {
  printf '\n== %s ==\n' "$1"
}

print_report() {
  local label="$1"
  print_heading "$label"
  printf 'mode: %s\n' "$([[ "$DRY_RUN" == "true" ]] && echo "dry-run" || echo "apply")"
  printf 'force: %s\n' "$FORCE"
  printf 'hostname: %s\n' "$(hostname)"
  printf 'whoami: %s\n' "$(whoami)"

  if [[ -d /opt ]]; then
    df -h / /opt
    df -Pi / /opt
  else
    echo "/opt does not exist on this host; showing / only"
    df -h /
    df -Pi /
  fi

  if command -v docker >/dev/null 2>&1; then
    local docker_root
    docker_root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
    if [[ -n "$docker_root" && -e "$docker_root" ]]; then
      printf 'DockerRootDir: %s\n' "$docker_root"
      df -h "$docker_root"
      df -Pi "$docker_root"
    fi
    docker system df || true
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" || true
  else
    echo "docker command is not available"
  fi
}

require_docker() {
  command -v docker >/dev/null 2>&1 || fail "missing required command: docker"
  docker info >/dev/null
}

print_list() {
  local empty_message="$1"
  shift
  if [[ "$#" -eq 0 ]]; then
    printf '  %s\n' "$empty_message"
    return 0
  fi

  local item
  for item in "$@"; do
    printf '  - %s\n' "$item"
  done
}

add_repository_from_image_ref() {
  local image_ref="$1"
  [[ -n "$image_ref" ]] || return 0
  [[ "$image_ref" != sha256:* ]] || return 0

  local last_component="${image_ref##*/}"
  local repository="$image_ref"
  if [[ "$last_component" == *:* ]]; then
    repository="${image_ref%:*}"
  fi

  [[ -n "$repository" ]] || return 0
  add_unique CANDIDATE_IMAGE_REPOSITORIES "$repository"
}

discover_protected_data_paths() {
  local deploy_source_root deploy_runner_root
  deploy_source_root="$(setting_value "$SCRIPT_DIR/read-deploy-setting.sh" data_import_source_root_host)"
  deploy_runner_root="$(setting_value "$SCRIPT_DIR/read-deploy-setting.sh" data_import_data_runner_root)"
  add_unique PROTECTED_DATA_PATHS "$deploy_source_root"
  add_unique PROTECTED_DATA_PATHS "$deploy_runner_root"

  shopt -s nullglob
  local env_file source_root runner_root
  for env_file in /opt/*/data-runner/.env; do
    [[ -r "$env_file" ]] || fail "deployed data-runner environment is unreadable: $env_file"
    add_unique PROTECTED_DATA_PATHS "$(dirname "$env_file")"
    source_root="$(read_env_value "$env_file" DATA_IMPORT_SOURCE_ROOT_HOST)"
    runner_root="$(read_env_value "$env_file" DATA_IMPORT_DATA_RUNNER_ROOT)"
    add_unique PROTECTED_DATA_PATHS "$source_root"
    add_unique PROTECTED_DATA_PATHS "$runner_root"
  done
  shopt -u nullglob
}

discover_protected_images() {
  local container_images
  if ! container_images="$(docker ps -a --format '{{.Image}}')"; then
    fail "could not inspect Docker containers for protection; refusing image cleanup"
  fi

  local running_image
  while IFS= read -r running_image; do
    add_unique PROTECTED_IMAGE_REFS "$running_image"
  done <<< "$container_images"

  shopt -s nullglob
  local env_file app_image app_version image_ref image_id
  for env_file in /opt/*/data-runner/.env; do
    [[ -r "$env_file" ]] || fail "deployed data-runner environment is unreadable: $env_file"
    echo "inspecting deployed data-runner env: $env_file"
    app_image="$(read_env_value "$env_file" APP_IMAGE)"
    app_version="$(read_env_value "$env_file" APP_VERSION)"
    if [[ -n "$app_image" && -n "$app_version" ]]; then
      image_ref="${app_image}:${app_version}"
      add_unique PROTECTED_IMAGE_REFS "$image_ref"
      add_unique DATA_RUNNER_IMAGE_REFS "$image_ref"
    else
      fail "$env_file does not contain both APP_IMAGE and APP_VERSION; refusing image cleanup"
    fi
  done
  shopt -u nullglob

  if [[ -n "${APP_IMAGE:-}" ]]; then
    add_repository_from_image_ref "$APP_IMAGE"
  fi
  if [[ -n "${APP_IMAGE:-}" && -n "${APP_VERSION:-}" ]]; then
    add_unique PROTECTED_IMAGE_REFS "${APP_IMAGE}:${APP_VERSION}"
  fi

  local release_image
  release_image="$(setting_value "$REPO_ROOT/Deployment/Common/Scripts/read-release-setting.sh" app_image)"
  add_repository_from_image_ref "$release_image"

  for image_ref in "${PROTECT_IMAGES[@]}"; do
    add_unique PROTECTED_IMAGE_REFS "$image_ref"
  done

  for image_ref in "${PROTECTED_IMAGE_REFS[@]}"; do
    if image_id="$(docker image inspect --format '{{.Id}}' "$image_ref" 2>/dev/null)"; then
      add_unique PROTECTED_IMAGE_IDS "$image_id"
    elif array_contains "$image_ref" "${DATA_RUNNER_IMAGE_REFS[@]}"; then
      echo "warning: deployed data-runner image ref is not present locally: $image_ref" >&2
    else
      echo "note: protected image ref is not present locally: $image_ref"
    fi
  done
}

is_protected_image() {
  local image_ref="$1"
  local image_id="${2:-}"
  local protected

  for protected in "${PROTECTED_IMAGE_REFS[@]}"; do
    [[ "$image_ref" != "$protected" ]] || return 0
  done

  if [[ -z "$image_id" ]]; then
    image_id="$(docker image inspect --format '{{.Id}}' "$image_ref" 2>/dev/null || true)"
  fi

  for protected in "${PROTECTED_IMAGE_IDS[@]}"; do
    image_ids_match "$image_id" "$protected" && return 0
  done

  return 1
}

normalize_image_id() {
  local image_id="${1#sha256:}"
  [[ "$image_id" =~ ^[0-9a-f]{12,64}$ ]] || return 1
  printf '%s\n' "$image_id"
}

image_ids_match() {
  local left right
  left="$(normalize_image_id "$1")" || return 1
  right="$(normalize_image_id "$2")" || return 1

  [[ "$left" == "$right" || "$left" == "$right"* || "$right" == "$left"* ]]
}

valid_image_ref() {
  local image_ref="$1"
  [[ -n "$image_ref" ]] || return 1
  [[ "$image_ref" != ":" ]] || return 1
  [[ "$image_ref" != "<none>" && "$image_ref" != "<none>:<none>" ]] || return 1
  [[ "$image_ref" != :* ]] || return 1
  [[ "$image_ref" != *: ]] || return 1
  [[ "$image_ref" != *[[:space:]]* ]] || return 1

  if [[ "$image_ref" == *@sha256:* ]]; then
    [[ "$image_ref" =~ @sha256:[0-9a-f]{64}$ ]]
    return
  fi

  local last_component="${image_ref##*/}"
  [[ "$last_component" == *:* ]] || return 1
  [[ -n "${last_component##*:}" ]] || return 1
}

remove_image_if_requested() {
  local image_ref="$1"
  if ! valid_image_ref "$image_ref"; then
    echo "skip invalid or empty --remove-image value: ${image_ref:-<empty>}"
    return 0
  fi

  local image_id
  image_id="$(docker image inspect --format '{{.Id}}' "$image_ref" 2>/dev/null || true)"
  if [[ -z "$image_id" ]]; then
    echo "skip missing requested image: $image_ref"
    return 0
  fi

  if is_protected_image "$image_ref" "$image_id"; then
    echo "skip protected image: $image_ref"
    DEFERRED_COUNT=$((DEFERRED_COUNT + 1))
    return 0
  fi

  local current_image_id
  current_image_id="$(docker image inspect --format '{{.Id}}' "$image_ref" 2>/dev/null || true)"
  if [[ -z "$current_image_id" ]]; then
    echo "skip image removed before requested cleanup: $image_ref"
    return 0
  fi
  if [[ "$current_image_id" != "$image_id" ]]; then
    echo "skip image changed during requested cleanup: $image_ref"
    return 0
  fi

  run_or_print docker image rm "$image_ref"
}

repository_is_candidate() {
  local repository="$1"
  local candidate
  for candidate in "${CANDIDATE_IMAGE_REPOSITORIES[@]}"; do
    [[ "$repository" != "$candidate" ]] || return 0
  done
  return 1
}

prune_old_unprotected_localcluster_images() {
  local retention="${1:-$LOCALCLUSTER_IMAGE_UNTIL}"
  if [[ "${#CANDIDATE_IMAGE_REPOSITORIES[@]}" -eq 0 ]]; then
    echo "no LocalCluster image repositories discovered for old tag cleanup"
    return 0
  fi

  local retention_seconds
  retention_seconds="$(duration_seconds "$retention")" \
    || fail "unsupported LocalCluster image retention duration: $retention"
  local cutoff_epoch=$(( $(date -u +%s) - retention_seconds ))

  # Process substitution would discard the inventory command's exit status,
  # including a daemon failure after it emitted a partial list.
  local inventory
  inventory="$(docker image ls --no-trunc --format '{{.ID}}\t{{.Repository}}\t{{.Tag}}')" \
    || fail "could not inventory Docker images; refusing retention cleanup"
  local id repository tag image_ref created created_epoch current_id
  while IFS=$'\t' read -r id repository tag; do
    [[ -n "$id" && -n "$repository" && -n "$tag" ]] || continue
    [[ "$repository" != "<none>" && "$tag" != "<none>" ]] || continue
    repository_is_candidate "$repository" || continue

    image_ref="${repository}:${tag}"
    if is_protected_image "$image_ref" "$id"; then
      echo "skip protected image: $image_ref"
      continue
    fi

    created="$(docker image inspect --format '{{.Created}}' "$image_ref" 2>/dev/null || true)"
    [[ -n "$created" ]] || continue
    created_epoch="$(date -u -d "$created" +%s 2>/dev/null || true)"
    [[ -n "$created_epoch" ]] || {
      echo "warning: could not parse image creation time for $image_ref: $created" >&2
      continue
    }

    if [[ "$created_epoch" -lt "$cutoff_epoch" ]]; then
      current_id="$(docker image inspect --format '{{.Id}}' "$image_ref" 2>/dev/null || true)"
      if [[ -z "$current_id" ]]; then
        echo "skip image removed before retention cleanup: $image_ref"
      elif ! image_ids_match "$current_id" "$id"; then
        echo "skip image changed during retention cleanup: $image_ref"
      else
        run_or_print docker image rm "$image_ref"
      fi
    fi
  done <<< "$inventory"
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

  echo "Docker cleanup completed, but /opt is still below threshold; investigate non-Docker disk usage." >&2
  echo "/opt free disk is ${free_mb}MiB; required minimum is ${MIN_FREE_MB}MiB." >&2
  echo "Suggested read-only checks:" >&2
  echo "  du -xh --max-depth=1 /opt | sort -h" >&2
  echo "  inspect runner work directories, logs, database backups, LocalData, and unexpected non-Docker files" >&2
  exit 2
}

prune_low_disk_localcluster_images_if_needed() {
  [[ "$MIN_FREE_MB" =~ ^[0-9]+$ ]] || fail "--min-free-mb must be an integer"
  [[ "$MIN_FREE_MB" -gt 0 ]] || return 0

  local free_mb
  free_mb="$(free_opt_mb)"
  [[ "$free_mb" =~ ^[0-9]+$ ]] || fail "could not measure free /opt space"
  if [[ "$free_mb" -ge "$MIN_FREE_MB" ]]; then
    return 0
  fi

  echo "/opt has ${free_mb}MiB free after routine Docker cleanup; pruning additional unused LocalCluster app images with until=${LOW_DISK_LOCALCLUSTER_IMAGE_UNTIL}."
  prune_old_unprotected_localcluster_images "$LOW_DISK_LOCALCLUSTER_IMAGE_UNTIL"
}

prune_low_disk_builder_cache_if_needed() {
  [[ "$MIN_FREE_MB" =~ ^[0-9]+$ ]] || fail "--min-free-mb must be an integer"
  [[ "$MIN_FREE_MB" -gt 0 ]] || return 0

  local free_mb
  free_mb="$(free_opt_mb)"
  [[ "$free_mb" =~ ^[0-9]+$ ]] || fail "could not measure free /opt space"
  if [[ "$free_mb" -ge "$MIN_FREE_MB" ]]; then
    return 0
  fi

  echo "/opt has ${free_mb}MiB free after routine Docker cleanup; pruning additional unused builder cache with until=${LOW_DISK_BUILDER_UNTIL}."
  run_or_print docker builder prune -af --filter "until=${LOW_DISK_BUILDER_UNTIL}"
}

print_protected_state() {
  print_heading "Protected host paths"
  print_list "no protected host paths discovered" "${PROTECTED_DATA_PATHS[@]}"

  print_heading "Protected image refs"
  print_list "no protected image refs discovered" "${PROTECTED_IMAGE_REFS[@]}"

  print_heading "Protected image ids"
  print_list "no protected image ids resolved locally" "${PROTECTED_IMAGE_IDS[@]}"

  print_heading "Candidate LocalCluster image repositories"
  print_list "no candidate repositories discovered" "${CANDIDATE_IMAGE_REPOSITORIES[@]}"
}

print_not_touched() {
  print_heading "Not touched"
  echo "Docker volumes are protected and were not pruned."
  echo "Host data paths were only reported, never deleted:"
  print_list "no protected host paths discovered" "${PROTECTED_DATA_PATHS[@]}"
  echo "Protected image refs:"
  print_list "no protected image refs discovered" "${PROTECTED_IMAGE_REFS[@]}"
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
    --dangling-image-until)
      [[ $# -ge 2 ]] || fail "--dangling-image-until requires a value"
      DANGLING_IMAGE_UNTIL="$2"
      shift 2
      ;;
    --localcluster-image-until)
      [[ $# -ge 2 ]] || fail "--localcluster-image-until requires a value"
      LOCALCLUSTER_IMAGE_UNTIL="$2"
      shift 2
      ;;
    --low-disk-localcluster-image-until)
      [[ $# -ge 2 ]] || fail "--low-disk-localcluster-image-until requires a value"
      LOW_DISK_LOCALCLUSTER_IMAGE_UNTIL="$2"
      shift 2
      ;;
    --builder-until)
      [[ $# -ge 2 ]] || fail "--builder-until requires a value"
      BUILDER_UNTIL="$2"
      shift 2
      ;;
    --low-disk-builder-until)
      [[ $# -ge 2 ]] || fail "--low-disk-builder-until requires a value"
      LOW_DISK_BUILDER_UNTIL="$2"
      shift 2
      ;;
    --allow-shared-builder-prune)
      ALLOW_SHARED_BUILDER_PRUNE="true"
      shift
      ;;
    --defer-if-skipped)
      DEFER_IF_SKIPPED="true"
      shift
      ;;
    --include-unlabelled-host-residue)
      INCLUDE_UNLABELLED_HOST_RESIDUE="true"
      shift
      ;;
    --container-until)
      [[ $# -ge 2 ]] || fail "--container-until requires a value"
      CONTAINER_UNTIL="$2"
      shift 2
      ;;
    --network-until)
      [[ $# -ge 2 ]] || fail "--network-until requires a value"
      NETWORK_UNTIL="$2"
      shift 2
      ;;
    --remove-image)
      [[ $# -ge 2 ]] || fail "--remove-image requires a value"
      REMOVE_IMAGES+=("$2")
      shift 2
      ;;
    --protect-image)
      [[ $# -ge 2 ]] || fail "--protect-image requires a value"
      PROTECT_IMAGES+=("$2")
      shift 2
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

for duration in "$CONTAINER_UNTIL" "$DANGLING_IMAGE_UNTIL" "$LOCALCLUSTER_IMAGE_UNTIL" "$LOW_DISK_LOCALCLUSTER_IMAGE_UNTIL" "$BUILDER_UNTIL" "$LOW_DISK_BUILDER_UNTIL" "$NETWORK_UNTIL"; do
  duration_seconds "$duration" >/dev/null || fail "unsupported duration: $duration"
done
[[ "$MIN_FREE_MB" =~ ^[0-9]+$ ]] || fail "--min-free-mb must be an integer"

print_heading "LocalCluster Docker residue cleanup"
echo "repository root: $REPO_ROOT"
print_report "Before cleanup"
require_docker

discover_protected_data_paths
discover_protected_images
print_protected_state

FREE_BEFORE_MB="$(free_opt_mb)"
[[ "$FREE_BEFORE_MB" =~ ^[0-9]+$ ]] || fail "could not measure free /opt space before cleanup"
SHOULD_RUN_RETENTION="$FORCE"
if [[ "$FREE_BEFORE_MB" -lt "$MIN_FREE_MB" ]]; then
  SHOULD_RUN_RETENTION="true"
fi
if [[ "${#REMOVE_IMAGES[@]}" -gt 0 ]]; then
  SHOULD_RUN_RETENTION="true"
fi

for image_ref in "${REMOVE_IMAGES[@]}"; do
  remove_image_if_requested "$image_ref"
done

if [[ "$SHOULD_RUN_RETENTION" == "true" ]]; then
  # node-main's Docker daemon is shared by every app on the cluster. Only
  # dangling images labelled by this repository's CI are eligible here; CI
  # containers and networks are removed by prune-ci-residue.py, which checks
  # that their run attempt has finished.
  if [[ -n "$CI_REPOSITORY" ]]; then
    run_or_print docker image prune -f \
      --filter "label=localcluster.ci.repository=${CI_REPOSITORY}" \
      --filter "until=${DANGLING_IMAGE_UNTIL}"
  else
    echo "no CI repository known (GITHUB_REPOSITORY or LOCALCLUSTER_CI_REPOSITORY); skipping labelled CI image prune"
  fi
  prune_old_unprotected_localcluster_images
  if [[ "$INCLUDE_UNLABELLED_HOST_RESIDUE" == "true" ]]; then
    echo "warning: host-wide prunes requested; they affect every app on this Docker daemon" >&2
    run_or_print docker container prune -f --filter "until=${CONTAINER_UNTIL}"
    run_or_print docker image prune -f --filter "until=${DANGLING_IMAGE_UNTIL}"
    run_or_print docker network prune -f --filter "until=${NETWORK_UNTIL}"
  else
    echo "host-wide container/image/network prunes skipped; pass --include-unlabelled-host-residue to run them"
  fi
  if [[ "$ALLOW_SHARED_BUILDER_PRUNE" == "true" || "$INCLUDE_UNLABELLED_HOST_RESIDUE" == "true" ]]; then
    run_or_print docker builder prune -af --filter "until=${BUILDER_UNTIL}"
  else
    echo "skipping host-wide BuildKit cache mutation; pass --allow-shared-builder-prune only on an isolated runner"
  fi
  prune_low_disk_localcluster_images_if_needed
  if [[ "$ALLOW_SHARED_BUILDER_PRUNE" == "true" || "$INCLUDE_UNLABELLED_HOST_RESIDUE" == "true" ]]; then
    prune_low_disk_builder_cache_if_needed
  fi
else
  echo "/opt has ${FREE_BEFORE_MB}MiB free; retention cleanup skipped. Use --force for routine scheduled maintenance."
fi

print_report "After cleanup"
print_not_touched
assert_min_free_space

if [[ "$DEFER_IF_SKIPPED" == "true" && "$DEFERRED_COUNT" -gt 0 ]]; then
  echo "Docker cleanup deferred ${DEFERRED_COUNT} protected candidate(s); no unsafe removal was attempted." >&2
  exit 75
fi

echo "LocalCluster Docker residue cleanup complete."
