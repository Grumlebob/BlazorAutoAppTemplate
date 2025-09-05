# Improvements Plan

This plan outlines targeted changes to modernize the repo, reinforce vertical slices, improve developer experience, CI/CD, security, and runtime performance. Items are grouped by priority with concrete steps and code pointers.

## Goals
- Enforce vertical-slice boundaries and avoid cross-cutting “catch‑all” namespaces.
- Strengthen correctness and guardrails (analyzers, tests, CI quality gates).
- Improve observability and operational readiness (health, metrics, logs).
- Optimize containerization and environment parity.
- Keep the template approachable: opt‑in for advanced features.

## High Priority
- Code quality and analyzers
  - Add `Directory.Build.props` to centralize settings:
    - `Nullable` enabled (already), `TreatWarningsAsErrors=true`, `AnalysisLevel=latest`, `EnableNETAnalyzers=true`, `CodeAnalysisTreatWarningsAsErrors=true` for non‑test projects.
    - Suggestion: relax to warnings in test project only.
  - Add `.editorconfig` with C# style rules and naming conventions aligned with the template; enable `dotnet_diagnostic` severity for common issues.

- Architecture guardrails
  - Keep per‑feature EF configuration: done for Movies. Repeat for future features.
  - Tests: added checks for no `Infrastructure` namespaces and that EF configurations live under `BlazorAutoApp.Features.*`.
  - Add DI wiring test (server) to ensure `IMoviesApi` resolves to `MoviesServerService`.
  - Add endpoint surface test to assert expected Minimal API routes exist for Movies.

- CI enhancements
  - Update GitHub Actions:
    - Add NuGet caching (`actions/setup-dotnet` cache or `actions/cache`).
    - Add `dotnet format --verify-no-changes` to enforce code style.
    - Publish test results and code coverage (e.g., `coverlet.collector`) as artifacts.
    - Add concurrency group to cancel superseded PR builds.

- Health and readiness endpoints
  - Add `MapHealthChecks("/health")` and optionally database readiness check.
  - Update Serilog request logging to demote health checks and static assets.

## Medium Priority
- Observability
  - Optional: Add OpenTelemetry (OTel) tracing/metrics with Serilog bridge; export OTLP when available.
  - Correlate logs: add `X-Request-ID` propagation and enrich logs with `TraceId`/`SpanId` when OTel is enabled.

- EF Core robustness and performance
  - Enable connection resiliency on Npgsql: `UseNpgsql(conn, o => o.EnableRetryOnFailure(5))`.
  - Add compiled queries for hot paths; ensure `AsNoTracking` on reads (already used in many places).
  - Consider `AddDbContextPool<AppDbContext>` for pooled contexts.

- Minimal APIs
  - Add API versioning (route or header based) using Microsoft.AspNetCore.Mvc.Versioning (optional for template).
  - Add response caching headers for GET endpoints (client or proxy cache), where appropriate.

- Blazor specifics
  - Add response compression (Brotli/Gzip) for server.
  - Consider static asset caching and fingerprinting guidance; ensure `appsettings.Production.json` leverages cache headers.

## Low Priority
- Container hardening
  - Run as non‑root user in final image; use a dedicated user and set proper file permissions.
  - Add `HEALTHCHECK` in Docker image (or rely on K8s/Compose health checks).
  - Multi‑arch build guidance in docs; optional GitHub Actions workflow to build/push images.

- Documentation and onboarding
  - Expand README with badges (test, coverage), and a minimal “feature add” cookbook.
  - Add a short CONTRIBUTING.md and PR checklist focused on vertical slices and tests.

## Concrete Changes (proposed diffs)

- Directory.Build.props (root)
  - Centralize analyzer and compiler settings across projects:
    - `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`
    - `<EnableNETAnalyzers>true</EnableNETAnalyzers>`
    - `<AnalysisLevel>latest</AnalysisLevel>`
    - `<LangVersion>preview</LangVersion>` (optional; if you use latest features)
  - For test project, override to not treat warnings as errors.

- .editorconfig (root)
  - Adopt common C# conventions (var usage, naming, expression‑bodied members, async suffix, file‑scoped namespaces). Set severities for clarity.

- Server: Program.cs
  - Health checks:
    - `builder.Services.AddHealthChecks().AddNpgSql(connString);`
    - `app.MapHealthChecks("/health");`
  - Serilog request logging tweak:
    - Demote static assets: paths starting with `/assets`, `/_framework`, `/favicon` → `Verbose`.

- Server: EF Core
  - `AddDbContextPool<AppDbContext>(options => options.UseNpgsql(conn, o => o.EnableRetryOnFailure(5)));`

- Tests (new)
  - `DiWiringTests`: resolve `IMoviesApi` in server DI and assert it is `MoviesServerService`.
  - `EndpointSurfaceTests`: assert verbs/paths exist for Movies endpoints.
  - `MigrationsUpToDateTests`: assert `GetPendingMigrations()` is empty at startup in test environment.

- GitHub Actions (update BuildAndTest.yml)
  - Add steps:
    - `dotnet tool restore` (if format/coverage tools are added)
    - `dotnet format --verify-no-changes`
    - NuGet cache: `cache: true` in `actions/setup-dotnet`
    - Collect coverage: `dotnet test --collect:'XPlat Code Coverage'` and upload artifact.
    - `concurrency: group: ci-${{ github.ref }}; cancel-in-progress: true`

- Dockerfile (final image)
  - Add non‑root user and run:
    - `RUN adduser --disabled-password app && chown -R app /app`
    - `USER app`

## Stretch: Template Options
- Provide toggles (docs or branches) for:
  - OTel on/off; Seq on/off; Redis cache on/off.
  - API versioning on/off.
  - WASM AOT build pipeline guidance.

## Suggested Task Breakdown
1) Add `Directory.Build.props` + `.editorconfig`; run `dotnet format` locally to fix style.
2) Add health checks and tweak Serilog request logging.
3) Switch to `AddDbContextPool` with retry.
4) Add DI + endpoint + migrations tests.
5) Enhance GitHub Actions with cache, format check, and coverage.
6) Harden Dockerfile for non‑root.
7) Review and adjust docs (README/HowToRun) to reflect new options.

---

If you want, I can start by adding the props/editorconfig, health checks, and a DI wiring test, then update the workflow for caching and format checks in a follow‑up PR.

