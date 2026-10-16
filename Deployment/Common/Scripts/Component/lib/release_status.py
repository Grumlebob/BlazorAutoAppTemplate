#!/usr/bin/env python3
"""Shared read-only release status validation for deployment runners."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
SOURCE_SHA = re.compile(r"[0-9a-f]{40}\Z")
POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*\Z")
PIN_KEY = re.compile(r"ghcr-[0-9a-f]{64}-[0-9a-f]{64}\Z")
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
    if transport == "actions-artifact" and pin_key:
        raise ReleaseStatusError("legacy release marker unexpectedly names a registry pin")

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


def pin_state(release: dict[str, Any] | None, protected_pins: set[str]) -> str:
    if release is None:
        return "no-release"
    key = release["release_payload_pin_key"]
    if key:
        if key not in protected_pins:
            raise ReleaseStatusError("release marker pin was not validated by local pin inspection")
        return "verified"
    if release["payload_transport"] == "actions-artifact":
        return "legacy-artifact-only"
    raise ReleaseStatusError("registry release has no durable local pin")


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
    for workflow in CD_WORKFLOWS:
        for status in ACTIVE_STATUSES:
            page = 1
            while True:
                query = urllib.parse.urlencode({"per_page": "100", "page": str(page), "status": status})
                payload = _api_get(
                    api_root,
                    f"/repos/{repository}/actions/workflows/{workflow}/runs?{query}",
                    token,
                )
                rows = payload.get("workflow_runs")
                if not isinstance(rows, list):
                    raise ReleaseStatusError("GitHub Actions run list is malformed")
                for run in rows:
                    if not isinstance(run, dict):
                        raise ReleaseStatusError("GitHub Actions run identity is malformed")
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
