#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "actions runner prerequisite check failed: $*" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
command -v docker >/dev/null 2>&1 || fail "docker is missing"

needs_apt=0
need_python_venv=0
need_shellcheck=0
need_pwsh=0
python3 -m venv --help >/dev/null 2>&1 || need_python_venv=1
command -v shellcheck >/dev/null 2>&1 || need_shellcheck=1
command -v pwsh >/dev/null 2>&1 || need_pwsh=1
if [[ "$need_python_venv" == "1" || "$need_shellcheck" == "1" || "$need_pwsh" == "1" ]]; then
  needs_apt=1
fi

if [[ "$needs_apt" == "1" ]]; then
  command -v sudo >/dev/null 2>&1 || fail "sudo is missing"
  command -v apt-get >/dev/null 2>&1 || fail "apt-get is missing; this runner bootstrap expects Debian/Ubuntu/Linux Mint"
  if ! sudo -n true >/dev/null 2>&1; then
    fail "passwordless sudo is required to install missing self-hosted Actions runner prerequisites"
  fi

  sudo env DEBIAN_FRONTEND=noninteractive apt-get update
  if [[ "$need_pwsh" == "1" ]]; then
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl gnupg
  fi
fi

if [[ "$need_python_venv" == "1" ]]; then
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-venv
fi

if [[ "$need_shellcheck" == "1" ]]; then
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends shellcheck
fi

if [[ "$need_pwsh" == "1" ]]; then
  # Linux Mint reports its Mint version in VERSION_ID, so use the Ubuntu base codename.
  # node-main is currently Linux Mint 22.3 based on Ubuntu noble.
  # shellcheck disable=SC1091
  . /etc/os-release

  ubuntu_version=""
  case "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" in
    noble) ubuntu_version="24.04" ;;
    jammy) ubuntu_version="22.04" ;;
    focal) ubuntu_version="20.04" ;;
    *)
      fail "unsupported Ubuntu base codename: ${UBUNTU_CODENAME:-${VERSION_CODENAME:-unknown}}"
      ;;
  esac

  tmp="$(mktemp -d)"
  cleanup() {
    rm -rf "$tmp"
  }
  trap cleanup EXIT

  curl -fsSL -o "$tmp/packages-microsoft-prod.deb" \
    "https://packages.microsoft.com/config/ubuntu/${ubuntu_version}/packages-microsoft-prod.deb"
  sudo dpkg -i "$tmp/packages-microsoft-prod.deb"
  sudo env DEBIAN_FRONTEND=noninteractive apt-get update
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends powershell
fi

command -v shellcheck >/dev/null 2>&1 || fail "shellcheck is missing after install"
command -v pwsh >/dev/null 2>&1 || fail "pwsh is missing after install"
python3 -m venv --help >/dev/null 2>&1 || fail "python3 venv support is missing after install"
docker info >/dev/null || fail "docker is not reachable by the runner user"

echo "actions runner prerequisites ok"
pwsh -NoLogo -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
