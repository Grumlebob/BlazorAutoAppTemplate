"""Restart one owned public app under the shared lock and prove catalog persistence."""
import getpass
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
from ls_settings import ROOT, TARGET, command, settings
from platform_check import native

spec = importlib.util.spec_from_file_location('app_instance', Path(__file__).with_name('resolve-app-instance.py'))
instance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(instance)
CHECK_PHASE = 'initial guards'


def guards():
    if not native() or getpass.getuser() != 'deploy' or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('Require the native deployment user and trusted main')
    if os.environ.get('LOCALSINGLENODE_ETC') or os.environ.get('OPT_ROOT'):
        raise ValueError('Fixture overrides are forbidden on the node')
    token = os.environ.get('LOCALCLUSTER_DEPLOY_LOCK_TOKEN')
    directory = Path(os.environ.get('LOCALCLUSTER_DEPLOY_LOCK_DIR', '/nonexistent'))
    if not token or (directory / 'token').read_text().strip() != token:
        raise ValueError('Require the held shared deployment lock')


def compose(root):
    """`docker compose` for a deployed app; its .compose.env holds required interpolation values."""
    env_file = Path(root) / '.compose.env'
    return ['docker', 'compose', '--project-directory', root,
            *(['--env-file', str(env_file)] if env_file.is_file() else [])]


def containers(config):
    root, app = config['deploy_root'], config['app_name']
    # APP_NAME belongs to the selected app and overrides another root's .env.
    # Pin the project independently when inspecting the primary sibling.
    identifiers = command(*compose(root), '--project-name', app, 'ps', '-q').splitlines()
    values = json.loads(command('docker', 'inspect', *identifiers)) if identifiers else []
    result = {}
    for value in values:
        labels = value['Config'].get('Labels') or {}
        service = labels.get('com.docker.compose.service')
        if (labels.get('com.docker.compose.project') != app or labels.get('localsinglenode.app') != app
                or labels.get('com.docker.compose.project.working_dir') != root
                or service not in ('web', 'postgres', 'redis') or service in result
                or value['State']['Status'] != 'running'):
            raise ValueError('Container ownership or running state does not match the selected app')
        result[service] = {
            'id': value['Id'], 'image': value['Image'], 'started': value['State']['StartedAt'],
            'restarts': value['RestartCount'], 'mounts': value.get('Mounts', []),
        }
    if set(result) != {'web', 'postgres', 'redis'}:
        raise ValueError('Require exactly the three healthy owned app services')
    return result


def catalog(config):
    base = 'http://127.0.0.1:' + str(config['app_port'])
    with urllib.request.urlopen(base + '/health/ready', timeout=10) as response:
        if response.status != 200 or response.read(64).strip() != b'Healthy':
            raise ValueError('App readiness failed')
    with urllib.request.urlopen(base + '/api/author-books', timeout=10) as response:
        value = json.load(response)
    if not isinstance(value, dict) or not isinstance(value.get('books'), list) or not value['books']:
        raise ValueError('Require a nonempty public seed catalog before restart')
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def verify_release(config):
    release = json.loads((Path(config['deploy_root']) / 'release.json').read_text())
    expected_source = os.environ['GITHUB_SERVER_URL'] + '/' + os.environ['GITHUB_REPOSITORY']
    if (release['image'] != os.environ['APP_IMAGE'] or release['source_repo_url'] != expected_source
            or release['frontend_profile'] != os.environ['FRONTEND_PROFILE']
            or release['acceptance_profile'] != os.environ['ACCEPTANCE_PROFILE']):
        raise ValueError('Release differs from the protected application identity')
    command('bash', str(Path(__file__).with_name('verify-release-identity.sh')),
            release['image'], release['digest'], release['frontend_profile'], release['acceptance_profile'],
            release['source_sha'], str(release['manifest_schema_version']), str(release['ci_run_id']),
            str(release['ci_run_attempt']), release['source_repo_url'])
    return release


def verify_after(before, after):
    for service in before:
        if service != 'web':
            if after[service] != before[service]:
                raise ValueError('A backing service or sibling app changed during the restart')
        else:
            if any(after[service][key] != before[service][key] for key in ('id', 'image', 'mounts', 'restarts')):
                raise ValueError('Web identity, storage or automatic restart count changed')
            if after[service]['started'] == before[service]['started']:
                raise ValueError('Web did not start a new process')


def main():
    global CHECK_PHASE
    CHECK_PHASE = 'initial guards'
    guards()
    config = settings()
    source = os.environ['GITHUB_SERVER_URL'] + '/' + os.environ['GITHUB_REPOSITORY']
    instance.verify_owned(config, source)
    CHECK_PHASE = 'selected container inventory'
    before = containers(config)
    CHECK_PHASE = 'selected release identity'
    release = verify_release(config)
    CHECK_PHASE = 'public catalog snapshot'
    seed = catalog(config)
    primary = settings(TARGET / 'inventory/group_vars/all.yml')
    CHECK_PHASE = 'primary sibling inventory'
    sibling = containers(primary) if primary['app_name'] != config['app_name'] else None
    CHECK_PHASE = 'web restart'
    print('Preflight passed; restarting only the explicitly selected web project.', flush=True)
    command(*compose(config['deploy_root']), '--project-name', config['app_name'], 'restart', '--no-deps', 'web', timeout=60)
    CHECK_PHASE = 'catalog recovery'
    deadline = time.monotonic() + 180
    while True:
        try:
            if catalog(config) != seed:
                raise ValueError('Public catalog changed after restart')
            break
        except (ValueError, OSError):
            if time.monotonic() >= deadline:
                raise ValueError('Catalog/readiness did not recover unchanged before deadline') from None
            time.sleep(2)
    CHECK_PHASE = 'release, storage and sibling stability'
    verify_after(before, containers(config))
    time.sleep(10)
    verify_after(before, containers(config))
    if catalog(config) != seed or verify_release(config) != release:
        raise ValueError('Catalog or immutable release changed during stability observation')
    if sibling is not None and containers(primary) != sibling:
        raise ValueError('Primary app changed during the additional app restart')
    print('Scoped web restart passed: catalog unchanged, release and storage retained, backing services and sibling unchanged.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError):
        print('Scoped app restart check failed during ' + CHECK_PHASE + '; inspect the owned app without automatic retry.', file=sys.stderr)
        sys.exit(1)
