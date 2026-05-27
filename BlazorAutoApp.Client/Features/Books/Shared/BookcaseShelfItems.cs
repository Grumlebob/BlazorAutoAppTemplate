namespace BlazorAutoApp.Client.Features.Books.Shared;

public static class BookcaseShelfItems
{
    public const int DefaultAutoScrollMinItems = 12;
    public const int DefaultAutoScrollMaxUniqueItems = 18;

    public static IReadOnlyList<BookcaseBook> Build(
        IReadOnlyList<BookcaseBook> books,
        bool autoScroll,
        int autoScrollMinItems,
        int autoScrollMaxUniqueItems)
    {
        if (books.Count == 0)
        {
            return [];
        }

        var minItems = NormalizeItemCount(autoScrollMinItems);
        var maxUniqueItems = NormalizeItemCount(autoScrollMaxUniqueItems);
        var items = autoScroll
            ? books.Take(maxUniqueItems).ToList()
            : books.ToList();

        if (!autoScroll)
        {
            return items;
        }

        var repeatSourceCount = items.Count;
        for (var i = 0; items.Count < minItems; i++)
        {
            items.Add(items[i % repeatSourceCount]);
        }

        return items;
    }

    public static int NormalizeItemCount(int value) => Math.Max(1, value);

    public static int GetVisibleItemCount(int bookCount, bool autoScroll, int autoScrollMaxUniqueItems)
    {
        if (bookCount <= 0)
        {
            return 0;
        }

        return autoScroll
            ? Math.Min(bookCount, NormalizeItemCount(autoScrollMaxUniqueItems))
            : bookCount;
    }
}
