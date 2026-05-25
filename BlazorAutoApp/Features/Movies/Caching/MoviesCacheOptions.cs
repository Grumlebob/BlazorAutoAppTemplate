namespace BlazorAutoApp.Features.Movies.Caching;

/// Cache settings for movie list and item lookups.
public class MoviesCacheOptions
{
    /// Minutes to cache the movie list.
    public int ListTtlMinutes { get; set; } = 5;

    /// Minutes to cache a single movie.
    public int ItemTtlMinutes { get; set; } = 10;

    /// Seconds to cache the movie list in each app server's local in-process cache.
    public int LocalListTtlSeconds { get; set; } = 5;

    /// Seconds to cache a single movie in each app server's local in-process cache.
    public int LocalItemTtlSeconds { get; set; } = 10;

    /// Disables local in-process caching for movie reads when strict cross-node freshness is required.
    public bool DisableLocalCache { get; set; }
}
