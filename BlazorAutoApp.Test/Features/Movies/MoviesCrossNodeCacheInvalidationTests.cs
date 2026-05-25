using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;
using BlazorAutoApp.Test.TestSupport.Integration;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

public sealed class MoviesCrossNodeCacheInvalidationTests(SharedIntegrationEnvironment environment)
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
        var first = await CreateMovieAsync(nodeA, "Delete A");
        var second = await CreateMovieAsync(nodeA, "Delete B");

        var warmedList = await GetMoviesAsync(nodeB);
        Assert.Equal(2, warmedList.Movies.Count);
        var warmedItem = await GetMovieAsync(nodeB, first.Id);
        Assert.NotNull(warmedItem);

        var delete = await nodeA.DeleteAsync($"/api/movies/{first.Id}");
        Assert.Equal(HttpStatusCode.NoContent, delete.StatusCode);

        await Eventually.EventuallyAsync(async () =>
        {
            var deletedItem = await nodeB.GetAsync($"/api/movies/{first.Id}");
            Assert.Equal(HttpStatusCode.NotFound, deletedItem.StatusCode);

            var list = await GetMoviesAsync(nodeB);
            Assert.Single(list.Movies);
            Assert.Equal(second.Id, list.Movies[0].Id);
        });
    }

    [Fact]
    public async Task Update_OnNodeA_InvalidatesItemAndList_OnNodeB()
    {
        var (nodeA, nodeB) = await StartNodesAsync();
        var created = await CreateMovieAsync(nodeA, "Original");

        var warmedItem = await GetMovieAsync(nodeB, created.Id);
        Assert.NotNull(warmedItem);
        Assert.Equal("Original", warmedItem!.Title);
        var warmedList = await GetMoviesAsync(nodeB);
        Assert.Single(warmedList.Movies);
        Assert.Equal("Original", warmedList.Movies[0].Title);

        var update = new UpdateMovieRequest
        {
            Id = created.Id,
            Title = "Updated",
            Director = created.Director,
            Rating = created.Rating
        };
        var response = await nodeA.PutAsJsonAsync($"/api/movies/{created.Id}", update);
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        await Eventually.EventuallyAsync(async () =>
        {
            var item = await GetMovieAsync(nodeB, created.Id);
            Assert.NotNull(item);
            Assert.Equal("Updated", item!.Title);

            var list = await GetMoviesAsync(nodeB);
            Assert.Single(list.Movies);
            Assert.Equal("Updated", list.Movies[0].Title);
        });
    }

    [Fact]
    public async Task Create_OnNodeA_InvalidatesList_OnNodeB()
    {
        var (nodeA, nodeB) = await StartNodesAsync();

        var emptyList = await GetMoviesAsync(nodeB);
        Assert.Empty(emptyList.Movies);

        var created = await CreateMovieAsync(nodeA, "Created");

        await Eventually.EventuallyAsync(async () =>
        {
            var list = await GetMoviesAsync(nodeB);
            Assert.Single(list.Movies);
            Assert.Equal(created.Id, list.Movies[0].Id);
        });
    }

    [Fact]
    public async Task MissedPubSubMessage_IsBoundedByLocalCacheExpiration()
    {
        var (nodeA, nodeB) = await StartNodesAsync(
            nodeBInvalidationEnabled: false,
            localListTtlSeconds: 1,
            localItemTtlSeconds: 1);

        var emptyList = await GetMoviesAsync(nodeB);
        Assert.Empty(emptyList.Movies);

        var created = await CreateMovieAsync(nodeA, "Fallback");

        var staleList = await GetMoviesAsync(nodeB);
        Assert.Empty(staleList.Movies);

        await Eventually.EventuallyAsync(async () =>
        {
            var list = await GetMoviesAsync(nodeB);
            Assert.Single(list.Movies);
            Assert.Equal(created.Id, list.Movies[0].Id);
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
        return (nodeA.HttpClient, nodeB.HttpClient);
    }

    private static async Task<CreateMovieResponse> CreateMovieAsync(HttpClient client, string title)
    {
        var request = new CreateMovieRequest
        {
            Title = title,
            Director = "Director",
            Rating = 8
        };

        var response = await client.PostAsJsonAsync("/api/movies", request);
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<CreateMovieResponse>();
        Assert.NotNull(payload);
        return payload!;
    }

    private static async Task<GetMoviesResponse> GetMoviesAsync(HttpClient client)
    {
        var payload = await client.GetFromJsonAsync<GetMoviesResponse>("/api/movies");
        Assert.NotNull(payload);
        return payload!;
    }

    private static async Task<GetMovieResponse?> GetMovieAsync(HttpClient client, int id)
    {
        var response = await client.GetAsync($"/api/movies/{id}");
        if (response.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }

        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<GetMovieResponse>();
    }
}
