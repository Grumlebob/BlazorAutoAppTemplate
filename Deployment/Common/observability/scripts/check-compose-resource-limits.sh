#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="obs-resource-limit-check"
IMAGE="${OBS_RESOURCE_LIMIT_TEST_IMAGE:-alpine:3.23}"
MEMORY_LIMIT_BYTES=67108864
CPU_LIMIT_NANOS=250000000
DOCKER_BIN=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
TMP_ROOT="$REPO_ROOT/.tmp/observability"
mkdir -p "$TMP_ROOT"
TMP_DIR="$(mktemp -d "$TMP_ROOT/resource-limit.XXXXXX")"
COMPOSE_FILE="$TMP_DIR/docker-compose.yml"
DOCKER_COMPOSE_FILE="$COMPOSE_FILE"

cleanup() {
  if [[ -n "$DOCKER_BIN" ]]; then
    "$DOCKER_BIN" compose -p "$PROJECT_NAME" -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
  rmdir "$TMP_ROOT" >/dev/null 2>&1 || true
  rmdir "$REPO_ROOT/.tmp" >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

ok() {
  printf 'OK    %s\n' "$*"
}

find_docker() {
  if command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1; then
    printf 'docker'
    return 0
  fi

  if command -v docker.exe >/dev/null 2>&1 && docker.exe version >/dev/null 2>&1; then
    printf 'docker.exe'
    return 0
  fi

  return 1
}

DOCKER_BIN="$(find_docker)" || fail "docker is missing or cannot reach Docker Desktop"
"$DOCKER_BIN" compose version >/dev/null 2>&1 || fail "docker compose is missing"
"$DOCKER_BIN" info >/dev/null 2>&1 || fail "Docker daemon is not reachable"

cat > "$COMPOSE_FILE" <<EOF
services:
  memlimit-check:
    image: ${IMAGE}
    command: ["sh", "-c", "sleep 60"]
    mem_limit: "64m"
    mem_reservation: "32m"
    cpus: "0.25"
EOF

if [[ "$DOCKER_BIN" == *".exe" ]]; then
  command -v wslpath >/dev/null 2>&1 || fail "wslpath is required when using docker.exe from WSL"
  DOCKER_COMPOSE_FILE="$(wslpath -w "$COMPOSE_FILE")"
fi

"$DOCKER_BIN" compose -p "$PROJECT_NAME" -f "$DOCKER_COMPOSE_FILE" config --quiet
"$DOCKER_BIN" compose -p "$PROJECT_NAME" -f "$DOCKER_COMPOSE_FILE" up -d --quiet-pull >/dev/null 2>&1

CONTAINER_ID="$("$DOCKER_BIN" compose -p "$PROJECT_NAME" -f "$DOCKER_COMPOSE_FILE" ps -q memlimit-check)"
[[ -n "$CONTAINER_ID" ]] || fail "test container did not start"

MEMORY_VALUE="$("$DOCKER_BIN" inspect "$CONTAINER_ID" --format '{{.HostConfig.Memory}}')"
MEMORY_RESERVATION_VALUE="$("$DOCKER_BIN" inspect "$CONTAINER_ID" --format '{{.HostConfig.MemoryReservation}}')"
CPU_VALUE="$("$DOCKER_BIN" inspect "$CONTAINER_ID" --format '{{.HostConfig.NanoCpus}}')"

[[ "$MEMORY_VALUE" == "$MEMORY_LIMIT_BYTES" ]] || fail "expected memory limit ${MEMORY_LIMIT_BYTES}, got ${MEMORY_VALUE}"
[[ "$MEMORY_RESERVATION_VALUE" -gt 0 ]] || fail "memory reservation was not applied"
[[ "$CPU_VALUE" == "$CPU_LIMIT_NANOS" ]] || fail "expected CPU limit ${CPU_LIMIT_NANOS}, got ${CPU_VALUE}"

ok "Docker Compose enforces mem_limit, mem_reservation, and cpus"
ok "memory_limit_bytes=${MEMORY_VALUE}"
ok "memory_reservation_bytes=${MEMORY_RESERVATION_VALUE}"
ok "cpu_limit_nanos=${CPU_VALUE}"
