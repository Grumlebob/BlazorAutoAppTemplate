#!/usr/bin/env python3
"""Run bounded, informational quality audits. See docs/Quality/QualityTools.md."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
import uuid


TOOLS = ("trivy-source", "trivy-image", "zap", "sitespeed", "scc", "qlty")


def git(repo, *arguments):
    return subprocess.check_output(["git", "-C", str(repo), *arguments])


def snapshot_source(repo, destination):
    """Copy tracked working files only; never follow links into local data."""
    copied = 0
    skipped = []
    for raw in git(repo, "ls-files", "--cached", "-z").split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw))
        source = repo / relative
        if source.is_symlink() or not source.is_file():
            skipped.append(relative.as_posix())
            continue
        if not source.resolve().is_relative_to(repo):
            raise ValueError(f"Tracked path escapes the checkout: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied += 1
    if not copied:
        raise ValueError("No tracked source files were found.")
    return {"trackedFilesCopied": copied, "skippedPaths": skipped}


def validate_target(tool, target):
    if tool in ("zap", "sitespeed"):
        _validate_web_target(target)
    elif tool == "trivy-image":
        _validate_image_target(target)
    elif target:
        raise ValueError(f"{tool} scans this checkout and does not accept --target.")


def _validate_web_target(target):
    url = urlsplit(target or "")
    if url.scheme not in ("http", "https") or not url.hostname:
        raise ValueError("Web audits require --target with an absolute HTTP(S) URL.")
    if url.username or url.password or url.query or url.fragment:
        raise ValueError("Use a public URL without credentials, query strings or fragments.")
    if url.hostname in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Container loopback is not the host; use host.docker.internal or a Docker service name.")


def _validate_image_target(target):
    digest_marker = "@sha256:"
    if not target or target.startswith("-") or digest_marker not in target:
        raise ValueError("Image audits require --target registry/image@sha256:<digest>.")
    digest = target.rsplit(digest_marker, 1)[1]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Image target must contain a full lowercase SHA-256 digest.")


def validate_image_archive(tool, image_archive):
    if image_archive is None:
        return None
    if tool != "trivy-image":
        raise ValueError("--image-archive is supported only by trivy-image.")
    archive = Path(image_archive)
    if archive.is_symlink():
        raise ValueError("Image archives must be regular files, not symbolic links.")
    try:
        archive = archive.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"Image archive does not exist: {archive}") from error
    if not archive.is_file() or archive.stat().st_size == 0:
        raise ValueError(f"Image archive must be a non-empty file: {archive}")
    return archive


def image_archive_metadata(archive):
    digest = hashlib.sha256()
    byte_count = 0
    with archive.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            byte_count += len(chunk)
    return {"fileName": archive.name, "sha256": digest.hexdigest(), "byteCount": byte_count}


def tool_command(tool, target, image_archive=None):
    if tool == "trivy-source":
        return ["fs", "--scanners", "vuln,misconfig,secret", "--format", "json",
                "--output", "/reports/trivy.json", "--exit-code", "0", "/src"]
    if tool == "trivy-image":
        command = ["image", "--scanners", "vuln", "--format", "json",
                   "--output", "/reports/trivy.json", "--exit-code", "0"]
        if image_archive is not None:
            return command + ["--input", "/image/image.tar"]
        return command + [target]
    if tool == "zap":
        return ["zap-baseline.py", "-t", target, "-m", "1", "-T", "5",
                "-J", "zap.json", "-r", "zap.html", "-w", "zap.md"]
    if tool == "sitespeed":
        return [target, "--browser", "chrome", "--browsertime.headless", "true",
                "--browsertime.iterations", "3", "--outputFolder", "/reports/sitespeed"]
    return ["scc", "--format", "json", "--by-file", "--no-cocomo",
            "--include-ext", "cs,razor,py,js,ts,tsx,jsx,ps1,psm1,sh,css",
            "--exclude-dir", "Migrations,lib,node_modules",
            "--output", "/reports/scc.json", "/src"]


def _build_docker_command(args, repo, reports, source, container, image, summary):
    command = ["docker", "run", "--rm", "--pull", "never", "--name", container,
               "--cpus", "2", "--memory", "4g", "--shm-size", "1g"]
    if os.name != "nt":
        command += ["--user", f"{os.getuid()}:{os.getgid()}", "--env", "HOME=/tmp"]
    report_mount = "/zap/wrk" if args.tool == "zap" else "/reports"
    command += ["--mount", f"type=bind,source={reports},target={report_mount}"]
    if args.tool in ("trivy-source", "scc"):
        summary["source"] = snapshot_source(repo, source)
        command += ["--mount", f"type=bind,source={source},target=/src,readonly"]
    if args.tool == "scc":
        command += ["--network", "none"]
    elif args.network:
        command += ["--network", args.network]
    if args.tool in ("zap", "sitespeed"):
        command += ["--add-host", "host.docker.internal:host-gateway"]
    image_archive = validate_image_archive(args.tool, getattr(args, "image_archive", None))
    if image_archive is not None:
        command += [
            "--mount",
            f"type=bind,source={image_archive},target=/image/image.tar,readonly",
        ]
    command += [image, *tool_command(args.tool, args.target, image_archive)]
    return command


def remove_container(name):
    result = subprocess.run(["docker", "rm", "--force", name], capture_output=True,
                            text=True, timeout=20, check=False)
    if result.returncode and "No such container:" not in (result.stderr or ""):
        raise ValueError(f"Could not confirm container cleanup: {name}")


def read_results(tool, report_dir, exit_code):
    """Require reports even when a tool returns zero; findings are not failures."""
    report = report_dir / {
        "trivy-source": "trivy.json", "trivy-image": "trivy.json",
        "zap": "zap.json", "scc": "scc.json", "sitespeed": "sitespeed/index.html",
    }[tool]
    accepted = (0, 1, 2) if tool == "zap" else (0,)
    if exit_code not in accepted:
        raise ValueError(f"{tool} failed with exit code {exit_code}; see tool.log.")
    if not report.is_file() or not report.stat().st_size:
        raise ValueError(f"{tool} did not produce its required report: {report.name}")
    if tool == "sitespeed":
        return {"report": "sitespeed/index.html", "iterations": 3}
    data = json.loads(report.read_text(encoding="utf-8-sig"))
    if tool.startswith("trivy"):
        return _summarize_trivy(data)
    if tool == "zap":
        return _summarize_zap(data)
    return _summarize_scc(data)


def _summarize_trivy(data):
    if not isinstance(data, dict) or data.get("SchemaVersion") != 2 or not data.get("ArtifactName"):
        raise ValueError("Trivy returned an invalid report.")
    counts = Counter()
    for result in data.get("Results", []):
        for family in ("Vulnerabilities", "Misconfigurations", "Secrets"):
            for finding in result.get(family, []):
                counts[f"{family}:{finding.get('Severity', 'UNKNOWN')}"] += 1
    return {"findings": dict(sorted(counts.items())), "targets": len(data.get("Results", []))}


def _summarize_zap(data):
    if not isinstance(data, dict) or not data.get("site"):
        raise ValueError("ZAP did not report any scanned site.")
    counts = Counter()
    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            counts[alert["riskdesc"]] += 1
    return {"alerts": dict(sorted(counts.items()))}


def _summarize_scc(data):
    if not isinstance(data, list) or not data:
        raise ValueError("scc returned an empty or invalid inventory.")
    return {"languages": len(data), "files": sum(row["Count"] for row in data),
            "codeLines": sum(row["Code"] for row in data),
            "complexity": sum(row["Complexity"] for row in data)}


def run_audit(args):
    image_archive = validate_image_archive(args.tool, getattr(args, "image_archive", None))
    if args.tool == "qlty":
        if __package__:
            from .qlty_audit import run_qlty_audit
        else:
            from qlty_audit import run_qlty_audit
        return run_qlty_audit(args, git, snapshot_source)
    repo = args.repo_root.resolve()
    validate_target(args.tool, args.target)
    archive_metadata = image_archive_metadata(image_archive) if image_archive is not None else None
    tool_key = args.tool.split("-", 1)[0]
    settings = json.loads((Path(__file__).with_name("audit-tools.json")).read_text())
    image = settings[tool_key]["image"]
    if "@sha256:" not in image:
        raise ValueError("Audit images must be pinned by digest.")
    sha = git(repo, "rev-parse", "HEAD").decode().strip()
    dirty = bool(git(repo, "status", "--porcelain"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    reports = repo / "TestResults" / "QualityTools" / run_id
    reports.mkdir(parents=True)
    container = "quality-audit-" + uuid.uuid4().hex
    cleanup_complete = False
    summary = {"schema": 1, "tool": args.tool, "version": settings[tool_key]["version"],
               "image": image, "sha": sha, "dirty": dirty, "target": args.target,
               "startedUtc": datetime.now(timezone.utc).isoformat(), "status": "error"}
    if archive_metadata is not None:
        summary["imageArchive"] = archive_metadata
    started = time.monotonic()
    deadline = started + args.timeout_minutes * 60

    def execute(command, log):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, args.timeout_minutes * 60)
        return subprocess.run(command, stdout=log, stderr=log, timeout=remaining, check=False)

    try:
        with (reports / "tool.log").open("wb") as log:
            if execute(["docker", "pull", image], log).returncode:
                raise ValueError("Could not pull the pinned image; see tool.log.")
            with tempfile.TemporaryDirectory(prefix="quality-source-") as temporary:
                source = Path(temporary)
                command = _build_docker_command(args, repo, reports, source, container, image, summary)
                try:
                    result = execute(command, log)
                finally:
                    # Stop before releasing the temporary source mount, including on timeout.
                    remove_container(container)
                    cleanup_complete = True
                summary["toolExitCode"] = result.returncode
                summary["results"] = read_results(args.tool, reports, result.returncode)
                summary["status"] = "completed"
    except subprocess.TimeoutExpired:
        summary["status"] = "timeout"
        summary["error"] = f"Audit exceeded {args.timeout_minutes} minutes."
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        summary["error"] = str(error)
    finally:
        # The name is unique to this invocation. Never stop other containers or prune volumes.
        try:
            if not cleanup_complete:
                remove_container(container)
        except (OSError, ValueError, subprocess.SubprocessError):
            summary["status"] = "error"
            summary["cleanupWarning"] = f"Could not confirm container cleanup: {container}"
        summary["durationSeconds"] = round(time.monotonic() - started, 2)
        (reports / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['status']}: {reports / 'summary.json'}")
    return 0 if summary["status"] == "completed" and "cleanupWarning" not in summary else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=TOOLS)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--target", help="Container-reachable public URL, or immutable registry image reference.")
    parser.add_argument(
        "--image-archive",
        type=Path,
        help="Read-only Docker-save tar for trivy-image; --target must still identify its immutable registry digest.",
    )
    parser.add_argument("--network", help="Existing Docker network for a disposable local app.")
    parser.add_argument("--timeout-minutes", type=int, choices=range(1, 61), default=15, metavar="1..60")
    args = parser.parse_args()
    try:
        return run_audit(args)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Audit could not start: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
