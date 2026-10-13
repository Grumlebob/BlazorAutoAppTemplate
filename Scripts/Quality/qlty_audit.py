"""Pinned, native Qlty maintainability analysis without linter plugins or cloud uploads."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile
import time
from urllib.request import urlopen
import uuid
import zipfile


def extract_binary(archive, expected_sha256, destination):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Qlty archive SHA-256 mismatch; binary was not executed.")
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as package:
            names = [name for name in package.namelist() if Path(name).name == "qlty.exe"]
            if len(names) != 1:
                raise ValueError("Qlty archive must contain exactly one executable.")
            contents = package.read(names[0])
    else:
        with tarfile.open(archive, "r:xz") as package:
            members = [member for member in package.getmembers() if member.isfile() and Path(member.name).name == "qlty"]
            if len(members) != 1:
                raise ValueError("Qlty archive must contain exactly one executable.")
            contents = package.extractfile(members[0]).read()
    # Copy only the expected file; never extract archive paths, links or permissions.
    destination.write_bytes(contents)
    destination.chmod(0o755)


def _download_archive(archive, package, remaining):
    if archive.exists():
        return
    try:
        with urlopen(package["url"], timeout=min(30, remaining())) as response, archive.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                remaining()
                output.write(chunk)
    except BaseException:
        archive.unlink(missing_ok=True)
        raise


def _qlty_package(settings):
    machine = "x86_64" if platform.machine().lower() in ("amd64", "x86_64") else platform.machine()
    platform_key = f"{platform.system()}-{machine}"
    if platform_key not in settings["archives"]:
        raise ValueError("The pinned Qlty audit supports Windows x64 and Linux x64.")
    package = settings["archives"][platform_key]
    return platform_key, package


def _ensure_qlty_binary(repo, version, platform_key, package, remaining):
    cache = repo / "TestResults" / "QualityTools" / "tools" / version / platform_key
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / ("qlty.zip" if platform.system() == "Windows" else "qlty.tar.xz")
    binary = cache / ("qlty.exe" if platform.system() == "Windows" else "qlty")
    _download_archive(archive, package, remaining)
    extract_binary(archive, package["sha256"], binary)
    return binary


def summarize_sarif(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("version") != "2.1.0" or not data.get("runs"):
        raise ValueError("Qlty did not produce valid SARIF.")
    counts = Counter()
    groups = set()
    for run in data["runs"]:
        if run.get("tool", {}).get("driver", {}).get("name", "").lower() != "qlty":
            raise ValueError("SARIF tool identity is not Qlty.")
        if "results" not in run:
            raise ValueError("Qlty SARIF is missing results.")
        for result in run["results"]:
            counts[result["ruleId"]] += 1
            if result["ruleId"] in ("qlty:similar-code", "qlty:identical-code"):
                locations = result.get("locations", []) + result.get("relatedLocations", [])
                group = tuple(sorted((location["physicalLocation"]["artifactLocation"]["uri"],
                                      location["physicalLocation"]["region"]["startLine"],
                                      location["physicalLocation"]["region"]["endLine"]) for location in locations))
                groups.add((result["ruleId"], group))
    return {"findingsByRule": dict(sorted(counts.items())), "reportedLocations": sum(counts.values()),
            "duplicationGroups": len(groups)}


def analysis_environment():
    # Never inherit worktree overrides into the disposable Git repository.
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(QLTY_TELEMETRY="off", NO_COLOR="1")
    return environment


def run_qlty_audit(args, git, snapshot_source):
    if args.target or args.network:
        raise ValueError("Qlty analyzes tracked source and does not accept a target or Docker network.")
    repo = args.repo_root.resolve()
    settings = json.loads(Path(__file__).with_name("audit-tools.json").read_text())["qlty"]
    platform_key, package = _qlty_package(settings)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    reports = repo / "TestResults" / "QualityTools" / run_id
    reports.mkdir(parents=True)
    summary = {"schema": 1, "tool": "qlty", "version": settings["version"], "archiveSha256": package["sha256"],
               "sha": git(repo, "rev-parse", "HEAD").decode().strip(),
               "dirty": bool(git(repo, "status", "--porcelain")),
               "startedUtc": datetime.now(timezone.utc).isoformat(), "status": "error"}
    started = time.monotonic()
    deadline = started + args.timeout_minutes * 60

    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise subprocess.TimeoutExpired("qlty audit", args.timeout_minutes * 60)
        return seconds

    try:
        binary = _ensure_qlty_binary(repo, settings["version"], platform_key, package, remaining)
        with tempfile.TemporaryDirectory(prefix="quality-qlty-") as temporary, (reports / "tool.log").open("wb") as log:
            source = Path(temporary)
            summary["source"] = snapshot_source(repo, source)
            if not (source / ".qlty/qlty.toml").is_file():
                raise ValueError("Stage .qlty/qlty.toml before running the tracked-source audit.")
            # Git overrides may refer to the invoking worktree (especially through WSL).
            # They must never redirect initialization or analysis out of the disposable copy.
            environment = analysis_environment()
            subprocess.run(["git", "-C", str(source), "init", "--quiet"], stdout=log, stderr=log,
                           env=environment, timeout=remaining(), check=True)
            for name, command in (
                ("metrics.txt", ["metrics", "--all", "--exclude-tests", "--sort", "complexity", "--limit", "30"]),
                ("qlty.sarif", ["smells", "--all", "--no-snippets", "--sarif"]),
            ):
                with (reports / name).open("wb") as output:
                    result = subprocess.run([str(binary), "--no-upgrade-check", *command], cwd=source,
                                            env=environment, stdout=output, stderr=log, timeout=remaining(), check=False)
                summary["toolExitCode"] = result.returncode
                if result.returncode or not (reports / name).stat().st_size:
                    raise ValueError(f"Qlty {command[0]} failed or returned no report; see tool.log.")
            summary["results"] = summarize_sarif(reports / "qlty.sarif")
            summary["status"] = "completed"
    except subprocess.TimeoutExpired:
        summary["status"] = "timeout"
        summary["error"] = f"Audit exceeded {args.timeout_minutes} minutes."
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, zipfile.BadZipFile, tarfile.TarError) as error:
        summary["error"] = str(error)
    finally:
        summary["durationSeconds"] = round(time.monotonic() - started, 2)
        (reports / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['status']}: {reports / 'summary.json'}")
    return 0 if summary["status"] == "completed" else 1
