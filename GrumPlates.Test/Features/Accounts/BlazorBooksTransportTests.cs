using System.Security.Claims;
using GrumPlates.Client.Features.Books;
using Microsoft.AspNetCore.Components.Authorization;

namespace GrumPlates.Test.Features.Accounts;

public sealed class BlazorBooksTransportTests
{
    [Fact]
    public async Task EnabledWrite_AttachesCapturedOwnerAndFreshCsrfToken()
    {
        var handler = new RecordingHandler((request, _) => new HttpResponseMessage(request.RequestUri!.AbsolutePath switch
        {
            "/api/client-config" => HttpStatusCode.OK,
            "/api/auth/session" => HttpStatusCode.OK,
            "/api/books" => HttpStatusCode.Created,
            _ => HttpStatusCode.NotFound
        })
        {
            Content = request.RequestUri!.AbsolutePath switch
            {
                "/api/client-config" => Json(new { schemaVersion = 1, accountsEnabled = true, applicationId = new string('a', 32) }),
                "/api/auth/session" => Json(new { enabled = true, registrationEnabled = false, emailEnabled = false, csrfToken = "fresh-csrf", user = (object?)null }),
                _ => Json(new { id = 7, title = "Fixture" })
            }
        });
        using var client = CreateClient(handler, "owner-7");

        using var response = await client.PostAsJsonAsync("api/books", new { title = "Fixture" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.Collection(handler.Requests,
            configuration => Assert.Equal("/api/client-config", configuration.Path),
            session => Assert.Equal("/api/auth/session", session.Path),
            write =>
            {
                Assert.Equal("/api/books", write.Path);
                Assert.Equal("owner-7", write.ExpectedUser);
                Assert.Equal("fresh-csrf", write.CsrfToken);
            });
    }

    [Fact]
    public async Task SessionChangeAfterOwnerCapture_KeepsTheOriginalExpectedUserOnWrite()
    {
        var handler = new RecordingHandler((request, captured) =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (path == "/api/client-config") return JsonResponse(new { schemaVersion = 1, accountsEnabled = true, applicationId = new string('b', 32) });
            if (path == "/api/auth/session") return JsonResponse(new { enabled = true, registrationEnabled = false, emailEnabled = false, csrfToken = "csrf-b", user = new { id = "owner-b", email = "b@example.test", roles = Array.Empty<string>() } });
            return captured.ExpectedUser == "owner-a"
                ? new HttpResponseMessage(HttpStatusCode.Conflict)
                : new HttpResponseMessage(HttpStatusCode.Created);
        });
        using var client = CreateClient(handler, "owner-a");

        using var response = await client.PostAsJsonAsync("api/books", new { title = "Should be rejected" });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("owner-a", handler.Requests[^1].ExpectedUser);
        Assert.Equal("csrf-b", handler.Requests[^1].CsrfToken);
    }

    [Fact]
    public async Task DisabledAccounts_PreservesTheExistingTransportWithoutSessionHeaders()
    {
        var handler = new RecordingHandler((request, _) => request.RequestUri!.AbsolutePath == "/api/client-config"
            ? JsonResponse(new { schemaVersion = 1, accountsEnabled = false, applicationId = new string('c', 32) })
            : new HttpResponseMessage(HttpStatusCode.OK));
        using var client = CreateClient(handler, "legacy-user");

        using var response = await client.GetAsync("api/books");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Collection(handler.Requests,
            configuration => Assert.Equal("/api/client-config", configuration.Path),
            books =>
            {
                Assert.Equal("/api/books", books.Path);
                Assert.Null(books.ExpectedUser);
                Assert.Null(books.CsrfToken);
            });
    }

    private static HttpClient CreateClient(RecordingHandler innerHandler, string userId)
    {
        var handler = new BooksAntiforgeryHandler(new FixtureAuthenticationStateProvider(userId))
        {
            InnerHandler = innerHandler
        };
        return new HttpClient(handler) { BaseAddress = new Uri("https://app.example.test/") };
    }

    private static StringContent Json<T>(T value) => new(System.Text.Json.JsonSerializer.Serialize(value), System.Text.Encoding.UTF8, "application/json");

    private static HttpResponseMessage JsonResponse<T>(T value) => new(HttpStatusCode.OK) { Content = Json(value) };

    private sealed class FixtureAuthenticationStateProvider(string userId) : AuthenticationStateProvider
    {
        public override Task<AuthenticationState> GetAuthenticationStateAsync() => Task.FromResult(
            new AuthenticationState(new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim(ClaimTypes.NameIdentifier, userId)], "fixture"))));
    }

    private sealed class RecordingHandler(Func<HttpRequestMessage, CapturedRequest, HttpResponseMessage> respond) : HttpMessageHandler
    {
        public List<CapturedRequest> Requests { get; } = [];

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            var captured = new CapturedRequest(
                request.RequestUri!.AbsolutePath,
                request.Method,
                request.Headers.TryGetValues("X-Expected-User", out var owner) ? owner.Single() : null,
                request.Headers.TryGetValues("X-CSRF-TOKEN", out var csrf) ? csrf.Single() : null);
            Requests.Add(captured);
            return Task.FromResult(respond(request, captured));
        }
    }

    private sealed record CapturedRequest(string Path, HttpMethod Method, string? ExpectedUser, string? CsrfToken);
}
