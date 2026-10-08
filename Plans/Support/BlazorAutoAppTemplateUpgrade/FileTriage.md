# BlazorAutoAppTemplate upgrade: file triage inventory

Generated from ImprovedDb `2073e2ec19b5ae5383132f75b90357c3d70e7751` and BlazorAutoAppTemplate `ad710610c9a6c0df8380cf1eb257226cb7d41bc7`. The plan is [../../BlazorAutoAppTemplateUpgrade.md](../../BlazorAutoAppTemplateUpgrade.md). When this table and a plan step disagree, the plan step wins.

## Decision legend

| Decision | Meaning |
| --- | --- |
| PORT | Copy the ImprovedDb file, then apply the plan's rename rules (section 3.4). |
| ADAPT | Port only the hunks the note and the plan phase name. Keep template-specific content. |
| REVIEW | Diff manually in the named phase. Port only generic fixes; record what you did in the PR. |
| KEEP-TEMPLATE | The template version stays. It is newer, or ImprovedDb's change is product-specific. |
| SKIP-DOMAIN | ImprovedDb product content (media, people, awards, data import). Never port. |
| SKIP-COMPLEX | ImprovedDb-only operations (coordinator, supervisor, desktop CI, data runner). Never port. |
| REGENERATE | Never copy; regenerate with the tool named in the note. |
| DEFER | Valuable but out of scope for this plan; see the plan's Deferred section. |

Totals: ADAPT 79, DEFER 31, KEEP-TEMPLATE 30, PORT 39, REGENERATE 1, REVIEW 18, SKIP-COMPLEX 36, SKIP-DOMAIN 65.

## A. Files present in both repositories whose content differs

Diff column: lines added/removed going from the template to ImprovedDb.

| File | Diff | Decision | Phase | Note |
| --- | --- | --- | --- | --- |
| `.config/dotnet-tools.json` | +1/-1 | KEEP-TEMPLATE | P4 | Version-only drift; keep the newest version on either side, never downgrade. |
| `.dockerignore` | +3/-0 | KEEP-TEMPLATE | - | ImprovedDb additions are product paths (LocalData, AwardPredictionLab, capacity script). |
| `.env.example` | +89/-2 | SKIP-DOMAIN | - | Only DataImport/provider keys were added. Keep template. |
| `.github/workflows/auto-merge-dependabot.yml` | +394/-31 | ADAPT | P6 | Port the hardened evaluation (exact head SHA, run identity, BEHIND refresh, disable auto-merge on excluded PRs). Runner label must stay variable-driven. |
| `.github/workflows/cd-cloud.yml` | +11/-26 | ADAPT | P7 | Template is NEWER for SSH-key handling (runner-local key, fingerprint). Port only GHCR-via-GITHUB_TOKEN; keep everything else from template. |
| `.github/workflows/cd-localcluster.yml` | +333/-56 | ADAPT | P7 | Port exact-SHA/manifest/digest verification and DOCKER_CONFIG isolation. Do NOT port coordinator, supervisor, request/operation IDs, data-import secrets, refresh_rating_ranks. |
| `.github/workflows/ci.yml` | +767/-121 | ADAPT | P5 | Port concurrency fix, validate/publish split, release manifest, smoke, TRX upload, check-only prereqs. Do NOT port desktop runner selection, ML/statistics steps, coordination tests. |
| `.gitignore` | +16/-2 | ADAPT | P10 | Port: track /Plans, ignore /Plans.local/ and .claude/settings.local.json. Skip LocalData/AwardPredictionLab lines. |
| `BlazorAutoApp.Client/Features/AppShell/Layout/MainLayout.razor` | +12/-3 | ADAPT | P2 | Port only the hidden app-interactivity-probe span. Keep template colours/layout. Footer link is optional (no /about page in template). |
| `BlazorAutoApp.Client/Features/AppShell/Layout/NavMenu.razor` | +141/-57 | SKIP-DOMAIN | - | Media navigation and search box. |
| `BlazorAutoApp.Client/Features/AppShell/Routes/NotFound.razor` | +9/-3 | ADAPT | P2 | Port data-testid hooks and a link back to '/'. Do not depend on MediaShared.CatalogStatePanel. |
| `BlazorAutoApp.Client/Program.cs` | +37/-9 | SKIP-DOMAIN | - | Only feature registrations differ. |
| `BlazorAutoApp.Client/Styles/input.css` | +1237/-0 | SKIP-DOMAIN | - | Product theme. Regenerate tailwind.css only if template markup changes. |
| `BlazorAutoApp.Client/_Imports.razor` | +1/-0 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp.Client/package-lock.json` | +389/-392 | REGENERATE | P4 | Never copy. Run npm install in BlazorAutoApp.Client after editing package.json, commit the result. |
| `BlazorAutoApp.Client/package.json` | +9/-3 | ADAPT | P4 | Add axe-core devDependency (used by E2E accessibility helper). Keep newest versions; port the @parcel/watcher override only if npm audit/ci needs it. |
| `BlazorAutoApp.Simulation/Auth/BrowserAuthBootstrap.cs` | +2/-2 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Browser/BrowserSampler.cs` | +81/-120 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/HelpText.cs` | +7/-7 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Http/HttpScenarioClient.cs` | +1/-1 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Options/TargetProfile.cs` | +2/-2 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/README.md` | +14/-11 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Reporting/SimulationReport.cs` | +7/-7 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Reporting/SimulationReportWriter.cs` | +4/-4 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Running/AuthCheckRunner.cs` | +5/-5 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Running/AuthenticatedScenarioRunner.cs` | +63/-137 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Running/ScenarioRunner.cs` | +10/-10 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Scenarios/Scenario.cs` | +18/-27 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Simulation/Scenarios/ScenarioCatalog.cs` | +11/-7 | SKIP-DOMAIN | - | Scenario/media changes. Template simulator keeps Books scenarios. |
| `BlazorAutoApp.Test/Architecture/Boundaries/HttpClientUsageTests.cs` | +5/-34 | REVIEW | P3 | Compare; ImprovedDb simplified it. Port only if it removes a false positive without weakening the rule. |
| `BlazorAutoApp.Test/Architecture/Composition/DiWiringTests.cs` | +33/-5 | REVIEW | P3 | Mostly feature lists; port generic assertion helpers only. |
| `BlazorAutoApp.Test/Architecture/Endpoints/EndpointSurfaceTests.cs` | +32/-9 | REVIEW | P3 | Mostly feature lists; port generic assertion helpers only. |
| `BlazorAutoApp.Test/Architecture/Persistence/EntityConfigurationLocationTests.cs` | +11/-4 | REVIEW | P3 | Allows feature-owned server Persistence entities; port the rule relaxation if Books needs none, otherwise keep. |
| `BlazorAutoApp.Test/Architecture/Slices/ArchitectureTests.cs` | +22/-4 | REVIEW | P3 | Port generic rules only. |
| `BlazorAutoApp.Test/Architecture/Slices/FeatureSlicesArchitectureTests.cs` | +56/-35 | PORT | P3 | Per-feature coverage rule plus PassiveRequestDtoConstructionTests_AreNotAllowed. |
| `BlazorAutoApp.Test/BlazorAutoApp.Test.csproj` | +21/-0 | ADAPT | P3 | Add bunit only if you port bUnit tests. Skip DataImport reference and Plans/Support fixtures. |
| `BlazorAutoApp.Test/E2E/AppShell/RenderModeE2ETests.cs` | +5/-6 | ADAPT | P3 | Use the interactivity probe wait. Keep Books selectors. |
| `BlazorAutoApp.Test/E2E/Features/Login/IdentityE2ETests.cs` | +10/-3 | ADAPT | P3 | Port the generic waits and credential helpers. |
| `BlazorAutoApp.Test/E2E/Observability/GrafanaObservabilityE2ETests.cs` | +14/-16 | REVIEW | P3 | Dashboard names differ; port only timeout/stability fixes. |
| `BlazorAutoApp.Test/E2E/Support/BlazorE2ETestBase.cs` | +413/-42 | ADAPT | P3 | Port WaitForInteractivityAsync, viewport/overflow/broken-image/axe helpers, failure tracing, RegisterUniqueUserAsync, LoginAsLocalAdminAsync, artifact paths. Skip media canaries. |
| `BlazorAutoApp.Test/E2E/Support/E2ETestDataCleanup.cs` | +19/-226 | KEEP-TEMPLATE | - | Template must keep Books cleanup; ImprovedDb only removed Books parts. |
| `BlazorAutoApp.Test/E2E/Support/E2ETestGuard.cs` | +16/-0 | ADAPT | P3 | Keep IsEnabled/IsObservabilityEnabled. Skip LocalData/provider/responsive flags. |
| `BlazorAutoApp.Test/E2E/VisualRegression/VisualSnapshotE2ETests.cs` | +59/-62 | REVIEW | P3 | Port the path helper changes only. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/ForwardedHeadersTests.cs` | +3/-5 | ADAPT | P3 | Collection/fixture renames plus small stability fixes; port the fixture usage, keep template routes. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/HeadRequestTests.cs` | +1/-1 | ADAPT | P3 | Collection/fixture renames plus small stability fixes; port the fixture usage, keep template routes. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/ObservabilityTests.cs` | +16/-11 | ADAPT | P3 | Collection/fixture renames plus small stability fixes; port the fixture usage, keep template routes. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/RateLimitingTests.cs` | +137/-14 | ADAPT | P2 | Port static-asset exemption tests (theory + integration). Skip MediaImages policy tests. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/RedisConfigurationTests.cs` | +4/-4 | ADAPT | P3 | Collection/fixture renames plus small stability fixes; port the fixture usage, keep template routes. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/RedisConnectionReuseTests.cs` | +1/-0 | ADAPT | P3 | Collection/fixture renames plus small stability fixes; port the fixture usage, keep template routes. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/RenderModeHtmlTests.cs` | +58/-4 | ADAPT | P3 | Port the static/account pages do-not-load-runtime and no-removed-scoped-css checks with template routes. Skip About page tests. |
| `BlazorAutoApp.Test/Simulation/ContractReuseTests.cs` | +28/-19 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp.Test/Simulation/DeploymentDoesNotPublishSimulationTests.cs` | +7/-21 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp.Test/TestSupport/Integration/SharedIntegrationEnvironment.cs` | +16/-10 | ADAPT | P3 | Port disposal, labels, tmpfs, generic options (ConfigurationOverrides, ConfigureTestServices, rate-limit overrides, UseIdentityCookieChallenge, roles header). Keep Books cache-tag reset. |
| `BlazorAutoApp.Test/TestSupport/Integration/TestAuthenticationHandler.cs` | +11/-1 | ADAPT | P3 | Port disposal, labels, tmpfs, generic options (ConfigurationOverrides, ConfigureTestServices, rate-limit overrides, UseIdentityCookieChallenge, roles header). Keep Books cache-tag reset. |
| `BlazorAutoApp.Test/TestSupport/Integration/TestCollections.cs` | +45/-4 | PORT | P3 | Named collections + MaxParallelThreads=2. Drop collections the template does not use (ContainerImport, SyntheticBrowser). |
| `BlazorAutoApp.Test/TestSupport/Integration/TestContainerImages.cs` | +48/-0 | PORT | P3 | tmpfs data dirs + labels. Replace com.improveddb.ci.* keys with the generic label scheme in the plan. |
| `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs` | +108/-39 | ADAPT | P3 | Port disposal, labels, tmpfs, generic options (ConfigurationOverrides, ConfigureTestServices, rate-limit overrides, UseIdentityCookieChallenge, roles header). Keep Books cache-tag reset. |
| `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactoryOptions.cs` | +26/-6 | ADAPT | P3 | Port disposal, labels, tmpfs, generic options (ConfigurationOverrides, ConfigureTestServices, rate-limit overrides, UseIdentityCookieChallenge, roles header). Keep Books cache-tag reset. |
| `BlazorAutoApp.sln` | +14/-0 | SKIP-DOMAIN | - | Adds DataImport project. |
| `BlazorAutoApp/BlazorAutoApp.csproj` | +13/-0 | SKIP-DOMAIN | - | ML/Skia packages. |
| `BlazorAutoApp/Components/App.razor` | +4/-2 | ADAPT | P2 | Fingerprinted favicon via @Assets[...]. Do not add the dark color-scheme meta unless the template theme is dark. |
| `BlazorAutoApp/Components/Pages/Error.razor` | +17/-18 | ADAPT | P2 | Remove the Development-mode text and add data-testid hooks. Use template styling. |
| `BlazorAutoApp/Dockerfile` | +99/-9 | KEEP-TEMPLATE | - | ImprovedDb moved to Ubuntu + dotnet-install for Python/Skia. Template keeps MCR images (Dependabot-trackable). Optionally port '-r linux-x64' on build/publish. |
| `BlazorAutoApp/Features/Login/Account/LoginFeatureExtensions.cs` | +41/-0 | ADAPT | P2 | Move CurrentUserAccessor registration here; port API 401/403 cookie events only if the P2 probe test fails. |
| `BlazorAutoApp/Infrastructure/Hosting/AntiforgeryExtensions.cs` | +1/-0 | SKIP-DOMAIN | - | MyPeople header name. |
| `BlazorAutoApp/Infrastructure/Hosting/AppCachingExtensions.cs` | +35/-1 | ADAPT | P2 | Port HybridCache default options (MaximumKeyLength, MaximumPayloadBytes, ReportTagMetrics=false). Skip PublicDataCache registrations. |
| `BlazorAutoApp/Infrastructure/Hosting/AppRateLimiting.cs` | +61/-0 | ADAPT | P2 | Port static-asset no-limiter partition. Skip MediaImages policy. |
| `BlazorAutoApp/Infrastructure/Hosting/AppRateLimitingOptions.cs` | +8/-1 | ADAPT | P2 | Port static-asset no-limiter partition. Skip MediaImages policy. |
| `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/CacheInvalidationMessage.cs` | +1/-1 | SKIP-DOMAIN | - | Visibility change for DataImport. |
| `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/CacheInvalidationOptions.cs` | +1/-1 | SKIP-DOMAIN | - | Visibility change for DataImport. |
| `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/HybridCacheInvalidationApplier.cs` | +9/-1 | SKIP-DOMAIN | - | Only PublicDataCache memo clearing. |
| `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/HybridCacheInvalidator.cs` | +24/-4 | PORT | P2 | Linked cancellation, CacheInvalidationResult, subscriber WaitAsync, incomplete-message guard. |
| `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/ICacheInvalidator.cs` | +1/-1 | PORT | P2 | Linked cancellation, CacheInvalidationResult, subscriber WaitAsync, incomplete-message guard. |
| `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/RedisCacheInvalidationSubscriber.cs` | +17/-1 | PORT | P2 | Linked cancellation, CacheInvalidationResult, subscriber WaitAsync, incomplete-message guard. |
| `BlazorAutoApp/Infrastructure/Hosting/HeadRequestExtensions.cs` | +1/-4 | SKIP-DOMAIN | - | Route/meter names only. |
| `BlazorAutoApp/Infrastructure/Hosting/ObservabilityExtensions.cs` | +2/-4 | SKIP-DOMAIN | - | Route/meter names only. |
| `BlazorAutoApp/Infrastructure/Persistence/AppDbContext.cs` | +44/-8 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp/Infrastructure/Persistence/Migrations/AppDbContextModelSnapshot.cs` | +1590/-39 | SKIP-DOMAIN | - | Never copy migrations or snapshots between apps. |
| `BlazorAutoApp/Infrastructure/Persistence/PersistenceExtensions.cs` | +6/-1 | PORT | P2 | Register DbCommandInterceptor services through the factory. |
| `BlazorAutoApp/Program.cs` | +67/-7 | ADAPT | P2 | Feature registrations differ. Port the pattern: user-specific API responses get 'Cache-Control: private, no-store' (generalised in plan). |
| `BlazorAutoApp/Properties/AssemblyInfo.cs` | +1/-0 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp/appsettings.Docker.json` | +1/-8 | SKIP-DOMAIN | - | App name and PublicData cache options. |
| `BlazorAutoApp/appsettings.json` | +32/-8 | SKIP-DOMAIN | - | App name and PublicData cache options. |
| `BlazorAutoApp/wwwroot/app.css` | +89/-92 | SKIP-DOMAIN | - | Product CSS. |
| `BlazorAutoApp/wwwroot/tailwind.css` | +5569/-696 | SKIP-DOMAIN | - | Product CSS. |
| `Deployment/Cloud/HowToDeployCloud.md` | +46/-91 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/README.md` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/Component/lib/cloud_settings.py` | +2/-2 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/Component/lib/render-inventory.py` | +2/-2 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/check-github-environment.sh` | +0/-2 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/check-ssh-reachability.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/configure-github-environment.sh` | +5/-13 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/deploy.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/doctor.sh` | +0/-2 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/observability-doctor.sh` | +8/-8 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/open-observability-tunnel.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/preflight.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/quick-destroy-cloud.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/quick-recreate-cloud-after-destruction.sh` | +2/-2 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/render-inventory-from-env.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/render-inventory-from-tofu.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/restore-db.sh` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/Scripts/set-temporary-ssh-firewall.sh` | +10/-175 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/ansible/roles/cloudflared/tasks/main.yml` | +6/-0 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/ansible/roles/observability_backend/templates/docker-compose.yml.j2` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/infra/opentofu/cloud-init.yaml.tftpl` | +1/-1 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/infra/opentofu/terraform.tfvars.example` | +2/-2 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/inventory/prod/group_vars/all.example.yml` | +6/-6 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/inventory/prod/group_vars/all.yml` | +6/-6 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Cloud/inventory/prod/hosts.example.yml` | +3/-3 | KEEP-TEMPLATE | P7 | Template Cloud files are newer (June 19 SSH hardening). Only the GHCR GITHUB_TOKEN change is ported; diffs are otherwise renames or regressions. |
| `Deployment/Common/README.md` | +1/-0 | ADAPT | P11 | Document new release manifest helpers. |
| `Deployment/Common/Scripts/Component/lib/find-successful-ci-run.py` | +265/-64 | PORT | P7 | Exact run id/attempt verification. Generic. |
| `Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py` | +175/-27 | ADAPT | P8 | Diff against template first (template has its own June 19 hardening). Port deployed-artifact protection but replace coordinator-status input with 'protect artifacts of the most recent successful CD run(s)'. |
| `Deployment/Common/Scripts/install-ansible.sh` | +148/-23 | PORT | P8 | --check/--provision split, flock, bounded apt with retries. |
| `Deployment/Common/observability/grafana/dashboard_spec.py` | +24/-24 | SKIP-DOMAIN | - | Dashboard content; template keeps Books dashboards. |
| `Deployment/Common/observability/grafana/dashboards/02-infrastructure-and-data.json` | +8/-56 | SKIP-DOMAIN | - | Dashboard content; template keeps Books dashboards. |
| `Deployment/Common/observability/grafana/dashboards/03-telemetry-and-alerts.json` | +8/-56 | SKIP-DOMAIN | - | Dashboard content; template keeps Books dashboards. |
| `Deployment/Common/observability/grafana/dashboards/04-logs-and-traces.json` | +10/-58 | SKIP-DOMAIN | - | Dashboard content; template keeps Books dashboards. |
| `Deployment/Common/observability/grafana/dashboards/application-overview.json` | +6/-5 | SKIP-DOMAIN | - | Dashboard content; template keeps Books dashboards. |
| `Deployment/Common/observability/grafana/generate-dashboards.py` | +6/-16 | SKIP-DOMAIN | - | Dashboard content; template keeps Books dashboards. |
| `Deployment/Common/observability/scripts/smoke-observability.sh` | +6/-6 | REVIEW | P1 | Small diffs; port only timeout/robustness changes, not names. |
| `Deployment/Common/observability/scripts/validate-observability.sh` | +3/-3 | REVIEW | P1 | Small diffs; port only timeout/robustness changes, not names. |
| `Deployment/Common/release.yml` | +2/-2 | SKIP-DOMAIN | - | Image/bundle names. |
| `Deployment/LocalCluster/HowToDeployLocalCluster.md` | +443/-13 | ADAPT | P11 | Port runner policy, release manifest, maintenance, low-disk recovery, known_hosts seeding sections. Skip data runner/provider sections. |
| `Deployment/LocalCluster/Scripts/Component/lib/audit_deployment.py` | +735/-77 | ADAPT | P1-P8 | Update needle checks in the same commit as each behaviour change. Port ImprovedDb's matching rule when one exists. |
| `Deployment/LocalCluster/Scripts/Component/lib/deploy_settings.py` | +452/-2 | REVIEW | P7 | Mostly data_import_* validation. Port only generic validations (for example capacity thresholds). |
| `Deployment/LocalCluster/Scripts/Component/lib/validate-vault.py` | +25/-1 | ADAPT | P7 | Make vault_ghcr_* optional once CD uses GITHUB_TOKEN; skip provider key checks. |
| `Deployment/LocalCluster/Scripts/Component/with-deploy-lock.sh` | +123/-27 | ADAPT | P1 | Rewrite per plan P1: no age-based reclamation, wait for child on TERM/INT, no python helper dependency. |
| `Deployment/LocalCluster/Scripts/Component/with-node-main-deploy-lock.sh` | +7/-130 | ADAPT | P1 | Remove remote stale cleanup; keep manual deploy path working (ImprovedDb disabled deploy.sh instead). |
| `Deployment/LocalCluster/Scripts/README.md` | +145/-8 | ADAPT | P11 | Document new scripts. |
| `Deployment/LocalCluster/Scripts/acceptance-check.sh` | +70/-4 | ADAPT | P1 | Port curl timeouts. Skip data-runner/statistics/media/award checks. |
| `Deployment/LocalCluster/Scripts/check-github-runner.sh` | +11/-49 | REVIEW | P8 | ImprovedDb version depends on ci_runner_contract.py (desktop CI). Keep template unless a fix is generic. |
| `Deployment/LocalCluster/Scripts/deploy.sh` | +5/-43 | KEEP-TEMPLATE | P1 | ImprovedDb disabled it in favour of a coordinator wrapper. Template keeps the manual path but it must use the fixed node-main lock. |
| `Deployment/LocalCluster/Scripts/ensure-actions-runner-prereqs.sh` | +49/-30 | PORT | P8 | --check/--provision split, bounded apt. |
| `Deployment/LocalCluster/Scripts/install-github-runner.sh` | +47/-79 | ADAPT | P8 | Port fail-closed on broken runner identity (never auto-delete a runner dir). Skip CI_RUNNER_LABEL/desktop label contract. |
| `Deployment/LocalCluster/Scripts/observability-capacity-check.sh` | +5/-3 | REVIEW | P1 | Port robustness fixes only. |
| `Deployment/LocalCluster/Scripts/observability-doctor.sh` | +8/-8 | REVIEW | P1 | Port robustness fixes only. |
| `Deployment/LocalCluster/Scripts/preflight.sh` | +1/-0 | ADAPT | P1 | Add optional inventory DNS validation (generic, opt-in setting). |
| `Deployment/LocalCluster/Scripts/prune-docker-residue.sh` | +149/-30 | ADAPT | P8 | Port low-disk handling and exit-code contract; replace ImprovedDb label filter with the generic repo-scoped label. |
| `Deployment/LocalCluster/Scripts/validate-rendered-templates.sh` | +392/-6 | REVIEW | P1 | Mostly data-runner renders. Port the Prometheus internal-port assertion. |
| `Deployment/LocalCluster/ansible/ansible.cfg` | +1/-0 | PORT | P1 | timeout = 30. |
| `Deployment/LocalCluster/ansible/playbooks/site.yml` | +608/-6 | ADAPT | P7 | Port image staging before app stop, serial:1 app rollout, Caddy/cloudflared after app readiness. Skip coordinator, data runner, rank refresh. |
| `Deployment/LocalCluster/ansible/roles/app/tasks/main.yml` | +92/-10 | ADAPT | P7 | Port command-scoped DOCKER_CONFIG for GHCR pull. Skip provider/LocalData tasks. |
| `Deployment/LocalCluster/ansible/roles/app/templates/app.env.j2` | +10/-0 | SKIP-DOMAIN | - |  |
| `Deployment/LocalCluster/ansible/roles/cloudflared/tasks/main.yml` | +6/-0 | PORT | P1 | Download retries/timeout/force. |
| `Deployment/LocalCluster/ansible/roles/firewall/tasks/main.yml` | +16/-0 | SKIP-DOMAIN | - | Data-runner access rules. |
| `Deployment/LocalCluster/ansible/roles/firewall/templates/app-docker-user-firewall.sh.j2` | +5/-1 | SKIP-DOMAIN | - | Data-runner access rules. |
| `Deployment/LocalCluster/ansible/roles/observability_backend/templates/docker-compose.yml.j2` | +1/-1 | REVIEW | P1 | One-line change; inspect. |
| `Deployment/LocalCluster/ansible/roles/observability_backend/templates/prometheus.yml.j2` | +11/-2 | PORT | P1 | Bug fix: in-network targets must use container ports 12345/9100, not host-published ports. |
| `Deployment/LocalCluster/compose/app-server/docker-compose.yml` | +10/-0 | SKIP-DOMAIN | - |  |
| `Deployment/LocalCluster/inventory/prod/group_vars/all.yml` | +92/-19 | SKIP-DOMAIN | - | Fork-specific values (nodes, ports, hostnames). Never copy ImprovedDb inventory values. |
| `Deployment/LocalCluster/inventory/prod/hosts.yml` | +5/-5 | SKIP-DOMAIN | - | Fork-specific values (nodes, ports, hostnames). Never copy ImprovedDb inventory values. |
| `Deployment/LocalCluster/inventory/prod/vault.example.yml` | +6/-0 | SKIP-DOMAIN | - | Fork-specific values (nodes, ports, hostnames). Never copy ImprovedDb inventory values. |
| `Deployment/LocalCluster/inventory/prod/vault.yml` | +29/-26 | SKIP-DOMAIN | - | Fork-specific values (nodes, ports, hostnames). Never copy ImprovedDb inventory values. |
| `Directory.Packages.props` | +33/-25 | ADAPT | P4 | Port CentralPackageTransitivePinningEnabled. Template versions are mostly NEWER: never downgrade. Add packages only when a ported file needs them. |
| `README.md` | +55/-17 | ADAPT | P11 | Port structural improvements (Requirements link); keep template wording. |
| `Scripts/AnalyzeSimulationReports.ps1` | +6/-1 | REVIEW | P9 |  |
| `Scripts/RunLocal.ps1` | +151/-44 | ADAPT | P9 | Port automatic Docker residue cleanup + -SkipDockerCleanup. Skip agent-task port reservation. |
| `docker-compose.yml` | +6/-1 | ADAPT | P2 | Port APP_NODE_NAME, App__Url, raised local rate limits. Keep Books dashboard path. |
| `docs/HowToAddANewFeature.md` | +20/-11 | ADAPT | P11 | Port Requirements link and lessons; keep Books examples. |
| `docs/HowToForkThisRepo.md` | +5/-5 | ADAPT | P11 | Template text is the base; apply plan P11 changes. |
| `docs/HowToRunLocally.md` | +42/-3 | ADAPT | P11 | Port Local Docker Storage Maintenance section. |
| `docs/ObservabilityGuide.md` | +21/-23 | REVIEW | P11 | Names only, most likely. |
| `docs/SimulationGuide.md` | +57/-49 | SKIP-DOMAIN | - |  |
| `docs/Test.md` | +187/-157 | ADAPT | P11 | Port generic test-gate guidance (collections, tmpfs, lifecycle test, E2E env vars). |

## B. ImprovedDb-only infrastructure files (product files excluded)

| File | Lines | Decision | Phase | Note |
| --- | --- | --- | --- | --- |
| `.github/actionlint.yaml` | 4 | REVIEW | P5 | Port only if the template needs custom runner labels declared. |
| `.github/workflows/localcluster-accepted-release-lock-recovery.yml` | 61 | SKIP-COMPLEX | - | Coordinator recovery / weekly refresh workflows. |
| `.github/workflows/localcluster-bootstrap-lock-recovery.yml` | 61 | SKIP-COMPLEX | - | Coordinator recovery / weekly refresh workflows. |
| `.github/workflows/localcluster-docker-maintenance.yml` | 91 | ADAPT | P8 | Port as scheduled maintenance; drop coordinator status step. |
| `.github/workflows/localcluster-readonly-diagnostics.yml` | 141 | ADAPT | P8 | Optional: read-only diagnostics workflow (disk, lock, containers). Strip data-runner parts. |
| `.github/workflows/localcluster-release-state-ownership-repair.yml` | 46 | SKIP-COMPLEX | - | Coordinator recovery / weekly refresh workflows. |
| `AGENTS.md` | 52 | ADAPT | P10 | Write a slim portable version (plan P10). Skip coordination-script and release-gate references. |
| `BlazorAutoApp.Test/Architecture/AgentGuardrailTests.cs` | 287 | ADAPT | P10 | Port generic guards (no setup-python, build/test separate, no docker volume prune, CD requires exact CI). Skip DataImport/CurrentPC guards. |
| `BlazorAutoApp.Test/Architecture/Boundaries/AuthBoundaryTests.cs` | 88 | SKIP-DOMAIN | - | Old-app Auth0 boundary. |
| `BlazorAutoApp.Test/Architecture/Boundaries/ObsoleteMachineLearningBoundaryTests.cs` | 79 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp.Test/E2E/AppShell/PreHydrationControlsE2ETests.cs` | 92 | ADAPT | P3 | Rewrite for Books buttons: interactive controls disabled before hydration, enabled after. |
| `BlazorAutoApp.Test/E2E/AppShell/ThemeAndIconE2ETests.cs` | 101 | ADAPT | P3 | Optional: icon/favicon assertions only. |
| `BlazorAutoApp.Test/E2E/Support/BrowserSmokeCatalog.cs` | 40 | ADAPT | P5 | Use for the CI Docker browser smoke list with template routes. |
| `BlazorAutoApp.Test/E2E/Support/E2EArtifactPaths.cs` | 53 | PORT | P3 | Generic E2E helpers. |
| `BlazorAutoApp.Test/E2E/Support/E2EArtifactPathsTests.cs` | 31 | PORT | P3 | Generic E2E helpers. |
| `BlazorAutoApp.Test/E2E/Support/E2ELocalAdminCredentials.cs` | 27 | PORT | P3 | Generic E2E helpers. |
| `BlazorAutoApp.Test/E2E/Support/E2ELocalAdminCredentialsTests.cs` | 59 | PORT | P3 | Generic E2E helpers. |
| `BlazorAutoApp.Test/E2E/Support/E2ETestCredentials.cs` | 6 | PORT | P3 | Generic E2E helpers. |
| `BlazorAutoApp.Test/E2E/Support/E2ETestGuardTests.cs` | 94 | PORT | P3 | Generic E2E helpers. |
| `BlazorAutoApp.Test/E2E/Support/ResponsiveViewport.cs` | 37 | PORT | P3 | Generic E2E helpers. |
| `BlazorAutoApp.Test/E2E/Support/SyntheticBrowserCollection.cs` | 9 | DEFER | - | Self-contained synthetic browser env is media-coupled; see plan 'Deferred'. |
| `BlazorAutoApp.Test/E2E/Support/SyntheticBrowserEnvironment.cs` | 507 | DEFER | - | Self-contained synthetic browser env is media-coupled; see plan 'Deferred'. |
| `BlazorAutoApp.Test/E2E/Support/SyntheticBrowserTestBase.cs` | 311 | DEFER | - | Self-contained synthetic browser env is media-coupled; see plan 'Deferred'. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/AppHeadAssetTests.cs` | 107 | ADAPT | P3 | Favicon served/fingerprinted assertions only. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/BrowseHydrationHtmlTests.cs` | 234 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp.Test/Infrastructure/Hosting/CacheInvalidation/HybridCacheInvalidatorTests.cs` | 119 | PORT | P2 | Tests for the invalidator result/cancellation. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/PublicDataCacheGenerationKeysTests.cs` | 22 | DEFER | - | PublicDataCache is deferred. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/PublicDataCacheInvalidatorTests.cs` | 131 | DEFER | - | PublicDataCache is deferred. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/PublicDataCacheKeysTests.cs` | 365 | DEFER | - | PublicDataCache is deferred. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/PublicDataCacheOptionsValidatorTests.cs` | 60 | DEFER | - | PublicDataCache is deferred. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/PublicDataCacheRedisGenerationTests.cs` | 38 | DEFER | - | PublicDataCache is deferred. |
| `BlazorAutoApp.Test/Infrastructure/Hosting/RetiredProductRouteTests.cs` | 37 | SKIP-DOMAIN | - |  |
| `BlazorAutoApp.Test/TestSupport/Integration/HttpProblemDetailsAssert.cs` | 42 | PORT | P3 | Shared ProblemDetails assertion; replaces Books-local ProblemDetailsAssert if equivalent. |
| `BlazorAutoApp.Test/TestSupport/Integration/PostgresTestDatabaseFixture.cs` | 161 | PORT | P3 | Standalone Postgres fixture for startup/seed tests. |
| `BlazorAutoApp.Test/TestSupport/Integration/TestContainerLifecycleTests.cs` | 140 | PORT | P3 | Proves containers are removed and use tmpfs; run by CI with RUN_TESTCONTAINER_LIFECYCLE=1. |
| `BlazorAutoApp.Test/TestSupport/Quality/ApplicationQualityTestGuard.cs` | 12 | DEFER | - | Application-quality manifest is ImprovedDb process. |
| `BlazorAutoApp.Test/TestSupport/Quality/ApplicationQualityTestGuardTests.cs` | 23 | DEFER | - | Application-quality manifest is ImprovedDb process. |
| `BlazorAutoApp.Test/TestSupport/Quality/application-quality-manifest.json` | 100 | DEFER | - | Application-quality manifest is ImprovedDb process. |
| `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation/CacheInvalidationResult.cs` | 26 | PORT | P2 |  |
| `BlazorAutoApp/Infrastructure/Hosting/IPublicDataCacheGenerationStore.cs` | 12 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/IPublicDataCacheInvalidator.cs` | 13 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/LocalPublicDataCacheGenerationStore.cs` | 23 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheEntryOptions.cs` | 49 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheFacade.cs` | 117 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheGenerationKeys.cs` | 21 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheGenerationStore.cs` | 92 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheInvalidationResult.cs` | 34 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheInvalidator.cs` | 131 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheKeys.cs` | 339 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheMetrics.cs` | 46 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheOptions.cs` | 71 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheOptionsValidator.cs` | 44 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheRedisGeneration.cs` | 70 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/PublicDataCacheTags.cs` | 37 | DEFER | - | Generation-based public cache: generic core but domain keys/options. Deferred. |
| `BlazorAutoApp/Infrastructure/Hosting/RetiredRouteStatusCodeExtensions.cs` | 29 | SKIP-DOMAIN | - |  |
| `Deployment/Common/Scripts/Component/lib/download-exact-release-artifact.py` | 304 | DEFER | - | Durable payload pinning belongs to the coordinator design. |
| `Deployment/Common/Scripts/Component/lib/pin_release_payload.py` | 138 | DEFER | - | Durable payload pinning belongs to the coordinator design. |
| `Deployment/Common/Scripts/Component/lib/release_artifact.py` | 230 | PORT | P7 | Replace the 'improveddb-migration-staging-' prefix with a value derived from migration_bundle_name. |
| `Deployment/Common/Scripts/Tests/test_ci_provenance.py` | 135 | PORT | P5-P8 | Tests for ported helpers; adapt fixtures/names. |
| `Deployment/Common/Scripts/Tests/test_pin_release_payload.py` | 140 | SKIP-DOMAIN | - |  |
| `Deployment/Common/Scripts/Tests/test_prune_actions_artifacts.py` | 157 | PORT | P5-P8 | Tests for ported helpers; adapt fixtures/names. |
| `Deployment/Common/Scripts/Tests/test_release_artifact.py` | 191 | PORT | P5-P8 | Tests for ported helpers; adapt fixtures/names. |
| `Deployment/Common/Scripts/Tests/test_release_contract.py` | 111 | PORT | P5-P8 | Tests for ported helpers; adapt fixtures/names. |
| `Deployment/Common/Scripts/validate_release_manifest.py` | 185 | PORT | P7 | Generic manifest validator. |
| `Deployment/Common/ci-python-constraints.txt` | 62 | ADAPT | P5 | Create a small constraints file with only jinja2/yamllint/pip deps the template CI installs. |
| `Deployment/LocalCluster/Scripts/Component/lib/ci_runner_contract.py` | 203 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/Component/verify-coordinator-source.sh` | 30 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/Tests/test-ci-docker-smoke.sh` | 102 | ADAPT | P1-P8 | Port alongside the script under test; remove coordinator expectations. |
| `Deployment/LocalCluster/Scripts/Tests/test-coordinator-source-guard.sh` | 63 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test-deploy-transaction-deferred.sh` | 157 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test-install-ansible-check.sh` | 86 | ADAPT | P1-P8 | Port alongside the script under test; remove coordinator expectations. |
| `Deployment/LocalCluster/Scripts/Tests/test-localcluster-maintenance.sh` | 103 | ADAPT | P1-P8 | Port alongside the script under test; remove coordinator expectations. |
| `Deployment/LocalCluster/Scripts/Tests/test-prune-actions-runner-residue.sh` | 127 | ADAPT | P1-P8 | Port alongside the script under test; remove coordinator expectations. |
| `Deployment/LocalCluster/Scripts/Tests/test-prune-docker-residue-low-disk.sh` | 174 | ADAPT | P1-P8 | Port alongside the script under test; remove coordinator expectations. |
| `Deployment/LocalCluster/Scripts/Tests/test-with-deploy-lock.sh` | 468 | ADAPT | P1-P8 | Port alongside the script under test; remove coordinator expectations. |
| `Deployment/LocalCluster/Scripts/Tests/test_accepted_release_deploy_lock_recovery.py` | 250 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_archive_orphaned_postgres_volumes.py` | 291 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_bootstrap_recovery_failure.py` | 204 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_capture_current_release_identities.sh` | 65 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_ci_release_artifact.py` | 163 | ADAPT | P7-P8 | Port alongside the script under test. |
| `Deployment/LocalCluster/Scripts/Tests/test_ci_runner_label.py` | 185 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_cluster_coordination.py` | 1924 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_coordinated_release_helpers.py` | 112 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_deploy_lock_bootstrap.py` | 219 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_deploy_lock_process_scan.py` | 203 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_deploy_lock_recovery.py` | 644 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_deploy_supervisor.py` | 344 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_prune_ci_residue.py` | 312 | ADAPT | P7-P8 | Port alongside the script under test. |
| `Deployment/LocalCluster/Scripts/Tests/test_stage_release_inputs.py` | 63 | SKIP-COMPLEX | - | Coordinator/supervisor tests. |
| `Deployment/LocalCluster/Scripts/Tests/test_verify_release_identity.sh` | 66 | ADAPT | P7-P8 | Port alongside the script under test. |
| `Deployment/LocalCluster/Scripts/accept-coordinated-deploy-release.py` | 183 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/archive-orphaned-postgres-volumes.py` | 403 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/begin-coordinated-deploy-mutation.py` | 191 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/capture-current-release-identities.sh` | 106 | ADAPT | P7 | Optional: verify running image digest on app nodes after deploy. |
| `Deployment/LocalCluster/Scripts/check-node-main-capacity.sh` | 23 | PORT | P8 | Capacity reserve checks. |
| `Deployment/LocalCluster/Scripts/ci-docker-smoke.sh` | 142 | ADAPT | P5 | Generic disposable Postgres/Redis/app smoke; replace award checks with /health/ready + E2E smoke filter; generic labels. |
| `Deployment/LocalCluster/Scripts/cluster-coordination.py` | 2986 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/deploy_lock.py` | 1585 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/localcluster-capacity-thresholds.sh` | 11 | PORT | P8 | Capacity reserve checks. |
| `Deployment/LocalCluster/Scripts/mark-deploy-lock-phase.sh` | 35 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/prune-actions-runner-residue.sh` | 514 | PORT | P8 | Generic runner/cluster residue cleanup. |
| `Deployment/LocalCluster/Scripts/prune-ci-residue.py` | 307 | ADAPT | P8 | Replace hard-coded repository/prefix with generic labels; replace deploy_lock import with the shell lock wrapper. |
| `Deployment/LocalCluster/Scripts/prune-cluster-docker-residue.sh` | 176 | PORT | P8 | Generic runner/cluster residue cleanup. |
| `Deployment/LocalCluster/Scripts/recover-accepted-release-deploy-lock.py` | 330 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/recover-bootstrap-deploy-lock.sh` | 231 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/retain-ci-release-payload.sh` | 46 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/run-localcluster-deploy-transaction.sh` | 197 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/run-localcluster-maintenance.sh` | 99 | ADAPT | P8 | Drop source-downloads stage and deploy_lock.py call. |
| `Deployment/LocalCluster/Scripts/stage-release-inputs.py` | 46 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/start-localcluster-deploy-supervisor.sh` | 276 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/supervise-localcluster-deploy.py` | 422 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/validate-ci-release-artifact.py` | 10 | PORT | P7 |  |
| `Deployment/LocalCluster/Scripts/validate-inventory-dns.sh` | 42 | ADAPT | P1 | Make the DNS suffix a setting (empty = skip). Never hard-code '.home'. |
| `Deployment/LocalCluster/Scripts/verify-bootstrap-recovery-failure.py` | 225 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/verify-release-identity.sh` | 125 | ADAPT | P7 | Optional: verify running image digest on app nodes after deploy. |
| `Deployment/LocalCluster/Scripts/write-deploy-supervisor-progress.py` | 114 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Deployment/LocalCluster/Scripts/write-destination-sync-receipt.py` | 223 | SKIP-COMPLEX | - | Coordinator, supervisor, recovery, data runner. |
| `Scripts/CI/check-runner-capacity.sh` | 35 | PORT | P5 | CI capacity check that only recovers capacity, never evicts the warm image. |
| `Scripts/CI/migration_staging_artifact.py` | 351 | PORT | P5 | Migration provenance (bundle sha256, ordered migration ids, sdk version). |
| `Scripts/CI/publisher_harness_artifact.py` | 110 | SKIP-COMPLEX | - | Needed only for the desktop/node-main split. |
| `Scripts/CompareCanaryMetrics.ps1` | 567 | SKIP-DOMAIN | - |  |
| `Scripts/DeployLocalCluster.ps1` | 1609 | DEFER | - | Coordination-heavy or ImprovedDb process; plan P7 uses gh workflow run instead. |
| `Scripts/ExportCanaryMetrics.ps1` | 78 | SKIP-DOMAIN | - |  |
| `Scripts/InitializeLocalData.ps1` | 269 | SKIP-DOMAIN | - |  |
| `Scripts/MeasureTests.ps1` | 481 | DEFER | - | Coordination-heavy or ImprovedDb process; plan P7 uses gh workflow run instead. |
| `Scripts/PruneLocalDockerResidue.ps1` | 134 | PORT | P9 | Replace image/compose names with the template's. |
| `Scripts/RunApplicationQuality.ps1` | 337 | DEFER | - | Coordination-heavy or ImprovedDb process; plan P7 uses gh workflow run instead. |
| `Scripts/RunDailyMdblistRefresh.ps1` | 162 | SKIP-DOMAIN | - |  |
| `Scripts/RunDailyOmdbRefresh.ps1` | 158 | SKIP-DOMAIN | - |  |
| `Scripts/RunDeployedLocalDataE2E.ps1` | 146 | SKIP-DOMAIN | - |  |
| `Scripts/RunDerivedDataRefresh.ps1` | 82 | SKIP-DOMAIN | - |  |
| `Scripts/VerifyLocalData.ps1` | 235 | SKIP-DOMAIN | - |  |
| `docs/Architecture.md` | 69 | ADAPT | P11 | Optional: short template architecture doc. |
| `docs/Requirements.md` | 45 | ADAPT | P10 | Write a generic template Requirements.md (plan P10). |

## C. Template-only files

All Books feature files, Books dashboards, `.codex/config.toml` and `docs/MigrateProjectPlanningPrompt.md` exist only in the template. Keep them all. ImprovedDb removed Books because it replaced the sample product, not because Books was wrong.

