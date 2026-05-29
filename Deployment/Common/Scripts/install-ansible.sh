#!/usr/bin/env bash
set -euo pipefail

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer expects a Debian, Ubuntu, or Linux Mint machine with apt-get." >&2
  exit 1
fi

sudo env DEBIAN_FRONTEND=noninteractive apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates openssh-client python3 python3-venv python3-pip sshpass

PYTHON_MINOR="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

if [[ -n "${ANSIBLE_CORE_VERSION:-}" ]]; then
  VERSION="$ANSIBLE_CORE_VERSION"
else
  case "$PYTHON_MINOR" in
    3.12|3.13|3.14) VERSION="2.21.0" ;;
    3.11) VERSION="2.19.4" ;;
    3.10) VERSION="2.17.14" ;;
    *)
      echo "Python $PYTHON_MINOR is too old for the pinned Ansible versions. Use Debian 12, Ubuntu 22.04, Linux Mint 21, or newer." >&2
      exit 1
      ;;
  esac
fi

INSTALL_ROOT="${ANSIBLE_INSTALL_ROOT:-$HOME/.local/share/books-ansible}"
BIN_DIR="${ANSIBLE_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$INSTALL_ROOT/ansible-core-$VERSION"

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"

if [[ -x "$VENV_DIR/bin/ansible-playbook" ]] && "$VENV_DIR/bin/ansible-playbook" --version 2>/dev/null | grep -q "\\[core $VERSION\\]"; then
  echo "ansible-core $VERSION already installed in $VENV_DIR"
else
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install "ansible-core==$VERSION"
fi

for exe in ansible ansible-config ansible-galaxy ansible-inventory ansible-playbook ansible-vault; do
  ln -sf "$VENV_DIR/bin/$exe" "$BIN_DIR/$exe"
  sudo ln -sf "$VENV_DIR/bin/$exe" "/usr/local/bin/$exe"
done

ansible-playbook --version
