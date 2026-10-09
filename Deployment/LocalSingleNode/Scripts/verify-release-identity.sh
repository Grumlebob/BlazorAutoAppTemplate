#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(bash "$SCRIPT_DIR/read-setting.sh" deploy_root)"
exec python3 - "$APP_ROOT" "$@" <<'PY'
import json
import re
import subprocess
import sys
if len(sys.argv) != 4 or not re.fullmatch(r'sha256:[0-9a-f]{64}', sys.argv[3]):
    raise SystemExit('Usage: verify-release-identity.sh <app_image> <sha256:digest>')
root, image, digest = sys.argv[1:]
def run(*args):
    return subprocess.check_output(args, text=True).strip()
container = run('docker', 'compose', '--project-directory', root, 'ps', '-q', 'web')
if not container:
    raise SystemExit('No running web container')
identity = json.loads(run('docker', 'inspect', container))[0]
if identity['State']['Status'] != 'running':
    raise SystemExit('Web container is not running')
descriptor = json.loads(run('docker', 'image', 'inspect', identity['Image']))[0]
if image + '@' + digest not in descriptor.get('RepoDigests', []):
    raise SystemExit('Running web image does not match the verified registry digest')
print('Running release identity verified: ' + digest)
PY
