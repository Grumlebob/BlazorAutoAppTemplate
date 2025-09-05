using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Data;
using Microsoft.EntityFrameworkCore;

namespace BlazorAutoApp.Features.Movies;

public class MoviesServerService : IMoviesApi
{
    private readonly AppDbContext _db;

    public MoviesServerService(AppDbContext db)
    {
        _db = db;
    }

    public async Task<GetMoviesResponse> GetAsync(GetMoviesRequest req)
    {
        var items = await _db.Movies.AsNoTracking().ToListAsync();
        return new GetMoviesResponse { Movies = items };
    }

    public async Task<GetMovieResponse?> GetByIdAsync(GetMovieRequest req)
    {
        var movie = await _db.Movies.AsNoTracking().FirstOrDefaultAsync(m => m.Id == req.Id);
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
        var movie = new Movie
        {
            Title = req.Title,
            Director = req.Director,
            Rating = req.Rating
        };
        _db.Movies.Add(movie);
        await _db.SaveChangesAsync();
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
        var movie = await _db.Movies.FirstOrDefaultAsync(m => m.Id == req.Id);
        if (movie is null) return false;
        movie.Title = req.Title;
        movie.Director = req.Director;
        movie.Rating = req.Rating;
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteMovieRequest req)
    {
        var movie = await _db.Movies.FirstOrDefaultAsync(m => m.Id == req.Id);
        if (movie is null) return false;
        _db.Movies.Remove(movie);
        await _db.SaveChangesAsync();
        return true;
    }
}
