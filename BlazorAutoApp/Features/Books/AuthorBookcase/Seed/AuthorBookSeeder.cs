using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Features.Books.Caching;
using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;

namespace BlazorAutoApp.Features.Books.AuthorBookcase.Seed;

internal interface IAuthorBookSeeder
{
    Task SeedAsync(CancellationToken cancellationToken = default);
}

internal sealed class AuthorBookSeeder(
    IDbContextFactory<AppDbContext> dbFactory,
    ICacheInvalidator cacheInvalidator,
    ILogger<AuthorBookSeeder> logger) : IAuthorBookSeeder
{
    private const string AdvisoryLockSql = "SELECT pg_advisory_xact_lock(26052801)";

    private static readonly AuthorBookSeedItem[] SeedItems =
    [
        new("traceback", "TraceBack", "Jacob Grum", null),
        new("ship", "Ship Inspections", "Jacob Grum", null),
        new("traceback", "TraceBack", "Jacob Grum", null),
        new("improveddb", "ImprovedDb", "Jacob Grum", null),
        new("kinojoin", "KinoJoin", "Jacob Grum", null),
        new("unlost", "Unlost", "Jacob Grum", null),
        new("geckobot", "GeckoBot", "Jacob Grum", null),
        new("geckobot", "Grumlebob", "Jacob Grum", null),
    ];

    private readonly IDbContextFactory<AppDbContext> _dbFactory = dbFactory;
    private readonly ICacheInvalidator _cacheInvalidator = cacheInvalidator;
    private readonly ILogger<AuthorBookSeeder> _logger = logger;

    public async Task SeedAsync(CancellationToken cancellationToken = default)
    {
        await using var strategyContext = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var strategy = strategyContext.Database.CreateExecutionStrategy();

        var changed = await strategy.ExecuteAsync(async () =>
        {
            await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            // Startup can run on multiple app nodes. The advisory lock keeps the idempotent seed atomic in PostgreSQL.
            await db.Database.ExecuteSqlRawAsync(
                AdvisoryLockSql,
                cancellationToken);

            var existing = await db.AuthorBooks
                .Include(authorBook => authorBook.Book)
                .ToDictionaryAsync(authorBook => authorBook.SeedKey, StringComparer.Ordinal, cancellationToken);

            var hasChanges = false;
            var missingItems = new List<AuthorBookSeedItem>();
            foreach (var item in SeedItems)
            {
                if (existing.TryGetValue(item.SeedKey, out var authorBook))
                {
                    hasChanges |= ApplyBookValues(authorBook.Book, item);
                    continue;
                }

                missingItems.Add(item);
            }

            if (hasChanges)
            {
                await db.SaveChangesAsync(cancellationToken);
            }

            foreach (var item in missingItems)
            {
                var book = new Book
                {
                    Title = item.Title,
                    Author = item.Author,
                    Url = item.Url
                };

                db.Books.Add(book);
                await db.SaveChangesAsync(cancellationToken);

                db.AuthorBooks.Add(new AuthorBook
                {
                    SeedKey = item.SeedKey,
                    BookId = book.Id
                });
                await db.SaveChangesAsync(cancellationToken);

                hasChanges = true;
            }

            await transaction.CommitAsync(cancellationToken);
            return hasChanges;
        });

        if (!changed)
        {
            return;
        }

        try
        {
            await _cacheInvalidator.InvalidateAsync(
                AuthorBooksCacheKeys.ForChangedAuthorBooks(),
                CancellationToken.None);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to invalidate author books cache after seeding.");
        }
    }

    private static bool ApplyBookValues(Book book, AuthorBookSeedItem item)
    {
        var changed = false;
        if (!string.Equals(book.Title, item.Title, StringComparison.Ordinal))
        {
            book.Title = item.Title;
            changed = true;
        }

        if (!string.Equals(book.Author, item.Author, StringComparison.Ordinal))
        {
            book.Author = item.Author;
            changed = true;
        }

        if (!string.Equals(book.Url, item.Url, StringComparison.Ordinal))
        {
            book.Url = item.Url;
            changed = true;
        }

        return changed;
    }

    private sealed record AuthorBookSeedItem(string SeedKey, string Title, string? Author, string? Url);
}
