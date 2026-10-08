namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed record CacheInvalidationResult
{
    public CacheInvalidationResult(
        bool localApplied,
        bool publishAttempted,
        bool published,
        IEnumerable<string> warnings)
    {
        LocalApplied = localApplied;
        PublishAttempted = publishAttempted;
        Published = published;
        Warnings = warnings.ToArray();
    }

    public bool LocalApplied { get; }

    public bool PublishAttempted { get; }

    public bool Published { get; }

    public IReadOnlyList<string> Warnings { get; }

    public bool HasWarnings => Warnings.Count > 0;
}
