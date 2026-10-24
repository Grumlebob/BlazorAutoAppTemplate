"""Operator status snapshot: validated, read-only, operator-readable, and never touching backups."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'publish-status-snapshot.py'
SPEC = importlib.util.spec_from_file_location('publish_status_snapshot', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def status(**overrides):
    value = {
        'mutation': 'none',
        'shared_lock': 'held',
        'target': 'localsinglenode',
        'repository': 'Grumlebob/CarbonCalculator',
        'empty_deployment': 'not-established',
        'current_release': None,
    }
    value.update(overrides)
    return value


class PublishStatusSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'backups'
        self.root.mkdir()
        self.vars = Path(self.temp.name) / 'deployment-vars.json'
        self.vars.write_text(json.dumps({'backup_root': str(self.root)}), encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def write_status(self, value, text=None):
        path = Path(self.temp.name) / 'release-status.out'
        path.write_text(text if text is not None else json.dumps(value) + '\n', encoding='utf-8')
        return path

    def test_rejects_status_that_is_not_read_only(self):
        path = self.write_status(status(mutation='registry-delete'))
        with self.assertRaises(MODULE.SnapshotError):
            MODULE.read_status(path)

    def test_rejects_status_without_the_shared_lock(self):
        path = self.write_status(status(shared_lock='not-held'))
        with self.assertRaises(MODULE.SnapshotError):
            MODULE.read_status(path)

    def test_rejects_other_targets(self):
        path = self.write_status(status(target='localcluster'))
        with self.assertRaises(MODULE.SnapshotError):
            MODULE.read_status(path)

    def test_rejects_empty_or_non_object_input(self):
        with self.assertRaises(MODULE.SnapshotError):
            MODULE.read_status(self.write_status(None, text='\n\n'))
        with self.assertRaises(MODULE.SnapshotError):
            MODULE.read_status(self.write_status(None, text='[1, 2]\n'))

    def test_uses_the_last_json_line_of_the_status_output(self):
        path = self.write_status(None, text='progress line\n' + json.dumps(status()) + '\n')
        self.assertEqual(MODULE.read_status(path)['target'], 'localsinglenode')

    def test_publishes_the_validated_status_with_export_metadata(self):
        source = status(current_release={'app_image': 'ghcr.io/grumlebob/carboncalculator@sha256:abc'})
        target = MODULE.publish(self.write_status(source), self.vars, '40123456789')
        self.assertEqual(target, self.root / 'status' / 'release-status.json')
        document = json.loads(target.read_text(encoding='utf-8'))
        self.assertEqual(sorted(document), ['exported_utc', 'source_run_id', 'status'])
        self.assertEqual(document['source_run_id'], '40123456789')
        self.assertEqual(document['status'], source)
        self.assertTrue(document['exported_utc'].endswith('Z'))

    def test_leaves_existing_backup_artifacts_and_no_temporary_files(self):
        artifact = self.root / 'carboncalculator-20261024T000000000000Z.dump'
        artifact.write_bytes(b'backup')
        MODULE.publish(self.write_status(status()), self.vars, '1')
        self.assertEqual(artifact.read_bytes(), b'backup')
        leftovers = [path.name for path in (self.root / 'status').iterdir() if path.name != 'release-status.json']
        self.assertEqual(leftovers, [])

    def test_replaces_the_previous_snapshot_atomically(self):
        MODULE.publish(self.write_status(status(empty_deployment='first')), self.vars, '1')
        target = MODULE.publish(self.write_status(status(empty_deployment='second')), self.vars, '2')
        self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['status']['empty_deployment'], 'second')

    def test_fails_closed_for_a_missing_backup_root(self):
        self.vars.write_text(json.dumps({'backup_root': str(self.root / 'missing')}), encoding='utf-8')
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            code = MODULE.main(['--status', str(self.write_status(status())), '--deployment-vars', str(self.vars)])
        self.assertEqual(code, 1)
        self.assertIn('not published', output.getvalue())
        self.assertFalse((self.root / 'missing').exists())

    def test_rejects_a_relative_backup_root(self):
        self.vars.write_text(json.dumps({'backup_root': 'relative/backups'}), encoding='utf-8')
        with self.assertRaises(MODULE.SnapshotError):
            MODULE.publish(self.write_status(status()), self.vars, '1')

    def test_passes_the_backup_root_group_to_the_directory_and_file(self):
        calls = []
        real_stat_gid = os.stat(self.root).st_gid
        with patch.object(MODULE.os, 'chown', create=True, side_effect=lambda path, uid, gid: calls.append((Path(path).name, uid, gid))):
            MODULE.publish(self.write_status(status()), self.vars, '1')
        self.assertEqual([name for name, _, _ in calls][:1], ['status'])
        self.assertTrue(all(uid == -1 and gid == real_stat_gid for _, uid, gid in calls))

    @unittest.skipUnless(os.name == 'posix', 'POSIX permission bits')
    def test_modes_keep_the_status_operator_readable_and_private_to_others(self):
        target = MODULE.publish(self.write_status(status()), self.vars, '1')
        self.assertEqual(oct(target.stat().st_mode & 0o777), '0o640')
        self.assertEqual(oct((self.root / 'status').stat().st_mode & 0o777), '0o750')


if __name__ == '__main__':
    unittest.main()
