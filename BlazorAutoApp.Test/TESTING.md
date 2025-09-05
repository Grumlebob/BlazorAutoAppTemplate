Vertical Slice Testing
======================

This project follows vertical slice architecture for tests: every Core feature slice has a matching test slice with a one-to-one naming and namespace mapping.

Layout
------
- Core slice: `BlazorAutoApp.Core/Features/{Feature}/{Slice}Request.cs`
- Test slice: `BlazorAutoApp.Test/Features/{Feature}/{Slice}Tests.cs`
- Test infra: `BlazorAutoApp.Test/TestingSetup/*` (shared helpers, WebAppFactory, data generator)
- Architecture checks: `BlazorAutoApp.Test/Architecture/*`

Conventions
-----------
- Test namespace: `BlazorAutoApp.Test.Features.{Feature}`
- Test class name: `{Slice}Tests` (suffix `Tests` required)
- Each feature test class must contain at least one `[Fact]`/`[Theory]` method
- Integration tests should use `[Collection("MediaTestCollection")]` to share the `WebAppFactory`

Architecture Enforcement
------------------------
- `FeatureSlicesArchitectureTests` scans Core for all public classes ending with `Request` under any `Features.{Feature}` namespace and asserts a matching test class exists with the conventions above.
- `ArchitectureTests` enforces Client/Server service implementations for Core `*Api` interfaces and their naming (`*ClientService` / `*ServerService`).

Authoring a New Feature's Tests
-------------------------------
1) Identify the Core slices in `BlazorAutoApp.Core/Features/{Feature}` (e.g., `GetMoviesRequest`, `CreateMovieRequest`, etc.).
2) For each `{Slice}Request`, add a corresponding `{Slice}Tests` to `BlazorAutoApp.Test/Features/{Feature}/`.
3) Use the naming/namespace conventions above and include at least one `[Fact]`/`[Theory]`.
4) If your tests hit the HTTP API, decorate the class with `[Collection("MediaTestCollection")]` and inject `WebAppFactory` in the constructor; obtain `HttpClient` via `factory.HttpClient` and services via `factory.Services`.

Scaffolding Helper
------------------
Run the script below to scaffold missing `{Slice}Tests` files for a Core feature (creates skipped placeholder tests that you can fill in):

- From repo root:
  - PowerShell: `pwsh -File .\\BlazorAutoApp.Test\\tools\\NewFeatureTests.ps1 -Feature Movies`

The scaffolder scans `BlazorAutoApp.Core/Features/{Feature}` for `*Request` classes and creates stub test files in `BlazorAutoApp.Test/Features/{Feature}` if they are missing.

Notes
-----
- Integration tests use Testcontainers + PostgreSQL; ensure Docker is running when executing `dotnet test`.
- If you add new Core requests, the architecture test will fail until you add matching test classes.

