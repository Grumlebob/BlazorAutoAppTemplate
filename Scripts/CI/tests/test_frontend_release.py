from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts/CI"))
from frontend_release_plan import release_plan
from write_release_manifest import write_manifest

SETTINGS = {"app_image": "ghcr.io/example/app", "migration_artifact_name": "app-migrate-linux-x64"}


class ReleasePlanTests(unittest.TestCase):
    def test_default_has_no_additional_publication(self):
        for profile in ("BlazorAuto", "React"):
            for setting in ("", "  "):
                self.assertTrue(all(value == "" for value in release_plan(profile, setting, SETTINGS).values()))

    def test_optional_profile_has_distinct_names_and_own_acceptance(self):
        for selected, additional, acceptance in (("BlazorAuto", "React", "ReactPublicV1"),
                                                  ("React", "BlazorAuto", "BlazorAutoV1")):
            plan = release_plan(selected, f" {additional} ", SETTINGS)
            self.assertEqual(plan["additional_profile"], additional)
            self.assertEqual(plan["additional_acceptance_profile"], acceptance)
            self.assertEqual(plan["additional_image"], f"{SETTINGS['app_image']}-{additional.lower()}")
            self.assertEqual(plan["additional_artifact_name"], f"{SETTINGS['migration_artifact_name']}-{additional.lower()}")

    def test_invalid_duplicate_and_injected_profiles_fail(self):
        for value in ("BlazorAuto", "React,React", "React,BlazorAuto", "React,", ",React", "react",
                      "Vue", "React\nadditional_image=evil", "$(touch evil)", "React;true"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                release_plan("BlazorAuto", value, SETTINGS)

    def test_invalid_selected_profile_fails_even_when_additional_unset(self):
        with self.assertRaises(ValueError):
            release_plan("unknown", "", SETTINGS)


class ReleaseFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "staging"
        self.directory.mkdir()
        self.env = {
            "FRONTEND_PROFILE": "React", "FRONTEND_ACCEPTANCE_PROFILE": "ReactPublicV1",
            "APP_IMAGE": "ghcr.io/example/app-react", "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": "example/template", "GITHUB_SHA": "a" * 40,
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2",
            "MIGRATION_BUNDLE_NAME": "app-migrate", "MIGRATION_RUNTIME": "linux-x64",
        }
        self.bundle = self.directory / "app-migrate"
        self.bundle.write_bytes(b"verified migration bytes")
        self.provenance = {
            "schema_version": 1, "repository": "https://github.com/example/template",
            "source_sha": "a" * 40, "run_id": "123", "run_attempt": "2",
            "bundle_filename": "app-migrate", "runtime": "linux-x64", "dotnet_sdk_version": "10.0.100",
            "ordered_migration_ids": ["20260101000000_Initial"],
            "bundle_sha256": hashlib.sha256(self.bundle.read_bytes()).hexdigest(),
        }
        self.save_provenance()
        self.digests = [f"{self.env['APP_IMAGE']}@sha256:{'b' * 64}"]
        self.labels = {
            "org.opencontainers.image.source": self.provenance["repository"],
            "org.opencontainers.image.revision": self.env["GITHUB_SHA"],
            "com.blazorautoapp.frontend-profile": "React",
            "com.blazorautoapp.acceptance-profile": "ReactPublicV1",
            "localcluster.ci.repository": "example/template", "localcluster.ci.owner": "ci-build",
            "localcluster.ci.run_id": "123", "localcluster.ci.run_attempt": "2",
        }

    def save_provenance(self):
        (self.directory / "migration-provenance.json").write_text(json.dumps(self.provenance), encoding="utf-8")


class ManifestTests(ReleaseFixture, unittest.TestCase):
    def test_react_manifest_matches_verified_bytes_source_digest_and_profile(self):
        manifest = write_manifest(self.directory, self.digests, self.labels, self.env)
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["frontend_profile"], "React")
        self.assertEqual(manifest["acceptance_profile"], "ReactPublicV1")
        self.assertEqual(manifest["bundle"]["sha256"], self.provenance["bundle_sha256"])
        self.assertEqual(manifest["image_digest"], "sha256:" + "b" * 64)
        self.assertEqual(manifest["image_ref"], self.env["APP_IMAGE"] + ":" + "a" * 40)
        self.assertEqual(json.loads((self.directory / "release-manifest.json").read_text()), manifest)

    def test_primary_blazor_metadata_retains_original_names(self):
        self.env.update(FRONTEND_PROFILE="BlazorAuto", FRONTEND_ACCEPTANCE_PROFILE="BlazorAutoV1", APP_IMAGE=SETTINGS["app_image"])
        self.labels.update({"com.blazorautoapp.frontend-profile": "BlazorAuto", "com.blazorautoapp.acceptance-profile": "BlazorAutoV1"})
        manifest = write_manifest(self.directory, [SETTINGS["app_image"] + "@sha256:" + "b" * 64], self.labels, self.env)
        self.assertEqual(manifest["frontend_profile"], "BlazorAuto")
        self.assertEqual(manifest["image_ref"], SETTINGS["app_image"] + ":" + "a" * 40)

    def test_missing_mismatched_or_duplicate_registry_digest_fails(self):
        for digests in (None, [], self.digests * 2, ["ghcr.io/example/other@sha256:" + "b" * 64],
                        [self.env["APP_IMAGE"] + "@sha256:bad"]):
            with self.subTest(digests=digests), self.assertRaises(ValueError):
                write_manifest(self.directory, digests, self.labels, self.env)

    def test_each_image_label_is_required_and_bound_to_release(self):
        for key in self.labels:
            for value in (None, "incorrect"):
                labels = {**self.labels, key: value}
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    write_manifest(self.directory, self.digests, labels, self.env)

    def test_cross_profile_acceptance_fails(self):
        self.env["FRONTEND_ACCEPTANCE_PROFILE"] = "BlazorAutoV1"
        with self.assertRaises(ValueError):
            write_manifest(self.directory, self.digests, self.labels, self.env)

    def test_changed_bundle_fails_without_manifest(self):
        self.bundle.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            write_manifest(self.directory, self.digests, self.labels, self.env)
        self.assertFalse((self.directory / "release-manifest.json").exists())

    def test_staging_source_run_runtime_or_filename_mismatch_fails(self):
        for key in ("source_sha", "repository", "run_id", "run_attempt", "runtime", "bundle_filename"):
            original = self.provenance[key]
            self.provenance[key] = "incorrect"
            self.save_provenance()
            with self.subTest(key=key), self.assertRaises(ValueError):
                write_manifest(self.directory, self.digests, self.labels, self.env)
            self.provenance[key] = original

    def test_existing_manifest_is_never_overwritten(self):
        output = self.directory / "release-manifest.json"
        output.write_text("original", encoding="utf-8")
        with self.assertRaises(ValueError):
            write_manifest(self.directory, self.digests, self.labels, self.env)
        self.assertEqual(output.read_text(), "original")


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "publisher fixtures require Linux bash")
class PublisherTests(ReleaseFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repository = Path(self.temp.name) / "repository"
        self.repository.mkdir()
        for relative in ("Scripts/CI/publish_additional_frontend.sh", "Scripts/CI/write_release_manifest.py",
                         "Scripts/CI/migration_staging_artifact.py", "Scripts/Frontend/resolve_frontend_profile.py"):
            target = self.repository / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        (self.repository / "frontend-profile.txt").write_text("BlazorAuto\n")
        cluster = self.repository / "Deployment/LocalCluster/Scripts"
        common = self.repository / "Deployment/Common/Scripts"
        cluster.mkdir(parents=True)
        common.mkdir(parents=True)
        (common / "read-release-setting.sh").write_text("echo ghcr.io/example/app\n")
        (cluster / "ci-docker-smoke.sh").write_text(
            'echo "smoke $*" >> "$COMMAND_LOG"\n'
            'if [[ "$*" != --cleanup-only && "${FAIL_SMOKE:-}" == 1 ]]; then exit 23; fi\n')
        artifacts = self.repository / "artifacts"
        artifacts.mkdir()
        shutil.copytree(self.directory, artifacts / "migrations")
        (artifacts / "migrations/release-manifest.json").write_text("primary manifest remains unchanged")
        binary = self.repository / "BlazorAutoApp.Test/bin/Release/net10.0/playwright.ps1"
        binary.parent.mkdir(parents=True)
        binary.write_text("fixture")
        self.log = self.repository / "commands.log"
        fakebin = self.repository / "fakebin"
        fakebin.mkdir()
        docker = fakebin / "docker"
        docker.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
with open(os.environ['COMMAND_LOG'], 'a') as stream:
    stream.write('docker ' + ' '.join(sys.argv[1:]) + '\\n')
if '.RepoDigests' in ' '.join(sys.argv):
    print(json.dumps([os.environ['APP_IMAGE'] + '@sha256:' + 'b' * 64]))
elif '.Config.Labels' in ' '.join(sys.argv):
    print(os.environ['FIXTURE_LABELS'])
''')
        dotnet = fakebin / "dotnet"
        dotnet.write_text('#!/bin/sh\necho "dotnet $*" >> "$COMMAND_LOG"\n')
        docker.chmod(0o755)
        dotnet.chmod(0o755)
        self.process_env = {**os.environ, **self.env, "PATH": str(fakebin) + os.pathsep + os.environ["PATH"],
                            "COMMAND_LOG": str(self.log), "FIXTURE_LABELS": json.dumps(self.labels),
                            "RUNNER_TEMP": self.temp.name, "CI_IMAGE_TAG": "a" * 40 + "-123-2"}

    def run_publisher(self):
        return subprocess.run(["bash", "Scripts/CI/publish_additional_frontend.sh"], cwd=self.repository,
                              env=self.process_env, text=True, capture_output=True)

    def test_success_smokes_before_push_and_preserves_primary(self):
        result = self.run_publisher()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.log.read_text()
        self.assertLess(commands.index("dotnet restore"), commands.index("dotnet build"))
        self.assertLess(commands.index("smoke \n"), commands.index("docker push"))
        self.assertIn("smoke --cleanup-only", commands)
        self.assertIn("docker image rm ghcr.io/example/app-react:" + "a" * 40 + "-123-2", commands)
        self.assertNotIn("docker push ghcr.io/example/app:", commands)
        self.assertEqual((self.repository / "artifacts/migrations/release-manifest.json").read_text(),
                         "primary manifest remains unchanged")
        manifest = json.loads((self.repository / "artifacts/additional-migrations/release-manifest.json").read_text())
        self.assertEqual(manifest["frontend_profile"], "React")

    def test_failed_smoke_cleans_own_resources_and_never_pushes(self):
        self.process_env["FAIL_SMOKE"] = "1"
        result = self.run_publisher()
        self.assertEqual(result.returncode, 23, result.stderr)
        commands = self.log.read_text()
        self.assertIn("smoke --cleanup-only", commands)
        self.assertIn("docker image rm ghcr.io/example/app-react:", commands)
        self.assertNotIn("docker push", commands)

    def test_wrong_image_rejected_before_any_command(self):
        self.process_env["APP_IMAGE"] = SETTINGS["app_image"]
        self.assertNotEqual(self.run_publisher().returncode, 0)
        self.assertFalse(self.log.exists())

    def test_changed_copy_rejected_before_build_or_push(self):
        (self.repository / "artifacts/migrations/app-migrate").write_bytes(b"changed")
        self.assertNotEqual(self.run_publisher().returncode, 0)
        commands = self.log.read_text()
        self.assertNotIn("dotnet", commands)
        self.assertNotIn("docker build", commands)
        self.assertNotIn("docker push", commands)


if __name__ == "__main__":
    unittest.main()
