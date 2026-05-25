using BlazorAutoApp.Core.Features.Books.Domain;

namespace BlazorAutoApp.Features.Books;

internal static class BookSeedExtensions
{
    private static readonly BookSeedItem[] DefaultBooks =
    [
        new("Pride and Prejudice", "Jane Austen"),
        new("1984", "George Orwell"),
        new("The Hobbit", "J.R.R. Tolkien"),
        new("To Kill a Mockingbird", "Harper Lee"),
        new("The Great Gatsby", "F. Scott Fitzgerald"),
        new("Moby-Dick", "Herman Melville"),
        new("Jane Eyre", "Charlotte Bronte"),
        new("Frankenstein", "Mary Shelley"),
        new("The Odyssey", "Homer"),
        new("Don Quixote", "Miguel de Cervantes")
    ];

    public static async Task SeedLocalBooksAsync(this WebApplication app)
    {
        var isLocalEnvironment = app.Environment.IsDevelopment()
            || string.Equals(app.Environment.EnvironmentName, "Docker", StringComparison.OrdinalIgnoreCase);
        var enabled = app.Configuration.GetValue("Books:SeedLocalDefaults", isLocalEnvironment);
        var migrationsRunAtStartup = app.Configuration.GetValue(
            "Database:RunMigrationsAtStartup",
            app.Environment.IsDevelopment());

        if (!enabled || !isLocalEnvironment || !migrationsRunAtStartup)
        {
            return;
        }

        using var scope = app.Services.CreateScope();
        var dbFactory = scope.ServiceProvider.GetRequiredService<IDbContextFactory<AppDbContext>>();
        var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();

        await using var db = await dbFactory.CreateDbContextAsync();
        var existingBooks = await db.Books
            .Select(book => new { book.Title, book.Author })
            .ToListAsync();

        var existing = existingBooks
            .Select(book => BuildKey(book.Title, book.Author))
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        var added = 0;
        foreach (var seed in DefaultBooks)
        {
            if (!existing.Add(BuildKey(seed.Title, seed.Author)))
            {
                continue;
            }

            db.Books.Add(new Book
            {
                Title = seed.Title,
                Author = seed.Author
            });
            added++;
        }

        if (added == 0)
        {
            logger.LogInformation("Local book seed found existing defaults");
            return;
        }

        await db.SaveChangesAsync();
        logger.LogInformation("Seeded {Count} local default books", added);
    }

    private static string BuildKey(string title, string? author) =>
        $"{title.Trim()}|{(author ?? string.Empty).Trim()}";

    private sealed record BookSeedItem(string Title, string Author);
}
