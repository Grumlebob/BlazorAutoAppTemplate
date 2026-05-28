using BlazorAutoApp.Client.Features.Books.Shared;

namespace BlazorAutoApp.Client.Features.Books.AuthorBookcase;

internal static class AuthorBookcaseCatalog
{
    public static readonly IReadOnlyList<AuthorBookPage> Pages =
    [
        new(1, "the-great-gatsby", "The Great Gatsby", "F. Scott Fitzgerald", "https://www.gutenberg.org/ebooks/64317"),
        new(2, "Ship", "Ship Maintaince", "Template Author", null),
        new(3, "traceback", "TraceBack", "Template Author", null),
        new(4, "improveddb", "ImprovedDb", "Template Author", null),
        new(5, "kinojoin", "KinoJoin", "Template Author", null)
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
