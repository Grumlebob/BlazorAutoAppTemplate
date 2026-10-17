"""Registry reservations inside the existing shared deployment lock.

An unfinished journal deliberately prevents the existing lock owner from
releasing its lock. Recovery must resume this exact owned reservation, after
verifying its process/run owner; this module never takes over or removes a lock.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable
import uuid

from pin_release_payload import _require_shared_lock
from registry_retention import (
    DIGEST, PACKAGE, Inventory, Protection, RetentionError, Version,
    inventory_from_record, inventory_record, normalize_repository, plan_retention,
)


JOURNAL = "registry-retention.json"
MAX_JOURNAL_BYTES = 1024 * 1024


def identity(version: Version) -> dict:
    return {"package": version.package, "version_id": version.version_id, "digest": version.digest,
            "tags": sorted(version.tags), "created": version.created.isoformat()}


def key(version: Version) -> str:
    return f"{version.package}|{version.version_id}"


def _read(path: Path) -> dict:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_size > MAX_JOURNAL_BYTES or info.st_mode & 0o022):
            raise RetentionError("registry reservation journal is unsafe")
        def unique(pairs):
            result = {}
            for name, item in pairs:
                if name in result:
                    raise RetentionError("registry reservation journal has duplicate keys")
                result[name] = item
            return result

        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RetentionError("registry reservation journal is unreadable") from error
    if (not isinstance(value, dict) or set(value) != {"schema_version", "repository", "reservation_id", "fingerprint", "candidates", "inventory", "order"}
            or value["schema_version"] != 1 or type(value["schema_version"]) is not int
            or not isinstance(value["repository"], str) or not value["repository"]
            or not isinstance(value["reservation_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value["reservation_id"])
            or not isinstance(value["fingerprint"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["fingerprint"])
            or not isinstance(value["candidates"], dict) or not 1 <= len(value["candidates"]) <= 100):
        raise RetentionError("registry reservation journal schema is invalid")
    if normalize_repository(value["repository"]) != value["repository"]:
        raise RetentionError("registry reservation repository is not canonical")
    for name, candidate in value["candidates"].items():
        if (not isinstance(candidate, dict) or set(candidate) != {"identity", "state", "api_status"}
                or candidate["state"] not in {"reserved", "delete_requested", "absent"}
                or (candidate["state"] == "absent" and (type(candidate["api_status"]) is not int or candidate["api_status"] != 404))
                or (candidate["state"] != "absent" and candidate["api_status"] is not None)):
            raise RetentionError("registry reservation lifecycle is invalid")
        item = candidate["identity"]
        if (not isinstance(item, dict) or set(item) != {"package", "version_id", "digest", "tags", "created"}
                or not isinstance(item["package"], str) or not PACKAGE.fullmatch(item["package"])
                or type(item["version_id"]) is not int or item["version_id"] <= 0
                or not isinstance(item["digest"], str) or not DIGEST.fullmatch(item["digest"])
                or not isinstance(item["tags"], list) or any(not isinstance(tag, str) or not tag for tag in item["tags"])
                or len(item["tags"]) != len(set(item["tags"]))
                or name != f"{item['package']}|{item['version_id']}"):
            raise RetentionError("registry reservation immutable identity is malformed")
        try:
            created = datetime.fromisoformat(item["created"])
            if created.tzinfo is None or created.utcoffset() is None:
                raise ValueError("missing timezone")
        except (TypeError, ValueError) as error:
            raise RetentionError("registry reservation creation timestamp is invalid") from error
    if (not isinstance(value["order"], list) or len(value["order"]) != len(set(value["order"]))
            or set(value["order"]) != set(value["candidates"])):
        raise RetentionError("registry reservation immutable deletion order is invalid")
    frozen = inventory_from_record(value["inventory"])
    if normalize_repository(frozen.repository) != value["repository"]:
        raise RetentionError("registry reservation inventory belongs to another repository")
    fingerprint = hashlib.sha256(json.dumps(
        {"identities": [item["identity"] for _, item in sorted(value["candidates"].items())],
         "inventory": value["inventory"], "order": value["order"]},
        sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    if value["fingerprint"] != fingerprint:
        raise RetentionError("registry reservation immutable identities changed")
    return value


def _sync_directory(path: Path) -> None:
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _save(path: Path, value: dict, *, create=False) -> None:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_JOURNAL_BYTES:
        raise RetentionError("registry reservation exceeds its journal byte bound")
    temporary = path if create else path.with_name("registry-retention-" + uuid.uuid4().hex + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        if not create:
            os.replace(temporary, path)
        _sync_directory(path.parent)
    except OSError as error:
        # Leave uncertain files for the existing lock owner's recovery path.
        raise RetentionError("could not persist the exact registry reservation") from error


class SharedLockGuard:
    def __init__(
        self,
        *,
        repository: str,
        reservation_id: str,
        inventory: Inventory | None,
        refresh_protection: Callable[[], Protection],
        controller_scope_complete: bool,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        if controller_scope_complete is not True:
            raise RetentionError("all consumers must share this verified deployment coordination boundary")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", reservation_id):
            raise RetentionError("registry reservation operation identity is invalid")
        self.repository = normalize_repository(repository)
        self.reservation_id = reservation_id
        self.refresh_protection = refresh_protection
        self.now = now
        self.lock_dir, self.token = _require_shared_lock()
        self.path = self.lock_dir / JOURNAL
        if inventory is None:
            journal = self._owned(reservation_id)
            inventory = inventory_from_record(journal["inventory"])
        if self.repository != normalize_repository(inventory.repository):
            raise RetentionError("registry reservation repository differs from its inventory")
        self.inventory = inventory

    def _lock(self) -> None:
        directory, token = _require_shared_lock()
        if directory != self.lock_dir or token != self.token:
            raise RetentionError("registry reservation lost its shared deployment lock")

    def _owned(self, reservation_id: str) -> dict:
        self._lock()
        value = _read(self.path)
        if (value["repository"] != self.repository or value["reservation_id"] != reservation_id
                or reservation_id != self.reservation_id):
            raise RetentionError("registry reservation belongs to another operation")
        return value

    def _eligible(self) -> set[str]:
        self._lock()
        current = plan_retention(self.inventory, self.refresh_protection(), now=self.now())
        return {key(item) for item in current.delete}

    def reserve(self, candidates: tuple[Version, ...]) -> str:
        self._lock()
        if not 1 <= len(candidates) <= 100 or len({key(item) for item in candidates}) != len(candidates):
            raise RetentionError("registry reservation requires a bounded unique candidate batch")
        if not {key(item) for item in candidates}.issubset(self._eligible()):
            raise RetentionError("registry candidate became protected or is outside the current retention plan")
        identities = {key(item): identity(item) for item in candidates}
        if self.path.exists() or self.path.is_symlink():
            value = self._owned(self.reservation_id)
            if {name: item["identity"] for name, item in value["candidates"].items()} != identities:
                raise RetentionError("resume must keep the original exact registry deletion batch")
        else:
            ordered = [item for _, item in sorted(identities.items())]
            snapshot = inventory_record(self.inventory)
            order = [key(item) for item in candidates]
            fingerprint = hashlib.sha256(json.dumps(
                {"identities": ordered, "inventory": snapshot, "order": order},
                sort_keys=True, separators=(",", ":"),
            ).encode()).hexdigest()
            _save(self.path, {"schema_version": 1, "repository": self.repository, "reservation_id": self.reservation_id,
                              "fingerprint": fingerprint, "inventory": snapshot, "order": order, "candidates": {
                                  name: {"identity": item, "state": "reserved", "api_status": None}
                                  for name, item in identities.items()}}, create=True)
        return self.reservation_id

    def reserved_candidates(self) -> tuple[Version, ...]:
        """Resume frozen graph metadata even after a parent disappeared remotely."""
        value = self._owned(self.reservation_id)
        frozen = {key(item): item for item in self.inventory.versions}
        candidates = tuple(frozen[name] for name in value["order"])
        if any(identity(item) != value["candidates"][key(item)]["identity"] for item in candidates):
            raise RetentionError("registry reservation differs from its frozen manifest graph")
        return candidates

    def check(self, reservation_id: str, candidate: Version) -> None:
        value = self._owned(reservation_id)
        entry = value["candidates"].get(key(candidate))
        if entry is None or entry["identity"] != identity(candidate) or key(candidate) not in self._eligible():
            raise RetentionError("registry reservation no longer owns an unreferenced exact candidate")

    def delete_requested(self, reservation_id: str, candidate: Version) -> None:
        self.check(reservation_id, candidate)
        value = self._owned(reservation_id)
        entry = value["candidates"][key(candidate)]
        if entry["state"] == "absent":
            raise RetentionError("an absent registry version cannot receive another deletion request")
        entry["state"] = "delete_requested"
        _save(self.path, value)

    def absent(self, reservation_id: str, candidate: Version, api_status: int) -> None:
        if type(api_status) is not int or api_status != 404:
            raise RetentionError("registry deletion requires an exact-version 404 receipt")
        self.check(reservation_id, candidate)
        value = self._owned(reservation_id)
        value["candidates"][key(candidate)].update(state="absent", api_status=404)
        _save(self.path, value)

    def complete(self, reservation_id: str) -> None:
        value = self._owned(reservation_id)
        if any(item["state"] != "absent" for item in value["candidates"].values()):
            raise RetentionError("an unresolved registry deletion reservation cannot be released")
        self.path.unlink()
        _sync_directory(self.lock_dir)


def assert_selection_available(package: str, digest: str, *, repository: str) -> None:
    """Reject a reserved digest before a locked reader retrieves or pins it."""
    lock_dir, _ = _require_shared_lock()
    path = lock_dir / JOURNAL
    if not path.exists() and not path.is_symlink():
        return
    journal = _read(path)
    if journal["repository"] != normalize_repository(repository):
        raise RetentionError("another registry retention operation owns this deployment lock")
    for item in journal["candidates"].values():
        value = item["identity"]
        if not isinstance(value, dict):
            raise RetentionError("registry reservation identity is malformed")
        if (value.get("package"), value.get("digest")) == (package, digest):
            raise RetentionError("payload selection conflicts with an exact registry deletion reservation")
