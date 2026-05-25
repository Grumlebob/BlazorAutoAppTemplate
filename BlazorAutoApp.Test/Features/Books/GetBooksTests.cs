using System;
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

namespace BlazorAutoApp.Test.Features.Books;

[Collection("IntegrationTestCollection")]
public class GetBooksTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly BookDataGenerator _data = new();
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public GetBooksTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
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
    public async Task GetAll_WithData_ReturnsOkWithAllItems()
    {
        var books = _data.Generator.Generate(10);
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await db.Books.AddRangeAsync(books);
            await db.SaveChangesAsync();
        }

        var httpResponse = await _client.GetAsync("/api/books");
        httpResponse.EnsureSuccessStatusCode();
        var payload = await httpResponse.Content.ReadFromJsonAsync<GetBooksResponse>();
        Assert.NotNull(payload);
        Assert.Equal(10, payload!.Books.Count);
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
