#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SYNTAX_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/single-node-syntax.XXXXXX")"
trap 'rm -rf -- "$SYNTAX_ROOT"' EXIT
printf '%s\n' 'all:' '  hosts:' '    node-rehearsal:' '      ansible_connection: local' '      ansible_python_interpreter: /usr/bin/python3' > "$SYNTAX_ROOT/hosts.yml"
export ANSIBLE_ROLES_PATH="$TARGET_ROOT/ansible/roles:$TARGET_ROOT/../Common/ansible/roles"
for playbook in PrepareSingleNode site; do
  ansible-playbook -i "$SYNTAX_ROOT/hosts.yml" --syntax-check "$TARGET_ROOT/ansible/playbooks/$playbook.yml"
done
