using System.Net;

namespace BlazorAutoApp.Simulation.Books;

internal sealed record BookClientResult<T>(
    string ScenarioName,
    string Path,
    HttpStatusCode? StatusCode,
    bool Expected,
    TimeSpan Duration,
    TimeSpan? RetryAfter,
    string? Error,
    T? Value);
