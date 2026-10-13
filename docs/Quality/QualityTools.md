# Quality tool selection and operation

The additional audits run on demand and produce informational reports. Run the source checks before dependency or infrastructure work, ZAP before changing HTTP security settings, and sitespeed.io when investigating a browser performance regression. They do not block merges. The small regression tests for the audit runner run in normal CI.

## Available tools

| Tool | Use and limits |
| --- | --- |
| [Playwright with axe](https://playwright.dev/docs/accessibility-testing) | Existing accessibility checks for public React journeys fail on serious or critical violations. Automated checks cover rendered states; keyboard, focus and screen-reader review still matter. |
| [Trivy](https://github.com/aquasecurity/trivy) | Source and immutable image audits for dependency vulnerabilities, Dockerfile/Terraform misconfigurations and tracked secrets. Scan the published image for runtime dependencies beyond the source scan. |
| [ZAP](https://www.zaproxy.org/docs/docker/baseline-scan/) | Optional passive HTTP baseline and one-minute spider against a disposable public target. It does not authenticate or exercise all UI states. Crawling makes requests and can encounter routes with side effects. |
| [Qlty](https://github.com/qltysh/qlty) | Optional complexity, code smells and duplication review without a build or server. Findings require source review. Only built-in analysis is enabled, with no cloud account. Its CLI uses a BSL/Fair Source license. |
| [sitespeed.io](https://www.sitespeed.io/documentation/sitespeed.io/docker/) | Three Chrome samples with HTML reports, browser timings and request waterfalls. Compare the same data, hardware, cache state and network conditions. Start with existing Lighthouse checks. |
| [scc](https://github.com/boyter/scc) | Per-file code inventory and lexical complexity estimates, including production code, tests and scripts. Counts are planning evidence, not quality or productivity scores. |

## Run an audit

Requirements: Python 3.10+ and Git. Qlty runs natively on Windows x64 or Linux x64 and downloads a pinned official release archive from GitHub, verifies its SHA-256 before execution, and caches it under ignored `TestResults/QualityTools/tools/`. The other audits require Docker with Linux containers and network access to the pinned image registry. Trivy also downloads its vulnerability database and checks. The Docker context must refer to the local engine because the runner mounts local directories. On Windows, run these commands directly in PowerShell with Docker Desktop. Linux commands on CurrentPC must use the WSL distribution configured in the deployment inventory through a login shell.

```powershell
python Scripts/Quality/run_quality_audit.py trivy-source
python Scripts/Quality/run_quality_audit.py scc
python Scripts/Quality/run_quality_audit.py qlty
python Scripts/Quality/run_quality_audit.py trivy-image --target "ghcr.io/owner/app@sha256:<full-image-digest>"
python Scripts/Quality/run_quality_audit.py zap --target "http://host.docker.internal:8080/"
python Scripts/Quality/run_quality_audit.py sitespeed --target "http://host.docker.internal:8080/"
```

Replace the example URL with the disposable app's actual address and port. For an app on an existing Docker network, use `--network <network-name> --target http://<service-name>:<port>/`. Container `localhost` is the audit container, not the app or host. On Linux, a host app must listen on a container-reachable interface. A self-signed HTTPS certificate can fail a browser run; use a trusted certificate or the disposable app's HTTP endpoint. The runner does not disable certificate checks.

`trivy-image` reads an immutable image from a registry without mounting the Docker socket. Public pulls work directly. Private registry authentication is deliberately not copied from the host; arrange an appropriate authorized scan environment separately.

The default deadline is 15 minutes, including image pulls. Override it with `--timeout-minutes 1` through `60`. Each Docker invocation uses a unique container name, a limit of two CPUs and 4 GiB of memory, and 1 GiB of shared memory. The first pull of a browser image can be large; subsequent runs reuse Docker's image cache. Trivy databases are downloaded per run, so include that cost when deciding whether to automate scans.

## Scope and reports

Reports are local and ignored by Git:

```text
TestResults/QualityTools/<UTC-time>-<unique-id>/
  summary.json
  tool.log
  trivy.json | scc.json | qlty.sarif + metrics.txt | zap.json + zap.html + zap.md | sitespeed/index.html
```

The summary records the checkout SHA, dirty state, tool version, immutable audit image or Qlty archive checksum, target where applicable, elapsed time, tool exit code and result counts. Findings are informational: exit `0` means the tool completed and its required report exists. ZAP's finding exit codes `1` and `2` are recorded and interpreted as completed scans. Startup failures, missing or malformed reports, tool errors, cleanup failures and timeouts return `1`; they must not be interpreted as clean scans.

Source tools receive a temporary copy of files tracked in Git, using their current working contents. Docker mounts this copy read-only. Qlty initializes a disposable Git repository inside its copy; the original checkout and its Git metadata are untouched. Stage new source paths before auditing them. Untracked files, ignored local data, build output and private Git metadata are not mounted. Tracked symlinks and deleted files are skipped and listed in the summary. Consequently this is a tracked-source audit, not a Git-history secret scan or a scan of locally installed dependencies. Trivy's [NuGet coverage](https://trivy.dev/docs/latest/coverage/language/dotnet/) distinguishes direct versions in `Directory.Packages.props` from transitive dependencies in `packages.lock.json` or runtime `*.deps.json` files.

Keep raw reports private. Security findings can contain source snippets and browser reports can contain target content or URLs. Review and redact them before sharing. The runner prints only the summary path, uploads nothing, deletes its temporary source copy and removes only its own container for Docker audits. It does not prune images or volumes. A force-killed runner can leave its uniquely named `quality-audit-*` container; verify ownership before removing it.

## Interpret Qlty reports

`metrics.txt` lists the 30 production files with the highest complexity. `qlty.sarif` lists maintainability findings and paired locations for similar or identical code. `.qlty/qlty.toml` excludes generated, vendored and evidence directories and identifies test directories. The summary counts reported locations and also deduplicates mirrored duplication pairs into groups; neither number is a defect count.

Duplication may be intentional; inspect paired locations before extracting shared behavior. Analyzer disagreement does not establish accuracy. SonarQube remains the source for coverage and broader source findings.

Qlty runs `metrics` and `smells` only, with telemetry and upgrade checks disabled. It does not run `check`, formatting, plugins, or cloud uploads. Native runs use the same deadline but do not have Docker CPU or memory limits. Prefer this fast optional review before considering a PR gate; review noise and usefulness on real changes first.

## Accessibility and other existing checks

Use the existing axe helper in a browser journey after the relevant state has loaded. Install the client lockfile first with `npm --prefix BlazorAutoApp.Client ci`. Public React tests use the `Category=ReactPublicBroad` filter. Follow [Test.md](../Test.md) for setup and guards.

Useful existing tools are worth keeping: SonarQube for source findings and coverage, Dependabot for dependency updates, `dotnet format` for C# formatting/analyzers, actionlint for workflows and ShellCheck for shell scripts. If source secret scanning proves useful but misses historical leaks, evaluate a separate Gitleaks history audit. Do not add a second secret scanner to every PR merely to duplicate Trivy.

## Maintain the integration

`Scripts/Quality/audit-tools.json` pins official upstream images by digest and Qlty release archives by SHA-256. Update both Qlty platform archives and their checksums together, and exercise native Windows and Linux runs. A cached archive with an incorrect checksum fails; remove that specific cache archive before downloading it again. Update the version and digest together, verify the registry manifest and run a smoke audit before committing. scc's upstream image uses a rolling `master` tag; the selected digest was verified to run scc 4.1.0, and the runner never resolves that rolling tag.

Run the fast runner checks with:

```powershell
python -m unittest Scripts.Quality.tests.test_run_quality_audit -v
```

They exercise source isolation, URL and image validation, report failures, informational findings and timeout cleanup, Qlty archive verification, SARIF validation, duplication grouping and Git environment isolation without pulling images or contacting a target.
