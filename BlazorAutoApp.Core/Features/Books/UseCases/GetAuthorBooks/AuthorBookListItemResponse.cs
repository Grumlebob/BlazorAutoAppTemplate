namespace BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;

public class AuthorBookListItemResponse
{
    public int Id { get; init; }

    public required string Title { get; init; }

    public string? Author { get; init; }

    public string? Url { get; init; }
}
