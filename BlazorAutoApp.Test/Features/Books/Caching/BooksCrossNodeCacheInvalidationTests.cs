using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Caching;

public sealed class BooksCrossNodeCacheInvalidationTests(SharedIntegrationEnvironment environment)
    : IClassFixture<SharedIntegrationEnvironment>, IAsyncLifetime
{
    private readonly List<WebAppFactory> _factories = [];

    public ValueTask InitializeAsync() => ValueTask.CompletedTask;

    public async ValueTask DisposeAsync()
    {
        for (var i = _factories.Count - 1; i >= 0; i--)
        {
            await _factories[i].DisposeAsync();
        }
    }

    [Fact]
    public async Task Delete_OnNodeA_InvalidatesListAndItem_OnNodeB()
    {
        var (nodeA, nodeB) = await StartNodesAsync();
        var first = await CreateBookAsync(nodeA, "Delete A");
        var second = await CreateBookAsync(nodeA, "Delete B");

        var warmedList = await GetBooksAsync(nodeB);
        Assert.Equal(2, warmedList.Books.Count);
        var warmedItem = await GetBookAsync(nodeB, first.Id);
        Assert.NotNull(warmedItem);

        var delete = await nodeA.DeleteAsync($"/api/books/{first.Id}");
        Assert.Equal(HttpStatusCode.NoContent, delete.StatusCode);

        await Eventually.EventuallyAsync(async () =>
        {
            var deletedItem = await nodeB.GetAsync($"/api/books/{first.Id}");
            Assert.Equal(HttpStatusCode.NotFound, deletedItem.StatusCode);

            var list = await GetBooksAsync(nodeB);
            Assert.Single(list.Books);
            Assert.Equal(second.Id, list.Books[0].Id);
        });
    }

    [Fact]
    public async Task Update_OnNodeA_InvalidatesItemAndList_OnNodeB()
    {
        var (nodeA, nodeB) = await StartNodesAsync();
        var created = await CreateBookAsync(nodeA, "Original");

        var warmedItem = await GetBookAsync(nodeB, created.Id);
        Assert.NotNull(warmedItem);
        Assert.Equal("Original", warmedItem!.Title);
        var warmedList = await GetBooksAsync(nodeB);
        Assert.Single(warmedList.Books);
        Assert.Equal("Original", warmedList.Books[0].Title);

        var update = new UpdateBookRequest
        {
            Id = created.Id,
            Title = "Updated",
            Author = created.Author,
            Url = created.Url
        };
        var response = await nodeA.PutAsJsonAsync($"/api/books/{created.Id}", update);
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        await Eventually.EventuallyAsync(async () =>
        {
            var item = await GetBookAsync(nodeB, created.Id);
            Assert.NotNull(item);
            Assert.Equal("Updated", item!.Title);

            var list = await GetBooksAsync(nodeB);
            Assert.Single(list.Books);
            Assert.Equal("Updated", list.Books[0].Title);
        });
    }

    [Fact]
    public async Task Create_OnNodeA_InvalidatesList_OnNodeB()
    {
        var (nodeA, nodeB) = await StartNodesAsync();

        var emptyList = await GetBooksAsync(nodeB);
        Assert.Empty(emptyList.Books);

        var created = await CreateBookAsync(nodeA, "Created");

        await Eventually.EventuallyAsync(async () =>
        {
            var list = await GetBooksAsync(nodeB);
            Assert.Single(list.Books);
            Assert.Equal(created.Id, list.Books[0].Id);
        });
    }

    [Fact]
    public async Task MissedPubSubMessage_IsBoundedByLocalCacheExpiration()
    {
        var (nodeA, nodeB) = await StartNodesAsync(
            nodeBInvalidationEnabled: false,
            localListTtlSeconds: 1,
            localItemTtlSeconds: 1);

        var emptyList = await GetBooksAsync(nodeB);
        Assert.Empty(emptyList.Books);

        var created = await CreateBookAsync(nodeA, "Fallback");

        var staleList = await GetBooksAsync(nodeB);
        Assert.Empty(staleList.Books);

        await Eventually.EventuallyAsync(async () =>
        {
            var list = await GetBooksAsync(nodeB);
            Assert.Single(list.Books);
            Assert.Equal(created.Id, list.Books[0].Id);
        }, timeout: TimeSpan.FromSeconds(8), pollInterval: TimeSpan.FromMilliseconds(200));
    }

    private async Task<(HttpClient NodeA, HttpClient NodeB)> StartNodesAsync(
        bool nodeBInvalidationEnabled = true,
        int localListTtlSeconds = 60,
        int localItemTtlSeconds = 60)
    {
        var suffix = Guid.NewGuid().ToString("N");
        var nodeA = environment.CreateFactory(
            $"node-a-{suffix}",
            runMigrations: true,
            localListTtlSeconds: localListTtlSeconds,
            localItemTtlSeconds: localItemTtlSeconds);
        _factories.Add(nodeA);
        await nodeA.InitializeAsync();

        var nodeB = environment.CreateFactory(
            $"node-b-{suffix}",
            runMigrations: false,
            cacheInvalidationEnabled: nodeBInvalidationEnabled,
            localListTtlSeconds: localListTtlSeconds,
            localItemTtlSeconds: localItemTtlSeconds);
        _factories.Add(nodeB);
        await nodeB.InitializeAsync();

        await nodeA.ResetDatabaseAsync();
        var userName = $"node-user-{suffix}@example.test";
        return (nodeA.CreateAuthenticatedClient(userName), nodeB.CreateAuthenticatedClient(userName));
    }

    private static async Task<CreateBookResponse> CreateBookAsync(HttpClient client, string title)
    {
        var request = new CreateBookRequest
        {
            Title = title,
            Author = "Author",
            Url = $"https://example.test/books/{Uri.EscapeDataString(title.ToLowerInvariant())}"
        };

        var response = await client.PostAsJsonAsync("/api/books", request);
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<CreateBookResponse>();
        Assert.NotNull(payload);
        return payload!;
    }

    private static async Task<GetBooksResponse> GetBooksAsync(HttpClient client)
    {
        var payload = await client.GetFromJsonAsync<GetBooksResponse>("/api/books");
        Assert.NotNull(payload);
        return payload!;
    }

    private static async Task<GetBookResponse?> GetBookAsync(HttpClient client, int id)
    {
        var response = await client.GetAsync($"/api/books/{id}");
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }

        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<GetBookResponse>();
    }
}
