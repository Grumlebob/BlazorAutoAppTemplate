using System;
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
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

[Collection("IntegrationTestCollection")]
public class CreateMovieTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly IServiceScope _scope;
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public CreateMovieTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        _scope = factory.Services.CreateScope();
        _dbFactory = _scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Create_Valid_ReturnsCreatedAndPersists()
    {
        var create = new CreateMovieRequest
        {
            Title = "Inception",
            Director = "Christopher Nolan",
            Rating = 9
        };

        var response = await _client.PostAsJsonAsync("/api/movies", create);
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<CreateMovieResponse>();
        Assert.NotNull(payload);
        Assert.True(payload!.Id > 0);
        Assert.Equal(create.Title, payload.Title);

        await using var db = await _dbFactory.CreateDbContextAsync();
        var persisted = await db.Movies.FindAsync(payload.Id);
        Assert.NotNull(persisted);
        Assert.Equal(create.Title, persisted!.Title);
    }

    [Fact]
    public async Task Create_MissingTitle_ReturnsBadRequest()
    {
        var body = new { Director = "Someone", Rating = 5 };
        var response = await _client.PostAsJsonAsync("/api/movies", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Create_InvalidRating_ReturnsBadRequest()
    {
        var create = new CreateMovieRequest
        {
            Title = "Bad Rating",
            Director = null,
            Rating = -1
        };

        var response = await _client.PostAsJsonAsync("/api/movies", create);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    public async ValueTask InitializeAsync() => await _resetDatabase();

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose()
    {
        _scope.Dispose();
        GC.SuppressFinalize(this);
    }
}
