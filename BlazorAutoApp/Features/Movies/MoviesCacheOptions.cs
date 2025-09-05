namespace BlazorAutoApp.Features.Movies;

/// Cache settings for movie list and item lookups.
public class MoviesCacheOptions
{
    /// Minutes to cache the movie list.
    public int ListTtlMinutes { get; set; } = 5;

    /// Minutes to cache a single movie.
    public int ItemTtlMinutes { get; set; } = 10;
}
