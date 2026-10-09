"""Run the public status CLI against PATH-stubbed host/Git/GitHub state."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT / "Deployment/LocalSingleNode"
SHA = "a" * 40

STUB = r'''#!/usr/bin/python3
import json
import os
from pathlib import Path
import sys
state = json.loads(os.environ['FIXTURE_STATE'])
name = Path(sys.argv[0]).name
args = sys.argv[1:]
def say(value):
    print(json.dumps(value) if isinstance(value, (dict, list)) else value)
if name == 'uname':
    say('Linux' if '-s' in args else 'fixture-native-kernel')
elif name == 'hostname':
    say(state.get('hostname', 'node-rehearsal'))
elif name == 'id':
    say('operator')
elif name == 'ip':
    if not state.get('machine', True):
        say('')
    elif 'route' in args:
        say('default via 192.0.2.1 dev eth0')
    else:
        say('2: eth0 inet 192.0.2.10/24 scope global eth0')
elif name == 'git':
    if state.get('error'):
        sys.exit(1)
    if 'get-url' in args:
        owner = 'fixture-owner' if not state.get('fork', True) else 'grumlebob'
        say('https://github.com/' + owner + '/fixture-repo.git')
    elif 'status' in args:
        say(' M file' if state.get('dirty') else '')
    elif 'branch' in args:
        say('main' if state.get('repo', True) else 'feature-preserved')
    elif 'rev-parse' in args:
        say('a' * 40)
    elif 'merge-base' in args:
        sys.exit(0)
    else:
        sys.exit(99)
elif name == 'bash':
    if any('doctor.sh' in arg for arg in args):
        sys.exit(0 if state.get('doctor', True) else 1)
    sys.exit(99)
elif name == 'gh':
    if args[:2] == ['auth', 'status']:
        sys.exit(0 if state.get('gh', True) else 1)
    if args[:2] == ['api', 'user']:
        say('fixture-login')
    elif args[0] == 'api' and '/variables?' in args[1]:
        values = {'DEPLOY_TARGETS': 'localsinglenode', 'LOCALSINGLENODE_HOST': 'node-rehearsal'} if state.get('variables', True) else {}
        say({'variables': [{'name': key, 'value': value} for key, value in values.items()]})
    elif args[0] == 'api' and '/runners?' in args[1]:
        runners = [{'name': 'fixture-ci', 'status': 'online', 'labels': [{'name': 'localcluster-books'}]}] if state.get('ci_capacity', True) else []
        if state.get('ci_registered_offline'):
            runners.append({'name': 'existing-ci-preserve', 'status': 'offline', 'labels': [{'name': 'localcluster-books'}]})
        if state.get('runner', True):
            runners.append({'name': 'node-rehearsal-books', 'status': 'online', 'labels': [{'name': 'localsinglenode-books'}]})
        say({'runners': runners})
    elif args[0] == 'api' and '.permissions.admin' in args:
        say('true' if state.get('gh', True) else 'false')
    elif args[:2] == ['run', 'list'] and 'ci.yml' in args:
        say([] if state.get('ci_missing') else [{'databaseId': 123, 'status': 'completed', 'conclusion': 'success' if state.get('ci', True) else 'failure'}])
    elif args[:2] == ['run', 'view']:
        say({'jobs': [{'name': name, 'conclusion': 'success'} for name in ('validate', 'build-test-push')]})
    elif args[:2] == ['run', 'list'] and 'cd-localsinglenode.yml' in args:
        say([{'databaseId': 124, 'status': 'completed', 'conclusion': 'success', 'displayTitle': 'CD LocalSingleNode @ ' + 'a' * 40}] if state.get('deploy', True) else [])
    else:
        sys.exit(98)
else:
    sys.exit(97)
'''


class StatusCliTests(unittest.TestCase):
    def invoke(self, state):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            tools = folder / "bin"
            tools.mkdir()
            for name in ("git", "gh", "uname", "hostname", "ip", "id", "bash"):
                path = tools / name
                path.write_text(STUB)
                path.chmod(0o755)
            etc = folder / "etc/localsinglenode"
            etc.mkdir(parents=True)
            if state.get('root', True):
                owner = 'fixture-owner' if not state.get('fork', True) else 'grumlebob'
                (etc / 'bootstrap.json').write_text(json.dumps(dict(version=1, apps={'books': dict(version=1, node='node-rehearsal', app='books', repo=owner + '/fixture-repo', ci_runner=False), 'other-app': dict(repo='foreign/preserve')})))
            record_path = folder / '.local/share/localsinglenode-setup' / hashlib.sha256(str(ROOT).encode()).hexdigest()[:16] / 'node-rehearsal.json'
            record_path.parent.mkdir(parents=True)
            record = dict(sha=SHA)
            if state.get('verify', True):
                record.update(verified_sha=SHA, verified_address='192.0.2.10', verified_port=80)
            if state.get('ambiguous'):
                record['dispatch_pending'] = True
            record_path.write_text(json.dumps(record))
            environment = {key: value for key, value in os.environ.items() if key not in ('WSL_INTEROP', 'WSL_DISTRO_NAME', 'SUDO_USER')}
            environment.update(PATH=str(tools) + ':/usr/bin:/bin', LOCALSINGLENODE_ETC=str(folder / 'etc'), HOME=str(folder), FIXTURE_STATE=json.dumps(state))
            result = subprocess.run([sys.executable, str(TARGET / 'Scripts/lib/setup_status.py'), '--node', 'node-rehearsal', '--json'], capture_output=True, text=True, env=environment)
            self.assertTrue(result.stdout.strip(), result.stderr)
            return result.returncode, json.loads(result.stdout)

    def test_all_public_cli_steps_and_exit_codes(self):
        cases = [(dict(repo=False), 'repo', 'agent', 10), (dict(dirty=True), 'repo', 'human', 20), (dict(gh=False), 'gh', 'human', 20), (dict(machine=False), 'machine', 'human', 20), (dict(fork=False), 'fork', 'agent', 10), (dict(ci=False), 'ci', 'agent', 10), (dict(ci=False, ci_missing=True), 'ci', 'human', 20), (dict(root=False), 'root', 'human', 20), (dict(variables=False), 'variables', 'agent', 10), (dict(runner=False), 'runner', 'agent', 10), (dict(deploy=False), 'deploy', 'agent', 10), (dict(verify=False), 'verify', 'agent', 10), (dict(deploy=False, ambiguous=True), 'deploy', 'human', 20), (dict(error=True), 'error', 'human', 1), (dict(), 'done', 'none', 0)]
        for state, step, actor, code in cases:
            with self.subTest(state=state):
                actual_code, value = self.invoke(state)
                self.assertEqual((code, step, actor), (actual_code, value['step'], value['actor']), value)

    def test_bootstrap_capacity_deferral(self):
        code, state = self.invoke(dict(ci_capacity=False, fork=False, ci=False, root=False))
        self.assertEqual((20, 'root'), (code, state['step']))
        self.assertIn('--ci-runner', state['command'])
        self.assertNotIn('fork', state['done'])

    def test_offline_existing_ci_registration_is_preserved(self):
        code, state = self.invoke(dict(ci_capacity=False, ci_registered_offline=True, ci=False, root=False))
        self.assertEqual((20, 'root'), (code, state['step']))
        self.assertFalse(state['ci_runner'])
        self.assertNotIn('--ci-runner', state['command'])
        code, state = self.invoke(dict(ci_capacity=False, ci_registered_offline=True, ci=False))
        self.assertEqual((10, 'ci'), (code, state['step']))
        self.assertFalse(state['ci_runner'])

    def test_initial_mixed_case_hostname_reaches_the_one_root_command(self):
        code, state = self.invoke(dict(hostname='Operator-Laptop', root=False))
        self.assertEqual((20, 'root'), (code, state['step']))
        self.assertEqual('Operator-Laptop', state['facts']['name'])
        self.assertIn('Native host: Operator-Laptop', state['human_message'])
        self.assertIn('--node node-rehearsal', state['command'])


if __name__ == '__main__':
    unittest.main()
