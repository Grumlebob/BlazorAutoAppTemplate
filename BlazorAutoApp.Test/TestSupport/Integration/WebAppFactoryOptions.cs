using System;
using System.Collections.Generic;
using Microsoft.Extensions.DependencyInjection;

namespace BlazorAutoApp.Test.TestSupport.Integration;

public sealed class WebAppFactoryOptions
{
    /// <summary>Extra configuration values applied after the factory defaults.</summary>
    public Dictionary<string, string?> ConfigurationOverrides { get; init; } = [];

    /// <summary>Extra service registrations applied after the test authentication setup.</summary>
    public Action<IServiceCollection>? ConfigureTestServices { get; init; }

    /// <summary>Set to false for factories that never call ResetDatabaseAsync.</summary>
    public bool InitializeDatabaseRespawner { get; init; } = true;

    public string? PostgresConnectionString { get; init; }

    public string? RedisConnectionString { get; init; }

    public string? CacheInvalidationNodeId { get; init; }

    public bool? CacheInvalidationEnabled { get; init; }

    public string? AppName { get; init; }

    public string? EnvironmentName { get; init; }

    public bool RunMigrations { get; init; } = true;

    public bool RunStartupMigrations { get; init; }

    public bool AuthorBooksSeedAtStartup { get; init; }

    public bool UseProcessEnvironmentOverrides { get; init; } = true;

    public int? LocalListTtlSeconds { get; init; }

    public int? LocalItemTtlSeconds { get; init; }

    public bool? DisableLocalCache { get; init; }

    public bool? OpenTelemetryEnabled { get; init; }

    public string? OpenTelemetryEndpoint { get; init; }

    public int? GlobalRateLimitPermitLimit { get; init; }

    public int? ApiRateLimitPermitLimit { get; init; }

    public int? AuthenticationRateLimitPermitLimit { get; init; }

    /// <summary>
    /// Challenge anonymous requests with the real Identity cookie scheme instead of
    /// the test scheme, so tests can assert redirect versus 401 behaviour.
    /// </summary>
    public bool UseIdentityCookieChallenge { get; init; }
}
