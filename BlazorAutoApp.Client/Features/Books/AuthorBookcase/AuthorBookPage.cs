namespace BlazorAutoApp.Client.Features.Books.AuthorBookcase;

internal sealed record AuthorBookPage(
    int Id,
    string Slug,
    string Title,
    string Author,
    string? Url);
