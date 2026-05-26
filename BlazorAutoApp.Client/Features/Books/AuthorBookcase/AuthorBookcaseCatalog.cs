using BlazorAutoApp.Client.Features.Books.Shared;

namespace BlazorAutoApp.Client.Features.Books.AuthorBookcase;

internal static class AuthorBookcaseCatalog
{
    public static readonly IReadOnlyList<BookcaseBook> Books =
    [
        new(-1, "Ship", null),
        new(-2, "TraceBack", null),
        new(-3, "ImprovedDb", null),
        new(-4, "KinoJoin", null),
        new(-5, "Pride and Prejudice", null),
        new(-6, "1984", null),
        new(-7, "The Hobbit", null),
        new(-8, "To Kill a Mockingbird", null),
        new(-9, "The Great Gatsby", null),
        new(-10, "Moby-Dick", null),
        new(-11, "Jane Eyre", null),
        new(-12, "Frankenstein", null),
        new(-13, "The Odyssey", null),
        new(-14, "Don Quixote", null)
    ];
}
