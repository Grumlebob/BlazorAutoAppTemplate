using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

namespace BlazorAutoApp.Features.Books.Caching;

public static class BooksCacheKeys
{
    public const string Scope = "books";
    public const string AllTag = "books";

    public static string List(string userId) => $"books:user:{userId}:list";

    public static string ListTag(string userId) => $"books:user:{userId}:list";

    public static string Item(string userId, int id) => $"books:user:{userId}:item:{id}";

    public static string ItemTag(string userId, int id) => $"books:user:{userId}:item:{id}";

    internal static CacheInvalidationRequest ForChangedBook(string userId, int id) =>
        new(Scope, [List(userId), Item(userId, id)], [ListTag(userId), ItemTag(userId, id)]);
}
