namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed record CacheInvalidationRequest(
    string Scope,
    IReadOnlyCollection<string> Keys,
    IReadOnlyCollection<string> Tags);
