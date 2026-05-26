using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.Domain;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.DeleteBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
using BlazorAutoApp.Features.Books.Caching;
using BlazorAutoApp.Infrastructure.Hosting.CacheInvalidation;
using Microsoft.Extensions.Caching.Hybrid;
using Microsoft.Extensions.Options;

namespace BlazorAutoApp.Features.Books.Services;

internal class BooksServerService(
    IDbContextFactory<AppDbContext> dbFactory,
    HybridCache cache,
    ICacheInvalidator cacheInvalidator,
    IOptions<BooksCacheOptions> cacheOptions,
    ICurrentUserAccessor currentUser,
    ILogger<BooksServerService> logger) : IBooksApi
{
    private readonly IDbContextFactory<AppDbContext> _dbFactory = dbFactory;
    private readonly HybridCache _cache = cache;
    private readonly ICacheInvalidator _cacheInvalidator = cacheInvalidator;
    private readonly BooksCacheOptions _cacheOptions = cacheOptions.Value ?? new BooksCacheOptions();
    private readonly ICurrentUserAccessor _currentUser = currentUser;
    private readonly ILogger<BooksServerService> _logger = logger;

    public async Task<GetBooksResponse> GetAsync(GetBooksRequest req, CancellationToken cancellationToken = default)
    {
        var userId = _currentUser.GetRequiredUserId();
        var key = BooksCacheKeys.List(userId);
        var result = await _cache.GetOrCreateAsync(key,
            ct => new ValueTask<GetBooksResponse>(LoadBooksAsync(userId, ct)),
            CreateEntryOptions(_cacheOptions.ListTtlMinutes, _cacheOptions.LocalListTtlSeconds),
            tags: [BooksCacheKeys.AllTag, BooksCacheKeys.ListTag(userId)],
            cancellationToken: cancellationToken);
        return result!;
    }

    public async Task<GetBookResponse?> GetByIdAsync(GetBookRequest req, CancellationToken cancellationToken = default)
    {
        var userId = _currentUser.GetRequiredUserId();
        var key = BooksCacheKeys.Item(userId, req.Id);
        var result = await _cache.GetOrCreateAsync(key,
            ct => new ValueTask<GetBookResponse?>(LoadBookAsync(userId, req.Id, ct)),
            CreateEntryOptions(_cacheOptions.ItemTtlMinutes, _cacheOptions.LocalItemTtlSeconds),
            tags: [BooksCacheKeys.AllTag, BooksCacheKeys.ItemTag(userId, req.Id)],
            cancellationToken: cancellationToken);
        return result;
    }

    private async Task<GetBooksResponse> LoadBooksAsync(string userId, CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var items = await db.Books
            .AsNoTracking()
            .Where(book => book.OwnerUserId == userId)
            .OrderBy(book => book.Id)
            .ToListAsync(ct);
        return new GetBooksResponse { Books = items };
    }

    private async Task<GetBookResponse?> LoadBookAsync(string userId, int id, CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var book = await db.Books
            .AsNoTracking()
            .FirstOrDefaultAsync(m => m.Id == id && m.OwnerUserId == userId, ct);
        if (book is null) return null;
        return new GetBookResponse
        {
            Id = book.Id,
            Title = book.Title,
            Author = book.Author,
            Url = book.Url
        };
    }

    public async Task<CreateBookResponse> CreateAsync(CreateBookRequest req, CancellationToken cancellationToken = default)
    {
        var userId = _currentUser.GetRequiredUserId();
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var book = new Book
        {
            Title = req.Title,
            Author = req.Author,
            Url = NormalizeUrl(req.Url),
            OwnerUserId = userId
        };
        db.Books.Add(book);
        await db.SaveChangesAsync(cancellationToken);
        await InvalidateAsync(userId, book.Id);
        return new CreateBookResponse
        {
            Id = book.Id,
            Title = book.Title,
            Author = book.Author,
            Url = book.Url
        };
    }

    public async Task<bool> UpdateAsync(UpdateBookRequest req, CancellationToken cancellationToken = default)
    {
        var userId = _currentUser.GetRequiredUserId();
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var book = await db.Books.FirstOrDefaultAsync(
            m => m.Id == req.Id && m.OwnerUserId == userId,
            cancellationToken);
        if (book is null) return false;
        book.Title = req.Title;
        book.Author = req.Author;
        book.Url = NormalizeUrl(req.Url);
        await db.SaveChangesAsync(cancellationToken);
        await InvalidateAsync(userId, req.Id);
        return true;
    }

    public async Task<bool> DeleteAsync(DeleteBookRequest req, CancellationToken cancellationToken = default)
    {
        var userId = _currentUser.GetRequiredUserId();
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var book = await db.Books.FirstOrDefaultAsync(
            m => m.Id == req.Id && m.OwnerUserId == userId,
            cancellationToken);
        if (book is null) return false;
        db.Books.Remove(book);
        await db.SaveChangesAsync(cancellationToken);
        await InvalidateAsync(userId, req.Id);
        return true;
    }

    private async Task InvalidateAsync(string userId, int id)
    {
        try
        {
            await _cacheInvalidator.InvalidateAsync(BooksCacheKeys.ForChangedBook(userId, id), CancellationToken.None);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to invalidate Books cache for book {BookId}", id);
        }
    }

    private static string? NormalizeUrl(string? url) =>
        string.IsNullOrWhiteSpace(url) ? null : url.Trim();

    private HybridCacheEntryOptions CreateEntryOptions(int distributedTtlMinutes, int localTtlSeconds)
    {
        var flags = _cacheOptions.DisableLocalCache
            ? HybridCacheEntryFlags.DisableLocalCache
            : HybridCacheEntryFlags.None;

        return new HybridCacheEntryOptions
        {
            Expiration = TimeSpan.FromMinutes(Math.Max(1, distributedTtlMinutes)),
            LocalCacheExpiration = TimeSpan.FromSeconds(Math.Max(1, localTtlSeconds)),
            Flags = flags
        };
    }
}
