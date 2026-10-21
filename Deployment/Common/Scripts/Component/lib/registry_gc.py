"""Apply exact registry-version deletions through an existing coordination owner.

The guard adapter must atomically reserve unreferenced identities and reject
selection of reserved identities. An exception never releases a reservation;
resumption reconciles the exact remote version before any repeated request.
"""

from __future__ import annotations

from datetime import datetime
import re
import time
from typing import Protocol

from registry_retention import DIGEST, MAX_DELETIONS, PACKAGE, RetentionError, Version


class DeletionUncertain(RetentionError):
    """The reservation must be reconciled before retry or release."""


class Guard(Protocol):
    def reserve(self, candidates: tuple[Version, ...]) -> str:
        """Reserve exact unreferenced identities, or resume the identical batch."""

    def check(self, reservation_id: str, candidate: Version) -> None:
        """Verify reservation ownership, held coordination and fresh references."""

    def delete_requested(self, reservation_id: str, candidate: Version) -> None:
        """Refresh protection and persist immutable intent immediately before DELETE."""

    def absent(self, reservation_id: str, candidate: Version, api_status: int) -> None:
        """Persist the exact-version 404 receipt."""

    def complete(self, reservation_id: str) -> None:
        """Finish only after every reserved identity has an absence receipt."""


class Registry(Protocol):
    def version(self, package: str, version_id: int) -> dict | None:
        """Return version metadata, or None only for an exact-version 404."""

    def delete_version(self, package: str, version_id: int) -> None:
        """Send DELETE for this exact immutable version."""


ABSENCE_RETRY_DELAYS = (0.5, 1.0, 2.0, 3.0)


def _confirm_exact_absence(registry: Registry, candidate: Version) -> bool:
    """Allow bounded GHCR visibility lag without repeating the DELETE request."""
    for delay in (0.0, *ABSENCE_RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        if registry.version(candidate.package, candidate.version_id) is None:
            return True
    return False


def _matches(candidate: Version, remote: dict) -> bool:
    try:
        tags = remote["metadata"]["container"]["tags"]
        created = datetime.fromisoformat(remote["created_at"].replace("Z", "+00:00"))
        return (type(remote["id"]) is int and remote["id"] == candidate.version_id
                and remote["name"] == candidate.digest
                and isinstance(tags, list) and len(tags) == len(set(tags))
                and frozenset(tags) == candidate.tags and created == candidate.created)
    except (KeyError, AttributeError, TypeError, ValueError):
        return False


def apply_deletions(
    candidates: tuple[Version, ...],
    *,
    registry: Registry,
    guard: Guard,
    complete_reservation: bool = True,
) -> tuple[dict, ...]:
    """Recheck each reserved identity, delete it and prove exact remote absence."""
    if type(complete_reservation) is not bool:
        raise RetentionError("registry reservation completion mode must be explicit")
    if not candidates:
        return ()
    if len(candidates) > MAX_DELETIONS:
        raise RetentionError("registry deletion exceeds its fixed batch cap")
    identities = set()
    for item in candidates:
        key = item.package, item.version_id
        if (key in identities or not PACKAGE.fullmatch(item.package) or not DIGEST.fullmatch(item.digest)
                or type(item.version_id) is not int or item.version_id <= 0):
            raise RetentionError("registry deletion has duplicate or invalid immutable identities")
        identities.add(key)
    reservation = guard.reserve(candidates)
    if not isinstance(reservation, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", reservation):
        raise RetentionError("coordination did not return a valid owned reservation")
    receipts = []
    for candidate in candidates:
        remote = registry.version(candidate.package, candidate.version_id)
        if remote is not None:
            if not isinstance(remote, dict) or not _matches(candidate, remote):
                raise RetentionError("reserved registry version identity or referencing tags changed; no DELETE was sent")
            # This boundary refreshes protection and persists intent before DELETE.
            guard.delete_requested(reservation, candidate)
            try:
                registry.delete_version(candidate.package, candidate.version_id)
                confirmed_absent = _confirm_exact_absence(registry, candidate)
            except Exception as error:
                raise DeletionUncertain(
                    f"registry deletion outcome is unknown for {candidate.package} version {candidate.version_id}; "
                    f"resume reservation {reservation} to reconcile that exact identity"
                ) from error
            if not confirmed_absent:
                raise DeletionUncertain(
                    "registry version remains present after bounded exact-ID verification; "
                    "its owned deletion reservation remains pending"
                )
        guard.absent(reservation, candidate, 404)
        receipts.append({
            "reservation_id": reservation, "package": candidate.package, "version_id": candidate.version_id,
            "digest": candidate.digest, "tags": sorted(candidate.tags), "api_status": 404,
        })
    if complete_reservation:
        guard.complete(reservation)
    return tuple(receipts)
