from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Component" / "lib"))

from release_status import (
    ReleaseStatusError,
    list_active_deployment_runs,
    pin_state,
    summarize_marker,
)


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
        self.repository_url = "https://github.com/Grumlebob/BlazorAutoAppTemplate"
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
        with self.assertRaises(ReleaseStatusError):
            pin_state(summarize_marker(self.marker, repository_url=self.repository_url, app_image=self.marker["image"]), set())

    def test_lists_active_deployment_runs_and_freezes_dispatch_target_sha(self):
        target_sha = "e" * 40
        run = {
            "id": 77,
            "status": "queued",
            "head_sha": "f" * 40,
            "run_attempt": 1,
            "display_title": f"CD LocalCluster @ {target_sha}",
        }

        def response(request, timeout):
            if "cd-localcluster.yml" in request.full_url and "status=queued" in request.full_url:
                return JsonResponse({"workflow_runs": [run]})
            return JsonResponse({"workflow_runs": []})

        with patch("release_status.urllib.request.urlopen", side_effect=response):
            result = list_active_deployment_runs(
                "Grumlebob/BlazorAutoAppTemplate",
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

    def test_fails_closed_when_active_run_has_incomplete_identity(self):
        run = {"id": 77, "status": "in_progress", "head_sha": "not-a-sha", "run_attempt": 1}

        with patch("release_status.urllib.request.urlopen", return_value=JsonResponse({"workflow_runs": [run]})):
            with self.assertRaises(ReleaseStatusError):
                list_active_deployment_runs(
                    "Grumlebob/BlazorAutoAppTemplate",
                    api_root="https://api.github.com",
                    token="fixture-token",
                )
