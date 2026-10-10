"""Retire only the exact legacy Caddy apt source installed by this repository."""
import os
from pathlib import Path
import sys


SOURCE = Path("/etc/apt/sources.list.d/caddy-stable.list")
REPOSITORY = "https://dl.cloudsmith.io/public/caddy/stable/deb/debian"
OPTIONS = "[signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg]"


def retire(source=SOURCE):
    if source.is_symlink():
        raise ValueError(f"Refusing symlink at {source}; operator inspection required")
    if not source.exists():
        return False
    content = source.read_text()
    entries = [line.split() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    allowed = [[kind, OPTIONS, REPOSITORY, "any-version", "main"] for kind in ("deb", "deb-src")]
    if not entries or any(entry not in allowed for entry in entries):
        raise ValueError(f"Foreign Caddy apt source at {source}; operator inspection required")
    backup = source.with_suffix(".list.disabled")
    if backup.is_symlink() or (backup.exists() and backup.read_text() != content):
        raise ValueError(f"Refusing to overwrite {backup}; operator inspection required")
    if backup.exists():
        source.unlink()
    else:
        source.rename(backup)
    print("Retired legacy Caddy source; preserved it as " + str(backup))
    return True


if __name__ == "__main__":
    try:
        if os.geteuid() != 0:
            raise ValueError("Run only through the operator bootstrap or provisioning playbook")
        retire()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
