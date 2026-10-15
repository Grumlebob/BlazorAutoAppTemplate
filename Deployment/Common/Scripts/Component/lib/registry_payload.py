from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Any
import uuid


LIB = Path(__file__).resolve().parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from release_manifest import ManifestError, sha256_file, validate_manifest_payload  # noqa: E402
from release_settings import derive_release_payload_image, validate_app_image, validate_profile_name  # noqa: E402


DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
SHA_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
POSITIVE_ID_RE = re.compile(r"[1-9][0-9]{0,19}\Z")
SAFE_FILENAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
DOCKER_TAG_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")
PUSH_DIGEST_RE = re.compile(r"(?:^|\s)digest:\s*(sha256:[0-9a-f]{64})(?:\s|$)", re.MULTILINE)

PAYLOAD_KIND = "final"
PAYLOAD_KINDS = frozenset({"staging", "harness", "final"})
PAYLOAD_IMAGE_SUFFIX = "-release-payload"
# Payload images use FROM scratch and have no default command. Docker requires
# a command to create a container, though this placeholder is never started.
PAYLOAD_CREATE_PLACEHOLDER_COMMAND = "/__payload_not_started__"
MANIFEST_FILENAME = "release-manifest.json"
PROFILE_LABEL = "io.github.release-payload.profile"
ACCEPTANCE_PROFILE_LABEL = "io.github.release-payload.acceptance-profile"
KIND_LABEL = "io.github.release-payload.kind"
RUNTIME_LABEL = "io.github.release-payload.runtime"
APP_IMAGE_LABEL = "io.github.release-payload.app-image"
APP_IMAGE_DIGEST_LABEL = "io.github.release-payload.app-image-digest"
MANIFEST_LABEL = "io.github.release-payload.manifest-sha256"
BUNDLE_LABEL = "io.github.release-payload.bundle-sha256"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_BYTES = MAX_BUNDLE_BYTES + 4 * 1024 * 1024


class PayloadError(ValueError):
    """Raised when a registry payload or its frozen identity is unsafe or inconsistent."""


@dataclass(frozen=True)
class ReleasePayloadIdentity:
    repository: str
    commit_sha: str
    run_id: str
    run_attempt: str
    profile: str
    acceptance_profile: str | None
    runtime: str
    app_image: str
    app_image_digest: str
    bundle_filename: str | None
    manifest_sha256: str
    bundle_sha256: str | None

    @property
    def payload_image(self) -> str:
        return derive_release_payload_image(self.app_image)

    @property
    def tag(self) -> str:
        return payload_tag(self.run_id, self.run_attempt, self.profile)

    @property
    def image_ref(self) -> str:
        return f"{self.payload_image}:{self.tag}"


def _validate_repository(repository: str) -> str:
    prefix = "https://github.com/"
    if not isinstance(repository, str) or not repository.startswith(prefix):
        raise PayloadError("repository must be a canonical GitHub repository URL")
    path = repository[len(prefix):]
    if not path or path.endswith("/") or "?" in path or "#" in path or len(path.split("/")) != 2:
        raise PayloadError("repository must identify exactly one GitHub owner and repository")
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part in {".", ".."} for part in path.split("/")):
        raise PayloadError("repository contains an unsafe owner or repository name")
    return repository


def _validate_identity(identity: ReleasePayloadIdentity) -> None:
    _validate_repository(identity.repository)
    if not isinstance(identity.commit_sha, str) or not SHA_RE.fullmatch(identity.commit_sha):
        raise PayloadError("commit SHA must be a full lowercase hexadecimal SHA")
    if not isinstance(identity.run_id, str) or not POSITIVE_ID_RE.fullmatch(identity.run_id):
        raise PayloadError("CI run ID must be a positive decimal ID")
    if not isinstance(identity.run_attempt, str) or not POSITIVE_ID_RE.fullmatch(identity.run_attempt):
        raise PayloadError("CI run attempt must be a positive decimal number")
    try:
        validate_profile_name(identity.profile)
        if identity.acceptance_profile is not None:
            validate_profile_name(identity.acceptance_profile)
    except ValueError as error:
        raise PayloadError(str(error)) from error
    if identity.runtime not in {"linux-x64", "linux-arm64"}:
        raise PayloadError("bundle runtime must be linux-x64 or linux-arm64")
    try:
        validate_app_image(identity.app_image)
    except ValueError as error:
        raise PayloadError(str(error)) from error
    if not isinstance(identity.app_image_digest, str) or not DIGEST_RE.fullmatch(identity.app_image_digest):
        raise PayloadError("app image digest must be a lowercase sha256 digest")
    if (identity.bundle_filename is None) != (identity.bundle_sha256 is None):
        raise PayloadError("bundle filename and checksum must either both be present or both be absent")
    if identity.bundle_filename is not None:
        if not isinstance(identity.bundle_filename, str) or not SAFE_FILENAME_RE.fullmatch(identity.bundle_filename):
            raise PayloadError("bundle filename must be a safe basename")
        if identity.bundle_filename in {MANIFEST_FILENAME, ".", ".."}:
            raise PayloadError("bundle filename conflicts with the release manifest or a path component")
        if not re.fullmatch(r"[0-9a-f]{64}", identity.bundle_sha256 or ""):
            raise PayloadError("bundle SHA-256 must be 64 lowercase hexadecimal characters")
    if not isinstance(identity.manifest_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", identity.manifest_sha256):
        raise PayloadError("manifest SHA-256 must be 64 lowercase hexadecimal characters")


def content_checksum(files: dict[str, str]) -> str:
    if not isinstance(files, dict) or not files:
        raise PayloadError("payload content checksum requires at least one named file")
    normalized: list[dict[str, str]] = []
    for name, digest in files.items():
        if not isinstance(name, str) or not SAFE_FILENAME_RE.fullmatch(name):
            raise PayloadError("payload content checksum contains an unsafe filename")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PayloadError("payload content checksum contains an invalid SHA-256")
        normalized.append({"file": name, "sha256": digest})
    canonical = json.dumps(sorted(normalized, key=lambda item: item["file"]), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _allowed_manifest_schema_versions(identity: ReleasePayloadIdentity) -> tuple[int, ...]:
    if identity.bundle_filename is None:
        return (3,)
    if identity.acceptance_profile is None:
        return (1,)
    return (1, 2)


def payload_tag(run_id: str, run_attempt: str, profile: str, *, kind: str = PAYLOAD_KIND) -> str:
    if not POSITIVE_ID_RE.fullmatch(str(run_id)) or not POSITIVE_ID_RE.fullmatch(str(run_attempt)):
        raise PayloadError("CI run and attempt must be positive decimal values")
    try:
        safe_profile = validate_profile_name(profile)
    except ValueError as error:
        raise PayloadError(str(error)) from error
    safe_kind = _validate_kind(kind)
    tag = f"run-{run_id}-attempt-{run_attempt}-kind-{safe_kind.lower()}-profile-{safe_profile.lower()}"
    if not DOCKER_TAG_RE.fullmatch(tag):
        raise PayloadError("derived payload tag is invalid")
    return tag


def _validate_kind(kind: str) -> str:
    if not isinstance(kind, str) or kind not in PAYLOAD_KINDS:
        raise PayloadError(f"payload kind must be one of {sorted(PAYLOAD_KINDS)}")
    return kind


def payload_labels(identity: ReleasePayloadIdentity, *, kind: str = PAYLOAD_KIND) -> dict[str, str]:
    _validate_identity(identity)
    safe_kind = _validate_kind(kind)
    repository_name = identity.repository.removeprefix("https://github.com/")
    return {
        "org.opencontainers.image.source": identity.repository,
        "org.opencontainers.image.revision": identity.commit_sha,
        "localcluster.ci.repository": repository_name,
        "localcluster.ci.run_id": identity.run_id,
        "localcluster.ci.run_attempt": identity.run_attempt,
        PROFILE_LABEL: identity.profile,
        ACCEPTANCE_PROFILE_LABEL: identity.acceptance_profile or "",
        KIND_LABEL: safe_kind,
        RUNTIME_LABEL: identity.runtime,
        APP_IMAGE_LABEL: identity.app_image,
        APP_IMAGE_DIGEST_LABEL: identity.app_image_digest,
        MANIFEST_LABEL: identity.manifest_sha256,
        BUNDLE_LABEL: identity.bundle_sha256 or "",
    }


def validate_payload_labels(
    labels: Any,
    identity: ReleasePayloadIdentity,
    *,
    kind: str = PAYLOAD_KIND,
) -> None:
    if not isinstance(labels, dict):
        raise PayloadError("payload image labels must be an object")
    for key, expected in payload_labels(identity, kind=kind).items():
        if labels.get(key) != expected:
            raise PayloadError(f"payload image label {key!r} does not match the expected release")


def _hash_and_copy(source: Path, destination: Path, *, max_bytes: int) -> str:
    if source.is_symlink() or not source.is_file():
        raise PayloadError(f"payload input is missing or not a regular file: {source.name}")
    if source.stat().st_size <= 0 or source.stat().st_size > max_bytes:
        raise PayloadError(f"payload input has an invalid size: {source.name}")
    digest = hashlib.sha256()
    with source.open("rb") as input_stream, destination.open("xb") as output_stream:
        for chunk in iter(lambda: input_stream.read(1024 * 1024), b""):
            digest.update(chunk)
            output_stream.write(chunk)
    return digest.hexdigest()


def _docker(args: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["docker", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        command = args[0] if args else "command"
        code = getattr(error, "returncode", None)
        suffix = f" (exit {code})" if code is not None else ""
        raise PayloadError(f"docker {command} failed{suffix}") from error


def _inspect_image(image_ref: str) -> dict[str, Any]:
    result = _docker(["image", "inspect", "--format", "{{json .}}", image_ref])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise PayloadError("docker image inspect returned invalid JSON") from error
    if isinstance(payload, list):
        if len(payload) != 1 or not isinstance(payload[0], dict):
            raise PayloadError("docker image inspect did not return exactly one image")
        payload = payload[0]
    if not isinstance(payload, dict):
        raise PayloadError("docker image inspect returned an invalid image object")
    return payload


def _registry_digest(image: dict[str, Any], expected_image: str) -> str:
    digests = image.get("RepoDigests")
    if not isinstance(digests, list):
        raise PayloadError("docker image inspect did not return repository digests")
    prefix = f"{expected_image}@"
    matches = [value[len(prefix):] for value in digests if isinstance(value, str) and value.startswith(prefix)]
    if len(matches) != 1 or not DIGEST_RE.fullmatch(matches[0]):
        raise PayloadError("docker image inspect did not return one valid registry digest for the payload package")
    return matches[0]


def publish_release_payload(
    identity: ReleasePayloadIdentity,
    manifest_path: Path,
    bundle_path: Path | None = None,
    *,
    kind: str = PAYLOAD_KIND,
) -> dict[str, Any]:
    """Build and push a scratch image; return only the registry-confirmed payload digest."""
    _validate_identity(identity)
    if kind != PAYLOAD_KIND:
        raise PayloadError("release manifest payloads must use kind 'final'")
    if manifest_path.name != MANIFEST_FILENAME:
        raise PayloadError("payload input filenames do not match the frozen release identity")
    if identity.bundle_filename is None:
        if bundle_path is not None:
            raise PayloadError("file-only release identity cannot include a migration bundle")
    elif bundle_path is None or bundle_path.name != identity.bundle_filename:
        raise PayloadError("payload input filenames do not match the frozen release identity")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise PayloadError("release manifest is missing or not a regular file")
    if manifest_path.stat().st_size <= 0 or manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise PayloadError("release manifest exceeds the size limit")
    if bundle_path is not None:
        if bundle_path.is_symlink() or not bundle_path.is_file():
            raise PayloadError("migration bundle is missing or not a regular file")
        if bundle_path.stat().st_size <= 0 or bundle_path.stat().st_size > MAX_BUNDLE_BYTES:
            raise PayloadError("migration bundle has an invalid size")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PayloadError("release manifest is missing or invalid JSON") from error
    if not isinstance(manifest, dict):
        raise PayloadError("release manifest must be an object")
    if sha256_file(manifest_path) != identity.manifest_sha256:
        raise PayloadError("release manifest checksum does not match the frozen identity")
    if bundle_path is not None and sha256_file(bundle_path) != identity.bundle_sha256:
        raise PayloadError("migration bundle checksum does not match the frozen identity")
    try:
        manifest_digest = validate_manifest_payload(
            manifest,
            expected_repository=identity.repository,
            expected_sha=identity.commit_sha,
            expected_ci_run_id=identity.run_id,
            expected_ci_run_attempt=identity.run_attempt,
            expected_image=identity.app_image,
            expected_bundle_name=identity.bundle_filename,
            expected_frontend_profile=identity.profile if identity.acceptance_profile is not None else None,
            expected_acceptance_profile=identity.acceptance_profile,
            bundle_dir=bundle_path.parent if bundle_path is not None else None,
            expected_bundle_runtime=identity.runtime if identity.acceptance_profile is not None else None,
            require_migration_metadata=identity.acceptance_profile is not None,
            require_bundle_runtime=identity.acceptance_profile is not None,
            allowed_schema_versions=_allowed_manifest_schema_versions(identity),
        )
    except ManifestError as error:
        raise PayloadError(f"release manifest does not match the payload identity: {error}") from error
    if manifest_digest != identity.app_image_digest:
        raise PayloadError("release manifest application image digest does not match the frozen identity")

    labels = payload_labels(identity, kind=kind)
    tag = payload_tag(identity.run_id, identity.run_attempt, identity.profile, kind=kind)
    image_ref = f"{identity.payload_image}:{tag}"
    with tempfile.TemporaryDirectory(prefix="release-payload-") as temporary:
        context = Path(temporary)
        payload_dir = context / "payload"
        payload_dir.mkdir()
        copied_manifest = payload_dir / MANIFEST_FILENAME
        if _hash_and_copy(manifest_path, copied_manifest, max_bytes=MAX_MANIFEST_BYTES) != identity.manifest_sha256:
            raise PayloadError("release manifest changed while preparing the container context")
        if bundle_path is not None and identity.bundle_filename is not None:
            copied_bundle = payload_dir / identity.bundle_filename
            if _hash_and_copy(bundle_path, copied_bundle, max_bytes=MAX_BUNDLE_BYTES) != identity.bundle_sha256:
                raise PayloadError("migration bundle changed while preparing the container context")
        dockerfile = context / "Dockerfile"
        dockerfile.write_text("FROM scratch\nCOPY payload/ /release/\n", encoding="utf-8")
        build_args = ["build", "--file", str(dockerfile)]
        for key, value in labels.items():
            build_args.extend(["--label", f"{key}={value}"])
        build_args.extend(["--tag", image_ref, str(context)])
        _docker(build_args)
        pushed = _docker(["push", image_ref])
        push_digests = set(PUSH_DIGEST_RE.findall(pushed.stdout + "\n" + pushed.stderr))
        if len(push_digests) != 1:
            raise PayloadError("docker push did not report exactly one registry manifest digest")
        pushed_digest = next(iter(push_digests))
        inspected = _inspect_image(image_ref)
        if _registry_digest(inspected, identity.payload_image) != pushed_digest:
            raise PayloadError("pushed digest does not match the registry digest returned by image inspect")
        config = inspected.get("Config")
        inspected_labels = config.get("Labels") if isinstance(config, dict) else None
        validate_payload_labels(inspected_labels, identity, kind=kind)

    return {
        "transport": "ghcr-container",
        "kind": kind,
        "payload_image": identity.payload_image,
        "payload_tag": tag,
        "payload_digest": pushed_digest,
        "payload_ref": f"{identity.payload_image}@{pushed_digest}",
        "repository": identity.repository,
        "commit_sha": identity.commit_sha,
        "run_id": identity.run_id,
        "run_attempt": identity.run_attempt,
        "profile": identity.profile,
        "acceptance_profile": identity.acceptance_profile,
        "runtime": identity.runtime,
        "content_sha256": content_checksum(
            {
                **{MANIFEST_FILENAME: identity.manifest_sha256},
                **({identity.bundle_filename: identity.bundle_sha256} if identity.bundle_filename is not None else {}),
            }
        ),
        "manifest_sha256": identity.manifest_sha256,
        "bundle_filename": identity.bundle_filename,
        "bundle_sha256": identity.bundle_sha256,
        "app_image": identity.app_image,
        "app_image_digest": identity.app_image_digest,
    }


def extract_payload_archive(
    archive_path: Path,
    *,
    identity: ReleasePayloadIdentity,
    output_dir: Path,
) -> dict[str, Path]:
    """Extract the two allowed regular files from a docker-export tar without running the image."""
    _validate_identity(identity)
    if archive_path.is_symlink() or not archive_path.is_file():
        raise PayloadError("container export archive is missing or not a regular file")
    if archive_path.stat().st_size <= 0 or archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise PayloadError("container export archive has an invalid size")
    if output_dir.exists() or output_dir.is_symlink():
        raise PayloadError("payload extraction output path must not already exist")

    expected_files = {
        f"release/{MANIFEST_FILENAME}": (MANIFEST_FILENAME, identity.manifest_sha256, MAX_MANIFEST_BYTES),
    }
    if identity.bundle_filename is not None and identity.bundle_sha256 is not None:
        expected_files[f"release/{identity.bundle_filename}"] = (
            identity.bundle_filename,
            identity.bundle_sha256,
            MAX_BUNDLE_BYTES,
        )
    seen: set[str] = set()
    found: dict[str, Path] = {}
    total_bytes = 0
    output_dir.mkdir(parents=True)
    try:
        with tarfile.open(archive_path, mode="r:") as archive:
            members = archive.getmembers()
            for member in members:
                raw_name = member.name
                if not isinstance(raw_name, str) or "\\" in raw_name or raw_name.startswith("/"):
                    raise PayloadError("container export contains an unsafe path")
                normalized = raw_name
                while normalized.startswith("./"):
                    normalized = normalized[2:]
                normalized = normalized.rstrip("/")
                if normalized in {"", "."}:
                    if not member.isdir():
                        raise PayloadError("container export has an invalid root entry")
                    continue
                parts = PurePosixPath(normalized).parts
                if any(part in {"", ".", ".."} for part in parts):
                    raise PayloadError("container export contains path traversal")
                if normalized == "release":
                    if not member.isdir():
                        raise PayloadError("container payload root is not a directory")
                    if normalized in seen:
                        raise PayloadError("container export contains duplicate paths")
                    seen.add(normalized)
                    continue
                expected = expected_files.get(normalized)
                if expected is None:
                    raise PayloadError(f"container export contains an unexpected path: {normalized}")
                if not member.isfile() or member.issym() or member.islnk():
                    raise PayloadError(f"container payload entry is not a regular file: {normalized}")
                if normalized in seen:
                    raise PayloadError("container export contains duplicate paths")
                if member.size <= 0 or member.size > expected[2]:
                    raise PayloadError(f"container payload file has an invalid size: {normalized}")
                total_bytes += member.size
                if total_bytes > MAX_ARCHIVE_BYTES:
                    raise PayloadError("container payload exceeds the size limit")
                stream = archive.extractfile(member)
                if stream is None:
                    raise PayloadError(f"container payload entry cannot be read: {normalized}")
                destination = output_dir / expected[0]
                digest = hashlib.sha256()
                written = 0
                with stream, destination.open("xb") as output:
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > expected[2]:
                            raise PayloadError(f"container payload file exceeds the size limit: {normalized}")
                        digest.update(chunk)
                        output.write(chunk)
                if digest.hexdigest() != expected[1]:
                    raise PayloadError(f"container payload checksum mismatch: {normalized}")
                seen.add(normalized)
                found[normalized] = destination
        if set(found) != set(expected_files):
            missing = sorted(set(expected_files).difference(found))
            raise PayloadError(f"container export is missing required payload files: {missing}")
        try:
            manifest = json.loads(found[f"release/{MANIFEST_FILENAME}"].read_text(encoding="utf-8"))
            manifest_digest = validate_manifest_payload(
                manifest,
                expected_repository=identity.repository,
                expected_sha=identity.commit_sha,
                expected_ci_run_id=identity.run_id,
                expected_ci_run_attempt=identity.run_attempt,
                expected_image=identity.app_image,
                expected_bundle_name=identity.bundle_filename,
                expected_frontend_profile=identity.profile if identity.acceptance_profile is not None else None,
                expected_acceptance_profile=identity.acceptance_profile,
                bundle_dir=output_dir if identity.bundle_filename is not None else None,
                expected_bundle_runtime=identity.runtime if identity.acceptance_profile is not None else None,
                require_migration_metadata=identity.acceptance_profile is not None,
                require_bundle_runtime=identity.acceptance_profile is not None,
                allowed_schema_versions=_allowed_manifest_schema_versions(identity),
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ManifestError) as error:
            raise PayloadError(f"extracted release manifest failed validation: {error}") from error
        if manifest_digest != identity.app_image_digest:
            raise PayloadError("extracted manifest application image digest does not match the payload identity")
        result = {"manifest": found[f"release/{MANIFEST_FILENAME}"]}
        if identity.bundle_filename is not None:
            result["bundle"] = found[f"release/{identity.bundle_filename}"]
        return result
    except (tarfile.TarError, OSError) as error:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise PayloadError("container export archive could not be safely read") from error
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def pull_and_extract_release_payload(
    identity: ReleasePayloadIdentity,
    payload_digest: str,
    output_dir: Path,
    *,
    kind: str = PAYLOAD_KIND,
) -> dict[str, Path]:
    """Pull an immutable payload, inspect its identity, create but never start a container, then export it."""
    _validate_identity(identity)
    if not isinstance(payload_digest, str) or not DIGEST_RE.fullmatch(payload_digest):
        raise PayloadError("payload digest must be a lowercase sha256 digest")
    frozen_ref = f"{identity.payload_image}@{payload_digest}"
    _docker(["pull", frozen_ref])
    inspected = _inspect_image(frozen_ref)
    if _registry_digest(inspected, identity.payload_image) != payload_digest:
        raise PayloadError("pulled registry digest does not match the frozen payload digest")
    config = inspected.get("Config")
    inspected_labels = config.get("Labels") if isinstance(config, dict) else None
    validate_payload_labels(inspected_labels, identity, kind=kind)

    container_id = ""
    container_name = f"release-payload-extract-{uuid.uuid4().hex}"
    created_container = False
    try:
        created = _docker(
            ["create", "--name", container_name, frozen_ref, PAYLOAD_CREATE_PLACEHOLDER_COMMAND]
        )
        created_container = True
        container_id = created.stdout.strip()
        if not re.fullmatch(r"[a-f0-9]{12,64}", container_id):
            raise PayloadError("docker create returned an invalid container ID")
        with tempfile.TemporaryDirectory(prefix="release-payload-export-") as temporary:
            archive_path = Path(temporary) / "container-export.tar"
            _docker(["export", "--output", str(archive_path), container_id])
            return extract_payload_archive(archive_path, identity=identity, output_dir=output_dir)
    finally:
        if created_container:
            active_exception = sys.exc_info()[0] is not None
            cleanup_target = container_id if re.fullmatch(r"[a-f0-9]{12,64}", container_id) else container_name
            try:
                cleanup = subprocess.run(
                    ["docker", "rm", cleanup_target],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                cleanup_failed = cleanup.returncode != 0
            except (OSError, subprocess.TimeoutExpired):
                cleanup_failed = True
            if cleanup_failed and not active_exception:
                shutil.rmtree(output_dir, ignore_errors=True)
                raise PayloadError("docker could not remove the stopped payload inspection container")
