#!/usr/bin/env python3
"""Read-only verification of an explicitly configured Linux CI runner."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import subprocess
import sys

try:
    from Scripts.CI.runner_profiles import ProfileError, RunnerProfile, load_profiles, select_profile, verify_runtime
except ModuleNotFoundError:
    from runner_profiles import ProfileError, RunnerProfile, load_profiles, select_profile, verify_runtime


def canonical_directory(value: PurePosixPath | str) -> Path:
    path = Path(str(value))
    try:
        resolved = path.resolve(strict=True)
        if resolved != path or not path.is_dir() or resolved == Path("/mnt") or Path("/mnt") in resolved.parents:
            raise ProfileError(f"CI directory is linked, noncanonical or Windows-mounted: {path}")
    except OSError as error:
        raise ProfileError(f"CI directory is unavailable: {path}") from error
    return path


def mount_for(path: Path, mountinfo: Path = Path("/proc/self/mountinfo")) -> dict:
    def decode(value: str) -> str:
        return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), value)

    candidates = []
    device = path.stat().st_dev
    expected_device = f"{os.major(device)}:{os.minor(device)}"
    for line in mountinfo.read_text(encoding="utf-8").splitlines():
        before, separator, after = line.partition(" - ")
        fields, filesystem = before.split(), after.split()
        if not separator or len(fields) < 6 or len(filesystem) < 3:
            raise ProfileError("Linux mount information is malformed")
        target = Path(decode(fields[4]))
        if fields[2] == expected_device and (path == target or target in path.parents):
            candidates.append(dict(mountId=fields[0], device=fields[2], target=str(target),
                                   filesystem=filesystem[0], source=decode(filesystem[1])))
    if not candidates:
        raise ProfileError(f"Cannot identify the actual filesystem for {path}")
    longest = max(len(Path(item["target"]).parts) for item in candidates)
    matches = [item for item in candidates if len(Path(item["target"]).parts) == longest]
    if len(matches) != 1:
        raise ProfileError(f"Ambiguous filesystem identity for {path}")
    selected = matches[0]
    if selected["filesystem"].casefold() in {"9p", "drvfs", "ntfs", "ntfs3", "fuseblk", "vfat", "cifs", "smb3"}:
        raise ProfileError(f"CI path is not on an approved Linux filesystem: {path}")
    return selected


def inspect_capacity(profile: RunnerProfile) -> dict:
    """Validate every configured path; combine identical filesystems for reporting."""
    canonical_directory(profile.runner_root)
    filesystems = {}
    for root in profile.capacity_roots:
        path = canonical_directory(root.path)
        mount = mount_for(path)
        space = os.statvfs(path)
        if min(space.f_blocks, space.f_frsize, space.f_files) <= 0 or min(space.f_bavail, space.f_favail) < 0:
            raise ProfileError(f"Filesystem byte or inode capacity is unavailable: {path}")
        available = space.f_bavail * space.f_frsize
        byte_percent = 100 * space.f_bavail / space.f_blocks
        inode_percent = 100 * space.f_favail / space.f_files
        if (available < root.minimum_free_bytes or byte_percent < root.minimum_free_percent
                or inode_percent < root.minimum_free_inode_percent):
            raise ProfileError(f"CI path does not meet its byte/inode reserve: {path}")
        identity = (mount["device"], mount["filesystem"], mount["source"])
        observation = filesystems.setdefault(identity, dict(
            device=mount["device"], filesystem=mount["filesystem"], source=mount["source"], paths=[],
            availableBytes=available, freePercent=byte_percent, freeInodePercent=inode_percent,
        ))
        observation["availableBytes"] = min(observation["availableBytes"], available)
        observation["freePercent"] = min(observation["freePercent"], byte_percent)
        observation["freeInodePercent"] = min(observation["freeInodePercent"], inode_percent)
        observation["paths"].append(dict(
            path=str(path), mountId=mount["mountId"], minimumFreeBytes=root.minimum_free_bytes,
            minimumFreePercent=root.minimum_free_percent, minimumFreeInodePercent=root.minimum_free_inode_percent,
            availableBytes=available, freePercent=byte_percent, freeInodePercent=inode_percent,
        ))
    return dict(result="passed", profile=profile.id, filesystems=list(filesystems.values()))


def safe_capacity_summary(report: dict, runner_id: int) -> dict:
    """Return useful capacity evidence without exposing configured mount paths."""
    filesystems = report["filesystems"]
    return dict(
        result=report["result"], profile=report["profile"], runnerId=runner_id,
        rootsChecked=sum(len(filesystem["paths"]) for filesystem in filesystems),
        filesystems=[dict(
            availableBytes=filesystem["availableBytes"],
            freePercent=round(filesystem["freePercent"], 2),
            freeInodePercent=round(filesystem["freeInodePercent"], 2),
        ) for filesystem in filesystems],
    )


def verify_local_registration(profile: RunnerProfile, selected_label: str | None = None,
                              expected_runner_id: int | None = None) -> int:
    if selected_label is not None and selected_label not in profile.labels:
        raise ProfileError("Selected scheduling label is outside the profile allowlist")
    if expected_runner_id is not None and (type(expected_runner_id) is not int or expected_runner_id < 1):
        raise ProfileError("Selected registration ID must be a positive integer")
    root = canonical_directory(profile.runner_root)
    registration_path = root / ".runner"
    if registration_path.is_symlink() or not registration_path.is_file():
        raise ProfileError("Local runner registration is missing or linked")
    registration = json.loads(registration_path.read_text(encoding="utf-8-sig"))
    if (not isinstance(registration, dict) or type(registration.get("agentId")) is not int
            or registration["agentId"] < 1 or registration.get("agentName") != profile.runner_name
            or str(registration.get("gitHubUrl", "")).rstrip("/").casefold() != f"https://github.com/{profile.repository}".casefold()):
        raise ProfileError("Local runner registration ID/name/repository does not match the selected profile")
    if expected_runner_id is not None and registration["agentId"] != expected_runner_id:
        raise ProfileError("Local runner registration differs from the selected API registration ID")
    work = registration.get("workFolder")
    if (not isinstance(work, str) or not work or PurePosixPath(work).is_absolute()
            or ".." in PurePosixPath(work).parts or profile.runner_root / work != profile.workspace_root):
        raise ProfileError("Local runner work folder differs from the selected profile")
    canonical_directory(profile.workspace_root)
    if profile.kind == "desktop":
        assert profile.marker_path is not None and profile.service is not None
        marker_path = Path(str(profile.marker_path))
        if marker_path.resolve(strict=True) != marker_path or not marker_path.is_file():
            raise ProfileError("Runner ownership marker is missing, linked or noncanonical")
        info = marker_path.stat()
        if info.st_uid != 0 or info.st_gid != 0 or stat.S_IMODE(info.st_mode) != 0o644:
            raise ProfileError("Runner ownership marker is not the expected root-owned file")
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            raise ProfileError("Runner ownership marker must be an object")
        if type(marker.get("runnerId")) is not int:
            raise ProfileError("Runner ownership marker must declare a numeric registration ID")
        owner = (marker.get("ownerRepository"), marker.get("ownerTaskId"))
        if owner == (None, None) and profile.repository == profile.owner_repository:
            owner = (marker.get("repository"), marker.get("taskId"))
        if owner != (profile.owner_repository, profile.owner_task_id) or (
            marker.get("repository"), marker.get("taskId"), marker.get("runnerRoot"), marker.get("runnerName"),
            marker.get("runnerId"), marker.get("serviceName"), marker.get("state"),
        ) != (
            profile.repository, profile.owner_task_id, str(profile.runner_root), profile.runner_name,
            registration["agentId"], profile.service, "service-installed",
        ):
            raise ProfileError("Runner ownership marker does not match the selected installation and registration")
        labels = marker.get("customLabels")
        if not isinstance(labels, list) or len(labels) != 1 or labels[0] not in profile.labels:
            raise ProfileError("Runner ownership marker does not declare one approved CI label")
        if selected_label is not None and labels != [selected_label]:
            raise ProfileError("Selected scheduling label differs from the owned registration marker")
    return registration["agentId"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    config = parser.add_mutually_exclusive_group(required=True)
    config.add_argument("--config", type=Path)
    config.add_argument("--config-json-env")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--runner-id", type=int)
    arguments = parser.parse_args()
    try:
        if sys.platform != "linux":
            raise ProfileError("CI runtime verification requires Linux")
        profile = select_profile(load_profiles(config_path=arguments.config,
                                               config_json_env=arguments.config_json_env), arguments.profile)
        if arguments.label not in profile.labels:
            raise ProfileError("Selected scheduling label is outside the profile allowlist")
        if os.environ.get("DOCKER_CONTEXT"):
            raise ProfileError("An explicit Docker context conflicts with the selected local socket")
        endpoint = os.environ.get("DOCKER_HOST") or "unix:///var/run/docker.sock"
        if endpoint != profile.docker_endpoint:
            raise ProfileError("Runtime Docker endpoint differs from the selected profile")
        workspace = canonical_directory(os.environ.get("GITHUB_WORKSPACE", ""))
        runner_id = verify_local_registration(profile, selected_label=arguments.label,
                                              expected_runner_id=arguments.runner_id)
        docker = subprocess.run(
            ["docker", "--host", endpoint, "info", "--format", "{{json .}}"],
            check=True, capture_output=True, text=True, timeout=30,
        )
        verify_runtime(profile, repository=os.environ.get("GITHUB_REPOSITORY", ""),
                       runner_name=os.environ.get("RUNNER_NAME", ""), runner_os=os.environ.get("RUNNER_OS", ""),
                       hostname=socket.gethostname(), workspace=str(workspace), docker_endpoint=endpoint,
                       docker_info=json.loads(docker.stdout))
        print(json.dumps(safe_capacity_summary(inspect_capacity(profile), runner_id), sort_keys=True))
        return 0
    except (ProfileError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"CI runner verification failed ({type(error).__name__}); private profile details were withheld.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
