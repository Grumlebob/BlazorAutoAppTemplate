# Server feature slice

This page covers shared contracts, persistence, API behavior, and server wiring. Feature-level product constraints belong in [Requirements](../Requirements.md). The [feature entry](../HowToAddANewFeature.md) gives the overall order.

## Core contract and types

Put shared domain types under `BlazorAutoApp.Core/Features/{Feature}/Domain`, API interfaces under `Contracts`, and public request/response DTOs under `UseCases/{UseCase}`. Keep Core independent of EF Core, ASP.NET Core, and browser HTTP. Use simple serializable DTOs. Put deterministic validation in DTOs or Core rules; put database uniqueness and access checks in server behavior.

Async contract methods accept a `CancellationToken` and pass it through. Do not expose EF entities or Identity authorization logic in a response contract.

The current examples are [IBooksApi](../../BlazorAutoApp.Core/Features/Books/Contracts/IBooksApi.cs), [GetBooksResponse](../../BlazorAutoApp.Core/Features/Books/UseCases/GetBooks/GetBooksResponse.cs), and [BookRules](../../BlazorAutoApp.Core/Features/Books/Contracts/BookRules.cs). These show this repository's shape; they do not make every feature a CRUD API.

## Persistence and service

When a feature stores data, use Core domain entities for its `AppDbContext` sets and put EF mappings in `BlazorAutoApp/Features/{Feature}/Persistence`. Add a migration for schema changes; see [local migration commands](../HowToRunLocally.md#migrations). Choose indexes, relationships, delete behavior, and concurrency rules from the feature's needs.

The current persisted feature uses `IDbContextFactory<AppDbContext>`; follow that data-access shape unless the feature has a concrete reason to differ. Put business operations in `BlazorAutoApp/Features/{Feature}/Services`. Enforce owner or tenant scope in the database query itself; endpoint authorization alone does not prevent cross-owner reads. Pass cancellation through database and cache calls. Project query results into response DTOs. Add cache keys and invalidation only if the feature needs caching. Version keys when a response shape changes; cached writes must invalidate all relevant app nodes. Test the cross-node path when the feature uses shared Redis.

The Books examples are [BookEntityTypeConfiguration](../../BlazorAutoApp/Features/Books/Persistence/BookEntityTypeConfiguration.cs) and [BooksServerService](../../BlazorAutoApp/Features/Books/Services/BooksServerService.cs). Books has both public catalog and user-owned data, so copy only the behavior relevant to your feature.

## Endpoints and wiring

Map APIs under `/api/{feature}` in `BlazorAutoApp/Features/{Feature}/Endpoints`. Keep handlers small; they bind the contract, apply access/rate-limit policy, and translate outcomes into typed HTTP results. Declare validation and problem-response metadata so OpenAPI describes the actual contract. Use `401/403` for access failures and `404` where absence or lack of ownership should not reveal a record.

User-specific responses must be `private, no-store`. Keep APIs under `/api` so cookie challenges return API status codes rather than login HTML. Do not assume every feature is public or every write requires the same role; define the access policy from its data.

Register the server implementation and bind safe feature defaults in its `DependencyInjection.cs`. Call its feature mapping method from `BlazorAutoApp/Program.cs`. Keep machine-specific values in environment or deployment configuration. The current examples are [BooksEndpoints](../../BlazorAutoApp/Features/Books/Endpoints/BooksEndpoints.cs), [Books DependencyInjection](../../BlazorAutoApp/Features/Books/DependencyInjection.cs), and [Program.cs](../../BlazorAutoApp/Program.cs).

## Validation

Test validation, access, not-found behavior, persistence, ownership isolation, and cache behavior when applicable. Add tests for the contract rather than tests that only construct DTOs. See [Infrastructure testing](../Testing/Infrastructure.md) and the [local gate](../Test.md#local-gate).

Log useful outcomes without secrets or full user payloads. Add metrics only to answer an operator question, and keep labels low-cardinality. Link new operator-facing signals from [Observability](../ObservabilityGuide.md).
