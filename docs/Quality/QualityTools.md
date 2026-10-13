# Optional quality audits

The on-demand audits below produce reports for review and do not block merges. Their runner regression tests run in CI. Use [SonarQube](SonarQubeAnalysis.md) for source findings and coverage.

## Available tools

| Tool | Use and limit |
| --- | --- |
| [Trivy](https://github.com/aquasecurity/trivy) | Audits tracked source and immutable images for vulnerabilities, configuration issues, and secrets. Image scans cover runtime dependencies. |
| [ZAP](https://www.zaproxy.org/docs/docker/baseline-scan/) | Runs a passive baseline and short spider against a disposable HTTP target. It does not authenticate; crawling can reach routes with side effects. |
| [Qlty](https://github.com/qltysh/qlty) | Reviews source complexity, code smells, and duplication. Findings need source review. Built-in analysis only; CLI uses a BSL/Fair Source license. |
| [sitespeed.io](https://www.sitespeed.io/documentation/sitespeed.io/docker/) | Collects three Chrome timing samples and request waterfalls. Compare runs under the same conditions. |
| [scc](https://github.com/boyter/scc) | Counts code and estimates lexical complexity. Use counts for planning, not as quality or productivity scores. |

The React public Chromium suite includes axe assertions and runs in CI; it is separate from this audit runner. For local browser setup, see [React public browser checks](../Testing/Browser.md#react-public-browser-checks). Install the client lockfile with `npm --prefix BlazorAutoApp.Client ci` so axe is available.

## Run an audit

Run PowerShell commands from the repository root. Python 3.10+, Git, and Docker with Linux containers are required. Qlty also runs natively on Windows x64 or Linux x64; the runner verifies its pinned archive checksum. Pinned images, versions, and checksums are in [`Scripts/Quality/audit-tools.json`](../../Scripts/Quality/audit-tools.json). Accepted tools and options are declared in [`run_quality_audit.py`](../../Scripts/Quality/run_quality_audit.py).

```powershell
python Scripts/Quality/run_quality_audit.py trivy-source
python Scripts/Quality/run_quality_audit.py scc
python Scripts/Quality/run_quality_audit.py qlty
python Scripts/Quality/run_quality_audit.py trivy-image --target "ghcr.io/owner/app@sha256:<full-image-digest>"
python Scripts/Quality/run_quality_audit.py trivy-image --target "ghcr.io/owner/app@sha256:<full-image-digest>" --image-archive "/path/to/verified-docker-save.tar"
python Scripts/Quality/run_quality_audit.py zap --target "http://host.docker.internal:8080/"
python Scripts/Quality/run_quality_audit.py sitespeed --target "http://host.docker.internal:8080/"
```

Use a disposable app for ZAP and sitespeed. Replace the example URL with its actual container-reachable address. Pass `--network <name>` when the app uses an existing Docker network; container `localhost` refers to the audit container. On Linux, the host app must listen on an interface reachable from Docker. A self-signed HTTPS certificate can fail browser scans; use a trusted certificate or the app's HTTP endpoint. The runner never disables certificate checks.

`trivy-image` requires an immutable digest in `--target`. By default it reads that image from a registry without mounting the Docker socket. Public pulls work directly; private registry credentials are not copied from the host. For a private image, use `--image-archive` with a non-empty Docker-save tar created by an authorized environment after pulling the target by digest. The wrapper mounts the archive read-only and records its SHA-256 and byte count beside the requested digest. The caller must preserve evidence that the archive came from that digest.

The default timeout is 15 minutes, including image pulls. Set `--timeout-minutes 1` through `60` to change it. Docker audits use a unique container, two CPUs, 4 GiB memory, and 1 GiB shared memory. The first browser-image pull can be large. Trivy downloads its vulnerability database for each run.

## Reports and cleanup

Reports are local and ignored by Git:

```text
TestResults/QualityTools/<UTC-time>-<unique-id>/
  summary.json
  tool.log
  trivy.json | scc.json | qlty.sarif + metrics.txt | zap.json + zap.html + zap.md | sitespeed/index.html
```

The summary records checkout SHA, dirty state, tool version, target, image archive hash and size, elapsed time, exit code, and result counts. Exit `0` means the required report exists. ZAP finding exit codes `1` and `2` are recorded as completed scans. Startup failures, malformed reports, cleanup failures, and timeouts return `1`; do not treat them as clean scans.

Source tools use current working contents of Git-tracked files in a temporary copy mounted read-only. Stage new source paths before scanning. Untracked files, ignored data, build output, Git history, and installed dependencies are outside the scan. Tracked symlinks and deleted files are skipped and listed. Qlty creates a disposable Git repository inside its copy; the original checkout stays untouched.

Keep reports private. They can contain source snippets, target content, and URLs. The runner uploads nothing, removes its temporary source copy, and removes only its own audit container. It never prunes images or volumes. After forced termination, verify ownership before removing a leftover `quality-audit-*` container.

`metrics.txt` ranks production files by complexity. `qlty.sarif` contains maintainability findings and paired duplication locations. The summary counts locations and groups mirrored pairs; neither is a defect count. Review paired source before extracting shared code. Qlty runs `metrics` and `smells`, with telemetry and upgrade checks disabled. It does not run formatting, plugins, or cloud uploads.
