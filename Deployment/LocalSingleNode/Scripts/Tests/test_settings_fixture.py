"""Stable settings for offline tests, independent of a clone's app identity."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from ls_settings import settings as validate_settings

SETTINGS_YAML = """app_name: books
app_port: 8080
postgres_port: 5432
redis_port: 6379
deploy_root: /opt/books
docker_subnet: 172.30.10.0/24
lan_http_port: 80
lan_hostnames: []
backup_root: /opt/books-backups
backup_keep_days: 7
observability_enabled: false
"""


def write_settings(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SETTINGS_YAML)


def fixture_settings():
    # Exercise the production parser and validation rather than bypassing them.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'settings.yml'
        write_settings(path)
        return validate_settings(path)
