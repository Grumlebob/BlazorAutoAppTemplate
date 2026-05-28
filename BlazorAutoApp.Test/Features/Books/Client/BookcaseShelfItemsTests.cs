using BlazorAutoApp.Client.Features.Books.Shared;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Client;

public sealed class BookcaseShelfItemsTests
{
    [Fact]
    public void Build_LimitedShelf_CapsBooksWithoutRepeating()
    {
        var books = BuildBooks(25);

        var items = BookcaseShelfItems.Build(
            books,
            limitItems: true,
            maxItems: 18);

        Assert.Equal(18, items.Count);
        Assert.Equal(Enumerable.Range(1, 18), items.Select(book => book.Id));
    }

    [Fact]
    public void Build_LimitedShelf_DoesNotPadSmallBooksets()
    {
        var books = BuildBooks(5);

        var items = BookcaseShelfItems.Build(
            books,
            limitItems: true,
            maxItems: 18);

        Assert.Equal(5, items.Count);
        Assert.Equal(Enumerable.Range(1, 5), items.Select(book => book.Id));
    }

    [Fact]
    public void Build_UnlimitedShelf_DoesNotCapOrRepeat()
    {
        var books = BuildBooks(25);

        var items = BookcaseShelfItems.Build(
            books,
            limitItems: false,
            maxItems: 5);

        Assert.Equal(25, items.Count);
        Assert.Equal(Enumerable.Range(1, 25), items.Select(book => book.Id));
    }

    [Fact]
    public void Build_NormalizesInvalidBounds()
    {
        var books = BuildBooks(3);

        var items = BookcaseShelfItems.Build(
            books,
            limitItems: true,
            maxItems: 0);

        Assert.Single(items);
        Assert.Equal(1, items[0].Id);
    }

    private static IReadOnlyList<BookcaseBook> BuildBooks(int count) =>
        Enumerable
            .Range(1, count)
            .Select(id => new BookcaseBook(id, $"Book {id.ToString(System.Globalization.CultureInfo.InvariantCulture)}", null))
            .ToList();
}
