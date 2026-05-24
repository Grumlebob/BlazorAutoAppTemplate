using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

[Collection("MediaTestCollection")]
public class GetMovieTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly DataGenerator _data = new();
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public GetMovieTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        var scope = factory.Services.CreateScope();
        _dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task GetById_Found_ReturnsOk()
    {
        var movie = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.Movies.Add(movie);
            await db.SaveChangesAsync();
        }

        var response = await _client.GetAsync($"/api/movies/{movie.Id}");
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<GetMovieResponse>();
        Assert.NotNull(payload);
        Assert.Equal(movie.Id, payload!.Id);
        Assert.Equal(movie.Title, payload.Title);
    }

    [Fact]
    public async Task GetById_NotFound_Returns404()
    {
        var response = await _client.GetAsync("/api/movies/999999");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    public ValueTask InitializeAsync() => ValueTask.CompletedTask;

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose() => GC.SuppressFinalize(this);
}
