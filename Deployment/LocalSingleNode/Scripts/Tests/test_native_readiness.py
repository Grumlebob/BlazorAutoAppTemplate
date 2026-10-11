"""Offline controller diagnostics: no sudo, workload mutation or private output."""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'native-readiness.py'
SPEC = importlib.util.spec_from_file_location('native_readiness', SCRIPT)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
PAYLOAD = {'expected_host': 'node-rehearsal',
           'source_repo_url': 'https://github.com/fixture-owner/candidate',
           'settings_yaml': 'app_name: candidate-app\n'}


class NativeReadinessTests(unittest.TestCase):
    def test_native_identity_and_deployment_user_are_required(self):
        with patch.object(probe, 'native', return_value=True), \
                patch.object(probe.os, 'geteuid', return_value=1000), \
                patch.object(probe, 'command', return_value='deploy'), \
                patch.object(probe.socket, 'gethostname', return_value='node-rehearsal'), \
                patch.object(probe, 'read_yaml', return_value={'name': 'node-rehearsal'}):
            probe.verify(PAYLOAD)
            for bad in ({**PAYLOAD, 'expected_host': 'foreign-node'},
                        {**PAYLOAD, 'source_repo_url': 'https://example.test/repo'},
                        {**PAYLOAD, 'extra': 'untrusted'}):
                with self.subTest(keys=sorted(bad)), self.assertRaises(ValueError):
                    probe.verify(bad)
            with patch.object(probe, 'command', return_value='operator'), self.assertRaises(ValueError):
                probe.verify(PAYLOAD)
            with patch.object(probe.os, 'geteuid', return_value=0), self.assertRaises(ValueError):
                probe.verify(PAYLOAD)
            with patch.object(probe, 'native', return_value=False), self.assertRaises(ValueError):
                probe.verify(PAYLOAD)

    def test_probe_uses_default_collision_gate_and_removes_private_file(self):
        for collision_failure in (False, True):
            with self.subTest(collision_failure=collision_failure), tempfile.TemporaryDirectory() as directory:
                current = {'app_name': 'books', 'backup_root': directory}
                containers = [{'Config': {'Labels': {'localsinglenode.app': 'books'}},
                               'State': {'Running': True, 'Health': {'Status': 'healthy'}}}] * 3
                def command(*args):
                    if args[:2] == ('docker', 'info'):
                        return '/fixture/docker' if args[-1] == '{{.DockerRootDir}}' else 'fixture-version'
                    if args[:2] == ('docker', 'ps'):
                        return 'fixture-container'
                    if args[:2] == ('docker', 'inspect'):
                        return json.dumps(containers)
                    if args[:3] == ('docker', 'network', 'ls'):
                        return 'fixture-network'
                    if args[:3] == ('docker', 'network', 'inspect'):
                        return '[]'
                    self.fail('Unexpected command: ' + args[0])
                def collision(source, **kwargs):
                    self.assertEqual(PAYLOAD['source_repo_url'], source)
                    self.assertEqual({'settings_file'}, set(kwargs))
                    path = kwargs['settings_file']
                    self.assertEqual(PAYLOAD['settings_yaml'], path.read_text())
                    self.assertEqual(0o600, path.stat().st_mode & 0o777)
                    if collision_failure:
                        raise ValueError('private installation details')
                with patch.object(probe, 'verify'), \
                        patch.object(probe, 'configured_identity', return_value=current), \
                        patch.object(probe, 'settings', side_effect=lambda path=None: current if path is None else {'app_name': 'candidate-app'}), \
                        patch.object(probe.doctor, 'check', return_value=[{'pass': True}]), \
                        patch.object(probe, 'command', side_effect=command), \
                        patch.object(probe, 'backup_freshness', return_value='fresh'), \
                        patch.object(probe, 'capacity', return_value='adequate'), \
                        patch.object(probe.collisions, 'check', side_effect=collision), \
                        patch.dict(os.environ, {'RUNNER_TEMP': directory}):
                    result = probe.inspect(PAYLOAD)
                self.assertEqual('fail' if collision_failure else 'pass', result['collision'])
                self.assertEqual('healthy', result['existing_app'])
                self.assertEqual([], list(Path(directory).iterdir()))
                self.assertNotIn('private installation details', json.dumps(result))

    def test_invalid_settings_file_is_validated_before_host_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.yml'
            path.write_text('app_name: candidate-app\n')
            with patch.object(probe.collisions, 'command') as command, self.assertRaisesRegex(ValueError, 'missing or unknown'):
                probe.collisions.check(PAYLOAD['source_repo_url'], settings_file=path)
            command.assert_not_called()

    def test_capacity_floor_and_insufficient_available_memory(self):
        for available, expected in ((4 * 1024 ** 2, 'adequate'), (3 * 1024 ** 2, 'inadequate')):
            memory = f'MemTotal: {7 * 1024 ** 2} kB\nMemAvailable: {available} kB\n'
            with patch.object(Path, 'read_text', return_value=memory), \
                    patch.object(probe.os, 'cpu_count', return_value=4), \
                    patch.object(probe.os, 'getloadavg', return_value=(0, 0, 0)), \
                    patch.object(probe.doctor.shutil, 'disk_usage', return_value=SimpleNamespace(free=40 * 1024 ** 3)):
                self.assertEqual(expected, probe.capacity())
                with patch.object(probe.os, 'getloadavg', return_value=(4, 4, 4)):
                    self.assertEqual('inadequate', probe.capacity())

    def test_private_errors_are_not_printed(self):
        with patch.object(probe.sys, 'argv', ['native-readiness.py']), \
                patch.dict(os.environ, {'READINESS_CANDIDATE': json.dumps(PAYLOAD)}), \
                patch.object(probe, 'inspect', side_effect=ValueError('private installation details')), \
                redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
            self.assertEqual(1, probe.main())
            self.assertEqual('', output.getvalue())
            self.assertNotIn('private installation details', error.getvalue())

    def test_configured_app_ownership_is_required(self):
        config = {'app_name': 'books', 'deploy_root': '/opt/books', 'backup_root': '/opt/books-backups'}
        identity = {**config, 'source_repo_url': 'https://github.com/fixture-owner/host-repo'}
        with patch.object(probe, 'settings', return_value=config), \
                patch.object(Path, 'is_symlink', return_value=False), \
                patch.dict(os.environ, {'GITHUB_REPOSITORY': 'fixture-owner/host-repo'}):
            with patch.object(Path, 'read_text', return_value=json.dumps(identity)):
                self.assertEqual(config, probe.configured_identity())
            for bad in ([], {}, {**identity, 'source_repo_url': PAYLOAD['source_repo_url']},
                        {**identity, 'deploy_root': '/opt/foreign'}):
                with patch.object(Path, 'read_text', return_value=json.dumps(bad)), self.assertRaises(ValueError):
                    probe.configured_identity()


if __name__ == '__main__':
    unittest.main()
