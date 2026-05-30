using BlazorAutoApp.Simulation.Running;
using BlazorAutoApp.Simulation.Scenarios;

namespace BlazorAutoApp.Simulation.Books;

internal sealed class SyntheticBookCleanup
{
    private readonly AuthenticatedBooksClient _books;
    private readonly string _target;
    private readonly RateLimitBudget _writeBudget;

    public SyntheticBookCleanup(
        AuthenticatedBooksClient books,
        string target,
        RateLimitBudget writeBudget)
    {
        _books = books;
        _target = target;
        _writeBudget = writeBudget;
    }

    public async Task<CleanupResult> CleanupAsync(
        List<ScenarioRunResult> results,
        SyntheticBookLedger ledger,
        CancellationToken cancellationToken)
    {
        var list = await _books.ListAsync("authenticated_book_cleanup_list", cancellationToken);
        results.Add(_books.ToScenarioResult(list, ScenarioCategory.AuthenticatedApi));
        if (!list.Expected || list.Value is null)
        {
            return new CleanupResult(0, 1, false);
        }

        var candidates = list.Value
            .Where(book => SyntheticBookNaming.IsSafeToDelete(book, _target))
            .ToArray();

        var deleted = 0;
        foreach (var book in candidates)
        {
            await WaitForBudgetAsync(cancellationToken);
            var delete = await _books.DeleteAsync(book.Id, cancellationToken);
            results.Add(_books.ToScenarioResult(delete, ScenarioCategory.AuthenticatedWrite));
            if (delete.Expected)
            {
                deleted++;
                ledger.RecordDeleted(book);
            }
        }

        var verify = await _books.ListAsync("authenticated_book_cleanup_verify", cancellationToken);
        results.Add(_books.ToScenarioResult(verify, ScenarioCategory.AuthenticatedApi));
        var leftovers = verify.Value?.Count(book => SyntheticBookNaming.IsSafeToDelete(book, _target)) ?? candidates.Length - deleted;

        return new CleanupResult(deleted, leftovers, leftovers == 0);
    }

    private async Task WaitForBudgetAsync(CancellationToken cancellationToken)
    {
        while (!_writeBudget.IsAvailable(DateTimeOffset.UtcNow))
        {
            await Task.Delay(100, cancellationToken);
        }

        _writeBudget.MarkUsed(DateTimeOffset.UtcNow);
    }
}

internal sealed record CleanupResult(int Deleted, int Leftovers, bool Succeeded);
