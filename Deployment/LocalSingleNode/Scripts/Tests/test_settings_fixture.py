"""Stable settings for offline tests, independent of a clone's app identity."""
from pathlib import Path
import unittest
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


class AccountSettingsTests(unittest.TestCase):
    def test_legacy_settings_default_account_features_off(self):
        values = fixture_settings()
        self.assertFalse(values["accounts_enabled"])
        self.assertFalse(values["accounts_registration_enabled"])
        self.assertFalse(values["accounts_admin_seed_enabled"])
        self.assertEqual(587, values["accounts_email_port"])
        self.assertEqual("StartTls", values["accounts_email_security"])

    def test_known_account_settings_accept_synthetic_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.yml"
            path.write_text(SETTINGS_YAML + """accounts_enabled: true
accounts_registration_enabled: true
accounts_admin_seed_enabled: false
accounts_admin_seed_email: ""
accounts_public_origin: https://books.example.invalid
accounts_email_host: smtp.example.invalid
accounts_email_port: 587
accounts_email_security: StartTls
accounts_email_from: accounts@example.invalid
""")
            values = validate_settings(path)
        self.assertTrue(values["accounts_enabled"])
        self.assertTrue(values["accounts_registration_enabled"])
        self.assertEqual("https://books.example.invalid", values["accounts_public_origin"])

    def test_legacy_data_protection_source_settings_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.yml"
            path.write_text(SETTINGS_YAML + "data_protection_legacy_key_store: Redis\ndata_protection_legacy_redis_key: fixture:legacy-keys\n")
            values = validate_settings(path)
        self.assertEqual("Redis", values["data_protection_legacy_key_store"])
        self.assertEqual("fixture:legacy-keys", values["data_protection_legacy_redis_key"])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.yml"
            path.write_text(SETTINGS_YAML + "data_protection_legacy_key_store: FileSystem\ndata_protection_legacy_redis_key: fixture:legacy-keys\n")
            with self.assertRaisesRegex(ValueError, "required only when.*Redis"):
                validate_settings(path)

    def test_unknown_account_setting_and_registration_without_accounts_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.yml"
            path.write_text(SETTINGS_YAML + "accounts_unreviewed: true\n")
            with self.assertRaisesRegex(ValueError, "missing or unknown"):
                validate_settings(path)
            path.write_text(SETTINGS_YAML + "accounts_registration_enabled: true\n")
            with self.assertRaisesRegex(ValueError, "requires accounts_enabled"):
                validate_settings(path)
