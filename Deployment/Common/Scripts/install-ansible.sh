#!/usr/bin/env bash
set -euo pipefail

# Routine jobs use --check. Provisioning is explicit (the no-argument form is
# retained for existing control-machine and Cloud setup callers).
MODE="provision"
USER_ONLY=false
for option in "$@"; do
  case "$option" in
    --check) MODE="check" ;;
    --provision) MODE="provision" ;;
    --user-only) USER_ONLY=true ;;
    -h|--help)
      echo 'Usage: install-ansible.sh [--check|--provision] [--user-only]'
      echo '--user-only requires installed prerequisites; no sudo, apt or global links.'
      exit 0
      ;;
    *) echo "Unknown option: $option" >&2; exit 2 ;;
  esac
done
[[ "$USER_ONLY" != true || "$MODE" == provision ]] || {
  echo '--user-only requires provisioning mode.' >&2; exit 2;
}

fail() { echo "Ansible setup failed: $*" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
command -v timeout >/dev/null 2>&1 || fail "timeout is required for bounded Ansible provisioning"

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
    *) fail "Python $PYTHON_MINOR is too old for the pinned Ansible versions" ;;
  esac
fi

INSTALL_ROOT="${ANSIBLE_INSTALL_ROOT:-$HOME/.local/share/books-ansible}"
BIN_DIR="${ANSIBLE_BIN_DIR:-$HOME/.local/bin}"
VERSION_DIR="$INSTALL_ROOT/ansible-core-$VERSION"
CURRENT_LINK="$INSTALL_ROOT/current"

version_is_valid() {
  local root="$1"
  [[ -f "$root/.ready" ]] || return 1
  executable_version_is_valid "$root"
}

executable_version_is_valid() {
  local root="$1"
  [[ -x "$root/bin/ansible-playbook" ]] || return 1
  "$root/bin/ansible-playbook" --version 2>/dev/null | grep -Fq "[core $VERSION]"
}

check_venv_creation() {
  local temp_root
  temp_root="$(mktemp -d "${TMPDIR:-/tmp}/ansible-venv-check.XXXXXX")"
  if ! python3 -m venv "$temp_root/venv" >/dev/null 2>&1; then
    rm -rf -- "$temp_root"
    fail "python3 -m venv cannot create a temporary environment"
  fi
  if [[ ! -x "$temp_root/venv/bin/python" ]]; then
    rm -rf -- "$temp_root"
    fail "temporary venv has no Python executable"
  fi
  rm -rf -- "$temp_root"
}

check_generation() {
  local root=""
  if [[ -L "$CURRENT_LINK" || -d "$CURRENT_LINK" ]]; then
    root="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
  fi
  [[ -n "$root" ]] || fail "no ready Ansible $VERSION generation at $CURRENT_LINK"
  version_is_valid "$root" || fail "Ansible generation is missing, incomplete, or has the wrong version: $root"
  for exe in ansible ansible-config ansible-galaxy ansible-inventory ansible-playbook ansible-vault; do
    [[ -x "$root/bin/$exe" ]] || fail "Ansible executable is missing: $root/bin/$exe"
  done
  check_venv_creation
  printf 'ansible-core %s ready at %s\n' "$VERSION" "$root"
  "$root/bin/ansible-playbook" --version
}

if [[ "$MODE" == "check" ]]; then
  check_generation
  exit 0
fi

if [[ "$USER_ONLY" != true ]]; then
  command -v apt-get >/dev/null 2>&1 || fail "this installer expects apt-get"
  command -v sudo >/dev/null 2>&1 || fail "sudo is required for provisioning"
  sudo -n true >/dev/null 2>&1 || fail "passwordless sudo is required for provisioning"
fi
mkdir -p "$INSTALL_ROOT" "$BIN_DIR"

LOCK_FILE="$INSTALL_ROOT/.install.lock"
exec 9>"$LOCK_FILE"
command -v flock >/dev/null 2>&1 || fail "flock is required to serialize Ansible provisioning"
flock -w "${ANSIBLE_INSTALL_LOCK_TIMEOUT_SECONDS:-300}" 9 || fail "another Ansible provisioner holds $LOCK_FILE"

need_packages=()
command -v ssh >/dev/null 2>&1 || need_packages+=(openssh-client)
command -v sshpass >/dev/null 2>&1 || need_packages+=(sshpass)
python3 -m venv --help >/dev/null 2>&1 || need_packages+=(python3-venv)
python3 -m pip --version >/dev/null 2>&1 || need_packages+=(python3-pip)
if ((${#need_packages[@]} > 0)); then
  [[ "$USER_ONLY" != true ]] || fail "--user-only requires preinstalled prerequisites: ${need_packages[*]}"
  mapfile -t need_packages < <(printf '%s\n' "${need_packages[@]}" | awk '!seen[$0]++')
  apt_timeout="${ANSIBLE_APT_TIMEOUT_SECONDS:-300}"
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
  apt_run install -y --no-install-recommends ca-certificates "${need_packages[@]}" || \
    fail "apt-get could not install required Ansible prerequisites"
fi

check_venv_creation
if version_is_valid "$VERSION_DIR"; then
  generation="$VERSION_DIR"
  echo "ansible-core $VERSION already installed in $generation"
elif executable_version_is_valid "$VERSION_DIR"; then
  generation="$VERSION_DIR"
  touch "$generation/.ready"
  echo "ansible-core $VERSION existing generation validated and adopted at $generation"
elif [[ -L "$CURRENT_LINK" ]]; then
  current_generation="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
  if [[ -n "$current_generation" && "$current_generation" == "$INSTALL_ROOT/ansible-core-$VERSION-"* ]] && \
     version_is_valid "$current_generation"; then
    generation="$current_generation"
    echo "ansible-core $VERSION reused current ready generation at $generation"
  fi
fi

if [[ -z "${generation:-}" ]]; then
  # Never remove a possibly in-use environment; publish a new immutable generation.
  generation="$INSTALL_ROOT/ansible-core-$VERSION-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  python3 -m venv "$generation"
  pip_timeout="${ANSIBLE_PIP_TIMEOUT_SECONDS:-300}"
  pip_run() {
    timeout "$pip_timeout" "$generation/bin/python" -m pip \
      --disable-pip-version-check \
      --no-input \
      --timeout 30 \
      --retries 3 \
      "$@"
  }
  # Keep the bootstrap tool deterministic; a transient index failure cannot
  # leave a half-published generation because the ready marker is last.
  pip_run install "pip==${ANSIBLE_PIP_VERSION:-26.1.1}"
  pip_run install "ansible-core==$VERSION"
  for exe in ansible ansible-config ansible-galaxy ansible-inventory ansible-playbook ansible-vault; do
    [[ -x "$generation/bin/$exe" ]] || fail "new generation is missing $exe"
  done
  "$generation/bin/ansible-playbook" --version 2>/dev/null | grep -Fq "[core $VERSION]" || \
    fail "new generation reports an unexpected Ansible version"
  touch "$generation/.ready"
fi

version_is_valid "$generation" || fail "validated generation became invalid: $generation"
pointer_tmp="$INSTALL_ROOT/.current.$$"
ln -s "$generation" "$pointer_tmp"
mv -Tf "$pointer_tmp" "$CURRENT_LINK"
for exe in ansible ansible-config ansible-galaxy ansible-inventory ansible-playbook ansible-vault; do
  ln -sfn "$generation/bin/$exe" "$BIN_DIR/$exe"
  if [[ "$USER_ONLY" != true ]]; then
    sudo ln -sfn "$generation/bin/$exe" "/usr/local/bin/$exe"
  fi
done
"$generation/bin/ansible-playbook" --version
printf 'ansible-core %s provisioned at %s\n' "$VERSION" "$generation"
