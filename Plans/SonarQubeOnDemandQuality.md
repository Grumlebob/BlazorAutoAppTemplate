# SonarQube On-Demand Quality Audits

Status: implementation in progress; local gates, candidate server acceptance, PR integration, and trusted baseline remain. All recommendations were accepted on 2026-10-11. There are no unresolved scope decisions.

Execution prompt: [SonarQubeOnDemandQualityGoal.md](SonarQubeOnDemandQualityGoal.md). Its `/goal` block started implementation in the dedicated feature worktree.

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

The accepted implementation scope ends after tooling, verified baselines, and a reviewed improvement backlog. Do not implement the first application-remediation wave as part of this goal. Its future work is described in the backlog. Section 12 records the accepted decisions.

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

The source is available through this checkout's `improveddb` Git remote and through the operator-provided sibling checkout. Review found that the frozen commit was initially absent from the template's object database; `git fetch improveddb 175f069fff0b2b8e8870eab704f133d217930e7d` successfully retrieved it. A different checkout must check with `git cat-file -e <sha>^{commit}` and fetch the exact SHA if missing. Use the authenticated source URL from `git remote get-url improveddb`, or the supplied sibling checkout; do not assume that adding a remote fetches its objects. Extract with `git show <frozen-sha>:<path>`. Do not merge ImprovedDb history or copy private settings.

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

These are observed working-source pins, not a claim that each is the newest release. Adopt these exact initial versions; do not turn checking for newer releases into an approval dependency. Change a pin only if concrete compatibility/security evidence requires it, then record the replacement and rerun affected checks. Never upgrade during an audit. Do not copy ImprovedDb's old claim that PostgreSQL support ends at 17: current Community Build documentation lists 14–18 from 26.2 onward. Version 17 remains a valid initial choice. See [database requirements](https://docs.sonarsource.com/sonarqube-community-build/server-installation/installing-the-database).

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

### 2.5 Additional execution preflight completed during review

Both profiles restored and built in a separate worktree with zero warnings/errors. The existing collector produced Microsoft XML coverage without adding a package:

- BlazorAuto: `BookCoverGeometryTests`, **5 passed**, production `BlazorAutoApp.Client.dll` with **187 covered lines**, and expected book geometry/catalog source paths.
- React: `OpenApiMetadataTests`, **1 passed**, production `BlazorAutoApp.dll` with **259 covered lines**, including the React composition and OpenAPI metadata host source paths.
- Each run produced one direct GUID-child XML report and one duplicate deeper collector copy. Use `tests/*/*.xml`, not recursive `tests/**/*.xml`, for coverage import. The focused counts are not the full-suite expectations.
- `Microsoft.CodeCoverage/18.10.1` is already a transitive dependency of the current Test SDK. Do not add a redundant direct reference unless the actual dependency graph or collector behavior changes.
- A read-only Docker probe found the Linux VM's memory-map/file limits meet the cited Sonar prerequisites. No kernel setting or deployment host was changed. Store raw machine results only in ignored local preparation notes. See [Sonar Linux prerequisites](https://docs.sonarsource.com/sonarqube-community-build/server-installation/pre-installation/linux) and [Microsoft coverage documentation](https://github.com/microsoft/codecoverage).

Raw probe artifacts are not accepted Sonar baselines and do not prove server indexing. Phase 9 still requires complete scans on merged main.

## 3. Decisions and defaults

These decisions are accepted. Make routine implementation choices autonomously within them.

1. **Hosting:** a dedicated local stack for this repository. Do not start, stop, reprovision, or reuse ImprovedDb's server. Its images may be reused from Docker's cache.
2. **Identity:** derive a stable namespace from normalized `origin` repository identity, not from worktree location. Use a readable repository slug plus an 8-character SHA-256 suffix for Compose names and the local secret namespace. Clones/worktrees of one repository share identity; forks have different identities.
3. **Port:** default to loopback `127.0.0.1:9200`. This is a developer-tool default, not a deployment value. Allow an ignored local override. On the first initialization, if the default is occupied and no override exists, select the first available port in 9201–9299 and persist it in private repository-scoped settings. Do not change an established stack's port or stop another port owner. Pass the resolved port consistently to Compose, APIs, reports, and MCP; a bind race fails cleanly without affecting unrelated processes.
4. **State:** dedicated PostgreSQL and named SonarQube data/extensions/log/database volumes. Both services use `restart: "no"`. Normal stop preserves all history.
5. **Profiles:** use separate Sonar projects `<repository-prefix>-BlazorAuto` and `<repository-prefix>-React`. Each gets its own complete begin/build/test/end cycle and history. Never upload two competing compositions to one project or add unsupported PR/branch parameters.
6. **Default audit:** analyze both frontend profiles sequentially from the same fetched `origin/main` SHA. Allow explicit `BlazorAuto` or `React`; do not implement an additional `Selected` option. Never infer profile from installed assets.
7. **Candidate validation:** support clean committed candidate scans through `-Candidate` in Full mode, using separate keys ending in `-candidate-<sha12>`. The default always scans fetched main. Do not implement dirty Full scans, arbitrary-ref experiments, skipped tests, or `-NoExport` in version 1. Quick mode may inspect labeled dirty source as section 4.3 specifies. Candidate scans require complete tests/coverage and never replace trusted main history.
8. **Secrets:** PowerShell 7 on Windows with DPAPI for the initial full-scan implementation. Generate admin, database, analysis, and reader credentials automatically. Use one reader account per profile; it can browse only that profile's owned main/candidate projects. Each analysis token is scoped to exactly one project.
9. **Other operating systems:** Python report tests and ordinary app builds remain cross-platform. Document Windows-only credential provisioning clearly. Do not invent a Linux plaintext fallback. Cross-platform secrets are a later enhancement.
10. **Tool isolation:** an explicit Full audit authorizes installation/reuse of its pinned scanner/JRE and React dependencies; it requires no second permission question. Quick mode restores its opt-in NuGet analyzer. Do not add scanner restoration to ordinary application tooling. Preserve the root EF tool manifest.
11. **Quality profiles:** use built-in Sonar way initially. Add reviewed, declarative overrides only after real template findings justify them. Do not import ImprovedDb's application-specific ignores.
12. **Failure semantics:** scanner, test, coverage, processing, identity, secret-hygiene, and export failures return nonzero. Sonar's red/failed quality gate remains an informational finding and does not fail an otherwise complete audit.
13. **Shutdown:** the high-level command stops a dedicated server that it started, even after failure, unless `-KeepServerRunning` was explicitly requested. Leave a previously running server running. Verify ownership while holding the lifecycle/run lock.
14. **Reports:** write ignored run artifacts, then archive sanitized reports outside temporary worktrees before removing them. Retain selected compact evidence as Markdown. Do not commit raw source excerpts or JSON dumps by default.
15. **Scope:** analyze shared C#, the active frontend, hand-authored CSS/JS/TS, Python helpers, and supported infrastructure/secrets inputs. Do not promise general PowerShell or Bash semantic analysis; existing analyzers remain necessary.
16. **MCP delivery:** deliver the launcher, a headless protocol probe, and registration instructions. Do not register it in personal clients as a completion dependency. The protocol probe proves the integration without requiring client trust clicks, a reload, Claude credentials, or a paid CLI.
17. **Implementation simplicity:** use explicit exported helper functions and one immutable resolved context; do not port `Export-ModuleMember -Function *`, global mutable project constants, shared temporary-file names, or the ImprovedDb coordination framework. This goal does not create a general job scheduler or plugin platform.

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
Scripts/Quality/probe_sonar_mcp.py
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

Add ignore rules for `.sonarqube/`, `Scripts/Quality/quality-settings.local.json`, and any additional output not already covered by `artifacts/` or React `coverage/` rules. The example settings file contains a schema, a loopback port, and optional non-secret toolchain overrides. Actual machine tool paths belong only in ignored local settings. Credentials never appear in either settings file.

Do not modify application Dockerfiles, deployment settings, production assets, or the root EF manifest merely to install this tool.

### 4.1 Settings, identity, and durable state contract

Resolve context once in the invoking checkout, before creating a worktree. Pass that context explicitly to helpers; do not reread local settings in detached worktrees. Resolution order is explicit command argument, invoking checkout's ignored local settings, persisted per-user repository settings, then tracked defaults. The settings example uses this shape:

```json
{
  "schema": "blazorautoapp.sonar-settings/1",
  "hostPort": null,
  "nodeToolchainDirectory": null,
  "pythonExecutable": null
}
```

Null means automatic resolution; unknown fields and non-loopback endpoints are errors. Do not expose an arbitrary remote-server URL or mutable project-key override in version 1.

Normalize `origin` to `host/owner/repository`: remove credentials, SSH username, scheme, trailing slash, and `.git`; lowercase GitHub identities consistently. Keep the full normalized identity and full SHA-256 in context. Derive `repositorySlug` from the sanitized repository name and `identityHash8` from the hash. Use `sonarqube-<slug>-<hash8>` for Compose project/network and `<slug>-<hash8>-<profile>` for project keys. Prefix explicit named volumes with that Compose identity. A missing/unsupported origin must report the needed origin configuration; never fall back to a worktree folder name.

Use the computed per-user base `%LOCALAPPDATA%/BlazorAutoAppQuality/SonarQube/<slug>-<hash8>/` for encrypted secrets, persisted settings, tools, lock, and report archives. Worktrees of the same origin resolve this same base. Keep a settings record containing the full identity/hash and reject a collision. A repository rename creates a new namespace; never migrate/delete old history automatically.

Resolve Node from the configured tool directory, a matching executable on PATH, then a verified installed per-user `Programs/nodejs/v<pinned-version>` runtime. Invoke `node.exe` and npm's `npm-cli.js` by absolute path; prepend their directory in child environments. Discover the real Python executable; do not trust an unverified Windows Store `python3` alias. Restore any temporary environment changes. In Phase 0, install a missing pinned runtime into the private tool directory with the official checksum/signature checks rather than requiring administrator action. Regular audits do not upgrade the host implicitly.

### 4.2 Lock, timeouts, credentials, and process contract

- Use an exclusive OS-held file handle (`FileShare.None`) at the private namespace's `audit.lock`. The file's existence alone is not ownership. A crashed process releases the OS handle; an old metadata file does not require deletion/reclamation. A second invocation waits at most 30 seconds, then reports busy. The outer wrapper owns the handle; internal helpers receive the context and never reacquire it. Standalone lifecycle commands acquire it themselves. This lock is unrelated to deployment locks.
- Default server readiness timeout: 600 seconds, polling every 5 seconds. Default individual build/test timeout: 20 minutes. Compute-engine timeout: 15 minutes, polling every 5 seconds. MCP probe timeout: 60 seconds. Total full-batch deadline: 90 minutes; each wait uses the remaining deadline. Keep HTTP retries bounded and record retry exhaustion.
- Use `ProcessStartInfo.ArgumentList`, explicit executable paths and working directories, redirected output, and `WaitForExitAsync`. Kill only the process tree launched by this run on timeout/cancellation. Avoid shell command strings, detached background helpers, and reliance on `$LASTEXITCODE` after an unrelated command.
- Child output goes to a fresh private staging directory. Redact it before emitting any public log/tail or copying logs to archives. Test secrets split across output chunks. Raw transient captures and `.sonarqube` may contain scanner-injected credentials; never publish them, and scrub/remove owned transient state in `finally`. If persistent logs contain a secret after sanitization, report a secret-hygiene failure rather than a successful audit.
- Secret files are encrypted CLIXML written through a same-directory temporary file and atomically promoted while holding the lock. Store `database-password`, confirmed/pending admin passwords, profile reader passwords/tokens, and project-scoped analysis tokens. Names must be derived from owned identities, not arbitrary caller paths.
- Admin rotation uses an explicit recovery journal: persist the generated pending password first; change the fresh server's default password; authenticate with the pending password; promote it to confirmed. On retry, try the pending password first. If it works, promote it without another rotation. Otherwise, only a proven fresh owned server may retry the default credential and change to that same pending password. Never discard an unknown existing credential or reset an existing database.
- Token creation cannot be atomic with local storage. If an owned token name exists but its local encrypted value is missing/invalid, validate the owned admin identity, revoke only that exact owned token name/account/project, regenerate, and atomically persist. Do not revoke unrelated tokens or rotate healthy ones. Provisioning journals and idempotence tests must exercise failure between API creation and local persistence.
- Generate reader passwords before creating readers, persist them encrypted, and recover using that owned journal. Check effective group/global permissions on each own reader. Since this is a dedicated server, create a reader group with no global Execute Analysis/admin grants; do not modify another application's server/groups.

### 4.3 Scan transaction and candidate contract

The public command is `Invoke-CodeQualityAudit.ps1`. Parameters are `-Mode Quick|Full` (Full default), `-FrontendProfile BlazorAuto|React|Both` (Both default), `-Candidate`, `-KeepServerRunning`, and `-SettingsPath`. `-Candidate` and `-KeepServerRunning` are Full-only. Invalid combinations fail before creating state.

Default Full mode fetches main and resolves its SHA once. `-Candidate` resolves the invoking clean, committed HEAD instead, records `baselineEligible=false`, and uses `<main-project-key>-candidate-<sha12>`. Require actual source/config files to be committed before candidate acceptance; ordinary ignored build output does not count as dirty. Provision analysis credentials and reader access for candidate projects through the same owned server helper. Do not delete candidate history automatically.

Create one unique detached worktree per requested profile under the private run directory. Its source SHA contains the driver, module, settings template, and React coverage wiring. Invoke that worktree's lower PowerShell scripts in the same PowerShell process using `&`, with explicit `-RepoRoot` and an internal `-Context` object. The context holds non-secret identity/settings/paths; helpers retrieve credentials only when needed. Never serialize plaintext credentials into command lines/context files to pass context between shells. This removes the earlier ambiguity about using new scripts to scan a main checkout that does not contain them. Candidate acceptance runs before tooling merge; trusted baselines run only after tooling merge.

For each profile, use this exact order:

1. For React, run pinned `npm ci`, `api:check`, `typecheck`, and `test:coverage` before any scanner begin. Write a JSON unit report and validate current approved test counts as well as nonempty LCOV. Do not invoke an API-generation helper inside an active scanner window.
2. Invoke the pinned scanner executable with `begin`, `/k:<resolved-project>`, `/v:<commit-date>-<sha12>`, `/s:<absolute-settings.xml>`, `/d:sonar.projectBaseDir=<worktree>`, `/d:sonar.scm.revision=<full-sha>`, host URL, and analysis token. Supply C# XML/TRX paths and, for React only, LCOV path. Use token-bearing arguments internally, redacted arguments publicly.
3. Restore `BlazorAutoApp.sln` with `-p:FrontendProfile=<profile>`.
4. Build it with `-c Release --no-restore --no-incremental --disable-build-servers -nr:false` and the same profile.
5. Test **`BlazorAutoApp.Test/BlazorAutoApp.Test.csproj`**, not every non-test project, using `-c Release --no-build --no-restore`, the same profile, `--collect "Code Coverage;Format=Xml"`, `--logger "trx;LogFileName=suite.trx"`, and this profile's results directory. For React, add `--filter "FrontendProfile!=BlazorAuto"`. Set inherited E2E/lifecycle opt-ins off in the child environment; restore the parent values.
6. Run `validate_dotnet_test_results.py` on `suite.trx` using current approved expectations. Parse direct GUID-child coverage XML reports, require covered production source lines, and reject unresolved source paths. Never import the collector's deeper duplicate `In/` copies. Do not accept a zero-test or empty-coverage run just because the process exit code is zero.
7. Only after all required checks pass, invoke scanner `end`; retain task ID and poll that exact task. Preserve its analysis ID, source SHA, project and project version.
8. Query the exact-analysis gate; export with the reader token while checking latest-view identity before and after. On a mismatch, fail the report export rather than relabeling another analysis.
9. Archive the sanitized outputs, finalize profile status, and clean only owned transient scanner state/worktree. Do not submit partial results with `end` in a `finally` block.

A two-profile batch is not an atomic server transaction. If BlazorAuto succeeds and React fails, retain the successful profile report and both statuses, return nonzero, and mark the batch ineligible as an accepted baseline. Do not roll back or delete the successful server analysis. Resume with a new complete batch after fixing the cause.

Quick mode may analyze the caller's dirty source because it does not update server history. Serialize it through the same repository lock, label the dirty state, and give each profile separate outputs. Always restore the invoking checkout's normal selected-profile package graph in `finally` after an opt-in analyzer restore; failure to restore is visible. Do not silently leave SonarAnalyzer in ordinary build inputs after a quick audit.

### 4.4 Scope and coverage contract

Set common UTF-8/multilanguage properties in the XML template. Add profile exclusions at runtime; do not rewrite the tracked XML or tracked frontend selector. Keep an effective, sanitized settings snapshot and digest in the report. Initial common exclusions cover `**/bin/**`, `**/obj/**`, `.git/**`, `.sonarqube/**`, `**/node_modules/**`, `artifacts/**`, `**/TestResults/**`, `Plans/**`, `Plans.local/**`, generated React `build/`, `.react-router/`, `coverage/`, declarations/OpenAPI snapshots, generated `tailwind.css`, and generated EF migrations. Respect SCM ignores for actual secrets/local runtime files; do not disable them to collect more LOC.

| Profile | Additional production exclusions | Required named evidence |
| --- | --- | --- |
| BlazorAuto | `BlazorAutoApp.React/**`; inactive `FrontendComposition.React.cs` is already omitted by compilation | `BookCoverGeometry.cs`, a Books Razor component's source findings/scope, shared Core/backend files, handwritten client CSS. |
| React | `BlazorAutoApp.Client/**`, inactive host `**/*.razor` / `**/*.razor.js`, and the two Blazor-only Account registration files currently removed by the host project | `FrontendComposition.React.cs`, `OpenApiMetadataHosting.cs`, `BlazorAutoApp.React/app/features/books/catalog-page.tsx`, and a tested React API module with imported LCOV hits. |

The Test project still references Client in React mode. Therefore a successful React build is not proof that Client files are absent from production Sonar scope. Verify upload/server inventory and exclude them explicitly. Do not blanket-exclude the entire host `Features/Login` directory: it also contains server contracts; use the current compilation exclusions and actual component inventory.

Classify C# test projects as tests, not production. JS/TS tests (`**/*.test.ts`, `**/*.test.tsx`), `app/test/**`, typecheck fixtures, and generated declarations are excluded from production issue/coverage scope but their tests still execute. Include untested real React source in the LCOV denominator. Leave Razor coverage truthfully measured/uncovered; do not remove Razor to raise the percentage. Scripts/deployment/Docker/Simulation stay visible for supported issue analysis but are excluded from coverage where no corresponding coverage is collected. Report these exclusions instead of calling them covered.

### 4.5 Output and completeness contract

Use a collision-resistant `runId` containing UTC timestamp, SHA prefix, and a GUID suffix. Full-mode outputs live under the private namespace's `runs/<runId>/` directory, with audit worktrees in its `worktrees/<profile>/` children. Pass this absolute output root to lower-level scripts. The canonical run layout is:

```text
summary.json
batch.md
<profile>/summary.json
<profile>/report.md
<profile>/report.json
<profile>/tests/suite.trx
<profile>/tests/<guid>/*.xml
React/react-coverage/lcov.info
worktrees/<profile>/                             # owned detached Git worktrees
```

The batch summary uses schema `blazorautoapp.sonar-audit/1` and contains mode, runId, normalized repository identity, driver/analyzed SHA, selected profiles, candidate/dirty flags, baseline eligibility, UTC timestamps, outcome, failure reason, server start/stop ownership, settings/tool digests, and relative output locations. Each profile record adds project key, stage timings/exit codes, test counts, coverage validity, CE task/analysis IDs, report completeness, informational gate status, and warnings. Missing measurements are null with a reason, not numeric zero.

Required data: matching identity, core measures, complete issue/file lists, all approved tests, valid coverage, and exported reports. Security hotspot data is required when the pinned server supports it; unsupported capability is an explicit status. Authentication/permission or network failure on a supported endpoint fails required export. An optional unsupported field is a warning; a truncated required list fails the audit. Normalize MQR impacts and retain legacy type/severity fallback rather than counting an issue once per impact.

Use 500-item pages. Above the API's result cap, split by software quality, rule, then indexed file where necessary; deduplicate by issue key and validate complete counts, including rule-facet truncation. If a single partition still exceeds the cap, report incomplete data and fail rather than silently returning its first 10,000 records. Markdown can truncate displayed examples; JSON must not silently truncate the underlying result list. No fixture assumes the project has findings: an honest zero-issue audit can succeed.

Archive only sanitized summaries, batch/report Markdown/JSON, the effective settings snapshot, and their SHA-256 manifest under the private `reports/<runId>/` directory. Normalize report source locations to repository-relative paths. Do not copy raw TRX/XML/LCOV/scanner directories by default; they contain machine paths and sometimes credential-bearing state. On failure, keep only an explicitly private diagnostic bundle if needed, with the cleanup/retention outcome recorded. Printed report paths refer to verified archives that survive worktree removal.

### 4.6 Dependency order and deterministic completion

Implement Phases 0–2, then lifecycle/provisioning in Phase 3, coverage/scope in Phase 4, scan transactions in Phase 5, exporter in Phase 6, and orchestration/MCP in Phase 7. Keep helpers independently testable so an early phase does not require an unimplemented later wrapper. The already completed collector probes remove the main coverage uncertainty; server scope is verified during candidate acceptance.

Phase 8 runs offline tests, then complete **candidate** audits with both profiles, then the current full repository gate and exact-head tooling PR CI. Commit the candidate before running `-Candidate`; run the driver from that clean commit. If candidate validation changes code, commit the correction and repeat affected validation against the new SHA. Do not merge untested server tooling because no trusted main baseline exists yet.

Phase 9 runs trusted audits from merged main, records baseline evidence, builds a real backlog, and integrates documentation through the repository's reviewed Markdown-only exception. No remediation wave, Linux credential provider, branch experimentation framework, global package migration, or personal MCP registration is necessary to finish. No task depends on a calendar date or a future operator preference.

The MCP launcher accepts `-FrontendProfile BlazorAuto|React` and an optional non-secret `-ProjectKey` limited to that profile's derived main key or owned candidate-key pattern. The headless probe supplies the candidate key explicitly before merge, then the main key during baseline acceptance; it must not query an unanalyzed main project and mistake empty measures for candidate results. The launcher/probe receive the resolved private settings path for port/network consistency. Read-only launcher startup does not acquire the batch/lifecycle lock or start the server. A running MCP reader container is removed by its `--rm` process shutdown, not by deleting Sonar history.

## 5. Execution instructions

Read `AGENTS.md`, `docs/Requirements.md`, `docs/Test.md`, and this plan first. Run one phase at a time. Each task has an observable completion condition. Do not mark a task complete because a file exists without its verification.

Use a dedicated implementation worktree and a PR. Keep .NET build/test processes sequential in each checkout. Use explicit staging paths. Do not stash/reset other work, prune Docker volumes, reclaim deployment locks, force-push `main`, or dispatch a deployment.

### Phase 0 — Establish the current baseline

- [x] **0.1 Fetch and isolate.** The planning packet is merged as PR #173 at `09040e564a08659c23c2a2c730f52875e5392ac5`. Created the feature worktree at that SHA with both planning files present, then fast-forwarded it to current `origin/main` `9dbf825cd14d5e5d7e80d385642c182a00e572f3` before validation. Existing worktree files and local drafts remain untouched.
- [x] **0.2 Recheck relevant contracts.** Current profile resolver, profile test script, test project, dependency manifests, and workflow were reviewed. Current approved expectations remain 211 passed / 13 skipped for BlazorAuto and 203 passed / 13 skipped for React. The solution has five projects; the existing SDK, test, Vitest, Node, and npm pins match the preparation notes.
- [x] **0.3 Verify executable resolution.** PowerShell 7.6.6, Python 3.13.7, .NET SDK 10.0.303, Docker Linux containers, Node 24.21.0, and npm 12.2.0 are available. The pinned user-local Node archive hash and signature were verified during host preparation; the implementation invokes absolute executable paths.
- [x] **0.4 Check ownership and resources.** The repository namespace is new, loopback port 9200 is available, and Docker reports 15 GiB memory with 16 CPUs. Existing unrelated Sonar resources were left untouched. Kernel limits meet requirements per the read-only preflight in section 2.5.
- [x] **0.5 Capture ordinary builds.** Release restore/build passed sequentially for both profiles with zero warnings and errors. Per-profile NuGet graphs are saved in ignored `Plans.local/SonarQubeOnDemandQuality/Phase0Baseline/`; neither graph contains `SonarAnalyzer.CSharp`, and no scanner state exists.
- [x] **0.6 Freeze reuse input.** The listed source and sanitized fixtures were extracted from frozen ImprovedDb commit `175f069fff0b2b8e8870eab704f133d217930e7d` into ignored scratch with SHA-256 manifest. No environment, DPAPI, MCP, or deployment-local files were included.

### Phase 1 — Shared identity, process execution, and safety helpers

- [x] **1.1 Implement settings resolution.** Read tracked defaults and optional ignored local settings. Normalize HTTPS and SSH `origin` URLs to the same owner/repository identity. Strip embedded credentials before any error/log output. Validate project keys, Compose names, and loopback URLs. Verified by `Test-SonarQualityFoundation.ps1` across HTTPS, SSH, trailing `.git`, credential redaction, forks, settings validation, and private identity persistence.
- [x] **1.2 Implement scoped process execution.** Replace `Invoke-ImprovedDbDotnetSequence` with a small template helper using explicit executable paths, argument arrays, exit codes, stdout/stderr capture, and timeouts. Preserve real command arguments; display only redacted arguments. Verified by the PowerShell foundation suite with nonzero exit, split-token output, timeout, and process-tree termination.
- [x] **1.3 Implement run ownership.** Use section 4.2's exclusive OS-held handle around Quick/Full batches and server lifecycle changes. Record owner/run identifiers separately from the lock handle. Never mistake an old lock file for a live owner, or delete it to bypass an active owner. Internal helpers use the outer context. Verified by exclusive-lock contention and release tests; Quick and Full entry points hold the lock for their batch.
- [ ] **1.4 Harden cleanup paths.** Resolve all target paths before deleting anything. Only remove scanner directories or worktrees created by this run. An existing unknown `.sonarqube` directory causes an actionable failure, not automatic recursive deletion. Quick-mode sentinel preservation and command-scoped Git long-path worktree creation/removal are verified; full scanner/worktree cleanup remains part of candidate acceptance.
- [x] **1.5 Implement output hygiene.** Redact secrets before output can reach the console or retained logs. Sanitize caught API exceptions, process arguments, summaries, and diagnostic tails. Restore temporarily changed environment variables to their original values. Verified by split-token console/log redaction and archive sanitizer tests; live archive checks remain part of candidate acceptance.
- [x] **1.6 Establish schemas.** Implement section 4.5's batch/profile schemas plus `blazorautoapp.sonar-report/1` and the quick SARIF-summary schema. Add repository identity and frontend profile fields. Export helper functions explicitly and pass resolved context rather than module-wide mutable identity. Verified by Python schema/identity tests and explicit PowerShell exports; no `improveddb.*` schema or wildcard export remains.
- [ ] **1.7 Test private recovery boundaries.** Add tests for split-token output, reserved/invalid paths, partial credential persistence, interrupted child processes, and invalid parameter combinations. Verification: each failure leaves a truthful status and does not mutate an unrelated sentinel resource.

### Phase 2 — Quick C# analyzer mode

- [x] **2.1 Add conditional package wiring.** Pin `SonarAnalyzer.CSharp` centrally. Add its `PackageReference` only when `RunSonarAnalyzers=true`, with `PrivateAssets=all`. Keep all existing frontend-resolution properties. Verified by Quick opt-in restore/build and the final normal restore with no analyzer references in the five active project assets files.
- [x] **2.2 Add opt-in SARIF paths.** Set `ErrorLog` to a run/profile/project-specific `.sarif` path and create its directory before compilation. Never write different profiles into the same SARIF file. Quick run `quick-20261011T212804Z-9dbf825cd14d-b7b6ea53` produced five nonempty SARIF files per profile; fixtures and generated summaries parse successfully.
- [x] **2.3 Port the summarizer.** Preserve production/test/generated separation, family counts, high-signal findings, deduplication, normalized paths, and bounded Markdown. Record profile, SHA, dirty state, and configuration. Verified by fixture tests, including Windows paths with spaces, and the generated two-profile Quick summaries.
- [x] **2.4 Implement the quick driver.** Support `-FrontendProfile BlazorAuto|React|Both` with `Both` default, sequential builds, `--no-incremental`, bounded timeouts, and explicit arguments. It may inspect a dirty working tree because it does not overwrite server history, but must label it. Verified by the successful dirty two-profile Quick run above; no server or coverage workflow is invoked.
- [x] **2.5 Prevent mode overlap.** A full scan rejects `RunSonarAnalyzers=true`; the quick driver rejects active scanner state. Test lowercase/case-insensitive environment resolution as appropriate to Windows/MSBuild. Verified by `Test-SonarQualityAuditContract.ps1`, including mixed-case environment rejection and preservation of an unowned `.sonarqube` sentinel.
- [x] **2.6 Prove default isolation.** Make normal selected-profile restore a Quick-driver `finally` action. The successful two-profile run restored the selected profile; an injected two-profile restore failure verified the finalizer still attempted the normal React-profile restore. All five active assets files have zero `SonarAnalyzer.CSharp` references.

### Phase 3 — Dedicated on-demand server

- [ ] **3.1 Create standalone Compose.** Use the pinned source images, a private network, internal-only PostgreSQL, loopback Sonar port, named volumes, `restart: "no"`, log rotation, readiness checks, and bounded memory. Do not use application database volumes. Verification: rendered Compose contains only two owned services and one loopback published port; no `latest` tag or external DB port exists.
- [ ] **3.2 Generate database credentials.** Replace ImprovedDb's literal `sonar` password with a generated local secret. Persist it with DPAPI before the first boot and supply it through the process environment. Never change it automatically on an existing DB. Verification: password values are absent from tracked files and logs; a second start uses the same secret.
- [ ] **3.3 Port lifecycle commands.** Provide `-Start`, `-Stop`, `-Status`, `-Logs`, `-Start -Initialize`, and `-Start -ApplyProfile`. Validate mutually exclusive flags. `-Stop` uses scoped Compose stop and keeps volumes. Verification: no action starts Docker services unless explicitly selected, and stop affects only this repository's stack.
- [ ] **3.4 Implement bounded readiness.** Poll `/api/system/status`; distinguish unreachable, starting, down, and migration-required states. Do not hide database migration behind an endless wait. Verification: failed readiness reports an actionable state and a scoped log command.
- [ ] **3.5 Rotate the default admin password.** Implement section 4.2's pending/confirmed password journal. Test interruption both before and after the server commits a password change. Unknown existing credentials cause a stop, never volume deletion. Verification: rerunning completes either interrupted transition without operator action, losing credentials, or rotating an already confirmed password.
- [ ] **3.6 Provision two private projects.** Create the per-profile projects and configure their new-code definition. Generate a project analysis token for each. Start with inherited Sonar way profiles and empty reviewed overrides. Verification: project names, visibility, permissions, and profile associations are correct; repeated initialization creates no duplicate project/token/profile.
- [ ] **3.7 Provision profile reader accounts.** Create one reader for each profile using the journal and group policy in section 4.2. Grant browse/code-view only for that profile's owned projects. Check inherited permissions; explicit write-grant absence alone is not proof. Verification: reader queries succeed and an authenticated effective-permissions check shows no Execute Analysis/admin/write rights. Test denial only against an owned disposable candidate resource if a negative probe requires an endpoint call.
- [ ] **3.8 Verify persistence and isolation.** Stop/restart the owned stack and reinitialize. Compare project IDs, token presence, volume names, and analysis history. Verification: data survives, no new credentials are issued unnecessarily, and ImprovedDb resources retain their previous state.
- [ ] **3.9 Implement candidate provisioning and token recovery.** Create the SHA-specific candidate projects only for explicit Full candidate validation. Apply profile reader permissions and generate exact-project analysis tokens. Implement recovery after token creation without local persistence. Verification: retries replace only the orphaned owned token; main project history and another profile's credentials remain unchanged.

### Phase 4 — Coverage and profile-specific scan scope

- [ ] **4.1 Verify the proven C# collector contract.** Reuse section 2.5's collector, transitive package, named tests, and GUID-child report selection. Reprobe only if SDK/test dependencies or runtime changed. Implement XML validation against actual covered production paths. Verification: missing collector, duplicate import, empty production coverage, or unresolved source paths fails preflight; no redundant direct coverage package is introduced.
- [ ] **4.2 Preserve real suite validation.** Reuse the current TRX validator and expectations from `Scripts/CI/validate-frontend-profiles.sh`. Put reports in unique profile/run directories. Keep E2E and lifecycle opt-ins off. Verification: failed, missing, extra-skipped, or empty tests prevent scanner `end`.
- [ ] **4.3 Add opt-in React coverage.** Pin `@vitest/coverage-v8` to the current exact Vitest version and regenerate the lockfile with pinned npm. Add `test:coverage` using `vitest run --coverage`; keep ordinary `npm test` without coverage. Configure `lcov` plus a human-readable/JSON summary reporter. Verification: normal tests still pass without creating coverage; the explicit command produces nonempty LCOV.
- [ ] **4.4 Define an honest React denominator.** Include `app/**/*.{ts,tsx}` so untested app modules count. Exclude tests, `app/test/**`, generated declarations, and `.typecheck.ts` fixtures. Do not exclude ordinary components or routes because they have low coverage. Verification: an untested real source file appears with zero hits rather than disappearing.
- [ ] **4.5 Normalize LCOV paths.** Run npm in the React package, inspect actual `SF:` entries, and normalize only if they do not map to repository-root files. Configure `sonar.javascript.lcov.reportPaths` to this run's absolute report path. Verification: server coverage for a named tested React module agrees with LCOV; there are no unresolved-source warnings.
- [ ] **4.6 Build common exclusions.** Exclude `.git`, `bin`, `obj`, node dependencies, build/coverage/test outputs, plan artifacts, generated declarations/OpenAPI snapshots, generated Tailwind, EF generated migrations, ignored runtime data, and actual secrets/local inventories. Keep handwritten app CSS, infrastructure, and helper sources. Verification: inspect a generated-file sample and a handwritten-file sample on the server; generated output is absent, handwritten input remains.
- [ ] **4.7 Adapt profile exclusions.** Implement section 4.4's matrix and verify it against current compilation rules. Never exclude the whole Login server feature merely because two Account registration files are inactive. Shared backend and hosting code remain visible in each project. Verification: compare named source evidence and inactive-file exclusions with scanner output and the server's file tree for each profile.
- [ ] **4.8 Define coverage-only exclusions.** Keep helpers/deployment/simulation visible for issue analysis while excluding only justified, currently unmeasured sources from coverage. Record the reason for each exclusion. Do not exclude `Program.cs`, all Razor, all TSX, or all production files merely to improve percentages. Verification: report clearly distinguishes excluded coverage from zero coverage and unavailable coverage.
- [ ] **4.9 Check language support honestly.** Enable `sonar.scanner.scanAll=true` and UTF-8. Generate React Router types/typecheck inputs before analysis if required by its TSConfig. Verify C#, Razor source locations, TS/TSX, handwritten CSS, Python, Dockerfile, and supported IaC examples. Verification: record actual analyzed files/languages and unsupported inputs; language totals alone are insufficient.
- [ ] **4.10 Validate complete React test evidence.** Run coverage with the current ordinary unit suite and a Vitest JSON result reporter. Validate passed/failed/skipped counts using the same approved expectation as CI. Verification: no missing or skipped test can be hidden behind successful LCOV creation; ordinary `npm test` still does not enable coverage.

### Phase 5 — Reliable full-scan driver

- [ ] **5.1 Install the pinned scanner explicitly.** Read `tool-versions.json`, install/reuse `dotnet-sonarscanner` at an absolute per-user versioned path, and validate its version. Fail if a mismatched executable occupies that path. Verification: normal EF tooling and app CI do not download or invoke this scanner.
- [ ] **5.2 Establish immutable run identity.** Require a clean audit worktree at the wrapper's pinned SHA. Record full SHA, project, frontend profile, UTC times, tool/server versions, settings digest, and coverage/test mode before starting. Verification: a dirty tree, unexpected ref, or mismatched profile fails before `begin`.
- [ ] **5.3 Prepare React inputs outside scanner instrumentation.** For React, run `npm ci`, API contract check, typecheck, and explicit coverage before scanner begin. These helpers can invoke .NET; keep them outside the begin/end window. Run every child with the pinned toolchain. Verification: no unrelated .NET build occurs inside an active scan and no committed generated file changes.
- [ ] **5.4 Execute one profile sequence.** Implement section 4.3's exact begin/restore/build/test/validate/end sequence, testing only the Test project and importing direct GUID-child reports. Do not use unsupported `sonar.sources`/`sonar.tests`. Verification: only a complete validated sequence reaches `end`, inherited opt-ins are disabled for these children, and the parent environment is restored.
- [ ] **5.5 Upload and bind processing identity.** Run `end`, read `report-task.txt`, poll that exact `ceTaskId`, and retain the returned `analysisId`. Treat `FAILED`, `CANCELED`, and timeout as failures. Verification: the run points to a successful exact task, not merely a currently green dashboard.
- [ ] **5.6 Bind gate and reports to the analysis.** Query gate status by `analysisId`. Check server analysis revision/version/project against the pinned run before and after exporting mutable latest-view endpoints. Hold the project/run lock through export. If an outside scan changes latest state, fail or retry explicitly; never label its results with this run's SHA. Verification: a simulated concurrent analysis cannot produce a falsely attributed report.
- [ ] **5.7 Finalize on every path.** Use `try/catch/finally` for environment restoration, log sanitization, owned scanner cleanup, process shutdown, lock release, and a final summary. Avoid `exit` bypassing cleanup inside helper functions. Verification: forced build/test/end/export/time-out failures each retain a truthful summary and release owned resources.
- [ ] **5.8 Protect main from candidate scans.** Route explicit clean committed candidate runs to SHA-specific projects with `baselineEligible=false`; require all tests/coverage and reject dirty inputs. Do not port `-SkipTests`, `-AllowDirty`, or `-NoExport`. Verification: candidate validation cannot replace either trusted profile's previous good analysis.
- [ ] **5.9 Test partial batch failure.** Inject failure into the second profile after a successful first profile. Verification: the successful report survives, the batch returns nonzero and is not accepted as a complete baseline, no server analysis is deleted, and cleanup records both profiles accurately.

### Phase 6 — Durable reports and actionable ranking

- [ ] **6.1 Port the API client and fixtures.** Keep dependency-light Python and reader-token-only GET requests. Capture sanitized current-server fixtures for issues, measures, analyses, gate, files, and supported hotspot data. Verification: fixture tests run offline with neither Docker nor real credentials.
- [ ] **6.2 Prove completeness.** Preserve pagination, issue-key deduplication across qualities, and splitting above the 10,000-result limit. Handle an oversized individual rule partition or declare incompleteness explicitly. Compare retrieved totals against API totals. Verification: boundary fixtures for empty, multi-page, duplicate-impact, and oversized partitions cannot silently truncate.
- [ ] **6.3 Do not swallow missing security data.** ImprovedDb's exporter treats hotspot endpoint errors as an empty list. Replace that behavior with capability/status metadata. Unsupported, forbidden, unreachable, and genuinely empty are different states. Verification: 403/404/503 fixtures produce truthful warnings or a failed required export, never “no hotspots” without evidence.
- [ ] **6.4 Produce the Markdown report.** Include run identity, settings, actual scope, test/coverage completeness, informational gate, security/reliability findings, hotspots requiring review, top rules, duplication, and ranked files. Include exact `rule path:line`, issue key, impact, and suggested effort for actionable findings. Bound example lists and link to full JSON.
- [ ] **6.5 Preserve meaningful risk ranking.** Adopt ImprovedDb's existing heuristic and label it as a heuristic: `sqrt(cognitive) * (1 + log2(1 + commits)) * (1 + uncovered) + 10 * log2(1 + reliability/security issues) + 2 * log2(1 + other issues)`. Use a 180-day churn window. For ranking only, missing coverage uses 0.5 uncovered and carries a visible fallback flag; coverage itself stays null. Files with no coverable lines use 0 uncovered. Verification: fixtures sort deterministically without misleading coverage percentages or duplicated issue-impact counts.
- [ ] **6.6 Produce a batch index.** Join profile reports by SHA and configuration. Deduplicate shared findings for triage using rule/path/line/message while retaining both profile references. Do not sum shared LOC/issues or average profile coverage into a fabricated repository metric. Verification: a shared backend issue appears once in the backlog and links to both profiles.
- [ ] **6.7 Describe comparison limits.** Record prior analysis/version, settings digest, and tools. Changing exclusions/rules/profile/tools changes comparability. “New code” from the server is not guaranteed to equal a Git diff. Verification: first run says no comparison baseline; configuration changes visibly invalidate simple before/after claims.
- [ ] **6.8 Sanitize archives.** Omit authors' emails, machine paths, secrets, and unneeded source excerpts from retained reports. Keep JSON schema version and all issue locations required for later work. Verification: token sentinels and known private paths cannot survive export/archive.

### Phase 7 — One-command audits and optional MCP

- [ ] **7.1 Implement the public entry point.** Implement exactly section 4.3's parameter contract and defaults. Do not add experimental switches or implicit lifecycle hooks. Verification: the documented commands work and invalid mode/flag combinations fail before side effects.
- [ ] **7.2 Pin and create audit worktrees.** Implement section 4.3's separate default-main/candidate source selection and script-root rules. Resolve local context before worktree creation; use the same SHA for both requested profiles. Verification: candidates include all new committed tooling, main baselines analyze merged code, every source tree is immutable, and ordinary active work is untouched.
- [ ] **7.3 Manage server ownership.** Initialize/start only the resolved dedicated stack. Track whether this command started it. Archive reports, stop owned startup by default, and leave previously running state alone. Verification: success and failure both meet decision 13; `-KeepServerRunning` leaves a usable dashboard.
- [ ] **7.4 Archive before deleting.** Copy sanitized reports to the per-user repository namespace and verify their contents before removing audit worktrees. Remove only run-created worktrees after checking tracked/untracked user changes. If archive fails, retain the worktree and explain recovery. Verification: printed report paths still exist after cleanup.
- [ ] **7.5 Add the MCP launcher.** Run the pinned official image over stdio on the owned Docker network. Resolve the selected profile, use its reader token via environment, set `SONARQUBE_READ_ONLY=true`, and restrict toolsets to investigation. Send launcher diagnostics to stderr, never stdout. Do not mount Docker socket or source with write access. Verification: an MCP handshake/tool query succeeds without protocol pollution.
- [ ] **7.6 Verify least privilege headlessly.** Implement `probe_sonar_mcp.py` using JSON-RPC stdio initialize, initialized notification, tools/list, and read-only tool calls against the launcher. Use bounded timeouts and the negotiated protocol version. Verify issues/rules/measures/coverage/gate queries and absent mutation tools. Do not assume `SONARQUBE_PROJECT_KEY` universally restricts tools; the profile reader's actual permissions enforce access. Verification: both profile probes succeed without a configured desktop/Claude client or credentials outside the owned store.
- [ ] **7.7 Document optional client configuration.** Provide registration instructions without literal secrets or machine paths in tracked files. Preserve existing ImprovedDb entries. Do not perform client registration during this goal. Registration must never start Sonar automatically; clients that start MCP processes on launch should leave this entry disabled until selected. Verification: headless probes and exported reports complete acceptance without client trust/reload actions.

### Phase 8 — Validation, documentation, and tooling PR

- [x] **8.1 Run focused offline tests.** Run Python summarizer/exporter suites, PowerShell helper/driver tests, and relevant scope/settings contract checks. Ran `python -m unittest discover -s Scripts/Quality/tests -p 'test_*.py'` (58 passed), `Test-SonarQualityModule.ps1` (12 assertions), `Test-SonarQualityFoundation.ps1`, and `Test-SonarQualityAuditContract.ps1`. Tests use fixtures and temporary secret sentinels.
- [ ] **8.2 Protect opt-in behavior.** Check normal profile builds and ordinary npm tests again. Inspect application Compose and workflow changes. Offline test execution in CI is allowed; live Sonar startup/scan/coverage, a new Sonar check, and scheduled triggers are not. Verification: ordinary workflow evidence shows no live Sonar work.
- [x] **8.3 Add operator documentation.** Provide literal first-use, routine audit, quick audit, one-profile, dashboard/MCP, stop, token rotation, report-location, failure recovery, backup/upgrade, and fork identity instructions. Explain persistent history and stopped-server MCP behavior. Commands use relative repository paths or computed Git roots.
- [x] **8.4 Link the second quality tool.** Added links from README and Test docs plus fork identity guidance. Lighthouse remains runtime measurement; Sonar remains source findings, with no automatic coupling or duplicate test guide.
- [ ] **8.5 Preserve candidate acceptance evidence.** Commit the candidate, then run Full `-Candidate` for both profiles. Record exact SHA, tasks, scope/coverage samples, redaction, MCP probes, and stop/restart persistence in ignored notes for the tooling PR. Verification: live server behavior passed locally; CI is not its first test. Repeat affected evidence whenever a code/configuration correction changes the candidate SHA.
- [ ] **8.6 Run the required local gate.** Follow the complete current `docs/Test.md#local-gate`, including format, both profile tests, deployment audit, script/template/YAML/ShellCheck/actionlint checks. Also run `yamllint docker/sonarqube/compose.yaml`; the existing YAML gate does not include this new path. Validate scoped Compose with `config --quiet` using protected process-local variables, without dumping resolved credentials. Run .NET build/test sequentially. Run React `npm ci`, `api:check`, typecheck, lint, tests, and build because its package/config changed. Only rerun broader checks after a relevant change or failure.
- [ ] **8.7 Open the tooling PR.** Stage explicit paths, review `git diff --check`, include focused and full validation evidence, and note no deployment is needed. Merge only with `build-test-push` green on the exact PR head. Verification: record tooling merge SHA and wait for green `main` CI. CI reports do not substitute for 8.5's local server acceptance.

### Phase 9 — Baseline, triage, and closeout

- [ ] **9.1 Audit merged main literally.** Follow the new documented full-audit command with both profiles on one fetched SHA. Do not reuse candidate/scaffold results as the accepted baseline. Verification: both processing tasks succeed, exports match exact analyses, coverage maps to named production files, and reports survive cleanup.
- [ ] **9.2 Record compact evidence.** Write `Plans/Support/SonarQubeOnDemandQuality/Baseline.md` with analyzed SHA, driver/tool versions, profile scope, gate, language LOC, coverage denominator, tests, counts, runtimes, report digests, and limitations. Keep machine-specific archival paths in ignored local notes. No guessed coverage threshold or copied ImprovedDb issue count is an acceptance criterion.
- [ ] **9.3 Triage high-value findings.** Read actual code for security, reliability, and highest-risk examples. Classify each as confirmed defect, worthwhile improvement, reviewed noise, or deferred design work. A security hotspot is a review task, not automatically a vulnerability. No blanket `NOSONAR` or rule deactivation to manufacture a green report.
- [ ] **9.4 Create the improvement backlog.** Write `Plans/CodeQualityImprovements.md` from the accepted report with the template in section 8. Prioritize correctness/security, then valuable low-effort work, then tested refactors. Include both frontends and shared infrastructure findings as appropriate. Do not begin those changes unless authorized by scope.
- [ ] **9.5 Respect the accepted stop point.** Verify all reported application improvements remain backlog items and no unrequested remediation changes were included. Record future quick wins with exact issue evidence and acceptance criteria. Verification: tooling/baseline/backlog are complete; implementing the backlog is not required to tick this task.
- [ ] **9.6 Integrate evidence and backlog.** Review the complete documentation-only PR diff and run `git diff --check`. Merge with `[skip ci]`, fetch, and verify its content on `origin/main`; do not wait for documentation PR/main CI. Mixed PRs retain the full code gate. Record documentation merge SHA and verification alongside the tooling merge's green exact-main CI in this plan or PR descriptions.
- [ ] **9.7 Finish resource accounting.** Confirm no run-owned worktree/process/scanner state remains; reports are archived; owned server is stopped unless explicitly retained; all history volumes remain; ImprovedDb/application resources are unchanged. Mark this plan complete only when required PRs are integrated, tooling exact-main CI is green, and the final Markdown content is verified on `origin/main`.

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

# Validate committed tooling before merge; this writes only candidate project history.
pwsh -NoProfile -File Scripts/Quality/Invoke-CodeQualityAudit.ps1 -Mode Full -Candidate

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
| Candidate validation | Clean committed SHA, complete tests/coverage, candidate keys, and `baselineEligible=false`; trusted baseline remains intact. |
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

Delivery uses two required implementation PRs, after integrating the planning documentation packet if needed:

1. Tooling, coverage plumbing, offline tests, and operator documentation. Validate locally and on exact PR head before merge.
2. Accepted baseline evidence, improvement backlog, and plan execution record. Review and `git diff --check` are required; the Markdown-only exception permits merging with `[skip ci]` without waiting for PR/main CI. Verify integration on fetched `origin/main`.

Application remediation PRs belong to future work and are outside this goal. Each code/configuration or mixed PR uses the full current local gate and exact-head/main CI; never use skip markers for those PRs. No PR requires a production deployment for tooling acceptance. The final documentation merge changes only excluded documentation; its accepted baseline can cite the tooling merge SHA without an endless scan/edit/rescan cycle. The operator requested the ImprovedDb-inspired docs-only exception: classify the complete PR, preserve enforced protection, and verify the integrated content rather than requiring a new build of unchanged source.

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
| Operator preferences | Resolved | All recommendations accepted on 2026-10-11; section 12. |
| Collector/source/host preflight | Complete | Section 2.5; 5 BlazorAuto and 1 React focused tests passed with production XML coverage; frozen source fetched. |
| Phase 0 current baseline | Complete | Planning PR #173 merged as `09040e564a08659c23c2a2c730f52875e5392ac5`; both profile Release builds passed with zero warnings/errors; runtime/resource/reuse evidence and package graphs are recorded in ignored `Plans.local/SonarQubeOnDemandQuality/`. |
| Phases 1–7 tooling | In progress | Core scripts, Compose stack, coverage wiring, reports, and MCP probe are implemented. Focused tests pass: 61 Python tests, 12 PowerShell module assertions, the PowerShell foundation suite, and the audit-contract suite. Both-profile Quick audit succeeded on the implementation tree; normal restore left zero analyzer package references in active project assets. The dedicated candidate stack is healthy. Both profile scans now pass builds, tests, and coverage and upload successfully. Report retrieval exposed a helper that exists only in the server script; the analysis driver now uses the module's exported auth-header function. Candidate rerun remains. |
| Phase 8 local gate and tooling PR | In progress | Focused offline tests and operator/fork documentation are complete. Candidate acceptance and the full local gate remain. |
| Tooling merge and main CI | Not started | |
| Phase 9 accepted full baseline | Not started | |
| Backlog/evidence Markdown integration verification | Not started | No docs-only CI wait. |
| Application remediation wave | Outside accepted goal | Prioritized backlog only. |
| Resource closeout | Not started | |

Record corrections here with the disproved assumption, evidence, and replacement instruction. Continue autonomously through routine implementation choices already covered by the plan.

## 12. Accepted decisions and review corrections

The operator accepted every recommendation on 2026-10-11. Use a dedicated repository server, complete tooling/baseline/backlog, and leave the first application-improvement PR for a later goal. No scope question remains. Optional personal MCP registration and unrelated system-wide upgrades are not completion gates.

Executor review identified and resolved these risks:

| Original execution risk | Resolution |
| --- | --- |
| A configured ImprovedDb remote did not contain the frozen source object. | Fetched and verified the commit; section 2.2 gives the exact missing-object recovery. |
| Candidate source, script root, and project identity were ambiguous before tooling reached main. | Sections 4.3/4.6 define committed candidate worktrees, separate project keys, and mandatory pre-merge candidate acceptance. |
| Too many optional scope branches could cause repeated questions or unbounded work. | Fixed version-1 flags, exact initial tool pins, no dirty Full/skipped-test experiments, no remediation wave, no required desktop MCP configuration. |
| Password/token persistence could strand an otherwise healthy server after interruption. | Pending/confirmed journals, exact owned-token recovery, atomic encrypted file promotion, and explicit interruption tests. |
| A file-based lock could appear permanently stale after a crash. | OS-held exclusive handle releases on process death; metadata/file existence is not ownership. |
| Quick analysis could leave optional analyzer packages in default build inputs. | Normal selected-profile restore runs in the driver finalizer, tested after success and failure. |
| Windows Git rejected the private full-audit worktree path at 263 characters; profile Git checks also reported deep tracked paths as dirty without long-path support. | A command-scoped `core.longpaths=true` worktree add/remove succeeded. Both the Full driver and profile driver now apply it to Git operations. At a 272-character file path, plain `git status` reported four false modifications; the configured status was clean. |
| The first Full candidate retry reached the server lifecycle wrapper but array splatting bound switch strings positionally. | The wrapper now forwards lifecycle actions through a named parameter hashtable. The failure occurred before Docker startup; the archived run retained its failure summary and cleaned its worktree. |
| Server action validation used `.Count` on a scalar under strict mode, and `-Status` rejected a missing first-use DB password before Compose could apply its safe placeholder. | Explicit action arrays and `[AllowEmptyString()]` fix both cases. A temporary-context contract test verifies one action reaches the scoped Compose call and rejects invalid combinations before service changes. |
| SonarQube rejected `ps=500` on group permissions with HTTP 400 (`ps` must be less than 100), grants default `admin` permission to `sonar-administrators`, and denied project-token generation without project `scan`; raw JSON archive scanning also treated an escaped apostrophe as a UNC path. | Page Sonar APIs in batches of 100 and verify reported totals. Preserve administrator `admin` and `scan` permissions, with no other non-reader group access. Parse archived JSON before scanning decoded strings; keep raw checks for non-JSON files and allow empty string-collector lists during recursion. |
| Retrying reader setup attempted to add a group membership already created by an earlier partial run. | Read current reader groups first, add the owned reader group only when absent, then verify the exact expected membership set. |
| The pinned .NET scanner executable rejects `--version` and reports that `begin` or `end` is required. | Verify the exact package ID, command, and pinned version through `dotnet tool list --tool-path <versioned-directory> --format json`; keep the scanner executable check for existence. |
| Full-profile preparation set `FrontendProfile` in child environments even though `Directory.Build.targets` rejects the environment override; archive sanitization also missed `file:///C:/...` diagnostics. | Pass profile only through explicit `-p:FrontendProfile=...` arguments. Replace and reject Windows file-URI paths during archive sanitization. |
| Blazor scanner argument validation treated its intentionally empty React LCOV path as invalid. | Allow an empty `ReactLcov` parameter; add the LCOV scanner property only for React. |
| Microsoft coverage XML includes nonphysical source-generator files under `obj` and SourceLink paths under `/_/src`; React validation rejected valid coverage when every file had at least one covered line. | Ignore generated paths and external SourceLink virtual paths consistent with scanner scope. Require every included React app source plus valid covered-line totals; do not require one file to have zero coverage. |
| After scanner upload, report retrieval called `Get-QualityApiHeaders`, a function local to the server lifecycle script. | Use the exported `New-QualityAuthHeader` function from the imported quality module. |
| Coverage collection was assumed and duplicate files could distort import. | Both profile probes passed with the existing collector; direct GUID-child glob imports one canonical copy. |
| React still compiles Client through solution/test references. | Explicit profile scope matrix and named server-inventory checks; no blanket Login exclusion. |
| A second-profile failure could produce a misleading successful overall audit. | Per-profile status preservation and a nonzero, baseline-ineligible batch outcome. |
| Client trust prompts could become artificial mandatory blockers. | Headless MCP handshake/tool probes provide acceptance without registration or paid clients. |
| Code smells in inherited scripts could spread into the template. | Explicit exports/context, argument-array process launching, bounded deadlines, owned cleanup, staged output sanitization, and truthful API completeness. |

If new evidence disproves a fact, correct this table and the affected task, then continue within accepted scope. Stop only for a concrete inaccessible permission/credential or other real hard stop; report its exact evidence. Do not ask again about routine choices already settled here.
