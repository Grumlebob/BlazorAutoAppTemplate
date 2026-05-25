using BlazorAutoApp.Core.Features.Books.Domain;

namespace BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;

public class GetBooksResponse
{
    public required List<Book> Books { get; init; }
}
