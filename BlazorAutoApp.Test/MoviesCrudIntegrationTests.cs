using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test;

[Collection("MediaTestCollection")]
public class MoviesCrudIntegrationTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly DataGenerator _data = new();
    private readonly AppDbContext _db;

    public MoviesCrudIntegrationTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;

        var scope = factory.Services.CreateScope();
        _db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    }

    // GET /api/movies — empty returns 200 with empty list
    [Fact]
    public async Task GetAll_Empty_ReturnsOkWithEmptyList()
    {
        var response = await _client.GetAsync("/api/movies");
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<GetMoviesResponse>();
        Assert.NotNull(payload);
        Assert.Empty(payload!.Movies);
    }

    // GET /api/movies — with data returns all
    [Fact]
    public async Task GetAll_WithData_ReturnsOkWithAllItems()
    {
        var movies = _data.Generator.Generate(3);
        await _db.Movies.AddRangeAsync(movies);
        await _db.SaveChangesAsync();

        var response = await _client.GetAsync("/api/movies");
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<GetMoviesResponse>();
        Assert.NotNull(payload);
        Assert.Equal(3, payload!.Movies.Count);
    }

    // GET /api/movies/{id} — found
    [Fact]
    public async Task GetById_Found_ReturnsOk()
    {
        var movie = _data.Generator.Generate();
        _db.Movies.Add(movie);
        await _db.SaveChangesAsync();

        var response = await _client.GetAsync($"/api/movies/{movie.Id}");
        response.EnsureSuccessStatusCode();
        var payload = await response.Content.ReadFromJsonAsync<GetMovieResponse>();
        Assert.NotNull(payload);
        Assert.Equal(movie.Id, payload!.Id);
        Assert.Equal(movie.Title, payload.Title);
    }

    // GET /api/movies/{id} — not found
    [Fact]
    public async Task GetById_NotFound_Returns404()
    {
        var response = await _client.GetAsync("/api/movies/999999");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    // POST /api/movies — valid create
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

        var persisted = await _db.Movies.FindAsync(payload.Id);
        Assert.NotNull(persisted);
        Assert.Equal(create.Title, persisted!.Title);
    }

    // POST /api/movies — missing required Title -> 400
    [Fact]
    public async Task Create_MissingTitle_ReturnsBadRequest()
    {
        var body = new { Director = "Someone", Rating = 5 };
        var response = await _client.PostAsJsonAsync("/api/movies", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    // POST /api/movies — invalid rating -> 400
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

    // PUT /api/movies/{id} — success
    [Fact]
    public async Task Update_Valid_ReturnsNoContentAndPersists()
    {
        var movie = _data.Generator.Generate();
        _db.Movies.Add(movie);
        await _db.SaveChangesAsync();

        var update = new UpdateMovieRequest
        {
            Id = movie.Id,
            Title = movie.Title + " (Updated)",
            Director = movie.Director,
            Rating = movie.Rating
        };

        var response = await _client.PutAsJsonAsync($"/api/movies/{movie.Id}", update);
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        // Ensure verification is against database state, not a tracked cache
        _db.ChangeTracker.Clear();
        var refreshed = await _db.Movies.AsNoTracking().FirstOrDefaultAsync(m => m.Id == movie.Id);
        Assert.NotNull(refreshed);
        Assert.Equal(update.Title, refreshed!.Title);
    }

    // PUT /api/movies/{id} — id mismatch -> 400
    [Fact]
    public async Task Update_IdMismatch_ReturnsBadRequest()
    {
        var movie = _data.Generator.Generate();
        _db.Movies.Add(movie);
        await _db.SaveChangesAsync();

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

    // PUT /api/movies/{id} — not found -> 404
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

    // PUT /api/movies/{id} — invalid body -> 400
    [Fact]
    public async Task Update_InvalidBody_ReturnsBadRequest()
    {
        var movie = _data.Generator.Generate();
        _db.Movies.Add(movie);
        await _db.SaveChangesAsync();

        var update = new UpdateMovieRequest
        {
            Id = movie.Id,
            Title = "", // invalid due to [Required] + StringLength
            Director = movie.Director,
            Rating = 11 // invalid due to [Range(0,10)]
        };

        var response = await _client.PutAsJsonAsync($"/api/movies/{movie.Id}", update);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    // DELETE /api/movies/{id} — success
    [Fact]
    public async Task Delete_Existing_ReturnsNoContent()
    {
        var movie = _data.Generator.Generate();
        _db.Movies.Add(movie);
        await _db.SaveChangesAsync();

        var response = await _client.DeleteAsync($"/api/movies/{movie.Id}");
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        // Ensure we don't return a tracked entity from the change tracker cache
        _db.ChangeTracker.Clear();
        var stillThere = await _db.Movies.AsNoTracking().FirstOrDefaultAsync(m => m.Id == movie.Id);
        Assert.Null(stillThere);
    }

    // DELETE /api/movies/{id} — not found
    [Fact]
    public async Task Delete_NotFound_Returns404()
    {
        var response = await _client.DeleteAsync("/api/movies/10101010");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    public Task InitializeAsync() => Task.CompletedTask;

    public Task DisposeAsync() => _resetDatabase();

    public void Dispose()
    {
        _db?.Dispose();
        GC.SuppressFinalize(this);
    }
}
