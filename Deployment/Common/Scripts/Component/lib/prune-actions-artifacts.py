#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_API_ROOT = "https://api.github.com"


def fail(message: str) -> None:
    raise SystemExit(f"artifact prune failed: {message}")


def optional_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def github_request(
    api_root: str,
    method: str,
    path: str,
    token: str,
    *,
    ignore_not_found: bool = False,
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{api_root.rstrip('/')}{path}",
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        if ignore_not_found and exc.code == 404:
            return {}
        details = exc.read().decode("utf-8", errors="replace")
        fail(f"GitHub API returned HTTP {exc.code}: {details}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API request failed: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"GitHub API returned invalid JSON: {exc}")


def list_artifacts(api_root: str, repo: str, token: str, artifact_name: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "per_page": "100",
                "page": str(page),
                "name": artifact_name,
            }
        )
        payload = github_request(api_root, "GET", f"/repos/{repo}/actions/artifacts?{query}", token)
        page_artifacts = payload.get("artifacts")
        if not isinstance(page_artifacts, list):
            fail("unexpected artifacts response")

        artifacts.extend(
            artifact
            for artifact in page_artifacts
            if isinstance(artifact, dict) and artifact.get("name") == artifact_name
        )
        if len(page_artifacts) < 100:
            break
        page += 1

    return artifacts


def size_mib(artifact: dict[str, Any]) -> float:
    size = artifact.get("size_in_bytes")
    return round(float(size or 0) / 1024 / 1024, 1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prune old GitHub Actions artifacts with a matching name."
    )
    parser.add_argument("--artifact-name", required=True, help="Artifact name to prune.")
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of newest matching artifacts to keep.",
    )
    parser.add_argument(
        "--repo",
        default=optional_env("GITHUB_REPOSITORY"),
        help="GitHub repository in owner/name form. Defaults to GITHUB_REPOSITORY.",
    )
    parser.add_argument(
        "--token",
        default=optional_env("GITHUB_TOKEN", "GH_TOKEN"),
        help="GitHub token with Actions write permission. Defaults to GITHUB_TOKEN or GH_TOKEN.",
    )
    parser.add_argument(
        "--api-root",
        default=optional_env("GITHUB_API_URL") or DEFAULT_API_ROOT,
        help="GitHub API root URL.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print deletions without deleting.")
    args = parser.parse_args()

    repo_parts = args.repo.split("/")
    if len(repo_parts) != 2 or not all(repo_parts):
        fail("--repo must be in owner/name form or GITHUB_REPOSITORY must be set")
    artifact_name = args.artifact_name.strip()
    if not artifact_name:
        fail("--artifact-name must not be empty")
    if not args.token:
        fail("--token, GITHUB_TOKEN, or GH_TOKEN is required")
    if args.keep < 1:
        fail("--keep must be at least 1")

    artifacts = list_artifacts(args.api_root, args.repo, args.token, artifact_name)
    artifacts.sort(key=lambda artifact: str(artifact.get("created_at", "")), reverse=True)
    stale_artifacts = artifacts[args.keep :]

    print(
        "artifact prune: "
        f"name={artifact_name} found={len(artifacts)} "
        f"keep={args.keep} delete={len(stale_artifacts)} dry_run={args.dry_run}"
    )

    for artifact in stale_artifacts:
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, int):
            fail(f"artifact has invalid id: {artifact}")
        created_at = artifact.get("created_at", "")
        print(f"delete artifact id={artifact_id} created_at={created_at} size_mib={size_mib(artifact)}")
        if not args.dry_run:
            github_request(
                args.api_root,
                "DELETE",
                f"/repos/{args.repo}/actions/artifacts/{artifact_id}",
                args.token,
                ignore_not_found=True,
            )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(1)
