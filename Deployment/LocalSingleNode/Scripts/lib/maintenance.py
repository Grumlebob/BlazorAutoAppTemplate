"""Delete only proven, old repository images; preserve every container image and all volumes."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

from ls_settings import ROOT, command, settings


def candidates(images, containers, release, now):
    protected = {container["Image"] for container in containers}
    result = []
    for image in images:
        if image["Id"] in protected:
            continue
        if release["image"] + "@" + release["digest"] in (image.get("RepoDigests") or []):
            continue
        labels = image.get("Config", {}).get("Labels") or {}
        refs = (image.get("RepoTags") or []) + (image.get("RepoDigests") or [])
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
        if belongs and now - created > timedelta(hours=168):
            result.append(image["Id"])
        elif not refs:
            print("Report only: unreferenced image lacks repository ownership proof " + image["Id"])
    return result


def main():
    config = settings()
    root = Path(config["deploy_root"])
    release = json.loads((root / "release.json").read_text())
    # A successful backup must be recent before cleanup starts.
    timestamp = datetime.fromisoformat((Path(config["backup_root"]) / "last-success").read_text().strip())
    now = datetime.now(timezone.utc)
    if timestamp > now + timedelta(minutes=5) or now - timestamp > timedelta(hours=36):
        raise ValueError("Backup timestamp is invalid or older than 36 hours")
    ids = command("docker", "ps", "-aq").splitlines()
    containers = json.loads(command("docker", "inspect", *ids)) if ids else []
    ids = list(dict.fromkeys(command("docker", "image", "ls", "-aq", "--no-trunc").splitlines()))
    images = json.loads(command("docker", "image", "inspect", *ids)) if ids else []
    for image in candidates(images, containers, release, now):
        # Recheck all container references immediately before removing without --force.
        used = command("docker", "ps", "-aq", "--filter", "ancestor=" + image)
        if used:
            print("Image acquired a container reference; leaving it: " + image)
            continue
        command("docker", "image", "rm", image)
        print("Removed proven old app image " + image)
    residue = subprocess.run(["bash", str(ROOT / "Deployment/Common/Scripts/prune-actions-runner-residue.sh"), "--runner-root", "/home/deploy/actions-runner-" + config["app_name"], "--defer-if-skipped"], check=False)
    if residue.returncode:
        return residue.returncode if residue.returncode in (1, 2, 75) else 1
    print("Dangling volumes (report only):")
    print(command("docker", "volume", "ls", "--filter", "dangling=true"))
    print(command("df", "-h", "/opt"))
    print(command("df", "-i", "/opt"))
    print("Recent protected backup verified")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
