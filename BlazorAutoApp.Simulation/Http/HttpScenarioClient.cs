using System.Diagnostics;
using System.Net;

namespace BlazorAutoApp.Simulation.Http;

internal sealed class HttpScenarioClient : IDisposable
{
    private readonly HttpClient _client;

    public HttpScenarioClient(Uri baseUrl)
    {
        _client = new HttpClient(HttpClientFactory.CreateHandler(baseUrl))
        {
            BaseAddress = baseUrl,
            Timeout = TimeSpan.FromSeconds(30)
        };
        _client.DefaultRequestHeaders.UserAgent.ParseAdd("BooksTrafficSimulation/1.0");
        _client.DefaultRequestHeaders.Accept.ParseAdd("*/*");
    }

    public async Task<HttpResult> GetAsync(string path, CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, path);
            using var response = await _client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                cancellationToken);

            stopwatch.Stop();
            return new HttpResult(
                path,
                response.StatusCode,
                stopwatch.Elapsed,
                response.Headers.RetryAfter?.Delta);
        }
        catch (HttpRequestException ex)
        {
            stopwatch.Stop();
            return new HttpResult(path, null, stopwatch.Elapsed, null, ex.Message);
        }
        catch (TaskCanceledException ex) when (!cancellationToken.IsCancellationRequested)
        {
            stopwatch.Stop();
            return new HttpResult(path, null, stopwatch.Elapsed, null, ex.Message);
        }
    }

    public void Dispose()
    {
        _client.Dispose();
    }

}

internal sealed record HttpResult(
    string Path,
    HttpStatusCode? StatusCode,
    TimeSpan Duration,
    TimeSpan? RetryAfter,
    string? Error = null);
