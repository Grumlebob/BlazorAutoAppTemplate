namespace BlazorAutoApp.Features.Movies.Caching;

public static class MoviesCacheKeys
{
    public const string List = "movies:list";
    public const string Tag = "movies";

    public static string Item(int id) => $"movies:item:{id}";
}
