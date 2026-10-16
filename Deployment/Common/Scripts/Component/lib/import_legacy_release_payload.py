#!/usr/bin/env python3
"""Verify and pin a release payload from an exact legacy Actions artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Any

LIB = Path(__file__).resolve().parent
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import pin_release_payload  # noqa: E402
import registry_payload  # noqa: E402
from release_manifest import ManifestError, sha256_file, validate_manifest_payload  # noqa: E402

API_ROOT = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
API_VERSION = "2022-11-28"
MANIFEST = registry_payload.MANIFEST_FILENAME
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
OWNER_REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
MAX_ARCHIVE_BYTES = registry_payload.MAX_ARCHIVE_BYTES


class ImportError(ValueError):
    """Raised when artifact provenance or contents are unsafe or inconsistent."""


def _github_json(path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError, urllib.error.HTTPError) as error:
        raise ImportError("GitHub Actions artifact provenance is unavailable") from error
    if not isinstance(value, dict):
        raise ImportError("GitHub Actions artifact response is malformed")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _artifact_download_url(api_root: str, repository: str, artifact_id: str, token: str) -> str:
    url = f"{api_root.rstrip('/')}/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise ImportError("GitHub Actions artifact download is unavailable") from error
        location = error.headers.get("Location", "")
    except (OSError, urllib.error.URLError) as error:
        raise ImportError("GitHub Actions artifact download is unavailable") from error
    else:
        with response:
            if response.status != 200:
                raise ImportError("GitHub Actions artifact download returned an unexpected response")
            # The API normally redirects. Keeping direct responses in a temporary
            # file is handled by the caller through the same bounded stream path.
            raise ImportError("GitHub Actions artifact API did not return a download redirect")
    parsed = urllib.parse.urlsplit(location)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ImportError("GitHub Actions artifact download redirect is unsafe")
    return location


def _download_archive(location: str, destination: Path, expected_size: int) -> str:
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(urllib.request.Request(location), timeout=120) as response:
            with destination.open("xb") as output:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > min(MAX_ARCHIVE_BYTES, expected_size):
                        raise ImportError("Actions artifact archive exceeds its verified size")
                    digest.update(chunk)
                    output.write(chunk)
    except (OSError, urllib.error.URLError) as error:
        raise ImportError("GitHub Actions artifact archive could not be downloaded") from error
    if total != expected_size:
        raise ImportError("Actions artifact archive size differs from GitHub metadata")
    return "sha256:" + digest.hexdigest()


def _validate_run_and_publisher(repository: str, selected: dict[str, Any], token: str) -> None:
    run_id = selected["id"]
    attempt = selected["run_attempt"]
    sha = selected["head_sha"]
    run = _github_json(f"/repos/{repository}/actions/runs/{run_id}", token)
    repository_info = run.get("repository")
    trusted = (
        isinstance(repository_info, dict)
        and repository_info.get("full_name", "").casefold() == repository.casefold()
        and run.get("head_sha") == sha
        and run.get("head_branch") == "main"
        and run.get("event") in {"push", "workflow_dispatch"}
        and str(run.get("path", "")).split("@", 1)[0] == ".github/workflows/ci.yml"
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and type(run.get("run_attempt")) is int
        and str(run["run_attempt"]) == attempt
    )
    if not trusted:
        raise ImportError("selected CI run is no longer trusted successful main provenance")

    jobs: list[dict[str, Any]] = []
    for page in range(1, 101):
        query = urllib.parse.urlencode({"per_page": "100", "page": str(page)})
        payload = _github_json(
            f"/repos/{repository}/actions/runs/{run_id}/attempts/{attempt}/jobs?{query}", token
        )
        rows = payload.get("jobs")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ImportError("selected CI attempt job metadata is malformed")
        jobs.extend(rows)
        if len(rows) < 100:
            break
    else:
        raise ImportError("selected CI attempt job history exceeds the safe pagination limit")
    publishers = [job for job in jobs if job.get("name") == "build-test-push"]
    if len(publishers) != 1:
        raise ImportError("selected CI attempt has no unique successful publisher job")
    job = publishers[0]
    if (job.get("status") != "completed" or job.get("conclusion") != "success"
            or str(job.get("run_id", "")) != run_id
            or str(job.get("run_attempt", "")) != attempt
            or str(job.get("head_sha", "")).lower() != sha):
        raise ImportError("selected CI publisher job differs from the exact run attempt")


def _list_artifacts(repository: str, run_id: str, sha: str, token: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for page in range(1, 101):
        query = urllib.parse.urlencode({"per_page": "100", "page": str(page)})
        payload = _github_json(f"/repos/{repository}/actions/runs/{run_id}/artifacts?{query}", token)
        rows = payload.get("artifacts")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ImportError("selected CI artifact metadata is malformed")
        for artifact in rows:
            workflow_run = artifact.get("workflow_run")
            if not isinstance(workflow_run, dict):
                raise ImportError("selected CI artifact has no run identity")
            if (str(workflow_run.get("id", "")) != run_id
                    or workflow_run.get("head_sha", "").lower() != sha):
                raise ImportError("GitHub returned an artifact from a different CI run")
            artifacts.append(artifact)
        if len(rows) < 100:
            return artifacts
    raise ImportError("selected CI artifact history exceeds the safe pagination limit")


def _artifact_members(archive: Path, bundle_name: str | None) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
    try:
        zipped = zipfile.ZipFile(archive)
        infos = zipped.infolist()
    except (OSError, zipfile.BadZipFile) as error:
        raise ImportError("Actions artifact is not a valid ZIP archive") from error
    members: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = info.filename
        posix = PurePosixPath(name)
        mode = info.external_attr >> 16
        if (not name or name in members or name.endswith("/") or "\\" in name
                or posix.is_absolute() or len(posix.parts) != 1 or ".." in posix.parts
                or not pin_release_payload.SAFE_FILENAME.fullmatch(name)
                or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                or info.flag_bits & 0x1):
            zipped.close()
            raise ImportError("Actions artifact contains an unsafe or duplicate archive entry")
        members[name] = info
    expected_names = {MANIFEST}
    if bundle_name is not None:
        expected_names.add(bundle_name)
    if set(members) != expected_names:
        zipped.close()
        raise ImportError("Actions artifact contains missing or unexpected release files")
    if members[MANIFEST].file_size <= 0 or members[MANIFEST].file_size > registry_payload.MAX_MANIFEST_BYTES:
        zipped.close()
        raise ImportError("Actions artifact release manifest has an invalid size")
    if bundle_name is not None:
        bundle_info = members[bundle_name]
        if bundle_info.file_size <= 0 or bundle_info.file_size > registry_payload.MAX_BUNDLE_BYTES:
            zipped.close()
            raise ImportError("Actions artifact migration bundle has an invalid size")
    if sum(info.file_size for info in members.values()) > registry_payload.MAX_BUNDLE_BYTES + registry_payload.MAX_MANIFEST_BYTES:
        zipped.close()
        raise ImportError("Actions artifact uncompressed contents exceed the release size limit")
    return zipped, members


def _read_manifest(zipped: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict[str, Any]:
    try:
        with zipped.open(info) as stream:
            content = stream.read(registry_payload.MAX_MANIFEST_BYTES + 1)
        value = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise ImportError("Actions artifact release manifest is malformed") from error
    if len(content) > registry_payload.MAX_MANIFEST_BYTES or not isinstance(value, dict):
        raise ImportError("Actions artifact release manifest has an invalid size or shape")
    return value


def _matches_selection(manifest: dict[str, Any], selected: dict[str, str]) -> bool:
    return (
        str(manifest.get("ci_run_id", "")) == selected["id"]
        and str(manifest.get("attempt", "")) == selected["run_attempt"]
        and manifest.get("commit_sha") == selected["head_sha"]
    )


def _extract(zipped: zipfile.ZipFile, members: dict[str, zipfile.ZipInfo], destination: Path) -> None:
    destination.mkdir(mode=0o700)
    for name, info in members.items():
        source = zipped.open(info)
        total = 0
        try:
            with source, (destination / name).open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    total += len(chunk)
                    if total > info.file_size:
                        raise ImportError("Actions artifact entry exceeded its declared size")
                    output.write(chunk)
                if total != info.file_size:
                    raise ImportError("Actions artifact entry size differs from its ZIP metadata")
        except (OSError, zipfile.BadZipFile) as error:
            raise ImportError("Actions artifact release file could not be extracted") from error
        os.chmod(destination / name, 0o600)


def _make_provenance(
    staging: Path,
    *,
    artifact: dict[str, Any],
    artifact_digest: str,
    repository_url: str,
    selected: dict[str, str],
    profile: str,
    acceptance_profile: str,
    runtime: str,
    app_image: str,
    bundle_name: str | None,
) -> dict[str, Any]:
    manifest_path = staging / MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ImportError("verified Actions artifact manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = manifest.get("schema_version")
    expected_runtime = runtime if bundle_name is not None and schema != 1 else None
    try:
        image_digest = validate_manifest_payload(
            manifest,
            expected_repository=repository_url,
            expected_sha=selected["head_sha"],
            expected_ci_run_id=selected["id"],
            expected_ci_run_attempt=selected["run_attempt"],
            expected_image=app_image,
            expected_bundle_name=bundle_name,
            expected_frontend_profile=profile,
            expected_acceptance_profile=acceptance_profile,
            bundle_dir=staging if bundle_name is not None else None,
            expected_bundle_runtime=expected_runtime,
            require_migration_metadata=bundle_name is not None and schema >= 2,
            require_bundle_runtime=bundle_name is not None and schema != 1,
            allowed_schema_versions=(1, 2) if bundle_name is not None else (3,),
        )
    except (ManifestError, OSError, ValueError, TypeError) as error:
        raise ImportError("legacy release manifest does not match the trusted target and profile") from error
    if type(schema) is not int:
        raise ImportError("legacy release manifest schema is malformed")
    if schema == 1 and (profile, acceptance_profile) != ("BlazorAuto", "BlazorAutoV1"):
        raise ImportError("legacy manifest schema-v1 is supported only for the Blazor profile")
    bundle_sha = manifest["bundle"]["sha256"] if bundle_name is not None else None
    files = {MANIFEST: sha256_file(manifest_path)}
    if bundle_name is not None:
        files[bundle_name] = bundle_sha
    return {
        "schema_version": 1,
        "transport": "actions-artifact",
        "repository": repository_url,
        "target_sha": selected["head_sha"],
        "run_id": selected["id"],
        "run_attempt": selected["run_attempt"],
        "profile": profile,
        "acceptance_profile": acceptance_profile,
        "runtime": runtime,
        "app_image": app_image,
        "image_digest": image_digest,
        "manifest_sha256": files[MANIFEST],
        "bundle_filename": bundle_name,
        "bundle_sha256": bundle_sha,
        "content_sha256": registry_payload.content_checksum(files),
        "manifest_schema_version": schema,
        "artifact_id": str(artifact["id"]),
        "artifact_name": artifact["name"],
        "artifact_digest": artifact_digest,
        "artifact_size_bytes": artifact["size_in_bytes"],
    }


def import_legacy_artifact(
    selection: dict[str, Any],
    root: Path,
    *,
    repository: str,
    repository_url: str,
    token: str,
    artifact_name: str,
    profile: str,
    acceptance_profile: str,
    runtime: str,
    app_image: str,
    bundle_name: str | None,
    expected_image_digest: str | None = None,
) -> dict[str, Any]:
    if selection.get("outcome") != "legacy_artifact" or not isinstance(selection.get("selected"), dict):
        raise ImportError("CI selection is not an exact legacy release")
    if not OWNER_REPO.fullmatch(repository) or not token.strip():
        raise ImportError("GitHub repository or token is unavailable")
    selected_raw = selection["selected"]
    try:
        selected = {
            "id": str(selected_raw["id"]),
            "run_attempt": str(selected_raw["run_attempt"]),
            "head_sha": str(selected_raw["head_sha"]).lower(),
        }
    except (KeyError, TypeError) as error:
        raise ImportError("legacy CI selection identity is malformed") from error
    if (not re.fullmatch(r"[1-9][0-9]{0,19}", selected["id"])
            or not re.fullmatch(r"[1-9][0-9]{0,19}", selected["run_attempt"])
            or not re.fullmatch(r"[0-9a-f]{40}", selected["head_sha"])):
        raise ImportError("legacy CI selection identity is malformed")
    _validate_run_and_publisher(repository, selected, token)
    artifacts = _list_artifacts(repository, selected["id"], selected["head_sha"], token)
    matching = [artifact for artifact in artifacts if artifact.get("name") == artifact_name]
    if not matching:
        raise ImportError("selected CI attempt has no artifact with the configured release name")
    for artifact in matching:
        if (type(artifact.get("id")) is not int or artifact["id"] <= 0
                or type(artifact.get("size_in_bytes")) is not int
                or artifact["size_in_bytes"] <= 0 or artifact["size_in_bytes"] > MAX_ARCHIVE_BYTES
                or not isinstance(artifact.get("digest"), str) or not SHA256.fullmatch(artifact["digest"])
                or artifact.get("expired") is not False):
            raise ImportError("selected CI release artifact is expired or has incomplete integrity metadata")

    exact_matches: list[tuple[dict[str, Any], dict[str, Any], Path]] = []
    with tempfile.TemporaryDirectory(prefix="legacy-release-import-") as temporary:
        scratch = Path(temporary)
        for index, artifact in enumerate(matching):
            location = _artifact_download_url(API_ROOT, repository, str(artifact["id"]), token)
            archive_path = scratch / f"artifact-{index}.zip"
            actual_digest = _download_archive(location, archive_path, artifact["size_in_bytes"])
            if actual_digest != artifact["digest"]:
                raise ImportError("Actions artifact archive SHA-256 differs from GitHub metadata")
            zipped, members = _artifact_members(archive_path, bundle_name)
            try:
                manifest = _read_manifest(zipped, members[MANIFEST])
                if not _matches_selection(manifest, selected):
                    continue
                stage = scratch / f"staging-{index}"
                _extract(zipped, members, stage)
                provenance = _make_provenance(
                    stage,
                    artifact=artifact,
                    artifact_digest=actual_digest,
                    repository_url=repository_url,
                    selected=selected,
                    profile=profile,
                    acceptance_profile=acceptance_profile,
                    runtime=runtime,
                    app_image=app_image,
                    bundle_name=bundle_name,
                )
                if expected_image_digest and provenance["image_digest"] != expected_image_digest:
                    raise ImportError("legacy manifest image digest differs from the accepted release marker")
                exact_matches.append((artifact, provenance, stage))
            finally:
                zipped.close()
        if len(exact_matches) != 1:
            if len(exact_matches) > 1:
                raise ImportError("multiple Actions artifacts match the exact CI run attempt")
            raise ImportError("no Actions artifact manifest matches the exact CI run attempt")
        _, provenance, stage = exact_matches[0]
        result = pin_release_payload.pin_legacy(stage, provenance, root)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-file", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--repository", required=True, help="GitHub owner/name")
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--acceptance-profile", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--app-image", required=True)
    parser.add_argument("--bundle-name", default="")
    parser.add_argument("--expected-image-digest", default="")
    args = parser.parse_args()
    try:
        selection = json.loads(args.selection_file.read_text(encoding="utf-8"))
        if not isinstance(selection, dict):
            raise ImportError("CI selection is malformed")
        result = import_legacy_artifact(
            selection,
            args.root,
            repository=args.repository,
            repository_url=args.repository_url,
            token=os.environ.get("GITHUB_TOKEN", ""),
            artifact_name=args.artifact_name,
            profile=args.profile,
            acceptance_profile=args.acceptance_profile,
            runtime=args.runtime,
            app_image=args.app_image,
            bundle_name=args.bundle_name or None,
            expected_image_digest=args.expected_image_digest or None,
        )
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f"legacy release payload import failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
