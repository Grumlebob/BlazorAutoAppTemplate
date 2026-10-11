#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 9 ]]; then
  echo 'Usage: verify-release-identity.sh <app_image> <sha256:digest> <frontend_profile> <acceptance_profile> <source_sha> <manifest_schema> <ci_run_id> <ci_run_attempt> <source_repo_url>' >&2
  exit 2
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(bash "$SCRIPT_DIR/read-setting.sh" deploy_root)"
exec python3 - "$APP_ROOT" "$@" <<'PY'
import json
import re
import subprocess
import sys
if len(sys.argv) != 11:
    raise SystemExit('Usage: verify-release-identity.sh <app_image> <sha256:digest> <frontend_profile> <acceptance_profile> <source_sha> <manifest_schema> <ci_run_id> <ci_run_attempt> <source_repo_url>')
root, image, digest, frontend, acceptance, source_sha, schema, run_id, run_attempt, source_repo = sys.argv[1:]
if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
    raise SystemExit('Release digest is malformed')
if frontend not in ('BlazorAuto', 'React') or acceptance != {'BlazorAuto': 'BlazorAutoV1', 'React': 'ReactPublicV1'}.get(frontend):
    raise SystemExit('Frontend and acceptance profiles do not match')
if schema not in ('1', '2') or not re.fullmatch(r'[0-9a-f]{40}', source_sha):
    raise SystemExit('Release source or manifest schema is malformed')
if schema == '1' and (frontend, acceptance) != ('BlazorAuto', 'BlazorAutoV1'):
    raise SystemExit('Legacy schema v1 is supported only for BlazorAuto')
if not run_id.isdigit() or not run_attempt.isdigit() or int(run_attempt) < 1:
    raise SystemExit('Release CI run metadata is malformed')
if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', source_repo):
    raise SystemExit('Release source repository is malformed')
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
labels = descriptor.get('Config', {}).get('Labels') or {}
repository_slug = source_repo.removeprefix('https://github.com/')
for key, expected in {
    'org.opencontainers.image.source': source_repo,
    'localcluster.ci.repository': repository_slug,
    'localcluster.ci.run_id': run_id,
    'localcluster.ci.run_attempt': run_attempt,
}.items():
    if labels.get(key) != expected:
        raise SystemExit('Running web image does not match verified CI label ' + key)
profile_labels = {
    'org.opencontainers.image.revision': source_sha,
    'com.blazorautoapp.frontend-profile': frontend,
    'com.blazorautoapp.acceptance-profile': acceptance,
}
if schema == '2':
    for key, expected in profile_labels.items():
        if labels.get(key) != expected:
            raise SystemExit('Running web image does not match verified release label ' + key)
else:
    for key, expected in profile_labels.items():
        if key in labels and labels[key] != expected:
            raise SystemExit('Legacy image conflicts with verified Blazor release label ' + key)
print('Running release identity verified: ' + digest + ' ' + frontend + '/' + acceptance)
PY
