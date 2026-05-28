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
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;
using BlazorAutoApp.Test.Features.Books.TestData;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection("IntegrationTestCollection")]
public class GetBookTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly HttpClient _anonymousClient;
    private readonly Func<Task> _resetDatabase;
    private readonly BookDataGenerator _data = new();
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public GetBookTests(WebAppFactory factory)
    {
        _client = factory.CreateAuthenticatedClient();
        _anonymousClient = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task GetById_Anonymous_ReturnsUnauthorized()
    {
        var response = await _anonymousClient.GetAsync("/api/books/1");
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task GetById_Found_ReturnsOk()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.UserBooks.Add(BookDataGenerator.AsUserBook(book));
            await db.SaveChangesAsync();
        }

        var response = await _client.GetAsync($"/api/books/{book.Id}");
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<GetBookResponse>();
        Assert.NotNull(payload);
        Assert.Equal(book.Id, payload!.Id);
        Assert.Equal(book.Title, payload.Title);
    }

    [Fact]
    public async Task GetById_OtherUsersBook_Returns404()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.OtherUserId);
            db.UserBooks.Add(BookDataGenerator.AsUserBook(book, BookTestUsers.OtherUserId));
            await db.SaveChangesAsync();
        }

        var response = await _client.GetAsync($"/api/books/{book.Id}");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status404NotFound, "Book not found");
    }

    [Fact]
    public async Task GetById_NotFound_Returns404()
    {
        var response = await _client.GetAsync("/api/books/999999");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status404NotFound, "Book not found");
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
