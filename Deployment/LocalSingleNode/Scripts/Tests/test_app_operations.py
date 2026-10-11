"""Offline ownership, selection and persistence checks for app operations."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS / 'lib'))
import doctor
import ls_settings
import maintenance
from test_settings_fixture import fixture_settings

spec = importlib.util.spec_from_file_location('restart_app', SCRIPTS / 'restart-app-check.py')
restart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restart)


class AppOperationsTests(unittest.TestCase):
    def fixture(self):
        return {service: {'id': service, 'image': 'image', 'started': 'before', 'restarts': 0, 'mounts': []}
                for service in ('web', 'postgres', 'redis')}

    def test_only_web_start_time_changes(self):
        before = self.fixture()
        after = copy.deepcopy(before)
        after['web']['started'] = 'after'
        restart.verify_after(before, after)
        for service, key in (('postgres', 'started'), ('redis', 'id'), ('web', 'image'), ('web', 'id'),
                             ('web', 'mounts'), ('web', 'restarts')):
            broken = copy.deepcopy(after)
            broken[service][key] = 'changed'
            with self.subTest(service=service, key=key), self.assertRaises(ValueError):
                restart.verify_after(before, broken)
        with self.assertRaisesRegex(ValueError, 'new process'):
            restart.verify_after(before, before)

    def test_native_main_user_and_lock_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / 'token').write_text('owned')
            env = {'GITHUB_REF': 'refs/heads/main', 'LOCALCLUSTER_DEPLOY_LOCK_DIR': temporary,
                   'LOCALCLUSTER_DEPLOY_LOCK_TOKEN': 'owned'}
            with patch.dict(os.environ, env, clear=True), patch.object(restart, 'native', return_value=True), patch.object(restart.getpass, 'getuser', return_value='deploy'):
                restart.guards()
                for key, value in (('GITHUB_REF', 'refs/heads/feature'), ('LOCALCLUSTER_DEPLOY_LOCK_TOKEN', 'foreign'),
                                   ('LOCALSINGLENODE_ETC', temporary), ('OPT_ROOT', temporary)):
                    with self.subTest(key=key), patch.dict(os.environ, {key: value}), self.assertRaises(ValueError):
                        restart.guards()
                with patch.object(restart, 'native', return_value=False), self.assertRaises(ValueError):
                    restart.guards()
                with patch.object(restart.getpass, 'getuser', return_value='operator'), self.assertRaises(ValueError):
                    restart.guards()

    def test_container_inventory_rejects_foreign_duplicate_missing_and_stopped(self):
        config = fixture_settings()
        values = [{'Id': service, 'Image': 'image', 'RestartCount': 0, 'Mounts': [],
                   'State': {'Status': 'running', 'StartedAt': 'before'}, 'Config': {'Labels': {
                       'com.docker.compose.service': service, 'com.docker.compose.project': config['app_name'],
                       'localsinglenode.app': config['app_name'], 'com.docker.compose.project.working_dir': config['deploy_root']}}}
                  for service in ('web', 'postgres', 'redis')]
        def inspect(fixture):
            with patch.object(restart, 'command', side_effect=['web\npostgres\nredis', json.dumps(fixture)]):
                return restart.containers(config)
        self.assertEqual({'web', 'postgres', 'redis'}, set(inspect(values)))
        for key in ('com.docker.compose.project', 'localsinglenode.app', 'com.docker.compose.project.working_dir'):
            broken = copy.deepcopy(values)
            broken[0]['Config']['Labels'][key] = 'foreign'
            with self.subTest(key=key), self.assertRaises(ValueError):
                inspect(broken)
        broken = copy.deepcopy(values)
        broken[0]['State']['Status'] = 'exited'
        for fixture in (broken, values[:2], values + values[:1]):
            with self.assertRaises(ValueError):
                inspect(fixture)

    def test_successful_restart_targets_only_web_and_preserves_sibling(self):
        primary = fixture_settings()
        config = {**primary, 'app_name': 'catalog', 'deploy_root': '/opt/catalog'}
        before = self.fixture()
        after = copy.deepcopy(before)
        after['web']['started'] = 'after'
        sibling = self.fixture()
        with patch.object(restart, 'guards'), patch.object(restart, 'settings', side_effect=[config, primary]), \
                patch.object(restart.instance, 'verify_owned'), \
                patch.object(restart, 'containers', side_effect=[before, sibling, after, after, sibling]), \
                patch.object(restart, 'verify_release', return_value={'digest': 'unchanged'}), \
                patch.object(restart, 'catalog', return_value='seed'), patch.object(restart.time, 'sleep'), \
                patch.dict(os.environ, {'GITHUB_SERVER_URL':'https://github.com','GITHUB_REPOSITORY':'example/template'}), \
                patch.object(restart, 'command') as command:
            self.assertEqual(0, restart.main())
            command.assert_called_once_with('docker', 'compose', '--project-directory', '/opt/catalog', 'restart', 'web', timeout=60)

    def test_failed_ownership_or_release_prevents_restart(self):
        for target in ('ownership', 'release', 'catalog'):
            with patch.object(restart, 'guards'), patch.object(restart, 'settings', return_value=fixture_settings()), \
                    patch.object(restart.instance, 'verify_owned', side_effect=ValueError() if target == 'ownership' else None), \
                    patch.object(restart, 'containers', return_value=self.fixture()), \
                    patch.object(restart, 'verify_release', side_effect=ValueError() if target == 'release' else None), \
                    patch.object(restart, 'catalog', side_effect=ValueError() if target == 'catalog' else None), \
                    patch.dict(os.environ, {'GITHUB_SERVER_URL':'https://github.com','GITHUB_REPOSITORY':'example/template'}), \
                    patch.object(restart, 'command') as command, self.assertRaises(ValueError):
                restart.main()
            command.assert_not_called()

    def test_release_uses_independent_protected_expectations(self):
        with tempfile.TemporaryDirectory() as temporary:
            release = {'image':'ghcr.io/example/catalog-react','source_repo_url':'https://github.com/example/template',
                       'frontend_profile':'React','acceptance_profile':'ReactPublicV1','digest':'sha256:fixture',
                       'source_sha':'a'*40,'manifest_schema_version':2,'ci_run_id':42,'ci_run_attempt':1}
            path = Path(temporary) / 'release.json'
            path.write_text(json.dumps(release))
            env = {'APP_IMAGE':release['image'],'GITHUB_SERVER_URL':'https://github.com','GITHUB_REPOSITORY':'example/template',
                   'FRONTEND_PROFILE':'React','ACCEPTANCE_PROFILE':'ReactPublicV1'}
            with patch.dict(os.environ, env), patch.object(restart, 'command') as command:
                self.assertEqual(release, restart.verify_release({'deploy_root':temporary}))
                self.assertIn('verify-release-identity.sh', command.call_args.args[1])
                for key in ('image','source_repo_url','frontend_profile','acceptance_profile'):
                    path.write_text(json.dumps({**release,key:'foreign'}))
                    command.reset_mock()
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        restart.verify_release({'deploy_root':temporary})
                    command.assert_not_called()

    def test_catalog_requires_readiness_and_nonempty_wire_response(self):
        import io
        for value, valid in (({'books':[{'id':1,'title':'Fixture'}]}, True), ({'books':[]}, False),
                             ([], False), ({'items':[1]}, False)):
            responses = [io.BytesIO(b'Healthy'), io.BytesIO(json.dumps(value).encode())]
            responses[0].status = 200
            with self.subTest(value=value), patch.object(restart.urllib.request, 'urlopen', side_effect=responses):
                if valid:
                    self.assertEqual(json.dumps(value,sort_keys=True,separators=(',',':')),restart.catalog(fixture_settings()))
                else:
                    with self.assertRaises(ValueError):
                        restart.catalog(fixture_settings())

    def test_changed_catalog_or_sibling_fails_after_one_restart(self):
        primary = fixture_settings()
        config = {**primary,'app_name':'catalog','deploy_root':'/opt/catalog'}
        before = self.fixture()
        after = copy.deepcopy(before)
        after['web']['started']='after'
        sibling_changed = copy.deepcopy(before)
        sibling_changed['web']['started']='foreign-restart'
        for target in ('catalog','sibling'):
            with patch.object(restart, 'guards'), patch.object(restart, 'settings', side_effect=[config,primary]), \
                    patch.object(restart.instance, 'verify_owned'), \
                    patch.object(restart, 'containers', side_effect=[before,before,after,after,sibling_changed]), \
                    patch.object(restart, 'verify_release', return_value={'digest':'unchanged'}), \
                    patch.object(restart, 'catalog', side_effect=['seed','changed'] if target == 'catalog' else ['seed']*3), \
                    patch.object(restart.time,'monotonic',side_effect=[0,181]), patch.object(restart.time,'sleep'), \
                    patch.dict(os.environ,{'GITHUB_SERVER_URL':'https://github.com','GITHUB_REPOSITORY':'example/template'}), \
                    patch.object(restart,'command') as command, self.assertRaises(ValueError):
                restart.main()
            self.assertEqual(1,command.call_count)

    def test_runner_identity_ignores_additional_settings_selection(self):
        primary = fixture_settings()
        with patch.object(ls_settings, 'settings', return_value=primary) as read:
            self.assertEqual(primary['app_name'], ls_settings.runner_app())
            read.assert_called_once_with(ls_settings.TARGET / 'inventory/group_vars/all.yml')
        self.assertIn('runner_active(runner_app())', (SCRIPTS / 'lib/doctor.py').read_text())
        self.assertIn('runner_app()', (SCRIPTS / 'lib/maintenance.py').read_text())

    def test_workflow_protects_selection_cleanup_and_shared_reboot(self):
        workflow = (ls_settings.ROOT / '.github/workflows/localsinglenode-maintenance.yml').read_text()
        self.assertIn('inputs.app_instance', workflow)
        self.assertIn('vars.LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT', workflow)
        self.assertIn('secrets.LOCALSINGLENODE_APP_INSTANCE', workflow)
        self.assertLess(workflow.index('resolve-app-instance.py'), workflow.index('Protected backup and scoped maintenance'))
        for text in ('Require successful exact-source main CI','acceptance_only=true','Select only one restart',
                     'Additional-app maintenance cannot request a shared host reboot','if: always()', 'restart-app-check.py'):
            self.assertIn(text, workflow)


if __name__ == '__main__':
    unittest.main()
