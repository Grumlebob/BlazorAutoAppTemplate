#!/usr/bin/env python3
"""Validate and retain immutable release payloads on an owned machine."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

LIB = Path(__file__).resolve().parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import ci_payload_receipt  # noqa: E402
import pull_release_payload  # noqa: E402
import registry_payload  # noqa: E402
from release_manifest import ManifestError, sha256_file, validate_manifest_payload  # noqa: E402

MANIFEST = registry_payload.MANIFEST_FILENAME
PROVENANCE = "provenance.json"
SAFE_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PIN_KEY = re.compile(r"ghcr-[0-9a-f]{64}-[0-9a-f]{64}\Z")
LEGACY_PIN_KEY = re.compile(r"legacy-[1-9][0-9]{0,19}-[0-9a-f]{64}\Z")
ANY_PIN_KEY = re.compile(r"(?:ghcr-[0-9a-f]{64}-[0-9a-f]{64}|legacy-[1-9][0-9]{0,19}-[0-9a-f]{64})\Z")
MAX_LOCAL_PIN_BYTES = 1_073_741_824


class PinError(ValueError):
    """Raised when a local release pin is incomplete or inconsistent."""


def _read_json(path: Path, message: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PinError(message) from error
    if not isinstance(value, dict):
        raise PinError(message)
    return value


def _receipt_and_identity(
    provenance: dict[str, Any],
) -> tuple[dict[str, Any], registry_payload.ReleasePayloadIdentity, str]:
    if provenance.get("schema_version") != 1 or provenance.get("transport") != "ghcr-container":
        raise PinError("local pin provenance schema or transport is unsupported")
    required = {
        "repository", "target_sha", "run_id", "run_attempt", "profile", "acceptance_profile",
        "runtime", "app_image", "image_digest", "payload_image", "payload_digest",
        "payload_image_prefix", "manifest_sha256", "bundle_filename", "bundle_sha256",
        "content_sha256", "payload_receipt",
    }
    if not required.issubset(provenance) or set(provenance) != required | {"schema_version", "transport"}:
        raise PinError("local pin provenance fields are incomplete or unexpected")
    try:
        receipt = ci_payload_receipt.validate_receipt(provenance["payload_receipt"])
        if receipt.get("kind") != "final":
            raise PinError("local pin receipt is not for a final release")
        acceptance_profile = provenance["acceptance_profile"]
        bundle_name = provenance["bundle_filename"]
        if acceptance_profile is not None and not isinstance(acceptance_profile, str):
            raise PinError("local pin acceptance profile is malformed")
        if bundle_name is not None and not isinstance(bundle_name, str):
            raise PinError("local pin bundle filename is malformed")
        selection = {
            "selected": {
                "id": provenance["run_id"],
                "run_attempt": provenance["run_attempt"],
                "head_sha": provenance["target_sha"],
            },
            "receipt": receipt,
        }
        identity, digest = pull_release_payload.resolve_identity(
            selection,
            repository=provenance["repository"],
            profile=provenance["profile"],
            acceptance_profile=acceptance_profile,
            runtime=provenance["runtime"],
            app_image=provenance["app_image"],
            bundle_name=bundle_name,
            payload_image_prefix=provenance["payload_image_prefix"],
        )
    except (KeyError, TypeError, ValueError, ci_payload_receipt.ReceiptError,
            registry_payload.PayloadError) as error:
        raise PinError("local pin receipt does not match its frozen release identity") from error
    if digest != provenance["payload_digest"] or identity.payload_image != provenance["payload_image"]:
        raise PinError("local pin payload reference differs from its trusted CI receipt")
    if identity.app_image_digest != provenance["image_digest"]:
        raise PinError("local pin application image digest differs from its trusted CI receipt")
    if identity.manifest_sha256 != provenance["manifest_sha256"]:
        raise PinError("local pin manifest checksum differs from its trusted CI receipt")
    if identity.bundle_filename != provenance["bundle_filename"] or identity.bundle_sha256 != provenance["bundle_sha256"]:
        raise PinError("local pin bundle differs from its trusted CI receipt")
    if receipt["content_sha256"] != provenance["content_sha256"]:
        raise PinError("local pin content checksum differs from its trusted CI receipt")
    return receipt, identity, digest


def _legacy_identity(provenance: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "transport", "repository", "target_sha", "run_id", "run_attempt",
        "profile", "acceptance_profile", "runtime", "app_image", "image_digest",
        "manifest_sha256", "bundle_filename", "bundle_sha256", "content_sha256",
        "manifest_schema_version", "artifact_id", "artifact_name", "artifact_digest",
        "artifact_size_bytes",
    }
    if (provenance.get("schema_version") != 1 or provenance.get("transport") != "actions-artifact"
            or set(provenance) != required):
        raise PinError("legacy local pin provenance schema or fields are unsupported")
    repository = provenance["repository"]
    if (not isinstance(repository, str)
            or not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)):
        raise PinError("legacy local pin repository is malformed")
    if not isinstance(provenance["target_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", provenance["target_sha"]):
        raise PinError("legacy local pin source SHA is malformed")
    for field in ("run_id", "run_attempt", "artifact_id"):
        if not isinstance(provenance[field], str) or not re.fullmatch(r"[1-9][0-9]{0,19}", provenance[field]):
            raise PinError(f"legacy local pin {field} is malformed")
    for field in ("profile", "acceptance_profile", "runtime", "artifact_name"):
        value = provenance[field]
        if value is not None and (not isinstance(value, str) or not SAFE_FILENAME.fullmatch(value)):
            raise PinError(f"legacy local pin {field} is malformed")
    for field in ("image_digest", "artifact_digest"):
        if not isinstance(provenance[field], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", provenance[field]):
            raise PinError(f"legacy local pin {field} is malformed")
    for field in ("manifest_sha256", "content_sha256"):
        if not isinstance(provenance[field], str) or not SHA256.fullmatch(provenance[field]):
            raise PinError(f"legacy local pin {field} is malformed")
    if type(provenance["manifest_schema_version"]) is not int or provenance["manifest_schema_version"] not in (1, 2, 3):
        raise PinError("legacy local pin manifest schema is malformed")
    size = provenance["artifact_size_bytes"]
    if type(size) is not int or size <= 0 or size > registry_payload.MAX_ARCHIVE_BYTES:
        raise PinError("legacy local pin artifact size is malformed")
    bundle_name = provenance["bundle_filename"]
    bundle_sha = provenance["bundle_sha256"]
    if bundle_name is None:
        if bundle_sha is not None or provenance["manifest_schema_version"] != 3:
            raise PinError("file-only legacy local pin bundle metadata is inconsistent")
    elif (not isinstance(bundle_name, str) or not SAFE_FILENAME.fullmatch(bundle_name)
            or not isinstance(bundle_sha, str) or not SHA256.fullmatch(bundle_sha)):
        raise PinError("legacy local pin bundle metadata is malformed")
    if (not isinstance(provenance["app_image"], str) or not provenance["app_image"]
            or not isinstance(provenance["runtime"], str) or not provenance["runtime"]):
        raise PinError("legacy local pin release settings are malformed")
    if provenance["manifest_schema_version"] == 1 and (
            provenance["profile"], provenance["acceptance_profile"]) != ("BlazorAuto", "BlazorAutoV1"):
        raise PinError("legacy schema-v1 local pins are supported only for the Blazor profile")
    return provenance


def _pin_key(metadata: dict[str, Any]) -> str:
    if metadata.get("transport") == "actions-artifact":
        return f"legacy-{metadata['artifact_id']}-{metadata['artifact_digest'].removeprefix('sha256:')}"
    return f"ghcr-{hashlib.sha256(metadata['payload_ref'].encode('utf-8')).hexdigest()}-{metadata['manifest_sha256']}"


def payload_files(root: Path) -> tuple[str, ...]:
    if root.is_symlink() or not root.is_dir():
        raise PinError("pinned payload must be a directory and must not be a symlink")
    provenance_path = root / PROVENANCE
    if provenance_path.is_symlink() or not provenance_path.is_file():
        raise PinError("pinned payload provenance is missing or unsafe")
    provenance = _read_json(provenance_path, "pinned payload provenance is malformed")
    if provenance.get("transport") == "ghcr-container":
        _, identity, _ = _receipt_and_identity(provenance)
        bundle_name = identity.bundle_filename
    elif provenance.get("transport") == "actions-artifact":
        identity = _legacy_identity(provenance)
        bundle_name = identity["bundle_filename"]
    else:
        raise PinError("pinned payload transport is unsupported")
    names = [MANIFEST]
    if bundle_name is not None:
        names.append(bundle_name)
    names.append(PROVENANCE)
    if any(not SAFE_FILENAME.fullmatch(name) for name in names) or len(set(names)) != len(names):
        raise PinError("pinned payload contains an unsafe filename")
    if {entry.name for entry in root.iterdir()} != set(names):
        raise PinError("pinned payload contains missing or unexpected files")
    for name in names:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise PinError("pinned payload contains an unsafe file")
    return tuple(names)


def validate(root: Path) -> dict[str, Any]:
    names = payload_files(root)
    provenance = _read_json(root / PROVENANCE, "pinned payload provenance is malformed")
    if provenance.get("transport") == "actions-artifact":
        return _validate_legacy_pin(root, names, provenance)
    receipt, identity, digest = _receipt_and_identity(provenance)
    manifest_path = root / MANIFEST
    if manifest_path.stat().st_size <= 0 or manifest_path.stat().st_size > registry_payload.MAX_MANIFEST_BYTES:
        raise PinError("pinned release manifest has an invalid size")
    if sha256_file(manifest_path) != receipt["manifest_sha256"]:
        raise PinError("pinned release manifest checksum differs from its trusted receipt")
    content_files = {MANIFEST: receipt["manifest_sha256"]}
    if identity.bundle_filename is not None:
        bundle_path = root / identity.bundle_filename
        if bundle_path.stat().st_size <= 0 or bundle_path.stat().st_size > registry_payload.MAX_BUNDLE_BYTES:
            raise PinError("pinned migration bundle has an invalid size")
        if sha256_file(bundle_path) != receipt["bundle_sha256"]:
            raise PinError("pinned migration bundle checksum differs from its trusted receipt")
        content_files[identity.bundle_filename] = receipt["bundle_sha256"]
    if registry_payload.content_checksum(content_files) != receipt["content_sha256"]:
        raise PinError("pinned payload content checksum differs from its trusted receipt")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_digest = validate_manifest_payload(
            manifest,
            expected_repository=identity.repository,
            expected_sha=identity.commit_sha,
            expected_ci_run_id=identity.run_id,
            expected_ci_run_attempt=identity.run_attempt,
            expected_image=identity.app_image,
            expected_bundle_name=identity.bundle_filename,
            expected_frontend_profile=identity.profile if identity.acceptance_profile is not None else None,
            expected_acceptance_profile=identity.acceptance_profile,
            bundle_dir=root if identity.bundle_filename is not None else None,
            expected_bundle_runtime=identity.runtime if identity.acceptance_profile is not None else None,
            require_migration_metadata=identity.acceptance_profile is not None,
            require_bundle_runtime=identity.acceptance_profile is not None,
            allowed_schema_versions=registry_payload._allowed_manifest_schema_versions(identity),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ManifestError) as error:
        raise PinError("pinned release manifest failed identity validation") from error
    if image_digest != receipt["app_image_digest"]:
        raise PinError("pinned application image digest differs from its trusted receipt")
    return {
        "schema_version": 1,
        "transport": "ghcr-container",
        "repository": identity.repository,
        "target_sha": identity.commit_sha,
        "run_id": identity.run_id,
        "run_attempt": identity.run_attempt,
        "profile": identity.profile,
        "acceptance_profile": identity.acceptance_profile,
        "runtime": identity.runtime,
        "app_image": identity.app_image,
        "payload_image": identity.payload_image,
        "payload_digest": digest,
        "payload_ref": f"{identity.payload_image}@{digest}",
        "manifest_sha256": identity.manifest_sha256,
        "bundle_filename": identity.bundle_filename,
        "bundle_sha256": identity.bundle_sha256,
        "content_sha256": receipt["content_sha256"],
        "image_digest": identity.app_image_digest,
        "manifest_schema_version": manifest["schema_version"],
        "files": list(names),
    }


def _validate_legacy_pin(root: Path, names: tuple[str, ...], provenance: dict[str, Any]) -> dict[str, Any]:
    identity = _legacy_identity(provenance)
    manifest_path = root / MANIFEST
    if manifest_path.stat().st_size <= 0 or manifest_path.stat().st_size > registry_payload.MAX_MANIFEST_BYTES:
        raise PinError("pinned release manifest has an invalid size")
    if sha256_file(manifest_path) != identity["manifest_sha256"]:
        raise PinError("pinned release manifest checksum differs from its trusted provenance")
    content_files = {MANIFEST: identity["manifest_sha256"]}
    bundle_name = identity["bundle_filename"]
    if bundle_name is not None:
        bundle_path = root / bundle_name
        if bundle_path.stat().st_size <= 0 or bundle_path.stat().st_size > registry_payload.MAX_BUNDLE_BYTES:
            raise PinError("pinned migration bundle has an invalid size")
        if sha256_file(bundle_path) != identity["bundle_sha256"]:
            raise PinError("pinned migration bundle checksum differs from its trusted provenance")
        content_files[bundle_name] = identity["bundle_sha256"]
    if registry_payload.content_checksum(content_files) != identity["content_sha256"]:
        raise PinError("pinned payload content checksum differs from its trusted provenance")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_digest = validate_manifest_payload(
            manifest,
            expected_repository=identity["repository"],
            expected_sha=identity["target_sha"],
            expected_ci_run_id=identity["run_id"],
            expected_ci_run_attempt=identity["run_attempt"],
            expected_image=identity["app_image"],
            expected_bundle_name=bundle_name,
            expected_frontend_profile=identity["profile"],
            expected_acceptance_profile=identity["acceptance_profile"],
            bundle_dir=root if bundle_name is not None else None,
            expected_bundle_runtime=(
                identity["runtime"]
                if bundle_name is not None and identity["manifest_schema_version"] >= 2 else None
            ),
            require_migration_metadata=(bundle_name is not None and identity["manifest_schema_version"] >= 2),
            require_bundle_runtime=(bundle_name is not None and identity["manifest_schema_version"] >= 2),
            allowed_schema_versions=(1, 2) if bundle_name is not None else (3,),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ManifestError) as error:
        raise PinError("pinned release manifest failed identity validation") from error
    if image_digest != identity["image_digest"]:
        raise PinError("pinned application image digest differs from its trusted provenance")
    return {
        "schema_version": 1,
        "transport": "actions-artifact",
        "repository": identity["repository"],
        "target_sha": identity["target_sha"],
        "run_id": identity["run_id"],
        "run_attempt": identity["run_attempt"],
        "profile": identity["profile"],
        "acceptance_profile": identity["acceptance_profile"],
        "runtime": identity["runtime"],
        "app_image": identity["app_image"],
        "payload_digest": identity["artifact_digest"],
        "artifact_id": identity["artifact_id"],
        "artifact_name": identity["artifact_name"],
        "artifact_digest": identity["artifact_digest"],
        "artifact_size_bytes": identity["artifact_size_bytes"],
        "manifest_sha256": identity["manifest_sha256"],
        "bundle_filename": bundle_name,
        "bundle_sha256": identity["bundle_sha256"],
        "content_sha256": identity["content_sha256"],
        "image_digest": identity["image_digest"],
        "manifest_schema_version": manifest["schema_version"],
        "files": list(names),
    }


@contextlib.contextmanager
def publication_lock(root: Path):
    lock_path = root / ".publish.lock"
    if lock_path.is_symlink():
        raise PinError("local pin publication lock must not be a symlink")
    with lock_path.open("a+b") as lock_file:
        if os.name == "posix":
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        else:
            import msvcrt
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            deadline = time.monotonic() + 30
            while True:
                try:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.05)
        try:
            yield
        finally:
            if os.name == "posix":
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            else:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def _make_provenance(
    selection: dict[str, Any],
    *,
    repository: str,
    profile: str,
    acceptance_profile: str | None,
    runtime: str,
    app_image: str,
    bundle_name: str | None,
    payload_image_prefix: str,
) -> dict[str, Any]:
    try:
        if selection.get("outcome") != "success" or not isinstance(selection.get("selected"), dict):
            raise PinError("CI selection is not a successful exact release")
        receipt = ci_payload_receipt.validate_receipt(selection.get("payload_receipt"))
        if receipt.get("kind") != "final":
            raise PinError("CI selection receipt is not for a final release")
        identity, digest = pull_release_payload.resolve_identity(
            {"selected": selection["selected"], "receipt": receipt},
            repository=repository,
            profile=profile,
            acceptance_profile=acceptance_profile,
            runtime=runtime,
            app_image=app_image,
            bundle_name=bundle_name,
            payload_image_prefix=payload_image_prefix,
        )
    except (KeyError, TypeError, ValueError, ci_payload_receipt.ReceiptError,
            registry_payload.PayloadError) as error:
        if isinstance(error, PinError):
            raise
        raise PinError("successful CI selection does not match expected release settings") from error
    return {
        "schema_version": 1,
        "transport": "ghcr-container",
        "repository": identity.repository,
        "target_sha": identity.commit_sha,
        "run_id": identity.run_id,
        "run_attempt": identity.run_attempt,
        "profile": identity.profile,
        "acceptance_profile": identity.acceptance_profile,
        "runtime": identity.runtime,
        "app_image": identity.app_image,
        "image_digest": identity.app_image_digest,
        "payload_image": identity.payload_image,
        "payload_digest": digest,
        "payload_image_prefix": payload_image_prefix,
        "manifest_sha256": identity.manifest_sha256,
        "bundle_filename": identity.bundle_filename,
        "bundle_sha256": identity.bundle_sha256,
        "content_sha256": receipt["content_sha256"],
        "payload_receipt": receipt,
    }


def pin(
    staging: Path,
    selection_path: Path,
    root: Path,
    *,
    repository: str,
    profile: str,
    acceptance_profile: str | None,
    runtime: str,
    app_image: str,
    bundle_name: str | None,
    payload_image_prefix: str,
) -> dict[str, Any]:
    if root.is_symlink() or staging.is_symlink():
        raise PinError("staging and pin roots must not be symlinks")
    selection = _read_json(selection_path, "CI selection is missing or malformed")
    provenance = _make_provenance(
        selection,
        repository=repository,
        profile=profile,
        acceptance_profile=acceptance_profile,
        runtime=runtime,
        app_image=app_image,
        bundle_name=bundle_name,
        payload_image_prefix=payload_image_prefix,
    )
    expected_files = {MANIFEST}
    if provenance["bundle_filename"] is not None:
        expected_files.add(provenance["bundle_filename"])
    if not staging.is_dir() or {entry.name for entry in staging.iterdir()} != expected_files:
        raise PinError("staged release payload contains missing or unexpected files")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix=".pin-", dir=str(root)) as temporary:
        candidate = Path(temporary) / "payload"
        candidate.mkdir(mode=0o700)
        for name in sorted(expected_files):
            source = staging / name
            if source.is_symlink() or not source.is_file():
                raise PinError("staged release payload contains an unsafe file")
            shutil.copyfile(source, candidate / name)
        provenance_path = candidate / PROVENANCE
        provenance_path.write_text(json.dumps(provenance, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        metadata = validate(candidate)
        reference_hash = hashlib.sha256(metadata["payload_ref"].encode("utf-8")).hexdigest()
        key = f"ghcr-{reference_hash}-{metadata['manifest_sha256']}"
        destination = root / key
        with publication_lock(root):
            if destination.exists() or destination.is_symlink():
                if destination.is_symlink() or validate(destination) != metadata:
                    raise PinError("existing local pin has conflicting immutable provenance")
                outcome = "already_pinned"
            else:
                for name in payload_files(candidate):
                    path = candidate / name
                    with path.open("r+b") as output:
                        os.fsync(output.fileno())
                    os.chmod(path, 0o600)
                os.rename(candidate, destination)
                if os.name == "posix":
                    descriptor = os.open(root, os.O_RDONLY)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                outcome = "pinned"
    return {"schema_version": 1, "outcome": outcome, "pin_key": key, **metadata}


def pin_legacy(staging: Path, provenance: dict[str, Any], root: Path) -> dict[str, Any]:
    """Retain an exact, already verified Actions-artifact payload without its ZIP archive."""
    _require_shared_lock()
    if root.is_symlink() or staging.is_symlink():
        raise PinError("staging and pin roots must not be symlinks")
    identity = _legacy_identity(provenance)
    expected_files = {MANIFEST}
    if identity["bundle_filename"] is not None:
        expected_files.add(identity["bundle_filename"])
    if not staging.is_dir() or {entry.name for entry in staging.iterdir()} != expected_files:
        raise PinError("staged legacy release payload contains missing or unexpected files")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix=".pin-legacy-", dir=str(root)) as temporary:
        candidate = Path(temporary) / "payload"
        candidate.mkdir(mode=0o700)
        for name in sorted(expected_files):
            source = staging / name
            if source.is_symlink() or not source.is_file():
                raise PinError("staged legacy release payload contains an unsafe file")
            shutil.copyfile(source, candidate / name)
        (candidate / PROVENANCE).write_text(
            json.dumps(provenance, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        metadata = validate(candidate)
        key = _pin_key(metadata)
        destination = root / key
        with publication_lock(root):
            if destination.exists() or destination.is_symlink():
                if destination.is_symlink() or validate(destination) != metadata:
                    raise PinError("existing legacy local pin has conflicting immutable provenance")
                outcome = "already_pinned"
            else:
                for name in payload_files(candidate):
                    path = candidate / name
                    with path.open("r+b") as output:
                        os.fsync(output.fileno())
                    os.chmod(path, 0o600)
                os.rename(candidate, destination)
                if os.name == "posix":
                    descriptor = os.open(root, os.O_RDONLY)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                outcome = "pinned"
    return {"schema_version": 1, "outcome": outcome, "pin_key": key, **metadata}


def restore(
    pin_dir: Path,
    output_dir: Path,
    *,
    repository: str,
    target_sha: str,
    profile: str,
    acceptance_profile: str | None,
    runtime: str,
    app_image: str,
    bundle_name: str | None,
    payload_image_prefix: str,
) -> dict[str, Any]:
    if not ANY_PIN_KEY.fullmatch(pin_dir.name):
        raise PinError("local pin key is malformed")
    metadata = validate(pin_dir)
    provenance = _read_json(pin_dir / PROVENANCE, "pinned payload provenance is malformed")
    if metadata["transport"] == "actions-artifact":
        identity = _legacy_identity(provenance)
        if pin_dir.name != _pin_key(metadata):
            raise PinError("local legacy pin directory key does not match its artifact identity")
        expected = {
            "repository": repository,
            "target_sha": target_sha,
            "profile": profile,
            "acceptance_profile": acceptance_profile,
            "runtime": runtime,
            "app_image": app_image,
            "bundle_filename": bundle_name,
        }
        actual = {field: identity[field] for field in expected}
        if actual != expected:
            raise PinError("local pin does not match the requested repository, target, profile, or release settings")
        return _restore_files(pin_dir, output_dir, metadata)
    _, identity, _ = _receipt_and_identity(provenance)
    if pin_dir.name != _pin_key(metadata):
        raise PinError("local pin directory key does not match its immutable payload identity")
    expected = {
        "repository": repository,
        "target_sha": target_sha,
        "profile": profile,
        "acceptance_profile": acceptance_profile,
        "runtime": runtime,
        "app_image": app_image,
        "bundle_filename": bundle_name,
        "payload_image_prefix": payload_image_prefix,
    }
    actual = {
        "repository": identity.repository,
        "target_sha": identity.commit_sha,
        "profile": identity.profile,
        "acceptance_profile": identity.acceptance_profile,
        "runtime": identity.runtime,
        "app_image": identity.app_image,
        "bundle_filename": identity.bundle_filename,
        "payload_image_prefix": identity.payload_image_prefix,
    }
    if actual != expected:
        raise PinError("local pin does not match the requested repository, target, profile, or release settings")
    return _restore_files(pin_dir, output_dir, metadata)


def _restore_files(pin_dir: Path, output_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise PinError("local pin restore destination already exists")
    output_dir.mkdir(parents=True, mode=0o700)
    try:
        for name in payload_files(pin_dir):
            if name == PROVENANCE:
                continue
            source = pin_dir / name
            destination = output_dir / name
            if source.is_symlink() or not source.is_file():
                raise PinError("local pin contains an unsafe payload file")
            shutil.copyfile(source, destination)
            os.chmod(destination, 0o600)
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    return {"schema_version": 1, "outcome": "restored", "pin_key": pin_dir.name, **metadata}


def _require_shared_lock() -> tuple[Path, str]:
    lock_text = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_DIR", "")
    token = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_TOKEN", "")
    if not lock_text or not token:
        raise PinError("local release pin retention requires the shared deployment lock")
    lock_dir = Path(lock_text)
    token_path = lock_dir / "token"
    if (lock_dir.is_symlink() or not lock_dir.is_dir() or token_path.is_symlink()
            or not token_path.is_file()):
        raise PinError("shared deployment lock identity is unavailable")
    try:
        actual = token_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise PinError("shared deployment lock token cannot be read") from error
    if actual != token:
        raise PinError("shared deployment lock token changed")
    return lock_dir.resolve(), token


def _read_release_marker(path: Path, repository: str) -> dict[str, Any] | None:
    if path.is_symlink():
        raise PinError(f"release marker is a symlink: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise PinError(f"release marker is not a regular file: {path}")
    marker = _read_json(path, f"release marker is missing or malformed: {path}")
    source = marker.get("source_repo_url")
    source_sha = marker.get("source_sha")
    sha = marker.get("sha", source_sha)
    if (not isinstance(source, str) or source.casefold() != repository.casefold()
            or not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha)
            or sha != source_sha):
        raise PinError(f"release marker does not identify the expected repository and source SHA: {path}")
    key = marker.get("release_payload_pin_key", "")
    if key and (not isinstance(key, str) or not ANY_PIN_KEY.fullmatch(key)):
        raise PinError(f"release marker has a malformed local pin key: {path}")
    transport = marker.get("payload_transport", "actions-artifact")
    if transport not in {"actions-artifact", "ghcr-container", "local-pin"}:
        raise PinError(f"release marker has an unsupported payload transport: {path}")
    if transport == "actions-artifact" and key and not LEGACY_PIN_KEY.fullmatch(key):
        raise PinError(f"legacy release marker names a non-legacy local pin: {path}")
    if transport == "ghcr-container" and key and not PIN_KEY.fullmatch(key):
        raise PinError(f"GHCR release marker names a non-GHCR local pin: {path}")
    return marker


def _pin_size(path: Path) -> int:
    return sum((path / name).stat().st_size for name in payload_files(path))


def _pin_marker_matches(marker: dict[str, Any], pin: dict[str, Any]) -> bool:
    schema = marker.get("manifest_schema_version", 1)
    profile = marker.get("frontend_profile")
    acceptance = marker.get("acceptance_profile")
    if schema == 1:
        profile = profile or "BlazorAuto"
        acceptance = acceptance or "BlazorAutoV1"
    expected = {
        "source_sha": pin["target_sha"],
        "ci_run_id": pin["run_id"],
        "ci_run_attempt": pin["run_attempt"],
        "image": pin["app_image"],
        "digest": pin["image_digest"],
        "manifest_schema_version": pin["manifest_schema_version"],
    }
    return (
        profile == pin["profile"]
        and acceptance == pin["acceptance_profile"]
        and all(str(marker.get(field, "")) == str(value) for field, value in expected.items())
    )


def prune_local_pins(
    root: Path,
    *,
    repository: str,
    current_marker_path: Path,
    recovery_marker_path: Path | None,
    apply: bool = False,
    max_candidates_per_profile: int = 3,
    max_unprotected_bytes: int = MAX_LOCAL_PIN_BYTES,
) -> dict[str, Any]:
    """Dry-run or remove bounded unprotected pins under the shared deploy lock."""
    if not repository or max_candidates_per_profile < 0 or max_unprotected_bytes < 0:
        raise PinError("local pin retention settings are invalid")
    lock_dir, lock_token = _require_shared_lock()
    if root.is_symlink():
        raise PinError("local release pin root must not be a symlink")
    if root.exists() and not root.is_dir():
        raise PinError("local release pin root is not a directory")
    if not root.exists():
        return {
            "schema_version": 1, "outcome": "no_pins", "repository": repository,
            "pins": 0, "deleted": [], "dry_run": not apply,
            "protected": [], "marker_pins": {"current": None, "recovery": None},
        }
    root = root.resolve()
    current_marker = _read_release_marker(current_marker_path, repository)
    recovery_marker = (
        _read_release_marker(recovery_marker_path, repository)
        if recovery_marker_path is not None else None
    )
    entries: dict[str, dict[str, Any]] = {}
    for entry in root.iterdir():
        if entry.name == ".publish.lock":
            if entry.is_symlink() or not entry.is_file():
                raise PinError("local pin publication lock is unsafe")
            continue
        if entry.is_symlink() or not entry.is_dir() or not ANY_PIN_KEY.fullmatch(entry.name):
            raise PinError(f"local pin root contains an unknown or unsafe entry: {entry.name}")
        metadata = validate(entry)
        provenance = _read_json(entry / PROVENANCE, "pinned payload provenance is malformed")
        expected_key = _pin_key(metadata)
        if entry.name != expected_key or provenance.get("repository", "").casefold() != repository.casefold():
            raise PinError(f"local pin directory identity differs from its verified provenance: {entry.name}")
        entries[entry.name] = {**metadata, "bytes": _pin_size(entry)}

    protected: set[str] = set()
    marker_pins: dict[str, str | None] = {"current": None, "recovery": None}
    markers = (("current", current_marker), ("recovery", recovery_marker))
    for slot, marker in markers:
        if marker is None:
            continue
        key = marker.get("release_payload_pin_key", "")
        if key:
            pin = entries.get(key)
            if pin is None:
                raise PinError(f"release marker references a missing local pin: {key}")
            if not _pin_marker_matches(marker, pin):
                raise PinError(f"release marker identity differs from its verified local pin: {key}")
            protected.add(key)
            marker_pins[slot] = key
        elif marker.get("payload_transport", "actions-artifact") == "actions-artifact":
            matches = [
                candidate for candidate, pin in entries.items()
                if pin.get("transport") == "actions-artifact" and _pin_marker_matches(marker, pin)
            ]
            if len(matches) == 1:
                protected.add(matches[0])
                marker_pins[slot] = matches[0]
            elif len(matches) > 1:
                marker_pins[slot] = "ambiguous"

    blocked_reason = ""
    if entries and current_marker is not None and marker_pins["current"] == "ambiguous":
        blocked_reason = "current-release-local-pin-is-ambiguous"
    elif entries and recovery_marker is not None and marker_pins["recovery"] == "ambiguous":
        blocked_reason = "recovery-release-local-pin-is-ambiguous"
    elif entries and (current_marker is None or not marker_pins["current"]):
        blocked_reason = "current-release-local-pin-is-unknown"
    elif entries and recovery_marker is not None and not marker_pins["recovery"]:
        blocked_reason = "recovery-release-local-pin-is-unknown"

    profiles: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for key, pin in entries.items():
        if key not in protected:
            profiles.setdefault(pin["profile"], []).append((key, pin))
    for candidates in profiles.values():
        candidates.sort(key=lambda item: (int(item[1]["run_id"]), int(item[1]["run_attempt"]), item[0]))

    selected_for_retention: set[str] = set()
    deletion_keys: set[str] = set()
    for candidates in profiles.values():
        selected = candidates[-max_candidates_per_profile:] if max_candidates_per_profile else []
        selected_for_retention.update(key for key, _ in selected)
        deletion_keys.update(key for key, _ in candidates if key not in selected_for_retention)
    kept_candidates = [
        (key, pin) for candidates in profiles.values() for key, pin in candidates
        if key in selected_for_retention
    ]
    kept_candidates.sort(key=lambda item: (int(item[1]["run_id"]), int(item[1]["run_attempt"]), item[0]))
    candidate_bytes = sum(pin["bytes"] for _, pin in kept_candidates)
    while candidate_bytes > max_unprotected_bytes and kept_candidates:
        key, pin = kept_candidates.pop(0)
        deletion_keys.add(key)
        selected_for_retention.discard(key)
        candidate_bytes -= pin["bytes"]

    protected_bytes = sum(entries[key]["bytes"] for key in protected)
    planned = sorted(deletion_keys, key=lambda key: (int(entries[key]["run_id"]), int(entries[key]["run_attempt"]), key))
    if blocked_reason:
        planned = []

    deleted: list[str] = []
    if apply and not blocked_reason:
        for key in planned:
            current_lock, actual_token = _require_shared_lock()
            if current_lock != lock_dir or actual_token != lock_token:
                raise PinError("shared deployment lock identity changed during local pin retention")
            current_now = _read_release_marker(current_marker_path, repository)
            recovery_now = (
                _read_release_marker(recovery_marker_path, repository)
                if recovery_marker_path is not None else None
            )
            live_protected = set()
            for marker in (current_now, recovery_now):
                if marker is None:
                    continue
                marker_key = marker.get("release_payload_pin_key", "")
                if marker_key:
                    live_protected.add(marker_key)
                elif marker.get("payload_transport", "actions-artifact") == "actions-artifact":
                    if _pin_marker_matches(marker, entries[key]):
                        live_protected.add(key)
            if key in live_protected:
                raise PinError(f"refusing to delete a pin newly referenced by a release marker: {key}")
            candidate = root / key
            if candidate.is_symlink() or not candidate.is_dir() or validate(candidate) != {
                k: v for k, v in entries[key].items() if k != "bytes"
            }:
                raise PinError(f"local pin changed after selection; refusing deletion: {key}")
            shutil.rmtree(candidate)
            deleted.append(key)

    remaining_unprotected = [
        pin for key, pin in entries.items() if key not in protected and key not in deleted
    ]
    return {
        "schema_version": 1,
        "outcome": "blocked" if blocked_reason else "pruned" if apply else "dry_run",
        "repository": repository,
        "pins": len(entries),
        "protected": sorted(protected),
        "marker_pins": marker_pins,
        "protected_bytes": protected_bytes,
        "candidate_bytes": sum(pin["bytes"] for pin in remaining_unprotected),
        "candidate_limit_bytes": max_unprotected_bytes,
        "max_candidates_per_profile": max_candidates_per_profile,
        "blocked_reason": blocked_reason or None,
        "planned_delete": planned,
        "deleted": deleted,
        "dry_run": not apply,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--list-files", type=Path)
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--staging", type=Path)
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--repository")
    parser.add_argument("--target-sha")
    parser.add_argument("--profile")
    parser.add_argument("--acceptance-profile", default="")
    parser.add_argument("--runtime")
    parser.add_argument("--app-image")
    parser.add_argument("--bundle-name", default="")
    parser.add_argument("--payload-image-prefix", default="")
    parser.add_argument("--prune-root", type=Path)
    parser.add_argument("--current-marker", type=Path)
    parser.add_argument("--recovery-marker", type=Path)
    parser.add_argument("--max-candidates-per-profile", type=int, default=3)
    parser.add_argument("--max-unprotected-bytes", type=int, default=MAX_LOCAL_PIN_BYTES)
    parser.add_argument("--apply", action="store_true", help="apply selected local pin deletions")
    args = parser.parse_args()
    try:
        if args.verify:
            result = validate(args.verify)
        elif args.list_files:
            result = {"files": list(payload_files(args.list_files))}
        elif args.prune_root:
            if not args.repository or not args.current_marker:
                parser.error("local pin pruning requires repository and current marker")
            result = prune_local_pins(
                args.prune_root,
                repository=args.repository,
                current_marker_path=args.current_marker,
                recovery_marker_path=args.recovery_marker,
                apply=args.apply,
                max_candidates_per_profile=args.max_candidates_per_profile,
                max_unprotected_bytes=args.max_unprotected_bytes,
            )
        elif args.restore and args.output_dir:
            required = (args.repository, args.target_sha, args.profile, args.runtime, args.app_image)
            if any(not value for value in required):
                parser.error("restore requires repository, profile, runtime, and app image")
            result = restore(
                args.restore,
                args.output_dir,
                repository=args.repository,
                target_sha=args.target_sha,
                profile=args.profile,
                acceptance_profile=args.acceptance_profile or None,
                runtime=args.runtime,
                app_image=args.app_image,
                bundle_name=args.bundle_name or None,
                payload_image_prefix=args.payload_image_prefix,
            )
        elif args.staging and args.selection_file and args.root:
            required = (args.repository, args.profile, args.runtime, args.app_image)
            if any(not value for value in required):
                parser.error("pinning requires repository, profile, runtime, and app image")
            result = pin(
                args.staging,
                args.selection_file,
                args.root,
                repository=args.repository,
                profile=args.profile,
                acceptance_profile=args.acceptance_profile or None,
                runtime=args.runtime,
                app_image=args.app_image,
                bundle_name=args.bundle_name or None,
                payload_image_prefix=args.payload_image_prefix,
            )
        else:
            parser.error("use --verify, --list-files, --restore with an output directory, or pin with staging, selection, and root")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"release payload pin failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
