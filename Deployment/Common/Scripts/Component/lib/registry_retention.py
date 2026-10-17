"""Plan bounded payload retention from a complete, verified registry inventory.

Registry transport and coordination adapters must verify this input before
calling the planner. A plan is never deletion authority: apply must reserve and
recheck each immutable version under the deployment coordination boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Mapping


DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
PACKAGE = re.compile(r"ghcr\.io/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9._/-]*-release-payload\Z")
TERMINAL = frozenset({"completed"})
ACTIVE = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
FINAL_BYTES = 1_073_741_824
TRANSFER_BYTES = 2_147_483_648
FINAL_COUNT = 3
FINAL_AGE = timedelta(days=7)
TRANSFER_AGE = timedelta(hours=24)
MAX_DELETIONS = 100


class RetentionError(ValueError):
    """Protection or inventory is insufficient for safe retention."""


def normalize_repository(value: str) -> str:
    if not isinstance(value, str):
        raise RetentionError("registry repository identity is invalid")
    name = value.removeprefix("https://github.com/")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
        raise RetentionError("registry repository identity is invalid")
    return name.casefold()


@dataclass(frozen=True)
class Version:
    package: str
    version_id: int
    digest: str
    tags: frozenset[str]
    created: datetime
    # Direct manifest children and content-addressed config/layer sizes.
    children: frozenset[str]
    blobs: tuple[tuple[str, int], ...]
    manifest_bytes: int


@dataclass(frozen=True)
class Payload:
    package: str
    digest: str
    kind: str
    profile: str
    run_id: int
    run_attempt: int
    created: datetime
    commit_sha: str


@dataclass(frozen=True)
class Inventory:
    repository: str
    versions: tuple[Version, ...]
    payloads: tuple[Payload, ...]
    owned_packages: frozenset[str]
    complete: bool
    # Explicitly reviewed config-only bootstrap manifests are retained forever.
    # They are never presented as CI-produced payloads or deletion candidates.
    retained_manifests: frozenset[tuple[str, str]] = frozenset()


@dataclass(frozen=True)
class Protection:
    # References include package identity: identical digests in two packages
    # must not transfer ownership or protection between repositories.
    digests: frozenset[tuple[str, str]]
    tags: frozenset[tuple[str, str]]
    active_consumers: frozenset[tuple[int, int]]
    run_states: Mapping[tuple[int, int], str]
    complete: bool


@dataclass(frozen=True)
class RetentionPlan:
    delete: tuple[Version, ...]
    protected_bytes: int
    final_candidate_bytes: int
    transfer_candidate_bytes: int
    protected_final_bytes: int
    protected_transfer_bytes: int
    final_bytes_after: int
    transfer_bytes_after: int
    admission_blocked: bool
    deferred_groups: int


def _time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise RetentionError("registry timestamps must include a timezone")
    return value.astimezone(timezone.utc)


def _index(inventory: Inventory):
    if not inventory.complete or not inventory.repository or not inventory.owned_packages:
        raise RetentionError("complete repository-scoped registry inventory is required")
    owner = normalize_repository(inventory.repository).split("/")[0]
    if any(not PACKAGE.fullmatch(name) or ".." in name.split("/") for name in inventory.owned_packages):
        raise RetentionError("registry package is outside the configured payload namespace")
    if any(name.removeprefix("ghcr.io/").split("/")[0] != owner for name in inventory.owned_packages):
        raise RetentionError("registry package owner differs from the verified repository")
    versions: dict[tuple[str, str], Version] = {}
    ids: set[tuple[str, int]] = set()
    tag_owners: set[tuple[str, str]] = set()
    blob_sizes: dict[tuple[str, str], int] = {}
    for version in inventory.versions:
        key = version.package, version.digest
        identity = version.package, version.version_id
        if (version.package not in inventory.owned_packages or not DIGEST.fullmatch(version.digest)
                or type(version.version_id) is not int or version.version_id <= 0
                or type(version.manifest_bytes) is not int or version.manifest_bytes <= 0
                or key in versions or identity in ids):
            raise RetentionError("registry version ownership or immutable identity is invalid")
        _time(version.created)
        if len(version.blobs) != len({digest for digest, _ in version.blobs}):
            raise RetentionError("manifest contains a duplicate content descriptor")
        for digest, size in version.blobs:
            if not DIGEST.fullmatch(digest) or type(size) is not int or size < 0:
                raise RetentionError("registry content size or digest is invalid")
            blob_key = version.package, digest
            if blob_key in blob_sizes and blob_sizes[blob_key] != size:
                raise RetentionError("registry descriptors disagree about content size")
            blob_sizes[blob_key] = size
        for tag in version.tags:
            tag_key = version.package, tag
            if not tag or tag_key in tag_owners:
                raise RetentionError("registry tag ownership is ambiguous")
            tag_owners.add(tag_key)
        versions[key] = version
        ids.add(identity)

    closures: dict[tuple[str, str], frozenset[tuple[str, str]]] = {}

    def closure(key, visiting=frozenset()):
        if key in visiting or key not in versions:
            raise RetentionError("registry manifest graph is cyclic or incomplete")
        if key not in closures:
            found = {key}
            for child in versions[key].children:
                if not DIGEST.fullmatch(child):
                    raise RetentionError("registry child manifest digest is invalid")
                found.update(closure((key[0], child), visiting | {key}))
            closures[key] = frozenset(found)
        return closures[key]

    roots: dict[tuple[str, str], Payload] = {}
    covered: set[tuple[str, str]] = set()
    if (not isinstance(inventory.retained_manifests, frozenset) or len(inventory.retained_manifests) > 100
            or any(not isinstance(key, tuple) or len(key) != 2
                   or any(not isinstance(part, str) for part in key) for key in inventory.retained_manifests)):
        raise RetentionError("retained bootstrap identities are malformed")
    for payload in inventory.payloads:
        key = payload.package, payload.digest
        if (key not in versions or key in roots or payload.kind not in {"final", "staging", "harness"}
                or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", payload.profile)
                or type(payload.run_id) is not int or payload.run_id <= 0
                or type(payload.run_attempt) is not int or payload.run_attempt <= 0
                or not re.fullmatch(r"[0-9a-f]{40}", payload.commit_sha)):
            raise RetentionError("registry payload ownership or producer identity is invalid")
        _time(payload.created)
        if _time(payload.created) != _time(versions[key].created):
            raise RetentionError("payload timestamp differs from its immutable registry version")
        roots[key] = payload
        covered.update(closure(key))
    for key in inventory.retained_manifests:
        if key not in versions or key in covered:
            raise RetentionError("retained bootstrap identity is missing or overlaps a CI payload")
        version = versions[key]
        if (version.children or len(version.blobs) != 1
                or version.manifest_bytes + sum(size for _, size in version.blobs) > 65536):
            raise RetentionError("retained bootstrap must be a bounded config-only manifest")
        covered.add(key)
    if set(versions) != covered:
        raise RetentionError("unclassified registry versions prevent retention and publication admission")
    # A graph member cannot also masquerade as an independent payload root.
    for key in roots:
        if any(key in closures[other] for other in roots if other != key):
            raise RetentionError("registry payload roots overlap their manifest descendants")
    return versions, roots, closures


def inventory_record(inventory: Inventory) -> dict:
    """Freeze verified metadata inside an existing lock owner's journal."""
    _index(inventory)
    return {
        "repository": inventory.repository, "complete": True, "owned_packages": sorted(inventory.owned_packages),
        "retained_manifests": [list(key) for key in sorted(inventory.retained_manifests)],
        "versions": [{
            "package": item.package, "version_id": item.version_id, "digest": item.digest,
            "tags": sorted(item.tags), "created": item.created.isoformat(), "children": sorted(item.children),
            "blobs": [[digest, size] for digest, size in item.blobs], "manifest_bytes": item.manifest_bytes,
        } for item in inventory.versions],
        "payloads": [{
            "package": item.package, "digest": item.digest, "kind": item.kind, "profile": item.profile,
            "run_id": item.run_id, "run_attempt": item.run_attempt, "created": item.created.isoformat(),
            "commit_sha": item.commit_sha,
        } for item in inventory.payloads],
    }


def inventory_from_record(value: Any) -> Inventory:
    fields = {"repository", "complete", "owned_packages", "versions", "payloads"}
    if (not isinstance(value, dict) or set(value) not in (fields, fields | {"retained_manifests"})
            or value["complete"] is not True or not isinstance(value["owned_packages"], list)
            or not isinstance(value["versions"], list) or len(value["versions"]) > 10000
            or not isinstance(value["payloads"], list) or len(value["payloads"]) > 10000):
        raise RetentionError("frozen registry inventory schema is invalid")
    try:
        versions = []
        for item in value["versions"]:
            if not isinstance(item, dict) or set(item) != {"package", "version_id", "digest", "tags", "created", "children", "blobs", "manifest_bytes"}:
                raise RetentionError("frozen registry version schema is invalid")
            if (not isinstance(item["tags"], list) or len(item["tags"]) != len(set(item["tags"]))
                    or not isinstance(item["children"], list) or len(item["children"]) != len(set(item["children"]))
                    or not isinstance(item["blobs"], list)):
                raise RetentionError("frozen registry version descriptors are invalid")
            versions.append(Version(item["package"], item["version_id"], item["digest"], frozenset(item["tags"]),
                                    datetime.fromisoformat(item["created"]), frozenset(item["children"]),
                                    tuple(tuple(blob) for blob in item["blobs"]), item["manifest_bytes"]))
        payloads = []
        for item in value["payloads"]:
            if not isinstance(item, dict) or set(item) != {"package", "digest", "kind", "profile", "run_id", "run_attempt", "created", "commit_sha"}:
                raise RetentionError("frozen registry payload schema is invalid")
            payloads.append(Payload(item["package"], item["digest"], item["kind"], item["profile"], item["run_id"],
                                    item["run_attempt"], datetime.fromisoformat(item["created"]), item["commit_sha"]))
        retained = value.get("retained_manifests", [])
        if (not isinstance(retained, list) or len(retained) > 100
                or any(not isinstance(key, list) or len(key) != 2
                       or any(not isinstance(part, str) for part in key) for key in retained)
                or len(retained) != len({tuple(key) for key in retained})):
            raise RetentionError("frozen retained bootstrap references are invalid")
        result = Inventory(value["repository"], tuple(versions), tuple(payloads), frozenset(value["owned_packages"]), True,
                           frozenset(tuple(key) for key in retained))
        _index(result)
    except (KeyError, TypeError, ValueError) as error:
        raise RetentionError("frozen registry inventory is malformed or incomplete") from error
    return result


def inventory_usage(inventory: Inventory) -> dict[str, int]:
    """Measure stored content without classifying any release as disposable."""
    versions, roots, closures = _index(inventory)

    def size(selected):
        content = {}
        for key in selected:
            version = versions[key]
            content[key] = version.manifest_bytes
            for digest, length in version.blobs:
                content[version.package, digest] = length
        return sum(content.values())

    groups = {}
    for kind in ("final", "staging", "harness"):
        selected = set()
        for key, payload in roots.items():
            if payload.kind == kind:
                selected.update(closures[key])
        groups[kind + "_bytes"] = size(selected)
    groups["total_bytes"] = size(set(versions))
    groups["retained_manifest_bytes"] = size(set(inventory.retained_manifests))
    return groups


def plan_retention(
    inventory: Inventory,
    protection: Protection,
    *,
    now: datetime,
    max_deletions: int = MAX_DELETIONS,
) -> RetentionPlan:
    """Keep exact references and active inputs; bound only disposable payloads."""
    now = _time(now)
    if not protection.complete:
        raise RetentionError("complete accepted, recovery and pending protection is required")
    if type(max_deletions) is not int or not 1 <= max_deletions <= MAX_DELETIONS:
        raise RetentionError("registry deletion batches must contain at most 100 versions")
    versions, roots, closures = _index(inventory)
    protected = set(protection.digests) | set(inventory.retained_manifests)
    if not protected.issubset(versions):
        raise RetentionError("a protected registry reference is missing from the inventory")
    for package, tag in protection.tags:
        owners = [key for key, value in versions.items() if key[0] == package and tag in value.tags]
        if len(owners) != 1:
            raise RetentionError("a protected registry tag is missing or ambiguous")
        protected.add(owners[0])
    for key, payload in roots.items():
        identity = payload.run_id, payload.run_attempt
        state = protection.run_states.get(identity)
        if state not in TERMINAL | ACTIVE:
            raise RetentionError("a payload producer/consumer state is unavailable")
        if state in ACTIVE or identity in protection.active_consumers:
            protected.add(key)
        if _time(payload.created) > now or _time(versions[key].created) > now:
            raise RetentionError("registry creation timestamp is in the future")
    protected = set().union(*(closures.get(key) or {key} for key in protected)) if protected else set()
    # Expand descendants even when protection names a child directly.
    for key in tuple(protected):
        protected.update(closures.get(key) or {key})
    for key in roots:
        if closures[key] & protected:
            protected.update(closures[key])

    def members(keys):
        return set().union(*(closures[key] for key in keys)) if keys else set()

    def size(keys):
        content: dict[tuple[str, str], int] = {}
        for key in keys:
            version = versions[key]
            content[key] = version.manifest_bytes
            for digest, length in version.blobs:
                blob_key = version.package, digest
                if blob_key in content and content[blob_key] != length:
                    raise RetentionError("manifest and content descriptors disagree about size")
                content[blob_key] = length
        return sum(content.values())

    disposable_roots = {key for key in roots if not (closures[key] & protected)}
    final = {key for key in disposable_roots if roots[key].kind == "final"}
    transfer = disposable_roots - final
    final_bytes = size(members(final) - protected)
    transfer_bytes = size(members(transfer) - protected)
    protected_final = members({key for key in roots if key not in disposable_roots and roots[key].kind == "final"})
    protected_transfer = members({key for key in roots if key not in disposable_roots and roots[key].kind != "final"})
    protected_final_bytes = size(protected_final)
    protected_transfer_bytes = size(protected_transfer)
    protected_over_cap = protected_final_bytes > FINAL_BYTES or protected_transfer_bytes > TRANSFER_BYTES
    keep_final: set[tuple[str, str]] = set()
    for profile in {roots[key].profile for key in final}:
        recent = [key for key in final if roots[key].profile == profile and now - _time(roots[key].created) <= FINAL_AGE]
        recent.sort(key=lambda key: (_time(roots[key].created), key), reverse=True)
        keep_final.update(recent[:FINAL_COUNT])
    while keep_final and size(members(keep_final) - protected) > FINAL_BYTES:
        keep_final.remove(min(keep_final, key=lambda key: (_time(roots[key].created), key)))
    keep_transfer = {key for key in transfer if now - _time(roots[key].created) < TRANSFER_AGE}
    eligible = disposable_roots - keep_final - keep_transfer
    eligible_order = sorted(eligible, key=lambda key: (_time(roots[key].created), key))
    selected_roots: set[tuple[str, str]] = set()
    deferred = 0
    selected: set[tuple[str, str]] = set()
    for key in eligible_order:
        if protected_over_cap:
            deferred += 1
            continue
        trial_roots = selected_roots | {key}
        retained = members(set(roots) - trial_roots) | protected
        trial = members(trial_roots) - retained
        if len(trial) > max_deletions:
            deferred += 1
            continue
        selected_roots = trial_roots
        selected = trial
    retained_final = final - selected_roots
    retained_transfer = transfer - selected_roots
    final_after = size(members(retained_final) - protected)
    transfer_after = size(members(retained_transfer) - protected)
    # Parents are deleted before their manifests. Shared descendants remain
    # while any retained root, protected reference or tag still uses them.
    depth = {key: len(closures.get(key) or {key}) for key in selected}
    deletion_order = sorted(selected, key=lambda key: (-depth[key], key))
    protected_bytes = size(protected)
    return RetentionPlan(
        tuple(versions[key] for key in deletion_order), protected_bytes,
        final_bytes, transfer_bytes, protected_final_bytes, protected_transfer_bytes,
        final_after, transfer_after,
        final_after > FINAL_BYTES or transfer_after > TRANSFER_BYTES
        or protected_over_cap,
        deferred,
    )


def require_publication_capacity(plan: RetentionPlan, *, kind: str, reserved_bytes: int) -> None:
    """Fail admission rather than evict protected or active payloads."""
    if kind not in {"final", "staging", "harness"} or type(reserved_bytes) is not int or reserved_bytes <= 0:
        raise RetentionError("publication kind and reserved size must be valid")
    if plan.admission_blocked:
        raise RetentionError("payload store requires coordinated retention before publication")
    limit, used = (FINAL_BYTES, plan.protected_final_bytes + plan.final_candidate_bytes) if kind == "final" else (
        TRANSFER_BYTES, plan.protected_transfer_bytes + plan.transfer_candidate_bytes,
    )
    # Planned deletion does not free capacity until exact remote absence is
    # reconciled and a new inventory is obtained under the same coordination.
    if used + reserved_bytes > limit:
        raise RetentionError("payload publication would exceed its repository byte cap")
