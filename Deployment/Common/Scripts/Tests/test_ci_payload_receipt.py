from __future__ import annotations

from email.message import Message
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


LIB = Path(__file__).resolve().parents[1] / "Component" / "lib"
sys.path.insert(0, str(LIB))
CI = Path(__file__).resolve().parents[4] / "Scripts" / "CI"
sys.path.insert(0, str(CI))
import ci_payload_receipt as MODULE  # noqa: E402
import emit_release_payload_receipt as EMITTER  # noqa: E402
import registry_payload  # noqa: E402


class CiPayloadReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_sha = "a" * 64
        self.bundle_sha = "b" * 64
        self.bundle_name = "books-migrate"
        self.identity = registry_payload.ReleasePayloadIdentity(
            repository="https://github.com/grumlebob/BlazorAutoAppTemplate",
            commit_sha="1" * 40,
            run_id="123",
            run_attempt="2",
            profile="BlazorAuto",
            acceptance_profile="BlazorAutoV1",
            runtime="linux-x64",
            app_image="ghcr.io/grumlebob/books",
            app_image_digest="sha256:" + "c" * 64,
            bundle_filename=self.bundle_name,
            manifest_sha256=self.manifest_sha,
            bundle_sha256=self.bundle_sha,
        )
        payload_image = registry_payload.derive_release_payload_image(self.identity.app_image)
        digest = "sha256:" + "d" * 64
        self.published = {
            "kind": "final",
            "payload_image": payload_image,
            "payload_tag": "run-123-attempt-2-kind-final-profile-blazorauto",
            "payload_digest": digest,
            "payload_ref": f"{payload_image}@{digest}",
            "repository": self.identity.repository,
            "commit_sha": self.identity.commit_sha,
            "run_id": self.identity.run_id,
            "run_attempt": self.identity.run_attempt,
            "profile": self.identity.profile,
            "acceptance_profile": self.identity.acceptance_profile,
            "runtime": self.identity.runtime,
            "content_sha256": registry_payload.content_checksum({
                "release-manifest.json": self.manifest_sha,
                self.bundle_name: self.bundle_sha,
            }),
            "manifest_sha256": self.manifest_sha,
            "bundle_filename": self.bundle_name,
            "bundle_sha256": self.bundle_sha,
            "app_image": self.identity.app_image,
            "app_image_digest": self.identity.app_image_digest,
        }
        self.receipt = MODULE.final_receipt(self.identity, self.published)
        self.job = {
            "name": "build-test-push",
            "run_id": 123,
            "run_attempt": 2,
            "head_sha": self.identity.commit_sha,
            "status": "completed",
            "conclusion": "success",
            "steps": [
                {
                    "name": "Emit immutable release payload receipt",
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": "2026-10-15T10:00:00Z",
                    "completed_at": "2026-10-15T10:00:05Z",
                }
            ],
        }

    def line(self, receipt: dict[str, object] | None = None) -> str:
        return MODULE.format_receipt_line(receipt or self.receipt)

    def logs(self, *lines: tuple[str, str]) -> str:
        return "\n".join(f"{timestamp} {message}" for timestamp, message in lines)

    def read(self, log_text: str) -> list[dict[str, object]]:
        return MODULE.receipts_from_step_log(
            self.job,
            log_text,
            step_name="Emit immutable release payload receipt",
            expected_job_name="build-test-push",
            expected_run_id="123",
            expected_run_attempt="2",
            expected_sha=self.identity.commit_sha,
        )

    def test_final_receipt_is_compact_and_binds_all_final_content_hashes(self) -> None:
        line = self.line()
        self.assertTrue(line.startswith(MODULE.RECEIPT_PREFIX))
        parsed = MODULE.parse_receipt_line(line)
        self.assertEqual(parsed["payload_ref"], self.published["payload_ref"])
        self.assertEqual(parsed["app_image_digest"], self.identity.app_image_digest)
        self.assertEqual(parsed["content_sha256"], self.published["content_sha256"])
        self.assertEqual(line, MODULE.format_receipt_line(parsed))

    def test_emitter_hashes_exact_inputs_and_publishes_one_run_bound_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / self.bundle_name
            bundle.write_bytes(b"verified migration bundle")
            bundle_sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
            manifest = {
                "schema_version": 2,
                "repository": self.identity.repository,
                "commit_sha": self.identity.commit_sha,
                "frontend_profile": self.identity.profile,
                "acceptance_profile": self.identity.acceptance_profile,
                "ci_run_id": 123,
                "attempt": 2,
                "image_ref": self.identity.app_image + ":" + self.identity.commit_sha,
                "image_digest": self.identity.app_image_digest,
                "ordered_migration_ids": ["20261001000000_Initial"],
                "bundle": {"file": bundle.name, "sha256": bundle_sha, "runtime": self.identity.runtime},
                "tools": {"dotnet_sdk": "10.0.301"},
            }
            manifest_path = root / "release-manifest.json"
            manifest_bytes = (json.dumps(manifest, sort_keys=True) + "\n").encode()
            manifest_path.write_bytes(manifest_bytes)
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            identity = registry_payload.ReleasePayloadIdentity(
                repository=self.identity.repository,
                commit_sha=self.identity.commit_sha,
                run_id="123",
                run_attempt="2",
                profile=self.identity.profile,
                acceptance_profile=self.identity.acceptance_profile,
                runtime=self.identity.runtime,
                app_image=self.identity.app_image,
                app_image_digest=self.identity.app_image_digest,
                bundle_filename=bundle.name,
                manifest_sha256=manifest_sha,
                bundle_sha256=bundle_sha,
            )
            digest = "sha256:" + "d" * 64
            published = {
                "kind": "final",
                "payload_image": identity.payload_image,
                "payload_ref": f"{identity.payload_image}@{digest}",
                "payload_digest": digest,
                "repository": identity.repository,
                "commit_sha": identity.commit_sha,
                "run_id": identity.run_id,
                "run_attempt": identity.run_attempt,
                "profile": identity.profile,
                "acceptance_profile": identity.acceptance_profile,
                "runtime": identity.runtime,
                "content_sha256": registry_payload.content_checksum({
                    "release-manifest.json": manifest_sha,
                    bundle.name: bundle_sha,
                }),
                "manifest_sha256": manifest_sha,
                "bundle_filename": bundle.name,
                "bundle_sha256": bundle_sha,
                "app_image": identity.app_image,
                "app_image_digest": identity.app_image_digest,
            }

            with patch.object(EMITTER, "publish_release_payload", return_value=published) as publish:
                receipt = EMITTER.emit_payload_receipt(
                    manifest_path=manifest_path,
                    bundle_path=bundle,
                    repository=identity.repository,
                    commit_sha=identity.commit_sha,
                    run_id=identity.run_id,
                    run_attempt=identity.run_attempt,
                    profile=identity.profile,
                    acceptance_profile=identity.acceptance_profile,
                    runtime=identity.runtime,
                    app_image=identity.app_image,
                    payload_image=identity.payload_image,
                )

        publish.assert_called_once()
        emitted_identity = publish.call_args.args[0]
        self.assertEqual(emitted_identity.manifest_sha256, manifest_sha)
        self.assertEqual(emitted_identity.bundle_sha256, bundle_sha)
        self.assertEqual(receipt["payload_digest"], digest)
        self.assertTrue(MODULE.format_receipt_line(receipt).startswith(MODULE.RECEIPT_PREFIX))

    def test_final_receipt_rejects_forged_digest_and_content_checksum(self) -> None:
        bad_ref = dict(self.receipt)
        bad_ref["payload_ref"] = f"{bad_ref['payload_image']}:latest"
        with self.assertRaisesRegex(MODULE.ReceiptError, "reference"):
            MODULE.validate_receipt(bad_ref)

        bad_content = dict(self.receipt)
        bad_content["content_sha256"] = "e" * 64
        with self.assertRaisesRegex(MODULE.ReceiptError, "content checksum"):
            MODULE.validate_receipt(bad_content)

        with self.assertRaisesRegex(MODULE.ReceiptError, "publication result"):
            MODULE.final_receipt(self.identity, {**self.published, "payload_digest": "sha256:" + "f" * 64})

    def test_common_staging_receipt_does_not_require_final_image_fields(self) -> None:
        receipt = {
            "schema_version": 1,
            "kind": "staging",
            "repository": self.identity.repository,
            "sha": self.identity.commit_sha,
            "run_id": "123",
            "run_attempt": "2",
            "profile": "BlazorAuto",
            "runtime": "linux-x64",
            "payload_image": "ghcr.io/grumlebob/books-release-payload",
            "payload_ref": "ghcr.io/grumlebob/books-release-payload@sha256:" + "d" * 64,
            "payload_digest": "sha256:" + "d" * 64,
            "content_sha256": hashlib.sha256(b"staging content").hexdigest(),
        }
        self.assertEqual(MODULE.validate_receipt(receipt)["kind"], "staging")

    def test_reads_only_receipt_lines_inside_exact_successful_job_step(self) -> None:
        valid = self.line()
        react = dict(self.receipt)
        react["profile"] = "React"
        react["acceptance_profile"] = "ReactPublicV1"
        react["app_image"] = "ghcr.io/grumlebob/books-react"
        react["payload_image"] = registry_payload.derive_release_payload_image(react["app_image"])
        react["payload_ref"] = f"{react['payload_image']}@{react['payload_digest']}"
        log_text = self.logs(
            ("2026-10-15T09:59:59Z", valid),
            ("2026-10-15T10:00:00.500Z", MODULE.RECEIPT_COMMAND_MARKER + " --kind final"),
            ("2026-10-15T10:00:01Z", valid),
            ("2026-10-15T10:00:04.500Z", self.line(react)),
            ("2026-10-15T10:00:04.700Z", "##[group]Run an unrelated later step"),
            ("2026-10-15T10:00:04.800Z", valid),
            ("2026-10-15T10:00:06Z", valid),
        )
        found = self.read(log_text)
        self.assertEqual(len(found), 2)
        selected = MODULE.select_receipt(
            found,
            {
                "kind": "final",
                "repository": self.identity.repository,
                "sha": self.identity.commit_sha,
                "run_id": "123",
                "run_attempt": "2",
                "profile": "BlazorAuto",
                "runtime": "linux-x64",
            },
        )
        self.assertEqual(selected["payload_digest"], self.published["payload_digest"])

    def test_rejects_duplicate_missing_forged_and_wrong_profile_receipts(self) -> None:
        valid = self.line()
        with self.assertRaisesRegex(MODULE.ReceiptError, "duplicate"):
            self.read(self.logs(
                ("2026-10-15T10:00:00Z", MODULE.RECEIPT_COMMAND_MARKER),
                ("2026-10-15T10:00:01Z", valid),
                ("2026-10-15T10:00:02Z", valid),
            ))
        with self.assertRaisesRegex(MODULE.ReceiptError, "no valid payload receipt"):
            self.read(self.logs(
                ("2026-10-15T10:00:00Z", MODULE.RECEIPT_COMMAND_MARKER),
                ("2026-10-15T10:00:01Z", "ordinary log"),
            ))

        wrong_sha = dict(self.receipt)
        wrong_sha["sha"] = "2" * 40
        with self.assertRaisesRegex(MODULE.ReceiptError, "sha"):
            self.read(self.logs(
                ("2026-10-15T10:00:00Z", MODULE.RECEIPT_COMMAND_MARKER),
                ("2026-10-15T10:00:01Z", self.line(wrong_sha)),
            ))

        wrong_profile = dict(self.receipt)
        wrong_profile["profile"] = "React"
        wrong_profile["acceptance_profile"] = "ReactPublicV1"
        with self.assertRaisesRegex(MODULE.ReceiptError, "exactly one receipt"):
            MODULE.select_receipt(
                [MODULE.validate_receipt(wrong_profile)],
                {"kind": "final", "profile": "BlazorAuto"},
            )

    def test_failed_skipped_rerun_or_malformed_job_cannot_supply_receipt(self) -> None:
        valid = self.line()
        receipt_log = self.logs(("2026-10-15T10:00:01Z", valid))
        for overrides, message in (
            ({"conclusion": "failure"}, "job did not complete successfully"),
            ({"run_attempt": 3}, "run_attempt"),
            ({"head_sha": "2" * 40}, "head_sha"),
            ({"name": "validate"}, "job name"),
        ):
            with self.subTest(overrides=overrides):
                job = {**self.job, **overrides}
                with patch.object(self, "job", job):
                    with self.assertRaisesRegex(MODULE.ReceiptError, message):
                        self.read(receipt_log)

        failed_step = {**self.job, "steps": [{**self.job["steps"][0], "conclusion": "skipped"}]}
        with patch.object(self, "job", failed_step):
            with self.assertRaisesRegex(MODULE.ReceiptError, "step did not complete successfully"):
                self.read(receipt_log)

        duplicate_step = {**self.job, "steps": [*self.job["steps"], self.job["steps"][0]]}
        with patch.object(self, "job", duplicate_step):
            with self.assertRaisesRegex(MODULE.ReceiptError, "exactly one"):
                self.read(receipt_log)

    def test_job_log_redirect_does_not_forward_api_token_to_signed_host(self) -> None:
        class FakeOpener:
            def open(self, request, timeout):
                self.request = request
                headers = Message()
                headers["Location"] = "https://logs.example.invalid/signed?secret=kept-private"
                raise urllib.error.HTTPError(request.full_url, 302, "Found", headers, io.BytesIO())

        opener = FakeOpener()
        log_body = io.BytesIO(b"job logs\n")
        with patch.object(MODULE.urllib.request, "build_opener", return_value=opener), patch.object(
            MODULE.urllib.request, "urlopen", return_value=log_body
        ) as redirected:
            text = MODULE.download_job_logs("grumlebob/BlazorAutoAppTemplate", 44, "task-token")

        self.assertEqual(text, "job logs\n")
        self.assertEqual(opener.request.get_header("Authorization"), "Bearer task-token")
        redirected_request = redirected.call_args.args[0]
        self.assertIsNone(redirected_request.get_header("Authorization"))
        self.assertNotIn("secret=kept-private", text)

    def test_expired_job_logs_fail_closed(self) -> None:
        class FakeOpener:
            def open(self, request, timeout):
                headers = Message()
                raise urllib.error.HTTPError(request.full_url, 404, "Not Found", headers, io.BytesIO())

        with patch.object(MODULE.urllib.request, "build_opener", return_value=FakeOpener()):
            with self.assertRaisesRegex(MODULE.ReceiptError, "HTTP 404"):
                MODULE.download_job_logs("grumlebob/BlazorAutoAppTemplate", 44, "task-token")


if __name__ == "__main__":
    unittest.main()
