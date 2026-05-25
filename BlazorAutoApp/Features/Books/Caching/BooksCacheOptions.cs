namespace BlazorAutoApp.Features.Books.Caching;

/// Cache settings for book list and item lookups.
public class BooksCacheOptions
{
    /// Minutes to cache the book list.
    public int ListTtlMinutes { get; set; } = 5;

    /// Minutes to cache a single book.
    public int ItemTtlMinutes { get; set; } = 10;

    /// Seconds to cache the book list in each app server's local in-process cache.
    public int LocalListTtlSeconds { get; set; } = 5;

    /// Seconds to cache a single book in each app server's local in-process cache.
    public int LocalItemTtlSeconds { get; set; } = 10;

    /// Disables local in-process caching for book reads when strict cross-node freshness is required.
    public bool DisableLocalCache { get; set; }
}
