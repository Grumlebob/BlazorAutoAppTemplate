using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

namespace BlazorAutoApp.Features.Movies.Caching;

public static class MoviesCacheKeys
{
    public const string Scope = "movies";
    public const string List = "movies:list";
    public const string AllTag = "movies";
    public const string ListTag = "movies:list";

    public static string Item(int id) => $"movies:item:{id}";

    public static string ItemTag(int id) => $"movies:item:{id}";

    internal static CacheInvalidationRequest ForChangedMovie(int id) =>
        new(Scope, [List, Item(id)], [ListTag, ItemTag(id)]);
}
