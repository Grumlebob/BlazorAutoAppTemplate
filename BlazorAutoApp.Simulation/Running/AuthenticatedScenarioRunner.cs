using System.Net;
using BlazorAutoApp.Core.Features.Books.UseCases.CreateBook;
using BlazorAutoApp.Core.Features.Books.UseCases.UpdateBook;
using BlazorAutoApp.Simulation.Auth;
using BlazorAutoApp.Simulation.Books;
using BlazorAutoApp.Simulation.Browser;
using BlazorAutoApp.Simulation.Options;
using BlazorAutoApp.Simulation.Reporting;
using BlazorAutoApp.Simulation.Scenarios;

namespace BlazorAutoApp.Simulation.Running;

internal sealed class AuthenticatedScenarioRunner
{
    private readonly SimulationOptions _options;
    private readonly RateLimitBudget _writeBudget;

    public AuthenticatedScenarioRunner(SimulationOptions options)
    {
        _options = options;
        _writeBudget = new RateLimitBudget(options.AuthWriteRpsBudget);
    }

    public async Task<SimulationReport> RunAsync(CancellationToken cancellationToken)
    {
        using var readinessClient = new Http.HttpScenarioClient(_options.Target.BaseUrl);
        var ready = await readinessClient.GetAsync("/health/ready", cancellationToken);
        if (ready.StatusCode is null || (int)ready.StatusCode < 200 || (int)ready.StatusCode >= 400)
        {
            var status = ready.StatusCode?.ToString() ?? ready.Error ?? "unknown";
            throw new TargetUnavailableException($"/health/ready did not return success: {status}");
        }

        var startedAt = DateTimeOffset.UtcNow;
        var runId = RunId.Create(startedAt, _options.Target.Name);
        var syntheticRunId = SyntheticBookNaming.CreateRunId(startedAt);
        var results = new List<ScenarioRunResult>();
        var ledger = new SyntheticBookLedger();

        await using var session = await new BrowserAuthBootstrap(
            AuthBootstrapOptions.From(_options, keepBrowserOpen: _options.BrowserSampler)).BootstrapAsync(cancellationToken);

        using var books = new AuthenticatedBooksClient(_options.Target.BaseUrl, session.Cookies);
        var authCheck = await books.ListAsync("authenticated_book_list", cancellationToken);
        results.Add(books.ToScenarioResult(authCheck, ScenarioCategory.AuthenticatedApi));

        var cleanupDeleted = 0;
        var cleanupLeftovers = 0;
        var cleanupAttempted = false;
        var cleanupSucceeded = true;
        var browserReport = BrowserSamplerReport.Disabled;
        var created = 0;
        var updated = 0;
        var deleted = 0;
        var verifiedCreated = 0;
        var verifiedUpdated = 0;
        var verifiedDeleted = 0;

        try
        {
            if (_options.CleanupOnly || (_options.Cleanup && !_options.Writes))
            {
                cleanupAttempted = true;
                var cleanup = await CleanupAsync(books, results, ledger, cancellationToken);
                cleanupDeleted = cleanup.Deleted;
                cleanupLeftovers = cleanup.Leftovers;
                cleanupSucceeded = cleanup.Succeeded;
            }
            else if (_options.Writes)
            {
                var writeResult = await RunCrudSmokeAsync(
                    books,
                    syntheticRunId,
                    results,
                    ledger,
                    cancellationToken);

                created = writeResult.Created;
                updated = writeResult.Updated;
                deleted = writeResult.Deleted;
                verifiedCreated = writeResult.VerifiedCreated;
                verifiedUpdated = writeResult.VerifiedUpdated;
                verifiedDeleted = writeResult.VerifiedDeleted;

                if (_options.BrowserSampler)
                {
                    var browser = new BrowserSampler(
                        session,
                        books,
                        _options.Target.BaseUrl,
                        _options.Target.Name,
                        syntheticRunId,
                        _options.ReportDirectory,
                        WaitForWriteBudgetAsync);
                    var browserResult = await browser.RunAsync(results, ledger, cancellationToken);
                    browserReport = browserResult.Report;
                    created += browserResult.Created;
                    updated += browserResult.Updated;
                    deleted += browserResult.Deleted;
                    verifiedCreated += browserResult.VerifiedCreated;
                    verifiedUpdated += browserResult.VerifiedUpdated;
                    verifiedDeleted += browserResult.VerifiedDeleted;
                }

                if (!_options.KeepSyntheticData)
                {
                    cleanupAttempted = true;
                    var cleanup = await CleanupAsync(books, results, ledger, cancellationToken);
                    cleanupDeleted = cleanup.Deleted;
                    cleanupLeftovers = cleanup.Leftovers;
                    cleanupSucceeded = cleanup.Succeeded;
                }
            }
        }
        catch (OperationCanceledException) when (_options.Writes && !_options.KeepSyntheticData)
        {
            cleanupAttempted = true;
            using var cleanupTimeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            var cleanup = await CleanupAsync(books, results, ledger, cleanupTimeout.Token);
            cleanupDeleted = cleanup.Deleted;
            cleanupLeftovers = cleanup.Leftovers;
            cleanupSucceeded = cleanup.Succeeded;
            results.Add(new ScenarioRunResult(
                "simulation_cancelled",
                ScenarioCategory.AuthenticatedWrite,
                "cancellation",
                null,
                false,
                false,
                false,
                TimeSpan.Zero,
                null,
                "simulation was cancelled after best-effort cleanup"));
        }

        var endedAt = DateTimeOffset.UtcNow;
        var auth = new AuthReport(
            Enabled: true,
            Mode: session.RegisteredUser ? "browser-register" : "browser-login",
            Target: _options.Target.Name,
            EmailHash: session.EmailHash,
            LoginSucceeded: session.LoginSucceeded,
            RegisteredUser: session.RegisteredUser,
            BootstrapDurationMs: session.BootstrapDuration.TotalMilliseconds,
            AuthenticatedApiCheckSucceeded: authCheck.Expected);

        var writeReport = new WriteReport(
            Enabled: _options.Writes || _options.CleanupOnly || _options.Cleanup,
            RunId: syntheticRunId,
            Created: created,
            Updated: updated,
            Deleted: deleted,
            VerifiedCreated: verifiedCreated,
            VerifiedUpdated: verifiedUpdated,
            VerifiedDeleted: verifiedDeleted,
            CleanupAttempted: cleanupAttempted,
            CleanupDeleted: cleanupDeleted,
            LeftoverSyntheticBooks: cleanupLeftovers,
            CleanupSucceeded: cleanupSucceeded,
            KeptSyntheticData: _options.KeepSyntheticData);

        return SimulationReport.Create(
            runId,
            _options,
            startedAt,
            endedAt,
            results,
            auth,
            writeReport,
            browserReport,
            ledger.ToReportEntries());
    }

    private async Task<CrudSmokeResult> RunCrudSmokeAsync(
        AuthenticatedBooksClient books,
        string syntheticRunId,
        List<ScenarioRunResult> results,
        SyntheticBookLedger ledger,
        CancellationToken cancellationToken)
    {
        var planned = SyntheticBookNaming.Create(_options.Target.Name, syntheticRunId, _options.Profile.Name, 1);
        ledger.Record(planned);

        await WaitForWriteBudgetAsync(cancellationToken);
        var create = await books.CreateAsync(
            new CreateBookRequest
            {
                Title = planned.Title,
                Author = planned.Author,
                Url = planned.Url
            },
            cancellationToken);
        results.Add(books.ToScenarioResult(create, ScenarioCategory.AuthenticatedWrite));
        if (!create.Expected || create.Value is null)
        {
            return new CrudSmokeResult(0, 0, 0, 0, 0, 0);
        }

        ledger.RecordCreated(create.Value);
        var created = 1;

        var verifyCreated = await books.ListAsync("authenticated_book_verify_created", cancellationToken);
        results.Add(books.ToScenarioResult(verifyCreated, ScenarioCategory.AuthenticatedApi));
        var createdVisible = verifyCreated.Value?.Any(book => book.Id == create.Value.Id && book.Title == planned.Title) == true;
        results.Add(VerificationResult("authenticated_book_verify_created_visible", "/api/books", createdVisible));

        var updatedTitle = planned.Title.Replace($" {1:0000}", " updated 0001", StringComparison.Ordinal);
        await WaitForWriteBudgetAsync(cancellationToken);
        var update = await books.UpdateAsync(
            new UpdateBookRequest
            {
                Id = create.Value.Id,
                Title = updatedTitle,
                Author = planned.Author,
                Url = planned.Url
            },
            cancellationToken);
        results.Add(books.ToScenarioResult(update, ScenarioCategory.AuthenticatedWrite));
        var updated = update.Expected ? 1 : 0;

        var verifyUpdated = await books.GetAsync(create.Value.Id, cancellationToken);
        results.Add(books.ToScenarioResult(verifyUpdated, ScenarioCategory.AuthenticatedApi));
        var updatedVisible = verifyUpdated.Value?.Title == updatedTitle;
        results.Add(VerificationResult("authenticated_book_verify_updated_visible", $"/api/books/{create.Value.Id}", updatedVisible));
        if (updatedVisible && verifyUpdated.Value is not null)
        {
            ledger.RecordUpdated(verifyUpdated.Value);
        }

        var deleted = 0;
        var deletedVerified = 0;
        if (!_options.KeepSyntheticData)
        {
            await WaitForWriteBudgetAsync(cancellationToken);
            var delete = await books.DeleteAsync(create.Value.Id, cancellationToken);
            results.Add(books.ToScenarioResult(delete, ScenarioCategory.AuthenticatedWrite));
            deleted = delete.Expected ? 1 : 0;
            if (delete.Expected)
            {
                ledger.RecordDeleted(create.Value.Id, updatedTitle, planned.Author, planned.Url);
            }

            var verifyDeleted = await books.ListAsync("authenticated_book_verify_deleted", cancellationToken);
            results.Add(books.ToScenarioResult(verifyDeleted, ScenarioCategory.AuthenticatedApi));
            var stillPresent = verifyDeleted.Value?.Any(book => book.Id == create.Value.Id) == true;
            deletedVerified = stillPresent ? 0 : 1;
            results.Add(VerificationResult("authenticated_book_verify_deleted_missing", "/api/books", !stillPresent));
        }

        return new CrudSmokeResult(
            created,
            updated,
            deleted,
            createdVisible ? 1 : 0,
            updatedVisible ? 1 : 0,
            deletedVerified);
    }

    private async Task<CleanupResult> CleanupAsync(
        AuthenticatedBooksClient books,
        List<ScenarioRunResult> results,
        SyntheticBookLedger ledger,
        CancellationToken cancellationToken)
    {
        var cleanup = new SyntheticBookCleanup(books, _options.Target.Name, _writeBudget);
        return await cleanup.CleanupAsync(results, ledger, cancellationToken);
    }

    private async Task WaitForWriteBudgetAsync(CancellationToken cancellationToken)
    {
        while (!_writeBudget.IsAvailable(DateTimeOffset.UtcNow))
        {
            await Task.Delay(100, cancellationToken);
        }

        _writeBudget.MarkUsed(DateTimeOffset.UtcNow);
    }

    private static ScenarioRunResult VerificationResult(string name, string path, bool expected) =>
        new(
            name,
            ScenarioCategory.AuthenticatedApi,
            path,
            HttpStatusCode.OK,
            expected,
            false,
            false,
            TimeSpan.Zero,
            null,
            expected ? null : "logical verification failed");
}

internal sealed record CrudSmokeResult(
    int Created,
    int Updated,
    int Deleted,
    int VerifiedCreated,
    int VerifiedUpdated,
    int VerifiedDeleted);
