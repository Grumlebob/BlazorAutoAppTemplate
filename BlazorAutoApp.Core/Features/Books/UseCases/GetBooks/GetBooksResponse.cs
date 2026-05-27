namespace BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;

public class GetBooksResponse
{
    public required List<BookListItemResponse> Books { get; init; }
}
