# Migrate Project Planning Prompt

Use this prompt after forking this repository and before moving code from the old `ImprovedDb` Blazor Server app. It is designed to make another AI produce a careful `docs/MigrateProjectPlan.md` from evidence in both repositories.

Fill the placeholders before running it.

```text
You are a senior .NET migration architect and pragmatic coding agent.

Goal:
Create a thorough, evidence-based migration plan named docs/MigrateProjectPlan.md for moving the old ImprovedDb Blazor Server application into a new fork of this BlazorAutoApp template.

Important context:
- The old app is called ImprovedDb.
- The old app is Blazor Server only.
- The target app is this repository's .NET 10 Blazor Web App template using Interactive Auto render mode.
- The migration must be feature-by-feature. Each feature must be rebuilt into the new architecture instead of copied across with old layering.
- The target fork should remain deployable after each migrated feature.
- The initial fork/deploy path can reuse the existing four LocalCluster nodes through docs/HowToForkThisRepo.md.
- Do not implement the migration yet. Only inspect, reason, and write docs/MigrateProjectPlan.md.

Inputs:
- New fork repo path: <NEW_FORK_REPO_PATH>
- Old ImprovedDb repo path: <OLD_IMPROVEDDB_REPO_PATH>
- GitHub fork owner/repo: <GITHUB_OWNER>/<GITHUB_REPO>
- New app slug: <APP_SLUG>
- New public hostname: <PUBLIC_HOSTNAME>
- Existing LocalCluster app slug to reuse nodes from, if any: <EXISTING_LOCALCLUSTER_APP_SLUG>
- Any old production database/data that must be preserved: <YES/NO/UNKNOWN and notes>

First actions:
1. Open the new fork repo and read:
   - README.md
   - docs/HowToForkThisRepo.md
   - docs/HowToAddANewFeature.md
   - docs/HowToRunLocally.md
   - docs/Test.md
   - docs/ObservabilityGuide.md
   - docs/SimulationGuide.md
   - Deployment/LocalCluster/HowToDeployLocalCluster.md
   - Deployment/Common/release.yml
   - Deployment/LocalCluster/inventory/prod/group_vars/all.yml
   - .github/workflows/ci.yml
   - .github/workflows/cd-localcluster.yml
2. Inspect the old ImprovedDb repo. Identify projects, pages/components, services, data access, database migrations/schema, authentication, authorization, configuration, external dependencies, JavaScript/CSS, files/storage, background jobs, integrations, reports, and deployment assumptions.
3. If the old repo path is unavailable, stop and write docs/MigrateProjectPlan.md with a clear "Blocked: old repo unavailable" section plus the exact files and facts needed. Do not invent old-app features.
4. If the new fork path is unavailable, stop and ask for the correct path. Do not write a plan against an unknown target.

Planning rules:
- Use the new repo's architecture as the target. Do not preserve old Blazor Server structure when it conflicts with the template.
- Migrate one vertical feature slice at a time.
- Every migrated feature must define Core contracts/domain/use-case DTOs, server persistence/services/endpoints, client Interactive Auto UI/service behavior, tests, and docs where relevant.
- Do not put public request/response DTOs outside BlazorAutoApp.Core.
- Do not inject HttpClient directly into Razor components.
- Do not put EF Core, ASP.NET Core endpoint code, or Npgsql in BlazorAutoApp.Core.
- Treat authorization as a service/query responsibility too, not only endpoint attributes.
- Preserve old behavior intentionally, but redesign implementation to fit the new template.
- Separate feature migration from one-time data import. Do not hide data imports inside startup code.
- Keep the new fork shippable after each phase: build, tests, migrations, CI/CD, LocalCluster deployment, and acceptance checks should have a known state.
- Call out any behavior intentionally deferred.
- Use concrete file paths from both repos. Include line references where they materially support a decision.
- Be honest about uncertainty. Add open questions instead of guessing.

Target architecture reminders:
- BlazorAutoApp.Core/Features/{Feature}: domain types, contracts, and public request/response DTOs.
- BlazorAutoApp/Features/{Feature}: server services, Minimal API endpoints, persistence mapping, dependency injection, telemetry.
- BlazorAutoApp.Client/Features/{Feature}: Interactive Auto client service, routable components under Routes, shared UI/state.
- BlazorAutoApp.Test/Features/{Feature}: integration, API, client-state, architecture, and E2E tests.
- BlazorAutoApp.Simulation: synthetic traffic only for workflows that matter to demos/observability.
- Deployment/Common and Deployment/LocalCluster: deployment settings only when the migration changes runtime configuration or infrastructure.

The generated docs/MigrateProjectPlan.md must have this structure:

# Migrate ImprovedDb Into Fork

## 1. Executive Summary
- State the migration goal.
- State the recommended first fork/deploy path.
- State the recommended migration strategy in 5-10 bullets.
- State what is intentionally out of scope for the first plan.

## 2. Evidence Reviewed
- List the new repo docs/files inspected.
- List the old ImprovedDb files/folders inspected.
- List commands run.
- List anything not available.

## 3. Current Target Repo Shape
- Summarize the target app architecture and rules that affect migration.
- Summarize CI/CD, LocalCluster, testing, observability, and simulation surfaces that must stay working.
- Mention that the target is Interactive Auto and explain the practical implications for prerendering, hydration, Core contracts, and client services.

## 4. Old ImprovedDb Inventory
Create a detailed inventory from the old repo:
- Projects and target frameworks.
- Pages/components/routes.
- Services and domain logic.
- Data model, DbContext(s), migrations, SQL scripts, seed data.
- Authentication/authorization/users/roles.
- Configuration and secrets.
- External services/APIs.
- File storage or uploads.
- Background jobs/timers/scheduled work.
- Reports/export/import flows.
- JavaScript/CSS/static assets.
- Tests.
- Deployment/runtime assumptions.

Do not summarize vaguely. Use a table where useful.

## 5. Feature Inventory And Migration Order
Create a table with one row per feature:
- Feature name.
- Old paths.
- User-visible routes/screens.
- API/server behavior.
- Data tables/entities.
- Auth/role/ownership rules.
- External dependencies.
- Target new slice paths.
- Dependencies on other features.
- Complexity/risk.
- Recommended migration phase.
- Definition of done.

Order features so foundational/shared pieces come first, but avoid a giant "platform phase" unless truly required. Prefer small vertical slices.

## 6. Fork And Deployment Preparation
Use docs/HowToForkThisRepo.md to plan the fork setup:
- Values to choose: APP_SLUG, APP_IDENTITY_NAME, APP_IMAGE, PUBLIC_HOSTNAME, ports, deploy root, runner label, GitHub environment.
- LocalCluster side-by-side or replacement decision.
- Cloudflare hostname/tunnel work.
- GitHub secrets/variables.
- CI and CD checks.
- Acceptance checks.

Make clear which steps are manual on CurrentPC, ControlPC, GitHub, and Cloudflare.

## 7. Shared Platform Decisions
Plan cross-cutting migration decisions before individual features:
- Identity/user migration strategy.
- Database provider/schema strategy.
- Old data import or no-data strategy.
- Authorization model.
- Navigation and app shell changes.
- Error handling and validation conventions.
- Caching and Redis use.
- File storage strategy.
- Email/notification strategy.
- Observability and logging conventions.
- Rate limits.
- Configuration and secret ownership.

For each decision, state recommendation, reason, files affected, and risk.

## 8. Feature Migration Phases
For each phase, include:
- Goal.
- Old behavior to preserve.
- Behavior intentionally deferred.
- Target Core files.
- Target server files.
- Target client files.
- EF migration/data changes.
- Auth/authorization rules.
- Cache/Redis needs.
- Observability/logging needs.
- Simulation needs.
- Tests to add.
- Local verification commands.
- E2E/deployed verification when relevant.
- Definition of done.
- Rollback or recovery notes.

Each phase must be small enough that it can be implemented, tested, reviewed, and deployed before starting the next phase.

## 9. Data Migration Plan
Only include this if old data matters. Cover:
- Source database/provider and schema.
- Target PostgreSQL schema.
- Mapping table by entity/table.
- Identity/user mapping if relevant.
- Import tooling recommendation.
- Validation queries/checks.
- Dry-run strategy.
- Backup/rollback.
- What not to import.

If old data does not matter, say so explicitly and explain how the new database will be created through EF migrations.

## 10. Testing Strategy
Map test types to migration phases:
- Unit tests where useful.
- Integration/API tests for feature behavior.
- Architecture tests that must continue to pass.
- Playwright E2E for important browser workflows.
- Lighthouse/performance only where relevant.
- Simulation after feature workflows are stable.

Include exact commands:
- dotnet restore
- dotnet build
- dotnet test
- E2E command when needed
- Scripts/RunLocal.ps1
- Scripts/RunSimulation.ps1 or Scripts/RunSimulationMatrix.ps1 when relevant

## 11. Observability And Simulation Plan
State when to update:
- Structured logs.
- Metrics/traces.
- Dashboards.
- Alerts/runbooks.
- BlazorAutoApp.Simulation.
- docs/ObservabilityGuide.md.
- docs/SimulationGuide.md.

Avoid adding observability work to every feature by default. Add it when it answers an operator or demo question.

## 12. Deployment Plan
State the deploy rhythm:
- Keep main green.
- Deploy after each meaningful feature slice.
- Use LocalCluster first.
- Use Cloud only after fork-specific Cloud settings are deliberately updated.
- Run acceptance checks and observability doctor when enabled.

Mention any deployment setting changes required by each phase.

## 13. Risk Register
Create a table:
- Risk.
- Likelihood.
- Impact.
- Mitigation.
- Owner/action.

Include risks around Blazor Server to Interactive Auto differences, auth/data migration, old hidden dependencies, deployment settings, missing tests, and performance.

## 14. Open Questions
List questions that must be answered before implementation. Separate blocking questions from questions that can be deferred.

## 15. First Implementation Prompt
Write a ready-to-copy prompt for the first feature migration. It must:
- Name the first feature.
- List exact old files to inspect.
- List exact new target files to create/change.
- Reference docs/HowToAddANewFeature.md.
- Require tests.
- Require build/test commands.
- Require a short final report of changed files, deferred behavior, and verification.

Quality bar for docs/MigrateProjectPlan.md:
- It must be specific enough that a weaker AI can follow it without broad architectural judgment.
- It must not assume the old app's behavior without evidence.
- It must be ordered so the fork can be created and deployed before large feature migration work.
- It must preserve the new template's architecture.
- It must make feature migration incremental, tested, and deployable.
- It must clearly mark manual steps.
- It must avoid root clutter and keep docs under docs/.

After writing docs/MigrateProjectPlan.md:
- Run markdown/reference sanity checks where practical.
- Do not modify application code unless explicitly asked.
- Report the file created, evidence reviewed, missing information, and the most important risks.
```
