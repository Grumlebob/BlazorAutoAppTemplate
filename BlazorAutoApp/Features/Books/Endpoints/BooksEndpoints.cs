using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.DeleteBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
using BlazorAutoApp.Features.Books;
using BlazorAutoApp.Infrastructure.Hosting;
using Microsoft.AspNetCore.Http.HttpResults;

namespace BlazorAutoApp.Features.Books.Endpoints;

public static class BookEndpoints
{
    public static IEndpointRouteBuilder MapBookEndpoints(this IEndpointRouteBuilder routes)
    {
        var group = routes.MapGroup("/api/books")
            .WithTags("Books")
            .RequireRateLimiting(AppRateLimiting.ApiPolicyName);

        group.MapGet("/", ListBooksAsync)
            .WithName("ListBooks")
            .RequireAuthorization();

        group.MapGet("/{id:int}", GetBookAsync)
            .WithName("GetBook")
            .ProducesProblem(StatusCodes.Status404NotFound)
            .RequireAuthorization();

        group.MapPost("/", CreateBookAsync)
            .WithName("CreateBook")
            .ProducesValidationProblem()
            .RequireAuthorization();

        group.MapPut("/{id:int}", UpdateBookAsync)
            .WithName("UpdateBook")
            .ProducesValidationProblem()
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .RequireAuthorization();

        group.MapDelete("/{id:int}", DeleteBookAsync)
            .WithName("DeleteBook")
            .ProducesProblem(StatusCodes.Status404NotFound)
            .RequireAuthorization();

        return routes;
    }

    private static async Task<Ok<GetBooksResponse>> ListBooksAsync(
        IBooksApi books,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        const string operation = "list";
        using var activity = BooksTelemetry.StartActivity(operation);
        var startTimestamp = BooksTelemetry.GetTimestamp();

        try
        {
            log.LogDebug("Listing books");
            var result = await books.GetAsync(cancellationToken);
            BooksTelemetry.Record(operation, "success", startTimestamp);
            return TypedResults.Ok(result);
        }
        catch (Exception ex)
        {
            BooksTelemetry.RecordException(operation, startTimestamp, ex);
            throw;
        }
    }

    private static async Task<Results<Ok<GetBookResponse>, ProblemHttpResult>> GetBookAsync(
        [AsParameters] GetBookRequest req,
        IBooksApi books,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        const string operation = "get";
        using var activity = BooksTelemetry.StartActivity(operation);
        var startTimestamp = BooksTelemetry.GetTimestamp();

        try
        {
            var result = await books.GetByIdAsync(req, cancellationToken);
            if (result is null)
            {
                log.LogWarning("Book {BookId} not found", req.Id);
                BooksTelemetry.Record(operation, "not_found", startTimestamp);
                return BookNotFound(req.Id);
            }

            log.LogInformation("Fetched book {BookId}", req.Id);
            BooksTelemetry.Record(operation, "success", startTimestamp);
            return TypedResults.Ok(result);
        }
        catch (Exception ex)
        {
            BooksTelemetry.RecordException(operation, startTimestamp, ex);
            throw;
        }
    }

    private static async Task<Created<CreateBookResponse>> CreateBookAsync(
        IBooksApi books,
        CreateBookRequest dto,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        const string operation = "create";
        using var activity = BooksTelemetry.StartActivity(operation);
        var startTimestamp = BooksTelemetry.GetTimestamp();

        try
        {
            var response = await books.CreateAsync(dto, cancellationToken);
            log.LogInformation("Created book {BookId}", response.Id);
            BooksTelemetry.Record(operation, "success", startTimestamp);
            return TypedResults.Created($"/api/books/{response.Id}", response);
        }
        catch (Exception ex)
        {
            BooksTelemetry.RecordException(operation, startTimestamp, ex);
            throw;
        }
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> UpdateBookAsync(
        int id,
        UpdateBookRequest req,
        IBooksApi books,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        const string operation = "update";
        using var activity = BooksTelemetry.StartActivity(operation);
        var startTimestamp = BooksTelemetry.GetTimestamp();

        if (id != req.Id)
        {
            log.LogWarning("Update mismatch: route id {RouteId} != body id {BodyId}", id, req.Id);
            BooksTelemetry.Record(operation, "bad_request", startTimestamp);
            return TypedResults.Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Book id mismatch",
                detail: "The route id and body id do not match.");
        }

        try
        {
            var success = await books.UpdateAsync(req, cancellationToken);
            if (!success)
            {
                log.LogWarning("Book {BookId} not found for update", req.Id);
                BooksTelemetry.Record(operation, "not_found", startTimestamp);
                return BookNotFound(req.Id);
            }

            log.LogInformation("Updated book {BookId}", req.Id);
            BooksTelemetry.Record(operation, "success", startTimestamp);
            return TypedResults.NoContent();
        }
        catch (Exception ex)
        {
            BooksTelemetry.RecordException(operation, startTimestamp, ex);
            throw;
        }
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> DeleteBookAsync(
        [AsParameters] DeleteBookRequest req,
        IBooksApi books,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        const string operation = "delete";
        using var activity = BooksTelemetry.StartActivity(operation);
        var startTimestamp = BooksTelemetry.GetTimestamp();

        try
        {
            var success = await books.DeleteAsync(req, cancellationToken);
            if (!success)
            {
                log.LogWarning("Book {BookId} not found for delete", req.Id);
                BooksTelemetry.Record(operation, "not_found", startTimestamp);
                return BookNotFound(req.Id);
            }

            log.LogInformation("Deleted book {BookId}", req.Id);
            BooksTelemetry.Record(operation, "success", startTimestamp);
            return TypedResults.NoContent();
        }
        catch (Exception ex)
        {
            BooksTelemetry.RecordException(operation, startTimestamp, ex);
            throw;
        }
    }

    private static ProblemHttpResult BookNotFound(int id) =>
        TypedResults.Problem(
            statusCode: StatusCodes.Status404NotFound,
            title: "Book not found",
            detail: $"Book {id} was not found.");
}

internal sealed class BooksEndpointLogCategory;
