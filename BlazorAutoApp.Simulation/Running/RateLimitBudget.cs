namespace BlazorAutoApp.Simulation.Running;

internal sealed class RateLimitBudget
{
    private readonly TimeSpan _minimumSpacing;
    private DateTimeOffset _nextAvailable;

    public RateLimitBudget(double requestsPerSecond)
    {
        RequestsPerSecond = requestsPerSecond;
        _minimumSpacing = requestsPerSecond <= 0
            ? TimeSpan.MaxValue
            : TimeSpan.FromSeconds(1 / requestsPerSecond);
        _nextAvailable = DateTimeOffset.MinValue;
    }

    public double RequestsPerSecond { get; }

    public bool IsAvailable(DateTimeOffset now) =>
        RequestsPerSecond > 0 && now >= _nextAvailable;

    public void MarkUsed(DateTimeOffset now)
    {
        _nextAvailable = now + _minimumSpacing;
    }

    public void BackOff(DateTimeOffset now, TimeSpan retryAfter)
    {
        if (retryAfter <= TimeSpan.Zero)
        {
            retryAfter = TimeSpan.FromSeconds(1);
        }

        var next = now + retryAfter;
        if (next > _nextAvailable)
        {
            _nextAvailable = next;
        }
    }
}
