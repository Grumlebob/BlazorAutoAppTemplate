using BlazorAutoApp.Core.Features.Movies.Contracts;
using BlazorAutoApp.Core.Features.Movies.Domain;
using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.DeleteMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;
using BlazorAutoApp.Features.Movies.Caching;
using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;
using Microsoft.Extensions.Caching.Hybrid;
using Microsoft.Extensions.Options;

namespace BlazorAutoApp.Features.Movies.Services;

internal class MoviesServerService(
    IDbContextFactory<AppDbContext> dbFactory,
    HybridCache cache,
    ICacheInvalidator cacheInvalidator,
    IOptions<MoviesCacheOptions> cacheOptions,
    ILogger<MoviesServerService> logger) : IMoviesApi
{
    private readonly IDbContextFactory<AppDbContext> _dbFactory = dbFactory;
    private readonly HybridCache _cache = cache;
    private readonly ICacheInvalidator _cacheInvalidator = cacheInvalidator;
    private readonly MoviesCacheOptions _cacheOptions = cacheOptions.Value ?? new MoviesCacheOptions();
    private readonly ILogger<MoviesServerService> _logger = logger;

    public async Task<GetMoviesResponse> GetAsync(GetMoviesRequest req, CancellationToken cancellationToken = default)
    {
        var key = MoviesCacheKeys.List;
        var result = await _cache.GetOrCreateAsync(key,
            ct => new ValueTask<GetMoviesResponse>(LoadMoviesAsync(ct)),
            CreateEntryOptions(_cacheOptions.ListTtlMinutes, _cacheOptions.LocalListTtlSeconds),
            tags: [MoviesCacheKeys.AllTag, MoviesCacheKeys.ListTag],
            cancellationToken: cancellationToken);
        return result!;
    }

    public async Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req, CancellationToken cancellationToken = default)
    {
        var key = MoviesCacheKeys.Item(req.Id);
        var result = await _cache.GetOrCreateAsync(key,
            ct => new ValueTask<GetMovieResponse?>(LoadMovieAsync(req.Id, ct)),
            CreateEntryOptions(_cacheOptions.ItemTtlMinutes, _cacheOptions.LocalItemTtlSeconds),
            tags: [MoviesCacheKeys.AllTag, MoviesCacheKeys.ItemTag(req.Id)],
            cancellationToken: cancellationToken);
        return result;
    }

    private async Task<GetMoviesResponse> LoadMoviesAsync(CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var items = await db.Movies.AsNoTracking().ToListAsync(ct);
        return new GetMoviesResponse { Movies = items };
    }

    private async Task<GetMovieResponse?> LoadMovieAsync(int id, CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var movie = await db.Movies.AsNoTracking().FirstOrDefaultAsync(m => m.Id == id, ct);
        if (movie is null) return null;
        return new GetMovieResponse
        {
            Id = movie.Id,
            Title = movie.Title,
            Director = movie.Director,
            Rating = movie.Rating
        };
    }

    public async Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req, CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var movie = new Movie
        {
            Title = req.Title,
            Director = req.Director,
            Rating = req.Rating
        };
        db.Movies.Add(movie);
        await db.SaveChangesAsync(cancellationToken);
        await InvalidateAsync(movie.Id);
        return new CreateMovieResponse
        {
            Id = movie.Id,
            Title = movie.Title,
            Director = movie.Director,
            Rating = movie.Rating
        };
    }

    public async Task<bool> UpdateAsync(UpdateMovieRequest req, CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var movie = await db.Movies.FirstOrDefaultAsync(m => m.Id == req.Id, cancellationToken);
        if (movie is null) return false;
        movie.Title = req.Title;
        movie.Director = req.Director;
        movie.Rating = req.Rating;
        await db.SaveChangesAsync(cancellationToken);
        await InvalidateAsync(req.Id);
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteMovieRequest req, CancellationToken cancellationToken = default)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var movie = await db.Movies.FirstOrDefaultAsync(m => m.Id == req.Id, cancellationToken);
        if (movie is null) return false;
        db.Movies.Remove(movie);
        await db.SaveChangesAsync(cancellationToken);
        await InvalidateAsync(req.Id);
        return true;
    }

    private async Task InvalidateAsync(int id)
    {
        try
        {
            await _cacheInvalidator.InvalidateAsync(MoviesCacheKeys.ForChangedMovie(id), CancellationToken.None);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to invalidate Movies cache for movie {MovieId}", id);
        }
    }

    private HybridCacheEntryOptions CreateEntryOptions(int distributedTtlMinutes, int localTtlSeconds)
    {
        var flags = _cacheOptions.DisableLocalCache
            ? HybridCacheEntryFlags.DisableLocalCache
            : HybridCacheEntryFlags.None;

        return new HybridCacheEntryOptions
        {
            Expiration = TimeSpan.FromMinutes(Math.Max(1, distributedTtlMinutes)),
            LocalCacheExpiration = TimeSpan.FromSeconds(Math.Max(1, localTtlSeconds)),
            Flags = flags
        };
    }
}
