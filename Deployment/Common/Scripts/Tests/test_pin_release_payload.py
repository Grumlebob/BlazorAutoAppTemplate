from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch


LIB = Path(__file__).resolve().parents[1] / "Component" / "lib"
sys.path.insert(0, str(LIB))
import ci_payload_receipt  # noqa: E402
import pin_release_payload as MODULE  # noqa: E402
import registry_payload  # noqa: E402


class PinReleasePayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.staging = self.root / "staging"
        self.staging.mkdir()
        self.pin_root = self.root / "pins"
        self.selection_path = self.root / "selection.json"
        self.identity = registry_payload.ReleasePayloadIdentity(
            repository="https://github.com/grumlebob/GrumPlates",
            commit_sha="1" * 40,
            run_id="123",
            run_attempt="2",
            profile="BlazorAuto",
            acceptance_profile="BlazorAutoV1",
            runtime="linux-x64",
            app_image="ghcr.io/grumlebob/books",
            app_image_digest="sha256:" + "a" * 64,
            bundle_filename="books-migrate",
            manifest_sha256="0" * 64,
            bundle_sha256="0" * 64,
            payload_image_prefix="private-",
        )
        self.digest = "sha256:" + "b" * 64
        self._write_release()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_release(self, *, file_only: bool = False) -> None:
        if file_only:
            self.identity = registry_payload.ReleasePayloadIdentity(
                repository="https://github.com/grumlebob/Portfolio",
                commit_sha="2" * 40,
                run_id="456",
                run_attempt="1",
                profile="React",
                acceptance_profile="PortfolioPublicV1",
                runtime="linux-x64",
                app_image="ghcr.io/grumlebob/portfolio",
                app_image_digest="sha256:" + "c" * 64,
                bundle_filename=None,
                manifest_sha256="0" * 64,
                bundle_sha256=None,
            )
        bundle_bytes = b"migration bundle bytes" if self.identity.bundle_filename else None
        bundle_hash = hashlib.sha256(bundle_bytes).hexdigest() if bundle_bytes else None
        manifest = {
            "schema_version": 3 if file_only else 2,
            "repository": self.identity.repository,
            "commit_sha": self.identity.commit_sha,
            "frontend_profile": self.identity.profile,
            "acceptance_profile": self.identity.acceptance_profile,
            "ci_run_id": int(self.identity.run_id),
            "attempt": int(self.identity.run_attempt),
            "image_ref": f"{self.identity.app_image}:{self.identity.commit_sha}",
            "image_digest": self.identity.app_image_digest,
        }
        if file_only:
            manifest["content_revision"] = "f" * 16
        else:
            manifest.update(
                {
                    "ordered_migration_ids": ["20261001000000_Initial"],
                    "bundle": {
                        "file": self.identity.bundle_filename,
                        "sha256": bundle_hash,
                        "runtime": self.identity.runtime,
                    },
                    "tools": {"dotnet_sdk": "10.0.301"},
                }
            )
        manifest_bytes = (json.dumps(manifest, sort_keys=True) + "\n").encode()
        self.identity = replace(
            self.identity,
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            bundle_sha256=bundle_hash,
        )
        for path in self.staging.iterdir():
            if path.is_file() or path.is_symlink():
                path.unlink()
        (self.staging / MODULE.MANIFEST).write_bytes(manifest_bytes)
        if bundle_bytes is not None:
            (self.staging / self.identity.bundle_filename).write_bytes(bundle_bytes)

        published = {
            "kind": "final",
            "payload_image": self.identity.payload_image,
            "payload_ref": f"{self.identity.payload_image}@{self.digest}",
            "payload_digest": self.digest,
            "repository": self.identity.repository,
            "commit_sha": self.identity.commit_sha,
            "run_id": self.identity.run_id,
            "run_attempt": self.identity.run_attempt,
            "profile": self.identity.profile,
            "acceptance_profile": self.identity.acceptance_profile,
            "runtime": self.identity.runtime,
            "content_sha256": registry_payload.content_checksum(
                {
                    MODULE.MANIFEST: self.identity.manifest_sha256,
                    **({self.identity.bundle_filename: self.identity.bundle_sha256} if self.identity.bundle_filename else {}),
                }
            ),
            "manifest_sha256": self.identity.manifest_sha256,
            "bundle_filename": self.identity.bundle_filename,
            "bundle_sha256": self.identity.bundle_sha256,
            "app_image": self.identity.app_image,
            "app_image_digest": self.identity.app_image_digest,
        }
        receipt = ci_payload_receipt.final_receipt(self.identity, published)
        selection = {
            "schema_version": 1,
            "outcome": "success",
            "selected": {
                "id": self.identity.run_id,
                "run_attempt": self.identity.run_attempt,
                "head_sha": self.identity.commit_sha,
            },
            "payload_receipt": receipt,
        }
        self.selection_path.write_text(json.dumps(selection), encoding="utf-8")

    def _pin(self) -> dict:
        return MODULE.pin(
            self.staging,
            self.selection_path,
            self.pin_root,
            repository=self.identity.repository,
            profile=self.identity.profile,
            acceptance_profile=self.identity.acceptance_profile,
            runtime=self.identity.runtime,
            app_image=self.identity.app_image,
            bundle_name=self.identity.bundle_filename,
            payload_image_prefix=self.identity.payload_image_prefix,
        )

    def _legacy_provenance(self, *, artifact_id: str = "789", artifact_digest: str | None = None) -> dict:
        manifest_sha = hashlib.sha256((self.staging / MODULE.MANIFEST).read_bytes()).hexdigest()
        bundle_sha = hashlib.sha256((self.staging / self.identity.bundle_filename).read_bytes()).hexdigest()
        content_sha = registry_payload.content_checksum(
            {MODULE.MANIFEST: manifest_sha, self.identity.bundle_filename: bundle_sha}
        )
        return {
            "schema_version": 1,
            "transport": "actions-artifact",
            "repository": self.identity.repository,
            "target_sha": self.identity.commit_sha,
            "run_id": self.identity.run_id,
            "run_attempt": self.identity.run_attempt,
            "profile": self.identity.profile,
            "acceptance_profile": self.identity.acceptance_profile,
            "runtime": self.identity.runtime,
            "app_image": self.identity.app_image,
            "image_digest": self.identity.app_image_digest,
            "manifest_sha256": manifest_sha,
            "bundle_filename": self.identity.bundle_filename,
            "bundle_sha256": bundle_sha,
            "content_sha256": content_sha,
            "manifest_schema_version": 2,
            "artifact_id": artifact_id,
            "artifact_name": "books-migrate-linux-x64",
            "artifact_digest": artifact_digest or "sha256:" + "e" * 64,
            "artifact_size_bytes": 1000,
        }

    def _publish_version(self, index: int) -> str:
        sha = format(index, "x").rjust(40, "0")
        self.identity = replace(self.identity, commit_sha=sha, run_id=str(100 + index), run_attempt="1")
        self.digest = "sha256:" + format(index + 20, "x").rjust(64, "0")
        self._write_release()
        return self._pin()["pin_key"]

    def _write_release_marker(self, path: Path, pin_key: str) -> None:
        metadata = MODULE.validate(self.pin_root / pin_key)
        marker = {
            "sha": metadata["target_sha"],
            "source_sha": metadata["target_sha"],
            "source_repo_url": self.identity.repository,
            "frontend_profile": metadata["profile"],
            "acceptance_profile": metadata["acceptance_profile"],
            "image": metadata["app_image"],
            "digest": metadata["image_digest"],
            "manifest_schema_version": metadata["manifest_schema_version"],
            "ci_run_id": metadata["run_id"],
            "ci_run_attempt": metadata["run_attempt"],
            "payload_transport": "ghcr-container",
            "release_payload_pin_key": pin_key,
        }
        path.write_text(json.dumps(marker), encoding="utf-8")

    def _locked_prune(self, **kwargs: object) -> dict:
        lock_dir = self.root / "deploy-lock"
        lock_dir.mkdir(exist_ok=True)
        token = "fixture-lock-token"
        (lock_dir / "token").write_text(token, encoding="utf-8")
        with patch.dict(os.environ, {
            "LOCALCLUSTER_DEPLOY_LOCK_DIR": str(lock_dir),
            "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": token,
        }):
            return MODULE.prune_local_pins(
                self.pin_root,
                repository=self.identity.repository,
                current_marker_path=kwargs["current_marker_path"],
                recovery_marker_path=kwargs.get("recovery_marker_path"),
                apply=bool(kwargs.get("apply", False)),
                max_candidates_per_profile=int(kwargs.get("max_candidates_per_profile", 3)),
                max_unprotected_bytes=int(kwargs.get("max_unprotected_bytes", MODULE.MAX_LOCAL_PIN_BYTES)),
            )

    def _locked_pin_legacy(self, provenance: dict) -> dict:
        lock_dir = self.root / "pin-deploy-lock"
        lock_dir.mkdir(exist_ok=True)
        token = "fixture-pin-lock-token"
        (lock_dir / "token").write_text(token, encoding="utf-8")
        with patch.dict(os.environ, {
            "LOCALCLUSTER_DEPLOY_LOCK_DIR": str(lock_dir),
            "LOCALCLUSTER_DEPLOY_LOCK_TOKEN": token,
        }):
            return MODULE.pin_legacy(self.staging, provenance, self.pin_root)

    def test_pins_and_offline_verifies_profiled_migration_payload(self) -> None:
        pinned = self._pin()
        self.assertEqual(pinned["outcome"], "pinned")
        directory = self.pin_root / pinned["pin_key"]
        self.assertEqual(
            set(MODULE.payload_files(directory)),
            {MODULE.MANIFEST, self.identity.bundle_filename, MODULE.PROVENANCE},
        )
        with patch.object(registry_payload, "_docker", side_effect=AssertionError("offline validation used Docker")):
            verified = MODULE.validate(directory)
        self.assertEqual(verified["payload_ref"], f"{self.identity.payload_image}@{self.digest}")
        self.assertEqual(verified["target_sha"], self.identity.commit_sha)
        self.assertEqual(self._pin()["outcome"], "already_pinned")

    def test_pins_file_only_portfolio_payload_without_fabricated_bundle(self) -> None:
        self._write_release(file_only=True)
        pinned = self._pin()
        directory = self.pin_root / pinned["pin_key"]
        verified = MODULE.validate(directory)
        self.assertIsNone(verified["bundle_filename"])
        self.assertEqual(
            set(MODULE.payload_files(directory)),
            {MODULE.MANIFEST, MODULE.PROVENANCE},
        )

    def test_pins_and_restores_legacy_artifact_without_registry_access(self) -> None:
        provenance = self._legacy_provenance()
        pinned = self._locked_pin_legacy(provenance)
        directory = self.pin_root / pinned["pin_key"]
        with patch.object(registry_payload, "_docker", side_effect=AssertionError("legacy pin used Docker")):
            verified = MODULE.validate(directory)
            restored = MODULE.restore(
                directory,
                self.root / "legacy-restored",
                repository=self.identity.repository,
                target_sha=self.identity.commit_sha,
                profile=self.identity.profile,
                acceptance_profile=self.identity.acceptance_profile,
                runtime=self.identity.runtime,
                app_image=self.identity.app_image,
                bundle_name=self.identity.bundle_filename,
                payload_image_prefix=self.identity.payload_image_prefix,
            )
        self.assertEqual(verified["transport"], "actions-artifact")
        self.assertEqual(verified["artifact_id"], "789")
        self.assertEqual(restored["outcome"], "restored")
        self.assertEqual(
            (self.root / "legacy-restored" / self.identity.bundle_filename).read_bytes(),
            (self.staging / self.identity.bundle_filename).read_bytes(),
        )

    def test_pins_schema_one_legacy_bundle_without_newer_manifest_fields(self) -> None:
        bundle_sha = hashlib.sha256((self.staging / self.identity.bundle_filename).read_bytes()).hexdigest()
        manifest = {
            "schema_version": 1,
            "repository": self.identity.repository,
            "commit_sha": self.identity.commit_sha,
            "ci_run_id": int(self.identity.run_id),
            "attempt": int(self.identity.run_attempt),
            "image_ref": f"{self.identity.app_image}:{self.identity.commit_sha}",
            "image_digest": self.identity.app_image_digest,
            "bundle": {"file": self.identity.bundle_filename, "sha256": bundle_sha},
        }
        (self.staging / MODULE.MANIFEST).write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        provenance = self._legacy_provenance()
        provenance["manifest_schema_version"] = 1
        provenance["manifest_sha256"] = hashlib.sha256((self.staging / MODULE.MANIFEST).read_bytes()).hexdigest()
        provenance["bundle_sha256"] = bundle_sha
        provenance["content_sha256"] = registry_payload.content_checksum(
            {MODULE.MANIFEST: provenance["manifest_sha256"], self.identity.bundle_filename: bundle_sha}
        )
        pinned = self._locked_pin_legacy(provenance)
        self.assertEqual(MODULE.validate(self.pin_root / pinned["pin_key"])["manifest_schema_version"], 1)

    def test_legacy_pin_implicitly_protects_matching_artifact_marker(self) -> None:
        pinned = self._locked_pin_legacy(self._legacy_provenance())
        current = self.root / "legacy-release.json"
        current.write_text(json.dumps({
            "sha": self.identity.commit_sha,
            "source_sha": self.identity.commit_sha,
            "source_repo_url": self.identity.repository,
            "image": self.identity.app_image,
            "digest": self.identity.app_image_digest,
            "frontend_profile": self.identity.profile,
            "acceptance_profile": self.identity.acceptance_profile,
            "manifest_schema_version": 2,
            "ci_run_id": self.identity.run_id,
            "ci_run_attempt": self.identity.run_attempt,
            "payload_transport": "actions-artifact",
        }), encoding="utf-8")
        result = self._locked_prune(current_marker_path=current, recovery_marker_path=None)
        self.assertEqual(result["protected"], [pinned["pin_key"]])
        self.assertEqual(result["marker_pins"]["current"], pinned["pin_key"])
        self.assertEqual(result["outcome"], "dry_run")

    def test_ambiguous_legacy_marker_blocks_retention_without_deletion(self) -> None:
        first = self._locked_pin_legacy(self._legacy_provenance(artifact_id="789"))
        second = self._locked_pin_legacy(self._legacy_provenance(artifact_id="790"))
        current = self.root / "legacy-release.json"
        current.write_text(json.dumps({
            "sha": self.identity.commit_sha,
            "source_sha": self.identity.commit_sha,
            "source_repo_url": self.identity.repository,
            "image": self.identity.app_image,
            "digest": self.identity.app_image_digest,
            "frontend_profile": self.identity.profile,
            "acceptance_profile": self.identity.acceptance_profile,
            "manifest_schema_version": 2,
            "ci_run_id": self.identity.run_id,
            "ci_run_attempt": self.identity.run_attempt,
            "payload_transport": "actions-artifact",
        }), encoding="utf-8")
        result = self._locked_prune(current_marker_path=current, recovery_marker_path=None, apply=True)
        self.assertEqual(result["outcome"], "blocked")
        self.assertEqual(result["blocked_reason"], "current-release-local-pin-is-ambiguous")
        self.assertEqual(result["planned_delete"], [])
        self.assertTrue((self.pin_root / first["pin_key"]).is_dir())
        self.assertTrue((self.pin_root / second["pin_key"]).is_dir())

    def test_legacy_pin_creation_requires_the_shared_deployment_lock(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(MODULE.PinError, "shared deployment lock"):
                MODULE.pin_legacy(self.staging, self._legacy_provenance(), self.pin_root)

    def test_restores_exact_pin_without_registry_access_and_checks_target(self) -> None:
        pinned = self._pin()
        directory = self.pin_root / pinned["pin_key"]
        restored = self.root / "restored"
        with patch.object(registry_payload, "_docker", side_effect=AssertionError("offline restore used Docker")):
            result = MODULE.restore(
                directory,
                restored,
                repository=self.identity.repository,
                target_sha=self.identity.commit_sha,
                profile=self.identity.profile,
                acceptance_profile=self.identity.acceptance_profile,
                runtime=self.identity.runtime,
                app_image=self.identity.app_image,
                bundle_name=self.identity.bundle_filename,
                payload_image_prefix=self.identity.payload_image_prefix,
            )
        self.assertEqual(result["outcome"], "restored")
        self.assertEqual(
            {path.name for path in restored.iterdir()},
            {MODULE.MANIFEST, self.identity.bundle_filename},
        )
        with self.assertRaisesRegex(MODULE.PinError, "does not match"):
            MODULE.restore(
                directory,
                self.root / "wrong-target",
                repository=self.identity.repository,
                target_sha="f" * 40,
                profile=self.identity.profile,
                acceptance_profile=self.identity.acceptance_profile,
                runtime=self.identity.runtime,
                app_image=self.identity.app_image,
                bundle_name=self.identity.bundle_filename,
                payload_image_prefix=self.identity.payload_image_prefix,
            )

    def test_rejects_manifest_tampering_and_unexpected_files(self) -> None:
        pinned = self._pin()
        directory = self.pin_root / pinned["pin_key"]
        (directory / MODULE.MANIFEST).write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(MODULE.PinError, "manifest checksum"):
            MODULE.validate(directory)

        (directory / MODULE.MANIFEST).write_bytes((self.staging / MODULE.MANIFEST).read_bytes())
        (directory / "unexpected.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(MODULE.PinError, "unexpected files"):
            MODULE.validate(directory)

    def test_rejects_staging_that_does_not_match_receipt_file_set(self) -> None:
        (self.staging / "unexpected.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(MODULE.PinError, "staged release payload"):
            self._pin()

    def test_local_pin_retention_protects_current_and_recovery_and_keeps_three(self) -> None:
        keys = [self._publish_version(index) for index in range(1, 7)]
        current = self.root / "release.json"
        recovery = self.root / "previous.json"
        self._write_release_marker(current, keys[-1])
        self._write_release_marker(recovery, keys[-2])

        result = self._locked_prune(current_marker_path=current, recovery_marker_path=recovery)
        self.assertEqual(result["outcome"], "dry_run")
        self.assertEqual(result["protected"], sorted(keys[-2:]))
        self.assertEqual(result["planned_delete"], [keys[0]])
        self.assertTrue((self.pin_root / keys[0]).is_dir())

        applied = self._locked_prune(
            current_marker_path=current,
            recovery_marker_path=recovery,
            apply=True,
            max_unprotected_bytes=0,
        )
        self.assertEqual(set(applied["deleted"]), set(keys[:-2]))
        self.assertTrue((self.pin_root / keys[-1]).is_dir())
        self.assertTrue((self.pin_root / keys[-2]).is_dir())

    def test_local_pin_retention_blocks_unknown_current_or_recovery_state(self) -> None:
        key = self._publish_version(1)
        current = self.root / "release.json"
        recovery = self.root / "previous.json"
        self._write_release_marker(current, key)
        current_marker = json.loads(current.read_text(encoding="utf-8"))
        current_marker["release_payload_pin_key"] = ""
        current.write_text(json.dumps(current_marker), encoding="utf-8")
        blocked = self._locked_prune(current_marker_path=current, recovery_marker_path=recovery, apply=True)
        self.assertEqual(blocked["outcome"], "blocked")
        self.assertEqual(blocked["blocked_reason"], "current-release-local-pin-is-unknown")
        self.assertTrue((self.pin_root / key).is_dir())

        self._write_release_marker(current, key)
        self._write_release_marker(recovery, key)
        recovery_marker = json.loads(recovery.read_text(encoding="utf-8"))
        recovery_marker["release_payload_pin_key"] = ""
        recovery.write_text(json.dumps(recovery_marker), encoding="utf-8")
        blocked = self._locked_prune(current_marker_path=current, recovery_marker_path=recovery, apply=True)
        self.assertEqual(blocked["outcome"], "blocked")
        self.assertEqual(blocked["blocked_reason"], "recovery-release-local-pin-is-unknown")
        self.assertTrue((self.pin_root / key).is_dir())

    def test_local_pin_retention_requires_lock_and_refuses_unknown_entries(self) -> None:
        key = self._publish_version(1)
        current = self.root / "release.json"
        self._write_release_marker(current, key)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(MODULE.PinError, "shared deployment lock"):
                MODULE.prune_local_pins(
                    self.pin_root,
                    repository=self.identity.repository,
                    current_marker_path=current,
                    recovery_marker_path=None,
                )
        (self.pin_root / "unowned-data").mkdir()
        with self.assertRaisesRegex(MODULE.PinError, "unknown or unsafe entry"):
            self._locked_prune(current_marker_path=current)
        self.assertTrue((self.pin_root / key).is_dir())


if __name__ == "__main__":
    unittest.main()
