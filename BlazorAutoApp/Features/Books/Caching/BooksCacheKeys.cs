using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

namespace BlazorAutoApp.Features.Books.Caching;

public static class BooksCacheKeys
{
    public const string Scope = "books";
    public const string List = "books:list";
    public const string AllTag = "books";
    public const string ListTag = "books:list";

    public static string Item(int id) => $"books:item:{id}";

    public static string ItemTag(int id) => $"books:item:{id}";

    internal static CacheInvalidationRequest ForChangedBook(int id) =>
        new(Scope, [List, Item(id)], [ListTag, ItemTag(id)]);
}
