# Infrastructure and architecture tests

Integration tests use [WebAppFactory](../../GrumPlates.Test/TestSupport/Integration/WebAppFactory.cs), PostgreSQL and Redis Testcontainers. Docker must be running. The pinned images and container settings are in [TestContainerImages](../../GrumPlates.Test/TestSupport/Integration/TestContainerImages.cs). The fixture owns its containers and database reset; PostgreSQL and Redis test data is disposable and uses no named data volumes. Use unique test data and fixture cleanup.

## Collections and fixtures

Tests sharing a host, containers, or process-wide state belong in a named xUnit collection. Names and parallelism are defined in [TestCollections](../../GrumPlates.Test/TestSupport/Integration/TestCollections.cs). Shared integration tests use `IntegrationTestCollection`. That collection runs serially. Global test parallelism is capped in `TestCollections`; pure unit tests do not need a collection.

Use `WebAppFactory` clients for API tests. It supplies authenticated and anonymous clients, resets database state, and raises default rate limits so unrelated tests do not hit `429`. A test of rate-limit behavior must create its own factory with a deliberately low limit. Environment-mutating tests must use the environment scope helper.

## Architecture and hosting

Architecture tests define feature boundaries and expected placement. Read their names and current rules in the [feature slice architecture tests](../../GrumPlates.Test/Architecture/Slices/FeatureSlicesArchitectureTests.cs). Do not duplicate the full inventory here: the test source is authoritative.

Profile hosting tests exercise physical static roots, safe navigation fallback, assets, reserved paths, and API privacy. OpenAPI metadata tests verify endpoint status and DTO metadata without loading database, Redis, or Identity services. Follow the exact profile setup and filters in the [React hosting tests](../../GrumPlates.Test/Infrastructure/Hosting/ReactFrontendHostingTests.cs) and [OpenAPI metadata tests](../../GrumPlates.Test/Architecture/OpenApi/OpenApiMetadataTests.cs).

## Cache behavior

Feature cache tests verify local freshness and invalidation. Cross-node tests use two hosts against shared PostgreSQL and Redis; run them with:

```powershell
dotnet test .\GrumPlates.Test\GrumPlates.Test.csproj --filter "FullyQualifiedName~BooksCrossNodeCacheInvalidationTests"
```

The shared Redis fixture is enabled only for tests that need it. Do not infer distributed invalidation behavior from ordinary single-host tests.
