"""Bound the shared Docker daemon's BuildKit cache with the daemon's own garbage collection.

LocalSingleNode only. Scheduled trims (build_cache.py) keep the cache near its budget, but they depend on
GitHub Actions schedules and a green main. This helper sets BuildKit's garbage-collection policy in the
Docker daemon configuration, so the daemon bounds the cache itself between those runs.

Only the `builder.gc` keys this helper owns are written; every other daemon setting, the file's mode
and ownership are preserved. A candidate is checked with `dockerd --validate` before an atomic replace,
and the previous file (or its absence) is kept as a timestamped backup. Applying restarts Docker, which
restarts every container on the node while live restore is off, so it refuses unless the node is quiet
(only long-running Compose services that Docker restarts itself, no CI or test stacks, and no image
build in progress). It then waits until every container
that was running is running again and healthy where it has a health check. If any step after the
replace fails, the previous file is restored and Docker is restarted again. Images, containers, volumes
and build cache entries are never removed here.

Usage (as root, normally through the LocalSingleNode Docker GC workflow under the deployment lock):
  docker_gc.py report
  docker_gc.py apply [--dry-run]
  docker_gc.py rollback --backup /etc/docker/daemon.json.bak-<UTC timestamp>[.absent]
"""
import argparse
import copy
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

DAEMON_CONFIG = Path("/etc/docker/daemon.json")
DEFAULT_RESERVED = "10GB"
DEFAULT_MAX_USED = "30GB"
DEFAULT_MIN_FREE = "30%"
RESTARTING_POLICIES = ("always", "unless-stopped")
_CI_PROJECT = re.compile(r"(?:^|-)ci(?:-|$)")
OWNED_KEYS = ("enabled", "defaultReservedSpace", "defaultMaxUsedSpace", "defaultMinFreeSpace")
_SIZE = re.compile(r"[1-9][0-9]{0,5}(?:\.[0-9]+)?(?:B|KB|kB|MB|GB|TB)")
_PERCENT = re.compile(r"(?:[1-9]|[1-8][0-9]|90)%")
ABSENT_SUFFIX = ".absent"


class GcError(Exception):
    pass


def run(*args, timeout=120, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if check and result.returncode:
        raise GcError(f"{' '.join(args[:3])} failed (exit {result.returncode}): {(result.stderr or result.stdout).strip()[:300]}")
    return result


def desired_policy(reserved, max_used, min_free):
    if not _SIZE.fullmatch(reserved) or not _SIZE.fullmatch(max_used):
        raise GcError("reserved and max-used space must be sizes such as 10GB")
    if not _PERCENT.fullmatch(min_free):
        raise GcError("min-free space must be a percentage from 1% to 90%")
    return {"enabled": True, "defaultReservedSpace": reserved, "defaultMaxUsedSpace": max_used,
            "defaultMinFreeSpace": min_free}


def load_config(path):
    """Return (config, original_bytes or None, stat or None). Refuses unreadable or non-object JSON."""
    if not path.exists():
        return {}, None, None
    raw = path.read_bytes()
    info = path.stat()
    if not raw.strip():
        return {}, raw, info
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as error:
        raise GcError(f"{path} is not valid JSON ({error.msg}); fix it by hand before applying") from error
    if not isinstance(config, dict):
        raise GcError(f"{path} must contain a JSON object")
    return config, raw, info


def merge(config, policy):
    """Return a copy of config with only the owned builder.gc keys set; refuse incompatible shapes."""
    merged = copy.deepcopy(config)
    builder = merged.setdefault("builder", {})
    if not isinstance(builder, dict):
        raise GcError("existing builder setting is not an object; refusing to change it")
    gc = builder.setdefault("gc", {})
    if not isinstance(gc, dict):
        raise GcError("existing builder.gc setting is not an object; refusing to change it")
    if "defaultKeepStorage" in gc:
        raise GcError("existing builder.gc.defaultKeepStorage conflicts with the space keys; resolve it by hand")
    for key in OWNED_KEYS:
        gc[key] = policy[key]
    return merged


def render(config):
    return (json.dumps(config, indent=2) + "\n").encode("utf-8")


def write_atomically(path, data, mode, owner):
    """Write data next to path and atomically replace it, keeping mode and (as root) ownership."""
    handle, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        if owner is not None and hasattr(os, "chown") and getattr(os, "geteuid", lambda: 1)() == 0:
            os.chown(temp, *owner)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def validate(path, runner):
    result = runner("dockerd", "--validate", "--config-file", str(path), check=False)
    output = (result.stdout + result.stderr).strip()
    if result.returncode or "configuration OK" not in output:
        raise GcError(f"dockerd rejected the candidate configuration: {output[:300]}")


def running_containers(runner):
    """Return {name: (has_healthcheck, compose_project, restart_policy)} for every running container."""
    ids = runner("docker", "ps", "-q").stdout.split()
    containers = {}
    for container in ids:
        line = runner("docker", "inspect", "-f",
                      '{{.Name}}|{{if .State.Health}}yes{{else}}no{{end}}|{{index .Config.Labels "com.docker.compose.project"}}'
                      '|{{.HostConfig.RestartPolicy.Name}}',
                      container).stdout.strip()
        name, health, project, restart = (line.split("|") + ["", "", ""])[:4]
        containers[name.lstrip("/")] = (health == "yes", "" if project == "<no value>" else project, restart)
    return containers


def require_quiet_node(runner, containers):
    """Refuse while CI or test containers run or an image build is in progress.

    Only long-running Compose services survive the restart: they come back through their restart policy.
    A CI stack is a Compose project too (for example `carboncalculator-ci-<run>`), so its project name
    and its missing restart policy both mark it as a container the restart would kill mid-run.
    """
    strays = sorted(name for name, (_, project, restart) in containers.items()
                    if not project or _CI_PROJECT.search(project) or restart not in RESTARTING_POLICIES)
    if strays:
        raise GcError(f"CI, test or other short-lived containers are running ({', '.join(strays[:5])}); "
                      "wait for CI to finish")
    builds = runner("pgrep", "-af", "docker(-buildx)? (buildx )?build", check=False).stdout.strip()
    if builds:
        raise GcError("an image build is in progress; wait for it to finish")


def restart_docker(runner, sleep, timeout=180):
    runner("systemctl", "restart", "docker", timeout=timeout)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if runner("docker", "info", "--format", "{{.ServerVersion}}", check=False).returncode == 0:
            return
        sleep(3)
    raise GcError("Docker did not come back after the restart")


def wait_for_containers(runner, expected, sleep, timeout=300):
    """Wait until every expected container runs, and is healthy where it has a health check."""
    deadline = time.monotonic() + timeout
    pending = dict(expected)
    while pending and time.monotonic() < deadline:
        for name, (has_health, *_) in list(pending.items()):
            state = runner("docker", "inspect", "-f",
                           "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}", name,
                           check=False).stdout.strip()
            status, _, health = state.partition("|")
            if status == "running" and (not has_health or health == "healthy"):
                del pending[name]
        if pending:
            sleep(5)
    if pending:
        raise GcError(f"containers did not recover after the restart: {', '.join(sorted(pending))}")


def backup_path(path, now, absent):
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    return path.with_name(f"{path.name}.bak-{stamp}{ABSENT_SUFFIX if absent else ''}")


def restore(path, backup, original_info):
    if backup.name.endswith(ABSENT_SUFFIX):
        path.unlink(missing_ok=True)
        return
    owner = (original_info.st_uid, original_info.st_gid) if original_info else None
    mode = stat.S_IMODE(original_info.st_mode) if original_info else 0o644
    write_atomically(path, backup.read_bytes(), mode, owner)


def report(path, policy, runner, out):
    config, _, _ = load_config(path)
    current = (config.get("builder") or {}).get("gc") if isinstance(config.get("builder"), dict) else None
    out(f"daemon config: {'present' if path.exists() else 'absent'}")
    out(f"current builder.gc: {json.dumps(current) if current else 'not set'}")
    out(f"planned builder.gc keys: {json.dumps(policy)}")
    cache = runner("docker", "system", "df", "--format", "{{.Type}}: {{.Size}} (reclaimable {{.Reclaimable}})",
                   check=False).stdout
    for line in cache.splitlines():
        if line.startswith("Build Cache"):
            out(line)
    return 0


def apply(path, policy, runner, out, sleep=time.sleep, now=None, dry_run=False):
    config, raw, info = load_config(path)
    merged = merge(config, policy)
    if merged == config:
        out("BuildKit GC policy already set; nothing to change and no restart.")
        return 0
    candidate = render(merged)
    mode = stat.S_IMODE(info.st_mode) if info else 0o644
    owner = (info.st_uid, info.st_gid) if info else None
    handle, probe = tempfile.mkstemp(prefix=f".{path.name}.candidate.", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(candidate)
        validate(Path(probe), runner)
    finally:
        Path(probe).unlink(missing_ok=True)
    if dry_run:
        out("Dry run; the merged configuration validates. It would be:")
        out(candidate.decode("utf-8").rstrip())
        return 0

    containers = running_containers(runner)
    require_quiet_node(runner, containers)
    backup = backup_path(path, now or datetime.now(timezone.utc), absent=raw is None)
    if raw is None:
        backup.write_bytes(b"")
    else:
        write_atomically(backup, raw, 0o600, owner)
    out(f"Backup: {backup}")
    write_atomically(path, candidate, mode, owner)
    try:
        restart_docker(runner, sleep)
        wait_for_containers(runner, containers, sleep)
    except GcError as error:
        out(f"Apply failed after the restart ({error}); restoring the previous configuration.")
        restore(path, backup, info)
        restart_docker(runner, sleep)
        wait_for_containers(runner, containers, sleep)
        raise GcError(f"apply rolled back: {error}") from error
    out(f"Applied BuildKit GC policy; {len(containers)} containers recovered.")
    return 0


def rollback(path, backup, runner, out, sleep=time.sleep):
    if not backup.name.startswith(f"{path.name}.bak-") or backup.parent != path.parent:
        raise GcError("the backup must be a daemon.json.bak-<timestamp> file next to the daemon configuration")
    if not backup.exists():
        raise GcError(f"backup {backup} does not exist")
    if not backup.name.endswith(ABSENT_SUFFIX):
        restored, _, _ = load_config(backup)
        handle, probe = tempfile.mkstemp(prefix=f".{path.name}.candidate.", dir=str(path.parent))
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(render(restored) if restored else backup.read_bytes())
            validate(Path(probe), runner)
        finally:
            Path(probe).unlink(missing_ok=True)
    containers = running_containers(runner)
    require_quiet_node(runner, containers)
    _, _, info = load_config(path)
    restore(path, backup, info)
    restart_docker(runner, sleep)
    wait_for_containers(runner, containers, sleep)
    out(f"Restored {backup.name}; {len(containers)} containers recovered.")
    return 0


def main(argv=None, runner=run, out=print, config_path=DAEMON_CONFIG, sleep=time.sleep):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("report", "apply", "rollback"))
    parser.add_argument("--dry-run", action="store_true", help="apply: validate and print the merged file only")
    parser.add_argument("--backup", help="rollback: the backup file an earlier apply printed")
    parser.add_argument("--reserved", default=DEFAULT_RESERVED)
    parser.add_argument("--max-used", default=DEFAULT_MAX_USED)
    parser.add_argument("--min-free", default=DEFAULT_MIN_FREE)
    parser.add_argument("--config", default=str(config_path), help="daemon configuration path (tests and dry runs)")
    args = parser.parse_args(argv)
    policy = desired_policy(args.reserved, args.max_used, args.min_free)
    path = Path(args.config)
    if args.mode == "report":
        return report(path, policy, runner, out)
    if args.mode == "apply":
        return apply(path, policy, runner, out, sleep=sleep, dry_run=args.dry_run)
    if not args.backup:
        raise GcError("rollback needs --backup")
    return rollback(path, Path(args.backup), runner, out, sleep=sleep)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (GcError, OSError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
