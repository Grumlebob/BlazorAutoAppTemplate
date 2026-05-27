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
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;
using BlazorAutoApp.Test.Features.Books.TestData;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection("IntegrationTestCollection")]
public class UpdateBookTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly HttpClient _anonymousClient;
    private readonly Func<Task> _resetDatabase;
    private readonly BookDataGenerator _data = new();
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public UpdateBookTests(WebAppFactory factory)
    {
        _client = factory.CreateAuthenticatedClient();
        _anonymousClient = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Update_Valid_ReturnsNoContentAndPersists()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.Books.Add(book);
            await db.SaveChangesAsync();
        }

        var update = new UpdateBookRequest
        {
            Id = book.Id,
            Title = book.Title + " (Updated)",
            Author = book.Author,
            Url = book.Url
        };

        var response = await _client.PutAsJsonAsync($"/api/books/{book.Id}", update);
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.ChangeTracker.Clear();
            var refreshed = await db.Books.AsNoTracking().FirstOrDefaultAsync(m => m.Id == book.Id);
            Assert.NotNull(refreshed);
            Assert.Equal(update.Title, refreshed!.Title);
        }
    }

    [Fact]
    public async Task Update_IdMismatch_ReturnsBadRequest()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.Books.Add(book);
            await db.SaveChangesAsync();
        }

        var update = new UpdateBookRequest
        {
            Id = book.Id + 1,
            Title = book.Title,
            Author = book.Author,
            Url = book.Url
        };

        var response = await _client.PutAsJsonAsync($"/api/books/{book.Id}", update);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status400BadRequest, "Book id mismatch");
    }

    [Fact]
    public async Task Update_NotFound_Returns404()
    {
        var update = new UpdateBookRequest
        {
            Id = 424242,
            Title = "Does not matter",
            Author = null,
            Url = null
        };

        var response = await _client.PutAsJsonAsync("/api/books/424242", update);
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status404NotFound, "Book not found");
    }

    [Fact]
    public async Task Update_OtherUsersBook_Returns404AndDoesNotPersist()
    {
        var book = _data.Generator.Generate();
        book.OwnerUserId = "other-user@example.test";
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.OtherUserId);
            db.Books.Add(book);
            await db.SaveChangesAsync();
        }

        var update = new UpdateBookRequest
        {
            Id = book.Id,
            Title = "Should Not Persist",
            Author = book.Author,
            Url = book.Url
        };

        var response = await _client.PutAsJsonAsync($"/api/books/{book.Id}", update);
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status404NotFound, "Book not found");

        await using var verifyDb = await _dbFactory.CreateDbContextAsync();
        var refreshed = await verifyDb.Books.AsNoTracking().FirstAsync(m => m.Id == book.Id);
        Assert.Equal(book.Title, refreshed.Title);
        Assert.Equal("other-user@example.test", refreshed.OwnerUserId);
    }

    [Fact]
    public async Task Update_InvalidBody_ReturnsBadRequest()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.Books.Add(book);
            await db.SaveChangesAsync();
        }

        var update = new UpdateBookRequest
        {
            Id = book.Id,
            Title = "",
            Author = book.Author,
            Url = book.Url
        };

        var response = await _client.PutAsJsonAsync($"/api/books/{book.Id}", update);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await ProblemDetailsAssert.IsValidationProblemAsync(
            response,
            nameof(UpdateBookRequest.Title));
    }

    [Fact]
    public async Task Update_InvalidUrl_ReturnsBadRequest()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.Books.Add(book);
            await db.SaveChangesAsync();
        }

        var update = new UpdateBookRequest
        {
            Id = book.Id,
            Title = book.Title,
            Author = book.Author,
            Url = "not-a-url"
        };

        var response = await _client.PutAsJsonAsync($"/api/books/{book.Id}", update);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await ProblemDetailsAssert.IsValidationProblemAsync(response, nameof(UpdateBookRequest.Url));
    }

    [Fact]
    public async Task Update_Anonymous_ReturnsUnauthorized()
    {
        var update = new UpdateBookRequest
        {
            Id = 424242,
            Title = "Does not matter",
            Author = null,
            Url = null
        };

        var response = await _anonymousClient.PutAsJsonAsync("/api/books/424242", update);
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
