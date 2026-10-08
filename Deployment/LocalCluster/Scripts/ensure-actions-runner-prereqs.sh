#!/usr/bin/env bash
set -euo pipefail

MODE="provision"
case "${1:-}" in
  "") ;;
  --check) MODE="check" ;;
  --provision) MODE="provision" ;;
  -h|--help)
    printf '%s\n' 'Usage: ensure-actions-runner-prereqs.sh [--check|--provision]' \
      '--check      inspect tools and Docker without apt, sudo, or mutation' \
      '--provision  install missing host packages (the historical no-argument mode)'
    exit 0
    ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac

fail() {
  echo "actions runner prerequisite check failed: $*" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
command -v docker >/dev/null 2>&1 || fail "docker is missing"

need_python_venv=0
need_shellcheck=0
need_pwsh=0
python3 -m venv --help >/dev/null 2>&1 || need_python_venv=1
command -v shellcheck >/dev/null 2>&1 || need_shellcheck=1
command -v pwsh >/dev/null 2>&1 || need_pwsh=1

if [[ "$MODE" == "check" ]]; then
  [[ "$need_python_venv" == "0" ]] || fail "python3-venv is missing; run --provision through host administration"
  [[ "$need_shellcheck" == "0" ]] || fail "shellcheck is missing; run --provision through host administration"
  [[ "$need_pwsh" == "0" ]] || fail "PowerShell is missing; run --provision through host administration"
  docker info >/dev/null || fail "docker is not reachable by the runner user"
  echo "actions runner prerequisites ok (check-only; no apt or sudo used)"
  pwsh -NoLogo -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
  exit 0
fi

needs_apt=0
[[ "$need_python_venv" == "1" || "$need_shellcheck" == "1" || "$need_pwsh" == "1" ]] && needs_apt=1
if [[ "$needs_apt" == "1" ]]; then
  command -v sudo >/dev/null 2>&1 || fail "sudo is missing"
  command -v apt-get >/dev/null 2>&1 || fail "apt-get is missing; this runner bootstrap expects Debian/Ubuntu/Linux Mint"
  sudo -n true >/dev/null 2>&1 || fail "passwordless sudo is required to install missing self-hosted Actions runner prerequisites"
  apt_timeout="${RUNNER_PREREQ_APT_TIMEOUT_SECONDS:-300}"
  apt_run() {
    local attempt
    for attempt in 1 2 3; do
      if timeout "$apt_timeout" sudo env DEBIAN_FRONTEND=noninteractive apt-get "$@"; then return 0; fi
      [[ "$attempt" -lt 3 ]] || break
      sleep $((attempt * 5))
    done
    return 1
  }
  apt_run update || fail "apt-get update did not complete within the provisioning deadline"
  if [[ "$need_pwsh" == "1" ]]; then
    apt_run install -y --no-install-recommends ca-certificates curl gnupg || \
      fail "could not install PowerShell repository prerequisites"
  fi
fi

if [[ "$need_python_venv" == "1" ]]; then
  apt_run install -y --no-install-recommends python3-venv || fail "could not install python3-venv"
fi
if [[ "$need_shellcheck" == "1" ]]; then
  apt_run install -y --no-install-recommends shellcheck || fail "could not install shellcheck"
fi
if [[ "$need_pwsh" == "1" ]]; then
  # Linux Mint reports its Mint version in VERSION_ID, so use the Ubuntu base codename.
  # shellcheck disable=SC1091
  . /etc/os-release
  case "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" in
    noble) ubuntu_version="24.04" ;;
    jammy) ubuntu_version="22.04" ;;
    focal) ubuntu_version="20.04" ;;
    *) fail "unsupported Ubuntu base codename: ${UBUNTU_CODENAME:-${VERSION_CODENAME:-unknown}}" ;;
  esac
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/pwsh-repo.XXXXXX")"
  cleanup() { rm -rf "$tmp"; }
  trap cleanup EXIT
  curl --fail --silent --show-error --location --connect-timeout 10 --max-time 60 \
    --output "$tmp/packages-microsoft-prod.deb" \
    "https://packages.microsoft.com/config/ubuntu/${ubuntu_version}/packages-microsoft-prod.deb"
  sudo dpkg -i "$tmp/packages-microsoft-prod.deb"
  apt_run update || fail "PowerShell repository update did not complete"
  apt_run install -y --no-install-recommends powershell || fail "could not install PowerShell"
fi

command -v shellcheck >/dev/null 2>&1 || fail "shellcheck is missing after install"
command -v pwsh >/dev/null 2>&1 || fail "pwsh is missing after install"
python3 -m venv --help >/dev/null 2>&1 || fail "python3 venv support is missing after install"
docker info >/dev/null || fail "docker is not reachable by the runner user"
echo "actions runner prerequisites ok (provisioned only when required)"
pwsh -NoLogo -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
