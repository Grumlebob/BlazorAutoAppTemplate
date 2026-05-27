namespace BlazorAutoApp.Test.TestSupport.Integration;

internal static class TestContainerImages
{
    public const string PostgreSql = "postgres:18.4-alpine3.23";
    public const string Redis = "redis:8.8.0-alpine3.23";
    public const string Ryuk = "testcontainers/ryuk:0.14.0";
}
