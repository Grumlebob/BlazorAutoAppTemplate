namespace BlazorAutoApp.Client.Features.Books.Shared;

public static class BookcaseShelfItems
{
    public const int DefaultMaxItems = 18;

    public static IReadOnlyList<BookcaseBook> Build(
        IReadOnlyList<BookcaseBook> books,
        bool limitItems,
        int maxItems)
    {
        if (books.Count == 0)
        {
            return [];
        }

        return limitItems
            ? books.Take(NormalizeItemCount(maxItems)).ToList()
            : books.ToList();
    }

    public static int NormalizeItemCount(int value) => Math.Max(1, value);
}
