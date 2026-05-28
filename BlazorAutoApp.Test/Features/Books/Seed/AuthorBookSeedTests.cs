using BlazorAutoApp.Infrastructure.Persistence;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace BlazorAutoApp.Test.Features.Books.Seed;

public sealed class AuthorBookSeedTests
{
    [Fact]
    public async Task StartupSeed_IsIdempotentAndUpdatesAuthorBooksBySeedKey()
    {
        var firstFactory = CreateSeedFactory();
        await firstFactory.InitializeAsync();

        try
        {
            var originalIds = await ReadAuthorBookIdsAsync(firstFactory);
            Assert.Equal(
                [
                    "geckobot",
                    "improveddb",
                    "kinojoin",
                    "ship",
                    "traceback",
                    "unlost"
                ],
                originalIds.Keys);
            Assert.All(originalIds.Values, id => Assert.True(id > 0));

            await RenameSeededBookAsync(firstFactory, "ship", "Changed Ship");

            var secondFactory = CreateSeedFactory(firstFactory.ConnectionString);
            await secondFactory.InitializeAsync();

            try
            {
                var reseededIds = await ReadAuthorBookIdsAsync(secondFactory);
                Assert.Equal(originalIds, reseededIds);

                using var scope = secondFactory.Services.CreateScope();
                var dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
                await using var db = await dbFactory.CreateDbContextAsync();
                var ship = await db.AuthorBooks
                    .AsNoTracking()
                    .Include(authorBook => authorBook.Book)
                    .SingleAsync(authorBook => authorBook.SeedKey == "ship");

                Assert.Equal("Ship Inspections", ship.Book.Title);
                Assert.Equal("Jacob Grum", ship.Book.Author);
            }
            finally
            {
                await secondFactory.DisposeAsync();
            }
        }
        finally
        {
            await firstFactory.DisposeAsync();
        }
    }

    private static WebAppFactory CreateSeedFactory(string? connectionString = null) =>
        new(new WebAppFactoryOptions
        {
            PostgresConnectionString = connectionString,
            RunMigrations = false,
            RunStartupMigrations = true,
            AuthorBooksSeedAtStartup = true
        });

    private static async Task<SortedDictionary<string, int>> ReadAuthorBookIdsAsync(WebAppFactory factory)
    {
        using var scope = factory.Services.CreateScope();
        var dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
        await using var db = await dbFactory.CreateDbContextAsync();
        var rows = await db.AuthorBooks
            .AsNoTracking()
            .OrderBy(authorBook => authorBook.SeedKey)
            .Select(authorBook => new { authorBook.SeedKey, authorBook.BookId })
            .ToListAsync();

        return new SortedDictionary<string, int>(
            rows.ToDictionary(row => row.SeedKey, row => row.BookId),
            StringComparer.Ordinal);
    }

    private static async Task RenameSeededBookAsync(WebAppFactory factory, string seedKey, string title)
    {
        using var scope = factory.Services.CreateScope();
        var dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
        await using var db = await dbFactory.CreateDbContextAsync();
        var authorBook = await db.AuthorBooks
            .Include(book => book.Book)
            .SingleAsync(book => book.SeedKey == seedKey);

        authorBook.Book.Title = title;
        await db.SaveChangesAsync();
    }
}
