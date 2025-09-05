using Xunit;

namespace BlazorAutoApp.Test.TestingSetup;

// Centralized xUnit collection definition for integration tests
[CollectionDefinition("MediaTestCollection")]
public class MediaTestCollection : ICollectionFixture<WebAppFactory>
{
}

