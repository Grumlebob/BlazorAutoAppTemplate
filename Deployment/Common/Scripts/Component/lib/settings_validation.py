"""Pure validation primitives shared by deployment settings readers."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


def valid_dns_name(value: str) -> bool:
    if len(value) > 253 or "." not in value:
        return False
    labels = value.rstrip(".").split(".")
    for label in labels:
        if not 1 <= len(label) <= 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not re.match(r"^[A-Za-z0-9-]+$", label):
            return False
    return True


def posix_opt_path_checks(value: str) -> tuple[bool, bool, bool]:
    """Return prefix, whitespace and character checks in owner-message order."""
    return (
        value.startswith("/opt/"),
        re.search(r"\s", value) is None,
        re.match(r"^/[A-Za-z0-9._/-]+$", value) is not None,
    )


def validate_observability_ports(
    values: Mapping[str, str],
    keys: Iterable[str],
    occupied_ports: Mapping[int, str],
) -> list[str]:
    """Return the same ordered errors without changing the caller's port map."""
    errors: list[str] = []
    seen_ports = dict(occupied_ports)

    for key in keys:
        port_value = values.get(key, "")
        if not port_value:
            continue
        if not port_value.isdigit():
            errors.append(f"{key} must be a number")
            continue
        port = int(port_value)
        if port < 1024 or port > 65535:
            errors.append(f"{key} must be between 1024 and 65535")
        previous_key = seen_ports.get(port)
        if previous_key:
            errors.append(f"{key} must not reuse {previous_key} ({port})")
        else:
            seen_ports[port] = key

    return errors


def valid_retention_period(value: str) -> bool:
    return re.match(r"^[0-9]+[hdwmy]$", value) is not None


def valid_retention_size(value: str) -> bool:
    return re.match(r"^[0-9]+(MB|GB)$", value) is not None
