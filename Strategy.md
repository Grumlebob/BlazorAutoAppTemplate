# Proper Cross-Node Invalidation Strategy

Status: Implemented and verified.

This plan accepts Redis pub/sub as the chosen strategy. It is written as an implementation plan, not just a design note.

## Decision

Use Redis pub/sub to broadcast cache invalidation messages between app servers, and keep a short explicit `HybridCacheEntryOptions.LocalCacheExpiration` as the fallback for missed pub/sub messages.

This is the right fit for this repo because:

- The production deployment already runs multiple app servers: `node-app1` and `node-app2`.
- Both app servers share the same PostgreSQL and Redis service.
- The app already registers Redis through `AddStackExchangeRedisCache` and directly uses `IConnectionMultiplexer`.
- The official `HybridCache` docs state that key/tag invalidation affects the current server and secondary cache, but not other servers' in-memory primary caches.
- Redis pub/sub is fast and simple enough for this template, while the explicit local TTL bounds stale reads if a node misses a pub/sub message.

Official references:

- https://learn.microsoft.com/en-us/aspnet/core/performance/caching/hybrid?view=aspnetcore-10.0
- https://learn.microsoft.com/en-us/dotnet/api/microsoft.extensions.caching.hybrid.hybridcacheentryflags?view=net-10.0-pp
- https://learn.microsoft.com/en-us/dotnet/api/microsoft.extensions.caching.hybrid.hybridcacheentryoptions.localcacheexpiration?view=net-10.0-pp
- https://redis.io/docs/latest/develop/use-cases/pub-sub/dotnet/
- https://stackexchange.github.io/StackExchange.Redis/Basics.html

## Current Repo Facts

Deployment:

- `Deployment/LocalCluster/inventory/prod/hosts.yml` contains two app servers.
- `Deployment/LocalCluster/ansible/roles/caddy/templates/app.caddy.j2` reverse-proxies to all hosts in `groups['app_servers']`.
- Caddy uses `lb_policy cookie`, which improves user affinity but does not provide cache correctness.
- `Deployment/LocalCluster/compose/app-server/docker-compose.yml` runs one `web` container per app node.
- `Deployment/LocalCluster/compose/node-db/docker-compose.yml` runs shared PostgreSQL and Redis.

Server app:

- `BlazorAutoApp/Infrastructure/Hosting/AppCachingExtensions.cs` owns Redis, data protection, distributed cache, and `HybridCache` registration.
- `BlazorAutoApp/Features/Movies/Services/MoviesServerService.cs` owns movie reads/writes and currently invalidates the local node plus Redis.
- `BlazorAutoApp/Features/Movies/Caching/MoviesCacheKeys.cs` is already the right place for feature-specific keys and tags.
- Current architecture tests only allow server infrastructure namespaces under `BlazorAutoApp.Infrastructure.Hosting` and `BlazorAutoApp.Infrastructure.Persistence`.

Test project:

- Existing single-node integration tests use `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs`.
- Current test factory owns one PostgreSQL Testcontainer and deliberately disables Redis by setting `Redis:Configuration` to `CHANGE_ME`.
- Cross-node tests need two app hosts sharing the same PostgreSQL and Redis containers.

## Failure Mode To Fix

1. Node A warms `movies:list`.
2. Node B warms `movies:list`.
3. A user deletes a movie through Node A.
4. Node A removes its local cache entry and Redis cache entry.
5. Node B can still serve its stale in-memory entry until local expiration.

The same issue exists for create and update. Sticky load-balancer cookies do not fix this for other users, new sessions, restarted nodes, or direct app-node traffic.

## Implementation Rules

- Publish invalidation only after the database write succeeds.
- Do not use the request cancellation token after `SaveChangesAsync`; use `CancellationToken.None` for post-commit invalidation.
- Local invalidation must happen on the mutating node even when Redis publish fails.
- Remote invalidation messages must be idempotent.
- Remote invalidation must never publish a second message.
- Redis pub/sub is not durable, so every cached movie entry must also have a short local TTL.
- Message channels must be app/environment scoped so side-by-side template deployments do not invalidate each other.
- Do not rely on Caddy stickiness for correctness.

## Phase 1: Make Movie Local Cache Freshness Explicit

Status: Completed.

Files:

- `BlazorAutoApp/Features/Movies/Caching/MoviesCacheOptions.cs`
- `BlazorAutoApp/Features/Movies/Services/MoviesServerService.cs`
- `BlazorAutoApp/appsettings.json`
- `BlazorAutoApp/appsettings.Docker.json`
- `BlazorAutoApp/settings.defaults.json` only if the deployment contract should expose cache settings

Tasks:

1. Add these properties to `MoviesCacheOptions`:
   - `ListTtlMinutes`
   - `ItemTtlMinutes`
   - `LocalListTtlSeconds`
   - `LocalItemTtlSeconds`
   - `DisableLocalCache`
2. Keep distributed cache TTL defaults:
   - list: 5 minutes
   - item: 10 minutes
3. Add local cache TTL defaults:
   - list: 5 seconds
   - item: 10 seconds
4. In `MoviesServerService`, create helper methods for list/item options:
   - Set `Expiration`.
   - Set `LocalCacheExpiration`.
   - If `DisableLocalCache` is true, set `Flags = HybridCacheEntryFlags.DisableLocalCache`.
5. Keep `DisableLocalCache` false by default.
6. Add the same cache options to `appsettings.json` and `appsettings.Docker.json`; leave `settings.defaults.json` unchanged unless it is deliberately used as the deployment contract for cache settings.

Done when:

- Config clearly distinguishes distributed TTL from local in-process TTL.
- Single-node movie cache tests still pass.
- Strict mode is available without code changes.

## Phase 2: Add Cache Invalidation Runtime Under Hosting

Status: Completed.

Place files under `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation` so existing architecture rules remain valid.

Files to add:

- `CacheInvalidationRequest.cs`
- `CacheInvalidationMessage.cs`
- `CacheInvalidationOptions.cs`
- `ICacheInvalidator.cs`
- `ICacheInvalidationPublisher.cs`
- `ICacheInvalidationApplier.cs`
- `HybridCacheInvalidationApplier.cs`
- `HybridCacheInvalidator.cs`
- `NoOpCacheInvalidationPublisher.cs`
- `CacheInvalidationServiceCollectionExtensions.cs`

Contracts:

```csharp
internal sealed record CacheInvalidationRequest(
    string Scope,
    IReadOnlyCollection<string> Keys,
    IReadOnlyCollection<string> Tags);

internal sealed record CacheInvalidationMessage(
    int Version,
    string AppName,
    string EnvironmentName,
    string SourceNodeId,
    string Scope,
    string[] Keys,
    string[] Tags,
    DateTimeOffset CreatedUtc);

internal interface ICacheInvalidator
{
    Task InvalidateAsync(CacheInvalidationRequest request, CancellationToken cancellationToken = default);
}
```

Behavior:

- `HybridCacheInvalidationApplier` applies keys with `HybridCache.RemoveAsync(keys, token)` and tags with `HybridCache.RemoveByTagAsync(tags, token)`.
- `HybridCacheInvalidator` applies local invalidation first, then calls `ICacheInvalidationPublisher`.
- `NoOpCacheInvalidationPublisher` is used when Redis is not configured.
- After a database commit, invalidation failures should be logged and swallowed; stale data is then bounded by local TTL or strict mode.
- Keep these contracts internal to the server assembly so infrastructure Request/Response-shaped records do not become public DTO surface.

Options:

- Section name: `Cache:Invalidation`.
- `Enabled`: default true when Redis is configured, false when Redis is placeholder.
- `ChannelName`: optional override.
- `NodeId`: optional override.
- `PublishTimeoutSeconds`: default 2.
- `ApplyTimeoutSeconds`: default 5.

Node id:

- Use `Cache:Invalidation:NodeId` if configured.
- Else use `CACHE_INVALIDATION_NODE_ID` if set.
- Else use `$"{Environment.MachineName}:{Environment.ProcessId}"`.

Channel name:

- Default: `"{App:Name}:{EnvironmentName}:cache-invalidation:v1"`.
- Use `App:Name` to isolate side-by-side template deployments.
- Use environment name to isolate `Development`, `Docker`, and test hosts.

Done when:

- The app has a reusable invalidation abstraction.
- The implementation stays in `Infrastructure.Hosting`.
- No feature code knows about Redis pub/sub directly.

## Phase 3: Add Redis Pub/Sub Publisher And Subscriber

Status: Completed.

Files to add under `BlazorAutoApp/Infrastructure/Hosting/CacheInvalidation`:

- `RedisCacheInvalidationPublisher.cs`
- `RedisCacheInvalidationSubscriber.cs`

Dependency cleanup:

- Add an explicit `StackExchange.Redis` package reference because the server app directly uses `IConnectionMultiplexer` and will use pub/sub APIs directly.
- Use central package management in `Directory.Packages.props`.
- Pin to the version already resolved by the Microsoft Redis packages unless a restore/audit shows a safer newer compatible version.

Publisher details:

- Inject `IConnectionMultiplexer`.
- Get subscriber with `GetSubscriber()`.
- Serialize `CacheInvalidationMessage` with `System.Text.Json`.
- Publish with `PublishAsync(RedisChannel.Literal(channelName), payload)`.
- Do not throw back to the feature after the DB write has committed; log publish failures and rely on local TTL fallback.

Subscriber details:

- Implement `BackgroundService`.
- Subscribe on startup with `SubscribeAsync(RedisChannel.Literal(channelName))`.
- Prefer `ChannelMessageQueue.ReadAsync(stoppingToken)` or ordered queue consumption.
- Deserialize defensively.
- Ignore messages where app/environment do not match.
- Ignore same-node messages because the mutating node already invalidated locally.
- Apply keys and tags through `ICacheInvalidationApplier`.
- Log applied, ignored, invalid, and failed messages.
- On shutdown, unsubscribe if the queue exists.

Reliability notes:

- Redis pub/sub is at-most-once. A node that is disconnected at publish time can miss the message.
- The short local TTL from Phase 1 is the required fallback.
- Do not add durable Redis streams or a database outbox in this implementation unless tests prove pub/sub is not enough.

Done when:

- All live nodes receive invalidation messages quickly.
- Redis unavailable in local dev does not crash the app.
- Logging makes publish/receive/apply failures visible.

## Phase 4: Wire Registration Into Existing Caching Setup

Status: Completed.

Files:

- `BlazorAutoApp/Infrastructure/Hosting/AppCachingExtensions.cs`
- new `CacheInvalidationServiceCollectionExtensions.cs`

Tasks:

1. Keep Redis connection creation in `AppCachingExtensions`.
2. After `services.AddHybridCache()`, call an extension such as:
   - `services.AddAppCacheInvalidation(configuration, environment, hasRedis);`
3. Register:
   - `ICacheInvalidationApplier` as singleton or scoped-safe singleton.
   - `ICacheInvalidator` as singleton.
   - `ICacheInvalidationPublisher` as Redis publisher when Redis exists and invalidation is enabled.
   - `ICacheInvalidationPublisher` as no-op when Redis is missing or disabled.
   - `RedisCacheInvalidationSubscriber` as hosted service only when Redis exists and invalidation is enabled.
4. Avoid resolving `IConnectionMultiplexer` when Redis is disabled.

Done when:

- One registration path handles local dev, test, Docker, and production.
- Redis placeholder config still works.
- Health checks remain unchanged.

## Phase 5: Wire Movies To The Invalidation Abstraction

Status: Completed.

Files:

- `BlazorAutoApp/Features/Movies/Services/MoviesServerService.cs`
- `BlazorAutoApp/Features/Movies/Caching/MoviesCacheKeys.cs`
- `BlazorAutoApp/Features/Movies/DependencyInjection.cs` only if feature-local helper registration is needed

Tasks:

1. Inject `ICacheInvalidator` into `MoviesServerService`.
2. Replace direct `HybridCache.RemoveAsync` and `RemoveByTagAsync` mutation cleanup with `ICacheInvalidator`.
3. Keep `HybridCache` injection for reads.
4. Add helper on `MoviesCacheKeys`:
   - `CacheInvalidationRequest ForChangedMovie(int id)`
5. The helper should include:
   - keys: `movies:list`, `movies:item:{id}`
   - tags: `movies:list`, `movies:item:{id}`
   - scope: `movies`
6. Use the helper after create, update, and delete.
7. Use `CancellationToken.None` for post-commit invalidation.
8. Keep movie cache keys and tags feature-owned; keep the pub/sub transport infrastructure-owned.

Create:

- Invalidate the list key/tag.
- Also include the created item key/tag. It is harmless if absent and keeps the helper consistent.

Update:

- Invalidate the list key/tag.
- Invalidate the updated item key/tag.

Delete:

- Invalidate the list key/tag.
- Invalidate the deleted item key/tag.

Done when:

- Movie mutations publish one consistent invalidation message.
- Deleting on one node invalidates stale list and stale item caches on other nodes.
- Feature code still has no Redis dependency.

## Phase 6: Upgrade Test Support For Shared Redis And Multi-Node Hosts

Status: Completed.

Files:

- `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactory.cs`
- new `BlazorAutoApp.Test/TestSupport/Integration/WebAppFactoryOptions.cs`
- new `BlazorAutoApp.Test/TestSupport/Integration/SharedIntegrationEnvironment.cs`
- possible new `BlazorAutoApp.Test/TestSupport/Integration/RedisTestContainer.cs`

Tasks:

1. Keep the existing parameterless `WebAppFactory` path for normal tests.
2. Add options for external services:
   - `PostgresConnectionString`
   - `RedisConnectionString`
   - `CacheInvalidationNodeId`
   - `AppName`
   - `EnvironmentName`
   - `RunMigrations`
3. Prefer `ConfigureAppConfiguration` with in-memory values per factory for per-node settings.
4. Use scoped process environment overrides only for settings that minimal hosting reads before the in-memory test provider is available. This is acceptable here because the test assembly disables parallelization.
5. For normal single-node tests, keep Redis disabled unless a test explicitly needs it.
6. Create one PostgreSQL container and one Redis container for the cross-node test fixture.
7. Use the deployment Redis image for tests: `redis:7.4.9-alpine3.21`.
8. Use generic `Testcontainers.ContainerBuilder` for Redis unless adding `Testcontainers.Redis` proves cleaner.

Redis test container settings:

- Start Redis with a password.
- Disable append-only persistence for tests.
- Wait for `redis-cli -a <password> ping` to return `PONG`.
- Connection string format: `localhost:<mapped-port>,password=<password>,abortConnect=false`.

Done when:

- One test can start two `WebAppFactory` instances with the same DB and Redis.
- Each factory has a different cache invalidation node id.
- Existing tests remain isolated and deterministic.

## Phase 7: Add Cross-Node Cache Tests

Status: Completed.

Preferred location:

- `BlazorAutoApp.Test/Features/Movies/MoviesCrossNodeCacheInvalidationTests.cs`

Required tests:

1. `Delete_OnNodeA_InvalidatesListAndItem_OnNodeB`
2. `Update_OnNodeA_InvalidatesItem_OnNodeB`
3. `Create_OnNodeA_InvalidatesList_OnNodeB`
4. `MissedPubSubMessage_IsBoundedByLocalCacheExpiration`

Delete test shape:

1. Seed two movies.
2. Warm list and item cache through Node B.
3. Delete one movie through Node A.
4. Poll Node B until:
   - deleted item returns 404
   - list contains only the remaining movie
5. Fail if Node B still returns stale data after a short timeout.

Update test shape:

1. Seed or create one movie.
2. Warm item cache through Node B.
3. Update through Node A.
4. Poll Node B until item returns the new title/rating.

Create test shape:

1. Warm empty list through Node B.
2. Create through Node A.
3. Poll Node B until list contains the created movie.

Missed-message fallback test shape:

1. Configure a very short `LocalListTtlSeconds`, such as 1.
2. Disable pub/sub publisher or subscriber for the receiving node through config.
3. Warm cache on Node B.
4. Mutate on Node A.
5. Assert Node B may be stale immediately but becomes fresh after local TTL expires.

Polling helper:

- Add a small `EventuallyAsync` helper under `BlazorAutoApp.Test/TestSupport/Integration`.
- Default timeout: 5 seconds.
- Poll interval: 100 milliseconds.
- Include last observed response in failure message.

Done when:

- Tests prove real cross-node freshness.
- Existing `MoviesCachingTests` still prove single-node key/tag behavior.
- CI can catch regressions before deployment.

## Phase 8: Add Architecture And Documentation Updates

Status: Completed.

Architecture tests:

- If all new invalidation runtime files stay under `Infrastructure/Hosting/CacheInvalidation`, no architecture whitelist change should be needed.
- If a root `Infrastructure/Caching` folder is introduced instead, update `NoInfrastructureNamespaceTests` deliberately and document why.

Documentation:

- Update `BlazorAutoApp.Test/TESTING.md` with the new cross-node Redis test fixture.
- Update `Deployment/LocalCluster/HowToDeployLocalCluster.md` with:
  - Redis is required for multi-node cache invalidation.
  - Redis pub/sub is at-most-once.
  - Local TTL is the fallback.
  - Strict mode can disable local cache.
  - The invalidation channel naming scheme.

Acceptance checks:

- Add a deployment acceptance check only after the cross-node tests are stable.
- Prefer direct app-node checks through Ansible so both app nodes are proven.
- Avoid mutating production data unless the check creates and deletes a clearly test-owned movie.

Done when:

- Operators know what Redis is doing beyond data protection and distributed cache.
- The template explains why local in-memory cache needs cross-node invalidation.

## Phase 9: Verification Commands

Status: Completed.

Run after implementation:

```powershell
dotnet restore
dotnet build .\BlazorAutoApp.sln --configuration Release --no-restore
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --configuration Release --no-build --filter "FullyQualifiedName~MoviesCachingTests"
dotnet test .\BlazorAutoApp.Test\BlazorAutoApp.Test.csproj --configuration Release --no-build --filter "FullyQualifiedName~MoviesCrossNodeCacheInvalidationTests"
dotnet test --configuration Release --no-build
```

Also run:

```powershell
git diff --check
```

If deployment docs or scripts are changed, also run the existing deployment validation commands used by CI.

## Rollback Plan

If pub/sub introduces instability:

1. Set `Cache:Invalidation:Enabled=false`.
2. Set `Cache:Movies:DisableLocalCache=true` for strict correctness.
3. Keep Redis as the distributed cache.
4. Re-enable pub/sub after fixing the subscriber/publisher issue.

This gives a correctness-first fallback without deleting the implementation.

## Final Acceptance Criteria

- Delete through Node A invalidates list and item cache on Node B.
- Update through Node A invalidates item and list cache on Node B.
- Create through Node A invalidates list cache on Node B.
- A disconnected or disabled subscriber can only serve stale data until explicit local TTL expires.
- Local development still works without Redis.
- Production multi-node deployment uses Redis pub/sub automatically when Redis is configured.
- Feature code depends on an invalidation abstraction, not Redis.
- The solution builds and the full Release test suite passes.
