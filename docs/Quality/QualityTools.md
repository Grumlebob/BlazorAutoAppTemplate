# Quality tool selection and operation

The additional audits run on demand and produce informational reports. Run the source checks before dependency or infrastructure work, ZAP before changing HTTP security settings, and sitespeed.io when investigating a browser performance regression. They do not block merges. The small regression tests for the audit runner run in normal CI.

## Selection

| Tool | Decision for ImprovedDb and the template | Reason and limits |
| --- | --- | --- |
| [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing) with axe | Keep the existing implementation | Both repositories already install axe-core and have Playwright helpers that check WCAG 2 A/AA and 2.1 A/AA rules. ImprovedDb checks browse filters, toolbar and front-page states; the template checks public React journeys. Existing assertions fail on serious or critical violations. Automated scans cover only the rendered state and cannot establish full accessibility compliance; keyboard, focus and screen-reader review still matter. |
| [Trivy](https://github.com/aquasecurity/trivy) | Add source and immutable image audits | Finds dependency vulnerabilities, Dockerfile/Terraform misconfigurations and tracked secrets. This covers areas outside the SonarQube source analysis. Source scans inspect central NuGet versions and npm lockfiles. They do not establish complete runtime or transitive NuGet coverage; scan the published image too. |
| [ZAP](https://www.zaproxy.org/docs/docker/baseline-scan/) | Add an optional baseline audit | Adds passive HTTP security checks and a one-minute traditional spider. No active scan is configured. Use a disposable local or staging target with public pages. It does not authenticate, exercise all Blazor/React states, or establish application security. Crawling still makes requests and can encounter routes with side effects. |
| [Semgrep](https://docs.semgrep.dev/semgrep-ce-languages) | Defer | The CE documentation lists C# support through 7.0 and single-function analysis. These .NET 10 repositories use newer language features. The commercial product's C# support must not be attributed to CE. Python/JavaScript rules could help later if a specific gap remains after SonarQube findings are reviewed. Do not introduce another broad scan without evidence of useful unique findings. |
| [Qlty](https://github.com/qltysh/qlty) | Defer | Its C# offering lists complexity and duplication. It also orchestrates tools such as Semgrep and Trivy. SonarQube and the existing format/lint checks already cover much of that role. Another configuration layer adds maintenance without a demonstrated gap. Its CLI uses a BSL/Fair Source license, rather than a conventional open source license. |
| [sitespeed.io](https://www.sitespeed.io/documentation/sitespeed.io/docker/) | Add an optional investigation audit | Three Chrome samples produce HTML reports, browser timings and request waterfalls. Use it for comparisons under the same conditions. Existing Lighthouse and application performance tests remain the faster starting points. Do not invent universal timing budgets or compare different data, hardware, cache states or network profiles. |
| [scc](https://github.com/boyter/scc) | Add an optional inventory audit | Produces a fast per-file code inventory and lexical complexity estimates without a Sonar server. Counts code extensions only and excludes migrations, vendored `lib` directories and node_modules. Includes production code, tests and scripts. Counts are planning evidence, not quality scores or developer productivity measures. |

The current selection favors tools that add distinct evidence. PR scanning remains an option if measured findings justify it. The initial Trivy baseline produced one low severity Dockerfile finding in about one minute, so a new mandatory scan is not justified yet. ZAP and sitespeed.io require a running target and take longer. There is no new scheduled job, service, account or paid provider integration.

## Run an audit

Requirements: Python 3.10+, Git, Docker with Linux containers, and network access to the pinned image registry. Trivy also downloads its vulnerability database and checks. The Docker context must refer to the local engine because the runner mounts local directories. On Windows, run these commands directly in PowerShell with Docker Desktop. Linux commands on CurrentPC must use the WSL distribution configured in the deployment inventory through a login shell.

```powershell
python Scripts/Quality/run_quality_audit.py trivy-source
python Scripts/Quality/run_quality_audit.py scc
python Scripts/Quality/run_quality_audit.py trivy-image --target "ghcr.io/owner/app@sha256:<full-image-digest>"
python Scripts/Quality/run_quality_audit.py zap --target "http://host.docker.internal:8080/"
python Scripts/Quality/run_quality_audit.py sitespeed --target "http://host.docker.internal:8080/"
```

Replace the example URL with the disposable app's actual address and port. For an app on an existing Docker network, use `--network <network-name> --target http://<service-name>:<port>/`. Container `localhost` is the audit container, not the app or host. On Linux, a host app must listen on a container-reachable interface. A self-signed HTTPS certificate can fail a browser run; use a trusted certificate or the disposable app's HTTP endpoint. The runner does not disable certificate checks.

`trivy-image` reads an immutable image from a registry without mounting the Docker socket. Public pulls work directly. Private registry authentication is deliberately not copied from the host; arrange an appropriate authorized scan environment separately.

The default deadline is 15 minutes, including image pulls. Override it with `--timeout-minutes 1` through `60`. Each invocation uses a unique container name, a limit of two CPUs and 4 GiB of memory, and 1 GiB of shared memory. The first pull of a browser image can be large; subsequent runs reuse Docker's image cache. Trivy databases are downloaded per run, so include that cost when deciding whether to automate scans.

## Scope and reports

Reports are local and ignored by Git:

```text
TestResults/QualityTools/<UTC-time>-<unique-id>/
  summary.json
  tool.log
  trivy.json | scc.json | zap.json + zap.html + zap.md | sitespeed/index.html
```

The summary records the checkout SHA, dirty state, tool version, immutable audit image, target, elapsed time, tool exit code and result counts. Findings are informational: exit `0` means the tool completed and its required report exists. ZAP's finding exit codes `1` and `2` are recorded and interpreted as completed scans. Startup failures, missing or malformed reports, tool errors, cleanup failures and timeouts return `1`; they must not be interpreted as clean scans.

Source tools receive a temporary, read-only copy of files tracked in Git, using their current working contents. Stage new source paths before auditing them. Untracked files, ignored local data, build output and private Git metadata are not mounted. Tracked symlinks and deleted files are skipped and listed in the summary. Consequently this is a tracked-source audit, not a Git-history secret scan or a scan of locally installed dependencies. Trivy's [NuGet coverage](https://trivy.dev/docs/latest/coverage/language/dotnet/) distinguishes direct versions in `Directory.Packages.props` from transitive dependencies in `packages.lock.json` or runtime `*.deps.json` files.

Keep raw reports private. Security findings can contain source snippets and browser reports can contain target content or URLs. Review and redact them before sharing. The runner prints only the summary path, uploads nothing, deletes its temporary source copy and removes only its own container. It does not prune images or volumes. A force-killed runner can leave its uniquely named `quality-audit-*` container; verify ownership before removing it.

## Accessibility and other existing checks

Use the existing axe helper in a browser journey after the relevant state has loaded. Install the client lockfile first with `npm --prefix BlazorAutoApp.Client ci`. ImprovedDb's `Scripts/RunApplicationQuality.ps1` selects the existing synthetic browser and performance layers; the template's public React tests use the `Category=ReactPublicBroad` filter. Follow each repository's `docs/Test.md` for setup and guards.

Useful existing tools are worth keeping: SonarQube for source findings and coverage, Dependabot for dependency updates, `dotnet format` for C# formatting/analyzers, actionlint for workflows and ShellCheck for shell scripts. If source secret scanning proves useful but misses historical leaks, evaluate a separate Gitleaks history audit. Do not add a second secret scanner to every PR merely to duplicate Trivy.

## Maintain the integration

`Scripts/Quality/audit-tools.json` pins official upstream images by digest. Update the version and digest together, verify the registry manifest and run a smoke audit before committing. scc's upstream image uses a rolling `master` tag; the selected digest was verified to run scc 4.1.0, and the runner never resolves that rolling tag.

Run the fast runner checks with:

```powershell
python -m unittest Scripts.Quality.tests.test_run_quality_audit -v
```

They exercise source isolation, URL and image validation, report failures, informational findings and timeout cleanup without pulling images or contacting a target. Actual scan timings and integration evidence are recorded in [the task plan](../../Plans/QualityToolsAssessment.md).
