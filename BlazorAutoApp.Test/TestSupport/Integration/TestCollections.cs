using Xunit;

[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace BlazorAutoApp.Test.TestSupport.Integration;

// Centralized xUnit collection definition for integration tests
[CollectionDefinition("IntegrationTestCollection")]
public class IntegrationTestCollection : ICollectionFixture<WebAppFactory>
{
}
