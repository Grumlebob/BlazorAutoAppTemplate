# SonarQube On-Demand Quality Audits

Status: planning complete; implementation has not started. Two operator preferences are listed in section 12.

Created: 2026-10-11. This is an implementation plan, not authorization to deploy or to repair every reported finding.

## 1. Goal and boundaries

Add SonarQube as the template's second explicitly invoked quality tool, alongside Lighthouse. Lighthouse measures browser performance and related page quality. SonarQube inspects source code and imports test coverage. Its useful output is a measured, prioritized improvement backlog that a person or an AI can act on later.

Deliver two modes:

1. **Quick:** opt-in SonarAnalyzer C# build, without a server, producing SARIF and concise Markdown/JSON summaries.
2. **Full:** an on-demand local SonarQube Community Build, covering both frontend profiles sequentially, with coverage and durable Markdown/JSON reports.

Also deliver a read-only MCP launcher for interactive investigation. Exported reports remain the primary interface and work without any MCP client.

The following requirements are fixed by the request:

- Nothing scans on a push, pull request, ordinary build, application startup, deployment, timer, or schedule.
- Do not add a SonarQube CI workflow, GitHub secrets, PR decoration, webhook, required check, or blocking quality gate.
- Do not start SonarQube from `Scripts/RunLocal.ps1` or add it to application/observability Compose files.
- Do not put SonarQube on LocalCluster, LocalSingleNode, or Cloud. This is developer tooling.
- Keep existing `build-test-push` and all existing local checks. An informational SonarQube gate does not replace them.
- Do not run Lighthouse automatically as part of a source audit. Link the two tools in documentation and explain when each helps.
- Installing the tools does not authorize application changes to satisfy their findings. Report and triage first.

Default implementation scope ends after tooling, verified baselines, and a reviewed improvement backlog. A first remediation PR is optional and depends on the answer in section 12.

## 2. Preparation already completed

Do not redo this research unless the relevant source or dependency has changed.

### 2.1 Template facts

The inspected checkout was `9f45a7cecf3c9c98a860f09aa30a433ca8a623e5`. Remote `main` had advanced to `5b0ddf90147d2d147932dfac18f23ed93b64c285` during preparation. Start implementation from a freshly fetched `origin/main`; do not assume this plan's inspection SHA is still current.

- `Plans/` is tracked; `Plans.local/` is ignored. Some older plans incorrectly say `Plans/` is ignored. Follow current `AGENTS.md`, `Plans/README.md`, and `.gitignore`.
- There is no existing SonarQube integration in the template.
- `global.json` requests SDK `10.0.300` with `latestFeature` roll-forward. Projects target `net10.0`.
- `Directory.Packages.props` uses Central Package Management. Add a central version for a new NuGet dependency.
- `Directory.Build.props` resolves the frontend profile. `Directory.Build.targets` rejects a `FrontendProfile` environment variable. Use explicit `-p:FrontendProfile=...` arguments; never set that environment variable.
- `frontend-profile.txt` currently selects `BlazorAuto`. Both `BlazorAuto` and `React` are supported template compositions.
- Solution projects are `BlazorAutoApp`, `.Client`, `.Core`, `.Test`, and `.Simulation`. There is no ImprovedDb DataImport or ML project to copy into the scope.
- Current tracked-file inventory: 216 C# files, 73 Razor files, 39 JS/TS files, 73 Python files, 143 shell scripts, 80 `.yml` files, 6 Terraform files, 11 PowerShell scripts, and 4 CSS files. These are inventory counts, not SonarQube LOC or issue counts.
- `BlazorAutoApp.Test` uses xUnit v3 and `Microsoft.NET.Test.Sdk` `18.10.1`. Integration tests need Docker, PostgreSQL, and Redis.
- `Scripts/CI/validate-frontend-profiles.sh` restores, builds, and tests profiles sequentially. Current expectations are 211 passed / 13 expected skips for BlazorAuto, and 203 passed / 13 expected skips for React. React uses `FrontendProfile!=BlazorAuto`. Read the current script before implementing these expectations.
- The separately opted-in Testcontainers lifecycle suite expects 3 passed / 0 skipped. Full Sonar scans do not enable it or browser E2E.
- React has 31 ordinary unit tests, Vitest `5.0.3`, and no coverage provider or coverage command yet.
- React, CI, and the React Docker build pin Node `24.21.0` and npm `12.2.0`. The Blazor CSS/Lighthouse package currently allows Node `>=22.19`; do not silently change that compatibility contract in this plan.
- Lighthouse is invoked through `Scripts/RunLighthouse.ps1`, documented in `docs/Test.md`, and stores ignored reports in `TestResults/Lighthouse`.
- Generated React declarations live in `BlazorAutoApp.React/app/api/generated/schema.d.ts`; the OpenAPI snapshot is `BlazorAutoApp.React/api/openapi.json`. Generated CSS is `BlazorAutoApp/wwwroot/tailwind.css`.
- There is no template `Scripts/Coordination/DotnetCoordination.ps1` or ImprovedDb task-registration API. Do not copy calls to those helpers.

### 2.2 ImprovedDb reuse, frozen source

Use the implementation from [ImprovedDb commit `175f069fff0b2b8e8870eab704f133d217930e7d`](https://github.com/Grumlebob/ImprovedDb/tree/175f069fff0b2b8e8870eab704f133d217930e7d), rather than reconstructing it from its older plan. The relevant source files were clean when inspected.

The source is already available through this checkout's `improveddb` Git remote and through the operator-provided sibling checkout. Prefer `git show <frozen-sha>:<path>` when extracting it. Do not merge ImprovedDb history or copy its private settings.

| Source path | Reuse and required adaptation |
| --- | --- |
| `Scripts/Quality/summarize_sarif.py` | Reuse parsing, analyzer families, deduplication, and production/test/generated classification. Change schema and plan links; add frontend-profile metadata. |
| `Scripts/Quality/Invoke-SonarAnalyzerBuild.ps1` | Reuse forced rebuild and summaries. Replace the ImprovedDb process launcher; pass explicit frontend profile; record dirty state and configuration. |
| `Scripts/Quality/SonarQuality.psm1` | Reuse DPAPI, authentication, redaction, readiness polling, and argument construction. Replace project constants with resolved repository identity and per-profile keys. |
| `Scripts/Quality/SonarQubeServer.ps1` | Reuse explicit lifecycle and idempotent provisioning. Isolate Compose identity, credentials, permissions, and profiles. Repair partial-initialization handling. |
| `Scripts/Quality/Invoke-SonarAnalysis.ps1` | Reuse begin/build/test/end/task-poll structure. Add profile validation, coverage preflight, owned cleanup, immutable analysis identity, and failure-safe finalization. |
| `Scripts/Quality/sonar_report.py` | Reuse API access, pagination, ranking, and output structure. Add exact-analysis checks and explicit unavailable/truncated-data reporting. |
| `Scripts/Quality/Start-SonarQubeMcp.ps1` | Reuse stdio launcher and read-only environment flags. Resolve the template network, selected profile, token, and pinned image. |
| `Scripts/Quality/tests/` | Port both Python suites, PowerShell module checks, and sanitized fixtures. Replace application-specific paths and add the failure cases below. |
| `docker/sonarqube/compose.yaml` | Reuse standalone architecture and bounded resources. Replace names, port, and example database password. |
| `Scripts/Quality/SonarQube/SonarQube.Analysis.xml` | Reuse property-file structure only. Build exclusions from this template's files. |
| `Scripts/Quality/SonarQube/profile-overrides.json` | Reuse declarative format and reason validation. Start with empty overrides; do not inherit ImprovedDb's suppressed rules. |
| `docs/Quality/SonarQubeAnalysis.md` | Reuse topics, then rewrite commands and operational behavior for the template. |

Preparation ran ImprovedDb's existing `test_sonar_report` and `test_summarize_sarif` suites: **37 tests passed**. This validates the reuse candidates, not an implementation in this template.

Source pins worth reusing initially:

- SonarQube image: `sonarqube:26.9.0.129388-community`.
- Sonar database: `postgres:17.11-alpine3.23`.
- Scanner: `dotnet-sonarscanner` `11.3.0`.
- Optional build analyzer: `SonarAnalyzer.CSharp` `10.35.0.4138`.
- MCP image: `sonarsource/sonarqube-mcp:1.28.0.4397`.

These are observed working-source pins, not a claim that each is the newest release. Recheck compatibility and release notes before implementation; upgrade deliberately in a separate decision, never during an audit. Do not copy ImprovedDb's old claim that PostgreSQL support ends at 17: current Community Build documentation lists 14–18 from 26.2 onward. Version 17 remains a valid initial choice. See [database requirements](https://docs.sonarsource.com/sonarqube-community-build/server-installation/installing-the-database).

### 2.3 Useful compatibility research

- `@vitest/coverage-v8@5.0.3` exists in the npm registry and requires `vitest` `5.0.3`. Pin both together. Use explicitly invoked V8 coverage and include untested application files; see [Vitest coverage](https://vitest.dev/guide/coverage).
- JS and TS coverage uses `sonar.javascript.lcov.reportPaths`. Coverage must be generated before analysis upload; see [Sonar JS/TS coverage](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/test-coverage/javascript-typescript-test-coverage).
- SonarScanner for .NET does not support `sonar.sources` or `sonar.tests`. Its settings file needs an absolute path; see [scanner usage](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/scanners/dotnet/using).
- Multilanguage scanning does not prove every repository file was analyzed. C# files excluded from compilation are not analyzed by Roslyn. Inspect generated scope and server file inventory; see [scanner configuration](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/scanners/dotnet/configuring).
- ImprovedDb found an empty `dotnet-coverage` report with its xUnit v3 setup, then successfully used `dotnet test --collect "Code Coverage;Format=Xml"`. Treat this as local evidence, not a universal xUnit limitation. Prove the collector works here before adopting it. Import Microsoft XML through `sonar.cs.vscoveragexml.reportsPaths`; see [.NET coverage formats](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/test-coverage/dotnet-test-coverage).
- The official MCP supports read-only mode and selected toolsets. A token's effective permissions still need verification; see [official MCP documentation](https://github.com/SonarSource/sonarqube-mcp-server).

### 2.4 Host tooling follow-up

The operator explicitly requested host Node/npm alignment during planning. Node `24.21.0` is the current Node 24 LTS download, and npm `12.2.0` is the registry's current `latest` tag on the research date. The template pins already match them. See [Node downloads](https://nodejs.org/en/download) and [npm registry metadata](https://registry.npmjs.org/npm/latest).

Record the host installation outcome in ignored `Plans.local/SonarQubeOnDemandQuality/HostPreparation.md`. Keep actual machine paths, shell-profile backups, and local permissions out of tracked files. The implementation must still check resolved executable versions at runtime; a pinned repository does not prove a shell is using those versions.

Host alignment completed during planning using a verified user-local runtime and PowerShell activation. Existing system/global packages were preserved. Validation on fetched main passed React dependency installation, typecheck, lint, all **31 unit tests**, production build, and API contract check. No template dependency pin or application file needed changing. This runtime validation is separate from future Sonar integration acceptance.

## 3. Decisions and defaults

Defaults are executable unless the operator chooses otherwise in section 12.

1. **Hosting:** a dedicated local stack for this repository. Do not start, stop, reprovision, or reuse ImprovedDb's server by default. Its images may be reused from Docker's cache.
2. **Identity:** derive a stable namespace from normalized `origin` repository identity, not from worktree location. Use a readable repository slug plus an 8-character SHA-256 suffix for Compose names and the local secret namespace. Clones/worktrees of one repository share identity; forks have different identities.
3. **Port:** default to loopback `127.0.0.1:9200`. This is a developer-tool default, not a deployment value. Allow an ignored local override. If occupied, report it and accept an explicit alternate port; never stop the owner.
4. **State:** dedicated PostgreSQL and named SonarQube data/extensions/log/database volumes. Both services use `restart: "no"`. Normal stop preserves all history.
5. **Profiles:** use separate Sonar projects `<repository-prefix>-BlazorAuto` and `<repository-prefix>-React`. Each gets its own complete begin/build/test/end cycle and history. Never upload two competing compositions to one project or add unsupported PR/branch parameters.
6. **Default audit:** analyze both frontend profiles sequentially from the same fetched `origin/main` SHA. Allow an explicit single-profile run. Resolve `Selected` through `frontend-profile.txt` if supported; never infer profile from installed assets.
7. **Experiments:** branch, dirty, or tests-skipped scans use separate scratch project keys. They never replace either trusted main baseline. First version may omit experiments entirely; it must reject unsafe baseline replacement.
8. **Secrets:** Windows PowerShell 7 with DPAPI for the initial full-scan implementation. Generate admin, database, analysis, and reader credentials automatically. Tokens are scoped by project/profile; reader permissions are limited to the two owned projects.
9. **Other operating systems:** Python report tests and ordinary app builds remain cross-platform. Document Windows-only credential provisioning clearly. Do not invent a Linux plaintext fallback. Cross-platform secrets are a later enhancement.
10. **Tool isolation:** install the pinned scanner into a per-user versioned tool directory only when explicitly requested. Do not add scanner restoration to ordinary application tooling. Preserve the root EF tool manifest.
11. **Quality profiles:** use built-in Sonar way initially. Add reviewed, declarative overrides only after real template findings justify them. Do not import ImprovedDb's application-specific ignores.
12. **Failure semantics:** scanner, test, coverage, processing, identity, secret-hygiene, and export failures return nonzero. Sonar's red/failed quality gate remains an informational finding and does not fail an otherwise complete audit.
13. **Shutdown:** the high-level command stops a dedicated server that it started, even after failure, unless `-KeepServerRunning` was explicitly requested. Leave a previously running server running. Verify ownership while holding the lifecycle/run lock.
14. **Reports:** write ignored run artifacts, then archive sanitized reports outside temporary worktrees before removing them. Retain selected compact evidence as Markdown. Do not commit raw source excerpts or JSON dumps by default.
15. **Scope:** analyze shared C#, the active frontend, hand-authored CSS/JS/TS, Python helpers, and supported infrastructure/secrets inputs. Do not promise general PowerShell or Bash semantic analysis; existing analyzers remain necessary.

## 4. Files to produce

Use these paths unless an existing implementation discovered during Phase 0 already provides the same function.

```text
Scripts/Quality/Invoke-CodeQualityAudit.ps1
Scripts/Quality/Invoke-SonarAnalyzerBuild.ps1
Scripts/Quality/Invoke-SonarAnalysis.ps1
Scripts/Quality/SonarQuality.psm1
Scripts/Quality/SonarQubeServer.ps1
Scripts/Quality/Start-SonarQubeMcp.ps1
Scripts/Quality/summarize_sarif.py
Scripts/Quality/sonar_report.py
Scripts/Quality/SonarQube/SonarQube.Analysis.xml
Scripts/Quality/SonarQube/profile-overrides.json
Scripts/Quality/SonarQube/tool-versions.json
Scripts/Quality/quality-settings.example.json
Scripts/Quality/tests/                           # adapted tests and sanitized fixtures
docker/sonarqube/compose.yaml
docs/Quality/SonarQubeAnalysis.md
Plans/Support/SonarQubeOnDemandQuality/Baseline.md
Plans/CodeQualityImprovements.md
```

Modify `Directory.Build.props`, `Directory.Packages.props`, `.gitignore`, React `package.json`, React `package-lock.json`, React `vitest.config.ts`, `README.md`, `docs/Test.md`, and `docs/HowToForkThisRepo.md`. Add only offline quality-tool tests to the existing CI validation job if appropriate.

Add ignore rules for `.sonarqube/`, `Scripts/Quality/quality-settings.local.json`, and any additional output not already covered by `artifacts/` or React `coverage/` rules. The example settings file contains a schema, a loopback port, and optional non-secret identity/toolchain overrides. Actual machine tool paths belong only in ignored local settings. Credentials never appear in either settings file.

Do not modify application Dockerfiles, deployment settings, production assets, or the root EF manifest merely to install this tool.

## 5. Execution instructions

Read `AGENTS.md`, `docs/Requirements.md`, `docs/Test.md`, and this plan first. Run one phase at a time. Each task has an observable completion condition. Do not mark a task complete because a file exists without its verification.

Use a dedicated implementation worktree and a PR. Keep .NET build/test processes sequential in each checkout. Use explicit staging paths. Do not stash/reset other work, prune Docker volumes, reclaim deployment locks, force-push `main`, or dispatch a deployment.

### Phase 0 — Establish the current baseline

- [ ] **0.1 Fetch and isolate.** Fetch `origin`, record its current `main` SHA, and create a uniquely named feature worktree/branch. Leave the primary checkout and other tasks unchanged. Verification: `git status --porcelain` is empty in the new worktree, and the branch starts at the recorded SHA.
- [ ] **0.2 Recheck relevant contracts.** Read the current profile resolver, profile test script, test project, dependency manifests, and workflow. Record any differences from section 2. Verification: the execution record names actual package versions and current test expectations.
- [ ] **0.3 Verify executable resolution.** Check PowerShell 7, Python, .NET, Docker Linux containers, Node, and npm. Require Node/npm pins for React analysis. Use a verified per-user runtime if necessary; no administrator installation is required for the planned workflow. Verification: subprocesses launched by the audit resolve the intended Node and npm, not merely the parent terminal.
- [ ] **0.4 Check ownership and resources.** Inspect only Sonar-related Compose projects, the selected loopback port, available Docker memory, and required images. Do not start or inspect credentials from ImprovedDb. Verification: selected namespace is distinct and its port is available or explicitly overridden.
- [ ] **0.5 Capture ordinary builds.** Restore/build both frontend profiles sequentially before changing tooling. Save warning counts and package graphs. Run the existing profile gate if a fresh baseline is needed; do not invent altered skip expectations. Verification: no Sonar package/analyzer or scanner state exists in ordinary build inputs.
- [ ] **0.6 Freeze reuse input.** Extract the section 2 source files from the frozen ImprovedDb commit to ignored scratch space. Preserve relative fixture paths. Verification: copied files match that commit, and no `.env`, `.clixml`, local MCP config, or deployment identity was copied.

### Phase 1 — Shared identity, process execution, and safety helpers

- [ ] **1.1 Implement settings resolution.** Read tracked defaults and optional ignored local settings. Normalize HTTPS and SSH `origin` URLs to the same owner/repository identity. Strip embedded credentials before any error/log output. Validate project keys, Compose names, and loopback URLs. Verification: fixtures for HTTPS, SSH, trailing `.git`, worktrees, two forks, and missing/invalid origin produce deterministic results or actionable errors.
- [ ] **1.2 Implement scoped process execution.** Replace `Invoke-ImprovedDbDotnetSequence` with a small template helper using explicit executable paths, argument arrays, exit codes, stdout/stderr capture, and timeouts. Preserve real command arguments; display only redacted arguments. Verification: a deliberately failing or timed-out child does not continue to the next step.
- [ ] **1.3 Implement run ownership.** Use a per-repository cross-process lock around a full batch and server lifecycle changes. Record owner/run identifiers. Do not silently reclaim a lock held by another process. Coordinate nested helpers without taking the same non-reentrant lock twice. Verification: a second audit fails clearly or waits within a bounded timeout; a stop request cannot interrupt an active audit.
- [ ] **1.4 Harden cleanup paths.** Resolve all target paths before deleting anything. Only remove scanner directories or worktrees created by this run. An existing unknown `.sonarqube` directory causes an actionable failure, not automatic recursive deletion. Verification: an unrelated sentinel directory/file survives success, failure, and timeout cleanup.
- [ ] **1.5 Implement output hygiene.** Redact secrets before output can reach the console or retained logs. Sanitize caught API exceptions, process arguments, summaries, and diagnostic tails. Restore temporarily changed environment variables to their original values. Verification: synthetic token sentinels appear nowhere in captured public output, including failure paths.
- [ ] **1.6 Establish schemas.** Use stable template schema identifiers such as `blazorautoapp.sonar-report/1` and `blazorautoapp.sonar-analysis-run/1`. Add repository identity and frontend profile fields. Verification: no `improveddb.*` schema or obsolete remediation-plan link remains.

### Phase 2 — Quick C# analyzer mode

- [ ] **2.1 Add conditional package wiring.** Pin `SonarAnalyzer.CSharp` centrally. Add its `PackageReference` only when `RunSonarAnalyzers=true`, with `PrivateAssets=all`. Keep all existing frontend-resolution properties. Verification: a normal restore has no `SonarAnalyzer.CSharp/` package entry in its assets; opt-in restore does.
- [ ] **2.2 Add opt-in SARIF paths.** Set `ErrorLog` to a run/profile/project-specific `.sarif` path and create its directory before compilation. Never write different profiles into the same SARIF file. Verification: forced builds produce fresh, nonempty parseable SARIF for expected projects.
- [ ] **2.3 Port the summarizer.** Preserve production/test/generated separation, family counts, high-signal findings, deduplication, normalized paths, and bounded Markdown. Record profile, SHA, dirty state, and configuration. Verification: adapted fixture tests pass and Windows paths with spaces normalize correctly.
- [ ] **2.4 Implement the quick driver.** Support `-FrontendProfile BlazorAuto|React|Both` with `Both` default, sequential builds, `--no-incremental`, bounded timeouts, and explicit arguments. It may inspect a dirty working tree because it does not overwrite server history, but must label it. Verification: no Docker start, HTTP Sonar API call, coverage run, or MCP process occurs.
- [ ] **2.5 Prevent mode overlap.** A full scan rejects `RunSonarAnalyzers=true`; the quick driver rejects active scanner state. Test lowercase/case-insensitive environment resolution as appropriate to Windows/MSBuild. Verification: neither combination reaches a build with both analyzer sets enabled.
- [ ] **2.6 Prove default isolation.** Restore/build normally after the opt-in build for each profile. Verification: ordinary warnings match the baseline, default assets no longer contain the optional package, and no persistent analyzer hook changes ordinary builds.

### Phase 3 — Dedicated on-demand server

- [ ] **3.1 Create standalone Compose.** Use the pinned source images, a private network, internal-only PostgreSQL, loopback Sonar port, named volumes, `restart: "no"`, log rotation, readiness checks, and bounded memory. Do not use application database volumes. Verification: rendered Compose contains only two owned services and one loopback published port; no `latest` tag or external DB port exists.
- [ ] **3.2 Generate database credentials.** Replace ImprovedDb's literal `sonar` password with a generated local secret. Persist it with DPAPI before the first boot and supply it through the process environment. Never change it automatically on an existing DB. Verification: password values are absent from tracked files and logs; a second start uses the same secret.
- [ ] **3.3 Port lifecycle commands.** Provide `-Start`, `-Stop`, `-Status`, `-Logs`, `-Start -Initialize`, and `-Start -ApplyProfile`. Validate mutually exclusive flags. `-Stop` uses scoped Compose stop and keeps volumes. Verification: no action starts Docker services unless explicitly selected, and stop affects only this repository's stack.
- [ ] **3.4 Implement bounded readiness.** Poll `/api/system/status`; distinguish unreachable, starting, down, and migration-required states. Do not hide database migration behind an endless wait. Verification: failed readiness reports an actionable state and a scoped log command.
- [ ] **3.5 Rotate the default admin password.** Generate and encrypt credentials on fresh owned state. Design the password change/persistence sequence to recover from partial failure without losing the new credential. Unknown existing credentials cause a stop, never volume deletion. Verification: second initialization authenticates without rotating the password or creating duplicate state.
- [ ] **3.6 Provision two private projects.** Create the per-profile projects and configure their new-code definition. Generate a project analysis token for each. Start with inherited Sonar way profiles and empty reviewed overrides. Verification: project names, visibility, permissions, and profile associations are correct; repeated initialization creates no duplicate project/token/profile.
- [ ] **3.7 Provision a reader account.** Grant browse/code-view access only for owned projects. Check inherited group permissions: removing explicit write grants alone does not prove read-only access. Remove unintended analysis/admin rights using the supported API. Verification: reader queries succeed and a harmless permission-check probe proves writes/analysis are denied.
- [ ] **3.8 Verify persistence and isolation.** Stop/restart the owned stack and reinitialize. Compare project IDs, token presence, volume names, and analysis history. Verification: data survives, no new credentials are issued unnecessarily, and ImprovedDb resources retain their previous state.

### Phase 4 — Coverage and profile-specific scan scope

- [ ] **4.1 Prove C# coverage before upload.** Run a small known test with `--collect "Code Coverage;Format=Xml"` using the actual xUnit/Test SDK setup. Parse the XML, find production source paths, and require covered executable lines. Verification: a collector missing or producing an empty report fails preflight. If needed, add a compatible `Microsoft.CodeCoverage` reference centrally to the test project and rerun; do not install an unrelated collector blindly.
- [ ] **4.2 Preserve real suite validation.** Reuse the current TRX validator and expectations from `Scripts/CI/validate-frontend-profiles.sh`. Put reports in unique profile/run directories. Keep E2E and lifecycle opt-ins off. Verification: failed, missing, extra-skipped, or empty tests prevent scanner `end`.
- [ ] **4.3 Add opt-in React coverage.** Pin `@vitest/coverage-v8` to the current exact Vitest version and regenerate the lockfile with pinned npm. Add `test:coverage` using `vitest run --coverage`; keep ordinary `npm test` without coverage. Configure `lcov` plus a human-readable/JSON summary reporter. Verification: normal tests still pass without creating coverage; the explicit command produces nonempty LCOV.
- [ ] **4.4 Define an honest React denominator.** Include `app/**/*.{ts,tsx}` so untested app modules count. Exclude tests, `app/test/**`, generated declarations, and `.typecheck.ts` fixtures. Do not exclude ordinary components or routes because they have low coverage. Verification: an untested real source file appears with zero hits rather than disappearing.
- [ ] **4.5 Normalize LCOV paths.** Run npm in the React package, inspect actual `SF:` entries, and normalize only if they do not map to repository-root files. Configure `sonar.javascript.lcov.reportPaths` to this run's absolute report path. Verification: server coverage for a named tested React module agrees with LCOV; there are no unresolved-source warnings.
- [ ] **4.6 Build common exclusions.** Exclude `.git`, `bin`, `obj`, node dependencies, build/coverage/test outputs, plan artifacts, generated declarations/OpenAPI snapshots, generated Tailwind, EF generated migrations, ignored runtime data, and actual secrets/local inventories. Keep handwritten app CSS, infrastructure, and helper sources. Verification: inspect a generated-file sample and a handwritten-file sample on the server; generated output is absent, handwritten input remains.
- [ ] **4.7 Adapt profile exclusions.** BlazorAuto excludes `BlazorAutoApp.React/**`. React excludes the Blazor client source and inactive Blazor account/component inputs; use actual current composition rules, not a guess that a solution/test reference will keep them out. Shared backend and hosting code remain visible in each project. Verification: compare expected source inventory with scanner output and the server's file tree for each profile.
- [ ] **4.8 Define coverage-only exclusions.** Keep helpers/deployment/simulation visible for issue analysis while excluding only justified, currently unmeasured sources from coverage. Record the reason for each exclusion. Do not exclude `Program.cs`, all Razor, all TSX, or all production files merely to improve percentages. Verification: report clearly distinguishes excluded coverage from zero coverage and unavailable coverage.
- [ ] **4.9 Check language support honestly.** Enable `sonar.scanner.scanAll=true` and UTF-8. Generate React Router types/typecheck inputs before analysis if required by its TSConfig. Verify C#, Razor source locations, TS/TSX, handwritten CSS, Python, Dockerfile, and supported IaC examples. Verification: record actual analyzed files/languages and unsupported inputs; language totals alone are insufficient.

### Phase 5 — Reliable full-scan driver

- [ ] **5.1 Install the pinned scanner explicitly.** Read `tool-versions.json`, install/reuse `dotnet-sonarscanner` at an absolute per-user versioned path, and validate its version. Fail if a mismatched executable occupies that path. Verification: normal EF tooling and app CI do not download or invoke this scanner.
- [ ] **5.2 Establish immutable run identity.** Require a clean audit worktree at the wrapper's pinned SHA. Record full SHA, project, frontend profile, UTC times, tool/server versions, settings digest, and coverage/test mode before starting. Verification: a dirty tree, unexpected ref, or mismatched profile fails before `begin`.
- [ ] **5.3 Prepare React inputs outside scanner instrumentation.** For React, run `npm ci`, API contract check, typecheck, and explicit coverage before scanner begin. These helpers can invoke .NET; keep them outside the begin/end window. Run every child with the pinned toolchain. Verification: no unrelated .NET build occurs inside an active scan and no committed generated file changes.
- [ ] **5.4 Execute one profile sequence.** Run `begin`, explicit-profile restore, forced Release build, same-profile `dotnet test --no-build --no-restore` with TRX and XML coverage, then validate all outputs. Use absolute settings and `sonar.projectBaseDir` for the worktree root. Do not use unsupported `sonar.sources`/`sonar.tests`. Verification: only a complete validated sequence reaches `end`.
- [ ] **5.5 Upload and bind processing identity.** Run `end`, read `report-task.txt`, poll that exact `ceTaskId`, and retain the returned `analysisId`. Treat `FAILED`, `CANCELED`, and timeout as failures. Verification: the run points to a successful exact task, not merely a currently green dashboard.
- [ ] **5.6 Bind gate and reports to the analysis.** Query gate status by `analysisId`. Check server analysis revision/version/project against the pinned run before and after exporting mutable latest-view endpoints. Hold the project/run lock through export. If an outside scan changes latest state, fail or retry explicitly; never label its results with this run's SHA. Verification: a simulated concurrent analysis cannot produce a falsely attributed report.
- [ ] **5.7 Finalize on every path.** Use `try/catch/finally` for environment restoration, log sanitization, owned scanner cleanup, process shutdown, lock release, and a final summary. Avoid `exit` bypassing cleanup inside helper functions. Verification: forced build/test/end/export/time-out failures each retain a truthful summary and release owned resources.
- [ ] **5.8 Label incomplete experiments.** If implemented, `-SkipTests`/`-AllowDirty` require a scratch project and output `baselineEligible=false`; missing coverage stays null/unavailable. Verification: an experiment cannot overwrite the trusted profile's previous good analysis.

### Phase 6 — Durable reports and actionable ranking

- [ ] **6.1 Port the API client and fixtures.** Keep dependency-light Python and reader-token-only GET requests. Capture sanitized current-server fixtures for issues, measures, analyses, gate, files, and supported hotspot data. Verification: fixture tests run offline with neither Docker nor real credentials.
- [ ] **6.2 Prove completeness.** Preserve pagination, issue-key deduplication across qualities, and splitting above the 10,000-result limit. Handle an oversized individual rule partition or declare incompleteness explicitly. Compare retrieved totals against API totals. Verification: boundary fixtures for empty, multi-page, duplicate-impact, and oversized partitions cannot silently truncate.
- [ ] **6.3 Do not swallow missing security data.** ImprovedDb's exporter treats hotspot endpoint errors as an empty list. Replace that behavior with capability/status metadata. Unsupported, forbidden, unreachable, and genuinely empty are different states. Verification: 403/404/503 fixtures produce truthful warnings or a failed required export, never “no hotspots” without evidence.
- [ ] **6.4 Produce the Markdown report.** Include run identity, settings, actual scope, test/coverage completeness, informational gate, security/reliability findings, hotspots requiring review, top rules, duplication, and ranked files. Include exact `rule path:line`, issue key, impact, and suggested effort for actionable findings. Bound example lists and link to full JSON.
- [ ] **6.5 Preserve meaningful risk ranking.** Reuse ImprovedDb's documented heuristic if useful, but label it as a heuristic. Show its complexity/churn/coverage inputs. Missing coverage is unknown, not zero; any ranking fallback must be visible. Verification: fixtures for missing metrics and no-coverable-lines files sort deterministically without misleading percentages.
- [ ] **6.6 Produce a batch index.** Join profile reports by SHA and configuration. Deduplicate shared findings for triage using rule/path/line/message while retaining both profile references. Do not sum shared LOC/issues or average profile coverage into a fabricated repository metric. Verification: a shared backend issue appears once in the backlog and links to both profiles.
- [ ] **6.7 Describe comparison limits.** Record prior analysis/version, settings digest, and tools. Changing exclusions/rules/profile/tools changes comparability. “New code” from the server is not guaranteed to equal a Git diff. Verification: first run says no comparison baseline; configuration changes visibly invalidate simple before/after claims.
- [ ] **6.8 Sanitize archives.** Omit authors' emails, machine paths, secrets, and unneeded source excerpts from retained reports. Keep JSON schema version and all issue locations required for later work. Verification: token sentinels and known private paths cannot survive export/archive.

### Phase 7 — One-command audits and optional MCP

- [ ] **7.1 Implement the public entry point.** `Invoke-CodeQualityAudit.ps1` supports `-Mode Quick|Full`, `-FrontendProfile BlazorAuto|React|Both`, an explicit ref for permitted experiments, `-KeepServerRunning`, and settings overrides. Default to `Full` and `Both`. No command without an explicit invocation is hooked into normal workflows.
- [ ] **7.2 Pin and create audit worktrees.** Full mode fetches `origin/main`, resolves one full SHA, and creates run-owned detached audit worktrees. Use the same SHA for both profiles and run them sequentially. Use the caller's script version explicitly when bootstrapping a candidate before it is on main; record driver SHA separately from analyzed SHA. Verification: the source tree is immutable and ordinary active work is untouched.
- [ ] **7.3 Manage server ownership.** Initialize/start only the resolved dedicated stack. Track whether this command started it. Archive reports, stop owned startup by default, and leave previously running state alone. Verification: success and failure both meet decision 13; `-KeepServerRunning` leaves a usable dashboard.
- [ ] **7.4 Archive before deleting.** Copy sanitized reports to the per-user repository namespace and verify their contents before removing audit worktrees. Remove only run-created worktrees after checking tracked/untracked user changes. If archive fails, retain the worktree and explain recovery. Verification: printed report paths still exist after cleanup.
- [ ] **7.5 Add the MCP launcher.** Run the pinned official image over stdio on the owned Docker network. Resolve the selected profile, use its reader token via environment, set `SONARQUBE_READ_ONLY=true`, and restrict toolsets to investigation. Send launcher diagnostics to stderr, never stdout. Do not mount Docker socket or source with write access. Verification: an MCP handshake/tool query succeeds without protocol pollution.
- [ ] **7.6 Verify least privilege.** Test issues, rules, measures, coverage, and gate queries through MCP. Confirm mutation tools are absent and token permissions prevent writes independently. Do not assume `SONARQUBE_PROJECT_KEY` universally restricts every MCP tool; use one narrowly scoped reader per profile if the image's behavior needs it.
- [ ] **7.7 Handle client configuration optionally.** Document per-user launcher registration without literal secrets or machine paths in tracked files. Preserve existing ImprovedDb entries. Registration is opt-in and never starts the Sonar server automatically. If a client loads configured MCP processes on startup, keep this integration disabled until explicitly selected. Verification: no scanner/server runs from client startup; reports work with no MCP setup.

### Phase 8 — Validation, documentation, and tooling PR

- [ ] **8.1 Run focused offline tests.** Run Python summarizer/exporter suites, PowerShell helper/driver tests, and relevant scope/settings contract checks. Use `python -m unittest discover -s Scripts/Quality/tests -p 'test_*.py'` and `pwsh -NoProfile -File Scripts/Quality/tests/Test-SonarQualityModule.ps1`, then any added driver suite. Use mocked APIs/processes and temporary secrets, never actual credential names in a test. Verify interruption, cleanup, redaction, and profile identity cases above.
- [ ] **8.2 Protect opt-in behavior.** Check normal profile builds and ordinary npm tests again. Inspect application Compose and workflow changes. Offline test execution in CI is allowed; live Sonar startup/scan/coverage, a new Sonar check, and scheduled triggers are not. Verification: ordinary workflow evidence shows no live Sonar work.
- [ ] **8.3 Run the required local gate.** Follow the complete current `docs/Test.md#local-gate`, including format, both profile tests, deployment audit, script/template/YAML/ShellCheck/actionlint checks. Also run `yamllint docker/sonarqube/compose.yaml`; the existing YAML gate does not include this new path. Validate scoped Compose with `config --quiet` using protected process-local variables, without dumping resolved credentials. Run .NET build/test sequentially. Run React `npm ci`, `api:check`, typecheck, lint, tests, and build because its package/config changed. Only rerun broader checks after a relevant change or failure.
- [ ] **8.4 Add operator documentation.** Provide literal first-use, routine audit, quick audit, one-profile, dashboard/MCP, stop, token rotation, report-location, failure recovery, backup/upgrade, and fork identity instructions. Explain persistent history and stopped-server MCP behavior. Commands must use relative repository paths or computed Git roots.
- [ ] **8.5 Link the second quality tool.** Add short links from README and Test docs; add fork setup details. Explain Lighthouse's runtime measurements and Sonar's source findings without creating automatic coupling or duplicate test guides.
- [ ] **8.6 Open the tooling PR.** Stage explicit paths, review `git diff --check`, include focused and full validation evidence, and note no deployment is needed. Merge only with `build-test-push` green on the exact PR head. Verification: record tooling merge SHA and wait for green `main` CI.

### Phase 9 — Baseline, triage, and closeout

- [ ] **9.1 Audit merged main literally.** Follow the new documented full-audit command with both profiles on one fetched SHA. Do not reuse candidate/scaffold results as the accepted baseline. Verification: both processing tasks succeed, exports match exact analyses, coverage maps to named production files, and reports survive cleanup.
- [ ] **9.2 Record compact evidence.** Write `Plans/Support/SonarQubeOnDemandQuality/Baseline.md` with analyzed SHA, driver/tool versions, profile scope, gate, language LOC, coverage denominator, tests, counts, runtimes, report digests, and limitations. Keep machine-specific archival paths in ignored local notes. No guessed coverage threshold or copied ImprovedDb issue count is an acceptance criterion.
- [ ] **9.3 Triage high-value findings.** Read actual code for security, reliability, and highest-risk examples. Classify each as confirmed defect, worthwhile improvement, reviewed noise, or deferred design work. A security hotspot is a review task, not automatically a vulnerability. No blanket `NOSONAR` or rule deactivation to manufacture a green report.
- [ ] **9.4 Create the improvement backlog.** Write `Plans/CodeQualityImprovements.md` from the accepted report with the template in section 8. Prioritize correctness/security, then valuable low-effort work, then tested refactors. Include both frontends and shared infrastructure findings as appropriate. Do not begin those changes unless authorized by scope.
- [ ] **9.5 Optional first fixes.** Only if section 12 authorizes them: make one bounded remediation PR, include behavior tests where risk warrants them, run the required gate, merge with exact-head CI, and rerun the on-demand audit after merge. Record improved findings and any changed scope; do not copy ImprovedDb's 219-fix allowlist.
- [ ] **9.6 Integrate evidence and backlog.** Use a documentation PR with Markdown review and `git diff --check`; preserve existing CI requirements. Record each merge commit and green main CI in this plan or PR descriptions.
- [ ] **9.7 Finish resource accounting.** Confirm no run-owned worktree/process/scanner state remains; reports are archived; owned server is stopped unless explicitly retained; all history volumes remain; ImprovedDb/application resources are unchanged. Mark this plan complete only when required PRs are merged and main CI is green.

## 6. Command contract for the finished feature

These commands are acceptance targets. They do not exist yet. Run them only after implementation.

```powershell
# Full measured audit of both supported compositions, with automatic owned-server stop.
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Mode Full

# Fast C# findings; no server or coverage.
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Mode Quick

# Review React only and leave the dashboard available for explicit MCP/UI investigation.
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 `
  -Mode Full -FrontendProfile React -KeepServerRunning

# Explicit lifecycle operations; stop keeps history.
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Status
pwsh -NoProfile -File Scripts/Quality/SonarQubeServer.ps1 -Stop
```

`-NoProfile` means the command cannot depend on a personal PowerShell profile to find pinned Node/npm. The driver must resolve an explicit compatible executable/tool directory or fail preflight clearly. Provide a non-secret local toolchain override where required.

The command prints an archive path, batch-index path, analyzed SHA, each profile's result, dashboard URLs, and whether the server remains running. A red quality gate is reported as a finding. A failed/incomplete audit returns nonzero and never prints a success summary.

## 7. Minimum acceptance matrix

| Scenario | Required observation |
| --- | --- |
| Ordinary BlazorAuto/React restore/build | No opt-in analyzer dependency, Sonar process, server startup, or Sonar-generated warnings. |
| Ordinary React unit tests | Same approved tests; no coverage collection. |
| Quick audit | Fresh SARIF and summaries; correct profile/dirty metadata; no server access. |
| Fresh full audit | Automatic owned initialization, two separate project histories, nonempty mapped coverage, complete reports, default stop. |
| Existing running server | Audit preserves running state; no unnecessary credential rotation. |
| Server stopped/restarted | Existing projects and analysis history survive. |
| React scan | Real TS/TSX issues/coverage are indexed; Blazor implementation is excluded from production scope. |
| BlazorAuto scan | C#/Razor scope is verified; React implementation is excluded. |
| Test/build/export failure or timeout | Nonzero exit, truthful summary, secret-safe diagnostics, owned cleanup, no partial upload before validated tests. |
| External newer analysis during export | Mismatch detected; wrong results cannot be attributed to this SHA. |
| Concurrent run/stop | Lock protects batch/project/server state; no interrupted unrelated audit. |
| Missing/unsupported hotspot API | Explicit unavailable status; never an invented empty result. |
| Fork or second repository | Unique identities/secrets/state; no hard-coded ImprovedDb or deployment values. |
| MCP | Read queries work; write tools/permissions unavailable; no literal secret in configuration. |
| Experiment, if supported | Scratch key and `baselineEligible=false`; trusted baseline remains intact. |
| CI/application/deployment startup | No live Sonar invocation, new required quality check, or automatic trigger. |

## 8. Improvement-backlog template

Every actionable entry in `Plans/CodeQualityImprovements.md` uses this structure:

```markdown
### Q-001 — Concrete problem and intended behavior

- Evidence: analyzed SHA, frontend profile(s), issue key(s), rule, path:line.
- Why it matters: an observed defect/risk or a specific maintenance cost.
- Proposed change: exact files and a bounded implementation approach.
- Behavior to preserve: existing contract and edge cases.
- Verification: focused evidence/tests plus required repository gate.
- Effort: small / medium / large, with the reason.
- Dependencies: other entry IDs or none.
- Decision: fix / defer / reviewed noise, with a code-based reason.
- Acceptance: what must change in behavior/report, and what must remain comparable.
```

For each wave, preserve before/after SHA and report/configuration digests. A lower issue count caused by exclusions or rule deactivation is a scope change, not a code-quality improvement. Fix confirmed risks before cosmetic volume. Do not create tests that merely mirror a harmless edit.

## 9. PR boundaries and rollback

Recommended delivery uses two required PRs:

1. Tooling, coverage plumbing, offline tests, and operator documentation. Validate locally and on exact PR head before merge.
2. Accepted baseline evidence, improvement backlog, and plan execution record. Markdown-only local exemption applies; existing CI requirements still apply.

A third remediation PR is optional. Each code/configuration PR uses the full current local gate. No PR requires a production deployment for tooling acceptance. Do not bypass CI with skip markers.

If tooling is faulty, stop the owned local stack and revert the tooling PR through a new PR. Remove only run-owned temporary artifacts and optional personal MCP configuration after verifying their ownership. Preserve Sonar history volumes and encrypted credentials for diagnosis. Never automate volume deletion as rollback. Back up the owned database before a deliberate future server upgrade; migration approval is a separate upgrade operation, not a first-install requirement.

## 10. Manual blockers

**No certain operator-only blocker was found for this plan's default dedicated-local workflow.**

The executor can create Compose state, generate/encrypt credentials, rotate the fresh default password, provision projects/tokens/profiles, install pinned user-local tools, run audits, export reports, and open PRs within authorized implementation scope. Do not assign token creation, dashboard clicks, image pulls, or ordinary configuration work to the operator by default.

Optional personal MCP client trust/reload controls can vary by client. The report workflow must remain complete without them. This is not a mandatory blocker. System-wide replacement of a protected Node installation is also unnecessary for the planned audit; a verified user-local runtime is sufficient.

If execution later encounters an existing unknown admin password, unavailable protected setting, or an actual permission denial, record the exact failure and needed action then. Do not turn hypothetical cases into a pre-implementation checklist for the operator.

## 11. Execution record

Fill this during implementation. Keep preparation, candidate verification, and accepted main baselines distinct.

| Checkpoint | Status | Commit / evidence |
| --- | --- | --- |
| Repository/source inspection and reuse tests | Complete | Section 2; 37 ImprovedDb reuse tests passed. |
| Host Node/npm alignment | Complete | Verified Node `24.21.0` / npm `12.2.0`; official archive hash and executable signature checked. Per-user PowerShell activation and backups are recorded in ignored HostPreparation.md. |
| Operator preferences | Pending optional clarification | Section 12 defaults apply until changed. |
| Phase 0 current baseline | Not started | |
| Phases 1–7 tooling | Not started | |
| Phase 8 local gate and tooling PR | Not started | |
| Tooling merge and main CI | Not started | |
| Phase 9 accepted full baseline | Not started | |
| Backlog/evidence PR merge and main CI | Not started | |
| Optional remediation wave | Not authorized by default | |
| Resource closeout | Not started | |

Record corrections here with the disproved assumption, evidence, and replacement instruction. Continue autonomously through routine implementation choices already covered by the plan.

## 12. Important open preferences

1. **Dedicated server or shared ImprovedDb server?** Recommended: dedicated repository stack using cached images. This protects both histories and makes the template self-contained for forks. Sharing can save memory/storage, but needs a distinct project/reader setup and different lifecycle ownership. If sharing is selected, revise Phases 3 and 7 before execution; never reuse ImprovedDb project keys or credentials blindly.
2. **Tooling/baseline/backlog only, or also the first small improvement PR?** Recommended default: finish reliable tooling and the measured backlog first. If the operator wants immediate improvements, explicitly add one bounded, code-reviewed remediation wave after the baseline. Larger refactors remain separate planned work.
