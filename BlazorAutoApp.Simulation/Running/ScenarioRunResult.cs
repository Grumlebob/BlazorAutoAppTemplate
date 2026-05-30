using System.Net;
using BlazorAutoApp.Simulation.Scenarios;

namespace BlazorAutoApp.Simulation.Running;

internal sealed record ScenarioRunResult(
    string ScenarioName,
    ScenarioCategory Category,
    string Path,
    HttpStatusCode? StatusCode,
    bool Expected,
    bool RateLimited,
    bool RateLimitExpected,
    TimeSpan Duration,
    TimeSpan? RetryAfter,
    string? Error);
