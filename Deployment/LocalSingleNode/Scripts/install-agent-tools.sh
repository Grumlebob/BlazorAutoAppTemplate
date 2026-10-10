#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/lib/platform_check.py"
test "$(uname -m)" = x86_64 || { echo 'Only Linux x64 is supported.' >&2; exit 1; }
exec python3 - "$SCRIPT_DIR/../../Common/tool-versions.json" <<'PY'
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request

pin = json.loads(Path(__import__('sys').argv[1]).read_text())["gh"]
version = pin["version"]
url = f"https://github.com/cli/cli/releases/download/v{version}/gh_{version}_linux_amd64.tar.gz"
with urllib.request.urlopen(url, timeout=60) as response:
    data = response.read(100_000_000)
if hashlib.sha256(data).hexdigest() != pin["sha256"]:
    raise SystemExit("GitHub CLI archive checksum mismatch")
destination = Path.home() / ".local/share/localsinglenode-tools/bin/gh"
destination.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
    member = archive.getmember(f"gh_{version}_linux_amd64/bin/gh")
    if not member.isfile():
        raise SystemExit("GitHub CLI archive binary is not a regular file")
    binary = archive.extractfile(member).read()
temporary = destination.with_name(f"gh.{os.getpid()}.tmp")
temporary.write_bytes(binary)
temporary.chmod(0o755)
temporary.replace(destination)
print(f"GitHub CLI {version} verified at {destination}")
PY
