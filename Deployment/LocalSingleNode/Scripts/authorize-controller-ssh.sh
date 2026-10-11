#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 || ! "$1" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ || ! "$2" =~ ^[a-z][a-z0-9-]{0,31}$ ]]; then
  echo "Usage: authorize-controller-ssh.sh OWNER/REPOSITORY CONTROLLER" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/lib/platform_check.py"
# Facts are read locally and never written to the workflow log.
install_user="$(python3 - "$script_dir/lib" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from ls_settings import read_yaml
from machine import validate
print(validate(read_yaml(Path('/etc/localsinglenode/machine.yml'), node=True))['install_user'])
PY
)"

# The runner's home can be private. Copy only public program files to a readable
# temporary directory; retain the install user's existing authenticated gh config.
handoff="$(mktemp -d /tmp/localsinglenode-controller-ssh.XXXXXXXX)"
trap 'rm -rf -- "$handoff"' EXIT
chmod 0755 "$handoff"
public_scripts="$handoff/Deployment/LocalSingleNode/Scripts"
install -d -m 0755 "$handoff/Deployment" "$handoff/Deployment/LocalSingleNode" "$public_scripts" "$public_scripts/lib"
cp "$script_dir/controller-ssh.py" "$public_scripts/controller-ssh.py"
for module in ls_settings machine platform_check; do
  cp "$script_dir/lib/$module.py" "$public_scripts/lib/$module.py"
done
chmod 0644 "$public_scripts/controller-ssh.py" "$public_scripts/lib/"*.py
sudo -n -u "$install_user" -H -- python3 "$public_scripts/controller-ssh.py" authorize --repo "$1" --controller "$2"
