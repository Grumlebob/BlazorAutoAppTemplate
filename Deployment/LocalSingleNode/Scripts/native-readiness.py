"""Read-only deployment-user diagnostics with sanitized output only."""
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
import collisions
import doctor
from ls_settings import ETC, command, read_yaml, settings
from platform_check import native


def verify(payload):
    if not native() or os.geteuid() == 0 or command('id', '-un') != 'deploy':
        raise ValueError('deployment-user access required')
    if not isinstance(payload, dict) or set(payload) != {'expected_host', 'source_repo_url', 'settings_yaml'}:
        raise ValueError('invalid candidate input')
    host = payload['expected_host']
    if not isinstance(host, str) or host != socket.gethostname():
        raise ValueError('native host identity mismatch')
    if read_yaml(ETC / 'localsinglenode/machine.yml', node=True)['name'] != host:
        raise ValueError('recorded host identity mismatch')
    source = payload['source_repo_url']
    if not isinstance(source, str) or not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', source):
        raise ValueError('invalid candidate repository')
    if not isinstance(payload['settings_yaml'], str) or len(payload['settings_yaml']) > 16384:
        raise ValueError('invalid candidate settings')


def backup_freshness(config):
    try:
        folder = Path(config['backup_root'])
        marker = folder / 'last-success'
        if marker.is_symlink():
            return 'unknown'
        completed = datetime.fromisoformat(marker.read_text().strip())
        if completed.tzinfo is None:
            return 'unknown'
        age = datetime.now(timezone.utc) - completed
        dumps = [path for path in folder.glob(config['app_name'] + '-*.dump')
                 if not path.is_symlink() and path.is_file() and path.stat().st_size > 0]
        return 'fresh' if timedelta(0) <= age <= timedelta(hours=24) and dumps else 'stale'
    except (OSError, ValueError):
        return 'unknown'


def configured_identity():
    config = settings()
    marker = ETC / ('localsinglenode/apps/' + config['app_name'] + '.json')
    if marker.is_symlink():
        raise ValueError('unsafe configured ownership marker')
    identity = json.loads(marker.read_text())
    expected_source = 'https://github.com/' + os.environ['GITHUB_REPOSITORY']
    if (not isinstance(identity, dict)
            or str(identity.get('source_repo_url', '')).casefold() != expected_source.casefold()
            or identity.get('deploy_root') != config['deploy_root']
            or identity.get('backup_root') != config['backup_root']):
        raise ValueError('configured application ownership mismatch')
    return config


def capacity(docker_root='/var/lib/docker'):
    # Planning floors reserve room for one sequential build plus a small app.
    # Real CI and app health must still pass before a release can be deployed.
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        memory[key] = int(value.split()[0]) * 1024
    cpus = os.cpu_count() or 0
    adequate = (cpus >= 4 and os.getloadavg()[1] < cpus * 0.75
                and memory['MemTotal'] >= 7 * 1024 ** 3
                and memory['MemAvailable'] >= 4 * 1024 ** 3
                and all(doctor.shutil.disk_usage(path).free >= 40 * 1024 ** 3
                        for path in ('/opt', Path.cwd(), docker_root)))
    return 'adequate' if adequate else 'inadequate'


def inspect(payload):
    verify(payload)
    current = configured_identity()
    results = {'doctor': 'pass' if all(item['pass'] for item in doctor.check()) else 'fail',
               'docker_api': 'unavailable', 'collision': 'not-run',
               'existing_app': 'unknown', 'backup': backup_freshness(current),
               'capacity': 'unknown'}
    # No raw Docker output, command errors, installation values or tracebacks.
    command('docker', 'info', '--format', '{{.ServerVersion}}')
    results['docker_api'] = 'available'
    ids = command('docker', 'ps', '-aq').splitlines()
    containers = json.loads(command('docker', 'inspect', *ids)) if ids else []
    network_ids = command('docker', 'network', 'ls', '-q').splitlines()
    if network_ids:
        json.loads(command('docker', 'network', 'inspect', *network_ids))
    own = [item for item in containers
           if (item.get('Config', {}).get('Labels') or {}).get('localsinglenode.app') == current['app_name']]
    results['existing_app'] = 'healthy' if len(own) == 3 and all(
        item.get('State', {}).get('Running') is True
        and item.get('State', {}).get('Health', {}).get('Status', 'healthy') == 'healthy'
        for item in own) else 'unhealthy'
    docker_root = command('docker', 'info', '--format', '{{.DockerRootDir}}')
    if not Path(docker_root).is_absolute():
        raise ValueError('Docker root must be absolute')
    results['capacity'] = capacity(docker_root)
    descriptor, name = tempfile.mkstemp(prefix='node-readiness-', suffix='.yml', dir=os.environ['RUNNER_TEMP'])
    path = Path(name)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(payload['settings_yaml'])
        candidate = settings(path)
        if candidate['app_name'] == current['app_name']:
            raise ValueError('candidate must have a separate app identity')
        try:
            with redirect_stdout(io.StringIO()):
                collisions.check(payload['source_repo_url'], settings_file=path)
            results['collision'] = 'pass'
        except (ValueError, OSError, KeyError):
            results['collision'] = 'fail'
    finally:
        path.unlink(missing_ok=True)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        payload = json.loads(os.environ['READINESS_CANDIDATE'])
        if args.verify_only:
            verify(payload)
            print('Native deployment-user identity verified')
            return 0
        results = inspect(payload)
        print(json.dumps(results, sort_keys=True))
        expected = {'doctor': 'pass', 'docker_api': 'available', 'collision': 'pass',
                    'existing_app': 'healthy', 'backup': 'fresh', 'capacity': 'adequate'}
        return 0 if results == expected else 1
    except Exception:
        # Boundary deliberately suppresses timeout/OS/parser details as well.
        print('Read-only readiness unavailable; inspect access and protected candidate input', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
