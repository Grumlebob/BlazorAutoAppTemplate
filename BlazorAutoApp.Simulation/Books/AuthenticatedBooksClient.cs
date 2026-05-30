using System.Diagnostics;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
using BlazorAutoApp.Simulation.Http;
using BlazorAutoApp.Simulation.Running;
using BlazorAutoApp.Simulation.Scenarios;

namespace BlazorAutoApp.Simulation.Books;

internal sealed class AuthenticatedBooksClient : IDisposable
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private readonly HttpClient _client;

    public AuthenticatedBooksClient(Uri baseUrl, CookieContainer cookies)
    {
        _client = new HttpClient(HttpClientFactory.CreateHandler(baseUrl, cookies))
        {
            BaseAddress = baseUrl,
            Timeout = TimeSpan.FromSeconds(30)
        };
        _client.DefaultRequestHeaders.UserAgent.ParseAdd("BooksTrafficSimulation/1.0");
        _client.DefaultRequestHeaders.Accept.ParseAdd("application/json");
    }

    public async Task<BookClientResult<IReadOnlyList<BookListItemResponse>>> ListAsync(
        string scenarioName,
        CancellationToken cancellationToken)
    {
        var result = await SendAsync<GetBooksResponse>(HttpMethod.Get, "/api/books", null, scenarioName, HttpStatusCode.OK, cancellationToken);
        return new BookClientResult<IReadOnlyList<BookListItemResponse>>(
            result.ScenarioName,
            result.Path,
            result.StatusCode,
            result.Expected,
            result.Duration,
            result.RetryAfter,
            result.Error,
            result.Value?.Books ?? []);
    }

    public async Task<BookClientResult<GetBookResponse>> GetAsync(int id, CancellationToken cancellationToken)
    {
        var result = await SendAsync<GetBookResponse>(
            HttpMethod.Get,
            $"/api/books/{id}",
            null,
            "authenticated_book_detail",
            HttpStatusCode.OK,
            cancellationToken);
        return result;
    }

    public Task<BookClientResult<CreateBookResponse>> CreateAsync(
        CreateBookRequest request,
        CancellationToken cancellationToken) =>
        SendAsync<CreateBookResponse>(
            HttpMethod.Post,
            "/api/books",
            request,
            "authenticated_book_create",
            HttpStatusCode.Created,
            cancellationToken);

    public Task<BookClientResult<object>> UpdateAsync(
        UpdateBookRequest request,
        CancellationToken cancellationToken) =>
        SendAsync<object>(
            HttpMethod.Put,
            $"/api/books/{request.Id}",
            request,
            "authenticated_book_update",
            HttpStatusCode.NoContent,
            cancellationToken);

    public Task<BookClientResult<object>> DeleteAsync(int id, CancellationToken cancellationToken) =>
        SendAsync<object>(
            HttpMethod.Delete,
            $"/api/books/{id}",
            null,
            "authenticated_book_delete",
            HttpStatusCode.NoContent,
            cancellationToken);

    public ScenarioRunResult ToScenarioResult<T>(
        BookClientResult<T> result,
        ScenarioCategory category) =>
        new(
            result.ScenarioName,
            category,
            result.Path,
            result.StatusCode,
            result.Expected,
            result.StatusCode == HttpStatusCode.TooManyRequests,
            false,
            result.Duration,
            result.RetryAfter,
            result.Error);

    public void Dispose()
    {
        _client.Dispose();
    }

    private async Task<BookClientResult<T>> SendAsync<T>(
        HttpMethod method,
        string path,
        object? body,
        string scenarioName,
        HttpStatusCode expectedStatusCode,
        CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        try
        {
            using var request = new HttpRequestMessage(method, path);
            if (body is not null)
            {
                request.Content = JsonContent.Create(body, options: JsonOptions);
            }

            using var response = await _client.SendAsync(request, cancellationToken);
            stopwatch.Stop();

            T? value = default;
            if (response.Content.Headers.ContentLength != 0
                && response.Content.Headers.ContentType?.MediaType?.Contains("json", StringComparison.OrdinalIgnoreCase) == true)
            {
                value = await response.Content.ReadFromJsonAsync<T>(JsonOptions, cancellationToken);
            }

            return new BookClientResult<T>(
                scenarioName,
                path,
                response.StatusCode,
                response.StatusCode == expectedStatusCode,
                stopwatch.Elapsed,
                response.Headers.RetryAfter?.Delta,
                null,
                value);
        }
        catch (HttpRequestException ex)
        {
            stopwatch.Stop();
            return new BookClientResult<T>(
                scenarioName,
                path,
                null,
                false,
                stopwatch.Elapsed,
                null,
                ex.Message,
                default);
        }
        catch (TaskCanceledException ex) when (!cancellationToken.IsCancellationRequested)
        {
            stopwatch.Stop();
            return new BookClientResult<T>(
                scenarioName,
                path,
                null,
                false,
                stopwatch.Elapsed,
                null,
                ex.Message,
                default);
        }
    }
}
