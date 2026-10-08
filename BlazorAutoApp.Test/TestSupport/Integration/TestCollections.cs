using Xunit;

// Pure unit-test classes (no collection attribute) run in parallel. Every
// collection below disables parallelization: those tests share Docker
// containers, process environment variables or a WebApplicationFactory, and run
// one collection at a time after the parallel tests.
[assembly: CollectionBehavior(MaxParallelThreads = 2)]

namespace BlazorAutoApp.Test.TestSupport.Integration;

public static class TestCollectionNames
{
    public const string Integration = "IntegrationTestCollection";
    public const string StartupIntegration = "StartupIntegrationCollection";
    public const string StartupSeed = "StartupSeedCollection";
    public const string CrossNodeRedis = "CrossNodeRedisCollection";
    public const string EnvironmentMutation = "EnvironmentMutationCollection";
    public const string E2E = "E2ECollection";
}

/// <summary>Tests that share the default <see cref="WebAppFactory"/>.</summary>
[CollectionDefinition(TestCollectionNames.Integration, DisableParallelization = true)]
public sealed class IntegrationTestCollection : ICollectionFixture<WebAppFactory>
{
}

/// <summary>Tests that build their own factory with custom startup settings.</summary>
[CollectionDefinition(TestCollectionNames.StartupIntegration, DisableParallelization = true)]
public sealed class StartupIntegrationCollection
{
}

/// <summary>Tests that exercise startup seeding against their own database.</summary>
[CollectionDefinition(TestCollectionNames.StartupSeed, DisableParallelization = true)]
public sealed class StartupSeedCollection
{
}

/// <summary>Tests that run several app nodes against shared PostgreSQL and Redis containers.</summary>
[CollectionDefinition(TestCollectionNames.CrossNodeRedis, DisableParallelization = true)]
public sealed class CrossNodeRedisCollection
{
}

/// <summary>Tests that set process environment variables.</summary>
[CollectionDefinition(TestCollectionNames.EnvironmentMutation, DisableParallelization = true)]
public sealed class EnvironmentMutationCollection
{
}

/// <summary>Playwright browser tests.</summary>
[CollectionDefinition(TestCollectionNames.E2E, DisableParallelization = true)]
public sealed class E2ECollection
{
}
