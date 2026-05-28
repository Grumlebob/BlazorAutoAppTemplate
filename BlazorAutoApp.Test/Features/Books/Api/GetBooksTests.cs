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
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;
using BlazorAutoApp.Test.Features.Books.TestData;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection("IntegrationTestCollection")]
public class GetBooksTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly HttpClient _anonymousClient;
    private readonly Func<Task> _resetDatabase;
    private readonly BookDataGenerator _data = new();
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public GetBooksTests(WebAppFactory factory)
    {
        _client = factory.CreateAuthenticatedClient();
        _anonymousClient = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task GetAll_Anonymous_ReturnsUnauthorized()
    {
        var response = await _anonymousClient.GetAsync("/api/books");
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task GetAll_Empty_ReturnsOkWithEmptyList()
    {
        var response = await _client.GetAsync("/api/books");
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<GetBooksResponse>();
        Assert.NotNull(payload);
        Assert.Empty(payload!.Books);
    }

    [Fact]
    public async Task GetAll_WithData_ReturnsOkWithCurrentUsersItems()
    {
        var currentUserBooks = _data.Generator.Generate(10);
        var otherUserBooks = _data.Generator.Generate(3);

        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId, BookTestUsers.OtherUserId);
            await db.UserBooks.AddRangeAsync(currentUserBooks.Select(book => BookDataGenerator.AsUserBook(book)));
            await db.UserBooks.AddRangeAsync(otherUserBooks.Select(book => BookDataGenerator.AsUserBook(book, BookTestUsers.OtherUserId)));
            await db.SaveChangesAsync();
        }

        var httpResponse = await _client.GetAsync("/api/books");
        httpResponse.EnsureSuccessStatusCode();
        var json = await httpResponse.Content.ReadAsStringAsync();
        Assert.DoesNotContain("ownerUserId", json, StringComparison.OrdinalIgnoreCase);
        var payload = System.Text.Json.JsonSerializer.Deserialize<GetBooksResponse>(
            json,
            new System.Text.Json.JsonSerializerOptions(System.Text.Json.JsonSerializerDefaults.Web));
        Assert.NotNull(payload);
        Assert.Equal(10, payload!.Books.Count);
        Assert.All(payload.Books, book => Assert.Contains(currentUserBooks, seeded => seeded.Id == book.Id));
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
