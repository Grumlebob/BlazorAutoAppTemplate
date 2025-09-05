using BlazorAutoApp.Core.Features.Movies;
using BlazorAutoApp.Data;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using BlazorAutoApp.Infrastructure.Validation;
using Microsoft.Extensions.Logging;

namespace BlazorAutoApp.Features.Movies;

public static class MovieEndpoints
{
    public static IEndpointRouteBuilder MapMovieEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/movies");

        group.MapGet("/", async ([AsParameters] GetMoviesRequest req, IMoviesApi movies, ILogger<Program> log) =>
        {
            log.LogDebug("Listing movies");
            var result = await movies.GetAsync(req);
            return Results.Ok(result);
        });

        group.MapGet("/{id:int}", async ([AsParameters] GetMovieRequest req, IMoviesApi movies, ILogger<Program> log) =>
        {
            var result = await movies.GetByIdAsync(req);
            if (result is null)
            {
                log.LogWarning("Movie {MovieId} not found", req.Id);
                return Results.NotFound();
            }
            log.LogInformation("Fetched movie {MovieId}", req.Id);
            return Results.Ok(result);
        });

        group.MapPost("/", async (IMoviesApi movies, CreateMovieRequest dto, ILogger<Program> log) =>
        {
            var response = await movies.CreateAsync(dto);
            log.LogInformation("Created movie {MovieId} - {Title}", response.Id, response.Title);
            return Results.Created($"/api/movies/{response.Id}", response);
        })
        .AddEndpointFilter(new ValidateFilter<CreateMovieRequest>());

        group.MapPut("/{id:int}", async (int id, UpdateMovieRequest req, IMoviesApi movies, ILogger<Program> log) =>
        {
            if (id != req.Id)
            {
                log.LogWarning("Update mismatch: route id {RouteId} != body id {BodyId}", id, req.Id);
                return Results.BadRequest("Route id and body id do not match.");
            }
            var success = await movies.UpdateAsync(req);
            if (!success)
            {
                log.LogWarning("Movie {MovieId} not found for update", req.Id);
                return Results.NotFound();
            }
            log.LogInformation("Updated movie {MovieId}", req.Id);
            return Results.NoContent();
        })
        .AddEndpointFilter(new ValidateFilter<UpdateMovieRequest>());

        group.MapDelete("/{id:int}", async ([AsParameters] DeleteMovieRequest req, IMoviesApi movies, ILogger<Program> log) =>
        {
            var success = await movies.DeleteAsync(req);
            if (!success)
            {
                log.LogWarning("Movie {MovieId} not found for delete", req.Id);
                return Results.NotFound();
            }
            log.LogInformation("Deleted movie {MovieId}", req.Id);
            return Results.NoContent();
        });

        return routes;
    }
}
