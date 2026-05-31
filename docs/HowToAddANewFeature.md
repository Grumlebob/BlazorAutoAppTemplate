# How To Add A New Feature

This guide explains how to add a coherent vertical feature slice to this repository. Paths and commands are relative to the repository root.

The examples use `Sample` as the singular feature concept and `Samples` as the plural feature area. Replace those names with the real domain language, such as `Review` and `Reviews`.

This guide is written for incremental migration work. When moving an old project into this template, migrate one feature at a time and leave each feature in a shippable state before starting the next one.

## Goal

A normal feature should flow through the whole system like this:

- `BlazorAutoApp.Core` owns public domain types, contracts, and request/response DTOs.
- `BlazorAutoApp` owns server behavior: EF Core persistence, services, Minimal API endpoints, DI, telemetry, and startup mapping.
- `BlazorAutoApp.Client` owns the Interactive Auto/WASM client implementation and UI components.
- `BlazorAutoApp.Test` proves the slice works and keeps the architecture rules enforced.

Do not put EF Core, ASP.NET Core endpoint code, or `HttpClient` in Core. Do not put public `SampleRequest` or `SampleResponse` DTOs in the server or client projects. Do not inject `HttpClient` directly into Razor components.

## Technologies To Respect

New features should fit the technologies and runtime shape already used by the template:

- .NET 10 Blazor Web App with Interactive Auto render mode.
- Server prerendering followed by WebAssembly hydration.
- ASP.NET Core Identity for users, roles, cookies, passkeys schema, and account pages.
- EF Core 10 with PostgreSQL through `AppDbContext`.
- Redis-backed HybridCache, Data Protection keys, and cross-node cache invalidation.
- ASP.NET Core built-in rate limiting for API and account endpoints.
- Serilog request logging with OpenTelemetry trace/span correlation.
- Optional OpenTelemetry metrics/traces/log collection through Alloy, Prometheus, Loki, Tempo, and Grafana.
- Tailwind CSS generated from `BlazorAutoApp.Client/Styles/input.css`.
- xUnit, Testcontainers, architecture tests, and headed Playwright E2E.
- GitHub Actions CI/CD, EF migration bundles, Docker images, LocalCluster deployment, and Cloud deployment.
- Synthetic traffic through `BlazorAutoApp.Simulation` when dashboards or deployed demos need evidence.

The feature guide does not replace the operator docs. Use `HowToRunLocally.md`, `Test.md`, `ObservabilityGuide.md`, and `SimulationGuide.md` for the detailed commands in those areas.

## Migration Workflow

For each migrated feature, follow this order:

1. Define the feature boundary and name it in domain language.
2. Identify whether the data is public, authenticated-user-owned, role-restricted, or admin-only.
3. Decide which old-project behavior is being migrated now and which behavior is deliberately deferred.
4. Add Core domain/contracts/DTOs first.
5. Add server persistence, service behavior, endpoints, and DI.
6. Add the client API implementation and UI.
7. Add integration tests for the behavior before adding broad E2E coverage.
8. Add E2E only for workflows users actually perform in the browser.
9. Add observability, simulation, or docs only when the feature creates new operator-facing behavior.
10. Run the full local gate and keep the app deployable.

Avoid carrying old layering into the new repo. Old controllers, repositories, service locators, static globals, and database helper classes should be translated into this repo's feature-slice shape instead of copied across unchanged.

## Design The Slice Before Coding

Write down these answers before editing code:

- What is the singular and plural feature name?
- What are the user-visible routes?
- What are the API routes?
- Which actions require login?
- Which actions require owner checks or roles?
- Does the feature store data in PostgreSQL?
- Does the feature need Redis/HybridCache?
- Does it need local seed data?
- Does it affect health, observability dashboards, or synthetic simulation?
- What must be proven by unit/integration tests?
- What must be proven by browser E2E?

If the answer is unclear, keep the first slice smaller. A narrow, tested feature is better than a large partial migration.

## Recommended Slice Shape

Use this shape for a CRUD-style feature:

```text
BlazorAutoApp.Core/Features/Samples/
  Contracts/ISamplesApi.cs
  Domain/Sample.cs
  UseCases/CreateSample/CreateSampleRequest.cs
  UseCases/CreateSample/CreateSampleResponse.cs
  UseCases/DeleteSample/DeleteSampleRequest.cs
  UseCases/GetSample/GetSampleRequest.cs
  UseCases/GetSample/GetSampleResponse.cs
  UseCases/GetSamples/GetSamplesResponse.cs
  UseCases/GetSamples/SampleListItemResponse.cs
  UseCases/UpdateSample/UpdateSampleRequest.cs

BlazorAutoApp/Features/Samples/
  DependencyInjection.cs
  Endpoints/SamplesEndpoints.cs
  Persistence/SampleEntityTypeConfiguration.cs
  Services/SamplesServerService.cs

BlazorAutoApp.Client/Features/Samples/
  SamplesClientService.cs
  Routes/Index.razor
  Routes/Create.razor
  Routes/Details.razor
  Routes/Edit.razor
  Shared/*

BlazorAutoApp.Test/Features/Samples/
  Api/CreateSampleTests.cs
  Api/DeleteSampleTests.cs
  Api/GetSampleTests.cs
  Api/GetSamplesTests.cs
  Api/UpdateSampleTests.cs
  Client/*
  TestData/*
```

Use fewer files for a read-only feature and more files for a complex workflow, but keep the same ownership boundaries.

## Architecture Rules Enforced By Tests

The test suite actively enforces several boundaries. A new feature should satisfy these without special exceptions:

- Core feature files live under `Domain`, `Contracts`, or `UseCases`.
- Core use case files live under `UseCases/{UseCaseName}`.
- Public Core `*Request` and `*Response` DTOs live under `UseCases`.
- Core `*Api` interfaces live under `Contracts`.
- Core does not reference ASP.NET Core, EF Core, or Npgsql.
- Client references Core, not the server project.
- Client does not reference EF Core or Npgsql.
- Server and client assemblies do not declare public request/response DTOs.
- Blazor components do not inject `HttpClient` directly.
- Server code does not expose `HttpClient` as a dependency surface.
- Client routable components live under feature `Routes` folders, not root `Pages`.
- `AppDbContext` feature `DbSet` properties use Core domain entities.
- EF entity configurations live under `BlazorAutoApp/Features/{Feature}/Persistence`.
- Every public Core `*Request` has a matching feature test class with at least one `[Fact]` or `[Theory]`.
- Every public Core `*Api` interface has exactly one server implementation and is registered in DI.

These tests are there to protect the migration. If they fail, prefer changing the feature shape rather than weakening the tests.

## 1. Add Core Domain And Use Cases

Add domain entities under `BlazorAutoApp.Core/Features/{Feature}/Domain`.

```csharp
namespace BlazorAutoApp.Core.Features.Samples.Domain;

public class Sample
{
    public int Id { get; set; }

    public required string Name { get; set; }

    public string? Description { get; set; }
}
```

Add request and response DTOs under named `UseCases` folders. The architecture tests expect request classes to be public classes ending in `Request`.

```csharp
using System.ComponentModel.DataAnnotations;

namespace BlazorAutoApp.Core.Features.Samples.UseCases.CreateSample;

public class CreateSampleRequest
{
    [Required]
    [StringLength(120)]
    public required string Name { get; set; }

    [StringLength(500)]
    public string? Description { get; set; }
}
```

```csharp
namespace BlazorAutoApp.Core.Features.Samples.UseCases.CreateSample;

public class CreateSampleResponse
{
    public int Id { get; set; }

    public required string Name { get; set; }

    public string? Description { get; set; }
}
```

Put shared validation constants in `Contracts` when both domain and DTOs need them. The Books feature uses `BookRules` and URL validation as the pattern.

Use `IValidatableObject` for validation that cannot be expressed with attributes. Keep validation deterministic and independent from the database. Database uniqueness and permission checks belong in the server service.

Add the shared API contract under `Contracts`:

```csharp
using BlazorAutoApp.Core.Features.Samples.UseCases.CreateSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.DeleteSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSamples;
using BlazorAutoApp.Core.Features.Samples.UseCases.UpdateSample;

namespace BlazorAutoApp.Core.Features.Samples.Contracts;

public interface ISamplesApi
{
    Task<GetSamplesResponse> GetAsync(CancellationToken cancellationToken = default);
    Task<GetSampleResponse?> GetByIdAsync(GetSampleRequest req, CancellationToken cancellationToken = default);
    Task<CreateSampleResponse> CreateAsync(CreateSampleRequest req, CancellationToken cancellationToken = default);
    Task<bool> UpdateAsync(UpdateSampleRequest req, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(DeleteSampleRequest req, CancellationToken cancellationToken = default);
}
```

Keep the contract meaningful to the UI. The same interface is implemented by the server for prerendering and by the client after WebAssembly hydration.

Core guidance:

- Use `CancellationToken` on every async API method.
- Keep DTOs serializable with simple public get/set properties.
- Prefer explicit request types even when the request only contains `Id`; this keeps tests and API contracts consistent.
- Do not expose EF entities directly as responses.
- Do not put tenant/user authorization logic in Core DTOs.
- Do not add infrastructure abstractions to Core unless both server and client genuinely need the contract.

## 2. Add Persistence

If the feature stores data, add a `DbSet` to `BlazorAutoApp/Infrastructure/Persistence/AppDbContext.cs` using the Core domain entity:

```csharp
public DbSet<Sample> Samples => Set<Sample>();
```

Add an entity configuration under the server feature:

```csharp
using BlazorAutoApp.Core.Features.Samples.Domain;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace BlazorAutoApp.Features.Samples.Persistence;

public class SampleEntityTypeConfiguration : IEntityTypeConfiguration<Sample>
{
    public void Configure(EntityTypeBuilder<Sample> entity)
    {
        entity.HasKey(sample => sample.Id);
        entity.Property(sample => sample.Id).ValueGeneratedOnAdd();
        entity.Property(sample => sample.Name).IsRequired().HasMaxLength(120);
        entity.Property(sample => sample.Description).HasMaxLength(500);
    }
}
```

Register the configuration in `AppDbContext.OnModelCreating`:

```csharp
modelBuilder.ApplyConfiguration(new SampleEntityTypeConfiguration());
```

Persistence guidance:

- Use PostgreSQL-compatible EF Core mappings.
- Add required indexes for owner IDs, lookup keys, slugs, or unique constraints.
- Model delete behavior deliberately with `OnDelete(DeleteBehavior.Cascade)` or a stricter alternative.
- If records belong to a user, store the Identity user ID and enforce ownership in every server query.
- If updates can conflict, add a concurrency token and test the conflict behavior.
- Keep old-project table names only when they are needed for migration compatibility.
- Do not store secrets, tokens, or large files in normal feature tables without a separate design.
- Keep local/demo seed data behind Development/Docker configuration, as the Books seed does.

Add a migration:

```powershell
dotnet ef migrations add AddSamples --project BlazorAutoApp --startup-project BlazorAutoApp --output-dir Infrastructure\Persistence\Migrations
```

Then run the normal test gate before committing the migration:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
```

If the migration is for production data from an old system, add a separate migration/import plan. Do not hide one-time data imports inside startup code.

## 3. Add The Server Service

Create the server implementation under `BlazorAutoApp/Features/Samples/Services`.

```csharp
using BlazorAutoApp.Core.Features.Samples.Contracts;
using BlazorAutoApp.Core.Features.Samples.Domain;
using BlazorAutoApp.Core.Features.Samples.UseCases.CreateSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.DeleteSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSamples;
using BlazorAutoApp.Core.Features.Samples.UseCases.UpdateSample;

namespace BlazorAutoApp.Features.Samples.Services;

internal sealed class SamplesServerService(IDbContextFactory<AppDbContext> dbFactory) : ISamplesApi
{
    private readonly IDbContextFactory<AppDbContext> _dbFactory = dbFactory;

    public async Task<GetSamplesResponse> GetAsync(CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var items = await db.Samples
            .AsNoTracking()
            .OrderBy(sample => sample.Id)
            .Select(sample => new SampleListItemResponse
            {
                Id = sample.Id,
                Name = sample.Name
            })
            .ToListAsync(cancellationToken);

        return new GetSamplesResponse { Samples = items };
    }

    public async Task<GetSampleResponse?> GetByIdAsync(GetSampleRequest req, CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.Samples
            .AsNoTracking()
            .Where(sample => sample.Id == req.Id)
            .Select(sample => new GetSampleResponse
            {
                Id = sample.Id,
                Name = sample.Name,
                Description = sample.Description
            })
            .FirstOrDefaultAsync(cancellationToken);
    }

    public async Task<CreateSampleResponse> CreateAsync(CreateSampleRequest req, CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var sample = new Sample
        {
            Name = req.Name.Trim(),
            Description = string.IsNullOrWhiteSpace(req.Description) ? null : req.Description.Trim()
        };

        db.Samples.Add(sample);
        await db.SaveChangesAsync(cancellationToken);

        return new CreateSampleResponse
        {
            Id = sample.Id,
            Name = sample.Name,
            Description = sample.Description
        };
    }

    public async Task<bool> UpdateAsync(UpdateSampleRequest req, CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var sample = await db.Samples.FirstOrDefaultAsync(x => x.Id == req.Id, cancellationToken);
        if (sample is null)
        {
            return false;
        }

        sample.Name = req.Name.Trim();
        sample.Description = string.IsNullOrWhiteSpace(req.Description) ? null : req.Description.Trim();
        await db.SaveChangesAsync(cancellationToken);
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteSampleRequest req, CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var sample = await db.Samples.FirstOrDefaultAsync(x => x.Id == req.Id, cancellationToken);
        if (sample is null)
        {
            return false;
        }

        db.Samples.Remove(sample);
        await db.SaveChangesAsync(cancellationToken);
        return true;
    }
}
```

Server service guidance:

- Use `IDbContextFactory<AppDbContext>` like the existing feature services.
- Use `AsNoTracking()` for reads that do not update entities.
- Project entities into response DTOs in the query when possible.
- Pass the cancellation token through EF and async calls.
- Normalize user input before persistence, such as trimming strings and converting blank optional values to `null`.
- Treat endpoint authorization as necessary but not sufficient. Enforce ownership and data-scope rules in the service query itself.
- Do not trust route IDs, request IDs, owner IDs, or user IDs from the browser.
- Avoid N+1 query patterns; use projection, joins, or includes deliberately.
- Log useful operation outcomes, but do not log full request bodies or sensitive values.

If records belong to the current user, follow the Books pattern with `CurrentUserAccessor`, owner IDs, and per-user queries. If the feature is role-based, use Identity roles/policies at the endpoint and still scope the database query.

If the feature is cached, add feature-specific cache keys/options and invalidate on writes; do not reuse `BooksCacheKeys`. Remember that this app runs on multiple app nodes in LocalCluster and Cloud. Cache invalidation must work across nodes through Redis pub/sub or use short TTLs with `HybridCacheEntryFlags.DisableLocalCache` when strict freshness matters.

## 4. Add Minimal API Endpoints

Create endpoint mapping under `BlazorAutoApp/Features/Samples/Endpoints`.

```csharp
using BlazorAutoApp.Core.Features.Samples.Contracts;
using BlazorAutoApp.Core.Features.Samples.UseCases.CreateSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.DeleteSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSamples;
using BlazorAutoApp.Core.Features.Samples.UseCases.UpdateSample;
using BlazorAutoApp.Infrastructure.Hosting;
using Microsoft.AspNetCore.Http.HttpResults;

namespace BlazorAutoApp.Features.Samples.Endpoints;

public static class SamplesEndpoints
{
    public static IEndpointRouteBuilder MapSampleEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/samples")
            .WithTags("Samples")
            .RequireRateLimiting(AppRateLimiting.ApiPolicyName);

        group.MapGet("/", ListSamplesAsync)
            .WithName("ListSamples");

        group.MapGet("/{id:int}", GetSampleAsync)
            .WithName("GetSample")
            .ProducesProblem(StatusCodes.Status404NotFound);

        group.MapPost("/", CreateSampleAsync)
            .WithName("CreateSample")
            .ProducesValidationProblem()
            .RequireAuthorization();

        group.MapPut("/{id:int}", UpdateSampleAsync)
            .WithName("UpdateSample")
            .ProducesValidationProblem()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .RequireAuthorization();

        group.MapDelete("/{id:int}", DeleteSampleAsync)
            .WithName("DeleteSample")
            .ProducesProblem(StatusCodes.Status404NotFound)
            .RequireAuthorization();

        return routes;
    }

    private static async Task<Ok<GetSamplesResponse>> ListSamplesAsync(
        ISamplesApi samples,
        CancellationToken cancellationToken)
    {
        var result = await samples.GetAsync(cancellationToken);
        return TypedResults.Ok(result);
    }

    private static async Task<Results<Ok<GetSampleResponse>, ProblemHttpResult>> GetSampleAsync(
        [AsParameters] GetSampleRequest req,
        ISamplesApi samples,
        CancellationToken cancellationToken)
    {
        var result = await samples.GetByIdAsync(req, cancellationToken);
        return result is null ? SampleNotFound(req.Id) : TypedResults.Ok(result);
    }

    private static async Task<Created<CreateSampleResponse>> CreateSampleAsync(
        ISamplesApi samples,
        CreateSampleRequest req,
        CancellationToken cancellationToken)
    {
        var response = await samples.CreateAsync(req, cancellationToken);
        return TypedResults.Created($"/api/samples/{response.Id}", response);
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> UpdateSampleAsync(
        int id,
        UpdateSampleRequest req,
        ISamplesApi samples,
        CancellationToken cancellationToken)
    {
        if (id != req.Id)
        {
            return TypedResults.Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Sample id mismatch",
                detail: "The route id and body id do not match.");
        }

        var success = await samples.UpdateAsync(req, cancellationToken);
        return success ? TypedResults.NoContent() : SampleNotFound(req.Id);
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> DeleteSampleAsync(
        [AsParameters] DeleteSampleRequest req,
        ISamplesApi samples,
        CancellationToken cancellationToken)
    {
        var success = await samples.DeleteAsync(req, cancellationToken);
        return success ? TypedResults.NoContent() : SampleNotFound(req.Id);
    }

    private static ProblemHttpResult SampleNotFound(int id) =>
        TypedResults.Problem(
            statusCode: StatusCodes.Status404NotFound,
            title: "Sample not found",
            detail: $"Sample {id} was not found.");
}
```

Use `.RequireAuthorization()` for anything personal or mutating. Anonymous reads are fine only when the data is intentionally public.

Endpoint guidance:

- Put feature APIs under `/api/{feature}`.
- Use endpoint names such as `ListSamples`, `GetSample`, `CreateSample`, `UpdateSample`, and `DeleteSample`.
- Apply `.RequireRateLimiting(AppRateLimiting.ApiPolicyName)` to API groups.
- Use typed results and explicit `ProducesValidationProblem()` / `ProducesProblem(...)` metadata.
- Return `400` when route and body IDs disagree.
- Return `404` for missing records without revealing records owned by another user.
- Return `401`/`403` through authorization, not ad hoc response bodies.
- Keep endpoint methods small; business behavior belongs in the feature service.
- Add or update endpoint surface tests when a route is part of the stable contract.

The app has global antiforgery and status-code behavior already configured in `Program.cs`. Do not bypass those platform concerns inside feature endpoints.

## 5. Wire Server DI And Startup

Add a feature DI class:

```csharp
using BlazorAutoApp.Core.Features.Samples.Contracts;
using BlazorAutoApp.Features.Samples.Endpoints;
using BlazorAutoApp.Features.Samples.Services;

namespace BlazorAutoApp.Features.Samples;

public static class DependencyInjection
{
    public static IServiceCollection AddSamplesFeature(this IServiceCollection services, IConfiguration config)
    {
        services.AddScoped<ISamplesApi, SamplesServerService>();
        return services;
    }

    public static IEndpointRouteBuilder MapSamplesFeature(this IEndpointRouteBuilder routes)
    {
        routes.MapSampleEndpoints();
        return routes;
    }
}
```

Wire it in `BlazorAutoApp/Program.cs`:

```csharp
builder.Services.AddSamplesFeature(builder.Configuration);
```

and after health checks/components are mapped:

```csharp
app.MapSamplesFeature();
```

The architecture tests verify that each public Core `*Api` interface has exactly one server implementation and that it is registered in DI.

If the feature has options, bind them in the feature DI method with a feature-specific configuration section such as `Samples`. Add default values in `appsettings.json` only when they are safe for all environments. Put machine-specific values in `.env`, GitHub environment secrets, Ansible variables, or deployment configuration instead of hard-coding them.

## 6. Add The Client API Implementation

Create a WASM/client implementation under `BlazorAutoApp.Client/Features/Samples`.

```csharp
using System.Net;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Samples.Contracts;
using BlazorAutoApp.Core.Features.Samples.UseCases.CreateSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.DeleteSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSample;
using BlazorAutoApp.Core.Features.Samples.UseCases.GetSamples;
using BlazorAutoApp.Core.Features.Samples.UseCases.UpdateSample;

namespace BlazorAutoApp.Client.Features.Samples;

public sealed class SamplesClientService(HttpClient http) : ISamplesApi
{
    private readonly HttpClient _http = http;

    public async Task<GetSamplesResponse> GetAsync(CancellationToken cancellationToken = default)
    {
        var response = await _http.GetFromJsonAsync<GetSamplesResponse>("api/samples", cancellationToken);
        return response ?? new GetSamplesResponse { Samples = [] };
    }

    public async Task<GetSampleResponse?> GetByIdAsync(GetSampleRequest req, CancellationToken cancellationToken = default)
    {
        using var response = await _http.GetAsync($"api/samples/{req.Id}", cancellationToken);
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }

        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<GetSampleResponse>(cancellationToken);
    }

    public async Task<CreateSampleResponse> CreateAsync(CreateSampleRequest req, CancellationToken cancellationToken = default)
    {
        using var response = await _http.PostAsJsonAsync("api/samples", req, cancellationToken);
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<CreateSampleResponse>(cancellationToken))!;
    }

    public async Task<bool> UpdateAsync(UpdateSampleRequest req, CancellationToken cancellationToken = default)
    {
        using var response = await _http.PutAsJsonAsync($"api/samples/{req.Id}", req, cancellationToken);
        if (response.StatusCode == HttpStatusCode.NoContent) return true;
        if (response.StatusCode == HttpStatusCode.NotFound) return false;
        response.EnsureSuccessStatusCode();
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteSampleRequest req, CancellationToken cancellationToken = default)
    {
        using var response = await _http.DeleteAsync($"api/samples/{req.Id}", cancellationToken);
        if (response.StatusCode == HttpStatusCode.NoContent) return true;
        if (response.StatusCode == HttpStatusCode.NotFound) return false;
        response.EnsureSuccessStatusCode();
        return true;
    }
}
```

Register it in `BlazorAutoApp.Client/Program.cs`:

```csharp
builder.Services.AddScoped<ISamplesApi, SamplesClientService>();
```

Components should inject `ISamplesApi` or a feature state class, not `HttpClient`. That keeps prerendering and hydration coherent.

Client API guidance:

- Use relative API URLs such as `api/samples`.
- Handle `404` explicitly when the server service returns nullable details.
- Let unexpected status codes throw through `EnsureSuccessStatusCode()` unless the UI has a deliberate recovery path.
- Keep browser-only concerns in the client project.
- Keep shared DTOs in Core so prerendered server UI and hydrated WASM UI use the same contract.

## 7. Add UI Routes And State

Routable client components live under `BlazorAutoApp.Client/Features/{Feature}/Routes`, not `Pages`.

```razor
@page "/samples"
@inject ISamplesApi Samples

<PageTitle>Samples</PageTitle>

<h1 class="mb-4 text-3xl font-bold tracking-normal text-gray-900">Samples</h1>
```

For more than trivial UI, add a feature state class beside the UI and inject that into components. The Books feature uses `AuthorBookcaseState` and `UserBookcaseState` to keep loading/error/data transitions out of markup.

Use `PersistentComponentState` when a public or SSR-visible route loads data during prerender and should avoid an immediate duplicate request after hydration. The server implementation of `ISamplesApi` is used during prerender; the client implementation is used after WebAssembly hydration.

UI guidance:

- Keep route components thin; move repeated UI into `Shared` or feature-specific components.
- Add `data-testid` attributes for important workflow controls.
- Use existing Tailwind style patterns from nearby components.
- Keep text and controls responsive on mobile.
- Use `AuthorizeView` or `[Authorize]` route/page patterns for authenticated workflows.

If the feature should appear in navigation, update `BlazorAutoApp.Client/Features/AppShell/Layout/NavMenu.razor`.

Interactive Auto guidance:

- During prerender, injected Core API contracts resolve to server services.
- After hydration, the same contracts resolve to client `HttpClient` services.
- Use `PersistentComponentState` for SSR-loaded public data that should not immediately refetch after hydration.
- Be careful with authentication-dependent prerendering; unauthenticated and authenticated states can differ during hydration.
- Keep route components resilient to loading, empty, error, unauthorized, and not-found states.
- Dispose event subscriptions and cancellation token sources in stateful components.

Tailwind and UI guidance:

- Reuse existing spacing, typography, button, form, and validation styles before inventing new ones.
- Keep UI text inside containers on mobile and desktop.
- Put recurring UI into feature components under `Shared` or a more specific feature subfolder.
- Add `data-testid` only for stable workflow hooks, not for every decorative element.
- Rebuild Tailwind output when CSS classes or `BlazorAutoApp.Client/Styles/input.css` change:

```powershell
cd BlazorAutoApp.Client
npm install
npm run css:build
```

## 8. Add Observability Carefully

Use normal structured logging in endpoints/services:

```csharp
log.LogInformation("Created sample {SampleId}", response.Id);
```

Never log secrets, tokens, raw passwords, or full user-controlled payloads.

If the feature needs custom metrics/traces, follow the shape of `BlazorAutoApp/Features/Books/BooksTelemetry.cs`, but keep labels low-cardinality. Good labels are operation names such as `list`, `create`, or `delete` and outcomes such as `success`, `not_found`, or `bad_request`. Do not use sample IDs, user IDs, email addresses, URLs, or titles as metric labels.

For dashboard or alert changes, update `ObservabilityGuide.md` only when operators need to know about the new signal.

Feature-level observability should normally include:

- Structured logs for important successful writes and expected failure outcomes.
- Metrics/traces only when they answer an operator question better than built-in HTTP/server metrics.
- Error logs only for exceptional failures, not normal validation or not-found behavior.
- No high-cardinality metric labels.

If a feature becomes important to demos or dashboards, update the simulator in `BlazorAutoApp.Simulation`, `Scripts/RunSimulation.ps1`, and `SimulationGuide.md` so observability can show realistic traffic without manual clicking.

## 9. Add Tests

Every public Core request type must have a matching feature test class. For example, `CreateSampleRequest` requires a public `CreateSampleTests` class under a namespace that starts with `BlazorAutoApp.Test.Features.Samples`.

Use this layout:

```text
BlazorAutoApp.Test/Features/Samples/
  Api/CreateSampleTests.cs
  Api/DeleteSampleTests.cs
  Api/GetSampleTests.cs
  Api/GetSamplesTests.cs
  Api/UpdateSampleTests.cs
  Client/SampleStateTests.cs
  TestData/SampleDataGenerator.cs
```

API tests should use the integration fixture:

```csharp
using System.Net;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Samples.UseCases.CreateSample;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Features.Samples.Api;

[Collection("IntegrationTestCollection")]
public class CreateSampleTests : IAsyncLifetime
{
    private readonly HttpClient _client;
    private readonly HttpClient _anonymousClient;
    private readonly Func<Task> _resetDatabase;

    public CreateSampleTests(WebAppFactory factory)
    {
        _client = factory.CreateAuthenticatedClient();
        _anonymousClient = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
    }

    [Fact]
    public async Task Create_Valid_ReturnsCreated()
    {
        var request = new CreateSampleRequest { Name = "Sample" };

        var response = await _client.PostAsJsonAsync("/api/samples", request);

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
    }

    [Fact]
    public async Task Create_Anonymous_ReturnsUnauthorized()
    {
        var request = new CreateSampleRequest { Name = "Sample" };

        var response = await _anonymousClient.PostAsJsonAsync("/api/samples", request);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    public Task InitializeAsync() => _resetDatabase();

    public Task DisposeAsync() => _resetDatabase();
}
```

Add tests for:

- Happy path persistence and response shape.
- Not found behavior for reads, updates, and deletes.
- Unauthorized or forbidden behavior for protected endpoints.
- Owner isolation so one user cannot read, update, or delete another user's records.
- Validation failures for invalid request DTOs.
- Route/body ID mismatch behavior.
- Rate-limit behavior only when the feature uses a distinct policy or has special risk.
- Cache invalidation if the feature is cached.
- Cross-node cache invalidation if cached data can be stale across app servers.
- Client-only state or parsing logic when it exists.
- E2E browser coverage when the user-visible workflow is important.
- Lighthouse checks when a feature materially changes first-load performance or important public pages.

Do not depend on seeded rows. Create unique data inside tests and clean it up through the shared integration fixture or E2E cleanup helpers.

Test guidance:

- Use `WebAppFactory` and `[Collection("IntegrationTestCollection")]` for API/integration tests.
- Use authenticated clients from the test fixture for protected endpoints.
- Use anonymous clients to prove protected endpoints reject unauthenticated users.
- Reset database state before and after integration tests.
- Prefer direct API/integration tests for business behavior and reserve Playwright for browser workflows.
- Keep E2E tests behind `RUN_E2E=1`.
- For E2E-created users/books or new feature data, track cleanup so failed runs do not leave state behind.
- If the feature affects observability, add or update smoke checks rather than relying on manual dashboard inspection.

## 10. Run The Local Gate

Run this before committing:

```powershell
dotnet restore .\BlazorAutoApp.sln
dotnet build .\BlazorAutoApp.sln --no-restore
dotnet test .\BlazorAutoApp.sln --no-build
```

For visible E2E:

```powershell
.\Scripts\RunLocal.ps1 -NoBrowser
$env:RUN_E2E='1'
$env:E2E_BASE_URL='https://localhost:7186'
Remove-Item Env:\E2E_HEADLESS -ErrorAction SilentlyContinue
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --filter "Category=E2E"
```

For more test details, see `Test.md`.

For synthetic traffic after the feature is observable or demo-critical:

```powershell
.\Scripts\RunSimulation.ps1 -Target local -Profile smoke
.\Scripts\RunSimulationMatrix.ps1 -All
```

Only add feature-specific simulation writes when they can be safely cleaned up and paced below rate limits.

## Deployment And Operations Checklist

Most feature changes deploy through the existing CI/CD path without editing deployment files. Still check these points before shipping:

- EF migrations are committed and build into the migration bundle.
- New required configuration has safe defaults or documented environment variables.
- No secrets are committed.
- Redis assumptions are valid outside local development.
- Cache invalidation works with multiple app nodes.
- Public routes work behind forwarded headers and Caddy/Cloudflare.
- Health endpoints do not depend on feature data unless deliberately added as a readiness dependency.
- Observability docs mention any new operator-facing dashboards, alerts, or runbooks.
- Simulation docs/scripts are updated if the feature is part of demos or acceptance evidence.
- LocalCluster and Cloud do not need separate feature code; environment differences belong in configuration/deployment values.

For pure UI or API additions, no deployment guide change is normally needed. For new infrastructure dependencies, deployment changes must be planned explicitly before the feature is considered complete.

## AI Handoff Checklist

When asking an AI agent to migrate a feature into this repo, include this instruction:

```text
Follow docs/HowToAddANewFeature.md. Keep the feature vertically sliced.
Do not copy old-project layering blindly. Do not add public DTOs outside Core.
Add integration tests for the API behavior and only add E2E for real browser workflows.
Run dotnet build and dotnet test before finishing.
```

Ask the AI to report:

- Files added or changed by layer.
- Any old-project behavior intentionally not migrated yet.
- Any config, migration, cache, observability, simulation, or deployment impact.
- The exact tests it ran and any tests it could not run.

## Implementation Checklist

- Core domain types live under `BlazorAutoApp.Core/Features/{Feature}/Domain`.
- Core API contracts live under `BlazorAutoApp.Core/Features/{Feature}/Contracts`.
- Public request/response DTOs live under `BlazorAutoApp.Core/Features/{Feature}/UseCases/{UseCase}`.
- Server service implements the Core API contract and is the only server implementation.
- Server service enforces ownership/data scope, not only endpoint authorization.
- Minimal API endpoints use typed results, validation metadata, authorization, and the API rate-limit policy.
- Server DI registers the feature and `Program.cs` maps it.
- Client service implements the same Core API contract using `HttpClient`.
- Client components inject the API contract or feature state, not `HttpClient`.
- Routes live under `BlazorAutoApp.Client/Features/{Feature}/Routes`.
- EF configuration lives under `BlazorAutoApp/Features/{Feature}/Persistence`.
- `AppDbContext` uses Core domain entities for `DbSet` properties.
- EF migrations are created for persistence changes.
- Caching uses feature-specific keys/options and handles multi-node invalidation.
- Logs/metrics/traces avoid secrets and high-cardinality labels.
- Every Core `*Request` has a matching feature test class with at least one `[Fact]` or `[Theory]`.
- Integration tests cover validation, auth, not-found, persistence, and owner isolation where relevant.
- E2E covers important browser workflows where relevant.
- Docs, simulation, and observability are updated only when the feature changes those surfaces.
- `dotnet test` passes.
