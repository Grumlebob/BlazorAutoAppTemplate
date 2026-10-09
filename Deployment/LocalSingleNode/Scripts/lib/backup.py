"""Protected custom-format dumps and isolated restore verification. Never overwrite the live DB."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def run(*args, **options):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, **options)
    if result.returncode:
        raise ValueError(f"{args[0]} failed (exit {result.returncode}); inspect the service log")
    return result.stdout


def config(path):
    value = json.loads(path.read_text())
    app = value["app_name"]
    if not __import__('re').fullmatch(r"[a-z][a-z0-9-]{0,62}", app):
        raise ValueError("invalid backup app name")
    for key in ("deploy_root", "backup_root"):
        if not __import__('re').fullmatch(r"/opt/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", value[key]):
            raise ValueError("backup roots must stay below /opt")
    return value


def latest(value):
    folder = Path(value["backup_root"])
    files = sorted(folder.glob(value["app_name"] + "-*.dump"))
    if not files:
        raise ValueError("no app backup exists")
    result = files[-1]
    if result.is_symlink() or result.stat().st_size == 0:
        raise ValueError("backup is empty or a symlink")
    return result


def backup(value):
    folder = Path(value["backup_root"])
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("backup directory missing or unsafe")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = folder / f"{value['app_name']}-{stamp}.dump"
    temporary = destination.with_suffix(".partial")
    db = value["app_name"].replace("-", "_")
    with temporary.open("xb") as output:
        result = subprocess.run(["docker", "compose", "--project-directory", value["deploy_root"], "exec", "-T", "postgres", "pg_dump", "-U", db, "-d", db, "-Fc"], stdout=output, stderr=subprocess.PIPE, timeout=180)
    if result.returncode or not temporary.stat().st_size:
        temporary.unlink(missing_ok=True)
        raise ValueError("pg_dump failed; no completed backup was published")
    import grp
    gid = grp.getgrnam(value["install_group"]).gr_gid
    temporary.chmod(0o640)
    os.chown(temporary, -1, gid)
    temporary.replace(destination)
    source = Path(value["secrets_file"])
    if source.is_symlink() or source.stat().st_mode & 0o777 != 0o600:
        raise ValueError("runtime secrets must be a regular 0600 file")
    secret = folder / "secrets.yml"
    # Atomic replacement never follows an existing secret symlink.
    secret_tmp = folder / f".secrets-{uuid.uuid4().hex}.tmp"
    secret_tmp.write_bytes(source.read_bytes())
    secret_tmp.chmod(0o640)
    os.chown(secret_tmp, -1, gid)
    secret_tmp.replace(secret)
    timestamp = folder / "last-success"
    timestamp.write_text(datetime.now(timezone.utc).isoformat() + "\n")
    timestamp.chmod(0o640)
    os.chown(timestamp, -1, gid)
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(value["backup_keep_days"]))
    for file in folder.glob(value["app_name"] + "-*.dump"):
        if not file.is_symlink() and file != destination and datetime.fromtimestamp(file.stat().st_mtime, timezone.utc) < cutoff:
            file.unlink()
    print(f"Backup complete: {destination.name}")


def verify(value, dump):
    dump = dump.resolve(strict=True)
    folder = Path(value["backup_root"]).resolve(strict=True)
    if dump.parent != folder or not dump.name.startswith(value["app_name"] + "-") or dump.suffix != ".dump":
        raise ValueError("restore verification requires this app's protected backup")
    name = f"{value['app_name']}-restore-check-{uuid.uuid4().hex}"
    identity = uuid.uuid4().hex
    run("docker", "run", "-d", "--name", name, "--label", f"localsinglenode.restore={identity}", "--network", "none", "--tmpfs", "/var/lib/postgresql:rw,size=1073741824", "-e", "POSTGRES_PASSWORD=" + uuid.uuid4().hex, "-e", "POSTGRES_DB=restore_check", "postgres:18.4-alpine3.23")
    try:
        for _ in range(60):
            status = subprocess.run(["docker", "exec", name, "pg_isready", "-U", "postgres", "-d", "restore_check"], capture_output=True, timeout=10)
            if not status.returncode:
                break
            time.sleep(2)
        else:
            raise ValueError("throwaway PostgreSQL readiness deadline exceeded")
        with dump.open("rb") as source:
            run("docker", "exec", "-i", name, "pg_restore", "--exit-on-error", "--no-owner", "--no-acl", "-U", "postgres", "-d", "restore_check", stdin=source)
        count = int(run("docker", "exec", name, "psql", "-U", "postgres", "-d", "restore_check", "-Atc", "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';").strip())
        if count <= 0:
            raise ValueError("restore has no public tables")
        print(f"Restore verification passed: {count} tables")
    finally:
        data = json.loads(run("docker", "inspect", name))[0]
        if data.get("Config", {}).get("Labels", {}).get("localsinglenode.restore") == identity:
            run("docker", "rm", "-f", name)


def restore_replacement(value, dump, target, confirmation):
    # Manual recovery creates a new database; it never overwrites the live one.
    import re
    db = value["app_name"].replace("-", "_")
    if confirmation != value["app_name"] or not re.fullmatch(re.escape(db) + r"_restore_[a-z0-9_]{1,40}", target):
        raise ValueError("Manual restore needs --confirm-restore <app_name> and a new <db>_restore_<suffix> database")
    dump = dump.resolve(strict=True)
    if dump.parent != Path(value["backup_root"]).resolve(strict=True) or not dump.name.startswith(value["app_name"] + '-') or dump.suffix != '.dump':
        raise ValueError("Manual restore requires this app's protected backup")
    prefix = ["docker", "compose", "--project-directory", value["deploy_root"], "exec", "-T", "postgres"]
    exists = run(*prefix, "psql", "-U", db, "-d", "postgres", "-Atc", f"SELECT count(*) FROM pg_database WHERE datname='{target}';").strip()
    if exists != b"0":
        raise ValueError("Replacement database already exists; no restore performed")
    run(*prefix, "createdb", "-U", db, target)
    with dump.open('rb') as source:
        run(*prefix, "pg_restore", "--exit-on-error", "--no-owner", "--no-acl", "-U", db, "-d", target, stdin=source)
    print("Manual restore completed into replacement database " + target + "; live database unchanged")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--restore-into")
    parser.add_argument("--confirm-restore")
    args = parser.parse_args()
    value = config(args.config)
    if args.restore_into:
        restore_replacement(value, args.file or latest(value), args.restore_into, args.confirm_restore)
    elif args.verify:
        verify(value, args.file or latest(value))
    else:
        backup(value)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
