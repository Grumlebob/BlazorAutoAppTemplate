#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This setup script expects an apt-based Linux shell such as Ubuntu, Debian, or WSL Ubuntu." >&2
  echo "Use WSL Ubuntu for this guide, or install the required tools manually from the linked official docs." >&2
  exit 1
fi

if ((EUID == 0)); then
  SUDO=()
else
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required when this script is not run as root." >&2
    exit 1
  fi
  SUDO=(sudo)
fi

run_sudo() {
  "${SUDO[@]}" "$@"
}

apt_install() {
  run_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
}

install_base_packages() {
  run_sudo apt-get update
  apt_install \
    bash \
    ca-certificates \
    curl \
    git \
    gnupg \
    jq \
    openssh-client \
    openssl \
    python3 \
    python3-pip \
    python3-venv \
    shellcheck \
    sudo \
    yamllint
}

install_github_cli() {
  if command -v gh >/dev/null 2>&1; then
    return
  fi

  run_sudo install -d -m 0755 /etc/apt/keyrings

  local key_file
  key_file="$(mktemp)"
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o "$key_file"
  run_sudo install -m 0644 "$key_file" /etc/apt/keyrings/githubcli-archive-keyring.gpg
  rm -f "$key_file"

  local arch
  arch="$(dpkg --print-architecture)"
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\n' "$arch" \
    | run_sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null

  run_sudo apt-get update
  apt_install gh
}

install_opentofu() {
  if command -v tofu >/dev/null 2>&1; then
    return
  fi

  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' RETURN

  curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh -o "$tmpdir/install-opentofu.sh"
  chmod +x "$tmpdir/install-opentofu.sh"
  run_sudo "$tmpdir/install-opentofu.sh" --install-method deb
}

install_base_packages
install_github_cli
install_opentofu

bash "$REPO_ROOT/Deployment/Common/Scripts/install-ansible.sh"

if ! gh auth status >/dev/null 2>&1; then
  if [[ "${SKIP_GH_LOGIN:-}" == "1" ]]; then
    echo "GitHub CLI is installed but not authenticated. Run: gh auth login" >&2
  else
    echo "GitHub CLI is installed but not authenticated. Starting gh auth login."
    gh auth login
  fi
fi

bash "$SCRIPT_DIR/check-currentpc-tools.sh"
