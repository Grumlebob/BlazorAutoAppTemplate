using BlazorAutoApp.Client.Features.Books.Shared;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Client;

public sealed class BookcaseShelfItemsTests
{
    [Fact]
    public void Build_AutoScroll_CapsUniqueBooksBeforeRendering()
    {
        var books = BuildBooks(25);

        var items = BookcaseShelfItems.Build(
            books,
            autoScroll: true,
            autoScrollMinItems: 12,
            autoScrollMaxUniqueItems: 18);

        Assert.Equal(18, items.Count);
        Assert.Equal(Enumerable.Range(1, 18), items.Select(book => book.Id));
    }

    [Fact]
    public void Build_AutoScroll_RepeatsOnlyTheCappedDisplaySet()
    {
        var books = BuildBooks(25);

        var items = BookcaseShelfItems.Build(
            books,
            autoScroll: true,
            autoScrollMinItems: 12,
            autoScrollMaxUniqueItems: 5);

        Assert.Equal(12, items.Count);
        Assert.Equal(new[] { 1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2 }, items.Select(book => book.Id));
    }

    [Fact]
    public void Build_NonAutoScroll_DoesNotCapOrRepeat()
    {
        var books = BuildBooks(25);

        var items = BookcaseShelfItems.Build(
            books,
            autoScroll: false,
            autoScrollMinItems: 12,
            autoScrollMaxUniqueItems: 5);

        Assert.Equal(25, items.Count);
        Assert.Equal(Enumerable.Range(1, 25), items.Select(book => book.Id));
    }

    [Fact]
    public void Build_NormalizesInvalidBounds()
    {
        var books = BuildBooks(3);

        var items = BookcaseShelfItems.Build(
            books,
            autoScroll: true,
            autoScrollMinItems: 0,
            autoScrollMaxUniqueItems: 0);

        Assert.Single(items);
        Assert.Equal(1, items[0].Id);
    }

    [Fact]
    public void GetVisibleItemCount_MatchesCappedAutoScrollSource()
    {
        Assert.Equal(5, BookcaseShelfItems.GetVisibleItemCount(25, autoScroll: true, autoScrollMaxUniqueItems: 5));
        Assert.Equal(3, BookcaseShelfItems.GetVisibleItemCount(3, autoScroll: true, autoScrollMaxUniqueItems: 5));
        Assert.Equal(25, BookcaseShelfItems.GetVisibleItemCount(25, autoScroll: false, autoScrollMaxUniqueItems: 5));
        Assert.Equal(0, BookcaseShelfItems.GetVisibleItemCount(0, autoScroll: true, autoScrollMaxUniqueItems: 5));
    }

    private static IReadOnlyList<BookcaseBook> BuildBooks(int count) =>
        Enumerable
            .Range(1, count)
            .Select(id => new BookcaseBook(id, $"Book {id.ToString(System.Globalization.CultureInfo.InvariantCulture)}", null))
            .ToList();
}
