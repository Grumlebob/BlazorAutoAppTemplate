"""Exercise encrypted vault preparation with disposable fixture credentials."""
from pathlib import Path
import base64
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


class PrepareDataProtectionVaultTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scripts = self.root / 'Deployment/LocalCluster/Scripts'
        for name in ('setup-secrets.sh', 'check-vault.sh', 'Component/lib/data_protection_vault.py',
                     'Component/lib/validate-vault.py'):
            target = self.scripts / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SCRIPTS / name, target)
        self.inventory = self.root / 'Deployment/LocalCluster/inventory/prod'
        self.inventory.mkdir(parents=True)
        self.vault = self.inventory / 'vault.yml'
        self.password = self.root / 'password'
        self.password.write_text('disposable-fixture-vault-password')
        self.password.chmod(0o600)
        tools = self.root / 'bin'
        tools.mkdir()
        gh = tools / 'gh'
        gh.write_text('#!/bin/sh\ntouch "$FORBIDDEN_GH_MARKER"\nexit 99\n')
        gh.chmod(0o755)
        self.env = {**os.environ, 'ANSIBLE_VAULT_PASSWORD_FILE': str(self.password),
                    'ANSIBLE_EDITOR': 'false', 'FORBIDDEN_GH_MARKER': str(self.root / 'gh-called'),
                    'PATH': str(tools) + os.pathsep + os.environ['PATH']}
        self.original = ('vault_postgres_user: fixture_user\n'
                         'vault_postgres_db: fixture_db\n'
                         'vault_postgres_password: fixture_password_1234567890\n'
                         'vault_redis_password: fixture_redis_1234567890\n'
                         'vault_cloudflare_tunnel_token: eyJ' + 'x' * 110 + '\n')
        (self.inventory / 'vault.example.yml').write_text(self.original)
        self.encrypt(self.original)

    def encrypt(self, content):
        plain = self.root / 'fixture-plain.yml'
        plain.write_text(content)
        result = subprocess.run(['ansible-vault', 'encrypt', '--output', str(self.vault), str(plain)],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        plain.unlink()

    def decrypt(self):
        result = subprocess.run(['ansible-vault', 'view', str(self.vault)], env=self.env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def prepare(self):
        return subprocess.run(['bash', str(self.scripts / 'setup-secrets.sh'),
                               '--prepare-data-protection-only'], env=self.env,
                              text=True, capture_output=True, timeout=45)

    def test_adds_real_encrypted_certificate_and_preserves_existing_credentials(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        plain = self.decrypt()
        self.assertTrue(plain.startswith(self.original))
        certificate_line = next(line for line in plain.splitlines()
                                if line.startswith('vault_data_protection_certificate_base64:'))
        certificate = base64.b64decode(certificate_line.split(':', 1)[1].strip())
        self.assertIn(b'-----BEGIN CERTIFICATE-----', certificate)
        self.assertIn(b'-----BEGIN ENCRYPTED PRIVATE KEY-----', certificate)
        self.assertTrue(self.vault.read_text().startswith('$ANSIBLE_VAULT;'))
        self.assertNotIn('fixture_password_1234567890', result.stdout + result.stderr)
        self.assertNotIn('-----BEGIN', result.stdout + result.stderr)
        self.assertFalse((self.root / 'gh-called').exists())

    def test_complete_pair_is_not_rotated_on_resumption(self):
        self.assertEqual(self.prepare().returncode, 0)
        before = self.vault.read_bytes()
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, self.vault.read_bytes())
        self.assertFalse((self.root / 'gh-called').exists())

    def test_partial_pair_fails_without_replacing_encrypted_input(self):
        self.encrypt(self.original + 'vault_data_protection_certificate_password: ' + 'a' * 64 + '\n')
        before = self.vault.read_bytes()
        self.assertNotEqual(self.prepare().returncode, 0)
        self.assertEqual(before, self.vault.read_bytes())
        self.assertFalse((self.root / 'gh-called').exists())

    def test_missing_password_or_vault_does_not_bootstrap_new_credentials(self):
        self.password.unlink()
        before = self.vault.read_bytes()
        self.assertNotEqual(self.prepare().returncode, 0)
        self.assertEqual(before, self.vault.read_bytes())
        self.vault.unlink()
        self.assertNotEqual(self.prepare().returncode, 0)
        self.assertFalse(self.vault.exists())


if __name__ == '__main__':
    unittest.main()
