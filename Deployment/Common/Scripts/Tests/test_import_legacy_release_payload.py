from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[1] / "Component" / "lib"
sys.path.insert(0, str(LIB))

import import_legacy_release_payload as MODULE  # noqa: E402
import pin_release_payload  # noqa: E402


class ArtifactImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = "owner/repo"
        self.repository_url = "https://github.com/owner/repo"
        self.sha = "a" * 40
        self.run_id = "111"
        self.attempt = "2"
        self.bundle_name = "books-migrate"
        self.bundle = b"verified migration bundle fixture"
        self.manifest = {
            "schema_version": 2,
            "repository": self.repository_url,
            "commit_sha": self.sha,
            "frontend_profile": "React",
            "acceptance_profile": "ReactPublicV1",
            "ci_run_id": int(self.run_id),
            "attempt": int(self.attempt),
            "image_ref": f"ghcr.io/owner/books-react:{self.sha}",
            "image_digest": "sha256:" + "b" * 64,
            "ordered_migration_ids": ["20261001000000_Initial"],
            "bundle": {
                "file": self.bundle_name,
                "runtime": "linux-x64",
                "sha256": hashlib.sha256(self.bundle).hexdigest(),
            },
            "tools": {"dotnet_sdk": "10.0.402"},
        }
        self.archive_for_attempt_1 = self._archive(1)
        self.archive_for_attempt_2 = self._archive(2)
        self.selection = {
            "schema_version": 1,
            "outcome": "legacy_artifact",
            "transport": "actions-artifact",
            "selected": {"id": int(self.run_id), "run_attempt": int(self.attempt), "head_sha": self.sha},
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _archive(self, attempt: int) -> bytes:
        manifest = {**self.manifest, "attempt": attempt}
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            zipped.writestr(self.bundle_name, self.bundle)
            zipped.writestr(MODULE.MANIFEST, json.dumps(manifest, sort_keys=True) + "\n")
        return output.getvalue()

    def _artifact(self, artifact_id: int, archive: bytes) -> dict:
        return {
            "id": artifact_id,
            "name": "books-migrate-linux-x64-react",
            "size_in_bytes": len(archive),
            "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
            "expired": False,
            "workflow_run": {"id": int(self.run_id), "head_sha": self.sha},
        }

    def _github_response(self, path: str) -> dict:
        if path.endswith(f"/actions/runs/{self.run_id}"):
            return {
                "repository": {"full_name": self.repository},
                "head_sha": self.sha,
                "head_branch": "main",
                "event": "push",
                "path": ".github/workflows/ci.yml@refs/heads/main",
                "status": "completed",
                "conclusion": "success",
                "run_attempt": int(self.attempt),
            }
        if f"/attempts/{self.attempt}/jobs" in path:
            return {"jobs": [{
                "name": "build-test-push",
                "status": "completed",
                "conclusion": "success",
                "run_id": int(self.run_id),
                "run_attempt": int(self.attempt),
                "head_sha": self.sha,
            }]}
        if path.endswith(f"/actions/runs/{self.run_id}/artifacts?per_page=100&page=1"):
            return {"artifacts": [
                self._artifact(50, self.archive_for_attempt_1),
                self._artifact(51, self.archive_for_attempt_2),
            ]}
        return {"artifacts": []}

    def test_imports_exact_attempt_verifies_api_digest_and_restores_offline(self) -> None:
        archives = {"50": self.archive_for_attempt_1, "51": self.archive_for_attempt_2}

        def download(location: str, destination: Path, expected_size: int) -> str:
            data = archives[location]
            self.assertEqual(expected_size, len(data))
            destination.write_bytes(data)
            return "sha256:" + hashlib.sha256(data).hexdigest()

        with patch.object(MODULE, "_github_json", side_effect=lambda path, token: self._github_response(path)), \
                patch.object(MODULE, "_artifact_download_url", side_effect=lambda api, repo, aid, token: aid), \
                patch.object(MODULE, "_download_archive", side_effect=download), \
                patch.object(pin_release_payload, "_require_shared_lock", return_value=(self.root / "lock", "token")):
            pinned = MODULE.import_legacy_artifact(
                self.selection,
                self.root / "pins",
                repository=self.repository,
                repository_url=self.repository_url,
                token="fixture-token",
                artifact_name="books-migrate-linux-x64-react",
                profile="React",
                acceptance_profile="ReactPublicV1",
                runtime="linux-x64",
                app_image="ghcr.io/owner/books-react",
                bundle_name=self.bundle_name,
            )

        self.assertEqual(pinned["transport"], "actions-artifact")
        self.assertEqual(pinned["run_attempt"], self.attempt)
        self.assertEqual(pinned["artifact_id"], "51")
        self.assertEqual(pinned["pin_key"], "legacy-51-" + hashlib.sha256(self.archive_for_attempt_2).hexdigest())
        restored = self.root / "restored"
        result = pin_release_payload.restore(
            self.root / "pins" / pinned["pin_key"],
            restored,
            repository=self.repository_url,
            target_sha=self.sha,
            profile="React",
            acceptance_profile="ReactPublicV1",
            runtime="linux-x64",
            app_image="ghcr.io/owner/books-react",
            bundle_name=self.bundle_name,
            payload_image_prefix="private-",
        )
        self.assertEqual(result["outcome"], "restored")
        self.assertEqual((restored / self.bundle_name).read_bytes(), self.bundle)

    def test_rejects_archive_digest_mismatch(self) -> None:
        artifact = self._artifact(51, self.archive_for_attempt_2)

        def response(path: str) -> dict:
            if path.endswith(f"/actions/runs/{self.run_id}"):
                return self._github_response(path)
            if f"/attempts/{self.attempt}/jobs" in path:
                return self._github_response(path)
            if "/artifacts?" in path:
                return {"artifacts": [artifact]}
            return {"artifacts": []}

        def download(location: str, destination: Path, expected_size: int) -> str:
            destination.write_bytes(self.archive_for_attempt_2)
            return "sha256:" + "0" * 64

        with patch.object(MODULE, "_github_json", side_effect=lambda path, token: response(path)), \
                patch.object(MODULE, "_artifact_download_url", return_value="51"), \
                patch.object(MODULE, "_download_archive", side_effect=download):
            with self.assertRaisesRegex(MODULE.ImportError, "SHA-256"):
                MODULE.import_legacy_artifact(
                    self.selection, self.root / "pins", repository=self.repository,
                    repository_url=self.repository_url, token="fixture-token",
                    artifact_name="books-migrate-linux-x64-react", profile="React",
                    acceptance_profile="ReactPublicV1", runtime="linux-x64",
                    app_image="ghcr.io/owner/books-react", bundle_name=self.bundle_name,
                )

    def test_signed_archive_download_carries_no_github_token(self) -> None:
        class Response:
            def __init__(self, data: bytes):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self, size: int) -> bytes:
                data, self.data = self.data[:size], self.data[size:]
                return data

        archive = self.archive_for_attempt_2
        destination = self.root / "download.zip"
        with patch.object(MODULE.urllib.request, "urlopen", return_value=Response(archive)) as urlopen:
            digest = MODULE._download_archive("https://signed.example/archive?signature=fixture", destination, len(archive))
        request = urlopen.call_args.args[0]
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(digest, "sha256:" + hashlib.sha256(archive).hexdigest())
        self.assertEqual(destination.read_bytes(), archive)

    def test_rejects_path_traversal_and_symlink_entries(self) -> None:
        for name, mode in (("../release-manifest.json", 0o100644), (MODULE.MANIFEST, 0o120777)):
            with self.subTest(name=name, mode=mode):
                archive_path = self.root / "unsafe.zip"
                with zipfile.ZipFile(archive_path, "w") as zipped:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    zipped.writestr(info, b"{}")
                with self.assertRaises(MODULE.ImportError):
                    MODULE._artifact_members(archive_path, None)


if __name__ == "__main__":
    unittest.main()
