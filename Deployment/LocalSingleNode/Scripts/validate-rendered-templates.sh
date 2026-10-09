#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "$SCRIPT_DIR/.." <<'PY'
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from jinja2 import Environment, StrictUndefined

target = Path(sys.argv[1]).resolve()
context = dict(app_name='books', inventory_hostname='node-rehearsal', node_ip='192.0.2.10', lan_http_port=80, app_port=8080, postgres_port=5432, redis_port=6379, lan_hostnames=['books.example.invalid'], docker_subnet='172.30.10.0/24', app_image='ghcr.io/fixture-owner/books', release_image_digest='sha256:' + 'a' * 64, app_version='b' * 40, vault_postgres_password='FixturePassword12345678901234567890', vault_redis_password='FixtureRedis12345678901234567890123')
jinja = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
with tempfile.TemporaryDirectory(prefix='single-node-render-') as directory:
    folder = Path(directory)
    environment = jinja.from_string((target / 'ansible/templates/app.env.j2').read_text()).render(**context)
    env = folder / 'fake.env'
    env.write_text(environment)
    env.chmod(0o600)
    output = subprocess.check_output(['docker', 'compose', '--env-file', str(env), '-f', str(target / 'compose/docker-compose.yml'), 'config', '--format', 'json'], text=True)
    config = json.loads(output)
    for service in config['services'].values():
        for port in service.get('ports', []):
            assert port['host_ip'] == '127.0.0.1', 'Compose published a non-loopback port'
    assert config['services']['web']['image'] == context['app_image'] + '@' + context['release_image_digest']
    assert config['services']['web']['environment']['LocalAccounts__Enabled'] == 'false'
    assert config['networks']['default']['ipam']['config'][0]['subnet'] == context['docker_subnet']
    site = jinja.from_string((target / 'ansible/roles/single_node_caddy_site/templates/app.caddy.j2').read_text()).render(**context)
    assert 'http://192.0.2.10:80' in site and 'http://node-rehearsal.local:80' in site
    assert 'reverse_proxy 127.0.0.1:8080' in site and 'health_uri /health/ready' in site
    assert '{{' not in site and '{%' not in site
print('LocalSingleNode rendered environment, Compose and Caddy checks passed')
PY
