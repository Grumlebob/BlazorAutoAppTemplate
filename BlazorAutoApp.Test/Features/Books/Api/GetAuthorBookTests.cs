using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBook;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection("IntegrationTestCollection")]
public class GetAuthorBookTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public GetAuthorBookTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task GetById_Found_ReturnsAuthorBook()
    {
        var authorBook = GetAuthorBooksTests.CreateAuthorBook(
            "gatsby",
            "The Great Gatsby",
            "F. Scott Fitzgerald",
            "https://example.test/gatsby");
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.AuthorBooks.Add(authorBook);
            await db.SaveChangesAsync();
        }

        var response = await _client.GetAsync($"/api/author-books/{authorBook.BookId}");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<GetAuthorBookResponse>();
        Assert.NotNull(payload);
        Assert.Equal(authorBook.BookId, payload!.Id);
        Assert.Equal("The Great Gatsby", payload.Title);
        Assert.Equal("F. Scott Fitzgerald", payload.Author);
        Assert.Equal("https://example.test/gatsby", payload.Url);
    }

    [Fact]
    public async Task GetById_NotFound_Returns404Problem()
    {
        var response = await _client.GetAsync("/api/author-books/999999");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status404NotFound, "Author book not found");
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
