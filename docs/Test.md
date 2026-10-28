# Test

Use the full local gate for code, configuration, and other non-Markdown changes. Tests require Docker for PostgreSQL and Redis Testcontainers. Browser suites are opt-in; see [Browser testing](Testing/Browser.md). Fixture and architecture details live in [Infrastructure testing](Testing/Infrastructure.md). React package checks and contract generation live in [Frontend/React](Frontend/React.md).

## Normal run

Run `dotnet test` for the selected frontend profile; E2E tests stay skipped unless `RUN_E2E=1`. To validate both frontend compositions, run the profile script below. It restores separate profile inputs and verifies test result categories (no failures, no unexpected outcomes, and skips only for explicit `Set RUN_…=1` opt-ins); no test count is pinned:

```bash
bash Scripts/CI/validate-frontend-profiles.sh /tmp/frontend-profile-results
```

Run this when validating both compositions. It needs Docker. CI also builds and smoke-tests both profile images; the current workflow stages are in [ci.yml](../.github/workflows/ci.yml). Do not run build and test concurrently in the same checkout.

## GitHub Actions reports

The workflow policy requires an explicit `self-hosted` runner label; a runner group name does not establish runner type. Each `actions/setup-node` step must set `package-manager-cache: false`. Each CodeQL initialization step must set `env.CODEQL_OVERLAY_DATABASE_MODE: none` to preserve full scans without overlay caches. The audit also follows local reusable workflows and composite actions.

Publication, deployment and registry retention share a non-cancelling `queue: max` group, which retains up to 100 pending requests. The policy checks every workflow or job using the publisher's group, including case-insensitive matches. The local gate uses the pinned queue-aware actionlint runner below.

CI stores full TRX and React unit-test reports, plus available browser screenshots and traces, on the self-hosted runner. Packaged smoke TRX files use the same terminal job directory. Routine reports do not use GitHub artifact storage. Each terminal job summary reports test totals, the runner name, a retrieval command, and observed report-store size. Run that command on the same runner after checking out the reported commit. Reports expire after 3 days for successful jobs and 7 days for failed jobs; pins and active-reader locks protect selected reports. The LocalSingleNode maintenance workflow reports store usage and prunes expired reports under the shared deployment lock.

CI may use optional native/desktop runner profiles; native mode remains the default. Profile mode verifies the selected runner and every configured workspace, Docker, report and temporary filesystem root. The native deployment-volume reserve remains active for native jobs. See [CI runner profiles](CI/RunnerProfiles.md) before enabling the route. The stable `build-test-push` result gate also rejects skipped runner selection, validation or required main publication.

## Local Gate

For ordinary Markdown-only changes, follow the documentation exception in [AGENTS.md](../AGENTS.md#changes-and-checks). Mixed PRs use the full gate below.

Run every command successfully before pushing non-Markdown changes. Use Linux or WSL with the pinned .NET SDK, Python 3, Docker, and ShellCheck available in that environment. The virtual-environment paths below assume Linux.

```bash
git diff --check
dotnet restore GrumPlates.sln
python3 -m unittest Scripts/CI/tests/test_frontend_profile.py Scripts/CI/tests/test_frontend_release.py Scripts/CI/tests/test_ci_report_store.py
python3 -m unittest Scripts/CI/tests/test_runner_profiles.py Scripts/CI/tests/test_select_ci_runner.py Scripts/CI/tests/test_verify_ci_runner.py Scripts/CI/tests/test_ci_runner_routing_workflow.py Scripts/CI/tests/test_require_ci_results.py
python3 -m unittest Scripts/CI/tests/test_workflow_policy.py
python3 Scripts/CI/workflow_policy.py --repo-root .
dotnet format GrumPlates.sln --verify-no-changes --verbosity minimal --no-restore
bash Scripts/CI/validate-frontend-profiles.sh /tmp/frontend-profile-results # needs Docker
bash Deployment/Common/Scripts/validate-common-release.sh
bash Deployment/Cloud/Scripts/validate-cloud-settings.sh
bash Deployment/Common/observability/scripts/validate-observability.sh
bash Deployment/LocalCluster/Scripts/audit-deployment.sh
python3 -m unittest Deployment/LocalCluster/Scripts/Tests/test_doc_slice_loader.py -v
python3 -m venv /tmp/tpl-venv && /tmp/tpl-venv/bin/pip install --constraint Deployment/Common/ci-python-constraints.txt jinja2 yamllint
PATH="/tmp/tpl-venv/bin:$PATH" bash Deployment/LocalCluster/Scripts/validate-rendered-templates.sh
PATH="/tmp/tpl-venv/bin:$PATH" yamllint .github Deployment docker-compose.yml .yamllint.yml
find Deployment Scripts/CI -type f -name '*.sh' -print0 | xargs -0 shellcheck --severity=warning
bash Scripts/CI/run-actionlint.sh
```

If `GrumPlates.Client/Styles` or Razor classes change, run `npm ci && npm run css:build` from the client project and commit the generated `GrumPlates/wwwroot/tailwind.css` when it changes. Changes to deployment scripts also require suites under `Deployment/LocalCluster/Scripts/Tests/`, `Deployment/Common/Scripts/Tests/`, `Deployment/LocalSingleNode/Scripts/Tests/`, and `Scripts/CI/tests/`; CI's validate job lists the current commands.

## Lighthouse Performance

See [browser performance checks](Testing/Browser.md#lighthouse-performance). Optional static/source audits are in [Quality tools](Quality/QualityTools.md) and [SonarQube](Quality/SonarQubeAnalysis.md); they are not merge gates.
