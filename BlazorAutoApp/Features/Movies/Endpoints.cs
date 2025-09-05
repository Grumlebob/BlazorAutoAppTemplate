using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Data;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;

namespace BlazorAutoApp.Features.Movies;

public static class MovieEndpoints
{
    public static IEndpointRouteBuilder MapMovieEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/movies");

        group.MapGet("/", async ([AsParameters] GetMoviesRequest _req, AppDbContext db) =>
        {
            var items = await db.Movies.AsNoTracking().ToListAsync();
            return Results.Ok(new GetMoviesResponse { Movies = items });
        });

        group.MapGet("/{id:int}", async ([AsParameters] GetMovieRequest req, AppDbContext db) =>
        {
            var movie = await db.Movies.AsNoTracking().FirstOrDefaultAsync(m => m.Id == req.Id);
            if (movie is null)
            {
                return Results.NotFound();
            }

            var response = new GetMovieResponse
            {
                Id = movie.Id,
                Title = movie.Title,
                Director = movie.Director,
                Rating = movie.Rating
            };
            return Results.Ok(response);
        });

        group.MapPost("/", async (AppDbContext db, CreateMovieRequest dto) =>
        {
            var movie = new Movie
            {
                Title = dto.Title,
                Director = dto.Director,
                Rating = dto.Rating
            };

            db.Movies.Add(movie);
            await db.SaveChangesAsync();
            var response = new CreateMovieResponse
            {
                Id = movie.Id,
                Title = movie.Title,
                Director = movie.Director,
                Rating = movie.Rating
            };
            return Results.Created($"/api/movies/{movie.Id}", response);
        });

        group.MapPut("/{id:int}", async (AppDbContext db, int id, UpdateMovieRequest req) =>
        {
            if (id != req.Id)
            {
                return Results.BadRequest("Route id and body id do not match.");
            }
            var movie = await db.Movies.FirstOrDefaultAsync(m => m.Id == id);
            if (movie is null)
            {
                return Results.NotFound();
            }

            movie.Title = req.Title;
            movie.Director = req.Director;
            movie.Rating = req.Rating;

            await db.SaveChangesAsync();

            var response = new UpdateMovieResponse
            {
                Id = movie.Id,
                Title = movie.Title,
                Director = movie.Director,
                Rating = movie.Rating
            };
            return Results.Ok(response);
        });

        group.MapDelete("/{id:int}", async ([AsParameters] DeleteMovieRequest req, AppDbContext db) =>
        {
            var movie = await db.Movies.FirstOrDefaultAsync(m => m.Id == req.Id);
            if (movie is null)
            {
                return Results.NotFound();
            }

            db.Movies.Remove(movie);
            await db.SaveChangesAsync();

            var response = new DeleteMovieResponse { Id = movie.Id };
            return Results.Ok(response);
        });

        return routes;
    }
}
