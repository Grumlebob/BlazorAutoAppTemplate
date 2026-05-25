namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed record CacheInvalidationMessage(
    int Version,
    string AppName,
    string EnvironmentName,
    string SourceNodeId,
    string Scope,
    string[] Keys,
    string[] Tags,
    DateTimeOffset CreatedUtc);
