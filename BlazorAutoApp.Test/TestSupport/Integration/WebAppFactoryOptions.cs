namespace BlazorAutoApp.Test.TestSupport.Integration;

public sealed class WebAppFactoryOptions
{
    public string? PostgresConnectionString { get; init; }

    public string? RedisConnectionString { get; init; }

    public string? CacheInvalidationNodeId { get; init; }

    public bool? CacheInvalidationEnabled { get; init; }

    public string? AppName { get; init; }

    public string? EnvironmentName { get; init; }

    public bool RunMigrations { get; init; } = true;

    public bool UseProcessEnvironmentOverrides { get; init; } = true;

    public int? LocalListTtlSeconds { get; init; }

    public int? LocalItemTtlSeconds { get; init; }

    public bool? DisableLocalCache { get; init; }
}
