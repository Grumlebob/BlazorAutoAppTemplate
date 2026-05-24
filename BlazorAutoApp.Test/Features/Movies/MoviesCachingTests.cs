using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Movies.Contracts;
using BlazorAutoApp.Core.Features.Movies.Domain;
using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.DeleteMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

[Collection("MediaTestCollection")]
public class MoviesCachingTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly DataGenerator _data = new();
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public MoviesCachingTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        var scope = factory.Services.CreateScope();
        _dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    public ValueTask InitializeAsync() => ValueTask.CompletedTask;

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose() => GC.SuppressFinalize(this);

    [Fact]
    public async Task GetList_IsCached_UntilInvalidatedByCreate()
    {
        // Seed two movies directly (bypass API so cache must read DB)
        var m1 = _data.Generator.Generate();
        var m2 = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.Movies.AddRange(m1, m2);
            await db.SaveChangesAsync();
        }

        // Warm list cache
        var list1 = await _client.GetFromJsonAsync<GetMoviesResponse>("/api/movies");
        Assert.NotNull(list1);
        Assert.Equal(2, list1!.Movies.Count);

        // Change DB underneath (cache should still return old list)
        var m3 = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.Movies.Add(m3);
            await db.SaveChangesAsync();
        }

        var list2 = await _client.GetFromJsonAsync<GetMoviesResponse>("/api/movies");
        Assert.NotNull(list2);
        Assert.Equal(2, list2!.Movies.Count); // still cached

        // Create via API (should invalidate list cache)
        var create = new CreateMovieRequest { Title = "Cache Bust", Director = null, Rating = 7 };
        var created = await (await _client.PostAsJsonAsync("/api/movies", create)).Content.ReadFromJsonAsync<CreateMovieResponse>();
        Assert.NotNull(created);

        // Next list should reflect all 4 items (m1,m2,m3,created)
        var list3 = await _client.GetFromJsonAsync<GetMoviesResponse>("/api/movies");
        Assert.NotNull(list3);
        Assert.Equal(4, list3!.Movies.Count);
    }

    [Fact]
    public async Task GetById_IsCached_UntilInvalidatedByUpdate()
    {
        // Create movie via API
        var create = new CreateMovieRequest { Title = "Original", Director = "Dir", Rating = 5 };
        var created = await (await _client.PostAsJsonAsync("/api/movies", create)).Content.ReadFromJsonAsync<CreateMovieResponse>();
        Assert.NotNull(created);
        var id = created!.Id;

        // Warm item cache
        var item1 = await _client.GetFromJsonAsync<GetMovieResponse>($"/api/movies/{id}");
        Assert.NotNull(item1);
        Assert.Equal("Original", item1!.Title);

        // Change DB underneath (bypass API)
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            var dbMovie = await db.Movies.FirstAsync(m => m.Id == id);
            dbMovie.Title = "DB Changed";
            await db.SaveChangesAsync();
        }

        // Still cached
        var item2 = await _client.GetFromJsonAsync<GetMovieResponse>($"/api/movies/{id}");
        Assert.NotNull(item2);
        Assert.Equal("Original", item2!.Title);

        // Update via API (invalidates item + list)
        var update = new UpdateMovieRequest { Id = id, Title = "Updated", Director = created.Director, Rating = created.Rating };
        var res = await _client.PutAsJsonAsync($"/api/movies/{id}", update);
        Assert.Equal(HttpStatusCode.NoContent, res.StatusCode);

        // Next fetch should reflect updated
        var item3 = await _client.GetFromJsonAsync<GetMovieResponse>($"/api/movies/{id}");
        Assert.NotNull(item3);
        Assert.Equal("Updated", item3!.Title);
    }

    [Fact]
    public async Task Delete_Invalidates_List_And_Item_Cache()
    {
        // Create two movies via API
        var created1 = await (await _client.PostAsJsonAsync("/api/movies", new CreateMovieRequest { Title = "A", Director = null, Rating = 6 })).Content.ReadFromJsonAsync<CreateMovieResponse>();
        var created2 = await (await _client.PostAsJsonAsync("/api/movies", new CreateMovieRequest { Title = "B", Director = null, Rating = 7 })).Content.ReadFromJsonAsync<CreateMovieResponse>();
        Assert.NotNull(created1);
        Assert.NotNull(created2);

        // Warm caches
        _ = await _client.GetFromJsonAsync<GetMoviesResponse>("/api/movies");
        _ = await _client.GetFromJsonAsync<GetMovieResponse>($"/api/movies/{created1!.Id}");

        // Delete one
        var del = await _client.DeleteAsync($"/api/movies/{created1.Id}");
        Assert.Equal(HttpStatusCode.NoContent, del.StatusCode);

        // Item should be gone
        var itemRes = await _client.GetAsync($"/api/movies/{created1.Id}");
        Assert.Equal(HttpStatusCode.NotFound, itemRes.StatusCode);

        // List should reflect remaining single movie
        var list = await _client.GetFromJsonAsync<GetMoviesResponse>("/api/movies");
        Assert.NotNull(list);
        Assert.Single(list!.Movies);
        Assert.Equal(created2!.Id, list.Movies[0].Id);
    }
}
