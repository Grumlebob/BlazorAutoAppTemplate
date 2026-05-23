#!/usr/bin/env bash
set -euo pipefail

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer expects a Debian/Ubuntu/Linux Mint control machine with apt-get." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip pipx sshpass

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
      echo "Python $PYTHON_MINOR is too old for the pinned Ansible versions. Use Linux Mint 21 or newer." >&2
      exit 1
      ;;
  esac
fi

python3 -m pipx ensurepath
export PATH="$HOME/.local/bin:$PATH"

if [[ -x "$HOME/.local/bin/ansible-playbook" ]] && "$HOME/.local/bin/ansible-playbook" --version 2>/dev/null | grep -q "\\[core $VERSION\\]"; then
  echo "ansible-core $VERSION already installed"
else
  pipx install --include-deps --force "ansible-core==$VERSION"
fi

for exe in ansible ansible-config ansible-galaxy ansible-inventory ansible-playbook ansible-vault; do
  if [[ -x "$HOME/.local/bin/$exe" ]]; then
    sudo ln -sf "$HOME/.local/bin/$exe" "/usr/local/bin/$exe"
  fi
done

ansible-playbook --version
