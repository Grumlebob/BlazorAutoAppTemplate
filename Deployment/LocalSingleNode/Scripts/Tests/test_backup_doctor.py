"""Exercise backup permissions, isolated restore cleanup and read-only doctor with offline stubs."""
import grp
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import backup
import bootstrap
import doctor
from machine import yaml


class BackupTests(unittest.TestCase):
    def fixture(self, folder):
        secret = folder / 'runtime-secrets.yml'
        secret.write_text('fixture-secret-only')
        secret.chmod(0o600)
        protected = folder / 'backups'
        protected.mkdir(mode=0o750)
        return dict(app_name='books', deploy_root=str(folder / 'app'), backup_root=str(protected), backup_keep_days=7, install_group=grp.getgrgid(os.getgid()).gr_name, secrets_file=str(secret))

    def test_backup_permissions_and_completed_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            value = self.fixture(Path(temp))
            def dump(*args, **kwargs):
                kwargs['stdout'].write(b'PGDMP-fixture')
                return SimpleNamespace(returncode=0)
            with patch.object(backup.subprocess, 'run', side_effect=dump):
                backup.backup(value)
            folder = Path(value['backup_root'])
            file = backup.latest(value)
            self.assertEqual(0o640, file.stat().st_mode & 0o777)
            self.assertEqual(0o640, (folder / 'secrets.yml').stat().st_mode & 0o777)
            self.assertEqual(0o600, Path(value['secrets_file']).stat().st_mode & 0o777)
            self.assertTrue((folder / 'last-success').exists())

    def test_failed_dump_is_not_published(self):
        with tempfile.TemporaryDirectory() as temp:
            value = self.fixture(Path(temp))
            with patch.object(backup.subprocess, 'run', return_value=SimpleNamespace(returncode=1)), self.assertRaisesRegex(ValueError, 'pg_dump failed'):
                backup.backup(value)
            self.assertEqual([], list(Path(value['backup_root']).iterdir()))

    def test_isolated_restore_and_foreign_cleanup_guard(self):
        for foreign in (False, True):
            with self.subTest(foreign=foreign), tempfile.TemporaryDirectory() as temp:
                value = self.fixture(Path(temp))
                dump = Path(value['backup_root']) / 'books-fixture.dump'
                dump.write_bytes(b'PGDMP-fixture')
                calls = []
                def run(*args, **kwargs):
                    calls.append(args)
                    if args[:2] == ('docker', 'inspect'):
                        return json.dumps([dict(Config=dict(Labels={'localsinglenode.restore': 'foreign' if foreign else 'a' * 32}))]).encode()
                    if 'psql' in args:
                        return b'3\n'
                    return b'fixture'
                with patch.object(backup, 'run', side_effect=run), patch.object(backup.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), patch.object(backup.uuid, 'uuid4', return_value=SimpleNamespace(hex='a' * 32)):
                    backup.verify(value, dump)
                launch = calls[0]
                self.assertIn('--network', launch)
                self.assertIn('none', launch)
                self.assertIn('--tmpfs', launch)
                self.assertNotIn('-v', launch)
                removed = any(args[:3] == ('docker', 'rm', '-f') for args in calls)
                self.assertEqual(not foreign, removed)

    def test_manual_restore_rejects_live_database_and_missing_confirmation(self):
        for database, confirm in (('books', 'books'), ('books_restore_check', None), ('other_restore_check', 'books')):
            with patch.object(backup, 'run') as command, self.assertRaises(ValueError):
                backup.restore_replacement({'app_name': 'books'}, Path('/not-used'), database, confirm)
            command.assert_not_called()

    def test_explicit_replacement_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            value = self.fixture(Path(temp))
            dump = Path(value['backup_root']) / 'books-fixture.dump'
            dump.write_bytes(b'PGDMP-fixture')
            with patch.object(backup, 'run', return_value=b'0') as command:
                backup.restore_replacement(value, dump, 'books_restore_check', 'books')
            self.assertEqual(3, command.call_count)
            self.assertIn('createdb', command.call_args_list[1].args)
            self.assertIn('pg_restore', command.call_args_list[2].args)
            self.assertIn('books_restore_check', command.call_args_list[2].args)

    def test_restore_rejects_postgres_identifier_truncation(self):
        app = 'a' * 40
        with patch.object(backup, 'run') as command, self.assertRaises(ValueError):
            backup.restore_replacement({'app_name': app}, Path('/not-used'), app + '_restore_' + 'b' * 20, app)
        command.assert_not_called()


class DoctorTests(unittest.TestCase):
    def test_unsupported_platform_stops_before_services(self):
        with patch.object(doctor, 'native', return_value=False), patch.object(doctor, 'command') as command:
            self.assertEqual([dict(name='native-linux', **{'pass': False})], doctor.check())
            command.assert_not_called()

    def test_every_read_only_check(self):
        with tempfile.TemporaryDirectory() as temp:
            etc = Path(temp)
            (etc / 'localsinglenode').mkdir()
            (etc / 'localsinglenode/machine.yml').write_text(yaml(dict(name='node-rehearsal', ip='192.0.2.10', lan_cidr='192.0.2.0/24', install_user='operator')))
            (etc / 'ufw').mkdir()
            (etc / 'ufw/ufw.conf').write_text('ENABLED=yes\n')
            (etc / 'books').mkdir()
            secret = etc / 'books/secrets.yml'
            secret.write_text('fixture')
            secret.chmod(0o600)
            original = Path.read_text
            def read(path, *args, **kwargs):
                if path.name == '.service':
                    return 'fixture-runner.service'
                return original(path, *args, **kwargs)
            def command(*args):
                if args[0] == 'id':
                    return 'deploy docker'
                if args[0] == 'getent':
                    return '192.0.2.10 STREAM node-rehearsal.local'
                return 'active'
            with patch.object(doctor, 'ETC', etc), patch.object(doctor, 'native', return_value=True), patch.object(Path, 'read_text', read), patch.object(doctor, 'command', side_effect=command), patch.object(doctor.shutil, 'disk_usage', return_value=SimpleNamespace(free=21 * 1024 ** 3)):
                checks = doctor.check()
                self.assertEqual(['native-linux', 'runner', 'docker-group', 'firewall', 'caddy', 'secret-mode', 'disk-20GiB', 'mdns'], [item['name'] for item in checks])
                self.assertTrue(all(item['pass'] for item in checks))
                secret.chmod(0o644)
                checks = doctor.check()
                self.assertFalse(next(item for item in checks if item['name'] == 'secret-mode')['pass'])

    def test_operator_address_mismatch_precedes_mutation(self):
        args = SimpleNamespace(user='operator', node='node-rehearsal', github_login='fixture', yes=True, expected_address='192.0.2.11')
        environment = {key: value for key, value in os.environ.items() if key not in ('LOCALSINGLENODE_ETC', 'OPT_ROOT')}
        environment['SUDO_USER'] = 'operator'
        with patch.object(bootstrap, 'native', return_value=True), patch.object(bootstrap.os, 'geteuid', return_value=0), patch.dict(os.environ, environment, clear=True), patch.object(bootstrap.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=1000)), patch.object(bootstrap, 'detect', return_value=dict(name='node-rehearsal', ip='192.0.2.10')), self.assertRaisesRegex(ValueError, 'no changes'):
            bootstrap.guard(args)


if __name__ == '__main__':
    unittest.main()
