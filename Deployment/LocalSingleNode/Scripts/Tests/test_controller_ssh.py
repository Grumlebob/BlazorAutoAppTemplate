"""Controller pairing preserves existing access and refuses identity changes."""
import argparse
import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "controller-ssh.py"
SPEC = importlib.util.spec_from_file_location("controller_ssh", SCRIPT)
ssh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ssh)
KEY = "ssh-ed25519 " + base64.b64encode(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(32)).decode()
OTHER_KEY = "ssh-ed25519 " + base64.b64encode(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes([1]) * 32).decode()


class ControllerSshTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.home_patch = patch.object(Path, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.args = argparse.Namespace(repo="example/app", controller="main-pc", alias="node-rehearsal")
        self.record = {"version": 1, "hostname": "node-rehearsal", "address": "192.0.2.10",
                       "user": "operator", "host_key": KEY, "controller_key": KEY}

    def test_rejects_malformed_key_and_injected_options(self):
        self.assertEqual(KEY, ssh.public_key(KEY))
        for value in (KEY + " comment", KEY + "\nPermitRootLogin yes", "ssh-ed25519 AAAA", "ssh-rsa AAAA"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ssh.public_key(value)

    def test_authorization_preserves_restricted_keys_and_is_idempotent(self):
        directory = self.home / ".ssh"
        directory.mkdir()
        authorized = directory / "authorized_keys"
        original = 'restrict ' + OTHER_KEY + ' old restriction'
        authorized.write_text(original)
        ssh.authorize_key(directory, KEY)
        expected = original + "\n" + KEY + "\n"
        self.assertEqual(expected, authorized.read_text())
        ssh.authorize_key(directory, KEY)
        self.assertEqual(expected, authorized.read_text())

    def test_does_not_bypass_existing_restrictions_on_controller_key(self):
        directory = self.home / ".ssh"
        directory.mkdir()
        authorized = directory / "authorized_keys"
        original = "restrict " + KEY + "\n"
        authorized.write_text(original)
        with self.assertRaises(ValueError):
            ssh.authorize_key(directory, KEY)
        self.assertEqual(original, authorized.read_text())

    @unittest.skipIf(__import__("os").name == "nt", "Windows symlinks require operator privileges")
    def test_refuses_symlink_authorized_keys_without_changing_target(self):
        directory = self.home / ".ssh"
        directory.mkdir()
        foreign = self.home / "foreign"
        foreign.write_text("preserve")
        (directory / "authorized_keys").symlink_to(foreign)
        with self.assertRaises(ValueError):
            ssh.authorize_key(directory, KEY)
        self.assertEqual("preserve", foreign.read_text())

    def test_connection_rejects_wrong_node_user_address_or_controller(self):
        for change in ({"hostname": "foreign"}, {"user": "root"}, {"user": "deploy"},
                       {"address": "127.0.0.1"}, {"controller_key": OTHER_KEY}, {"host_key": "invalid"}):
            record = {**self.record, **change}
            def variable(repo, name):
                return "node-rehearsal" if name == "LOCALSINGLENODE_HOST" else json.dumps(record)
            with self.subTest(change=change), patch.object(ssh, "get_variable", side_effect=variable), self.assertRaises(ValueError):
                ssh.connection(self.args, KEY)

    def configure(self, command=None):
        actual_run = ssh.run
        def execute(*args, **kwargs):
            if args[0] == "ssh":
                return "hostname node-rehearsal" if command is None else command
            return actual_run(*args, **kwargs)
        with patch.object(ssh, "controller_key", return_value=(self.home / "key", KEY)), \
             patch.object(ssh, "connection", return_value=self.record), \
             patch.object(ssh, "run", side_effect=execute), \
             patch.object(ssh, "verify"):
            ssh.configure(self.args)

    def test_configuration_preserves_existing_config_and_pins_trust(self):
        directory = self.home / ".ssh"
        directory.mkdir()
        main = directory / "config"
        original = "Host foreign\n    User someone\n"
        main.write_text(original)
        self.configure()
        first = main.read_text()
        self.assertTrue(first.endswith(original))
        self.assertEqual(1, first.count("Include "))
        generated = next((directory / "localsinglenode").glob("*.conf")).read_text()
        self.assertIn("StrictHostKeyChecking yes", generated)
        self.assertIn("IdentitiesOnly yes", generated)
        self.assertIn("BatchMode yes", generated)
        self.assertIn("ForwardAgent no", generated)
        self.assertTrue(generated.endswith("Host *\n"))
        self.configure()
        self.assertEqual(first, main.read_text())
        # Use the real OpenSSH parser: includes must preserve other host blocks.
        effective = ssh.run("ssh", "-G", "-F", str(main), self.args.alias)
        self.assertIn("hostname 192.0.2.10", effective)
        self.assertIn("user operator", effective)
        self.assertIn("identitiesonly yes", effective)
        other = ssh.run("ssh", "-G", "-F", str(main), "foreign")
        self.assertIn("user someone", other)

    def test_windows_paths_are_home_relative_for_every_ssh_client(self):
        path = self.home / ".ssh" / "localsinglenode" / "abc.conf"
        self.assertEqual("~/.ssh/localsinglenode/abc.conf", ssh.ssh_path(path, windows=True))
        self.assertEqual(path.as_posix(), ssh.ssh_path(path, windows=False))

    def test_windows_configuration_replaces_absolute_include(self):
        directory = self.home / ".ssh"
        directory.mkdir()
        conf_directory, identity = ssh.paths(self.args.repo, self.args.controller)
        legacy = 'Include "' + (conf_directory / (identity + ".conf")).as_posix() + '"'
        main = directory / "config"
        foreign = "Host foreign\n    User someone\n"
        main.write_text(legacy + "\n" + foreign)
        original = ssh.ssh_path
        with patch.object(ssh, "ssh_path", lambda path: original(path, windows=True)):
            self.configure()
            self.configure()
        expected = 'Include "~/.ssh/localsinglenode/' + identity + '.conf"\n' + foreign
        self.assertEqual(expected, main.read_text())
        generated = (conf_directory / (identity + ".conf")).read_text()
        self.assertIn('IdentityFile "~/key"', generated)
        self.assertIn('UserKnownHostsFile "~/.ssh/localsinglenode/', generated)
        self.assertNotIn(self.home.as_posix(), generated)

    def test_configuration_refuses_changed_host_key(self):
        self.configure()
        main = self.home / ".ssh/config"
        previous = main.read_text()
        self.record["host_key"] = OTHER_KEY
        with self.assertRaises(ValueError):
            self.configure()
        self.assertEqual(previous, main.read_text())

    def test_configuration_refuses_an_existing_alias(self):
        directory = self.home / ".ssh"
        directory.mkdir()
        main = directory / "config"
        original = "Host node-rehearsal\n    HostName other\n"
        main.write_text(original)
        with self.assertRaises(ValueError):
            self.configure(command="hostname other")
        self.assertEqual(original, main.read_text())

    def test_remote_verification_rejects_wrong_identity_and_quotes_probe(self):
        for result in ({"hostname": "foreign", "user": "operator", "uid": 1000},
                       {"hostname": "node-rehearsal", "user": "root", "uid": 0}):
            with patch.object(ssh, "run", return_value=json.dumps(result)) as run, self.assertRaises(ValueError):
                ssh.verify(self.args, self.record)
            self.assertIn("StrictHostKeyChecking=yes", run.call_args.args)
            self.assertTrue(run.call_args.args[-1].startswith("python3 -c "))


if __name__ == "__main__":
    unittest.main()
