"""Offline regression fixtures. No root bootstrap, runner registration or host mutation."""
import importlib
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
import bootstrap
import collisions
import doctor
import machine
import maintenance
import runner
import setup_status
from ls_settings import ROOT, TARGET, read_yaml, settings

FACTS = {"name": "node-rehearsal", "ip": "192.0.2.10", "lan_cidr": "192.0.2.0/24", "install_user": "operator"}


class MachineTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(FACTS, machine.validate(FACTS, False))

    def test_hostnames_preserve_case_and_reject_invalid_labels(self):
        for name in ('Operator-Laptop', '7demo', 'a' * 63):
            self.assertEqual(name, machine.validate({**FACTS, 'name': name}, False)['name'])
        for name in ('-node', 'node-', 'node_name', 'a' * 64, None, True, False):
            with self.assertRaisesRegex(ValueError, 'hostname'):
                machine.validate({**FACTS, 'name': name}, False)

    def test_fact_writer_preserves_scalar_like_names(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'machine.yml'
            for name in ('false', 'true', '7', 'Operator-Laptop'):
                facts = {**FACTS, 'name': name}
                source.write_text(machine.yaml(facts))
                self.assertEqual(facts, read_yaml(source, node=True))

    def test_reject_bad_facts(self):
        for key, value in (("name", "REPLACE_WITH_NAME"), ("ip", "bad"), ("ip", "127.0.0.1"), ("ip", str(ipaddress.IPv4Address(0))), ("ip", "192.0.2.0"), ("ip", "192.0.2.255"), ("install_user", "root"), ("install_user", "deploy")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                machine.validate({**FACTS, key: value}, False)

    def test_address_outside_cidr(self):
        with self.assertRaisesRegex(ValueError, "LAN CIDR"):
            machine.validate({**FACTS, "ip": "192.0.2.130", "lan_cidr": "192.0.2.0/25"}, False)

    def test_hostname_guard(self):
        with patch.object(machine, "command", return_value="other-node"), self.assertRaises(ValueError):
            machine.validate(FACTS)

    def test_detect_and_preserve_install_user(self):
        def command(*args):
            return {("ip", "-4", "-o", "route", "show", "default"): "default via 192.0.2.1 dev eth0", ("ip", "-4", "-o", "address", "show", "dev", "eth0", "scope", "global"): "2: eth0 inet 192.0.2.10/24 scope global eth0", ("hostname",): "node-rehearsal", ("id", "-un"): "deploy"}[args]
        with tempfile.TemporaryDirectory() as temp:
            previous = Path(temp) / "machine.yml"
            previous.write_text(machine.yaml(FACTS))
            with patch.object(machine, "command", side_effect=command), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(FACTS, machine.detect(previous))

    def test_missing_route(self):
        with patch.object(machine, "command", return_value=""), self.assertRaisesRegex(ValueError, "default route"):
            machine.detect()

    def test_settings_shape(self):
        self.assertEqual("books", settings()["app_name"])
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "settings.yml"
            file.write_text("app_name: books\napp_name: other\n")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                read_yaml(file)

    def test_inventory_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            source, result = Path(temp) / "machine.yml", Path(temp) / "hosts.yml"
            source.write_text(machine.yaml(FACTS))
            with patch.object(machine, "command", side_effect=lambda *args: "node-rehearsal" if args == ("hostname",) else "operator"), patch.object(sys, "argv", ["machine.py", "inventory", "--machine", str(source), "--output", str(result)]):
                machine.main()
            self.assertEqual('all:\n  hosts:\n    "node-rehearsal":\n      ansible_connection: local\n      ansible_python_interpreter: /usr/bin/python3\n      node_ip: "192.0.2.10"\n      lan_cidr: "192.0.2.0/24"\n      install_user: "operator"\n      install_group: "operator"\n', result.read_text())


class SetupTests(unittest.TestCase):
    def checks(self):
        result = {key: True for key in ("platform", "repo", "tools", "gh", "machine", "fork", "ci", "root", "variables", "runner", "deploy", "verify", "ci_capacity")}
        result["login"] = "fixture-login"
        return result

    def test_each_next_actor(self):
        for name, actor in (("platform", "human"), ("repo", "agent"), ("tools", "agent"), ("gh", "human"), ("machine", "human"), ("fork", "agent"), ("ci", "agent"), ("root", "human"), ("variables", "agent"), ("runner", "agent"), ("deploy", "agent"), ("verify", "agent")):
            checks = self.checks()
            checks[name] = False
            result, code = setup_status.choose(checks, "node-rehearsal", "books", FACTS, "fixture-owner/fixture-repo", False)
            self.assertEqual((name, actor, 20 if actor == "human" else 10), (result["step"], result["actor"], code))
            if name == "platform":
                self.assertNotIn("bootstrap", result["command"])
            if name == "machine":
                checks["machine_error"] = "Detected address differs from the operator-provided target; stop before bootstrap"
                result, code = setup_status.choose(checks, "node-rehearsal", "books", FACTS, "fixture-owner/fixture-repo", False)
                self.assertEqual(20, code)
                self.assertEqual(checks["machine_error"], result["human_message"])
                self.assertEqual("", result["command"])

    def test_done(self):
        value, code = setup_status.choose(self.checks(), "node-rehearsal", "books", FACTS, "fixture-owner/fixture-repo", False)
        self.assertEqual(("done", "none", 0), (value["step"], value["actor"], code))

    def test_deferred_ci_and_fork(self):
        values = self.checks()
        values.update(ci_capacity=False, fork=False, ci=False, root=False)
        result, _ = setup_status.choose(values, "node-rehearsal", "books", FACTS, "fixture-owner/fixture-repo", True)
        self.assertEqual("root", result["step"])
        self.assertIn("--ci-runner", result["command"])
        self.assertNotIn("fork", result["done"])
        self.assertNotIn("ci", result["done"])

    def test_dirty_repo_and_ambiguous_dispatch(self):
        for step, extra in (("repo", "repo_human"), ("deploy", "deploy_ambiguous"), ("ci", "ci_missing")):
            values = self.checks()
            values.update({step: False, extra: True})
            result, code = setup_status.choose(values, "node-rehearsal", "books", FACTS, "fixture-owner/fixture-repo", False)
            self.assertEqual(("human", 20, ""), (result["actor"], code, result["command"]))

    def test_cli_unsupported_platforms(self):
        for system, release in (("Windows_NT", "fixture"), ("Linux", "microsoft-standard-WSL2")):
            with tempfile.TemporaryDirectory() as temp:
                stub = Path(temp) / "uname"
                stub.write_text(f"#!/bin/sh\nif [ \"$1\" = -s ]; then echo {system}; else echo {release}; fi\n")
                stub.chmod(0o755)
                environment = {key: value for key, value in os.environ.items() if key not in ("WSL_INTEROP", "WSL_DISTRO_NAME")}
                environment["PATH"] = temp + ":" + os.environ["PATH"]
                output = subprocess.run(["bash", str(TARGET / "Scripts/setup-status.sh"), "--node", "node-rehearsal", "--json"], capture_output=True, text=True, env=environment)
                self.assertEqual(20, output.returncode, output.stderr)
                state = json.loads(output.stdout)
                self.assertEqual("platform", state["step"])
                self.assertEqual("", state["command"])
                rejected = subprocess.run(["bash", str(TARGET / "Scripts/bootstrap-node.sh"), "--node", "node-rehearsal", "--user", "operator", "--github-login", "fixture", "--yes"], capture_output=True, text=True, env=environment)
                self.assertNotEqual(0, rejected.returncode)
                self.assertNotIn("Step 1", rejected.stdout)

    def test_bootstrap_root_and_sudo_user_guards(self):
        from types import SimpleNamespace
        args = SimpleNamespace(user="operator", node="node-rehearsal", github_login="fixture", yes=True, expected_address=None)
        with patch.object(bootstrap, "native", return_value=True), patch.object(bootstrap.os, "geteuid", return_value=1000), self.assertRaisesRegex(ValueError, "operator"):
            bootstrap.guard(args)
        with patch.object(bootstrap, "native", return_value=True), patch.object(bootstrap.os, "geteuid", return_value=0), patch.dict(os.environ, {"SUDO_USER": ""}), self.assertRaisesRegex(ValueError, "SUDO_USER"):
            bootstrap.guard(args)

    def test_read_error_is_exit_one(self):
        with patch.object(setup_status, "native", return_value=True), patch.object(setup_status, "repository", side_effect=ValueError("bad origin")), self.assertRaisesRegex(ValueError, "bad origin"):
            setup_status.status("node-rehearsal")


class CollisionTests(unittest.TestCase):
    def check(self, directory, scripts):
        with patch.object(collisions, "ETC", directory / "etc"), patch.dict(os.environ, {"OPT_ROOT": str(directory / "opt")}), patch.object(collisions, "command", side_effect=scripts):
            collisions.check("https://github.com/fixture-owner/fixture-repo")

    def test_empty_and_foreign_socket(self):
        def script(*args):
            return "State Recv-Q Send-Q Local Peer\n" if args[0] == "ss" else ""
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.check(folder, script)
            with self.assertRaisesRegex(ValueError, "socket"):
                self.check(folder, lambda *args: 'State Recv-Q Send-Q Local Peer\nLISTEN 0 128 *:8080 *:* users:(("other",pid=2,fd=4))' if args[0] == 'ss' else '')

    def test_foreign_root_and_compose(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            foreign = folder / "opt/other/docker-compose.yml"
            foreign.parent.mkdir(parents=True)
            foreign.write_text("fixture")
            with self.assertRaisesRegex(ValueError, "Port collision"):
                self.check(folder, lambda *args: json.dumps({"services": {"web": {"ports": [{"published": "8080"}]}}}))
            foreign.unlink()
            own = folder / "opt/books"
            own.mkdir()
            (own / "foreign-file").write_text("unowned")
            with self.assertRaisesRegex(ValueError, "Unowned"):
                self.check(folder, lambda *args: '')

    def test_foreign_caddy_and_known_root(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            file = folder / "etc/caddy/Caddyfile"
            file.parent.mkdir(parents=True)
            file.write_text("foreign custom config")
            with self.assertRaisesRegex(ValueError, "Foreign"):
                self.check(folder, lambda *args: '')
            file.write_bytes((ROOT / "Deployment/Common/caddy/Caddyfile").read_bytes())
            self.check(folder, lambda *args: "State Recv-Q Send-Q Local Peer\n" if args[0] == 'ss' else '')

    def test_foreign_secret_directory_is_never_adopted(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            secrets = folder / 'etc/books'
            secrets.mkdir(parents=True)
            (secrets / 'secrets.yml').write_text('foreign fixture')
            with self.assertRaisesRegex(ValueError, 'runtime secret directory'):
                self.check(folder, lambda *args: '')

    def test_docker_subnet_cannot_overlap_lan(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            facts = folder / 'etc/localsinglenode/machine.yml'
            facts.parent.mkdir(parents=True)
            facts.write_text(machine.yaml({**FACTS, 'ip': '172.30.10.20', 'lan_cidr': '172.30.10.0/24'}))
            with self.assertRaisesRegex(ValueError, 'deployment LAN'):
                self.check(folder, lambda *args: '')

    def test_owned_container_listener(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            marker = folder / "etc/localsinglenode/apps/books.json"
            marker.parent.mkdir(parents=True)
            marker.write_text(json.dumps({"source_repo_url": "https://github.com/fixture-owner/fixture-repo", "deploy_root": "/opt/books", "backup_root": "/opt/books-backups"}))
            def script(*args):
                if args[:3] == ("docker", "ps", "-q"):
                    return "owned-id"
                if args[:2] == ("docker", "inspect"):
                    return json.dumps([{"Config": {"Labels": {"com.docker.compose.project": "books", "localsinglenode.app": "books"}}, "NetworkSettings": {"Ports": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}}}])
                if args[0] == 'ss':
                    return 'State Recv-Q Send-Q Local Peer\nLISTEN 0 128 127.0.0.1:8080 *:* users:(("docker-proxy",pid=2,fd=4))'
                return ''
            self.check(folder, script)

    def test_repository_case_matches_but_foreign_identity_and_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            marker = folder / 'etc/localsinglenode/apps/books.json'
            marker.parent.mkdir(parents=True)
            identity = dict(source_repo_url='https://github.com/Fixture-Owner/Fixture-Repo', deploy_root='/opt/books', backup_root='/opt/books-backups')
            marker.write_text(json.dumps(identity))
            self.check(folder, lambda *args: '')
            for key, value in (('source_repo_url', 'https://github.com/Other-Owner/Fixture-Repo'), ('source_repo_url', None), ('deploy_root', '/opt/other'), ('backup_root', '/opt/other-backups')):
                marker.write_text(json.dumps({**identity, key: value}))
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'different repository or root'):
                    self.check(folder, lambda *args: '')

    def test_builtin_docker_networks_have_no_subnets_and_foreign_overlap_still_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            marker = folder / 'etc/localsinglenode/apps/books.json'
            marker.parent.mkdir(parents=True)
            marker.write_text(json.dumps(dict(source_repo_url='https://github.com/fixture-owner/fixture-repo', deploy_root='/opt/books', backup_root='/opt/books-backups')))
            networks = [
                dict(Name='host', Labels=None, IPAM=dict(Driver='default', Config=None)),
                dict(Name='none', IPAM=None),
                dict(Name='bridge', Labels={}, IPAM=dict(Config=[dict(Subnet='172.30.20.0/24')])),
                dict(Name='books_default', Labels={'com.docker.compose.project': 'books'}, IPAM=dict(Config=[dict(Subnet='172.30.10.0/24')])),
            ]
            def script(*args):
                if args[:3] == ('docker', 'network', 'ls'):
                    return 'host-id\nnone-id\nbridge-id'
                if args[:3] == ('docker', 'network', 'inspect'):
                    return json.dumps(networks)
                return ''
            self.check(folder, script)
            networks.append(dict(Name='foreign', IPAM=dict(Config=[dict(Subnet='172.30.10.0/24')])))
            with self.assertRaisesRegex(ValueError, 'foreign runtime network'):
                self.check(folder, script)


class RunnerRecoveryTests(unittest.TestCase):
    def recovery(self, directory, active=False):
        from types import SimpleNamespace
        registration = {"runners": [{"name": "node-rehearsal-books", "labels": [{"name": "localsinglenode-books"}]}]}
        identity = {"agentName": "node-rehearsal-books", "gitHubUrl": "https://github.com/fixture-owner/fixture-repo"}
        (directory / '.runner').write_text(json.dumps(identity))
        result = SimpleNamespace(returncode=0 if active else 3, stdout='active' if active else 'inactive')
        with patch.object(runner, 'native', return_value=True), patch.object(runner.os, 'geteuid', return_value=0), patch.dict(os.environ, {'SUDO_USER': 'operator'}), patch.object(runner, 'Path', return_value=directory), patch.object(runner, 'command', return_value=json.dumps(registration)), patch.object(runner.subprocess, 'run', return_value=result) as execute:
            runner.install('operator', 'fixture-owner/fixture-repo', 'node-rehearsal', False)
            return execute.call_args_list

    def test_missing_service_is_installed_without_reregistration(self):
        with tempfile.TemporaryDirectory() as temp:
            calls = self.recovery(Path(temp))
            self.assertEqual(['install', 'start'], [call.args[0][1] for call in calls])

    def test_partial_service_start_is_retried_only_with_owned_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / '.service').write_text('actions.runner.fixture.service')
            with self.assertRaisesRegex(ValueError, 'inspect it manually'):
                self.recovery(directory)
            (directory / '.installing.json').write_text(json.dumps({'repo': 'fixture-owner/fixture-repo', 'name': 'node-rehearsal-books'}))
            calls = self.recovery(directory)
            self.assertEqual('start', calls[-1].args[0][1])
            self.assertFalse((directory / '.installing.json').exists())

    def test_active_matching_service_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / '.service').write_text('actions.runner.fixture.service')
            calls = self.recovery(directory, active=True)
            self.assertEqual(1, len(calls))
            self.assertEqual('systemctl', calls[0].args[0][0])


class MaintenanceTests(unittest.TestCase):
    def test_bootstrap_refreshes_mdns_for_the_approved_hostname(self):
        text = (TARGET / 'ansible/playbooks/PrepareSingleNode.yml').read_text()
        task = text.split('- name: Enable native name resolution', 1)[1].split('- name: Enable Caddy', 1)[0]
        self.assertIn('name: avahi-daemon', task)
        self.assertIn('state: restarted', task)

    def test_http_acceptance_avoids_readonly_home_assignment(self):
        import re
        text = (ROOT / 'Scripts/Test-DeployedSite.ps1').read_text()
        self.assertIsNone(re.search(r'\$home\s*=', text, re.IGNORECASE))
        self.assertFalse(any(ord(character) < 32 and character not in '\n\r\t' for character in text))
        self.assertIn(r'<input\b[^>]*>', text)
        self.assertIn('$registrationSession', text)
        self.assertIn('$loginSession', text)
        self.assertIn("'delete-user'", text)

    def test_image_ownership_retention_and_container_protection(self):
        now = datetime.now(timezone.utc)
        release = {"image": "ghcr.io/fixture-owner/books", "digest": "sha256:" + "a" * 64, "source_repo_url": "https://github.com/fixture-owner/fixture-repo"}
        base = {"Config": {"Labels": {"org.opencontainers.image.source": release["source_repo_url"]}}, "RepoTags": [release["image"] + ":old"], "Created": (now - timedelta(hours=169)).isoformat()}
        images = [{**base, "Id": "old"}, {**base, "Id": "used"}, {**base, "Id": "current", "RepoDigests": [release["image"] + '@' + release["digest"]]}, {**base, "Id": "foreign", "Config": {"Labels": {"org.opencontainers.image.source": "foreign"}}}, {**base, "Id": "new", "Created": now.isoformat()}]
        self.assertEqual(["old"], maintenance.candidates(images, [{"Image": "used"}], release, now))

    def test_historical_ci_proof_and_foreign_reference_preservation(self):
        now = datetime.now(timezone.utc)
        release = dict(image='ghcr.io/fixture-owner/books', digest='sha256:' + 'a' * 64, source_repo_url='https://github.com/fixture-owner/fixture-repo')
        image = dict(Id='old', Created=(now - timedelta(hours=169)).isoformat(), RepoTags=[release['image'] + ':old'], Config=dict(Labels={'localcluster.ci.repository': 'fixture-owner/fixture-repo', 'localcluster.ci.owner': 'ci-build'}))
        self.assertEqual(['old'], maintenance.candidates([image], [], release, now))
        image['RepoTags'].append('ghcr.io/foreign-owner/other:keep')
        self.assertEqual([], maintenance.candidates([image], [], release, now))

    def test_backup_lock_order(self):
        text = (TARGET / "Scripts/run-maintenance.sh").read_text()
        self.assertLess(text.index("systemctl start --wait"), text.index("with-deploy-lock.sh"))
        self.assertLess(text.index("systemctl start --wait"), text.index("--report-fresh-since"))
        self.assertLess(text.index("--report-fresh-since"), text.index("with-deploy-lock.sh"))
        self.assertNotIn("systemctl start", (TARGET / "Scripts/maintenance-under-lock.sh").read_text())

    def test_root_owned_completion_reboot(self):
        text = (TARGET / "Scripts/wait-for-successful-run-reboot.sh").read_text()
        self.assertLess(text.index("completed:success"), text.index("sleep 30"))
        self.assertLess(text.index("sleep 30"), text.index("systemctl reboot"))
        self.assertIn("completed:*)", text)


if __name__ == "__main__":
    unittest.main()
