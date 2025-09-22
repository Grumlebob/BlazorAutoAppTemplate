namespace BlazorAutoApp.Features.Movies;

public class MoviesServerService : IMoviesApi
{
    private readonly IDbContextFactory<AppDbContext> _dbFactory;
    private readonly HybridCache _cache;
    private readonly MoviesCacheOptions _cacheOptions;

    public MoviesServerService(IDbContextFactory<AppDbContext> dbFactory, HybridCache cache, IOptions<MoviesCacheOptions> cacheOptions)
    {
        _dbFactory = dbFactory;
        _cache = cache;
        _cacheOptions = cacheOptions.Value ?? new MoviesCacheOptions();
    }

    public async Task<GetMoviesResponse> GetAsync(GetMoviesRequest req)
    {
        var key = "movies:list";
        var result = await _cache.GetOrCreateAsync(key,
            ct => new ValueTask<GetMoviesResponse>(LoadMoviesAsync(ct)),
            new HybridCacheEntryOptions
            {
                Expiration = TimeSpan.FromMinutes(Math.Max(1, _cacheOptions.ListTtlMinutes))
            });
        return result!;
    }

    public async Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req)
    {
        var key = $"movies:item:{req.Id}";
        var result = await _cache.GetOrCreateAsync(key,
            ct => new ValueTask<GetMovieResponse?>(LoadMovieAsync(req.Id, ct)),
            new HybridCacheEntryOptions
            {
                Expiration = TimeSpan.FromMinutes(Math.Max(1, _cacheOptions.ItemTtlMinutes))
            });
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

    public async Task<CreateMovieResponse> CreateAsync(CreateMovieRequest req)
    {
        await using var db = await _dbFactory.CreateDbContextAsync();
        var movie = new Movie
        {
            Title = req.Title,
            Director = req.Director,
            Rating = req.Rating
        };
        db.Movies.Add(movie);
        await db.SaveChangesAsync();
        await InvalidateAsync(movie.Id);
        return new CreateMovieResponse
        {
            Id = movie.Id,
            Title = movie.Title,
            Director = movie.Director,
            Rating = movie.Rating
        };
    }

    public async Task<bool> UpdateAsync(UpdateMovieRequest req)
    {
        await using var db = await _dbFactory.CreateDbContextAsync();
        var movie = await db.Movies.FirstOrDefaultAsync(m => m.Id == req.Id);
        if (movie is null) return false;
        movie.Title = req.Title;
        movie.Director = req.Director;
        movie.Rating = req.Rating;
        await db.SaveChangesAsync();
        await InvalidateAsync(req.Id);
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteMovieRequest req)
    {
        await using var db = await _dbFactory.CreateDbContextAsync();
        var movie = await db.Movies.FirstOrDefaultAsync(m => m.Id == req.Id);
        if (movie is null) return false;
        db.Movies.Remove(movie);
        await db.SaveChangesAsync();
        await InvalidateAsync(req.Id);
        return true;
    }

    private async Task InvalidateAsync(int id)
    {
        try
        {
            await _cache.RemoveAsync("movies:list");
            await _cache.RemoveAsync($"movies:item:{id}");
        }
        catch
        {
            // Best-effort invalidation; avoid surfacing cache errors to API consumers
        }
    }
}
