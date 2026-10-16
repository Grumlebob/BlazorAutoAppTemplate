from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, str(Path(__file__).parent))
from test_settings_fixture import fixture_settings

SCRIPT = Path(__file__).resolve().parents[1] / "resolve-app-instance.py"
SPEC = importlib.util.spec_from_file_location("app_instance", SCRIPT)
assert SPEC and SPEC.loader
instance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(instance)


class AppInstanceTests(unittest.TestCase):
    def setUp(self):
        self.primary = fixture_settings()
        self.candidate = {**self.primary, "app_name": "catalog", "deploy_root": "/opt/catalog",
                          "backup_root": "/opt/catalog-backups", "app_port": 18080,
                          "postgres_port": 15432, "redis_port": 16379, "lan_http_port": 18081,
                          "docker_subnet": "172.30.20.0/24", "lan_hostnames": ["catalog.local"]}
        self.config = {"schema_version": 1, "frontend_profile": "React", "settings": self.candidate, "public": {}}
        self.release = {"app_image": "ghcr.io/example/template", "migration_bundle_name": "app-migrate",
                        "migration_artifact_name": "app-migrate-linux-x64"}
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def validate(self):
        return instance.validate_additional(self.config, self.primary, "BlazorAuto")

    def resolve(self, selected="additional", payload=None):
        return instance.resolve(selected, json.dumps(self.config) if payload is None else payload,
                                "BlazorAuto", "BlazorAutoV1", self.release, self.primary, self.directory)

    def test_primary_keeps_default_names_settings_and_profile(self):
        values = self.resolve("primary", "invalid unused additional configuration")
        self.assertEqual(values["APP_IMAGE"], self.release["app_image"])
        self.assertEqual(values["DEPLOY_ROOT"], self.primary["deploy_root"])
        self.assertEqual(values["MIGRATION_ARTIFACT_NAME"], self.release["migration_artifact_name"])
        self.assertEqual(values["FRONTEND_PROFILE"], "BlazorAuto")
        self.assertEqual(values["LOCALSINGLENODE_SETTINGS_FILE"], "")
        self.assertEqual(json.loads(Path(values["INSTANCE_EXTRA_VARS_FILE"]).read_text())["app_name"], self.primary["app_name"])

    def test_run_scoped_instance_temp_directory_stays_inside_runner_temp(self):
        run_scoped = self.directory / "release-status-123-1"
        with mock.patch.dict(os.environ, {
            "RUNNER_TEMP": str(self.directory),
            "INSTANCE_TEMP_DIR": str(run_scoped),
        }, clear=False):
            result = instance.resolve_temporary_directory()
        self.assertEqual(result, run_scoped.resolve())
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(result.stat().st_mode), 0o700)

        with tempfile.TemporaryDirectory() as outside:
            with mock.patch.dict(os.environ, {
                "RUNNER_TEMP": str(self.directory),
                "INSTANCE_TEMP_DIR": str(Path(outside) / "outside"),
            }, clear=False):
                with self.assertRaises(ValueError):
                    instance.resolve_temporary_directory()

    def test_additional_settings_and_release_are_bound_independently(self):
        values = self.resolve()
        self.assertEqual(values["APP_NAME"], "catalog")
        self.assertEqual(values["DEPLOY_ROOT"], self.candidate["deploy_root"])
        self.assertEqual(values["APP_IMAGE"], "ghcr.io/example/template-react")
        self.assertEqual(values["MIGRATION_ARTIFACT_NAME"], "app-migrate-linux-x64-react")
        self.assertEqual(values["FRONTEND_PROFILE"], "React")
        self.assertEqual(values["ACCEPTANCE_PROFILE"], "ReactPublicV1")
        path = Path(values["LOCALSINGLENODE_SETTINGS_FILE"])
        self.assertEqual(instance.settings(path), self.candidate)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(Path(values["INSTANCE_EXTRA_VARS_FILE"]).stat().st_mode), 0o600)

    def test_legacy_additional_settings_default_account_features_off(self):
        legacy_candidate = {key: value for key, value in self.candidate.items()
                            if key not in instance.ACCOUNT_SETTING_DEFAULTS}
        self.config["settings"] = legacy_candidate
        candidate, _, _ = self.validate()
        self.assertFalse(candidate["accounts_enabled"])
        self.assertFalse(candidate["accounts_registration_enabled"])
        self.assertFalse(candidate["accounts_admin_seed_enabled"])
        self.assertEqual("", candidate["accounts_public_origin"])

    def test_unknown_and_missing_instances_fail(self):
        for selected, payload in (("unknown", "{}"), ("../additional", "{}"), ("additional", ""), ("additional", "{}")):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                self.resolve(selected, payload)

    def test_duplicate_configuration_keys_fail(self):
        with self.assertRaises(ValueError):
            self.resolve(payload='{"schema_version":1,"schema_version":2}')

    def test_unknown_settings_and_schema_fail(self):
        for field in ("schema_version", "frontend_profile", "settings", "public"):
            config = copy.deepcopy(self.config)
            config.pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                instance.validate_additional(config, self.primary, "BlazorAuto")
        self.config["schema_version"] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_primary_identity_and_nested_or_cross_app_roots_fail(self):
        for key, value in (("app_name", self.primary["app_name"]), ("deploy_root", self.primary["deploy_root"]),
                           ("backup_root", self.primary["backup_root"]), ("deploy_root", self.primary["backup_root"] + "/child"),
                           ("deploy_root", "/opt"), ("backup_root", "/opt/catalog/backup")):
            config = copy.deepcopy(self.config)
            config["settings"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                instance.validate_additional(config, self.primary, "BlazorAuto")

    def test_ports_subnet_and_lan_names_cannot_overlap_primary(self):
        self.primary["lan_hostnames"] = ["books.local"]
        for key, value in (("app_port", self.primary["lan_http_port"]), ("docker_subnet", "172.30.10.0/25"),
                           ("lan_hostnames", ["BOOKS.local"]), ("app_port", "18080"), ("deploy_root", "/opt/catalog\nevil: yes")):
            config = copy.deepcopy(self.config)
            config["settings"][key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, SyntaxError)):
                instance.validate_additional(config, self.primary, "BlazorAuto")

    def test_expected_profile_cannot_be_selected_profile_or_untrusted_value(self):
        for profile in ("BlazorAuto", "react", "unknown"):
            self.config["frontend_profile"] = profile
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.validate()

    def test_public_configuration_is_explicit_and_uses_distinct_port(self):
        self.config["public"] = {"hostname": "catalog.example.invalid", "tunnel_id": "00000000-0000-0000-0000-000000000000", "origin_port": 18085}
        values = self.resolve()
        self.assertEqual(values["INSTANCE_PUBLIC_HOSTNAME"], "catalog.example.invalid")
        self.assertEqual(values["INSTANCE_PUBLIC_ORIGIN_PORT"], "18085")

    def test_malformed_or_colliding_public_configuration_fails(self):
        public = {"hostname": "catalog.example.invalid", "tunnel_id": "00000000-0000-0000-0000-000000000000", "origin_port": 18085}
        for key, value in (("hostname", "catalog\nevil=value"), ("hostname", "singlelabel"), ("tunnel_id", "bad"),
                           ("origin_port", self.primary["lan_http_port"]), ("origin_port", self.candidate["app_port"]),
                           ("origin_port", "18085")):
            self.config["public"] = {**public, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate()

    def test_existing_output_is_never_overwritten(self):
        output = self.directory / "instance-settings.yml"
        output.write_text("preserved")
        with self.assertRaises(FileExistsError):
            self.resolve()
        self.assertEqual(output.read_text(), "preserved")

    def test_explicit_settings_path_takes_precedence_over_environment(self):
        values = self.resolve()
        with mock.patch.dict(os.environ, {"LOCALSINGLENODE_SETTINGS_FILE": values["LOCALSINGLENODE_SETTINGS_FILE"]}):
            self.assertEqual(instance.settings(), self.candidate)
            self.assertEqual(fixture_settings(), self.primary)

    def test_owner_marker_binds_repository_and_both_roots(self):
        marker = self.directory / "localsinglenode/apps/catalog.json"
        marker.parent.mkdir(parents=True)
        identity = {"source_repo_url": "https://github.com/example/template",
                    "deploy_root": self.candidate["deploy_root"], "backup_root": self.candidate["backup_root"]}
        protected = SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_uid=0)
        with mock.patch.object(Path, "lstat", return_value=protected):
            marker.write_text(json.dumps(identity))
            instance.verify_owned(self.candidate, identity["source_repo_url"], self.directory)
            for field in identity:
                marker.write_text(json.dumps({**identity, field: "foreign"}))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    instance.verify_owned(self.candidate, identity["source_repo_url"], self.directory)

    def test_unprotected_foreign_owned_or_symlinked_marker_fails(self):
        for mode, uid in ((stat.S_IFREG | 0o666, 0), (stat.S_IFREG | 0o644, 1000), (stat.S_IFLNK | 0o777, 0)):
            with mock.patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=mode, st_uid=uid)), self.assertRaises(ValueError):
                instance.verify_owned(self.candidate, "https://github.com/example/template", self.directory)

    def test_additional_environment_must_be_distinct_before_reading_configuration(self):
        for environment in ("", "localsinglenode", "LocalSingleNode"):
            with mock.patch.dict(os.environ, {"INPUT_APP_INSTANCE": "additional",
                                              "ADDITIONAL_INSTANCE_ENVIRONMENT": environment,
                                              "PRIMARY_INSTANCE_ENVIRONMENT": "localsinglenode",
                                              "APP_INSTANCE_CONFIG": "private-invalid-payload"}), \
                    redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as error:
                self.assertEqual(instance.main([]), 1)
                self.assertNotIn("private-invalid-payload", output.getvalue() + error.getvalue())
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
