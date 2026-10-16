from __future__ import annotations

import base64
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

LIB = Path(__file__).resolve().parents[1] / "Component/lib"
sys.path.insert(0, str(LIB))
import data_protection_vault

SPEC = importlib.util.spec_from_file_location("validate_vault", LIB / "validate-vault.py")
assert SPEC and SPEC.loader
validate_vault = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_vault
SPEC.loader.exec_module(validate_vault)


class DataProtectionVaultTests(unittest.TestCase):
    def inspect_state(self, path: Path) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, data_protection_vault.inspect(path))
        return output.getvalue().strip()

    def test_inspect_generates_only_when_both_values_are_absent_or_placeholders(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.yml"
            path.write_text("vault_postgres_password: synthetic\n")
            self.assertEqual("generate", self.inspect_state(path))
            path.write_text(
                "vault_data_protection_certificate_base64: REPLACE_WITH_CERT\n"
                "vault_data_protection_certificate_password: REPLACE_WITH_PASSWORD\n"
            )
            self.assertEqual("generate", self.inspect_state(path))

    def test_inspect_preserves_complete_pair_and_rejects_partial_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault.yml"
            path.write_text(
                "vault_data_protection_certificate_base64: U1lOVEhFVElD\n"
                "vault_data_protection_certificate_password: " + "a" * 64 + "\n"
            )
            self.assertEqual("keep", self.inspect_state(path))
            path.write_text("vault_data_protection_certificate_password: " + "a" * 64 + "\n")
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "partial"):
                data_protection_vault.inspect(path)

    def test_update_replaces_placeholders_and_preserves_other_vault_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "vault.yml"
            certificate = root / "certificate.b64"
            password = root / "password"
            value = base64.b64encode(
                b"-----BEGIN CERTIFICATE-----\nfixture\n"
                b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nfixture\n"
            ).decode("ascii")
            content.write_text(
                "vault_postgres_password: preserved\n"
                "vault_data_protection_certificate_base64: REPLACE_WITH_CERT\n"
                "vault_data_protection_certificate_password: REPLACE_WITH_PASSWORD\n"
            )
            certificate.write_text(value)
            password.write_text("a" * 64)
            data_protection_vault.update(content, certificate, password)
            self.assertIn("vault_postgres_password: preserved", content.read_text())
            self.assertIn(f"vault_data_protection_certificate_base64: {value}", content.read_text())
            self.assertEqual(0o600, content.stat().st_mode & 0o777)

    def test_validator_requires_encrypted_certificate_and_strong_password(self):
        pem = (
            b"-----BEGIN CERTIFICATE-----\nfixture\n"
            b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nfixture\n"
        )
        values = {
            "vault_postgres_user": "fixture",
            "vault_postgres_password": "FixtureDbPassword123456",
            "vault_postgres_db": "fixture",
            "vault_redis_password": "FixtureRedisPassword123456",
            "vault_cloudflare_tunnel_token": "eyJ" + "a" * 120,
            "vault_data_protection_certificate_base64": base64.b64encode(pem).decode("ascii"),
            "vault_data_protection_certificate_password": "b" * 64,
        }
        self.assertEqual([], validate_vault.validate(values))
        self.assertTrue(validate_vault.validate({**values, "vault_data_protection_certificate_password": "weak"}))
        self.assertTrue(validate_vault.validate({**values, "vault_data_protection_certificate_base64": "not-base64"}))


if __name__ == "__main__":
    unittest.main()
