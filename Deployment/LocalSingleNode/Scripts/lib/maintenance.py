"""Delete only proven, old repository images; preserve every container image and all volumes.

App images older than APP_IMAGE_MAX_AGE are removed unless a container, the current release, the verified
current or recovery pin or an active deployment still references them. Release payload images are only
needed while a deployment extracts them (they are pulled by digest and copied into file pins), so this
app's own payload images older than PAYLOAD_IMAGE_MAX_AGE are removed too. Everything runs under the
shared deployment lock, so no deployment extracts a payload meanwhile.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from ls_settings import ROOT, command, runner_app, settings

sys.path.insert(0, str(ROOT / "Deployment/Common/Scripts/Component/lib"))
import pin_release_payload
from release_status import protected_application_image_references


def protected_references():
    pin_release_payload._require_shared_lock()
    status = json.loads(command(sys.executable, str(ROOT / "Deployment/LocalSingleNode/Scripts/release-status.py")))
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    return protected_application_image_references(
        status, repository=repository,
        app_image=os.environ.get("APP_IMAGE", ""),
    )


APP_IMAGE_MAX_AGE = timedelta(hours=48)
PAYLOAD_IMAGE_MAX_AGE = timedelta(hours=24)


def repository_of(reference):
    """Return the repository part of an image reference such as repo:tag or repo@sha256:digest."""
    name = reference.split("@", 1)[0]
    last = name.rsplit("/", 1)[-1]
    if ":" in last:
        name = name[: len(name) - len(last)] + last.split(":", 1)[0]
    return name


def is_payload_reference(reference, app_image):
    """True for this app's release payload repository: <parent>/<app>-release-payload or <parent>/<prefix>-<app>-release-payload."""
    parent, app_name = app_image.rsplit("/", 1)
    repository = repository_of(reference)
    if "/" not in repository:
        return False
    ref_parent, ref_name = repository.rsplit("/", 1)
    suffix = f"{app_name}-release-payload"
    return ref_parent == parent and (ref_name == suffix or ref_name.endswith("-" + suffix))


def payload_candidates(images, containers, release, now, protected_refs=()):
    protected = {container["Image"] for container in containers}
    source = release["source_repo_url"].rstrip('/')
    result = []
    for image in images:
        if image["Id"] in protected:
            continue
        refs = (image.get("RepoTags") or []) + (image.get("RepoDigests") or [])
        if not refs or set(refs).intersection(protected_refs):
            continue
        labels = image.get("Config", {}).get("Labels") or {}
        source_proven = labels.get("org.opencontainers.image.source", "").rstrip('/').casefold() == source.casefold()
        if not source_proven or not all(is_payload_reference(ref, release["image"]) for ref in refs):
            continue
        created = datetime.fromisoformat(image["Created"].replace('Z', '+00:00'))
        if now - created > PAYLOAD_IMAGE_MAX_AGE:
            result.append(image["Id"])
    return result


def candidates(images, containers, release, now, protected_refs=()):
    protected = {container["Image"] for container in containers}
    result = []
    for image in images:
        if image["Id"] in protected:
            continue
        if release["image"] + "@" + release["digest"] in (image.get("RepoDigests") or []):
            continue
        labels = image.get("Config", {}).get("Labels") or {}
        refs = (image.get("RepoTags") or []) + (image.get("RepoDigests") or [])
        if set(refs).intersection(protected_refs):
            continue
        source = release["source_repo_url"].rstrip('/')
        repository = source.removeprefix("https://github.com/")
        source_proven = labels.get("org.opencontainers.image.source", "").rstrip('/').casefold() == source.casefold()
        ci_proven = labels.get("localcluster.ci.repository", "").casefold() == repository.casefold() and labels.get("localcluster.ci.owner") == "ci-build"
        references_proven = bool(refs) and all(ref.split('@')[0].rsplit(':', 1)[0] == release["image"] or ref.split('@')[0] == release["image"] for ref in refs)
        belongs = (source_proven or ci_proven) and references_proven
        # Removing an ID with multiple tags requires force. Preserve it for inspection.
        if len(image.get("RepoTags") or []) > 1:
            print("Report only: image has multiple tags; no forced removal " + image["Id"])
            continue
        created = datetime.fromisoformat(image["Created"].replace('Z', '+00:00'))
        if belongs and now - created > APP_IMAGE_MAX_AGE:
            result.append(image["Id"])
        elif not refs:
            print("Report only: unreferenced image lacks repository ownership proof " + image["Id"])
    return result


def main():
    config = settings()
    root = Path(config["deploy_root"])
    release = json.loads((root / "release.json").read_text())
    # Resolve both release pins and pending targets before any image mutation.
    protected_refs = protected_references()
    # A successful backup must be recent before cleanup starts.
    timestamp = datetime.fromisoformat((Path(config["backup_root"]) / "last-success").read_text().strip())
    now = datetime.now(timezone.utc)
    if timestamp > now + timedelta(minutes=5) or now - timestamp > timedelta(hours=36):
        raise ValueError("Backup timestamp is invalid or older than 36 hours")
    ids = command("docker", "ps", "-aq").splitlines()
    containers = json.loads(command("docker", "inspect", *ids)) if ids else []
    ids = list(dict.fromkeys(command("docker", "image", "ls", "-aq", "--no-trunc").splitlines()))
    images = json.loads(command("docker", "image", "inspect", *ids)) if ids else []
    for image in candidates(images, containers, release, now, protected_refs):
        current = json.loads(command("docker", "image", "inspect", image))
        if image not in candidates(current, [], release, now, protected_references()):
            continue
        # Recheck all container references immediately before removing without --force.
        used = command("docker", "ps", "-aq", "--filter", "ancestor=" + image)
        if used:
            print("Image acquired a container reference; leaving it: " + image)
            continue
        command("docker", "image", "rm", image)
        print("Removed proven old app image " + image)
    for image in payload_candidates(images, containers, release, now, protected_refs):
        current = json.loads(command("docker", "image", "inspect", image))
        if image not in payload_candidates(current, [], release, now, protected_references()):
            continue
        if command("docker", "ps", "-aq", "--filter", "ancestor=" + image):
            print("Payload image acquired a container reference; leaving it: " + image)
            continue
        # Untag each owned payload tag without force; remove a digest-only image by its ID.
        for tag in current[0].get("RepoTags") or []:
            command("docker", "image", "rm", tag)
        if subprocess.run(["docker", "image", "inspect", image], capture_output=True, check=False).returncode == 0:
            command("docker", "image", "rm", image)
        print("Removed proven old release payload image " + image)
    residue = subprocess.run(["bash", str(ROOT / "Deployment/Common/Scripts/prune-actions-runner-residue.sh"), "--runner-root", "/home/deploy/actions-runner-" + runner_app(), "--defer-if-skipped"], check=False)
    if residue.returncode:
        return residue.returncode if residue.returncode in (1, 2, 75) else 1
    print("Dangling volumes (report only):")
    print(command("docker", "volume", "ls", "--filter", "dangling=true"))
    print(command("df", "-h", "/opt"))
    print(command("df", "-i", "/opt"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
