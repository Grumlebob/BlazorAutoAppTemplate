"""Exercise backup permissions, isolated restore cleanup and read-only doctor with offline stubs."""
import grp
from datetime import datetime, timedelta, timezone
import io
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

    def test_requested_backup_reports_the_completed_dump_without_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            value = self.fixture(Path(temp))
            folder = Path(value['backup_root'])
            dump = folder / 'books-fixture.dump'
            dump.write_bytes(b'PGDMP-fixture')
            now = datetime.now(timezone.utc)
            (folder / 'last-success').write_text(now.isoformat())
            with patch.object(backup, 'run') as command, patch('sys.stdout', new_callable=io.StringIO) as output:
                backup.report_fresh(value, (now - timedelta(seconds=1)).isoformat())
                command.assert_not_called()
                self.assertIn('Fresh protected backup: books-fixture.dump (13 bytes)', output.getvalue())
                self.assertNotIn('fixture-secret-only', output.getvalue())

    def test_requested_backup_rejects_stale_future_and_naive_markers(self):
        with tempfile.TemporaryDirectory() as temp:
            value = self.fixture(Path(temp))
            folder = Path(value['backup_root'])
            (folder / 'books-fixture.dump').write_bytes(b'PGDMP-fixture')
            now = datetime.now(timezone.utc)
            for completed in (now - timedelta(seconds=1), now + timedelta(minutes=6), now.replace(tzinfo=None)):
                (folder / 'last-success').write_text(completed.isoformat())
                with self.subTest(completed=completed), self.assertRaises(ValueError):
                    backup.report_fresh(value, now.isoformat())

    def test_requested_backup_rejects_missing_empty_and_symlink_dumps(self):
        with tempfile.TemporaryDirectory() as temp:
            value = self.fixture(Path(temp))
            folder = Path(value['backup_root'])
            now = datetime.now(timezone.utc)
            (folder / 'last-success').write_text(now.isoformat())
            with self.assertRaisesRegex(ValueError, 'no app backup'):
                backup.report_fresh(value, now.isoformat())
            dump = folder / 'books-fixture.dump'
            dump.touch()
            with self.assertRaisesRegex(ValueError, 'empty or a symlink'):
                backup.report_fresh(value, now.isoformat())
            dump.unlink()
            dump.symlink_to(Path(value['secrets_file']))
            with self.assertRaisesRegex(ValueError, 'empty or a symlink'):
                backup.report_fresh(value, now.isoformat())

    def test_public_freshness_report_does_not_start_backup_or_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            value = self.fixture(Path(temp))
            now = datetime.now(timezone.utc)
            (Path(value['backup_root']) / 'last-success').write_text(now.isoformat())
            (Path(value['backup_root']) / 'books-fixture.dump').write_bytes(b'PGDMP-fixture')
            arguments = ['backup.py', '--config', '/opt/books/maintenance/settings.json', '--report-fresh-since', now.isoformat()]
            with patch.object(sys, 'argv', arguments), patch.object(backup, 'config', return_value=value), patch.object(backup, 'backup') as create, patch.object(backup, 'verify') as restore, patch('sys.stdout', new_callable=io.StringIO) as output:
                backup.main()
                create.assert_not_called()
                restore.assert_not_called()
                self.assertIn('Fresh protected backup:', output.getvalue())

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
            def command(*args):
                if args[:2] == ('systemctl', 'show'):
                    return 'Id=actions.runner.fixture.service\nActiveState=active\nUser=deploy\nWorkingDirectory=/home/deploy/actions-runner-books'
                if args[0] == 'id':
                    return 'deploy docker'
                if args[0] == 'ip':
                    return json.dumps([dict(ifindex=3, addr_info=[dict(local='192.0.2.10')])])
                if args[0] == 'busctl':
                    return json.dumps(dict(type='iisisu', data=[3, 0, 'node-rehearsal.local', 0, '192.0.2.10', 13]))
                return 'active'
            with patch.object(doctor, 'ETC', etc), patch.object(doctor, 'native', return_value=True), patch.object(doctor, 'command', side_effect=command), patch.object(doctor.shutil, 'disk_usage', return_value=SimpleNamespace(free=21 * 1024 ** 3)):
                checks = doctor.check()
                self.assertEqual(['native-linux', 'runner', 'docker-group', 'firewall', 'caddy', 'secret-mode', 'disk-20GiB', 'mdns'], [item['name'] for item in checks])
                self.assertTrue(all(item['pass'] for item in checks))
                secret.chmod(0o644)
                checks = doctor.check()
                self.assertFalse(next(item for item in checks if item['name'] == 'secret-mode')['pass'])

    def test_mdns_uses_the_lan_interface_when_docker_is_listed_first(self):
        machine = dict(name='Node-Rehearsal', ip='192.0.2.10')
        interfaces = [
            dict(ifindex=4, addr_info=[dict(local='172.30.10.1')]),
            dict(ifindex=7, addr_info=[dict(local=machine['ip'])]),
        ]
        result = dict(type='iisisu', data=[7, 0, 'node-rehearsal.local', 0, machine['ip'], 13])
        with patch.object(doctor, 'command', side_effect=[json.dumps(interfaces), json.dumps(result)]) as command:
            self.assertTrue(doctor.mdns_resolves_lan(machine))
        self.assertEqual(('ResolveHostName', 'iisiu', '7', '0', 'Node-Rehearsal.local', '0', '0'), command.call_args.args[-7:])
        self.assertIn('--timeout=10s', command.call_args.args)

    def test_mdns_rejects_wrong_address_interface_name_and_protocol(self):
        machine = dict(name='node-rehearsal', ip='192.0.2.10')
        interfaces = [dict(ifindex=3, addr_info=[dict(local=machine['ip'])])]
        for position, value in ((0, 4), (1, 1), (2, 'other.local'), (3, 1), (4, '172.30.10.1'), (4, '192.0.2.100')):
            data = [3, 0, 'node-rehearsal.local', 0, machine['ip'], 13]
            data[position] = value
            with self.subTest(position=position, value=value), patch.object(doctor, 'command', side_effect=[json.dumps(interfaces), json.dumps(dict(type='iisisu', data=data))]):
                self.assertFalse(doctor.mdns_resolves_lan(machine))

    def test_mdns_rejects_missing_lan_interface_and_malformed_response(self):
        machine = dict(name='node-rehearsal', ip='192.0.2.10')
        with patch.object(doctor, 'command', return_value='[]') as command:
            self.assertFalse(doctor.mdns_resolves_lan(machine))
            self.assertEqual(1, command.call_count)
        interfaces = [dict(ifindex=3, addr_info=[dict(local=machine['ip'])])]
        for response in ([], {}, dict(type='s', data=['192.0.2.10']), dict(type='iisisu', data=[]), dict(type='iisisu', data=None), dict(type='iisisu', data=[3, 0, None, 0, machine['ip'], 13])):
            with self.subTest(response=response), patch.object(doctor, 'command', side_effect=[json.dumps(interfaces), json.dumps(response)]):
                self.assertFalse(doctor.mdns_resolves_lan(machine))

    def test_mdns_lookup_failure_is_not_accepted(self):
        interfaces = [dict(ifindex=3, addr_info=[dict(local='192.0.2.10')])]
        with patch.object(doctor, 'command', side_effect=[json.dumps(interfaces), ValueError('busctl failed')]):
            with self.assertRaises(ValueError):
                doctor.mdns_resolves_lan(dict(name='node-rehearsal', ip='192.0.2.10'))

    def test_runner_check_does_not_read_deploy_home(self):
        service = 'Id=actions.runner.fixture.service\nActiveState=active\nUser=deploy\nWorkingDirectory=/home/deploy/actions-runner-books'
        foreign = service.replace('runner-books', 'runner-other').replace('fixture.service', 'other.service')
        with patch.object(Path, 'read_text', side_effect=PermissionError('private home')), patch.object(doctor, 'command', return_value=foreign + '\n\n' + service):
            self.assertTrue(doctor.runner_active('books'))
        for output in ('', foreign, service.replace('active', 'inactive'), service.replace('User=deploy', 'User=root'), service + '\n\n' + service):
            with self.subTest(output=output), patch.object(doctor, 'command', return_value=output):
                self.assertFalse(doctor.runner_active('books'))

    def test_operator_address_mismatch_precedes_mutation(self):
        args = SimpleNamespace(user='operator', node='node-rehearsal', github_login='fixture', yes=True, expected_address='192.0.2.11')
        environment = {key: value for key, value in os.environ.items() if key not in ('LOCALSINGLENODE_ETC', 'OPT_ROOT')}
        environment['SUDO_USER'] = 'operator'
        with patch.object(bootstrap, 'native', return_value=True), patch.object(bootstrap.os, 'geteuid', return_value=0), patch.dict(os.environ, environment, clear=True), patch.object(bootstrap.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=1000)), patch.object(bootstrap, 'detect', return_value=dict(name='node-rehearsal', ip='192.0.2.10')), self.assertRaisesRegex(ValueError, 'no changes'):
            bootstrap.guard(args)


if __name__ == '__main__':
    unittest.main()
