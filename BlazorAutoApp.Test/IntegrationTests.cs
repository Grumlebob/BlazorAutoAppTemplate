using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Data;
using BlazorAutoApp.Core.Features.Movies;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test;

[CollectionDefinition("MediaTestCollection")]
public class MediaTestCollection : ICollectionFixture<WebAppFactory> { }

[Collection("MediaTestCollection")]
public class IntegrationTests : IAsyncLifetime, IDisposable
{
    private HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly DataGenerator _dataGenerator = new();
    
    // Only store the AppDbContext - no scope field needed
    private readonly AppDbContext _appDbContext;

    public IntegrationTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        
        // Create scope locally, get context, don't store scope reference
        var scope = factory.Services.CreateScope();
        _appDbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    }

    [Fact]
    public async Task GetAllMoviesResultShouldBeOk()
    {
        // Use _appDbContext directly - no scope management needed
        var movies = _dataGenerator.Generator.Generate(10);
        await _appDbContext.Movies.AddRangeAsync(movies);
        await _appDbContext.SaveChangesAsync();

        // Act: call the API
        var httpResponse = await _client.GetAsync("/api/movies");

        // Assert: HTTP 200 and payload count matches
        httpResponse.EnsureSuccessStatusCode();
        var payload = await httpResponse.Content.ReadFromJsonAsync<GetMoviesResponse>();
        Assert.NotNull(payload);
        Assert.Equal(10, payload!.Movies.Count);
    }

    public Task InitializeAsync() => Task.CompletedTask;

    public Task DisposeAsync() => _resetDatabase();

    public void Dispose()
    {
        _appDbContext?.Dispose(); // This automatically disposes the underlying scope
        GC.SuppressFinalize(this);
    }
}