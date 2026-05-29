#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-local}"

warn() {
  printf 'WARN  %s\n' "$*"
}

ok() {
  printf 'OK    %s\n' "$*"
}

info() {
  printf '%s\n' "$*"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

find_docker() {
  if command_exists docker && docker version >/dev/null 2>&1; then
    printf 'docker'
    return 0
  fi

  if command_exists docker.exe && docker.exe version >/dev/null 2>&1; then
    printf 'docker.exe'
    return 0
  fi

  return 1
}

print_linux_memory() {
  if [[ ! -r /proc/meminfo ]]; then
    return 1
  fi

  awk '
    /^MemTotal:/ { total=$2 }
    /^MemAvailable:/ { available=$2 }
    /^MemFree:/ { free=$2 }
    /^Buffers:/ { buffers=$2 }
    /^Cached:/ { cached=$2 }
    END {
      if (available == 0) {
        available = free + buffers + cached
      }
      if (total > 0) {
        used = total - available
        printf "  total:     %.1f GiB\n", total / 1024 / 1024
        printf "  available: %.1f GiB\n", available / 1024 / 1024
        printf "  used:      %.1f GiB\n", used / 1024 / 1024
      }
    }
  ' /proc/meminfo
}

print_windows_memory() {
  if ! command_exists powershell.exe; then
    return 1
  fi

  powershell.exe -NoLogo -NoProfile -Command '
    $os = Get-CimInstance Win32_OperatingSystem;
    $total = [double]$os.TotalVisibleMemorySize;
    $available = [double]$os.FreePhysicalMemory;
    $used = $total - $available;
    "  total:     {0:N1} GiB" -f ($total / 1MB);
    "  available: {0:N1} GiB" -f ($available / 1MB);
    "  used:      {0:N1} GiB" -f ($used / 1MB);
    ' 2>/dev/null
}

print_disk() {
  local path="${1:-.}"

  if command_exists df; then
    df -h "$path" | awk 'NR == 1 || NR == 2 { print "  " $0 }'
    return
  fi

  warn "df missing; disk report unavailable"
}

print_docker_summary() {
  local docker_bin

  if ! docker_bin="$(find_docker)"; then
    warn "docker command missing; Docker report unavailable"
    return
  fi

  ok "docker available: $("$docker_bin" version --format '{{.Client.Version}}' 2>/dev/null || printf 'version unknown')"

  if "$docker_bin" compose version >/dev/null 2>&1; then
    ok "docker compose available: $("$docker_bin" compose version --short 2>/dev/null || "$docker_bin" compose version)"
  else
    warn "docker compose unavailable"
  fi

  info ""
  info "Docker containers"
  if ! "$docker_bin" ps --format '  {{.Names}}\t{{.Status}}\t{{.Image}}'; then
    warn "could not list Docker containers"
  fi

  info ""
  info "Docker container resource snapshot"
  if ! "$docker_bin" stats --no-stream --format '  {{.Name}}\tCPU={{.CPUPerc}}\tMEM={{.MemUsage}}\tNET={{.NetIO}}\tBLOCK={{.BlockIO}}'; then
    warn "could not read Docker stats"
  fi

  info ""
  info "Local compose services"
  if [[ -f docker-compose.yml ]]; then
    "$docker_bin" compose ps --format '  {{.Name}}\t{{.Service}}\t{{.State}}\t{{.Status}}' 2>/dev/null || warn "local compose stack is not running"
  else
    warn "docker-compose.yml missing in current directory"
  fi
}

info "observability resource report"
info "target: ${TARGET}"
info "timestamp_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
info ""

info "Host memory"
if ! print_linux_memory && ! print_windows_memory; then
  warn "host memory report unavailable"
fi

info ""
info "Disk"
print_disk "."

info ""
print_docker_summary
