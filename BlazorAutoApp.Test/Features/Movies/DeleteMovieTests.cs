using System;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using BlazorAutoApp.Data;
using BlazorAutoApp.Test.TestingSetup;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Movies;

[Collection("MediaTestCollection")]
public class DeleteMovieTests : IAsyncLifetime, IDisposable
{
    private readonly HttpClient _client;
    private readonly Func<Task> _resetDatabase;
    private readonly DataGenerator _data = new();
    private readonly IDbContextFactory<AppDbContext> _dbFactory;

    public DeleteMovieTests(WebAppFactory factory)
    {
        _client = factory.HttpClient;
        _resetDatabase = factory.ResetDatabaseAsync;
        var scope = factory.Services.CreateScope();
        _dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
    }

    [Fact]
    public async Task Delete_Existing_ReturnsNoContent()
    {
        var movie = _data.Generator.Generate();
        await using (var db = await _dbFactory.CreateDbContextAsync())
        {
            db.Movies.Add(movie);
            await db.SaveChangesAsync();
        }

        var response = await _client.DeleteAsync($"/api/movies/{movie.Id}");
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);

        await using var verifyDb = await _dbFactory.CreateDbContextAsync();
        verifyDb.ChangeTracker.Clear();
        var stillThere = await verifyDb.Movies.AsNoTracking().FirstOrDefaultAsync(m => m.Id == movie.Id);
        Assert.Null(stillThere);
    }

    [Fact]
    public async Task Delete_NotFound_Returns404()
    {
        var response = await _client.DeleteAsync("/api/movies/10101010");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    public ValueTask InitializeAsync() => ValueTask.CompletedTask;

    public async ValueTask DisposeAsync() => await _resetDatabase();

    public void Dispose() => GC.SuppressFinalize(this);
}
