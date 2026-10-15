#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_API_ROOT = "https://api.github.com"
ACTIVE_STATUSES = ("queued", "in_progress", "waiting", "requested", "pending")
COMMIT_SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")


def fail(message: str) -> None:
    raise SystemExit(f"artifact prune failed: {message}")


def optional_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def require_deploy_lock() -> None:
    lock_dir = optional_env("LOCALCLUSTER_DEPLOY_LOCK_DIR")
    lock_token = optional_env("LOCALCLUSTER_DEPLOY_LOCK_TOKEN")
    if not lock_dir or not lock_token:
        fail("the shared deployment lock is required for artifact selection and deletion")
    directory = Path(lock_dir)
    try:
        directory_info = directory.lstat()
        token_info = (directory / "token").lstat()
        current_token = (directory / "token").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        fail(f"cannot verify the shared deployment lock: {exc}")
    if (stat.S_ISLNK(directory_info.st_mode) or not stat.S_ISDIR(directory_info.st_mode)
            or stat.S_ISLNK(token_info.st_mode) or not stat.S_ISREG(token_info.st_mode)
            or current_token != lock_token):
        fail("shared deployment lock token is absent or changed")


def github_request(
    api_root: str,
    method: str,
    path: str,
    token: str,
    *,
    ignore_not_found: bool = False,
) -> dict[str, Any] | None:
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(1, 5):
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
                return None
            details = exc.read().decode("utf-8", errors="replace")
            if exc.code not in retryable_statuses or attempt == 4:
                fail(f"GitHub API returned HTTP {exc.code}: {details}")
            retry_after = exc.headers.get("Retry-After", "")
            try:
                delay = max(1, min(30, int(retry_after)))
            except ValueError:
                delay = min(30, attempt * 2)
            print(f"GitHub API returned retryable HTTP {exc.code}; retrying in {delay}s")
            time.sleep(delay)
        except urllib.error.URLError as exc:
            if attempt == 4:
                fail(f"GitHub API request failed: {exc}")
            delay = min(30, attempt * 2)
            print(f"GitHub API request failed transiently; retrying in {delay}s: {exc}")
            time.sleep(delay)
        except json.JSONDecodeError as exc:
            fail(f"GitHub API returned invalid JSON: {exc}")

    fail("GitHub API retry budget exhausted")


def list_artifacts(api_root: str, repo: str, token: str, artifact_name: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for page in range(1, 1001):
        query = urllib.parse.urlencode({"per_page": "100", "page": str(page), "name": artifact_name})
        payload = github_request(api_root, "GET", f"/repos/{repo}/actions/artifacts?{query}", token)
        if not isinstance(payload, dict) or not isinstance(payload.get("artifacts"), list):
            fail("unexpected artifacts response")
        page_artifacts = payload["artifacts"]
        artifacts.extend(item for item in page_artifacts if isinstance(item, dict) and item.get("name") == artifact_name)
        if len(page_artifacts) < 100:
            return artifacts
    fail("artifact pagination exceeded the 100,000-item safety limit")


def list_workflow_runs(
    api_root: str, repo: str, token: str, workflow_file: str, status: str,
    *, max_runs: int | None = None,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    workflow_path = urllib.parse.quote(workflow_file, safe="")
    page_size = min(100, max_runs) if max_runs is not None else 100
    for page in range(1, 1001):
        query = urllib.parse.urlencode({"per_page": str(page_size), "page": str(page), "status": status})
        payload = github_request(
            api_root, "GET", f"/repos/{repo}/actions/workflows/{workflow_path}/runs?{query}", token
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
            fail(f"unexpected workflow-run response for {workflow_file} ({status})")
        page_runs = payload["workflow_runs"]
        runs.extend(run for run in page_runs if isinstance(run, dict))
        if max_runs is not None and len(runs) >= max_runs:
            return runs[:max_runs]
        if len(page_runs) < 100:
            return runs
    fail(f"workflow pagination exceeded the 100,000-run safety limit for {workflow_file}")


def positive_id(value: object, description: str) -> int:
    if type(value) is not int or value < 1:
        fail(f"{description} is not a positive integer")
    return value


def list_active_producer_run_ids(
    api_root: str, repo: str, token: str, workflow_file: str
) -> set[int]:
    run_ids: set[int] = set()
    for status in ACTIVE_STATUSES:
        for run in list_workflow_runs(api_root, repo, token, workflow_file, status):
            run_ids.add(positive_id(run.get("id"), f"active producer run ID from {workflow_file}"))
    return run_ids


def list_deployment_shas(
    api_root: str, repo: str, token: str, workflow_files: list[str]
) -> set[str]:
    """Protect live deployment SHAs and the two newest successful targets per workflow."""
    shas: set[str] = set()
    for workflow_file in workflow_files:
        for status in ACTIVE_STATUSES:
            for run in list_workflow_runs(api_root, repo, token, workflow_file, status):
                title = str(run.get("display_title") or run.get("name") or "")
                title_shas = COMMIT_SHA_RE.findall(title)
                if title_shas:
                    shas.add(title_shas[-1])
                else:
                    fail("deployment run has no verifiable target SHA; refusing artifact deletion")
        recent_successes = list_workflow_runs(
            api_root, repo, token, workflow_file, "success", max_runs=100
        )
        successful_shas: list[str] = []
        for run in recent_successes:
            title = str(run.get("display_title") or run.get("name") or "")
            title_shas = COMMIT_SHA_RE.findall(title)
            if not title_shas:
                fail("successful deployment run has no verifiable target SHA; refusing artifact deletion")
            target_sha = title_shas[-1]
            if target_sha not in successful_shas:
                successful_shas.append(target_sha)
            if len(successful_shas) == 2:
                break
        if len(successful_shas) < 2 and len(recent_successes) == 100:
            fail("the 100 most recent successful deployments do not identify two unique target SHAs")
        shas.update(successful_shas)
    return shas


def artifact_identity(artifact: dict[str, Any]) -> tuple[int, str, str, int, int, str, str | None, bool]:
    artifact_id = positive_id(artifact.get("id"), "artifact ID")
    name = artifact.get("name")
    created_at = artifact.get("created_at")
    size = artifact.get("size_in_bytes")
    expired = artifact.get("expired", False)
    workflow_run = artifact.get("workflow_run")
    if not isinstance(name, str) or not name:
        fail(f"artifact {artifact_id} has no valid name")
    if not isinstance(created_at, str) or not created_at or len(created_at) > 80:
        fail(f"artifact {artifact_id} has no valid creation time")
    if type(size) is not int or size < 0:
        fail(f"artifact {artifact_id} has no valid size")
    if type(expired) is not bool:
        fail(f"artifact {artifact_id} has no valid expiration state")
    if not isinstance(workflow_run, dict):
        fail(f"artifact {artifact_id} has no workflow identity")
    run_id = positive_id(workflow_run.get("id"), f"artifact {artifact_id} workflow-run ID")
    head_sha = workflow_run.get("head_sha")
    if not isinstance(head_sha, str) or not COMMIT_SHA_RE.fullmatch(head_sha):
        fail(f"artifact {artifact_id} has no verifiable producer SHA")
    digest = artifact.get("digest")
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)):
        fail(f"artifact {artifact_id} has an invalid digest")
    return artifact_id, name, created_at, size, run_id, head_sha, digest, expired


def select_deletions(
    artifacts: list[dict[str, Any]],
    keep: int,
    protected_run_ids: set[int],
    active_producer_run_ids: set[int],
    active_deployment_shas: set[str],
    max_bytes: int,
    max_deletions: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """Return deletions, protected artifacts, protected bytes, and keep-floor bytes.

    The newest `keep` unprotected artifacts stay. Artifacts referenced by live
    producers, live deployments, or exact persisted release identities never
    enter the disposable set.
    """
    normalized: list[tuple[dict[str, Any], tuple[int, str, str, int, int, str, str | None, bool]]] = []
    seen_ids: set[int] = set()
    for artifact in artifacts:
        identity = artifact_identity(artifact)
        if identity[0] in seen_ids:
            fail(f"artifact list repeats ID {identity[0]}")
        seen_ids.add(identity[0])
        if identity[-1]:
            continue
        normalized.append((artifact, identity))

    protected: list[tuple[dict[str, Any], tuple[int, str, str, int, int, str, str | None, bool]]] = []
    unprotected: list[tuple[dict[str, Any], tuple[int, str, str, int, int, str, str | None, bool]]] = []
    all_protected_runs = protected_run_ids | active_producer_run_ids
    for item in normalized:
        _, _, _, _, run_id, head_sha, _, _ = item[1]
        if run_id in all_protected_runs or head_sha in active_deployment_shas:
            protected.append(item)
        else:
            unprotected.append(item)

    unprotected.sort(key=lambda item: item[1][2], reverse=True)
    protected_bytes = sum(item[1][3] for item in protected)
    keep_floor = unprotected[:keep]
    keep_floor_bytes = sum(item[1][3] for item in keep_floor)
    if protected_bytes > max_bytes:
        return [], [item[0] for item in protected], protected_bytes, keep_floor_bytes

    oldest_first = list(reversed(unprotected[keep:]))
    deletions = oldest_first[:max_deletions]
    return [item[0] for item in deletions], [item[0] for item in protected], protected_bytes, keep_floor_bytes


def same_artifact_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return artifact_identity(left) == artifact_identity(right)


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely prune old GitHub Actions artifacts with a matching name.")
    parser.add_argument("--artifact-name", required=True, help="Artifact name to prune.")
    parser.add_argument("--keep", type=int, default=2, help="Newest unprotected artifacts to retain.")
    parser.add_argument("--max-unprotected-bytes", type=int, default=536870912, help="512 MiB default candidate bound.")
    parser.add_argument("--max-deletions", type=int, default=100, help="Maximum exact artifacts handled per run.")
    parser.add_argument("--repo", default=optional_env("GITHUB_REPOSITORY"), help="owner/name; defaults to GITHUB_REPOSITORY.")
    parser.add_argument("--token", default=optional_env("GITHUB_TOKEN", "GH_TOKEN"), help="Actions write token.")
    parser.add_argument("--api-root", default=optional_env("GITHUB_API_URL") or DEFAULT_API_ROOT)
    parser.add_argument("--protect-run-id", type=int, action="append", default=[], help="Persisted accepted/recovery run ID.")
    parser.add_argument("--producer-workflow-file", default="ci.yml", help="Workflow producing the artifacts.")
    parser.add_argument(
        "--deployment-workflow-file",
        action="append",
        required=True,
        help="Workflow consuming the artifacts; repeat for every enabled target.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print selection without deleting.")
    args = parser.parse_args()

    require_deploy_lock()
    repo_parts = args.repo.split("/")
    if len(repo_parts) != 2 or not all(repo_parts):
        fail("--repo must be in owner/name form or GITHUB_REPOSITORY must be set")
    artifact_name = args.artifact_name.strip()
    if not artifact_name:
        fail("--artifact-name must not be empty")
    if not args.token:
        fail("--token, GITHUB_TOKEN, or GH_TOKEN is required")
    if args.keep < 1:
        fail("--keep must be at least one")
    if args.max_unprotected_bytes < 1:
        fail("--max-unprotected-bytes must be positive")
    if not 1 <= args.max_deletions <= 100:
        fail("--max-deletions must be between 1 and 100")
    if any(run_id < 1 for run_id in args.protect_run_id):
        fail("--protect-run-id must be a positive CI run ID")

    artifacts = list_artifacts(args.api_root, args.repo, args.token, artifact_name)
    active_producers = list_active_producer_run_ids(
        args.api_root, args.repo, args.token, args.producer_workflow_file
    )
    protected_deployments = list_deployment_shas(
        args.api_root, args.repo, args.token, args.deployment_workflow_file
    )
    deletions, protected, protected_bytes, keep_floor_bytes = select_deletions(
        artifacts,
        args.keep,
        set(args.protect_run_id),
        active_producers,
        protected_deployments,
        args.max_unprotected_bytes,
        args.max_deletions,
    )

    found_bytes = sum(artifact_identity(item)[3] for item in artifacts if not artifact_identity(item)[-1])
    print(
        "artifact prune: "
        f"name={artifact_name} found={len(artifacts)} bytes={found_bytes} "
        f"keep={args.keep} protected={len(protected)} protected_bytes={protected_bytes} "
        f"keep_floor_bytes={keep_floor_bytes} active_producers={len(active_producers)} "
        f"protected_deployments={len(protected_deployments)} delete={len(deletions)} dry_run={args.dry_run}"
    )
    if protected_bytes > args.max_unprotected_bytes:
        print("protected bytes exceed the 512 MiB bound; no artifact deletion was attempted")
        return 0
    for artifact in protected:
        identity = artifact_identity(artifact)
        print(f"keep protected artifact id={identity[0]} run_id={identity[4]} head_sha={identity[5]}")

    for artifact in deletions:
        identity = artifact_identity(artifact)
        artifact_id = identity[0]
        print(f"candidate artifact id={artifact_id} created_at={identity[2]} size_bytes={identity[3]}")
        if args.dry_run:
            continue
        require_deploy_lock()
        latest = github_request(
            args.api_root,
            "GET",
            f"/repos/{args.repo}/actions/artifacts/{artifact_id}",
            args.token,
            ignore_not_found=True,
        )
        if latest is None:
            fail(f"artifact {artifact_id} disappeared after selection; refusing to continue")
        if not isinstance(latest, dict) or not same_artifact_identity(artifact, latest):
            fail(f"artifact {artifact_id} identity changed after selection; refusing to delete")
        require_deploy_lock()
        github_request(
            args.api_root,
            "DELETE",
            f"/repos/{args.repo}/actions/artifacts/{artifact_id}",
            args.token,
            ignore_not_found=True,
        )
        receipt = github_request(
            args.api_root,
            "GET",
            f"/repos/{args.repo}/actions/artifacts/{artifact_id}",
            args.token,
            ignore_not_found=True,
        )
        if receipt is not None:
            fail(f"artifact {artifact_id} still exists after deletion; refusing to report success")
        print(f"deleted artifact id={artifact_id}; exact-ID GET verified 404")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(1)
