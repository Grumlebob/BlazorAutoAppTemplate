from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "Component" / "lib"
SCRIPT = LIB / "pull_release_payload.py"
SPEC = importlib.util.spec_from_file_location("pull_release_payload", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
import registry_payload  # noqa: E402
from ci_payload_receipt import final_receipt  # noqa: E402


class PullReleasePayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity = registry_payload.ReleasePayloadIdentity(
            repository="https://github.com/owner/repo",
            commit_sha="a" * 40,
            run_id="9",
            run_attempt="2",
            profile="ImprovedDb",
            acceptance_profile=None,
            runtime="linux-x64",
            app_image="ghcr.io/example/app",
            app_image_digest="sha256:" + "c" * 64,
            bundle_filename="app-migrate",
            manifest_sha256="a" * 64,
            bundle_sha256="b" * 64,
        )
        digest = "sha256:" + "d" * 64
        published = {
            "kind": "final",
            "payload_image": self.identity.payload_image,
            "payload_ref": f"{self.identity.payload_image}@{digest}",
            "payload_digest": digest,
            "repository": self.identity.repository,
            "commit_sha": self.identity.commit_sha,
            "run_id": self.identity.run_id,
            "run_attempt": self.identity.run_attempt,
            "profile": self.identity.profile,
            "acceptance_profile": None,
            "runtime": self.identity.runtime,
            "content_sha256": registry_payload.content_checksum({
                "release-manifest.json": self.identity.manifest_sha256,
                self.identity.bundle_filename: self.identity.bundle_sha256,
            }),
            "manifest_sha256": self.identity.manifest_sha256,
            "bundle_filename": self.identity.bundle_filename,
            "bundle_sha256": self.identity.bundle_sha256,
            "app_image": self.identity.app_image,
            "app_image_digest": self.identity.app_image_digest,
        }
        self.receipt = final_receipt(self.identity, published)
        self.digest = digest

    def write_selection(self, directory: Path, *, outcome: str = "success") -> Path:
        path = directory / "selection.json"
        path.write_text(json.dumps({
            "outcome": outcome,
            "selected": {"head_sha": self.identity.commit_sha, "id": 9, "run_attempt": 2},
            "payload_receipt": self.receipt,
        }), encoding="utf-8")
        return path

    def test_pull_uses_validated_receipt_and_returns_transport_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            selection = self.write_selection(directory)
            manifest = directory / "release-manifest.json"
            bundle = directory / self.identity.bundle_filename
            with patch.object(MODULE.registry_payload, "pull_and_extract_release_payload",
                              return_value={"manifest": manifest, "bundle": bundle}) as pull:
                result = MODULE.pull_from_selection(
                    selection, directory / "output", repository=self.identity.repository,
                    profile=self.identity.profile, acceptance_profile=None, runtime=self.identity.runtime,
                    app_image=self.identity.app_image, bundle_name=self.identity.bundle_filename,
                )
        self.assertEqual(result["transport"], "ghcr-container")
        self.assertEqual(result["payload_digest"], self.digest)
        self.assertEqual(result["manifest_sha256"], self.identity.manifest_sha256)
        self.assertEqual(result["bundle_sha256"], self.identity.bundle_sha256)
        self.assertEqual(result["content_sha256"], self.receipt["content_sha256"])
        pull.assert_called_once()
        self.assertEqual(pull.call_args.args[0], self.identity)
        self.assertEqual(pull.call_args.args[1], self.digest)

    def test_receipt_mismatch_stops_before_registry_pull(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            selection = self.write_selection(directory)
            with self.assertRaisesRegex(registry_payload.PayloadError, "profile"):
                MODULE.pull_from_selection(
                    selection, directory / "output", repository=self.identity.repository,
                    profile="OtherProfile", acceptance_profile=None, runtime=self.identity.runtime,
                    app_image=self.identity.app_image, bundle_name=self.identity.bundle_filename,
                )

    def test_legacy_selection_is_not_accepted_by_registry_reader(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            selection = self.write_selection(directory, outcome="legacy_artifact")
            with self.assertRaisesRegex(registry_payload.PayloadError, "does not contain"):
                MODULE.pull_from_selection(
                    selection, directory / "output", repository=self.identity.repository,
                    profile=self.identity.profile, acceptance_profile=None, runtime=self.identity.runtime,
                    app_image=self.identity.app_image, bundle_name=self.identity.bundle_filename,
                )

    def test_local_login_uses_isolated_docker_config_and_cleans_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            selection = self.write_selection(directory)
            token_file = directory / "token.txt"
            token_file.write_text("temporary-test-token\n", encoding="utf-8")
            observed: dict[str, str] = {}

            def fake_pull(identity, digest, output_dir):
                observed["docker_config"] = os.environ["DOCKER_CONFIG"]
                return {"manifest": output_dir / "release-manifest.json", "bundle": output_dir / "app-migrate"}

            prior = os.environ.get("DOCKER_CONFIG")
            with patch.object(MODULE.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "Login Succeeded", "")) as login, \
                 patch.object(MODULE.registry_payload, "pull_and_extract_release_payload", side_effect=fake_pull):
                MODULE.pull_from_selection(
                    selection, directory / "output", repository=self.identity.repository,
                    profile=self.identity.profile, acceptance_profile=None, runtime=self.identity.runtime,
                    app_image=self.identity.app_image, bundle_name=self.identity.bundle_filename,
                    registry_username="fixture-user", token_file=token_file,
                )
            docker_config = observed["docker_config"]
            self.assertFalse(Path(docker_config).exists())
            self.assertEqual(login.call_args.args[0][:4], ["docker", "login", "ghcr.io", "--username"])
            self.assertEqual(login.call_args.kwargs["input"], "temporary-test-token\n")
            self.assertNotEqual(login.call_args.kwargs["env"]["DOCKER_CONFIG"], prior)
            self.assertEqual(os.environ.get("DOCKER_CONFIG"), prior)


if __name__ == "__main__":
    unittest.main()
