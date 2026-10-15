from __future__ import annotations

import hashlib
import io
import json
from dataclasses import replace
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


LIB = Path(__file__).resolve().parents[1] / "Component" / "lib"
sys.path.insert(0, str(LIB))
import registry_payload as MODULE  # noqa: E402
import ci_payload_receipt as RECEIPTS  # noqa: E402


class RegistryPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bundle = self.root / "books-migrate"
        self.bundle.write_bytes(b"verified migration bundle")
        self.bundle_sha = hashlib.sha256(self.bundle.read_bytes()).hexdigest()
        self.app_digest = "sha256:" + "a" * 64
        self.manifest = {
            "schema_version": 2,
            "repository": "https://github.com/grumlebob/BlazorAutoAppTemplate",
            "commit_sha": "1" * 40,
            "frontend_profile": "BlazorAuto",
            "acceptance_profile": "BlazorAutoV1",
            "ci_run_id": 123,
            "attempt": 2,
            "image_ref": "ghcr.io/grumlebob/books:" + "1" * 40,
            "image_digest": self.app_digest,
            "ordered_migration_ids": ["20261001000000_Initial"],
            "bundle": {
                "file": self.bundle.name,
                "sha256": self.bundle_sha,
                "runtime": "linux-x64",
            },
            "tools": {"dotnet_sdk": "10.0.301"},
        }
        self.manifest_path = self.root / MODULE.MANIFEST_FILENAME
        self.manifest_bytes = (json.dumps(self.manifest, sort_keys=True) + "\n").encode()
        self.manifest_path.write_bytes(self.manifest_bytes)
        self.identity = MODULE.ReleasePayloadIdentity(
            repository=self.manifest["repository"],
            commit_sha=self.manifest["commit_sha"],
            run_id="123",
            run_attempt="2",
            profile="BlazorAuto",
            acceptance_profile="BlazorAutoV1",
            runtime="linux-x64",
            app_image="ghcr.io/grumlebob/books",
            app_image_digest=self.app_digest,
            bundle_filename=self.bundle.name,
            manifest_sha256=hashlib.sha256(self.manifest_bytes).hexdigest(),
            bundle_sha256=self.bundle_sha,
        )
        self.payload_digest = "sha256:" + "b" * 64

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_private_payload_prefix_changes_only_payload_image(self) -> None:
        identity = replace(self.identity, payload_image_prefix="private-")
        self.assertEqual(identity.app_image, "ghcr.io/grumlebob/books")
        self.assertEqual(identity.payload_image, "ghcr.io/grumlebob/private-books-release-payload")

    def _inspect_result(self, *, kind: str = "final", labels: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        image = {
            "RepoDigests": [f"{self.identity.payload_image}@{self.payload_digest}"],
            "Config": {"Labels": labels or MODULE.payload_labels(self.identity, kind=kind)},
        }
        return subprocess.CompletedProcess(
            args=["docker", "image", "inspect"],
            returncode=0,
            stdout=json.dumps(image),
            stderr="",
        )

    def _write_archive(self, path: Path, entries: list[tuple[str, bytes | None, bytes]]) -> None:
        with tarfile.open(path, "w:") as archive:
            for name, file_type, content in entries:
                member = tarfile.TarInfo(name)
                if file_type is None:
                    member.type = tarfile.DIRTYPE
                    archive.addfile(member)
                elif file_type == b"symlink":
                    member.type = tarfile.SYMTYPE
                    member.linkname = "books-migrate"
                    archive.addfile(member)
                elif file_type == b"hardlink":
                    member.type = tarfile.LNKTYPE
                    member.linkname = "release/books-migrate"
                    archive.addfile(member)
                else:
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))

    def _valid_archive(self, path: Path) -> None:
        self._write_archive(
            path,
            [
                ("./", None, b""),
                ("./release-manifest.json", b"file", self.manifest_bytes),
                ("./books-migrate", b"file", self.bundle.read_bytes()),
            ],
        )

    def test_payload_tag_and_labels_bind_full_identity(self) -> None:
        tag = MODULE.payload_tag("123", "2", "BlazorAuto", kind="staging")
        self.assertEqual(tag, "run-123-attempt-2-kind-staging-profile-blazorauto")
        labels = MODULE.payload_labels(self.identity, kind="staging")
        self.assertEqual(labels["localcluster.ci.run_attempt"], "2")
        self.assertEqual(labels[MODULE.MANIFEST_LABEL], self.identity.manifest_sha256)
        self.assertEqual(labels[MODULE.KIND_LABEL], "staging")
        labels["localcluster.ci.run_attempt"] = "1"
        with self.assertRaisesRegex(MODULE.PayloadError, "run_attempt"):
            MODULE.validate_payload_labels(labels, self.identity)

    def test_rejects_invalid_kind_and_unsafe_identity(self) -> None:
        with self.assertRaisesRegex(MODULE.PayloadError, "payload kind"):
            MODULE.payload_tag("123", "2", "BlazorAuto", kind="production")
        with self.assertRaisesRegex(MODULE.PayloadError, "repository"):
            MODULE._validate_identity(self.identity.__class__(
                **{**self.identity.__dict__, "repository": "https://github.com/grumlebob/../private"}
            ))
        with self.assertRaisesRegex(MODULE.PayloadError, "positive decimal"):
            MODULE.payload_tag("0", "2", "BlazorAuto")

    def test_publishes_only_registry_confirmed_digest_with_frozen_final_tag(self) -> None:
        commands: list[list[str]] = []

        def docker(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(args)
            if args[0] == "build":
                return subprocess.CompletedProcess(args, 0, "", "")
            if args[0] == "push":
                self.assertEqual(args[1], f"{self.identity.payload_image}:run-123-attempt-2-kind-final-profile-blazorauto")
                return subprocess.CompletedProcess(args, 0, f"digest: {self.payload_digest} size: 512\n", "")
            if args[:2] == ["image", "inspect"]:
                return self._inspect_result()
            self.fail(f"unexpected docker command: {args}")

        with patch.object(MODULE, "_docker", side_effect=docker):
            receipt = MODULE.publish_release_payload(self.identity, self.manifest_path, self.bundle)

        self.assertEqual(receipt["payload_digest"], self.payload_digest)
        self.assertEqual(receipt["payload_ref"], f"{self.identity.payload_image}@{self.payload_digest}")
        self.assertEqual(receipt["kind"], "final")
        self.assertEqual(receipt["runtime"], "linux-x64")
        self.assertEqual(receipt["content_sha256"], MODULE.content_checksum({
            MODULE.MANIFEST_FILENAME: self.identity.manifest_sha256,
            self.identity.bundle_filename: self.identity.bundle_sha256,
        }))
        self.assertEqual([args[0] for args in commands], ["build", "push", "image"])
        self.assertFalse(any(args[0] in {"run", "start", "exec"} for args in commands))

    def test_publisher_rejects_unconfirmed_or_mislabeled_registry_image(self) -> None:
        def no_digest(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if args[0] == "push":
                return subprocess.CompletedProcess(args, 0, "pushed\n", "")
            if args[0] == "build":
                return subprocess.CompletedProcess(args, 0, "", "")
            self.fail(f"unexpected docker command: {args}")

        with patch.object(MODULE, "_docker", side_effect=no_digest):
            with self.assertRaisesRegex(MODULE.PayloadError, "did not report"):
                MODULE.publish_release_payload(self.identity, self.manifest_path, self.bundle)

        wrong_labels = MODULE.payload_labels(self.identity)
        wrong_labels["org.opencontainers.image.revision"] = "2" * 40

        def wrong_identity(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if args[0] == "build" or args[0] == "push":
                stdout = f"digest: {self.payload_digest}\n" if args[0] == "push" else ""
                return subprocess.CompletedProcess(args, 0, stdout, "")
            if args[:2] == ["image", "inspect"]:
                return self._inspect_result(labels=wrong_labels)
            self.fail(f"unexpected docker command: {args}")

        with patch.object(MODULE, "_docker", side_effect=wrong_identity):
            with self.assertRaisesRegex(MODULE.PayloadError, "revision"):
                MODULE.publish_release_payload(self.identity, self.manifest_path, self.bundle)

    def test_publishes_and_extracts_manifest_only_portfolio_payload(self) -> None:
        app_image = "ghcr.io/grumlebob/portfolio"
        payload_image = MODULE.derive_release_payload_image(app_image)
        portfolio_manifest = {
            "schema_version": 3,
            "repository": "https://github.com/grumlebob/Portfolio",
            "commit_sha": "2" * 40,
            "frontend_profile": "React",
            "acceptance_profile": "PortfolioPublicV1",
            "ci_run_id": 456,
            "attempt": 1,
            "image_ref": f"{app_image}:" + "2" * 40,
            "image_digest": "sha256:" + "e" * 64,
            "content_revision": "f" * 16,
        }
        manifest_bytes = (json.dumps(portfolio_manifest, sort_keys=True) + "\n").encode()
        self.manifest_path.write_bytes(manifest_bytes)
        identity = MODULE.ReleasePayloadIdentity(
            repository=portfolio_manifest["repository"],
            commit_sha=portfolio_manifest["commit_sha"],
            run_id="456",
            run_attempt="1",
            profile="React",
            acceptance_profile="PortfolioPublicV1",
            runtime="linux-x64",
            app_image=app_image,
            app_image_digest=portfolio_manifest["image_digest"],
            bundle_filename=None,
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            bundle_sha256=None,
        )
        digest = "sha256:" + "9" * 64
        self.identity = identity
        self.payload_digest = digest
        commands: list[list[str]] = []

        def docker(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(args)
            if args[0] == "build":
                context = Path(args[-1])
                self.assertEqual(
                    {path.name for path in (context / "payload").iterdir()},
                    {MODULE.MANIFEST_FILENAME},
                )
                return subprocess.CompletedProcess(args, 0, "", "")
            if args[0] == "push":
                return subprocess.CompletedProcess(args, 0, f"digest: {digest} size: 128\n", "")
            if args[:2] == ["image", "inspect"]:
                return self._inspect_result()
            self.fail(f"unexpected docker command: {args}")

        with patch.object(MODULE, "_docker", side_effect=docker):
            published = MODULE.publish_release_payload(identity, self.manifest_path)
        self.assertEqual(published["payload_image"], payload_image)
        self.assertIsNone(published["bundle_filename"])
        self.assertIsNone(published["bundle_sha256"])
        self.assertEqual(
            published["content_sha256"],
            MODULE.content_checksum({MODULE.MANIFEST_FILENAME: identity.manifest_sha256}),
        )
        receipt = RECEIPTS.final_receipt(identity, published)
        self.assertNotIn("bundle_sha256", receipt)
        self.assertEqual(receipt["payload_digest"], digest)
        self.assertEqual([args[0] for args in commands], ["build", "push", "image"])

        archive = self.root / "portfolio-copy.tar"
        self._write_archive(
            archive,
            [("./", None, b""), ("./release-manifest.json", b"file", manifest_bytes)],
        )
        extracted = MODULE.extract_payload_archive(
            archive,
            identity=identity,
            output_dir=self.root / "portfolio-extracted",
        )
        self.assertEqual(set(extracted), {"manifest"})
        self.assertEqual(extracted["manifest"].read_bytes(), manifest_bytes)

    def test_publishes_legacy_bundle_manifest_without_profile_metadata(self) -> None:
        app_image = "ghcr.io/grumlebob/sample-app"
        bundle = self.root / "sample-app-migrate"
        bundle.write_bytes(b"legacy ImprovedDb migration bundle")
        bundle_sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
        legacy_manifest = {
            "schema_version": 1,
            "repository": "https://github.com/grumlebob/ImprovedDb",
            "commit_sha": "3" * 40,
            "ci_run_id": 789,
            "attempt": 3,
            "image_ref": f"{app_image}:" + "3" * 40,
            "image_digest": self.app_digest,
            "bundle": {"file": bundle.name, "sha256": bundle_sha},
        }
        manifest_bytes = (json.dumps(legacy_manifest, sort_keys=True) + "\n").encode()
        self.manifest_path.write_bytes(manifest_bytes)
        identity = MODULE.ReleasePayloadIdentity(
            repository=legacy_manifest["repository"],
            commit_sha=legacy_manifest["commit_sha"],
            run_id="789",
            run_attempt="3",
            profile="ImprovedDb",
            acceptance_profile=None,
            runtime="linux-x64",
            app_image=app_image,
            app_image_digest=self.app_digest,
            bundle_filename=bundle.name,
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            bundle_sha256=bundle_sha,
        )
        digest = "sha256:" + "8" * 64
        self.identity = identity
        self.payload_digest = digest

        def docker(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if args[0] == "build" or args[0] == "push":
                stdout = f"digest: {digest} size: 128\n" if args[0] == "push" else ""
                return subprocess.CompletedProcess(args, 0, stdout, "")
            if args[:2] == ["image", "inspect"]:
                return self._inspect_result()
            self.fail(f"unexpected docker command: {args}")

        with patch.object(MODULE, "_docker", side_effect=docker):
            published = MODULE.publish_release_payload(identity, self.manifest_path, bundle)

        self.assertEqual(published["payload_digest"], digest)
        self.assertEqual(published["bundle_filename"], bundle.name)
        receipt = RECEIPTS.final_receipt(identity, published)
        self.assertNotIn("acceptance_profile", receipt)
        self.assertEqual(receipt["bundle_sha256"], bundle_sha)

    def test_extracts_only_two_expected_regular_files(self) -> None:
        archive = self.root / "payload.tar"
        output = self.root / "extracted"
        self._valid_archive(archive)
        extracted = MODULE.extract_payload_archive(archive, identity=self.identity, output_dir=output)
        self.assertEqual(extracted["manifest"].read_bytes(), self.manifest_bytes)
        self.assertEqual(extracted["bundle"].read_bytes(), self.bundle.read_bytes())

    def test_rejects_extra_duplicate_traversal_link_and_corrupt_entries(self) -> None:
        valid_entries: list[tuple[str, bytes | None, bytes]] = [
            ("./", None, b""),
            ("./release-manifest.json", b"file", self.manifest_bytes),
            ("./books-migrate", b"file", self.bundle.read_bytes()),
        ]
        bad_cases = [
            ("nested", valid_entries + [("./nested/readme.txt", b"file", b"unexpected")], "unexpected path"),
            ("unexpected-root", valid_entries + [("readme.txt", b"file", b"unexpected")], "unexpected path"),
            ("duplicate", valid_entries + [valid_entries[-1]], "duplicate paths"),
            ("duplicate-root", valid_entries + [("./", None, b"")], "duplicate paths"),
            ("docker-metadata", valid_entries + [(".dockerenv", b"file", b"runtime metadata")], "unexpected path"),
            ("docker-device-path", valid_entries + [("./dev/console", b"file", b"")], "unexpected path"),
            ("traversal", [("../release-manifest.json", b"file", self.manifest_bytes)], "traversal"),
            ("symlink", [valid_entries[0], valid_entries[1], ("./books-migrate", b"symlink", b"")], "regular file"),
            ("hardlink", [valid_entries[0], valid_entries[1], ("./books-migrate", b"hardlink", b"")], "regular file"),
            ("corrupt", [valid_entries[0], valid_entries[1], ("./books-migrate", b"file", b"bad")], "checksum mismatch"),
        ]
        for name, entries, message in bad_cases:
            with self.subTest(case=name):
                archive = self.root / f"{name}.tar"
                output = self.root / f"out-{name}"
                self._write_archive(archive, entries)
                with self.assertRaisesRegex(MODULE.PayloadError, message):
                    MODULE.extract_payload_archive(archive, identity=self.identity, output_dir=output)
                self.assertFalse(output.exists())

    def test_pull_uses_frozen_digest_and_never_starts_payload(self) -> None:
        archive = self.root / "release-copy.tar"
        self._valid_archive(archive)
        commands: list[list[str]] = []
        external_commands: list[list[str]] = []

        def docker(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(args)
            if args[0] == "pull":
                self.assertEqual(args[1], f"{self.identity.payload_image}@{self.payload_digest}")
                return subprocess.CompletedProcess(args, 0, "pulled", "")
            if args[:2] == ["image", "inspect"]:
                return self._inspect_result()
            if args[0] == "create":
                self.assertEqual(args[-1], MODULE.PAYLOAD_CREATE_PLACEHOLDER_COMMAND)
                return subprocess.CompletedProcess(args, 0, "a" * 64, "")
            self.fail(f"unexpected docker command: {args}")

        def external(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            external_commands.append(command)
            if command[:2] == ["docker", "cp"]:
                output = kwargs["stdout"]
                output.write(archive.read_bytes())
                return subprocess.CompletedProcess(command, 0, None, b"")
            if command[:2] == ["docker", "rm"]:
                return subprocess.CompletedProcess(command, 0, "", "")
            self.fail(f"unexpected external command: {command}")

        with patch.object(MODULE, "_docker", side_effect=docker), patch.object(
            MODULE.subprocess, "run", side_effect=external
        ):
            result = MODULE.pull_and_extract_release_payload(
                self.identity, self.payload_digest, self.root / "pulled"
            )

        self.assertEqual(result["bundle"].read_bytes(), self.bundle.read_bytes())
        self.assertEqual([args[0] for args in commands], ["pull", "image", "create"])
        self.assertEqual(external_commands[0], ["docker", "cp", f"{'a' * 64}:/release/.", "-"])
        self.assertEqual(external_commands[1][:2], ["docker", "rm"])
        self.assertFalse(any(args[0] in {"run", "start", "exec", "export"} for args in commands))

    def test_cleanup_failure_does_not_mask_extraction_error(self) -> None:
        archive = self.root / "bad-copy.tar"
        self._write_archive(archive, [("./", None, b""), ("./books-migrate", b"file", b"bad")])

        def docker(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if args[0] == "pull":
                return subprocess.CompletedProcess(args, 0, "", "")
            if args[:2] == ["image", "inspect"]:
                return self._inspect_result()
            if args[0] == "create":
                return subprocess.CompletedProcess(args, 0, "a" * 64, "")
            self.fail(f"unexpected docker command: {args}")

        def external(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[:2] == ["docker", "cp"]:
                kwargs["stdout"].write(archive.read_bytes())
                return subprocess.CompletedProcess(command, 0, None, b"")
            if command[:2] == ["docker", "rm"]:
                return subprocess.CompletedProcess(command, 1, "", "failed")
            self.fail(f"unexpected external command: {command}")

        with patch.object(MODULE, "_docker", side_effect=docker), patch.object(
            MODULE.subprocess, "run", side_effect=external
        ):
            with self.assertRaisesRegex(MODULE.PayloadError, "checksum mismatch"):
                MODULE.pull_and_extract_release_payload(
                    self.identity, self.payload_digest, self.root / "bad-pulled"
                )
        self.assertFalse((self.root / "bad-pulled").exists())


if __name__ == "__main__":
    unittest.main()
