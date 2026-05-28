using BlazorAutoApp.Core.Features.Books.Contracts;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBook;
using BlazorAutoApp.Core.Features.Books.UseCases.GetAuthorBooks;
using BlazorAutoApp.Features.Books.Caching;
using Microsoft.Extensions.Caching.Hybrid;

namespace BlazorAutoApp.Features.Books.Services;

internal class AuthorBooksServerService(
    IDbContextFactory<AppDbContext> dbFactory,
    HybridCache cache) : IAuthorBooksApi
{
    private readonly IDbContextFactory<AppDbContext> _dbFactory = dbFactory;
    private readonly HybridCache _cache = cache;

    public async Task<GetAuthorBooksResponse> GetAsync(CancellationToken cancellationToken = default)
    {
        var result = await _cache.GetOrCreateAsync(
            AuthorBooksCacheKeys.ListKey,
            ct => new ValueTask<GetAuthorBooksResponse>(LoadBooksAsync(ct)),
            new HybridCacheEntryOptions
            {
                Expiration = TimeSpan.FromMinutes(60),
                LocalCacheExpiration = TimeSpan.FromMinutes(10)
            },
            tags: [AuthorBooksCacheKeys.AllTag, AuthorBooksCacheKeys.ListTag],
            cancellationToken: cancellationToken);

        return result!;
    }

    public async Task<GetAuthorBookResponse?> GetByIdAsync(GetAuthorBookRequest req, CancellationToken cancellationToken = default)
    {
        var result = await _cache.GetOrCreateAsync(
            AuthorBooksCacheKeys.Item(req.Id),
            ct => new ValueTask<GetAuthorBookResponse?>(LoadBookAsync(req.Id, ct)),
            new HybridCacheEntryOptions
            {
                Expiration = TimeSpan.FromMinutes(60),
                LocalCacheExpiration = TimeSpan.FromMinutes(10)
            },
            tags: [AuthorBooksCacheKeys.AllTag, AuthorBooksCacheKeys.ItemTag(req.Id)],
            cancellationToken: cancellationToken);

        return result;
    }

    private async Task<GetAuthorBooksResponse> LoadBooksAsync(CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var items = await db.AuthorBooks
            .AsNoTracking()
            .OrderBy(authorBook => authorBook.BookId)
            .Select(authorBook => new AuthorBookListItemResponse
            {
                Id = authorBook.Book.Id,
                Title = authorBook.Book.Title,
                Author = authorBook.Book.Author,
                Url = authorBook.Book.Url
            })
            .ToListAsync(cancellationToken);

        return new GetAuthorBooksResponse { Books = items };
    }

    private async Task<GetAuthorBookResponse?> LoadBookAsync(int id, CancellationToken cancellationToken)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        return await db.AuthorBooks
            .AsNoTracking()
            .Where(authorBook => authorBook.BookId == id)
            .Select(authorBook => new GetAuthorBookResponse
            {
                Id = authorBook.Book.Id,
                Title = authorBook.Book.Title,
                Author = authorBook.Book.Author,
                Url = authorBook.Book.Url
            })
            .FirstOrDefaultAsync(cancellationToken);
    }
}
