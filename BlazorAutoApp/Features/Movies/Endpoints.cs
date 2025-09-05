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

        group.MapGet("/", async ([AsParameters] GetMoviesRequest req, IMoviesApi movies) =>
        {
            var result = await movies.GetAsync(req);
            return Results.Ok(result);
        });

        group.MapGet("/{id:int}", async ([AsParameters] GetMovieRequest req, IMoviesApi movies) =>
        {
            var result = await movies.GetByIdAsync(req);
            if (result is null)
            {
                return Results.NotFound();
            }
            return Results.Ok(result);
        });

        group.MapPost("/", async (IMoviesApi movies, CreateMovieRequest dto) =>
        {
            var response = await movies.CreateAsync(dto);
            return Results.Created($"/api/movies/{response.Id}", response);
        });

        group.MapPut("/{id:int}", async (int id, UpdateMovieRequest req, IMoviesApi movies) =>
        {
            if (id != req.Id)
            {
                return Results.BadRequest("Route id and body id do not match.");
            }
            var success = await movies.UpdateAsync(req);
            if (!success)
            {
                return Results.NotFound();
            }
            return Results.NoContent();
        });

        group.MapDelete("/{id:int}", async ([AsParameters] DeleteMovieRequest req, IMoviesApi movies) =>
        {
            var success = await movies.DeleteAsync(req);
            if (!success)
            {
                return Results.NotFound();
            }
            return Results.NoContent();
        });

        return routes;
    }
}
