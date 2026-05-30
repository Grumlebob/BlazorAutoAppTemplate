using System.Globalization;
using System.Net;
using BlazorAutoApp.Simulation.Options;
using BlazorAutoApp.Simulation.Running;

namespace BlazorAutoApp.Simulation.Reporting;

internal sealed class SimulationReport
{
    public required string RunId { get; init; }

    public required string Target { get; init; }

    public required string BaseUrl { get; init; }

    public required string Profile { get; init; }

    public required DateTimeOffset StartedAtUtc { get; init; }

    public required DateTimeOffset EndedAtUtc { get; init; }

    public required double DurationSeconds { get; init; }

    public required double MaxRps { get; init; }

    public required double ApiRpsBudget { get; init; }

    public required double AuthWriteRpsBudget { get; init; }

    public required int VirtualUsers { get; init; }

    public required bool WritesEnabled { get; init; }

    public required bool BrowserSamplerEnabled { get; init; }

    public required AuthReport Auth { get; init; }

    public required WriteReport Writes { get; init; }

    public required BrowserSamplerReport BrowserSampler { get; init; }

    public required IReadOnlyList<SyntheticLedgerEntry> SyntheticBooks { get; init; }

    public required int RequestCount { get; init; }

    public required Dictionary<string, int> StatusCodes { get; init; }

    public required LatencySummary Latency { get; init; }

    public required RateLimitSummary RateLimit { get; init; }

    public required IReadOnlyList<ScenarioSummary> Scenarios { get; init; }

    public required IReadOnlyList<string> Errors { get; init; }

    public required bool FailedThresholds { get; init; }

    public static SimulationReport Create(
        string runId,
        SimulationOptions options,
        DateTimeOffset startedAt,
        DateTimeOffset endedAt,
        IReadOnlyList<ScenarioRunResult> results,
        AuthReport? auth = null,
        WriteReport? writes = null,
        BrowserSamplerReport? browserSampler = null,
        IReadOnlyList<SyntheticLedgerEntry>? syntheticBooks = null)
    {
        var unexpected = results.Where(static result => !result.Expected).ToArray();
        var unexpected5xx = unexpected.Count(static result => result.StatusCode is >= HttpStatusCode.InternalServerError);
        var unexpected429 = results.Count(static result => result.RateLimited && !result.RateLimitExpected);
        var failedThresholds = unexpected.Length > 0
            || (options.FailOn5xx && unexpected5xx > 0)
            || (!options.AllowRateLimit && unexpected429 > 0)
            || (auth is { Enabled: true, AuthenticatedApiCheckSucceeded: false })
            || (writes is { CleanupSucceeded: false });

        return new SimulationReport
        {
            RunId = runId,
            Target = options.Target.Name,
            BaseUrl = options.Target.BaseUrl.ToString(),
            Profile = options.Profile.Name,
            StartedAtUtc = startedAt,
            EndedAtUtc = endedAt,
            DurationSeconds = (endedAt - startedAt).TotalSeconds,
            MaxRps = options.MaxRps,
            ApiRpsBudget = options.ApiRpsBudget,
            AuthWriteRpsBudget = options.AuthWriteRpsBudget,
            VirtualUsers = options.VirtualUsers,
            WritesEnabled = options.Writes,
            BrowserSamplerEnabled = options.BrowserSampler,
            Auth = auth ?? AuthReport.Disabled,
            Writes = writes ?? WriteReport.Disabled,
            BrowserSampler = browserSampler ?? BrowserSamplerReport.Disabled,
            SyntheticBooks = syntheticBooks ?? [],
            RequestCount = results.Count,
            StatusCodes = BuildStatusCodes(results),
            Latency = LatencySummary.From(results.Select(static result => result.Duration.TotalMilliseconds)),
            RateLimit = RateLimitSummary.From(results),
            Scenarios = BuildScenarioSummaries(results),
            Errors = unexpected
                .Take(20)
                .Select(static result => $"{result.ScenarioName} {result.Path} status={StatusText(result.StatusCode)} error={result.Error ?? ""}".Trim())
                .ToArray(),
            FailedThresholds = failedThresholds
        };
    }

    public string ToConsoleSummary(string reportPath)
    {
        var lines = new List<string>
        {
            "Traffic simulation completed",
            $"target: {Target}",
            $"profile: {Profile}",
            $"requests: {RequestCount.ToString(CultureInfo.InvariantCulture)}",
            $"2xx: {CountStatusRange(200, 299).ToString(CultureInfo.InvariantCulture)}",
            $"3xx: {CountStatusRange(300, 399).ToString(CultureInfo.InvariantCulture)}",
            $"4xx expected: {CountExpected4xx().ToString(CultureInfo.InvariantCulture)}",
            $"4xx unexpected: {CountUnexpected4xx().ToString(CultureInfo.InvariantCulture)}",
            $"5xx: {CountStatusRange(500, 599).ToString(CultureInfo.InvariantCulture)}",
            $"p95: {Latency.P95Ms:0.#} ms",
            $"api budget: {ApiRpsBudget:0.###} rps",
            $"unexpected 429: {RateLimit.Unexpected429}",
            $"writes: {(WritesEnabled ? "enabled" : "disabled")}",
            $"browser sampler: {(BrowserSamplerEnabled ? "enabled" : "disabled")}",
            $"auth: {(Auth.Enabled ? Auth.Mode : "disabled")}",
            $"cleanup: {Writes.CleanupStatus}",
            "Grafana range: last 15 minutes",
            $"report: {reportPath}"
        };

        if (FailedThresholds)
        {
            lines.Insert(1, "result: failed thresholds");
        }

        return string.Join(Environment.NewLine, lines);
    }

    private int CountStatusRange(int min, int max) =>
        StatusCodes
            .Where(pair => int.TryParse(pair.Key, out var code) && code >= min && code <= max)
            .Sum(static pair => pair.Value);

    private int CountExpected4xx() =>
        StatusCodes
            .Where(static pair => pair.Key.EndsWith("_expected", StringComparison.Ordinal))
            .Sum(static pair => pair.Value);

    private int CountUnexpected4xx() =>
        StatusCodes
            .Where(pair => int.TryParse(pair.Key, out var code) && code >= 400 && code < 500)
            .Sum(static pair => pair.Value)
        + StatusCodes
            .Where(static pair => pair.Key.EndsWith("_unexpected", StringComparison.Ordinal)
                && pair.Key.StartsWith('4'))
            .Sum(static pair => pair.Value);

    private static Dictionary<string, int> BuildStatusCodes(IReadOnlyList<ScenarioRunResult> results)
    {
        var statusCodes = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var result in results)
        {
            var status = result.StatusCode is null
                ? "exception"
                : ((int)result.StatusCode).ToString(CultureInfo.InvariantCulture);

            if (result.StatusCode is >= HttpStatusCode.BadRequest and < HttpStatusCode.InternalServerError)
            {
                status += result.Expected ? "_expected" : "_unexpected";
            }

            statusCodes[status] = statusCodes.TryGetValue(status, out var count) ? count + 1 : 1;
        }

        return statusCodes;
    }

    private static IReadOnlyList<ScenarioSummary> BuildScenarioSummaries(IReadOnlyList<ScenarioRunResult> results) =>
        results
            .GroupBy(static result => result.ScenarioName, StringComparer.Ordinal)
            .OrderBy(static group => group.Key, StringComparer.Ordinal)
            .Select(static group => new ScenarioSummary(
                group.Key,
                group.Count(),
                group.Count(static result => result.Expected),
                group.Count(static result => !result.Expected),
                LatencySummary.From(group.Select(static result => result.Duration.TotalMilliseconds))))
            .ToArray();

    private static string StatusText(HttpStatusCode? statusCode) =>
        statusCode is null ? "exception" : ((int)statusCode).ToString(CultureInfo.InvariantCulture);
}

internal sealed record LatencySummary(double P50Ms, double P95Ms, double P99Ms)
{
    public static LatencySummary From(IEnumerable<double> values)
    {
        var sorted = values.Order().ToArray();
        if (sorted.Length == 0)
        {
            return new LatencySummary(0, 0, 0);
        }

        return new LatencySummary(
            Percentile(sorted, 0.50),
            Percentile(sorted, 0.95),
            Percentile(sorted, 0.99));
    }

    private static double Percentile(IReadOnlyList<double> sorted, double percentile)
    {
        var index = (int)Math.Ceiling(percentile * sorted.Count) - 1;
        index = Math.Clamp(index, 0, sorted.Count - 1);
        return sorted[index];
    }
}

internal sealed record RateLimitSummary(
    int Expected429,
    int Unexpected429,
    int RetryAfterBackoffs,
    double MaxRetryAfterSeconds)
{
    public static RateLimitSummary From(IReadOnlyList<ScenarioRunResult> results) =>
        new(
            results.Count(static result => result.RateLimited && result.RateLimitExpected),
            results.Count(static result => result.RateLimited && !result.RateLimitExpected),
            results.Count(static result => result.RetryAfter is not null),
            results.Select(static result => result.RetryAfter?.TotalSeconds ?? 0).DefaultIfEmpty(0).Max());
}

internal sealed record ScenarioSummary(
    string Name,
    int Count,
    int Expected,
    int Unexpected,
    LatencySummary Latency);

internal sealed record AuthReport(
    bool Enabled,
    string Mode,
    string? Target,
    string? EmailHash,
    bool LoginSucceeded,
    bool RegisteredUser,
    double BootstrapDurationMs,
    bool AuthenticatedApiCheckSucceeded)
{
    public static AuthReport Disabled { get; } = new(
        false,
        "disabled",
        null,
        null,
        false,
        false,
        0,
        false);
}

internal sealed record WriteReport(
    bool Enabled,
    string? RunId,
    int Created,
    int Updated,
    int Deleted,
    int VerifiedCreated,
    int VerifiedUpdated,
    int VerifiedDeleted,
    bool CleanupAttempted,
    int CleanupDeleted,
    int LeftoverSyntheticBooks,
    bool CleanupSucceeded,
    bool KeptSyntheticData)
{
    public string CleanupStatus =>
        !Enabled && !CleanupAttempted ? "not needed"
        : CleanupSucceeded ? $"ok, leftovers={LeftoverSyntheticBooks}"
        : $"failed, leftovers={LeftoverSyntheticBooks}";

    public static WriteReport Disabled { get; } = new(
        false,
        null,
        0,
        0,
        0,
        0,
        0,
        0,
        false,
        0,
        0,
        true,
        false);
}

internal sealed record BrowserSamplerReport(
    bool Enabled,
    int JourneysStarted,
    int JourneysSucceeded,
    int JourneysFailed,
    string? ScreenshotDirectory)
{
    public static BrowserSamplerReport Disabled { get; } = new(false, 0, 0, 0, null);
}

internal sealed record SyntheticLedgerEntry(
    int? Id,
    string Title,
    string? Author,
    string? Url,
    string State);
