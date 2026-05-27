using System;
using System.Linq;
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
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;
using BlazorAutoApp.Test.Features.Books.TestData;

namespace BlazorAutoApp.Test.Features.Books.Caching;

[Collection("IntegrationTestCollection")]
public class BooksCachingTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly HttpClient _otherClient;
    private readonly Func<Task> _resetDatabase;
    private readonly BookDataGenerator _data = new();
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public BooksCachingTests(WebAppFactory factory)
    {
        _client = factory.CreateAuthenticatedClient();
        _otherClient = factory.CreateAuthenticatedClient("other-user@example.test");
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }

    [Fact]
    public async Task GetList_Cache_IsScopedByUser()
    {
        var first = await (await _client.PostAsJsonAsync("/api/books", new CreateBookRequest { Title = "User A", Author = null, Url = null })).Content.ReadFromJsonAsync<CreateBookResponse>();
        var second = await (await _otherClient.PostAsJsonAsync("/api/books", new CreateBookRequest { Title = "User B", Author = null, Url = null })).Content.ReadFromJsonAsync<CreateBookResponse>();
        Assert.NotNull(first);
        Assert.NotNull(second);

        var firstList = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        var secondList = await _otherClient.GetFromJsonAsync<GetBooksResponse>("/api/books");

        Assert.NotNull(firstList);
        Assert.NotNull(secondList);
        Assert.Single(firstList!.Books);
        Assert.Single(secondList!.Books);
        Assert.Equal(first!.Id, firstList.Books[0].Id);
        Assert.Equal(second!.Id, secondList.Books[0].Id);
    }

    [Fact]
    public async Task GetList_IsCached_UntilInvalidatedByCreate()
    {
        // Seed two books directly (bypass API so cache must read DB)
        var m1 = _data.Generator.Generate();
        var m2 = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.Books.AddRange(m1, m2);
            await db.SaveChangesAsync();
        }

        // Warm list cache
        var list1 = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        Assert.NotNull(list1);
        Assert.Equal(2, list1!.Books.Count);

        // Change DB underneath (cache should still return old list)
        var m3 = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await BookTestUsers.EnsureAsync(db, BookTestUsers.DefaultUserId);
            db.Books.Add(m3);
            await db.SaveChangesAsync();
        }

        var list2 = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        Assert.NotNull(list2);
        Assert.Equal(2, list2!.Books.Count); // still cached

        // Create via API (should invalidate list cache)
        var create = new CreateBookRequest { Title = "Cache Bust", Author = null, Url = null };
        var created = await (await _client.PostAsJsonAsync("/api/books", create)).Content.ReadFromJsonAsync<CreateBookResponse>();
        Assert.NotNull(created);

        // Next list should reflect all 4 items (m1,m2,m3,created)
        var list3 = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        Assert.NotNull(list3);
        Assert.Equal(4, list3!.Books.Count);
    }

    [Fact]
    public async Task GetById_IsCached_UntilInvalidatedByUpdate()
    {
        // Create book via API
        var create = new CreateBookRequest { Title = "Original", Author = "Author", Url = "https://example.test/books/original" };
        var created = await (await _client.PostAsJsonAsync("/api/books", create)).Content.ReadFromJsonAsync<CreateBookResponse>();
        Assert.NotNull(created);
        var id = created!.Id;

        // Warm item and list caches
        var item1 = await _client.GetFromJsonAsync<GetBookResponse>($"/api/books/{id}");
        Assert.NotNull(item1);
        Assert.Equal("Original", item1!.Title);
        var list1 = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        Assert.NotNull(list1);
        Assert.Single(list1!.Books);
        Assert.Equal("Original", list1.Books[0].Title);

        // Change DB underneath (bypass API)
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            var dbBook = await db.Books.FirstAsync(m => m.Id == id);
            dbBook.Title = "DB Changed";
            await db.SaveChangesAsync();
        }

        // Still cached
        var item2 = await _client.GetFromJsonAsync<GetBookResponse>($"/api/books/{id}");
        Assert.NotNull(item2);
        Assert.Equal("Original", item2!.Title);

        // Update via API (invalidates item + list)
        var update = new UpdateBookRequest { Id = id, Title = "Updated", Author = created.Author, Url = created.Url };
        var res = await _client.PutAsJsonAsync($"/api/books/{id}", update);
        Assert.Equal(HttpStatusCode.NoContent, res.StatusCode);

        // Next fetch should reflect updated
        var item3 = await _client.GetFromJsonAsync<GetBookResponse>($"/api/books/{id}");
        Assert.NotNull(item3);
        Assert.Equal("Updated", item3!.Title);

        var list3 = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        Assert.NotNull(list3);
        Assert.Single(list3!.Books);
        Assert.Equal("Updated", list3.Books[0].Title);
    }

    [Fact]
    public async Task Delete_Invalidates_List_And_Item_Cache()
    {
        // Create two books via API
        var created1 = await (await _client.PostAsJsonAsync("/api/books", new CreateBookRequest { Title = "A", Author = null, Url = null })).Content.ReadFromJsonAsync<CreateBookResponse>();
        var created2 = await (await _client.PostAsJsonAsync("/api/books", new CreateBookRequest { Title = "B", Author = null, Url = "https://example.test/books/b" })).Content.ReadFromJsonAsync<CreateBookResponse>();
        Assert.NotNull(created1);
        Assert.NotNull(created2);

        // Warm caches
        _ = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        _ = await _client.GetFromJsonAsync<GetBookResponse>($"/api/books/{created1!.Id}");

        // Delete one
        var del = await _client.DeleteAsync($"/api/books/{created1.Id}");
        Assert.Equal(HttpStatusCode.NoContent, del.StatusCode);

        // Item should be gone
        var itemRes = await _client.GetAsync($"/api/books/{created1.Id}");
        Assert.Equal(HttpStatusCode.NotFound, itemRes.StatusCode);

        // List should reflect remaining single book
        var list = await _client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        Assert.NotNull(list);
        Assert.Single(list!.Books);
        Assert.Equal(created2!.Id, list.Books[0].Id);
    }
}
