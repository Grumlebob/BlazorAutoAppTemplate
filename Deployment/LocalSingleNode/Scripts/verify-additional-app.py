"""Read-only privileged guard for app-only preparation on an existing native host."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parent / "resolve-app-instance.py"
SPEC = importlib.util.spec_from_file_location("app_instance", SCRIPT)
assert SPEC and SPEC.loader
instance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(instance)
from ls_settings import ETC, TARGET, command, settings
from platform_check import native
from resolve_frontend_profile import resolve_frontend_profile


def inspect_resources(app: str, owned: bool) -> None:
    ids = command("docker", "ps", "-aq").splitlines()
    containers = json.loads(command("docker", "inspect", *ids)) if ids else []
    for item in containers:
        labels = item.get("Config", {}).get("Labels") or {}
        name = item.get("Name", "").lstrip("/")
        if labels.get("com.docker.compose.project") == app or name.startswith((app + "-", app + "_")):
            if not owned or labels.get("com.docker.compose.project") != app or labels.get("localsinglenode.app") != app:
                raise ValueError("unowned container uses the requested application identity")
    for kind in ("network", "volume"):
        ids = command("docker", kind, "ls", "-q").splitlines()
        objects = json.loads(command("docker", kind, "inspect", *ids)) if ids else []
        for item in objects:
            labels = item.get("Labels") or {}
            name = item.get("Name", "")
            if labels.get("com.docker.compose.project") == app or name.startswith(app + "_"):
                if not owned or labels.get("com.docker.compose.project") != app:
                    raise ValueError("unowned network or data volume uses the requested application identity")


def verify(path: Path, source: str) -> None:
    primary = settings(TARGET / "inventory/group_vars/all.yml")
    selected = resolve_frontend_profile(instance.ROOT / "frontend-profile.txt")
    other = "React" if selected == "BlazorAuto" else "BlazorAuto"
    candidate, _, _ = instance.validate_additional({"schema_version": 1, "frontend_profile": other,
                                                   "settings": settings(path), "public": {}}, primary, selected)
    instance.verify_owned(primary, source)
    marker = ETC / f"localsinglenode/apps/{candidate['app_name']}.json"
    owned = marker.exists() or marker.is_symlink()
    if owned:
        instance.verify_owned(candidate, source)
    for suffix in ("service", "timer"):
        unit = ETC / f"systemd/system/{candidate['app_name']}-backup.{suffix}"
        if unit.is_symlink() or (unit.exists() and not owned):
            raise ValueError("unowned backup unit uses the requested application identity")
    for root in (Path(candidate["deploy_root"]), Path(candidate["backup_root"]), ETC / candidate["app_name"]):
        if any(parent.is_symlink() for parent in (root, *root.parents)):
            raise ValueError("application paths cannot traverse symlinks")
    inspect_resources(candidate["app_name"], owned)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings-file", type=Path, required=True)
    parser.add_argument("--source-repo-url", required=True)
    args = parser.parse_args()
    try:
        if not native() or os.geteuid() != 0 or os.environ.get("LOCALSINGLENODE_ETC") or os.environ.get("OPT_ROOT"):
            raise ValueError("privileged guard requires the real configured native host")
        verify(args.settings_file, args.source_repo_url)
        print("Existing host ownership and additional app resources verified.")
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, SyntaxError):
        print("Additional app ownership or resource verification failed; no changes made.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
