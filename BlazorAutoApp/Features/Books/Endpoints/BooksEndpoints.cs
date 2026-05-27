using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.DeleteBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
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
        log.LogDebug("Listing books");
        var result = await books.GetAsync(cancellationToken);
        return TypedResults.Ok(result);
    }

    private static async Task<Results<Ok<GetBookResponse>, ProblemHttpResult>> GetBookAsync(
        [AsParameters] GetBookRequest req,
        IBooksApi books,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        var result = await books.GetByIdAsync(req, cancellationToken);
        if (result is null)
        {
            log.LogWarning("Book {BookId} not found", req.Id);
            return BookNotFound(req.Id);
        }

        log.LogInformation("Fetched book {BookId}", req.Id);
        return TypedResults.Ok(result);
    }

    private static async Task<Created<CreateBookResponse>> CreateBookAsync(
        IBooksApi books,
        CreateBookRequest dto,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        var response = await books.CreateAsync(dto, cancellationToken);
        log.LogInformation("Created book {BookId} - {Title}", response.Id, response.Title);
        return TypedResults.Created($"/api/books/{response.Id}", response);
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> UpdateBookAsync(
        int id,
        UpdateBookRequest req,
        IBooksApi books,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        if (id != req.Id)
        {
            log.LogWarning("Update mismatch: route id {RouteId} != body id {BodyId}", id, req.Id);
            return TypedResults.Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Book id mismatch",
                detail: "The route id and body id do not match.");
        }

        var success = await books.UpdateAsync(req, cancellationToken);
        if (!success)
        {
            log.LogWarning("Book {BookId} not found for update", req.Id);
            return BookNotFound(req.Id);
        }

        log.LogInformation("Updated book {BookId}", req.Id);
        return TypedResults.NoContent();
    }

    private static async Task<Results<NoContent, ProblemHttpResult>> DeleteBookAsync(
        [AsParameters] DeleteBookRequest req,
        IBooksApi books,
        ILogger<BooksEndpointLogCategory> log,
        CancellationToken cancellationToken)
    {
        var success = await books.DeleteAsync(req, cancellationToken);
        if (!success)
        {
            log.LogWarning("Book {BookId} not found for delete", req.Id);
            return BookNotFound(req.Id);
        }

        log.LogInformation("Deleted book {BookId}", req.Id);
        return TypedResults.NoContent();
    }

    private static ProblemHttpResult BookNotFound(int id) =>
        TypedResults.Problem(
            statusCode: StatusCodes.Status404NotFound,
            title: "Book not found",
            detail: $"Book {id} was not found.");
}

internal sealed class BooksEndpointLogCategory;
