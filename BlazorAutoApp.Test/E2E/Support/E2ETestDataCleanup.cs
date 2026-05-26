using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using BlazorAutoApp.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Playwright;

namespace BlazorAutoApp.Test.E2E.Support;

internal sealed class E2ETestDataCleanup(Func<IPage> page, Func<string, Task<IResponse?>> goTo)
{
    internal const string DefaultPassword = "Passw0rd!";

    private readonly List<TrackedBook> _trackedBooks = [];
    private readonly List<TrackedUser> _trackedUsers = [];

    public void TrackCreatedUser(string email, string password = DefaultPassword)
    {
        if (string.IsNullOrWhiteSpace(email))
        {
            return;
        }

        _trackedUsers.Add(new TrackedUser(email.Trim(), password));
    }

    public void TrackCreatedBook(string title, string? url = null, int? id = null)
    {
        if (string.IsNullOrWhiteSpace(title) && string.IsNullOrWhiteSpace(url) && id is null)
        {
            return;
        }

        _trackedBooks.Add(new TrackedBook(id, title?.Trim(), url?.Trim()));
    }

    public async Task TrackCreatedBookFromRowAsync(ILocator row, string title, string? url = null)
    {
        var testId = await row.GetAttributeAsync("data-testid");
        var id = TryGetBookId(testId);
        TrackCreatedBook(title, url, id);
    }

    public async Task CleanupAsync()
    {
        await CleanupTrackedBooksAsync();
        await CleanupTrackedUsersAsync();
    }

    private async Task CleanupTrackedBooksAsync()
    {
        if (_trackedBooks.Count == 0)
        {
            return;
        }

        var remainingBooks = await TryCleanupBooksThroughAppAsync(_trackedBooks);
        if (remainingBooks.Count == 0)
        {
            return;
        }

        if (_trackedUsers.Count > 0 && await TrySignInForCleanupAsync(_trackedUsers[0]))
        {
            remainingBooks = await TryCleanupBooksThroughAppAsync(remainingBooks);
            if (remainingBooks.Count == 0)
            {
                return;
            }
        }

        await CleanupBooksThroughDatabaseAsync(remainingBooks);
    }

    private async Task<IReadOnlyList<TrackedBook>> TryCleanupBooksThroughAppAsync(IReadOnlyList<TrackedBook> books)
    {
        if (books.Count == 0)
        {
            return [];
        }

        try
        {
            var safeBooks = books
                .Where(book => book.Id is not null || IsSafeE2EBookTitle(book.Title) || IsSafeE2EBookUrl(book.Url))
                .ToArray();
            if (safeBooks.Length == 0)
            {
                return [];
            }

            var payload = JsonSerializer.Serialize(new
            {
                ids = safeBooks.Where(book => book.Id is not null).Select(book => book.Id!.Value).Distinct().ToArray(),
                titles = safeBooks.Select(book => book.Title).Where(IsSafeE2EBookTitle).Distinct().ToArray(),
                urls = safeBooks.Select(book => book.Url).Where(IsSafeE2EBookUrl).Distinct().ToArray()
            });

            var cleanupResultJson = await page().EvaluateAsync<string>(
                """
                async payloadJson => {
                    const payload = JSON.parse(payloadJson);
                    const ids = new Set(payload.ids ?? []);
                    const titles = new Set(payload.titles ?? []);
                    const urls = new Set(payload.urls ?? []);
                    let listLoaded = false;

                    try {
                        const listResponse = await fetch('/api/books/', { credentials: 'same-origin' });
                        if (listResponse.ok) {
                            listLoaded = true;
                            const data = await listResponse.json();
                            const books = data.books ?? data.Books ?? [];
                            for (const book of books) {
                                if (titles.has(book.title ?? book.Title) || urls.has(book.url ?? book.Url)) {
                                    ids.add(book.id ?? book.Id);
                                }
                            }
                        }

                        const remaining = [];
                        for (const id of ids) {
                            const deleteResponse = await fetch(`/api/books/${id}`, {
                                method: 'DELETE',
                                credentials: 'same-origin'
                            });

                            if (!deleteResponse.ok && deleteResponse.status !== 404) {
                                remaining.push(id);
                            }
                        }

                        return JSON.stringify({ ListLoaded: listLoaded, RemainingIds: remaining });
                    } catch {
                        return JSON.stringify({ ListLoaded: listLoaded, RemainingIds: Array.from(ids) });
                    }
                }
                """,
                payload);

            var cleanupResult = JsonSerializer.Deserialize<BrowserBookCleanupResult>(cleanupResultJson)
                ?? new BrowserBookCleanupResult(false, []);
            var unresolvedIds = cleanupResult.RemainingIds.ToHashSet();
            var hasUnresolvedDiscoveredId = unresolvedIds.Any(id => safeBooks.All(book => book.Id != id));
            return safeBooks
                .Where(book =>
                    book.Id is not null && unresolvedIds.Contains(book.Id.Value) ||
                    book.Id is null && (!cleanupResult.ListLoaded || hasUnresolvedDiscoveredId))
                .ToArray();
        }
        catch
        {
            return books;
        }
    }

    private async Task<bool> TrySignInForCleanupAsync(TrackedUser user)
    {
        if (!IsSafeE2EEmail(user.Email))
        {
            return false;
        }

        try
        {
            await goTo("/Account/Login");
            await page().Locator("#Input\\.Email").FillAsync(user.Email, new LocatorFillOptions { Timeout = 5_000 });
            await page().Locator("#Input\\.Password").FillAsync(user.Password, new LocatorFillOptions { Timeout = 5_000 });
            await page()
                .GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Log in", Exact = true })
                .ClickAsync(new LocatorClickOptions { Timeout = 5_000 });
            await page().WaitForLoadStateAsync(LoadState.DOMContentLoaded, new PageWaitForLoadStateOptions { Timeout = 10_000 });
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static async Task CleanupBooksThroughDatabaseAsync(IReadOnlyList<TrackedBook> books)
    {
        var ids = books.Where(book => book.Id is not null).Select(book => book.Id!.Value).Distinct().ToArray();
        var titles = books.Select(book => book.Title).Where(IsSafeE2EBookTitle).Distinct().ToArray();
        var urls = books.Select(book => book.Url).Where(IsSafeE2EBookUrl).Distinct().ToArray();
        if (ids.Length == 0 && titles.Length == 0 && urls.Length == 0)
        {
            return;
        }

        await using var db = CreateCleanupDbContext();
        var persistedBooks = await db.Books
            .Where(book =>
                ids.Contains(book.Id) ||
                titles.Contains(book.Title) ||
                (book.Url != null && urls.Contains(book.Url)))
            .ToListAsync();

        db.Books.RemoveRange(persistedBooks);
        await db.SaveChangesAsync();
    }

    private async Task CleanupTrackedUsersAsync()
    {
        var emails = _trackedUsers
            .Select(user => user.Email)
            .Where(IsSafeE2EEmail)
            .Select(email => email.ToUpperInvariant())
            .Distinct()
            .ToArray();
        if (emails.Length == 0)
        {
            return;
        }

        await using var db = CreateCleanupDbContext();
        var users = await db.Users
            .Where(user => user.NormalizedEmail != null && emails.Contains(user.NormalizedEmail))
            .ToListAsync();

        db.Users.RemoveRange(users);
        await db.SaveChangesAsync();
    }

    private static AppDbContext CreateCleanupDbContext()
    {
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(GetCleanupConnectionString())
            .Options;

        return new AppDbContext(options);
    }

    private static string GetCleanupConnectionString()
    {
        var configured = Environment.GetEnvironmentVariable("E2E_CLEANUP_CONNECTION_STRING");
        if (!string.IsNullOrWhiteSpace(configured))
        {
            return configured;
        }

        configured = Environment.GetEnvironmentVariable("ConnectionStrings__DefaultConnection");
        if (!string.IsNullOrWhiteSpace(configured))
        {
            return configured;
        }

        var env = ReadDotEnv();
        var hostPort = GetEnvValue(env, "POSTGRES_HOST_PORT", "5432");
        var database = GetEnvValue(env, "POSTGRES_DB", "app");
        var username = GetEnvValue(env, "POSTGRES_USER", "postgres");
        var password = GetEnvValue(env, "POSTGRES_PASSWORD", "postgres");
        return $"Host=localhost;Port={hostPort};Database={database};Username={username};Password={password};GSS Encryption Mode=Disable";
    }

    private static Dictionary<string, string> ReadDotEnv()
    {
        var envPath = Path.Combine(FindRepositoryRoot(), ".env");
        if (!File.Exists(envPath))
        {
            return [];
        }

        return File.ReadLines(envPath)
            .Select(line => line.Trim())
            .Where(line => line.Length > 0 && !line.StartsWith('#'))
            .Select(line => line.Split('=', 2))
            .Where(parts => parts.Length == 2)
            .ToDictionary(parts => parts[0].Trim(), parts => parts[1].Trim().Trim('"'), StringComparer.OrdinalIgnoreCase);
    }

    private static string GetEnvValue(IReadOnlyDictionary<string, string> env, string key, string fallback) =>
        env.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value) ? value : fallback;

    private static int? TryGetBookId(string? testId)
    {
        const string prefix = "book-row-";
        if (testId is null || !testId.StartsWith(prefix, StringComparison.Ordinal))
        {
            return null;
        }

        return int.TryParse(testId[prefix.Length..], out var id) ? id : null;
    }

    private static bool IsSafeE2EEmail(string? email) =>
        !string.IsNullOrWhiteSpace(email) &&
        email.EndsWith("@example.test", StringComparison.OrdinalIgnoreCase);

    private static bool IsSafeE2EBookTitle(string? title) =>
        !string.IsNullOrWhiteSpace(title) &&
        (title.StartsWith("E2E Book ", StringComparison.Ordinal) ||
         title.StartsWith("E2E Book Updated ", StringComparison.Ordinal) ||
         title.StartsWith("Snapshot Book ", StringComparison.Ordinal));

    private static bool IsSafeE2EBookUrl(string? url) =>
        !string.IsNullOrWhiteSpace(url) &&
        url.StartsWith("https://example.test/books/", StringComparison.OrdinalIgnoreCase);

    private static string FindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "BlazorAutoApp.sln")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        return AppContext.BaseDirectory;
    }

    private sealed record TrackedBook(int? Id, string? Title, string? Url);

    private sealed record TrackedUser(string Email, string Password);

    private sealed record BrowserBookCleanupResult(bool ListLoaded, int[] RemainingIds);
}
