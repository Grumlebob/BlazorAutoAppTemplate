from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from test_settings_fixture import fixture_settings, write_settings

SCRIPTS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("additional_guard", SCRIPTS / "verify-additional-app.py")
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class AdditionalResourceTests(unittest.TestCase):
    def inspect(self, owned, containers=None, networks=None, volumes=None):
        objects = {"container": containers or [], "network": networks or [], "volume": volumes or []}

        def command(*args):
            if args[:3] == ("docker", "ps", "-aq"):
                return "container-id" if objects["container"] else ""
            if args[:2] == ("docker", "inspect"):
                return json.dumps(objects["container"])
            kind = args[1]
            if args[2] == "ls":
                return kind + "-id" if objects[kind] else ""
            return json.dumps(objects[kind])

        with mock.patch.object(guard, "command", side_effect=command) as calls:
            guard.inspect_resources("catalog", owned)
            for call in calls.call_args_list:
                self.assertNotIn("rm", call.args)
                self.assertNotIn("prune", call.args)

    def test_empty_identity_is_available_without_mutation(self):
        self.inspect(False)

    def test_foreign_apps_are_preserved(self):
        self.inspect(False,
                     containers=[{"Name": "/books-web-1", "Config": {"Labels": {"com.docker.compose.project": "books"}}}],
                     networks=[{"Name": "books_default", "Labels": {"com.docker.compose.project": "books"}}],
                     volumes=[{"Name": "books_postgres_data", "Labels": {"com.docker.compose.project": "books"}}])

    def test_new_app_cannot_adopt_existing_containers_networks_or_data(self):
        cases = [
            {"containers": [{"Name": "/catalog-web-1", "Config": {"Labels": {"com.docker.compose.project": "catalog", "localsinglenode.app": "catalog"}}}]},
            {"networks": [{"Name": "catalog_default", "Labels": {"com.docker.compose.project": "catalog"}}]},
            {"volumes": [{"Name": "catalog_postgres_data", "Labels": {"com.docker.compose.project": "catalog"}}]},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.inspect(False, **case)

    def test_owned_identity_requires_correct_runtime_labels(self):
        self.inspect(True,
                     containers=[{"Name": "/catalog-web-1", "Config": {"Labels": {"com.docker.compose.project": "catalog", "localsinglenode.app": "catalog"}}}],
                     networks=[{"Name": "catalog_default", "Labels": {"com.docker.compose.project": "catalog"}}],
                     volumes=[{"Name": "catalog_app_storage", "Labels": {"com.docker.compose.project": "catalog"}}])
        for case in (
            {"containers": [{"Name": "/catalog-web-1", "Config": {"Labels": {"com.docker.compose.project": "catalog"}}}]},
            {"volumes": [{"Name": "catalog_postgres_data", "Labels": {}}]},
            {"networks": [{"Name": "catalog_default", "Labels": {}}]},
        ):
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.inspect(True, **case)


class SetupResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.primary = fixture_settings()
        write_settings(self.directory / "target/inventory/group_vars/all.yml")
        self.candidate = {**self.primary, "app_name": "catalog", "deploy_root": "/opt/catalog",
                          "backup_root": "/opt/catalog-backups", "app_port": 18080, "postgres_port": 15432,
                          "redis_port": 16379, "lan_http_port": 18081, "docker_subnet": "172.30.20.0/24"}
        self.config = {"schema_version": 1, "frontend_profile": "React", "settings": self.candidate, "public": {}}
        self.env_file = self.directory / "github-env"
        self.env = {"INPUT_APP_INSTANCE": "additional", "ADDITIONAL_INSTANCE_ENVIRONMENT": "catalog",
                    "PRIMARY_INSTANCE_ENVIRONMENT": "localsinglenode", "APP_INSTANCE_CONFIG": json.dumps(self.config),
                    "FRONTEND_PROFILE": "BlazorAuto", "ACCEPTANCE_PROFILE": "BlazorAutoV1",
                    "GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": "example/template",
                    "GITHUB_ENV": str(self.env_file), "RUNNER_TEMP": str(self.directory), "LOCALSINGLENODE_HOST": "node-rehearsal"}

    def run_resolver(self, arguments):
        with mock.patch.dict(os.environ, self.env), mock.patch.object(guard.instance, "TARGET", self.directory / "target"), \
                mock.patch.object(guard.instance, "verify_owned") as owner, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = guard.instance.main(arguments)
        return result, owner

    def test_preparation_requires_primary_owner_and_emits_read_only_candidate(self):
        result, owner = self.run_resolver(["--prepare-additional"])
        self.assertEqual(result, 0)
        self.assertEqual(owner.call_args.args[0], self.primary)
        values = dict(line.split("=", 1) for line in self.env_file.read_text().splitlines())
        payload = json.loads(values["READINESS_CANDIDATE"])
        self.assertEqual(payload["source_repo_url"], "https://github.com/example/template")
        self.assertEqual(payload["expected_host"], "node-rehearsal")
        self.assertEqual(payload["settings_yaml"], Path(values["LOCALSINGLENODE_SETTINGS_FILE"]).read_text())

    def test_normal_deploy_requires_additional_owner(self):
        result, owner = self.run_resolver([])
        self.assertEqual(result, 0)
        self.assertEqual(owner.call_args.args[0]["app_name"], "catalog")
        self.assertNotIn("READINESS_CANDIDATE=", self.env_file.read_text())

    def test_prepare_primary_is_rejected_without_output(self):
        self.env["INPUT_APP_INSTANCE"] = "primary"
        result, owner = self.run_resolver(["--prepare-additional"])
        self.assertEqual(result, 1)
        owner.assert_not_called()
        self.assertFalse(self.env_file.exists())

    def test_masking_covers_installation_values_without_hiding_generic_profile_or_schema(self):
        with redirect_stdout(io.StringIO()) as output:
            guard.instance.mask(self.config)
        masks = output.getvalue().splitlines()
        self.assertIn("::add-mask::catalog", masks)
        self.assertIn("::add-mask::18080", masks)
        self.assertNotIn("::add-mask::React", masks)
        self.assertNotIn("::add-mask::1", masks)
        self.assertNotIn("::add-mask::7", masks)


class SetupScopeTests(unittest.TestCase):
    def test_existing_host_playbook_excludes_host_bootstrap_and_runner_changes(self):
        playbook = (SCRIPTS.parent / "ansible/playbooks/PrepareAdditionalApp.yml").read_text()
        for forbidden in ("mint_base", "caddy_install", "single_node_firewall", "avahi", "hostnamectl", "state: restarted",
                          "install-github-runner", "sudoers", "ansible.builtin.apt", "ansible.builtin.user"):
            self.assertNotIn(forbidden, playbook)
        for required in ("verify-additional-app.py", "--settings-file", "check-port-collisions.sh", "force: false",
                         "backup_existing_host: true", "single_node_backup", "ufw allow from {{ lan_cidr }} to any port {{ lan_http_port }}"):
            self.assertIn(required, playbook)
        self.assertLess(playbook.index("verify-additional-app.py"), playbook.index("Record only the additional app ownership"))
        self.assertLess(playbook.index("check-port-collisions.sh"), playbook.index("Record only the additional app ownership"))

    def test_scoped_wrapper_checks_lock_and_readiness_before_preparation(self):
        wrapper = (SCRIPTS / "prepare-additional-app.sh").read_text()
        self.assertIn('"$LOCALCLUSTER_DEPLOY_LOCK_TOKEN"', wrapper)
        self.assertIn("env -u LOCALSINGLENODE_SETTINGS_FILE python3", wrapper)
        self.assertLess(wrapper.index("native-readiness.py"), wrapper.index("ansible-playbook"))
        self.assertNotIn("--bootstrap", wrapper)

    def test_setup_workflow_preserves_existing_runner_and_requires_main_ci(self):
        workflow = (SCRIPTS.parents[2] / ".github/workflows/localsinglenode-app-setup.yml").read_text()
        self.assertIn("find-successful-ci-run.py --target-sha", workflow)
        self.assertIn("with-deploy-lock.sh", workflow)
        self.assertIn("--prepare-additional", workflow)
        self.assertIn("LOCALSINGLENODE_RUNNER_LABEL", workflow)
        self.assertNotIn("install-github-runner", workflow)
        self.assertIn("if: always()", workflow)


if __name__ == "__main__":
    unittest.main()
