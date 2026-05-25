namespace BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;

public class CreateBookResponse
{
    public int Id { get; init; }
    public required string Title { get; init; }
    public string? Author { get; init; }
    public string? Url { get; init; }
}
