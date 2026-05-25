using BlazorAutoApp.Core.Features.Movies.Contracts;
using BlazorAutoApp.Core.Features.Movies.UseCases.CreateMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.DeleteMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovie;
using BlazorAutoApp.Core.Features.Movies.UseCases.GetMovies;
using BlazorAutoApp.Core.Features.Movies.UseCases.UpdateMovie;
using BlazorAutoApp.Infrastructure.Hosting;
using Microsoft.AspNetCore.Http.HttpResults;

namespace BlazorAutoApp.Features.Movies.Endpoints;

public static class MovieEndpoints
{
    public static IEndpointRouteBuilder MapMovieEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/movies")
            .WithTags("Movies")
            .RequireRateLimiting(AppRateLimiting.ApiPolicyName);

        group.MapGet("/", ListMoviesAsync)
            .WithName("ListMovies");

        group.MapGet("/{id:int}", GetMovieAsync)
            .WithName("GetMovie")
            .ProducesProblem(StatusCodes.Status404NotFound);

        group.MapPost("/", CreateMovieAsync)
            .WithName("CreateMovie")
            .ProducesValidationProblem();

        group.MapPut("/{id:int}", UpdateMovieAsync)
            .WithName("UpdateMovie")
            .ProducesValidationProblem()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound);

        group.MapDelete("/{id:int}", DeleteMovieAsync)
            .WithName("DeleteMovie")
            .ProducesProblem(StatusCodes.Status404NotFound);

        return routes;
    }

    private static async Task<Ok<GetMoviesResponse>> ListMoviesAsync(
        [AsParameters] GetMoviesRequest req,
        IMoviesApi movies,
        ILogger<Program> log,
        CancellationToken cancellationToken)
    {
        log.LogDebug("Listing movies");
        var result = await movies.GetAsync(req, cancellationToken);
        return TypedResults.Ok(result);
    }

    private static async Task<Results<Ok<GetMovieResponse>, ProblemHttpResult>> GetMovieAsync(
        [AsParameters] GetMovieRequest req,
        IMoviesApi movies,
        ILogger<Program> log,
        CancellationToken cancellationToken)
    {
        var result = await movies.GetByIdAsync(req, cancellationToken);
        if (result is null)
        {
            log.LogWarning("Movie {MovieId} not found", req.Id);
            return MovieNotFound(req.Id);
        }

        log.LogInformation("Fetched movie {MovieId}", req.Id);
        return TypedResults.Ok(result);
    }

    private static async Task<Created<CreateMovieResponse>> CreateMovieAsync(
        IMoviesApi movies,
        CreateMovieRequest dto,
        ILogger<Program> log,
        CancellationToken cancellationToken)
    {
        var response = await movies.CreateAsync(dto, cancellationToken);
        log.LogInformation("Created movie {MovieId} - {Title}", response.Id, response.Title);
        return TypedResults.Created($"/api/movies/{response.Id}", response);
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> UpdateMovieAsync(
        int id,
        UpdateMovieRequest req,
        IMoviesApi movies,
        ILogger<Program> log,
        CancellationToken cancellationToken)
    {
        if (id != req.Id)
        {
            log.LogWarning("Update mismatch: route id {RouteId} != body id {BodyId}", id, req.Id);
            return TypedResults.Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Movie id mismatch",
                detail: "The route id and body id do not match.");
        }

        var success = await movies.UpdateAsync(req, cancellationToken);
        if (!success)
        {
            log.LogWarning("Movie {MovieId} not found for update", req.Id);
            return MovieNotFound(req.Id);
        }

        log.LogInformation("Updated movie {MovieId}", req.Id);
        return TypedResults.NoContent();
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> DeleteMovieAsync(
        [AsParameters] DeleteMovieRequest req,
        IMoviesApi movies,
        ILogger<Program> log,
        CancellationToken cancellationToken)
    {
        var success = await movies.DeleteAsync(req, cancellationToken);
        if (!success)
        {
            log.LogWarning("Movie {MovieId} not found for delete", req.Id);
            return MovieNotFound(req.Id);
        }

        log.LogInformation("Deleted movie {MovieId}", req.Id);
        return TypedResults.NoContent();
    }

    private static ProblemHttpResult MovieNotFound(int id) =>
        TypedResults.Problem(
            statusCode: StatusCodes.Status404NotFound,
            title: "Movie not found",
            detail: $"Movie {id} was not found.");
}
