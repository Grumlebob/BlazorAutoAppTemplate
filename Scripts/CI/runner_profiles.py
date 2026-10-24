"""Portable CI identities supplied by private installation state or CI settings.

This module validates data only. It never starts a service, changes a runner
registration, or substitutes observed machine values for configured identities.
Native identities use portable registration fields; managed desktop profiles add
the ownership marker and service identity their installation requires.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any


class ProfileError(ValueError):
    pass


def _text(value: Any, field: str, pattern: str | None = None) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProfileError(f"{field} must be a nonempty string without surrounding whitespace")
    if pattern and not re.fullmatch(pattern, value):
        raise ProfileError(f"{field} has an invalid format")
    return value


def _repository(value: Any, field: str) -> str:
    value = _text(value, field, r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*")
    return value


def _path(value: Any, field: str) -> PurePosixPath:
    value = _text(value, field)
    path = PurePosixPath(value)
    if (not path.is_absolute() or str(path) != value or value == "/"
            or ".." in path.parts or "\\" in value or path.parts[1] == "mnt"):
        raise ProfileError(f"{field} must be a canonical Linux path outside /mnt")
    return path


def _integer(value: Any, field: str, minimum: int, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or maximum is not None and value > maximum:
        raise ProfileError(f"{field} is outside its allowed integer range")
    return value


def _object(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ProfileError(f"{name} has missing or unknown fields")
    return value


@dataclass(frozen=True)
class CapacityRoot:
    path: PurePosixPath
    minimum_free_bytes: int
    minimum_free_percent: int
    minimum_free_inode_percent: int


@dataclass(frozen=True)
class RunnerProfile:
    id: str
    kind: str
    instance: str | None
    owner_repository: str | None
    owner_task_id: str | None
    repository: str
    runner_name: str
    expected_host: str
    labels: tuple[str, ...]
    runner_root: PurePosixPath
    workspace_root: PurePosixPath
    marker_path: PurePosixPath | None
    service: str | None
    docker_endpoint: str
    docker_id: str
    docker_data_root: PurePosixPath
    report_root: PurePosixPath
    temporary_root: PurePosixPath
    capacity_roots: tuple[CapacityRoot, ...]


PROFILE_FIELDS = {
    "id", "kind", "repository", "runnerName", "expectedHost", "labels",
    "runnerRoot", "workspaceRoot", "dockerEndpoint", "dockerId", "dockerDataRoot",
    "reportRoot", "temporaryRoot", "capacityRoots",
}
DESKTOP_PROFILE_FIELDS = {"instance", "ownerRepository", "ownerTaskId", "markerPath", "service"}


def parse_profile(value: Any) -> RunnerProfile:
    if (not isinstance(value, dict) or not isinstance(value.get("kind"), str)
            or value.get("kind") not in {"native", "desktop"}):
        raise ProfileError("unknown CI profile kind")
    kind = _text(value["kind"], "kind")
    expected_fields = PROFILE_FIELDS | (DESKTOP_PROFILE_FIELDS if kind == "desktop" else set())
    value = _object(value, expected_fields, "runner profile")
    repository = _repository(value["repository"], "repository")
    token = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
    name = _text(value["runnerName"], "runnerName", token)
    # Unit IDs may remain attached to an infrastructure slot during repository
    # reassignment. The managed installation separately binds these exact IDs
    # to its owned slots; do not derive authority from a unit's historical name.
    instance = owner = owner_task_id = marker_path = service = None
    if kind == "desktop":
        instance = _text(value["instance"], "instance", token)
        owner = _repository(value["ownerRepository"], "ownerRepository")
        owner_task_id = _text(value["ownerTaskId"], "ownerTaskId", token)
        marker_path = _path(value["markerPath"], "markerPath")
        service = _text(value["service"], "service", r"actions\.runner\.[A-Za-z0-9_.-]+\.service")
    labels = value["labels"]
    if not isinstance(labels, list) or not labels:
        raise ProfileError("labels must be a nonempty explicit CI allowlist")
    for label in labels:
        _text(label, "label", token)
        if label.casefold() in {"self-hosted", "linux", "x64"}:
            raise ProfileError("labels must contain custom scheduling labels only")
        if kind == "desktop" and (
            not re.search(r"(^|-)ci(-|$)", label, re.IGNORECASE)
            or re.search(r"(^|-)(deploy|deployment|cd|localcluster|localsinglenode)(-|$)", label, re.IGNORECASE)
        ):
            raise ProfileError("desktop profiles permit CI labels only, never deployment labels")
    if kind == "desktop" and (
        len(labels) != 2
        or sum(label.endswith("-desktop") for label in labels) != 1
        or sum(label.endswith("-canary") for label in labels) != 1
    ):
        raise ProfileError("desktop profiles require one production label and one separate canary label")
    if len({label.casefold() for label in labels}) != len(labels):
        raise ProfileError("duplicate scheduling label")
    runner_root = _path(value["runnerRoot"], "runnerRoot")
    workspace = _path(value["workspaceRoot"], "workspaceRoot")
    if workspace == runner_root or not workspace.is_relative_to(runner_root):
        raise ProfileError("workspaceRoot must be inside its runnerRoot")
    endpoint = _text(value["dockerEndpoint"], "dockerEndpoint")
    if not endpoint.startswith("unix://"):
        raise ProfileError("Docker endpoint must be an explicit local Unix socket")
    _path(endpoint.removeprefix("unix://"), "Docker socket")
    paths = {field: _path(value[field], field)
             for field in ("dockerDataRoot", "reportRoot", "temporaryRoot")}
    roots = value["capacityRoots"]
    if not isinstance(roots, list) or not roots:
        raise ProfileError("capacityRoots must be nonempty")
    capacities = []
    for root in roots:
        root = _object(root, {"path", "minimumFreeBytes", "minimumFreePercent", "minimumFreeInodePercent"}, "capacity root")
        capacities.append(CapacityRoot(
            _path(root["path"], "capacity path"),
            _integer(root["minimumFreeBytes"], "minimumFreeBytes", 1),
            _integer(root["minimumFreePercent"], "minimumFreePercent", 1, 100),
            _integer(root["minimumFreeInodePercent"], "minimumFreeInodePercent", 1, 100),
        ))
    capacity_paths = [root.path for root in capacities]
    required_paths = {workspace, paths["dockerDataRoot"], paths["reportRoot"], paths["temporaryRoot"]}
    if len(set(capacity_paths)) != len(capacity_paths) or not required_paths.issubset(capacity_paths):
        raise ProfileError("capacity roots must cover each actual workspace, Docker, report and temporary path exactly")
    return RunnerProfile(
        _text(value["id"], "id", token), kind,
        instance, owner, owner_task_id, repository, name,
        _text(value["expectedHost"], "expectedHost", r"[A-Za-z0-9][A-Za-z0-9.-]*"),
        tuple(labels), runner_root, workspace, marker_path, service, endpoint,
        _text(value["dockerId"], "dockerId", r"[A-Za-z0-9][A-Za-z0-9:-]*"),
        paths["dockerDataRoot"], paths["reportRoot"], paths["temporaryRoot"], tuple(capacities),
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def parse_profiles(text: str) -> dict[str, RunnerProfile]:
    try:
        document = json.loads(text, object_pairs_hook=_unique_object)
    except (TypeError, json.JSONDecodeError) as error:
        raise ProfileError("invalid CI profiles JSON") from error
    document = _object(document, {"schemaVersion", "profiles"}, "CI profiles document")
    if type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1:
        raise ProfileError("unsupported CI profiles schema version")
    if not isinstance(document["profiles"], list) or not document["profiles"]:
        raise ProfileError("profiles must be nonempty")
    profiles = [parse_profile(value) for value in document["profiles"]]
    for field in ("id", "runner_name", "runner_root", "workspace_root"):
        if len({getattr(profile, field) for profile in profiles}) != len(profiles):
            raise ProfileError(f"profiles have conflicting {field}")
    for index, left in enumerate(profiles):
        for right in profiles[index + 1:]:
            if left.runner_root.is_relative_to(right.runner_root) or right.runner_root.is_relative_to(left.runner_root):
                raise ProfileError("runner installations must not overlap")
    desktops = [profile for profile in profiles if profile.kind == "desktop"]
    if len({profile.repository for profile in desktops}) != len(desktops):
        raise ProfileError("a repository may use only one desktop profile")
    for field in ("instance", "marker_path", "service"):
        if len({getattr(profile, field) for profile in desktops}) != len(desktops):
            raise ProfileError(f"desktop profiles have conflicting {field}")
    return {profile.id: profile for profile in profiles}


def load_profiles(*, config_path: Path | None = None, config_json_env: str | None = None) -> dict[str, RunnerProfile]:
    """Load profiles from one explicit file or environment variable.

    CI may supply the private profile document as a secret environment value so
    workflow steps do not need to persist its host and installation details.
    The environment value is removed after reading so child processes do not
    inherit it. The document itself is never included in validation errors.
    """
    if (config_path is None) == (config_json_env is None):
        raise ProfileError("exactly one CI profiles source is required")
    if config_json_env is not None:
        _text(config_json_env, "config JSON environment variable", r"[A-Z_][A-Z0-9_]*")
        text = os.environ.pop(config_json_env, "")
        if not text:
            raise ProfileError("CI profiles environment variable is empty")
    else:
        assert config_path is not None
        text = config_path.read_text(encoding="utf-8")
    return parse_profiles(text)


def select_profile(profiles: dict[str, RunnerProfile], profile_id: str) -> RunnerProfile:
    try:
        return profiles[profile_id]
    except (KeyError, TypeError) as error:
        raise ProfileError("unknown or missing selected CI profile") from error


def verify_runtime(
    profile: RunnerProfile, *, repository: str, runner_name: str, runner_os: str,
    hostname: str, workspace: str, docker_endpoint: str, docker_info: dict[str, Any],
) -> None:
    if (repository, runner_name, runner_os, hostname) != (
        profile.repository, profile.runner_name, "Linux", profile.expected_host,
    ):
        raise ProfileError("runtime repository, runner, OS or host does not match the selected profile")
    if not _path(workspace, "runtime workspace").is_relative_to(profile.workspace_root):
        raise ProfileError("runtime workspace is outside the selected profile")
    if not isinstance(docker_info, dict) or docker_endpoint != profile.docker_endpoint or (
        docker_info.get("ID"), docker_info.get("DockerRootDir"), docker_info.get("OSType")
    ) != (profile.docker_id, str(profile.docker_data_root), "linux"):
        raise ProfileError("Docker endpoint or daemon identity does not match the selected profile")
