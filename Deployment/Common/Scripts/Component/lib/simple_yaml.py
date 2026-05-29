from __future__ import annotations

import re
from pathlib import Path


def read_simple_yaml(path: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    errors: list[str] = []

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", line)
        if not match:
            errors.append(f"{path}:{line_number}: unsupported setting line: {raw_line}")
            continue
        key, value = match.groups()
        if key in values:
            errors.append(f"{path}:{line_number}: duplicate setting: {key}")
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key] = value.strip()

    return values, errors
