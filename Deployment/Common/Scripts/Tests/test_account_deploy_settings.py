"""Synthetic account deployment settings and vault parsing checks."""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[4]
COMMON_LIB = ROOT / "Deployment/Common/Scripts/Component/lib"
sys.path.insert(0, str(COMMON_LIB))

from account_deploy_settings import validate_account_deploy_settings  # noqa: E402
from data_protection_deploy_settings import validate_legacy_data_protection_settings  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOCAL_CLUSTER = load_module(
    "account_deploy_settings_localcluster_under_test",
    ROOT / "Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py",
)
CLOUD = load_module(
    "account_deploy_settings_cloud_under_test",
    ROOT / "Deployment/Cloud/Scripts/Component/lib/cloud_settings.py",
)
VAULT = load_module(
    "validate_vault_under_test",
    ROOT / "Deployment/LocalCluster/Scripts/Component/lib/validate-vault.py",
)


def valid_settings(target: str) -> dict[str, str]:
    values = {
        "app_name": "fixture-books",
        "app_port": "8085",
        "postgres_port": "5432",
        "redis_port": "6379",
        "public_hostname": "books.example.invalid",
        "deploy_root": "/opt/fixture-books",
        "cloudflare_tunnel_name": "fixture-books",
        "cloudflared_version": "2026.5.0",
    }
    if target == "Cloud":
        values.update(
            {
                "cloud_private_network_cidr": "192.0.2.0/24",
                "cloud_private_gateway_ip": "192.0.2.1",
                "cloud_main_private_ip": "192.0.2.2",
                "cloud_app1_private_ip": "192.0.2.3",
                "cloud_app2_private_ip": "192.0.2.4",
                "cloud_db_private_ip": "192.0.2.5",
            }
        )
    return values


class AnsibleAccountValidationExpressionTests(unittest.TestCase):
    def test_account_assertions_compile_for_every_deployment_target(self) -> None:
        targets = (
            (
                ROOT / "Deployment/LocalCluster/ansible/roles/app/tasks/main.yml",
                "Validate account settings and secret values before staging the app",
            ),
            (
                ROOT / "Deployment/Cloud/ansible/roles/app/tasks/main.yml",
                "Validate account settings and secret values before staging the app",
            ),
            (
                ROOT / "Deployment/LocalSingleNode/ansible/roles/single_node_stack/tasks/main.yml",
                "Validate account environment values before rendering dotenv",
            ),
        )
        environment = jinja2.Environment()
        environment.filters["regex_search"] = lambda *_args, **_kwargs: None
        environment.filters["bool"] = bool
        environment.tests["match"] = lambda *_args, **_kwargs: True

        for path, task_name in targets:
            tasks = yaml.safe_load(path.read_text(encoding="utf-8"))
            task = next(
                item for item in tasks
                if item.get("name") == task_name
            )
            expressions = task["ansible.builtin.assert"]["that"]
            for index, expression in enumerate(expressions):
                with self.subTest(target=path.relative_to(ROOT), expression=index + 1):
                    environment.compile_expression(str(expression))


def valid_vault_values() -> dict[str, str]:
    pem = (
        b"-----BEGIN CERTIFICATE-----\nfixture\n"
        b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nfixture\n"
    )
    return {
        "vault_postgres_user": "fixture_user",
        "vault_postgres_password": "FixtureDbPassword123",
        "vault_postgres_db": "fixture_db",
        "vault_redis_password": "FixtureRedisPassword123",
        "vault_cloudflare_tunnel_token": "eyJ" + "A" * 100,
        "vault_data_protection_certificate_base64": base64.b64encode(pem).decode("ascii"),
        "vault_data_protection_certificate_password": "a" * 64,
    }


class AccountDeploymentSettingsTests(unittest.TestCase):
    def test_missing_account_settings_remain_disabled_for_both_targets(self):
        self.assertEqual([], validate_account_deploy_settings({}))
        for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            with self.subTest(target=target):
                self.assertEqual([], module.validate(valid_settings(target)))

    def test_legacy_data_protection_source_is_optional_and_pairing_is_strict(self):
        self.assertEqual([], validate_legacy_data_protection_settings({}))
        for store, redis_key in (("None", ""), ("FileSystem", ""), ("Redis", "fixture:legacy-keys")):
            with self.subTest(store=store):
                values = {
                    "data_protection_legacy_key_store": store,
                    "data_protection_legacy_redis_key": redis_key,
                }
                self.assertEqual([], validate_legacy_data_protection_settings(values))
                for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
                    self.assertEqual([], module.validate({**valid_settings(target), **values}))

        invalid_values = (
            ({"data_protection_legacy_key_store": "unknown", "data_protection_legacy_redis_key": ""},
             "data_protection_legacy_key_store must be None, Redis, or FileSystem"),
            ({"data_protection_legacy_key_store": "Redis", "data_protection_legacy_redis_key": ""},
             "data_protection_legacy_redis_key is required when the legacy key store is Redis"),
            ({"data_protection_legacy_key_store": "FileSystem", "data_protection_legacy_redis_key": "fixture:key"},
             "data_protection_legacy_redis_key requires the legacy key store to be Redis"),
            ({"data_protection_legacy_key_store": "Redis", "data_protection_legacy_redis_key": "fixture:key\nsecond"},
             "data_protection_legacy_redis_key must be a single-line value"),
        )
        for values, expected_error in invalid_values:
            with self.subTest(values=values):
                self.assertIn(expected_error, validate_legacy_data_protection_settings(values))
                for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
                    self.assertIn(expected_error, module.validate({**valid_settings(target), **values}))

    def test_seed_only_is_valid_without_smtp_and_registration_requires_complete_email(self):
        seed_only = {
            "accounts_enabled": "true",
            "accounts_admin_seed_enabled": "true",
            "accounts_admin_seed_email": "admin@example.invalid",
        }
        self.assertEqual([], validate_account_deploy_settings(seed_only))

        registration = {
            **seed_only,
            "accounts_admin_seed_enabled": "false",
            "accounts_registration_enabled": "true",
            "accounts_public_origin": "https://books.example.invalid",
            "accounts_email_host": "smtp.example.invalid",
            "accounts_email_from": "accounts@example.invalid",
        }
        self.assertEqual([], validate_account_deploy_settings(registration))

        incomplete = {**registration, "accounts_email_from": ""}
        self.assertIn(
            "accounts_registration_enabled requires enabled accounts and complete email settings",
            validate_account_deploy_settings(incomplete),
        )
        for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            with self.subTest(target=target):
                self.assertIn(
                    "accounts_registration_enabled requires enabled accounts and complete email settings",
                    module.validate({**valid_settings(target), **incomplete}),
                )

    def test_account_settings_types_and_unknown_keys_are_rejected(self):
        self.assertEqual(
            [
                "accounts_enabled must be true or false",
                "accounts_email_port must be an integer from 1 through 65535",
                "accounts_email_security must be StartTls or SslOnConnect",
            ],
            validate_account_deploy_settings(
                {
                    "accounts_enabled": "sometimes",
                    "accounts_email_port": "not-a-port",
                    "accounts_email_security": "Plaintext",
                }
            ),
        )
        for target, module in (("LocalCluster", LOCAL_CLUSTER), ("Cloud", CLOUD)):
            values = valid_settings(target)
            values["accounts_unreviewed_option"] = "true"
            with self.subTest(target=target):
                self.assertEqual(["unknown setting: accounts_unreviewed_option"], module.validate(values))

    def test_quoted_vault_credentials_preserve_spaces_and_shell_metacharacters(self):
        secret = ' spaces $dollar #hash = "double" \'single\' '
        values = {
            **valid_vault_values(),
            "vault_accounts_admin_seed_password": secret,
            "vault_accounts_email_username": secret,
            "vault_accounts_email_password": secret,
        }
        yaml_text = "\n".join(f"{key}: {json.dumps(value)}" for key, value in values.items())
        parsed, parse_errors = VAULT.parse_simple_yaml(yaml_text)
        self.assertEqual([], parse_errors)
        self.assertEqual(values, parsed)
        self.assertEqual([], VAULT.validate(parsed))

    def test_credential_pairing_and_line_break_errors_never_echo_secret_values(self):
        secret = "SYNTHETIC-MUST-NOT-APPEAR\nextra"
        values = {
            **valid_vault_values(),
            "vault_accounts_admin_seed_password": secret,
            "vault_accounts_email_username": "fixture-user",
        }
        yaml_text = "\n".join(f"{key}: {json.dumps(value)}" for key, value in values.items())
        parsed, parse_errors = VAULT.parse_simple_yaml(yaml_text)
        errors = parse_errors + VAULT.validate(parsed)
        self.assertIn("vault_accounts_admin_seed_password must be a single-line value", errors)
        self.assertIn(
            "vault_accounts_email_username and vault_accounts_email_password must be set together",
            errors,
        )
        self.assertNotIn(secret, "\n".join(errors))
        self.assertNotIn("SYNTHETIC-MUST-NOT-APPEAR", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
