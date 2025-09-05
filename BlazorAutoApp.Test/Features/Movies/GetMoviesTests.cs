using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

[Collection("MediaTestCollection")]
public class GetMoviesTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly DataGenerator _data = new();
    private readonly AppDbContext _db;

    public GetMoviesTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        var scope = factory.Services.CreateScope();
        _db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    }

    [Fact]
    public async Task GetAll_Empty_ReturnsOkWithEmptyList()
    {
        var response = await _client.GetAsync("/api/movies");
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<GetMoviesResponse>();
        Assert.NotNull(payload);
        Assert.Empty(payload!.Movies);
    }

    [Fact]
    public async Task GetAll_WithData_ReturnsOkWithAllItems()
    {
        var movies = _data.Generator.Generate(10);
        await _db.Movies.AddRangeAsync(movies);
        await _db.SaveChangesAsync();

        var httpResponse = await _client.GetAsync("/api/movies");
        httpResponse.EnsureSuccessStatusCode();
        var payload = await httpResponse.Content.ReadFromJsonAsync<GetMoviesResponse>();
        Assert.NotNull(payload);
        Assert.Equal(10, payload!.Movies.Count);
    }

    public Task InitializeAsync() => Task.CompletedTask;

    public Task DisposeAsync() => _resetDatabase();

    public void Dispose()
    {
        _db?.Dispose();
        GC.SuppressFinalize(this);
    }
}
