using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.DeleteBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.Features.Books.TestData;
using Microsoft.EntityFrameworkCore;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection("IntegrationTestCollection")]
public class CreateBookTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly HttpClient _anonymousClient;
    private readonly Func<Task> _resetDatabase;
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public CreateBookTests(WebAppFactory factory)
    {
        _client = factory.CreateAuthenticatedClient();
        _anonymousClient = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Create_Valid_ReturnsCreatedAndPersists()
    {
        var create = new CreateBookRequest
        {
            Title = "The Left Hand of Darkness",
            Author = "Ursula K. Le Guin",
            Url = "https://example.test/books/left-hand-of-darkness"
        };

        var response = await _client.PostAsJsonAsync("/api/books", create);
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<CreateBookResponse>();
        Assert.NotNull(payload);
        Assert.True(payload!.Id > 0);
        Assert.Equal(create.Title, payload.Title);

        await using var db = await _dbFactory.CreateDbContextAsync();
        var persisted = await db.Books.FindAsync(payload.Id);
        Assert.NotNull(persisted);
        Assert.Equal(create.Title, persisted!.Title);
        Assert.Equal(create.Url, persisted.Url);
        Assert.Equal(BookDataGenerator.DefaultOwnerUserId, persisted.OwnerUserId);
    }

    [Fact]
    public async Task Create_Valid_IsReturnedByNormalListForSameUser()
    {
        var create = new CreateBookRequest
        {
            Title = "Persisted Reload Book",
            Author = "Integration Test",
            Url = "https://example.test/books/persisted-reload"
        };

        var createResponse = await _client.PostAsJsonAsync("/api/books", create);
        createResponse.EnsureSuccessStatusCode();
        var created = await createResponse.Content.ReadFromJsonAsync<CreateBookResponse>();
        Assert.NotNull(created);

        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            var persisted = await db.Books.AsNoTracking().SingleOrDefaultAsync(book => book.Id == created!.Id);
            Assert.NotNull(persisted);
            Assert.Equal(BookDataGenerator.DefaultOwnerUserId, persisted!.OwnerUserId);
        }

        var listResponse = await _client.GetAsync("/api/books");
        listResponse.EnsureSuccessStatusCode();
        var list = await listResponse.Content.ReadFromJsonAsync<GetBooksResponse>();
        Assert.NotNull(list);
        var reloaded = Assert.Single(list!.Books, book => book.Id == created!.Id);
        Assert.Equal(create.Title, reloaded.Title);
        Assert.Equal(create.Author, reloaded.Author);
        Assert.Equal(create.Url, reloaded.Url);
    }

    [Fact]
    public async Task Create_Anonymous_ReturnsUnauthorized()
    {
        var create = new CreateBookRequest
        {
            Title = "Anonymous Book",
            Author = "Someone",
            Url = "https://example.test/books/anonymous"
        };

        var response = await _anonymousClient.PostAsJsonAsync("/api/books", create);
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Create_MissingTitle_ReturnsBadRequest()
    {
        var body = new { Author = "Someone", Url = "https://example.test/books/missing-title" };
        var response = await _client.PostAsJsonAsync("/api/books", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Create_InvalidUrl_ReturnsBadRequest()
    {
        var create = new CreateBookRequest
        {
            Title = "Bad URL",
            Author = null,
            Url = "not-a-url"
        };

        var response = await _client.PostAsJsonAsync("/api/books", create);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await ProblemDetailsAssert.IsValidationProblemAsync(response, nameof(CreateBookRequest.Url));
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
