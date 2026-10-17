"""Validate the existing shared deployment lock identity without importing pin code."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Type


def require_shared_lock(error_type: Type[ValueError]) -> tuple[Path, str]:
    lock_text = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_DIR", "")
    token = os.environ.get("LOCALCLUSTER_DEPLOY_LOCK_TOKEN", "")
    if not lock_text or not token:
        raise error_type("operation requires the shared deployment lock")
    lock_dir = Path(lock_text)
    token_path = lock_dir / "token"
    if (lock_dir.is_symlink() or not lock_dir.is_dir() or token_path.is_symlink()
            or not token_path.is_file()):
        raise error_type("shared deployment lock identity is unavailable")
    try:
        actual = token_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise error_type("shared deployment lock token cannot be read") from error
    if actual != token:
        raise error_type("shared deployment lock token changed")
    return lock_dir.resolve(), token
