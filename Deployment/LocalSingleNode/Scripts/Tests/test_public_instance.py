from contextlib import redirect_stderr, redirect_stdout
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from test_settings_fixture import fixture_settings

SPEC = importlib.util.spec_from_file_location("public_instance", Path(__file__).resolve().parents[1] / "configure-public-deployment.py")
assert SPEC and SPEC.loader
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class PublicInstanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_path = Path(self.temp.name) / "config.json"
        self.config = {"account_id": "a" * 32, "zone_name": "example.invalid", "tunnel_name": "catalog-public",
                       "public_hostname": "catalog.example.invalid", "origin_port": 18085}
        self.state = {"identity": hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest(),
                      "dns_id": "owned-dns", "tunnel_id": "123e4567-e89b-42d3-a456-426614174000"}
        self.token = base64.b64encode(json.dumps({"a": "a" * 32, "t": self.state["tunnel_id"], "s": "fixture-secret"}).encode()).decode()
        primary = fixture_settings()
        self.candidate = {**primary, "app_name": "catalog", "deploy_root": "/opt/catalog",
                          "backup_root": "/opt/catalog-backups", "app_port": 18080, "postgres_port": 15432,
                          "redis_port": 16379, "lan_http_port": 18081, "docker_subnet": "172.30.20.0/24"}
        self.instance = {"schema_version": 1, "frontend_profile": "React", "settings": self.candidate, "public": {}}
        self.repo_variables = {"LOCALSINGLENODE_HOST": "node-rehearsal", "LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT": "catalog",
                               "LOCALSINGLENODE_PUBLIC_HOSTNAME": "primary.example.invalid"}
        self.environment_variables = []
        self.writes = []

    def run_publisher(self, additional=True):
        self.config_path.write_text(json.dumps(self.config))
        arguments = ["publish", "--config", str(self.config_path), "--state", "state.json", "--connector-token-file", "connector.token",
                     "--repo", "example/template", "--node", "node-rehearsal"]
        if additional:
            arguments += ["--environment", "catalog", "--instance-config-file", "instance.json"]

        def gh(*args, input_value=None):
            if args[0] == "api":
                return json.dumps([{"variables": [{"name": key, "value": value} for key, value in self.repo_variables.items()]}])
            if args[:2] == ("variable", "list"):
                return json.dumps(self.environment_variables)
            self.writes.append((args, input_value))
            return ""

        def protected(path):
            return {"state.json": json.dumps(self.state), "connector.token": self.token, "instance.json": json.dumps(self.instance)}[str(path)]

        with mock.patch.object(sys, "argv", arguments), mock.patch.object(publisher, "settings", return_value=fixture_settings()), \
                mock.patch.object(publisher, "protected_read", side_effect=protected), mock.patch.object(publisher, "gh", side_effect=gh), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return publisher.main()

    def test_additional_public_secrets_and_variables_are_scoped_to_environment(self):
        # Patch only the instance conversion here; its production validation has separate fixtures below.
        public = {"hostname": self.config["public_hostname"], "tunnel_id": self.state["tunnel_id"], "origin_port": self.config["origin_port"]}
        payload = {**self.instance, "public": public}
        with mock.patch.object(publisher, "additional_configuration", return_value=(payload, self.candidate)):
            self.assertEqual(self.run_publisher(), 0)
        self.assertEqual(len(self.writes), 5)
        for arguments, _ in self.writes:
            self.assertIn("--env", arguments)
            self.assertEqual(arguments[arguments.index("--env") + 1], "catalog")
            self.assertNotIn(self.token, arguments)
        metadata = next(value for args, value in self.writes if args[1:3] == ("set", "LOCALSINGLENODE_APP_INSTANCE"))
        self.assertEqual(json.loads(metadata)["public"], public)
        self.assertEqual(self.repo_variables["LOCALSINGLENODE_PUBLIC_HOSTNAME"], "primary.example.invalid")

    def test_existing_different_environment_public_values_fail_without_writes(self):
        self.environment_variables = [{"name": "LOCALSINGLENODE_PUBLIC_HOSTNAME", "value": "foreign.example.invalid"}]
        with mock.patch.object(publisher, "additional_configuration", return_value=(self.instance, self.candidate)):
            self.assertEqual(self.run_publisher(), 1)
        self.assertEqual(self.writes, [])

    def test_wrong_additional_environment_fails_without_writes(self):
        self.repo_variables["LOCALSINGLENODE_ADDITIONAL_ENVIRONMENT"] = "different"
        with mock.patch.object(publisher, "additional_configuration", return_value=(self.instance, self.candidate)):
            self.assertEqual(self.run_publisher(), 1)
        self.assertEqual(self.writes, [])

    def test_primary_different_public_variables_still_refused(self):
        self.assertEqual(self.run_publisher(additional=False), 1)
        self.assertEqual(self.writes, [])

    def test_primary_public_setup_keeps_repository_scope_and_no_instance_secret(self):
        self.repo_variables.update(LOCALSINGLENODE_PUBLIC_HOSTNAME=self.config["public_hostname"],
                                   LOCALSINGLENODE_PUBLIC_TUNNEL_ID=self.state["tunnel_id"],
                                   LOCALSINGLENODE_PUBLIC_ORIGIN_PORT=str(self.config["origin_port"]))
        self.assertEqual(self.run_publisher(additional=False), 0)
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(self.writes[0][0][:3], ("secret", "set", "LOCALSINGLENODE_PUBLIC_TUNNEL_TOKEN"))
        self.assertNotIn("--env", self.writes[0][0])

    def test_additional_conversion_preserves_settings_and_refuses_changed_public_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frontend-profile.txt").write_text("BlazorAuto")
            from test_settings_fixture import write_settings
            write_settings(root / "Deployment/LocalSingleNode/inventory/group_vars/all.yml")
            with mock.patch.object(publisher, "ROOT", root), mock.patch.object(publisher, "protected_read", return_value=json.dumps(self.instance)):
                payload, settings = publisher.additional_configuration(Path("instance.json"), self.config, self.state)
                self.assertEqual(settings, self.candidate)
                self.assertEqual(payload["public"]["hostname"], self.config["public_hostname"])
            self.instance["public"] = {"hostname": "foreign.example.invalid"}
            with mock.patch.object(publisher, "ROOT", root), mock.patch.object(publisher, "protected_read", return_value=json.dumps(self.instance)), self.assertRaises(ValueError):
                publisher.additional_configuration(Path("instance.json"), self.config, self.state)


if __name__ == "__main__":
    unittest.main()
