namespace BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBook;

public class GetAuthorBookResponse
{
    public int Id { get; init; }

    public required string SeedKey { get; init; }

    public required string Title { get; init; }

    public string? Author { get; init; }

    public string? Url { get; init; }
}
