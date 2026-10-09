#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SCRIPT="$REPO_ROOT/Deployment/Common/Scripts/install-ansible.sh"
TMP_ROOT="$(mktemp -d)"
cleanup() { rm -rf "$TMP_ROOT"; }
trap cleanup EXIT

generation="$TMP_ROOT/ansible-core-2.17.14-20260929T000000Z-1234"
mkdir -p "$generation/bin" "$TMP_ROOT/bin"
cat > "$TMP_ROOT/bin/python3" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-" ]]; then
  printf '%s\n' '3.8.10'
  exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "venv" ]]; then
  if [[ "${3:-}" == "--help" ]]; then
    exit 0
  fi
  target="${3:?venv target is required}"
  mkdir -p "$target/bin"
  cat > "$target/bin/python" <<'PYTHON'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" ]]; then
  echo 'unexpected pip install; existing current generation should be reused' >&2
  exit 88
fi
exit 0
PYTHON
  chmod +x "$target/bin/python"
  exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "--version" ]]; then
  printf '%s\n' 'pip 24.0 from fixture'
  exit 0
fi
exit 1
SH
chmod +x "$TMP_ROOT/bin/python3"
cat > "$TMP_ROOT/bin/sudo" <<'SH'
#!/usr/bin/env bash
if [[ "${1:-}" == "-n" && "${2:-}" == "true" ]]; then
  exit 0
fi
if [[ "${1:-}" == "ln" ]]; then
  exit 0
fi
echo "unexpected sudo invocation: $*" >&2
exit 99
SH
chmod +x "$TMP_ROOT/bin/sudo"
# Stub every host tool provisioning probes for, so the fixture is hermetic.
for tool in ssh sshpass; do
  printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP_ROOT/bin/$tool"
  chmod +x "$TMP_ROOT/bin/$tool"
done
cat > "$generation/bin/ansible-playbook" <<'SH'
#!/usr/bin/env bash
printf '%s\n' 'ansible-playbook [core 2.17.14]'
SH
chmod +x "$generation/bin/ansible-playbook"
for executable in ansible ansible-config ansible-galaxy ansible-inventory ansible-vault; do
  printf '#!/usr/bin/env bash\nprintf "stub\\n"\n' > "$generation/bin/$executable"
  chmod +x "$generation/bin/$executable"
done
touch "$generation/.ready"
ln -s "$generation" "$TMP_ROOT/current"

# A healthy check must not need sudo/apt and must validate a real temporary venv.
ANSIBLE_CORE_VERSION=2.17.14 \
ANSIBLE_INSTALL_ROOT="$TMP_ROOT" \
ANSIBLE_BIN_DIR="$TMP_ROOT/bin" \
PATH="$TMP_ROOT/bin:$PATH" \
bash "$SCRIPT" --check >"$TMP_ROOT/output.log"
grep -Fq "ansible-core 2.17.14 ready" "$TMP_ROOT/output.log"

ANSIBLE_CORE_VERSION=2.17.14 \
ANSIBLE_INSTALL_ROOT="$TMP_ROOT" \
ANSIBLE_BIN_DIR="$TMP_ROOT/bin" \
PATH="$TMP_ROOT/bin:$PATH" \
bash "$SCRIPT" --provision >"$TMP_ROOT/provision.log"
grep -Fq "ansible-core 2.17.14 reused current ready generation" "$TMP_ROOT/provision.log"
[[ "$(readlink -f "$TMP_ROOT/current")" == "$generation" ]]

# User-only mode must neither probe sudo nor install packages or global links.
cat > "$TMP_ROOT/bin/sudo" <<'SH'
#!/usr/bin/env bash
echo sudo >> "$PRIVILEGED_CALLS"
exit 99
SH
cat > "$TMP_ROOT/bin/apt-get" <<'SH'
#!/usr/bin/env bash
echo apt-get >> "$PRIVILEGED_CALLS"
exit 99
SH
chmod +x "$TMP_ROOT/bin/sudo" "$TMP_ROOT/bin/apt-get"
export PRIVILEGED_CALLS="$TMP_ROOT/privileged-calls"
for round in 1 2; do
  ANSIBLE_CORE_VERSION=2.17.14 ANSIBLE_INSTALL_ROOT="$TMP_ROOT" \
    ANSIBLE_BIN_DIR="$TMP_ROOT/bin" PATH="$TMP_ROOT/bin:$PATH" \
    bash "$SCRIPT" --provision --user-only > "$TMP_ROOT/user-only-$round.log"
  [[ "$(readlink -f "$TMP_ROOT/current")" == "$generation" ]]
done
[[ ! -e "$PRIVILEGED_CALLS" ]]
sed -i '/printf.*pip 24.0/i\  if [[ "${FIXTURE_MISSING_PIP:-}" == true ]]; then exit 1; fi' "$TMP_ROOT/bin/python3"
if FIXTURE_MISSING_PIP=true ANSIBLE_CORE_VERSION=2.17.14 \
    ANSIBLE_INSTALL_ROOT="$TMP_ROOT" ANSIBLE_BIN_DIR="$TMP_ROOT/bin" PATH="$TMP_ROOT/bin:$PATH" \
    bash "$SCRIPT" --provision --user-only > "$TMP_ROOT/missing.log" 2>&1; then
  echo 'Missing prerequisite unexpectedly succeeded' >&2; exit 1
fi
grep -Fq -- '--user-only requires preinstalled prerequisites: python3-pip' "$TMP_ROOT/missing.log"
[[ ! -e "$PRIVILEGED_CALLS" ]]
echo 'User-only Ansible idempotence, missing prerequisite and no sudo/apt/global-link fixtures passed'
