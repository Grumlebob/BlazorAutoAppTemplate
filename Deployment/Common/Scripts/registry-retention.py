#!/usr/bin/env python3
"""Apply bounded GHCR payload retention through the shared deployment lock."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import uuid


LIB = Path(__file__).resolve().parent / "Component/lib"
sys.path.insert(0, str(LIB))

import registry_gc  # noqa: E402
import shared_deploy_lock  # noqa: E402
from registry_inventory import RegistryClient, collect_inventory  # noqa: E402
from registry_lock_guard import JOURNAL, SharedLockGuard  # noqa: E402
from registry_retention import (  # noqa: E402
    ACTIVE,
    DIGEST,
    FINAL_BYTES,
    MAX_DELETIONS,
    PACKAGE,
    TRANSFER_BYTES,
    Protection,
    RetentionError,
    Version,
    inventory_usage,
    plan_retention,
    require_publication_capacity,
)
from release_status import list_active_deployment_runs  # noqa: E402


SHA = re.compile(r"[0-9a-f]{40}\Z")
POSITIVE = re.compile(r"[1-9][0-9]{0,19}\Z")
REQUIRED_PROTECTIONS = {("localcluster", "cluster"), ("localsinglenode", "primary")}


def _parse_packages(values: list[str]) -> dict[str, str]:
    packages: dict[str, str] = {}
    for value in values:
        if value.count("=") != 1:
            raise RetentionError("configured payload package requires an exact image and expected visibility")
        image, visibility = value.split("=", 1)
        if (image in packages or not PACKAGE.fullmatch(image)
                or visibility not in {"private", "public", "internal"}):
            raise RetentionError("configured registry package or visibility is invalid")
        packages[image] = visibility
    if not packages:
        raise RetentionError("at least one configured payload package is required")
    return packages


def _parse_protections(values: list[str], *, require_additional: bool) -> tuple[dict, ...]:
    required = REQUIRED_PROTECTIONS | ({("localsinglenode", "additional")} if require_additional else set())
    parsed = []
    seen = set()
    for raw in values:
        try:
            item = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise RetentionError("release protection snapshot is malformed") from error
        if (not isinstance(item, dict)
                or set(item) != {"schema_version", "target", "instance", "complete", "consumers", "registry_payload_references"}
                or type(item.get("schema_version")) is not int or item.get("schema_version") != 1
                or item.get("complete") is not True
                or item.get("target") not in {"localcluster", "localsinglenode"}
                or item.get("instance") not in {"cluster", "primary", "additional"}):
            raise RetentionError("release protection snapshot is incomplete")
        identity = item["target"], item["instance"]
        if identity in seen or identity not in REQUIRED_PROTECTIONS | {("localsinglenode", "additional")}:
            raise RetentionError("release protection snapshots are duplicated or out of scope")
        seen.add(identity)
        if not isinstance(item["consumers"], list) or len(item["consumers"]) > 4:
            raise RetentionError("release consumer references are malformed")
        for consumer in item["consumers"]:
            if (not isinstance(consumer, dict) or set(consumer) != {"run_id", "run_attempt", "target_sha"}
                    or type(consumer.get("run_id")) is not int or consumer["run_id"] <= 0
                    or type(consumer.get("run_attempt")) is not int or consumer["run_attempt"] <= 0
                    or not isinstance(consumer.get("target_sha"), str) or not SHA.fullmatch(consumer["target_sha"])):
                raise RetentionError("release consumer identity is malformed")
        if not isinstance(item["registry_payload_references"], list) or len(item["registry_payload_references"]) > 2:
            raise RetentionError("verified registry release references are malformed")
        for reference in item["registry_payload_references"]:
            if (not isinstance(reference, dict)
                    or set(reference) != {"package", "digest", "run_id", "run_attempt", "source_sha"}
                    or not isinstance(reference.get("package"), str) or not PACKAGE.fullmatch(reference["package"])
                    or not isinstance(reference.get("digest"), str) or not DIGEST.fullmatch(reference["digest"])
                    or type(reference.get("run_id")) is not int or reference["run_id"] <= 0
                    or type(reference.get("run_attempt")) is not int or reference["run_attempt"] <= 0
                    or not isinstance(reference.get("source_sha"), str) or not SHA.fullmatch(reference["source_sha"])):
                raise RetentionError("immutable release payload reference is malformed")
            matching_consumers = [consumer for consumer in item["consumers"]
                                  if consumer["run_id"] == reference["run_id"]
                                  and consumer["run_attempt"] == reference["run_attempt"]]
            if not matching_consumers or any(consumer["target_sha"] != reference["source_sha"]
                                             for consumer in matching_consumers):
                raise RetentionError("registry payload reference differs from its current/recovery marker")
        parsed.append(item)
    if not required.issubset(seen) or ("localsinglenode", "additional") in seen and not require_additional:
        raise RetentionError("current/recovery protection is missing for an enabled deployment instance")
    return tuple(parsed)


def _protection(
    snapshots: tuple[dict, ...],
    states: dict[tuple[int, int], str],
    inventory,
    *,
    repository: str,
    token: str,
    active_runs_provider=list_active_deployment_runs,
) -> Protection:
    digests = set()
    active_consumers = set()
    for snapshot in snapshots:
        for consumer in snapshot["consumers"]:
            active_consumers.add((consumer["run_id"], consumer["run_attempt"]))
        for reference in snapshot["registry_payload_references"]:
            digests.add((reference["package"], reference["digest"]))
    active_runs = active_runs_provider(
        repository,
        api_root=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        token=token,
    )
    active_targets = {item["target_sha"] for item in active_runs}
    for payload in inventory.payloads:
        if payload.kind == "final" and payload.commit_sha in active_targets:
            active_consumers.add((payload.run_id, payload.run_attempt))
    unmatched_targets = {
        target for target in active_targets
        if not any(payload.kind == "final" and payload.commit_sha == target for payload in inventory.payloads)
    }
    if unmatched_targets:
        raise RetentionError("an active deployment target has no verified final payload in the complete inventory")
    active_consumers.update(
        (payload.run_id, payload.run_attempt)
        for payload in inventory.payloads
        if states.get((payload.run_id, payload.run_attempt)) in ACTIVE
    )
    return Protection(frozenset(digests), frozenset(), frozenset(active_consumers), states, True)


def _all_roots_protected(inventory, states: dict[tuple[int, int], str]) -> Protection:
    """Admission is conservative: no unexecuted deletion plan frees capacity."""
    return Protection(
        frozenset((payload.package, payload.digest) for payload in inventory.payloads),
        frozenset(), frozenset(), states, True,
    )


def _validate_workflow_scope(*, mode: str) -> None:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    ref = os.environ.get("GITHUB_REF", "")
    workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF", "")
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    if not repository or ref != "refs/heads/main" or event not in {"push", "workflow_dispatch", "schedule"}:
        raise RetentionError("registry maintenance is restricted to trusted main workflows")
    expected_file = "registry-retention.yml" if mode == "apply" else "ci.yml"
    if not workflow_ref.endswith(f".github/workflows/{expected_file}@refs/heads/main"):
        raise RetentionError("registry operation is running outside its reviewed main workflow")
    if mode == "apply" and os.environ.get("REGISTRY_COORDINATION_SCOPE_COMPLETE") != "true":
        raise RetentionError("the complete deployment coordination scope was not verified")


def _reservation_id() -> str:
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if POSITIVE.fullmatch(run_id) and POSITIVE.fullmatch(attempt):
        return f"run-{run_id}-{attempt}"
    return "manual-" + uuid.uuid4().hex


def _result(plan, inventory, *, outcome: str, receipts: tuple[dict, ...], admission: dict | None) -> dict:
    return {
        "schema_version": 2,
        "outcome": outcome,
        "repository": inventory.repository,
        "versions_scanned": len(inventory.versions),
        "payload_roots": len(inventory.payloads),
        "candidate_versions": len(plan.delete),
        "preview_candidates": [
            {
                "package": item.package,
                "version_id": item.version_id,
                "digest": item.digest,
                "tags": sorted(item.tags),
                "created": item.created.isoformat(),
            }
            for item in plan.delete
        ] if outcome == "preview" else None,
        "verified_absent_versions": len(receipts),
        "receipts": list(receipts),
        "usage": inventory_usage(inventory),
        "limits": {"final_bytes": FINAL_BYTES, "transfer_bytes": TRANSFER_BYTES, "delete_batch": MAX_DELETIONS},
        "admission_blocked": plan.admission_blocked,
        "deferred_groups": plan.deferred_groups,
        "admission": admission,
        "mutation": "exact-version-delete-only-if-present" if receipts else "none",
    }


def run(args: argparse.Namespace, *, client_factory=RegistryClient, guard_factory=SharedLockGuard,
        active_runs_provider=list_active_deployment_runs) -> dict:
    if args.assert_clear:
        lock_dir, _ = shared_deploy_lock.require_shared_lock(RetentionError)
        journal = lock_dir / JOURNAL
        if journal.exists() or journal.is_symlink():
            raise RetentionError("an unresolved GHCR deletion reservation blocks payload selection")
        return {"outcome": "clear", "pending_reservation": False, "mutation": "none"}

    packages = _parse_packages(args.package)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
    if not args.repository or not args.username or not token:
        raise RetentionError("repository, actor and existing workflow token are required")
    lock_dir, _ = shared_deploy_lock.require_shared_lock(RetentionError)
    journal = lock_dir / JOURNAL
    if not args.apply and (journal.exists() or journal.is_symlink()):
        raise RetentionError("an unresolved GHCR deletion reservation blocks registry inspection")

    if args.admission_kind and not args.apply:
        _validate_workflow_scope(mode="admission")
    elif args.apply:
        _validate_workflow_scope(mode="apply")

    retained = set()
    for value in args.retain_manifest:
        if value.count("@") != 1:
            raise RetentionError("retained bootstrap requires one exact package and manifest digest")
        package, digest = value.split("@", 1)
        if package not in packages or not DIGEST.fullmatch(digest) or (package, digest) in retained:
            raise RetentionError("retained bootstrap reference is invalid or duplicated")
        retained.add((package, digest))

    client = client_factory(args.username, token)
    inventory, states = collect_inventory(
        args.repository, packages, client, retained_manifests=frozenset(retained),
    )
    admission = None
    if args.admission_kind:
        if args.reserved_bytes is None:
            raise RetentionError("publication capacity requires a positive reserved byte count")
        admission = {"kind": args.admission_kind, "reserved_bytes": args.reserved_bytes}

    if not args.apply and args.admission_kind:
        capacity_plan = plan_retention(
            inventory, _all_roots_protected(inventory, states), now=datetime.now(timezone.utc),
        )
        require_publication_capacity(capacity_plan, **admission)
        return _result(capacity_plan, inventory, outcome="admitted", receipts=(), admission=admission)

    snapshots = _parse_protections(args.protection_json, require_additional=args.require_additional)
    if args.apply:
        guard = guard_factory(
            repository=args.repository,
            reservation_id=args.reservation_id or _reservation_id(),
            inventory=inventory,
            refresh_protection=lambda: _protection(
                snapshots, states, inventory, repository=args.repository, token=token,
                active_runs_provider=active_runs_provider,
            ),
            controller_scope_complete=True,
        )
    else:
        guard = None

    protection = _protection(
        snapshots, states, inventory, repository=args.repository, token=token,
        active_runs_provider=active_runs_provider,
    )
    plan = plan_retention(inventory, protection, now=datetime.now(timezone.utc), max_deletions=args.max_deletions)
    if not args.apply:
        if admission is not None:
            require_publication_capacity(
                plan_retention(inventory, _all_roots_protected(inventory, states), now=datetime.now(timezone.utc)),
                **admission,
            )
        return _result(plan, inventory, outcome="preview", receipts=(), admission=admission)

    receipts: tuple[dict, ...] = ()
    if plan.delete:
        receipts = registry_gc.apply_deletions(plan.delete, registry=client, guard=guard)
        fresh_inventory, fresh_states = collect_inventory(
            args.repository, packages, client, retained_manifests=frozenset(retained),
        )
        deleted = {(item["package"], item["digest"]) for item in receipts}
        if any((item.package, item.digest) in deleted for item in fresh_inventory.versions):
            raise RetentionError("an exact-404 registry version remains in fresh inventory")
        inventory, states = fresh_inventory, fresh_states
        protection = _protection(
            snapshots, states, inventory, repository=args.repository, token=token,
            active_runs_provider=active_runs_provider,
        )
        plan = plan_retention(inventory, protection, now=datetime.now(timezone.utc), max_deletions=args.max_deletions)
    if admission is not None:
        capacity_plan = plan_retention(
            inventory, _all_roots_protected(inventory, states), now=datetime.now(timezone.utc),
        )
        require_publication_capacity(capacity_plan, **admission)
    return _result(plan, inventory, outcome="applied" if receipts else "no_changes", receipts=receipts, admission=admission)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--username", default=os.environ.get("GITHUB_ACTOR", ""))
    parser.add_argument("--package", action="append", default=[],
                        help="Exact configured payload image and expected visibility: ghcr.io/owner/app-release-payload=private")
    parser.add_argument("--retain-manifest", action="append", default=[],
                        help="Preserve an exact reviewed config-only bootstrap: ghcr.io/owner/app-release-payload@sha256:...")
    parser.add_argument("--protection-json", action="append", default=[],
                        help="A compact verified current/recovery snapshot from one enabled target instance")
    parser.add_argument("--require-additional", action="store_true")
    parser.add_argument("--reservation-id", default="")
    parser.add_argument("--max-deletions", type=int, default=MAX_DELETIONS)
    parser.add_argument("--admission-kind", choices=("final", "staging", "harness"))
    parser.add_argument("--reserved-bytes", type=int)
    parser.add_argument("--assert-clear", action="store_true", help="Fail if a prior exact deletion reservation remains pending.")
    parser.add_argument("--apply", action="store_true", help="Apply bounded exact-version cleanup and re-inventory afterward.")
    args = parser.parse_args(argv)
    if args.assert_clear and (args.apply or args.admission_kind):
        print("Reservation check cannot be combined with mutation or admission.", file=sys.stderr)
        return 2
    if not 1 <= args.max_deletions <= MAX_DELETIONS:
        print("Registry deletion batch must contain between 1 and 100 versions.", file=sys.stderr)
        return 2
    if args.reserved_bytes is not None and args.reserved_bytes <= 0:
        print("Publication reserved bytes must be positive.", file=sys.stderr)
        return 2
    if args.admission_kind and args.reserved_bytes is None:
        print("Publication capacity requires a positive reserved byte count.", file=sys.stderr)
        return 2
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, RetentionError) as error:
        print(f"Registry retention failed closed; no unverified deletion was attempted: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
