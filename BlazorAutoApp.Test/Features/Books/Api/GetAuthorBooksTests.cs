using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection(TestCollectionNames.Integration)]
public class GetAuthorBooksTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public GetAuthorBooksTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task GetAll_ReturnsOnlyAuthorBooks()
    {
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.AuthorBooks.Add(CreateAuthorBook("gatsby", "The Great Gatsby", "F. Scott Fitzgerald"));
            db.AuthorBooks.Add(CreateAuthorBook("ship", "Ship", "Jacob Grum"));
            db.Books.Add(new Book
            {
                Title = "Private Draft",
                Author = "Integration",
                Url = null
            });
            await db.SaveChangesAsync();
        }

        var response = await _client.GetAsync("/api/author-books");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<GetAuthorBooksResponse>();
        Assert.NotNull(payload);
        Assert.Equal(2, payload!.Books.Count);
        Assert.Collection(
            payload.Books,
            first =>
            {
                Assert.Equal("gatsby", first.SeedKey);
                Assert.Equal("The Great Gatsby", first.Title);
            },
            second =>
            {
                Assert.Equal("ship", second.SeedKey);
                Assert.Equal("Ship", second.Title);
            });
    }

    [Fact]
    public async Task GetAll_PublicResponse_IsIndependentOfAuthenticatedUserAndCookies()
    {
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.AuthorBooks.Add(CreateAuthorBook("public", "Public title", "Public author"));
            await db.SaveChangesAsync();
        }

        using var anonymousRequest = new HttpRequestMessage(HttpMethod.Get, "/api/author-books");
        using var anonymousResponse = await _client.SendAsync(anonymousRequest);
        var anonymousBody = await anonymousResponse.Content.ReadAsStringAsync();

        using var authenticatedRequest = new HttpRequestMessage(HttpMethod.Get, "/api/author-books");
        authenticatedRequest.Headers.TryAddWithoutValidation(
            TestAuthenticationHandler.UserHeader,
            "catalog-viewer@example.test");
        authenticatedRequest.Headers.TryAddWithoutValidation(
            "Cookie",
            ".AspNetCore.Identity.Application=untrusted-ticket");
        using var authenticatedResponse = await _client.SendAsync(authenticatedRequest);
        var authenticatedBody = await authenticatedResponse.Content.ReadAsStringAsync();

        Assert.Equal(HttpStatusCode.OK, anonymousResponse.StatusCode);
        Assert.Equal(HttpStatusCode.OK, authenticatedResponse.StatusCode);
        Assert.Equal(anonymousBody, authenticatedBody);
        Assert.False(anonymousResponse.Headers.Contains("Set-Cookie"));
        Assert.False(authenticatedResponse.Headers.Contains("Set-Cookie"));
    }

    [Fact]
    public async Task AuthorSeedKeyRoute_IsACompatibilityRoute()
    {
        var authorBook = CreateAuthorBook("ship", "Ship", "Jacob Grum");
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.AuthorBooks.Add(authorBook);
            await db.SaveChangesAsync();
        }

        using var request = new HttpRequestMessage(HttpMethod.Get, "/books/author/ship");
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("text/html"));
        var response = await _client.SendAsync(request);

        Assert.NotEqual(HttpStatusCode.NotFound, response.StatusCode);
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }

    internal static AuthorBook CreateAuthorBook(string seedKey, string title, string? author, string? url = null) => new()
    {
        SeedKey = seedKey,
        Book = new Book
        {
            Title = title,
            Author = author,
            Url = url
        }
    };
}
