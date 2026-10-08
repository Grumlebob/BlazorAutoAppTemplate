from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Mapping


PROVENANCE_FILENAME = "migration-provenance.json"
PROVENANCE_KEYS = {
    "schema_version",
    "repository",
    "source_sha",
    "run_id",
    "run_attempt",
    "bundle_filename",
    "runtime",
    "dotnet_sdk_version",
    "ordered_migration_ids",
    "bundle_sha256",
}
MIGRATION_ROW_KEYS = {"id", "name", "safeName", "applied"}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SDK_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


class StagingArtifactError(ValueError):
    pass


def _fail(message: str) -> None:
    raise StagingArtifactError(message)


def _safe_filename(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or not re.fullmatch(r"[A-Za-z0-9._-]{1,255}", value)
    ):
        _fail("bundle filename must be a simple root-level filename")
    return value


def _required_environment(env: Mapping[str, str], key: str) -> str:
    value = env.get(key)
    if not isinstance(value, str) or not value:
        _fail(f"required environment value is missing: {key}")
    return value


def _repository_url(env: Mapping[str, str]) -> str:
    server = _required_environment(env, "GITHUB_SERVER_URL").rstrip("/")
    repository = _required_environment(env, "GITHUB_REPOSITORY")
    if repository.startswith("/") or ".." in repository.split("/"):
        _fail("repository name is malformed")
    return f"{server}/{repository}"


def _context(env: Mapping[str, str]) -> dict[str, str]:
    source_sha = _required_environment(env, "GITHUB_SHA")
    run_id = _required_environment(env, "GITHUB_RUN_ID")
    run_attempt = _required_environment(env, "GITHUB_RUN_ATTEMPT")
    if not SOURCE_SHA_RE.fullmatch(source_sha):
        _fail("source SHA must be a full lowercase Git commit ID")
    if not run_id.isdigit() or int(run_id) < 1:
        _fail("run ID must be a positive decimal string")
    if not run_attempt.isdigit() or int(run_attempt) < 1:
        _fail("run attempt must be a positive decimal string")
    return {
        "repository": _repository_url(env),
        "source_sha": source_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
    }


def parse_migration_list(output: str) -> list[str]:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as error:
        _fail(f"dotnet-ef migration output is not JSON: {error}")
    if type(payload) is not list:
        _fail("dotnet-ef migration output root must be an array")

    migration_ids: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(payload):
        if type(row) is not dict or set(row) != MIGRATION_ROW_KEYS:
            _fail(f"dotnet-ef migration row {index} has an unknown shape")
        if (
            type(row["id"]) is not str
            or type(row["name"]) is not str
            or type(row["safeName"]) is not str
            or (row["applied"] is not None and type(row["applied"]) is not bool)
        ):
            _fail(f"dotnet-ef migration row {index} has an invalid field type")
        migration_id = row["id"]
        if not migration_id.strip():
            _fail(f"dotnet-ef migration row {index} has an empty ID")
        if migration_id in seen:
            _fail(f"dotnet-ef migration output repeats ID {migration_id!r}")
        seen.add(migration_id)
        migration_ids.append(migration_id)
    return migration_ids


def _require_root_directory(directory: Path) -> None:
    try:
        mode = directory.lstat().st_mode
    except OSError as error:
        _fail(f"staging directory is unavailable: {error}")
    if not stat.S_ISDIR(mode):
        _fail("staging path must be a real directory, not a symlink")


def _require_regular_nonempty(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as error:
        _fail(f"{label} is missing: {error}")
    if not stat.S_ISREG(info.st_mode):
        _fail(f"{label} must be a regular file, not a symlink or directory")
    if info.st_size <= 0:
        _fail(f"{label} must not be empty")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_staging_artifact(
    directory: Path,
    bundle_filename: str,
    runtime: str,
    repository_root: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ if env is None else env
    bundle_filename = _safe_filename(bundle_filename)
    if bundle_filename == PROVENANCE_FILENAME:
        _fail("bundle filename collides with provenance filename")
    if not runtime:
        _fail("migration runtime must not be empty")
    _require_root_directory(directory)
    bundle_path = directory / bundle_filename
    _require_regular_nonempty(bundle_path, "migration bundle")

    migration_command = [
        "dotnet",
        "ef",
        "migrations",
        "list",
        "--no-connect",
        "--json",
        "--no-color",
        "--no-build",
        "--project",
        "BlazorAutoApp/BlazorAutoApp.csproj",
        "--startup-project",
        "BlazorAutoApp/BlazorAutoApp.csproj",
        "--configuration",
        "Release",
    ]
    try:
        migration_output = subprocess.run(
            migration_command,
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        sdk_version = subprocess.run(
            ["dotnet", "--version"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        _fail(f"could not query pinned dotnet-ef migration metadata: {error}")

    if not SDK_RE.fullmatch(sdk_version):
        _fail("dotnet --version returned an invalid SDK version")
    context = _context(env)
    provenance = {
        "schema_version": 1,
        **context,
        "bundle_filename": bundle_filename,
        "runtime": runtime,
        "dotnet_sdk_version": sdk_version,
        "ordered_migration_ids": parse_migration_list(migration_output),
        "bundle_sha256": _sha256(bundle_path),
    }
    provenance_path = directory / PROVENANCE_FILENAME
    if provenance_path.exists() or provenance_path.is_symlink():
        _fail("provenance output already exists")
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return provenance


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"provenance JSON repeats key {key!r}")
        result[key] = value
    return result


def _read_provenance(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _fail(f"provenance JSON cannot be read: {error}")
    if type(value) is not dict:
        _fail("provenance JSON root must be an object")
    if set(value) != PROVENANCE_KEYS:
        missing = sorted(PROVENANCE_KEYS - set(value))
        extra = sorted(set(value) - PROVENANCE_KEYS)
        _fail(f"provenance keys differ from schema (missing={missing}, extra={extra})")
    return value


def validate_staging_artifact(
    directory: Path,
    bundle_filename: str,
    runtime: str,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ if env is None else env
    bundle_filename = _safe_filename(bundle_filename)
    if bundle_filename == PROVENANCE_FILENAME:
        _fail("bundle filename collides with provenance filename")
    if not runtime:
        _fail("migration runtime must not be empty")
    _require_root_directory(directory)

    expected_files = {bundle_filename, PROVENANCE_FILENAME}
    try:
        actual_files = {entry.name for entry in directory.iterdir()}
    except OSError as error:
        _fail(f"staging directory cannot be listed: {error}")
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        extra = sorted(actual_files - expected_files)
        _fail(f"staging files differ from allowlist (missing={missing}, extra={extra})")

    bundle_path = directory / bundle_filename
    provenance_path = directory / PROVENANCE_FILENAME
    _require_regular_nonempty(bundle_path, "migration bundle")
    _require_regular_nonempty(provenance_path, "migration provenance")
    provenance = _read_provenance(provenance_path)

    if type(provenance["schema_version"]) is not int or provenance["schema_version"] != 1:
        _fail("provenance schema version must be integer 1")
    for key in PROVENANCE_KEYS - {"schema_version", "ordered_migration_ids"}:
        if type(provenance[key]) is not str or not provenance[key]:
            _fail(f"provenance field {key!r} must be a nonempty string")

    context = _context(env)
    for key, expected in context.items():
        if provenance[key] != expected:
            _fail(f"provenance field {key!r} does not match current workflow context")
    if provenance["bundle_filename"] != bundle_filename:
        _fail("provenance bundle filename does not match configured release setting")
    if provenance["runtime"] != runtime:
        _fail("provenance runtime does not match configured release setting")
    if not SDK_RE.fullmatch(provenance["dotnet_sdk_version"]):
        _fail("provenance SDK version is malformed")

    migration_ids = provenance["ordered_migration_ids"]
    if type(migration_ids) is not list:
        _fail("provenance migration IDs must be an array")
    seen: set[str] = set()
    for migration_id in migration_ids:
        if type(migration_id) is not str or not migration_id.strip():
            _fail("provenance migration IDs must be nonempty strings")
        if migration_id in seen:
            _fail(f"provenance repeats migration ID {migration_id!r}")
        seen.add(migration_id)

    bundle_sha256 = provenance["bundle_sha256"]
    if not SHA_RE.fullmatch(bundle_sha256):
        _fail("provenance bundle SHA-256 must be 64 lowercase hexadecimal characters")
    if _sha256(bundle_path) != bundle_sha256:
        _fail("migration bundle SHA-256 does not match provenance")
    return provenance


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or validate exact CI migration staging artifact.")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("create", "validate"):
        command = subparsers.add_parser(operation)
        command.add_argument("--directory", type=Path, required=True)
        command.add_argument("--bundle-filename", required=True)
        command.add_argument("--runtime", required=True)
        if operation == "create":
            command.add_argument("--repository-root", type=Path, default=Path.cwd())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.operation == "create":
            provenance = create_staging_artifact(
                args.directory,
                args.bundle_filename,
                args.runtime,
                args.repository_root,
            )
            print(json.dumps(provenance, indent=2, sort_keys=True))
        else:
            provenance = validate_staging_artifact(
                args.directory,
                args.bundle_filename,
                args.runtime,
            )
            print(
                "Validated migration staging artifact: "
                f"bundle={provenance['bundle_filename']} "
                f"run={provenance['run_id']}/{provenance['run_attempt']}"
            )
    except StagingArtifactError as error:
        print(f"migration staging artifact rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())