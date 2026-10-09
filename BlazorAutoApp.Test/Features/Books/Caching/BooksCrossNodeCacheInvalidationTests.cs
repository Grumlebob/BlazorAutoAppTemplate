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
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Internal;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Caching;

[Collection(TestCollectionNames.CrossNodeRedis)]
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
        var clock = new ControlledMemoryClock();
        var (nodeA, nodeB) = await StartNodesAsync(
            nodeBInvalidationEnabled: false,
            localListTtlSeconds: 1,
            localItemTtlSeconds: 1,
            configureNodeBServices: services =>
                services.Configure<MemoryCacheOptions>(options => options.Clock = clock));

        var emptyList = await GetBooksAsync(nodeB);
        Assert.Empty(emptyList.Books);

        // The first load starts asynchronous tag reads. A second read awaits any
        // pending tags before Node A writes their invalidation timestamps.
        var warmedList = await GetBooksAsync(nodeB);
        Assert.Empty(warmedList.Books);

        var created = await CreateBookAsync(nodeA, "Fallback");

        var staleList = await GetBooksAsync(nodeB);
        Assert.Empty(staleList.Books);

        clock.Advance(TimeSpan.FromMilliseconds(999));
        var stillStaleList = await GetBooksAsync(nodeB);
        Assert.Empty(stillStaleList.Books);

        clock.Advance(TimeSpan.FromMilliseconds(1));
        var refreshedList = await GetBooksAsync(nodeB);
        Assert.Single(refreshedList.Books);
        Assert.Equal(created.Id, refreshedList.Books[0].Id);
    }

    private async Task<(HttpClient NodeA, HttpClient NodeB)> StartNodesAsync(
        bool nodeBInvalidationEnabled = true,
        int localListTtlSeconds = 60,
        int localItemTtlSeconds = 60,
        Action<IServiceCollection>? configureNodeBServices = null)
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
            localItemTtlSeconds: localItemTtlSeconds,
            configureTestServices: configureNodeBServices);
        _factories.Add(nodeB);
        await nodeB.InitializeAsync();

        await nodeA.ResetDatabaseAsync();
        var userName = $"node-user-{suffix}@example.test";
        return (nodeA.CreateAuthenticatedClient(userName), nodeB.CreateAuthenticatedClient(userName));
    }

    // MemoryCache in .NET 10 uses ISystemClock; HybridCache's TimeProvider
    // alone does not control L1 expiration. Keep this clock local to Node B.
    private sealed class ControlledMemoryClock : ISystemClock
    {
        public DateTimeOffset UtcNow { get; private set; } = DateTimeOffset.UtcNow;

        public void Advance(TimeSpan amount) => UtcNow += amount;
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
