#!/usr/bin/env python3
"""Shared read-only release status validation for deployment runners."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import pin_release_payload
from release_manifest import sha256_file

SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
SOURCE_SHA = re.compile(r"[0-9a-f]{40}\Z")
POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*\Z")
PIN_KEY = re.compile(r"(?:ghcr-[0-9a-f]{64}-[0-9a-f]{64}|legacy-[1-9][0-9]{0,19}-[0-9a-f]{64})\Z")
LEGACY_PIN_KEY = re.compile(r"legacy-[1-9][0-9]{0,19}-[0-9a-f]{64}\Z")
ACTIVE_STATUSES = ("queued", "in_progress", "waiting", "requested", "pending")
CD_WORKFLOWS = ("cd-localcluster.yml", "cd-localsinglenode.yml")
PROFILE_ACCEPTANCE = {"BlazorAuto": "BlazorAutoV1", "React": "ReactPublicV1"}


class ReleaseStatusError(ValueError):
    """Raised when current release state cannot be verified safely."""


def summarize_marker(
    marker: dict[str, Any] | None,
    *,
    repository_url: str,
    app_image: str,
) -> dict[str, Any] | None:
    if marker is None:
        return None
    if not isinstance(marker, dict):
        raise ReleaseStatusError("release marker is not a JSON object")

    source_sha = marker.get("source_sha")
    source_repo_url = marker.get("source_repo_url")
    if (not isinstance(source_sha, str) or not SOURCE_SHA.fullmatch(source_sha)
            or marker.get("sha", source_sha) != source_sha
            or not isinstance(source_repo_url, str)
            or source_repo_url.casefold() != repository_url.casefold()):
        raise ReleaseStatusError("release marker source identity is invalid")

    schema = marker.get("manifest_schema_version")
    if type(schema) is not int or schema not in (1, 2):
        raise ReleaseStatusError("release marker manifest schema is unsupported")
    frontend = marker.get("frontend_profile")
    acceptance = marker.get("acceptance_profile")
    if schema == 1:
        if frontend is None and acceptance is None:
            frontend, acceptance = "BlazorAuto", "BlazorAutoV1"
        if (frontend, acceptance) != ("BlazorAuto", "BlazorAutoV1"):
            raise ReleaseStatusError("legacy release marker does not match the Blazor profile")
    elif frontend not in PROFILE_ACCEPTANCE or PROFILE_ACCEPTANCE[frontend] != acceptance:
        raise ReleaseStatusError("release marker frontend and acceptance profiles do not match")

    digest = marker.get("digest")
    image = marker.get("image")
    run_id = marker.get("ci_run_id")
    attempt = marker.get("ci_run_attempt")
    if (not isinstance(digest, str) or not SHA256.fullmatch(digest)
            or image != app_image
            or not isinstance(run_id, str) or not POSITIVE_INTEGER.fullmatch(run_id)
            or not isinstance(attempt, str) or not POSITIVE_INTEGER.fullmatch(attempt)):
        raise ReleaseStatusError("release marker image or CI run identity is invalid")

    transport = marker.get("payload_transport", "actions-artifact")
    pin_key = marker.get("release_payload_pin_key", "") or ""
    if transport not in ("actions-artifact", "ghcr-container", "local-pin"):
        raise ReleaseStatusError("release marker payload transport is unsupported")
    if not isinstance(pin_key, str) or (pin_key and not PIN_KEY.fullmatch(pin_key)):
        raise ReleaseStatusError("release marker local pin key is malformed")
    if transport in ("ghcr-container", "local-pin") and not pin_key:
        raise ReleaseStatusError("registry release marker has no immutable local pin key")
    if transport == "actions-artifact" and pin_key and not LEGACY_PIN_KEY.fullmatch(pin_key):
        raise ReleaseStatusError("legacy release marker local pin key is not an Actions-artifact pin")

    return {
        "source_sha": source_sha,
        "image": image,
        "digest": digest,
        "frontend_profile": frontend,
        "acceptance_profile": acceptance,
        "manifest_schema_version": schema,
        "ci_run_id": run_id,
        "ci_run_attempt": attempt,
        "payload_transport": transport,
        "release_payload_pin_key": pin_key or None,
    }


def pin_state(
    release: dict[str, Any] | None,
    protected_pins: set[str],
    inferred_pin_key: str | None = None,
) -> str:
    if release is None:
        return "no-release"
    key = release["release_payload_pin_key"]
    if key:
        if key not in protected_pins:
            raise ReleaseStatusError("release marker pin was not validated by local pin inspection")
        return "verified"
    if release["payload_transport"] == "actions-artifact":
        if inferred_pin_key == "ambiguous":
            return "ambiguous-local-pins"
        if inferred_pin_key is not None:
            if inferred_pin_key not in protected_pins:
                raise ReleaseStatusError("inferred legacy release pin was not validated by local pin inspection")
            return "verified"
        return "legacy-artifact-only"
    raise ReleaseStatusError("registry release has no durable local pin")


def verified_registry_payload_references(
    releases: dict[str, dict[str, Any] | None],
    marker_pins: dict[str, str | None],
    pin_root: Path,
) -> list[dict[str, str]]:
    """Return immutable GHCR roots proven by the exact current/recovery local pins."""
    references = []
    for slot in ("current", "recovery"):
        release = releases.get(slot)
        if release is None:
            continue
        pin_key = marker_pins.get(slot)
        is_registry = (release.get("payload_transport") == "ghcr-container"
                       or (release.get("payload_transport") == "local-pin"
                           and str(release.get("release_payload_pin_key") or "").startswith("ghcr-")))
        if not is_registry:
            continue
        if not isinstance(pin_key, str) or not pin_key.startswith("ghcr-") or pin_key == "ambiguous":
            raise ReleaseStatusError(f"{slot} GHCR marker has no verified local pin")
        try:
            pin = pin_release_payload.validate(pin_root / pin_key)
        except (OSError, ValueError) as error:
            raise ReleaseStatusError(f"{slot} GHCR local pin is unavailable") from error
        if (pin.get("transport") != "ghcr-container"
                or pin.get("target_sha") != release.get("source_sha")
                or str(pin.get("run_id")) != release.get("ci_run_id")
                or str(pin.get("run_attempt")) != release.get("ci_run_attempt")
                or not isinstance(pin.get("payload_image"), str)
                or not isinstance(pin.get("payload_digest"), str)):
            raise ReleaseStatusError(f"{slot} GHCR pin differs from its release marker")
        references.append({
            "payload_image": pin["payload_image"],
            "payload_digest": pin["payload_digest"],
            "ci_run_id": str(pin["run_id"]),
            "ci_run_attempt": str(pin["run_attempt"]),
            "source_sha": pin["target_sha"],
        })
    return references


def protected_application_image_references(status: dict, *, repository: str, app_image: str) -> tuple[str, ...]:
    """Derive image protection from the existing verified release status authority."""
    if (not isinstance(status, dict) or type(status.get("schema_version")) is not int or status.get("schema_version") != 1
            or str(status.get("repository", "")).casefold() != repository.casefold()
            or status.get("shared_lock") != "held" or status.get("mutation") != "none"
            or status.get("live_identity") != "verified"):
        raise ReleaseStatusError("verified locked release status is unavailable for image cleanup")
    if not isinstance(app_image, str) or not re.fullmatch(r"ghcr\.io/[a-z0-9][a-z0-9._/-]*[a-z0-9]", app_image):
        raise ReleaseStatusError("configured application image is malformed")
    references = set()
    for slot in ("current", "recovery"):
        release = status.get(slot + "_release")
        if not isinstance(release, dict) or status.get(slot + "_pin") != "verified":
            raise ReleaseStatusError("current and recovery image protection must both be verified")
        digest, source = release.get("digest"), release.get("source_sha")
        if (release.get("image") != app_image or not isinstance(digest, str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
                or not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source)):
            raise ReleaseStatusError("protected application image identity is malformed")
        references.update((app_image + "@" + digest, app_image + ":" + source))
    active = status.get("active_deployments")
    if not isinstance(active, list):
        raise ReleaseStatusError("active deployment image protection is unavailable")
    for deployment in active:
        source = deployment.get("target_sha") if isinstance(deployment, dict) else None
        if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source):
            raise ReleaseStatusError("active deployment target image is unknown")
        references.add(app_image + ":" + source)
    return tuple(sorted(references))


def verify_cached_application_image(release: dict[str, Any], *, inspect=None) -> None:
    """Inspect the exact local image without pulling or contacting a registry."""
    image, digest = release.get("image"), release.get("digest")
    if (not isinstance(image, str) or not re.fullmatch(r"ghcr\.io/[a-z0-9][a-z0-9._/-]*[a-z0-9]", image)
            or not isinstance(digest, str) or not SHA256.fullmatch(digest)):
        raise ReleaseStatusError("offline application image identity is malformed")
    reference = image + "@" + digest
    try:
        if inspect is None:
            result = subprocess.run(
                ["docker", "image", "inspect", reference], capture_output=True, text=True,
                check=True, timeout=30,
            )
            rows = json.loads(result.stdout)
        else:
            rows = inspect(reference)
        if (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
                or reference not in (rows[0].get("RepoDigests") or [])
                or not SHA256.fullmatch(str(rows[0].get("Id", "")))):
            raise ValueError("local image digest does not match")
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        raise ReleaseStatusError("exact offline application image is unavailable; no pull was attempted") from error


def verify_offline_pin_restore(
    release: dict[str, Any] | None,
    pin_root: Path,
    *,
    repository_url: str,
    runtime: str,
    bundle_name: str | None,
    payload_image_prefix: str,
    temp_root: Path,
    validated_pin_key: str | None = None,
    application_image_inspector=None,
) -> dict[str, Any]:
    """Restore one exact local pin with GitHub and registry credentials unavailable."""
    if release is None:
        return {"outcome": "no-release"}
    marker_pin_key = release.get("release_payload_pin_key")
    if marker_pin_key and validated_pin_key and marker_pin_key != validated_pin_key:
        raise ReleaseStatusError("offline local pin does not match the selected release")
    pin_key = marker_pin_key or validated_pin_key
    if not isinstance(pin_key, str) or not PIN_KEY.fullmatch(pin_key):
        raise ReleaseStatusError("release has no exact local pin for offline restore")

    credentials = (
        "GITHUB_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN", "GHCR_TOKEN", "GHCR_USERNAME", "DOCKER_CONFIG",
        "ACTIONS_RUNTIME_TOKEN", "ACTIONS_RESULTS_URL", "ACTIONS_CACHE_URL",
        "ACTIONS_ID_TOKEN_REQUEST_URL", "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    )
    saved_credentials = {name: os.environ.pop(name) for name in credentials if name in os.environ}
    try:
        pin_release_payload._require_shared_lock()
        pin_dir = pin_root / pin_key
        metadata = pin_release_payload.validate(pin_dir)
        expected_identity = {
            "repository": repository_url,
            "target_sha": release["source_sha"],
            "run_id": release["ci_run_id"],
            "run_attempt": release["ci_run_attempt"],
            "profile": release["frontend_profile"],
            "acceptance_profile": release["acceptance_profile"],
            "runtime": runtime,
            "app_image": release["image"],
            "image_digest": release["digest"],
            "manifest_schema_version": release["manifest_schema_version"],
            "bundle_filename": bundle_name,
        }
        if any(metadata.get(field) != value for field, value in expected_identity.items()):
            raise ReleaseStatusError("offline local pin does not match the selected release")

        expected_files = {"release-manifest.json": metadata["manifest_sha256"]}
        if metadata.get("bundle_filename") is not None:
            expected_files[metadata["bundle_filename"]] = metadata["bundle_sha256"]
        if not temp_root.is_dir() or temp_root.is_symlink():
            raise ReleaseStatusError("offline restore scratch directory is unavailable")

        with tempfile.TemporaryDirectory(prefix="template-offline-pin-restore-", dir=temp_root) as directory:
            output_dir = Path(directory) / "payload"
            restored = pin_release_payload.restore(
                pin_dir,
                output_dir,
                repository=repository_url,
                target_sha=release["source_sha"],
                profile=release["frontend_profile"],
                acceptance_profile=release["acceptance_profile"],
                runtime=runtime,
                app_image=release["image"],
                bundle_name=bundle_name,
                payload_image_prefix=payload_image_prefix,
            )
            if restored.get("pin_key") != pin_key:
                raise ReleaseStatusError("offline restore returned a different local pin identity")
            restored_names = {path.name for path in output_dir.iterdir()}
            if restored_names != set(expected_files):
                raise ReleaseStatusError("offline restore returned an unexpected payload file set")
            for name, digest in expected_files.items():
                path = output_dir / name
                if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
                    raise ReleaseStatusError("offline restore did not reproduce the pinned payload checksums")
            (application_image_inspector or verify_cached_application_image)(release)
    except ReleaseStatusError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ReleaseStatusError("offline local pin restore failed") from error
    finally:
        os.environ.update(saved_credentials)

    return {
        "outcome": "verified",
        "pin_key": pin_key,
        "transport": metadata["transport"],
        "file_count": len(expected_files),
        "application_image": "verified-local-digest",
    }


def _api_get(api_root: str, path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{api_root.rstrip('/')}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError, urllib.error.HTTPError) as error:
        raise ReleaseStatusError("GitHub Actions run status is unavailable") from error
    if not isinstance(value, dict):
        raise ReleaseStatusError("GitHub Actions run status response is malformed")
    return value


def list_active_deployment_runs(
    repository: str,
    *,
    api_root: str,
    token: str,
) -> list[dict[str, Any]]:
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or not isinstance(token, str) or not token.strip()):
        raise ReleaseStatusError("GitHub Actions status request identity is unavailable")

    runs_by_id: dict[str, dict[str, Any]] = {}
    workflows = {f".github/workflows/{workflow}": workflow for workflow in CD_WORKFLOWS}
    for status in ACTIVE_STATUSES:
        page = 1
        while True:
            query = urllib.parse.urlencode({"per_page": "100", "page": str(page), "status": status})
            payload = _api_get(
                api_root,
                f"/repos/{repository}/actions/runs?{query}",
                token,
            )
            rows = payload.get("workflow_runs")
            if not isinstance(rows, list):
                raise ReleaseStatusError("GitHub Actions run list is malformed")
            for run in rows:
                if not isinstance(run, dict):
                    raise ReleaseStatusError("GitHub Actions run identity is malformed")
                path = run.get("path")
                if not isinstance(path, str) or not path:
                    raise ReleaseStatusError("GitHub Actions workflow path is unavailable")
                workflow = workflows.get(path)
                if workflow is None:
                    continue
                run_id = run.get("id")
                run_status = run.get("status")
                head_sha = run.get("head_sha")
                attempt = run.get("run_attempt")
                title = run.get("display_title") or run.get("name") or ""
                title_shas = SOURCE_SHA.findall(title) if isinstance(title, str) else []
                target_sha = title_shas[-1] if title_shas else head_sha
                if (not isinstance(run_id, (int, str)) or isinstance(run_id, bool)
                        or not str(run_id).isdigit() or int(run_id) < 1
                        or run_status not in ACTIVE_STATUSES
                        or not isinstance(head_sha, str) or not SOURCE_SHA.fullmatch(head_sha)
                        or not isinstance(target_sha, str) or not SOURCE_SHA.fullmatch(target_sha)
                        or type(attempt) is not int or attempt < 1):
                    raise ReleaseStatusError("GitHub Actions run identity is incomplete")
                key = str(run_id)
                item = {
                    "workflow": workflow,
                    "run_id": key,
                    "status": run_status,
                    "head_sha": head_sha,
                    "target_sha": target_sha,
                    "run_attempt": attempt,
                }
                previous = runs_by_id.get(key)
                if previous is not None and previous != item:
                    raise ReleaseStatusError("GitHub Actions returned conflicting run identities")
                runs_by_id[key] = item
            if len(rows) < 100:
                break
            page += 1

    return sorted(runs_by_id.values(), key=lambda item: (item["workflow"], int(item["run_id"])))
