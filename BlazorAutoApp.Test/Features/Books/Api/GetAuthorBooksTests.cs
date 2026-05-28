using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection("IntegrationTestCollection")]
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
    public async Task AuthorSeedKeyRoute_IsACompatibilityRoute()
    {
        var authorBook = CreateAuthorBook("ship", "Ship", "Jacob Grum");
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.AuthorBooks.Add(authorBook);
            await db.SaveChangesAsync();
        }

        var response = await _client.GetAsync("/books/author/ship");

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
