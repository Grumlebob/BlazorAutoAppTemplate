namespace BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

internal sealed class CacheInvalidationOptions
{
    public const string SectionName = "Cache:Invalidation";
    public const int MessageVersion = 1;

    public bool Enabled { get; set; }

    public string? ChannelName { get; set; }

    public string? NodeId { get; set; }

    public int PublishTimeoutSeconds { get; set; } = 2;

    public int ApplyTimeoutSeconds { get; set; } = 5;

    public string AppName { get; set; } = "BlazorAutoApp";

    public string EnvironmentName { get; set; } = "Production";

    public string EffectiveNodeId =>
        !string.IsNullOrWhiteSpace(NodeId)
            ? NodeId
            : $"{Environment.MachineName}:{Environment.ProcessId}";

    public string EffectiveChannelName =>
        !string.IsNullOrWhiteSpace(ChannelName)
            ? ChannelName
            : $"{AppName}:{EnvironmentName}:cache-invalidation:v1";

    public TimeSpan PublishTimeout => TimeSpan.FromSeconds(Math.Max(1, PublishTimeoutSeconds));

    public TimeSpan ApplyTimeout => TimeSpan.FromSeconds(Math.Max(1, ApplyTimeoutSeconds));
}
