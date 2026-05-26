using BlazorAutoApp.Client.Features.Books.Shared;

namespace BlazorAutoApp.Client.Features.Books.AuthorBookcase;

internal static class AuthorBookcaseCatalog
{
    public static readonly IReadOnlyList<AuthorBookPage> Pages =
    [
        new(1, "ship", "Ship", "Template Author", null),
        new(2, "traceback", "TraceBack", "Template Author", null),
        new(3, "improveddb", "ImprovedDb", "Template Author", null),
        new(4, "kinojoin", "KinoJoin", "Template Author", null),
        new(5, "pride-and-prejudice", "Pride and Prejudice", "Jane Austen", "https://www.gutenberg.org/ebooks/1342"),
        new(6, "nineteen-eighty-four", "1984", "George Orwell", null),
        new(7, "the-hobbit", "The Hobbit", "J. R. R. Tolkien", null),
        new(8, "to-kill-a-mockingbird", "To Kill a Mockingbird", "Harper Lee", null),
        new(9, "the-great-gatsby", "The Great Gatsby", "F. Scott Fitzgerald", "https://www.gutenberg.org/ebooks/64317"),
        new(10, "moby-dick", "Moby-Dick", "Herman Melville", "https://www.gutenberg.org/ebooks/2701"),
        new(11, "jane-eyre", "Jane Eyre", "Charlotte Bronte", "https://www.gutenberg.org/ebooks/1260"),
        new(12, "frankenstein", "Frankenstein", "Mary Shelley", "https://www.gutenberg.org/ebooks/84"),
        new(13, "the-odyssey", "The Odyssey", "Homer", "https://www.gutenberg.org/ebooks/1727"),
        new(14, "don-quixote", "Don Quixote", "Miguel de Cervantes", "https://www.gutenberg.org/ebooks/996")
    ];

    public static readonly IReadOnlyList<BookcaseBook> Books = Pages
        .Select(page => new BookcaseBook(page.Id, page.Title, page.Url, $"/books?authorBookId={page.Id.ToString(System.Globalization.CultureInfo.InvariantCulture)}&bookMode=view"))
        .ToList();

    public static AuthorBookPage? FindById(int id) =>
        Pages.FirstOrDefault(page => page.Id == id);

    public static AuthorBookPage? FindBySlug(string? slug)
    {
        if (string.IsNullOrWhiteSpace(slug))
        {
            return null;
        }

        return Pages.FirstOrDefault(page => string.Equals(page.Slug, slug, StringComparison.OrdinalIgnoreCase));
    }
}
