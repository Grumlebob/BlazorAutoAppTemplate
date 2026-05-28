using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

namespace BlazorAutoApp.Features.Books.Caching;

public static class AuthorBooksCacheKeys
{
    public const string Scope = "author-books";
    public const string AllTag = "author-books";
    public const string ListKey = "author-books:list";
    public const string ListTag = "author-books:list";

    public static string Item(int id) => $"author-books:item:{id}";

    public static string ItemTag(int id) => $"author-books:item:{id}";

    internal static CacheInvalidationRequest ForChangedAuthorBooks() =>
        new(Scope, [ListKey], [AllTag, ListTag]);
}
