from __future__ import annotations

import json
import os
from pathlib import Path
import hashlib
import re
import sys
import tempfile
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Component" / "lib"))

from release_status import (
    ReleaseStatusError,
    list_active_deployment_runs,
    pin_state,
    summarize_marker,
    verify_offline_pin_restore,
    verified_registry_payload_references,
)
import pin_release_payload
import release_status


class CrossRepositoryDispatchContractTests(TestCase):
    def test_localcluster_dispatch_accepts_and_binds_exact_coordinator_provenance(self):
        repo_root = Path(__file__).resolve().parents[4]
        workflow = (repo_root / ".github/workflows/cd-localcluster.yml").read_text(encoding="utf-8")
        input_block = workflow.split("    inputs:\n", 1)[1].split("\npermissions:\n", 1)[0]
        declared = set(re.findall(r"^      ([a-z][a-z0-9_]*):$", input_block, re.MULTILINE))
        required = {
            "target_sha", "run_migrations", "refresh_rating_ranks", "workflow_sha",
            "ci_run_id", "ci_run_attempt", "payload_transport", "payload_image",
            "payload_digest", "artifact_id", "artifact_digest", "manifest_sha256",
            "image_digest", "operation_id", "request_id",
        }
        self.assertTrue(required.issubset(declared), required - declared)
        self.assertIn("inputs.request_id", workflow.splitlines()[1])
        self.assertIn('--expected-run-id "$INPUT_CI_RUN_ID"', workflow)
        self.assertIn('--expected-run-attempt "$INPUT_CI_RUN_ATTEMPT"', workflow)
        self.assertIn("Selected release payload", workflow)


class JsonResponse:
    def __init__(self, value: dict):
        self.body = json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body


class ReleaseStatusTests(TestCase):
    def setUp(self):
        self.repository_url = "https://github.com/Grumlebob/GrumPlates"
        self.marker = {
            "sha": "a" * 40,
            "source_sha": "a" * 40,
            "source_repo_url": self.repository_url,
            "image": "ghcr.io/grumlebob/books",
            "digest": "sha256:" + "b" * 64,
            "frontend_profile": "React",
            "acceptance_profile": "ReactPublicV1",
            "manifest_schema_version": 2,
            "ci_run_id": "12345",
            "ci_run_attempt": "2",
            "payload_transport": "ghcr-container",
            "release_payload_pin_key": "ghcr-" + "c" * 64 + "-" + "d" * 64,
        }

    def test_summarizes_supported_release_marker_without_returning_extra_fields(self):
        result = summarize_marker(self.marker, repository_url=self.repository_url, app_image=self.marker["image"])
        self.assertEqual(result["source_sha"], self.marker["source_sha"])
        self.assertEqual(result["frontend_profile"], "React")
        self.assertEqual(result["release_payload_pin_key"], self.marker["release_payload_pin_key"])
        self.assertNotIn("source_repo_url", result)

    def test_rejects_wrong_repository_profile_transport_and_missing_registry_pin(self):
        for update in (
            {"source_repo_url": "https://github.com/other/repo"},
            {"frontend_profile": "React", "acceptance_profile": "BlazorAutoV1"},
            {"payload_transport": "ghcr-container", "release_payload_pin_key": ""},
            {"payload_transport": "unknown"},
        ):
            with self.subTest(update=update):
                marker = {**self.marker, **update}
                with self.assertRaises(ReleaseStatusError):
                    summarize_marker(marker, repository_url=self.repository_url, app_image=self.marker["image"])

    def test_classifies_legacy_artifact_release_and_requires_registry_pin(self):
        legacy = {
            key: value for key, value in self.marker.items()
            if key not in ("frontend_profile", "acceptance_profile", "release_payload_pin_key")
        }
        legacy["manifest_schema_version"] = 1
        legacy["payload_transport"] = "actions-artifact"
        summary = summarize_marker(legacy, repository_url=self.repository_url, app_image=self.marker["image"])
        self.assertEqual(summary["frontend_profile"], "BlazorAuto")
        self.assertEqual(pin_state(summary, set()), "legacy-artifact-only")
        artifact_pin_key = "legacy-123-" + "e" * 64
        pinned_legacy = summarize_marker(
            {**legacy, "release_payload_pin_key": artifact_pin_key},
            repository_url=self.repository_url,
            app_image=self.marker["image"],
        )
        self.assertEqual(pin_state(pinned_legacy, {artifact_pin_key}), "verified")
        with self.assertRaises(ReleaseStatusError):
            pin_state(summarize_marker(self.marker, repository_url=self.repository_url, app_image=self.marker["image"]), set())

    def test_summarizes_and_verifies_an_explicit_legacy_local_pin(self):
        marker = {**self.marker, "payload_transport": "local-pin",
                  "release_payload_pin_key": "legacy-123-" + "e" * 64}
        summary = summarize_marker(marker, repository_url=self.repository_url, app_image=self.marker["image"])
        self.assertEqual(pin_state(summary, {marker["release_payload_pin_key"]}), "verified")

    def test_registry_protection_resolves_exact_ghcr_digest_from_a_verified_local_pin(self):
        summary = summarize_marker(self.marker, repository_url=self.repository_url, app_image=self.marker["image"])
        metadata = {
            "transport": "ghcr-container", "target_sha": summary["source_sha"],
            "run_id": summary["ci_run_id"], "run_attempt": summary["ci_run_attempt"],
            "payload_image": "ghcr.io/grumlebob/private-books-release-payload",
            "payload_digest": "sha256:" + "f" * 64,
        }
        with patch.object(pin_release_payload, "validate", return_value=metadata) as validate:
            references = verified_registry_payload_references(
                {"current": summary, "recovery": None},
                {"current": summary["release_payload_pin_key"], "recovery": None},
                Path("/verified/pins"),
            )
        validate.assert_called_once_with(Path("/verified/pins") / summary["release_payload_pin_key"])
        self.assertEqual(references[0]["payload_digest"], metadata["payload_digest"])

    def test_registry_protection_rejects_a_pin_that_differs_from_its_release_marker(self):
        summary = summarize_marker(self.marker, repository_url=self.repository_url, app_image=self.marker["image"])
        metadata = {
            "transport": "ghcr-container", "target_sha": "b" * 40,
            "run_id": summary["ci_run_id"], "run_attempt": summary["ci_run_attempt"],
            "payload_image": "ghcr.io/grumlebob/private-books-release-payload",
            "payload_digest": "sha256:" + "f" * 64,
        }
        with patch.object(pin_release_payload, "validate", return_value=metadata):
            with self.assertRaisesRegex(ReleaseStatusError, "differs"):
                verified_registry_payload_references(
                    {"current": summary}, {"current": summary["release_payload_pin_key"]}, Path("/verified/pins"),
                )

    def test_inferred_legacy_pin_requires_local_inventory_validation(self):
        legacy = {
            key: value for key, value in self.marker.items()
            if key not in ("frontend_profile", "acceptance_profile", "release_payload_pin_key")
        }
        legacy["manifest_schema_version"] = 1
        legacy["payload_transport"] = "actions-artifact"
        summary = summarize_marker(legacy, repository_url=self.repository_url, app_image=self.marker["image"])
        key = "legacy-123-" + "e" * 64
        self.assertEqual(pin_state(summary, {key}, key), "verified")
        with self.assertRaisesRegex(ReleaseStatusError, "not validated"):
            pin_state(summary, set(), key)

    def test_offline_pin_restore_uses_no_github_or_registry_credentials_and_checks_restored_bytes(self):
        summary = summarize_marker(self.marker, repository_url=self.repository_url, app_image=self.marker["image"])
        manifest = b"verified manifest"
        bundle = b"verified migration bundle"
        metadata = {
            "transport": "ghcr-container",
            "repository": self.repository_url,
            "target_sha": summary["source_sha"],
            "run_id": summary["ci_run_id"],
            "run_attempt": summary["ci_run_attempt"],
            "profile": summary["frontend_profile"],
            "acceptance_profile": summary["acceptance_profile"],
            "runtime": "linux-x64",
            "app_image": summary["image"],
            "image_digest": summary["digest"],
            "manifest_schema_version": summary["manifest_schema_version"],
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "bundle_filename": "books-migrate-linux-x64",
            "bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        }
        credential_state: list[dict[str, str | None]] = []

        def restore(pin_dir, output_dir, **kwargs):
            credential_state.append({name: os.environ.get(name) for name in (
                "GITHUB_TOKEN", "GH_TOKEN", "GHCR_TOKEN", "GHCR_USERNAME", "DOCKER_CONFIG",
            )})
            output_dir.mkdir()
            (output_dir / "release-manifest.json").write_bytes(manifest)
            (output_dir / metadata["bundle_filename"]).write_bytes(bundle)
            self.assertEqual(kwargs["target_sha"], summary["source_sha"])
            self.assertEqual(kwargs["payload_image_prefix"], "private-books-")
            return {"pin_key": pin_dir.name}

        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            with patch.dict(os.environ, {
                "GITHUB_TOKEN": "fixture-github-token",
                "GH_TOKEN": "fixture-gh-token",
                "GHCR_TOKEN": "fixture-ghcr-token",
                "GHCR_USERNAME": "fixture-user",
                "DOCKER_CONFIG": "fixture-docker-config",
            }, clear=False), \
                    patch.object(pin_release_payload, "_require_shared_lock"), \
                    patch.object(pin_release_payload, "validate", return_value=metadata), \
                    patch.object(pin_release_payload, "restore", side_effect=restore), \
                    patch.object(release_status, "verify_cached_application_image") as image_inspect:
                result = verify_offline_pin_restore(
                    summary,
                    temp_root / "pins",
                    repository_url=self.repository_url,
                    runtime="linux-x64",
                    bundle_name=metadata["bundle_filename"],
                    payload_image_prefix="private-books-",
                    temp_root=temp_root,
                )
                self.assertEqual(os.environ["GITHUB_TOKEN"], "fixture-github-token")
                self.assertEqual(os.environ["GHCR_TOKEN"], "fixture-ghcr-token")
                image_inspect.assert_called_once_with(summary)
            self.assertEqual(list(temp_root.iterdir()), [])

        self.assertEqual(credential_state, [{
            "GITHUB_TOKEN": None,
            "GH_TOKEN": None,
            "GHCR_TOKEN": None,
            "GHCR_USERNAME": None,
            "DOCKER_CONFIG": None,
        }])
        self.assertEqual(result, {
            "outcome": "verified",
            "pin_key": self.marker["release_payload_pin_key"],
            "transport": "ghcr-container",
            "file_count": 2,
            "application_image": "verified-local-digest",
        })

    def test_offline_pin_restore_rejects_missing_pin_and_changed_restored_checksum(self):
        summary = summarize_marker(self.marker, repository_url=self.repository_url, app_image=self.marker["image"])
        with self.assertRaisesRegex(ReleaseStatusError, "no exact local pin"):
            verify_offline_pin_restore(
                {**summary, "release_payload_pin_key": None},
                Path("unused"),
                repository_url=self.repository_url,
                runtime="linux-x64",
                bundle_name="books-migrate-linux-x64",
                payload_image_prefix="private-books-",
                temp_root=Path("."),
            )
        with self.assertRaisesRegex(ReleaseStatusError, "does not match the selected release"):
            verify_offline_pin_restore(
                summary,
                Path("unused"),
                repository_url=self.repository_url,
                runtime="linux-x64",
                bundle_name="books-migrate-linux-x64",
                payload_image_prefix="private-books-",
                temp_root=Path("."),
                validated_pin_key="ghcr-" + "f" * 64 + "-" + "e" * 64,
            )

        manifest = b"verified manifest"
        bundle = b"expected bundle"
        metadata = {
            "transport": "ghcr-container",
            "repository": self.repository_url,
            "target_sha": summary["source_sha"],
            "run_id": summary["ci_run_id"],
            "run_attempt": summary["ci_run_attempt"],
            "profile": summary["frontend_profile"],
            "acceptance_profile": summary["acceptance_profile"],
            "runtime": "linux-x64",
            "app_image": summary["image"],
            "image_digest": summary["digest"],
            "manifest_schema_version": summary["manifest_schema_version"],
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "bundle_filename": "books-migrate-linux-x64",
            "bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        }

        def corrupt_restore(pin_dir, output_dir, **kwargs):
            output_dir.mkdir()
            (output_dir / "release-manifest.json").write_bytes(manifest)
            (output_dir / metadata["bundle_filename"]).write_bytes(b"corrupt bundle")
            return {"pin_key": pin_dir.name}

        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(pin_release_payload, "_require_shared_lock"), \
                patch.object(pin_release_payload, "validate", return_value=metadata), \
                patch.object(pin_release_payload, "restore", side_effect=corrupt_restore):
            with self.assertRaisesRegex(ReleaseStatusError, "pinned payload checksums"):
                verify_offline_pin_restore(
                    summary,
                    Path(temporary) / "pins",
                    repository_url=self.repository_url,
                    runtime="linux-x64",
                    bundle_name=metadata["bundle_filename"],
                    payload_image_prefix="private-books-",
                    temp_root=Path(temporary),
                )

    def test_offline_pin_restore_accepts_an_inventory_validated_legacy_pin(self):
        legacy = {
            key: value for key, value in self.marker.items()
            if key not in ("frontend_profile", "acceptance_profile", "release_payload_pin_key")
        }
        legacy["manifest_schema_version"] = 1
        legacy["payload_transport"] = "actions-artifact"
        summary = summarize_marker(legacy, repository_url=self.repository_url, app_image=self.marker["image"])
        pin_key = "legacy-123-" + "e" * 64
        manifest = b"verified legacy manifest"
        bundle = b"verified legacy migration bundle"
        metadata = {
            "transport": "actions-artifact",
            "repository": self.repository_url,
            "target_sha": summary["source_sha"],
            "run_id": summary["ci_run_id"],
            "run_attempt": summary["ci_run_attempt"],
            "profile": summary["frontend_profile"],
            "acceptance_profile": summary["acceptance_profile"],
            "runtime": "linux-x64",
            "app_image": summary["image"],
            "image_digest": summary["digest"],
            "manifest_schema_version": summary["manifest_schema_version"],
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "bundle_filename": "books-migrate-linux-x64",
            "bundle_sha256": hashlib.sha256(bundle).hexdigest(),
        }

        def restore(pin_dir, output_dir, **kwargs):
            output_dir.mkdir()
            (output_dir / "release-manifest.json").write_bytes(manifest)
            (output_dir / metadata["bundle_filename"]).write_bytes(bundle)
            self.assertEqual(kwargs["target_sha"], summary["source_sha"])
            return {"pin_key": pin_dir.name}

        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(pin_release_payload, "_require_shared_lock"), \
                patch.object(pin_release_payload, "validate", return_value=metadata), \
                patch.object(pin_release_payload, "restore", side_effect=restore), \
                patch.object(release_status, "verify_cached_application_image") as image_inspect:
            result = verify_offline_pin_restore(
                summary,
                Path(temporary) / "pins",
                repository_url=self.repository_url,
                runtime="linux-x64",
                bundle_name=metadata["bundle_filename"],
                payload_image_prefix="private-books-",
                temp_root=Path(temporary),
                validated_pin_key=pin_key,
            )
            image_inspect.assert_called_once_with(summary)

        self.assertEqual(result, {
            "outcome": "verified",
            "pin_key": pin_key,
            "transport": "actions-artifact",
            "file_count": 2,
            "application_image": "verified-local-digest",
        })

    def test_lists_active_deployment_runs_and_freezes_dispatch_target_sha(self):
        target_sha = "e" * 40
        run = {
            "path": ".github/workflows/cd-localcluster.yml",
            "id": 77,
            "status": "queued",
            "head_sha": "f" * 40,
            "run_attempt": 1,
            "display_title": f"CD LocalCluster @ {target_sha}",
        }

        def response(request, timeout):
            if "status=queued" in request.full_url:
                return JsonResponse({"workflow_runs": [run]})
            return JsonResponse({"workflow_runs": []})

        with patch("release_status.urllib.request.urlopen", side_effect=response):
            result = list_active_deployment_runs(
                "Grumlebob/GrumPlates",
                api_root="https://api.github.com",
                token="fixture-token",
            )

        self.assertEqual(result, [{
            "workflow": "cd-localcluster.yml",
            "run_id": "77",
            "status": "queued",
            "head_sha": "f" * 40,
            "target_sha": target_sha,
            "run_attempt": 1,
        }])

    def test_repo_scan_covers_both_deployment_workflows_in_five_queries(self):
        runs = [{"id": 77 + index, "status": "queued", "head_sha": "a" * 40, "run_attempt": 1,
                 "path": f".github/workflows/{workflow}"}
                for index, workflow in enumerate(release_status.CD_WORKFLOWS)]
        runs.append({"path": ".github/workflows/ci.yml"})

        def response(request, timeout):
            self.assertIn("/actions/runs?", request.full_url)
            return JsonResponse({"workflow_runs": runs if "status=queued" in request.full_url else []})

        with patch("release_status.urllib.request.urlopen", side_effect=response) as api:
            result = list_active_deployment_runs(
                "Grumlebob/GrumPlates", api_root="https://api.github.com", token="fixture-token",
            )
        self.assertEqual(set(release_status.CD_WORKFLOWS), {run["workflow"] for run in result})
        self.assertEqual(5, api.call_count)

    def test_repo_scan_paginates_unrelated_runs_before_a_deployment(self):
        unrelated = [{"path": ".github/workflows/ci.yml"} for _ in range(100)]
        deployment = {"id": 77, "status": "queued", "head_sha": "a" * 40, "run_attempt": 1,
                      "path": ".github/workflows/cd-localcluster.yml"}

        def response(request, timeout):
            if "status=queued" not in request.full_url:
                rows = []
            else:
                rows = [deployment] if "page=2" in request.full_url else unrelated
            return JsonResponse({"workflow_runs": rows})

        with patch("release_status.urllib.request.urlopen", side_effect=response) as api:
            result = list_active_deployment_runs(
                "Grumlebob/GrumPlates", api_root="https://api.github.com", token="fixture-token",
            )
        self.assertEqual(["77"], [run["run_id"] for run in result])
        self.assertEqual(6, api.call_count)

    def test_repo_scan_refuses_a_run_without_a_workflow_path(self):
        with patch("release_status.urllib.request.urlopen", return_value=JsonResponse({"workflow_runs": [{}]})):
            with self.assertRaisesRegex(ReleaseStatusError, "workflow path"):
                list_active_deployment_runs(
                    "Grumlebob/GrumPlates", api_root="https://api.github.com", token="fixture-token",
                )

    def test_fails_closed_when_active_run_has_incomplete_identity(self):
        run = {"path": ".github/workflows/cd-localcluster.yml", "id": 77, "status": "in_progress", "head_sha": "not-a-sha", "run_attempt": 1}

        with patch("release_status.urllib.request.urlopen", return_value=JsonResponse({"workflow_runs": [run]})):
            with self.assertRaises(ReleaseStatusError):
                list_active_deployment_runs(
                    "Grumlebob/GrumPlates",
                    api_root="https://api.github.com",
                    token="fixture-token",
                )
