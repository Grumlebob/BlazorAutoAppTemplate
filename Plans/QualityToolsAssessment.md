# Quality tools assessment and integration

## Objective and decisions

Assess Playwright accessibility testing, ZAP, Semgrep, Trivy, Qlty, sitespeed.io and scc against ImprovedDb and BlazorAutoAppTemplate. Add tools that provide distinct useful evidence to both repositories.

The operator selected on-demand informational reports, then clarified that fast PR checks are also acceptable when they provide real value. Keep the scans on demand initially: browser scans require a running target, and the initial Trivy result does not justify another mandatory PR gate. Run the audit runner's fast regression checks in CI. Keep existing Playwright/axe, SonarQube, Lighthouse, format/lint checks and Dependabot. Add Trivy source/image scans, a ZAP passive baseline, sitespeed.io and scc. Defer Semgrep and Qlty for the documented language-support and overlap reasons in [QualityTools.md](../docs/Quality/QualityTools.md).

Work is isolated in task worktrees in each repository. ImprovedDb task identity: `QUALITY-TOOLS-20261012`. No deployment is required: these are local development tools and CI regression checks, with no production behavior change. No deployment configuration or shared service is modified.

## Implementation

- One portable Python entry point using official Docker images pinned by digest in a separate manifest.
- Local ignored reports, checkout identity and duration, with informational findings distinguished from execution errors.
- Tracked working source copied into a temporary read-only mount; no private Git directory, ignored data or untracked secrets mounted.
- Explicit public web targets and immutable image targets, with bounded runs and cleanup of only the invocation's own container.
- Seven fast regression tests cover source isolation, target validation, malformed/missing reports, finding interpretation, timeout cleanup and Docker cleanup failure detection.
- Shared runner, pins and tests are identical in both repositories. Existing browser and SonarQube implementations are reused.

## Verification and integration

Measurements and exact integration evidence will be recorded in the PR description after local verification. The first ImprovedDb Trivy source audit completed in 63.26 seconds, reported no dependency vulnerabilities in scanned manifests, and reported one low severity Dockerfile misconfiguration. This is not proof of complete runtime or transitive dependency coverage.

The first scc audit included model metadata and plan evidence, which dominated the line count. The final command limits the inventory to code extensions and excludes migration/vendor directories; comparisons must use those same filters.

Browser smoke audits use a disposable static HTTP fixture. They validate tool execution and report handling, not either application's accessibility, security or performance. Application checks remain the documented opt-in browser journeys and audits against a disposable app.

Measured wall times on the developer PC, excluding the separately completed first browser image downloads:

| Audit | ImprovedDb | Template | Evidence |
| --- | --- | --- | --- |
| Trivy tracked source | 63.26 s | 25.40 s | One low severity `DS-0026` (missing Dockerfile HEALTHCHECK) in each repository; no reported dependency vulnerabilities in the scanned manifests |
| scc with final code filters | 5.17 s | 4.24 s | Per-file code inventory; model JSON and plan evidence excluded by the extension filter |
| ZAP baseline | 32.06 s | Verified separately | JSON/HTML/Markdown reports; fixture warnings preserved as informational findings |
| sitespeed.io | 58.91 s | Verified separately | HTML report and three Chrome samples |
| Trivy immutable runtime base image | 24.25 s | Shared implementation | Public ASP.NET 10 runtime base image: five low and nine medium vulnerability records, no high or critical records; not an application image audit |

Windows and WSL source execution were exercised. Runner regression tests pass in under one second. Local verification includes ImprovedDb's coordinated restore/format gate, quality-report tests, deployment audit, and linting of the changed workflow. The template's full local gate passes, including BlazorAuto (211 passed, 13 expected skips) and React (203 passed, 13 expected skips), release/observability checks, template rendering, YAML, shell and workflow linting. The Windows .NET commands mirror the profile validation script sequentially to avoid mixing Linux and Windows build outputs.

Completion requires green required CI on each exact PR head, squash integration, verification on `origin/main`, and worktree closeout. The template also requires green exact-main CI. Integrated SHAs, final checks and deleted branch tips belong in the PR descriptions.
