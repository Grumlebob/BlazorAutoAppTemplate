using BlazorAutoApp.Core.Features.Movies.Contracts;
using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.DeleteMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;
using BlazorAutoApp.Features.Movies.Validation;
using BlazorAutoApp.Security;

namespace BlazorAutoApp.Features.Movies.Endpoints;

public static class MovieEndpoints
{
    public static IEndpointRouteBuilder MapMovieEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/movies")
            .RequireRateLimiting(AppRateLimiting.ApiPolicyName);

        group.MapGet("/", async ([AsParameters] GetMoviesRequest req, IMoviesApi movies, ILogger<Program> log, CancellationToken cancellationToken) =>
        {
            log.LogDebug("Listing movies");
            var result = await movies.GetAsync(req, cancellationToken);
            return Results.Ok(result);
        });

        group.MapGet("/{id:int}", async ([AsParameters] GetMovieRequest req, IMoviesApi movies, ILogger<Program> log, CancellationToken cancellationToken) =>
        {
            var result = await movies.GetByIdAsync(req, cancellationToken);
            if (result is null)
            {
                log.LogWarning("Movie {MovieId} not found", req.Id);
                return Results.Problem(
                    statusCode: StatusCodes.Status404NotFound,
                    title: "Movie not found",
                    detail: $"Movie {req.Id} was not found.");
            }
            log.LogInformation("Fetched movie {MovieId}", req.Id);
            return Results.Ok(result);
        });

        group.MapPost("/", async (IMoviesApi movies, CreateMovieRequest dto, ILogger<Program> log, CancellationToken cancellationToken) =>
        {
            var response = await movies.CreateAsync(dto, cancellationToken);
            log.LogInformation("Created movie {MovieId} - {Title}", response.Id, response.Title);
            return Results.Created($"/api/movies/{response.Id}", response);
        })
        .AddEndpointFilter(new DataAnnotationsValidateFilter<CreateMovieRequest>());

        group.MapPut("/{id:int}", async (int id, UpdateMovieRequest req, IMoviesApi movies, ILogger<Program> log, CancellationToken cancellationToken) =>
        {
            if (id != req.Id)
            {
                log.LogWarning("Update mismatch: route id {RouteId} != body id {BodyId}", id, req.Id);
                return Results.Problem(
                    statusCode: StatusCodes.Status400BadRequest,
                    title: "Movie id mismatch",
                    detail: "The route id and body id do not match.");
            }
            var success = await movies.UpdateAsync(req, cancellationToken);
            if (!success)
            {
                log.LogWarning("Movie {MovieId} not found for update", req.Id);
                return Results.Problem(
                    statusCode: StatusCodes.Status404NotFound,
                    title: "Movie not found",
                    detail: $"Movie {req.Id} was not found.");
            }
            log.LogInformation("Updated movie {MovieId}", req.Id);
            return Results.NoContent();
        })
        .AddEndpointFilter(new DataAnnotationsValidateFilter<UpdateMovieRequest>());

        group.MapDelete("/{id:int}", async ([AsParameters] DeleteMovieRequest req, IMoviesApi movies, ILogger<Program> log, CancellationToken cancellationToken) =>
        {
            var success = await movies.DeleteAsync(req, cancellationToken);
            if (!success)
            {
                log.LogWarning("Movie {MovieId} not found for delete", req.Id);
                return Results.Problem(
                    statusCode: StatusCodes.Status404NotFound,
                    title: "Movie not found",
                    detail: $"Movie {req.Id} was not found.");
            }
            log.LogInformation("Deleted movie {MovieId}", req.Id);
            return Results.NoContent();
        });

        return routes;
    }
}
