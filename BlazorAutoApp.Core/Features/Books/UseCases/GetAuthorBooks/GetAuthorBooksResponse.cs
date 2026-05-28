namespace BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;

public class GetAuthorBooksResponse
{
    public required List<AuthorBookListItemResponse> Books { get; init; }
}
