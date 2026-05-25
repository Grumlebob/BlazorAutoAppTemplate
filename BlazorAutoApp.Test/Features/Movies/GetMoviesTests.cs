using System;
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
using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using Xunit;
using BlazorAutoApp.Test.Features.Movies.TestData;

namespace BlazorAutoApp.Test.Features.Movies;

[Collection("IntegrationTestCollection")]
public class GetMoviesTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly MovieDataGenerator _data = new();
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public GetMoviesTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
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
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            await db.Movies.AddRangeAsync(movies);
            await db.SaveChangesAsync();
        }

        var httpResponse = await _client.GetAsync("/api/movies");
        httpResponse.EnsureSuccessStatusCode();
        var payload = await httpResponse.Content.ReadFromJsonAsync<GetMoviesResponse>();
        Assert.NotNull(payload);
        Assert.Equal(10, payload!.Movies.Count);
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
