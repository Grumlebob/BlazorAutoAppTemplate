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


def assert_runtime_environment(folder, expected):
    verifier = folder / 'verify-env.yml'
    node_script = "console.log(JSON.stringify({username:process.env.Accounts__Email__Username,password:process.env.Accounts__Email__Password,legacyKey:process.env.DataProtection__LegacyRedisKey ?? ''}))"
    verifier.write_text(json.dumps({'services': {'verify': {
        'image': 'node:26.12.0-bookworm-slim',
        'network_mode': 'none',
        'env_file': [{'path': './.env', 'format': 'raw'}],
        'command': ['node', '-e', node_script],
    }}}, indent=2))
    empty_interpolation = folder / 'empty-interpolation.env'
    empty_interpolation.write_text('')
    result = subprocess.check_output([
        'docker', 'compose', '--project-directory', str(folder), '--env-file', str(empty_interpolation),
        '-f', str(verifier), 'run', '--rm', '--no-deps', '-T', 'verify'
    ], text=True, stderr=subprocess.STDOUT)
    lines = [line for line in result.splitlines() if line.startswith('{')]
    assert lines and json.loads(lines[-1]) == expected, 'synthetic account environment did not round-trip'


target = Path(sys.argv[1]).resolve()
root = target.parents[1]
context = dict(app_name='books', inventory_hostname='node-rehearsal', node_ip='192.0.2.10', lan_http_port=80, app_port=8080, postgres_port=5432, redis_port=6379, lan_hostnames=['books.example.invalid'], docker_subnet='172.30.10.0/24', app_image='ghcr.io/fixture-owner/books', release_image_digest='sha256:' + 'a' * 64, app_version='b' * 40, vault_postgres_password='FixturePassword12345678901234567890', vault_redis_password='FixtureRedis12345678901234567890123', vault_data_protection_certificate_password='d' * 64, data_protection_certificate_gid='1001')
jinja = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
context['data_protection_legacy_key_store'] = 'None'
context['data_protection_legacy_redis_key'] = ''
with tempfile.TemporaryDirectory(prefix='single-node-render-') as directory:
    folder = Path(directory)
    template = jinja.from_string((target / 'ansible/templates/app.env.j2').read_text())
    compose_template = jinja.from_string((target / 'ansible/templates/compose.env.j2').read_text())
    single_fixture = folder / 'single-node-compose'
    single_fixture.mkdir()
    single_compose = single_fixture / 'docker-compose.yml'
    single_compose.write_text((target / 'compose/docker-compose.yml').read_text())
    environment = template.render(**context)
    env = single_fixture / '.env'
    env.write_text(environment)
    env.chmod(0o600)
    interpolation_env = single_fixture / 'compose-input.env'
    interpolation_env.write_text(compose_template.render(**context))
    assert 'Accounts__' not in interpolation_env.read_text(), 'Compose interpolation allowlist must exclude account settings'
    output = subprocess.check_output(['docker', 'compose', '--project-directory', str(single_fixture), '--env-file', str(interpolation_env), '-f', str(single_compose), 'config', '--format', 'json'], text=True)
    config = json.loads(output)
    for service in config['services'].values():
        for port in service.get('ports', []):
            assert port['host_ip'] == '127.0.0.1', 'Compose published a non-loopback port'
    assert config['services']['web']['image'] == context['app_image'] + '@' + context['release_image_digest']
    assert config['services']['web']['environment']['LocalAccounts__Enabled'] == 'false'
    assert config['services']['web']['environment']['Accounts__Enabled'] == 'false'
    assert config['services']['web']['environment']['Accounts__RegistrationEnabled'] == 'false'
    assert config['services']['web']['environment']['DataProtection__KeyEncryptionCertificatePath'] == '/run/secrets/data-protection.pem'
    assert config['services']['web']['environment']['DataProtection__KeyEncryptionCertificatePassword'] == 'd' * 64
    assert config['services']['web']['environment']['DataProtection__LegacyKeyStore'] == 'None'
    assert config['services']['web']['environment']['DataProtection__LegacyKeyStoragePath'] == ''
    filesystem_environment = template.render(**{**context, 'data_protection_legacy_key_store': 'FileSystem'})
    assert 'DataProtection__LegacyKeyStoragePath=/run/legacy-data-protection' in filesystem_environment
    assert config['services']['web']['group_add'] == ['1001']
    assert any(volume.get('target') == '/run/secrets/data-protection.pem' and volume.get('read_only') for volume in config['services']['web']['volumes'])
    assert any(volume.get('target') == '/run/legacy-data-protection' and volume.get('read_only') for volume in config['services']['web']['volumes'])
    assert 'Accounts__Email__Password' not in (config['services']['postgres'].get('environment') or {})
    assert config['networks']['default']['ipam']['config'][0]['subnet'] == context['docker_subnet']

    special_password = "SMTP $one #two = \"three\" 'four' spaced"
    enabled_context = {
        **context,
        'data_protection_legacy_key_store': 'Redis',
        'data_protection_legacy_redis_key': 'legacy:keys $dollar #hash = "quoted"',
        'accounts_enabled': True,
        'accounts_registration_enabled': True,
        'accounts_admin_seed_enabled': False,
        'accounts_public_origin': 'https://books.example.invalid',
        'accounts_email_host': 'smtp.example.invalid',
        'accounts_email_port': 587,
        'accounts_email_security': 'StartTls',
        'accounts_email_from': 'accounts@example.invalid',
        'vault_accounts_email_username': 'user $ # = "quoted"',
        'vault_accounts_email_password': special_password,
    }
    enabled_env = env
    enabled_environment = template.render(**enabled_context)
    enabled_env.write_text(enabled_environment)
    enabled_env.chmod(0o600)
    interpolation_env.write_text(compose_template.render(**enabled_context))
    assert 'Accounts__' not in interpolation_env.read_text(), 'enabled account settings must stay out of Compose interpolation'
    enabled_output = subprocess.check_output(['docker', 'compose', '--project-directory', str(single_fixture), '--env-file', str(interpolation_env), '-f', str(single_compose), 'config', '--format', 'json'], text=True)
    enabled_config = json.loads(enabled_output)
    web_environment = enabled_config['services']['web']['environment']
    assert web_environment['Accounts__Enabled'] == 'true'
    assert web_environment['Accounts__RegistrationEnabled'] == 'true'
    assert_runtime_environment(single_fixture, {
        'username': enabled_context['vault_accounts_email_username'],
        'password': special_password,
        'legacyKey': enabled_context['data_protection_legacy_redis_key'],
    })
    for service_name in ('postgres', 'redis'):
        assert 'Accounts__Email__Password' not in (enabled_config['services'][service_name].get('environment') or {})

    root_fixture = folder / 'root-compose'
    root_fixture.mkdir()
    root_env = (root / '.env.example').read_text()
    root_env = root_env.replace('Accounts__Enabled=false', 'Accounts__Enabled=true')
    root_env = root_env.replace('Accounts__RegistrationEnabled=false', 'Accounts__RegistrationEnabled=true')
    root_env = root_env.replace('Accounts__PublicOrigin=\n', 'Accounts__PublicOrigin=https://books.example.invalid\n')
    root_env = root_env.replace('Accounts__Email__Host=\n', 'Accounts__Email__Host=smtp.example.invalid\n')
    root_env = root_env.replace('Accounts__Email__From=\n', 'Accounts__Email__From=accounts@example.invalid\n')
    root_env = root_env.replace('Accounts__Email__Password=\n', f"Accounts__Email__Password={special_password}\n")
    (root_fixture / '.env').write_text(root_env)
    root_interpolation = root_fixture / 'compose-input.env'
    root_interpolation.write_text('\n'.join(line for line in root_env.splitlines() if not line.startswith('Accounts__')) + '\n')
    root_compose = root / 'docker-compose.yml'
    (root_fixture / 'docker-compose.yml').write_text(root_compose.read_text())
    root_output = subprocess.check_output([
        'docker', 'compose', '--project-directory', str(root_fixture), '--env-file', str(root_interpolation),
        '-f', str(root_fixture / 'docker-compose.yml'), 'config', '--format', 'json'
    ], text=True, cwd=root)
    root_config = json.loads(root_output)
    assert 'Accounts__Email__Password' in root_config['services']['web']['environment']
    for service_name in ('postgres', 'redis', 'redisinsight'):
        assert 'Accounts__Email__Password' not in (root_config['services'][service_name].get('environment') or {})
    assert root_config['services']['postgres']['environment']['POSTGRES_PASSWORD'] == 'postgres'
    assert_runtime_environment(root_fixture, {
        'username': '',
        'password': special_password,
        'legacyKey': '',
    })
    site = jinja.from_string((target / 'ansible/roles/single_node_caddy_site/templates/app.caddy.j2').read_text()).render(**context)
    assert 'http://192.0.2.10:80' in site and 'http://node-rehearsal.local:80' in site
    assert 'reverse_proxy 127.0.0.1:8080' in site and 'health_uri /health/ready' in site
    assert '{{' not in site and '{%' not in site
print('LocalSingleNode and root account settings, secret round-trip, Compose and Caddy checks passed')
PY
