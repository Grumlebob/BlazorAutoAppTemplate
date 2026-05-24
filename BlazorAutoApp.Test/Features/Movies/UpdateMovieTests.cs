using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

[Collection("MediaTestCollection")]
public class UpdateMovieTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly DataGenerator _data = new();
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public UpdateMovieTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        var scope = factory.Services.CreateScope();
        _dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Update_Valid_ReturnsNoContentAndPersists()
    {
        var movie = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.Movies.Add(movie);
            await db.SaveChangesAsync();
        }

        var update = new UpdateMovieRequest
        {
            Id = movie.Id,
            Title = movie.Title + " (Updated)",
            Director = movie.Director,
            Rating = movie.Rating
        };

        var response = await _client.PutAsJsonAsync($"/api/movies/{movie.Id}", update);
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.ChangeTracker.Clear();
            var refreshed = await db.Movies.AsNoTracking().FirstOrDefaultAsync(m => m.Id == movie.Id);
            Assert.NotNull(refreshed);
            Assert.Equal(update.Title, refreshed!.Title);
        }
    }

    [Fact]
    public async Task Update_IdMismatch_ReturnsBadRequest()
    {
        var movie = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.Movies.Add(movie);
            await db.SaveChangesAsync();
        }

        var update = new UpdateMovieRequest
        {
            Id = movie.Id + 1,
            Title = movie.Title,
            Director = movie.Director,
            Rating = movie.Rating
        };

        var response = await _client.PutAsJsonAsync($"/api/movies/{movie.Id}", update);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Update_NotFound_Returns404()
    {
        var update = new UpdateMovieRequest
        {
            Id = 424242,
            Title = "Does not matter",
            Director = null,
            Rating = 5
        };

        var response = await _client.PutAsJsonAsync("/api/movies/424242", update);
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Update_InvalidBody_ReturnsBadRequest()
    {
        var movie = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.Movies.Add(movie);
            await db.SaveChangesAsync();
        }

        var update = new UpdateMovieRequest
        {
            Id = movie.Id,
            Title = "",
            Director = movie.Director,
            Rating = 11
        };

        var response = await _client.PutAsJsonAsync($"/api/movies/{movie.Id}", update);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    public ValueTask InitializeAsync() => ValueTask.CompletedTask;

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose() => GC.SuppressFinalize(this);
}
