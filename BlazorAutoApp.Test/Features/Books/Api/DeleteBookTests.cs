using System;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;
using BlazorAutoApp.Test.Features.Books.TestData;

namespace BlazorAutoApp.Test.Features.Books.Api;

[Collection("IntegrationTestCollection")]
public class DeleteBookTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly HttpClient _anonymousClient;
    private readonly Func<Task> _resetDatabase;
    private readonly BookDataGenerator _data = new();
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public DeleteBookTests(WebAppFactory factory)
    {
        _client = factory.CreateAuthenticatedClient();
        _anonymousClient = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Delete_Existing_ReturnsNoContent()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.UserBooks.Add(BookDataGenerator.AsUserBook(book));
            await db.SaveChangesAsync();
        }

        var response = await _client.DeleteAsync($"/api/books/{book.Id}");
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        await using var verifyDb = await _dbFactory.CreateDbContextAsync();
        verifyDb.ChangeTracker.Clear();
        var stillThere = await verifyDb.Books.AsNoTracking().FirstOrDefaultAsync(m => m.Id == book.Id);
        Assert.Null(stillThere);
    }

    [Fact]
    public async Task Delete_NotFound_Returns404()
    {
        var response = await _client.DeleteAsync("/api/books/10101010");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status404NotFound, "Book not found");
    }

    [Fact]
    public async Task Delete_OtherUsersBook_Returns404AndLeavesBook()
    {
        var book = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.OtherUserId);
            db.UserBooks.Add(BookDataGenerator.AsUserBook(book, BookTestUsers.OtherUserId));
            await db.SaveChangesAsync();
        }

        var response = await _client.DeleteAsync($"/api/books/{book.Id}");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await ProblemDetailsAssert.IsProblemAsync(response, StatusCodes.Status404NotFound, "Book not found");

        await using var verifyDb = await _dbFactory.CreateDbContextAsync();
        var stillThere = await verifyDb.Books.AsNoTracking().FirstOrDefaultAsync(m => m.Id == book.Id);
        Assert.NotNull(stillThere);
        var ownerLink = await verifyDb.UserBooks.AsNoTracking().SingleOrDefaultAsync(userBook => userBook.BookId == book.Id);
        Assert.NotNull(ownerLink);
        Assert.Equal(BookTestUsers.OtherUserId, ownerLink!.OwnerUserId);
    }

    [Fact]
    public async Task Delete_Anonymous_ReturnsUnauthorized()
    {
        var response = await _anonymousClient.DeleteAsync("/api/books/10101010");
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
