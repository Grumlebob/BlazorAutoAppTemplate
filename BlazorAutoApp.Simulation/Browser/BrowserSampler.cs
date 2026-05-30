using BlazorAutoApp.Core.Features.Books.UseCases.GetBooks;
using Microsoft.Playwright;
using BlazorAutoApp.Simulation.Auth;
using BlazorAutoApp.Simulation.Books;
using BlazorAutoApp.Simulation.Reporting;
using BlazorAutoApp.Simulation.Running;
using BlazorAutoApp.Simulation.Scenarios;

namespace BlazorAutoApp.Simulation.Browser;

internal sealed class BrowserSampler
{
    private readonly AuthenticatedSession _session;
    private readonly AuthenticatedBooksClient _books;
    private readonly Uri _baseUrl;
    private readonly string _target;
    private readonly string _syntheticRunId;
    private readonly string _artifactRoot;
    private readonly Func<CancellationToken, Task> _waitForWriteBudget;
    private static readonly TimeSpan UserBookcaseTimeout = TimeSpan.FromSeconds(45);

    public BrowserSampler(
        AuthenticatedSession session,
        AuthenticatedBooksClient books,
        Uri baseUrl,
        string target,
        string syntheticRunId,
        string artifactRoot,
        Func<CancellationToken, Task> waitForWriteBudget)
    {
        _session = session;
        _books = books;
        _baseUrl = baseUrl;
        _target = target;
        _syntheticRunId = syntheticRunId;
        _artifactRoot = artifactRoot;
        _waitForWriteBudget = waitForWriteBudget;
    }

    public async Task<BrowserSamplerExecutionResult> RunAsync(
        List<ScenarioRunResult> results,
        SyntheticBookLedger ledger,
        CancellationToken cancellationToken)
    {
        if (_session.BrowserContext is null)
        {
            results.Add(FailedResult("browser context was not kept open"));
            return new BrowserSamplerExecutionResult(BrowserSamplerReport.Disabled, 0, 0, 0, 0, 0, 0);
        }

        var screenshotDirectory = Path.Combine(_artifactRoot, "browser-failures");
        var page = await _session.BrowserContext.NewPageAsync();
        var planned = SyntheticBookNaming.Create(_target, _syntheticRunId, "browser", 9001);
        var updatedTitle = planned.Title.Replace(" browser 9001", " browser updated 9001", StringComparison.Ordinal);
        var created = 0;
        var updated = 0;
        var deleted = 0;
        var verifiedCreated = 0;
        var verifiedUpdated = 0;
        var verifiedDeleted = 0;

        try
        {
            await page.GotoAsync(Absolute("/books"), new PageGotoOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
            await WaitForUserBookcaseAsync(page, cancellationToken);
            await WaitForInteractiveRendererAsync(page, cancellationToken);

            await page.GetByTestId("add-book").ClickAsync();
            await page.GetByTestId("book-page-editor").WaitForAsync(new LocatorWaitForOptions
            {
                State = WaitForSelectorState.Visible,
                Timeout = 15_000
            });
            await WaitForInteractiveRendererAsync(page, cancellationToken);
            await page.GetByTestId("book-title").FillAsync(planned.Title);
            await page.GetByTestId("book-author").FillAsync(planned.Author);
            await page.GetByTestId("book-url").FillAsync(planned.Url);
            await _waitForWriteBudget(cancellationToken);
            await page.GetByTestId("book-save").ClickAsync();
            created = 1;

            var createdLink = page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = $"{planned.Title} details" }).First;
            await createdLink.WaitForAsync(new LocatorWaitForOptions { State = WaitForSelectorState.Visible, Timeout = 30_000 });
            verifiedCreated = 1;

            var createdBook = await FindByTitleAsync(planned.Title, cancellationToken);
            if (createdBook is not null)
            {
                ledger.RecordCreated(createdBook);
            }

            await createdLink.ClickAsync();
            await page.GetByTestId("book-page-view").WaitForAsync(new LocatorWaitForOptions
            {
                State = WaitForSelectorState.Visible,
                Timeout = 15_000
            });
            await page.GetByTestId("book-edit-pencil").ClickAsync();
            await page.GetByTestId("book-page-editor").WaitForAsync(new LocatorWaitForOptions
            {
                State = WaitForSelectorState.Visible,
                Timeout = 15_000
            });
            await page.GetByTestId("book-title").FillAsync(updatedTitle);
            await _waitForWriteBudget(cancellationToken);
            await page.GetByTestId("book-save").ClickAsync();
            updated = 1;

            var updatedLink = page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = $"{updatedTitle} details" }).First;
            await updatedLink.WaitForAsync(new LocatorWaitForOptions { State = WaitForSelectorState.Visible, Timeout = 30_000 });
            verifiedUpdated = 1;

            var updatedBook = await FindByTitleAsync(updatedTitle, cancellationToken);
            if (updatedBook is not null)
            {
                ledger.RecordUpdated(updatedBook);
            }

            await updatedLink.ClickAsync();
            await page.GetByTestId("book-page-view").WaitForAsync(new LocatorWaitForOptions
            {
                State = WaitForSelectorState.Visible,
                Timeout = 15_000
            });
            await page.GetByTestId("book-delete").ClickAsync();
            await page.GetByTestId("book-delete-confirm").WaitForAsync(new LocatorWaitForOptions
            {
                State = WaitForSelectorState.Visible,
                Timeout = 15_000
            });
            await _waitForWriteBudget(cancellationToken);
            await page.GetByTestId("book-delete-confirm").ClickAsync();
            deleted = 1;
            await updatedLink.WaitForAsync(new LocatorWaitForOptions { State = WaitForSelectorState.Hidden, Timeout = 30_000 });
            verifiedDeleted = 1;

            if (updatedBook is not null)
            {
                ledger.RecordDeleted(updatedBook);
            }

            results.Add(SuccessResult());
            return new BrowserSamplerExecutionResult(
                new BrowserSamplerReport(true, 1, 1, 0, null),
                created,
                updated,
                deleted,
                verifiedCreated,
                verifiedUpdated,
                verifiedDeleted);
        }
        catch (Exception ex) when (ex is PlaywrightException or TimeoutException)
        {
            Directory.CreateDirectory(screenshotDirectory);
            var screenshotPath = Path.Combine(screenshotDirectory, $"{DateTimeOffset.UtcNow:yyyyMMdd-HHmmss}-browser-sampler.png");
            await page.ScreenshotAsync(new PageScreenshotOptions { Path = screenshotPath, FullPage = true });
            results.Add(FailedResult(ex.Message));
            return new BrowserSamplerExecutionResult(
                new BrowserSamplerReport(true, 1, 0, 1, screenshotDirectory),
                created,
                updated,
                deleted,
                verifiedCreated,
                verifiedUpdated,
                verifiedDeleted);
        }
        finally
        {
            await page.CloseAsync();
        }
    }

    private async Task<BookListItemResponse?> FindByTitleAsync(string title, CancellationToken cancellationToken)
    {
        var list = await _books.ListAsync("authenticated_book_browser_verify_list", cancellationToken);
        return list.Value?.FirstOrDefault(book => string.Equals(book.Title, title, StringComparison.Ordinal));
    }

    private static async Task WaitForUserBookcaseAsync(IPage page, CancellationToken cancellationToken)
    {
        var deadline = DateTimeOffset.UtcNow + UserBookcaseTimeout;
        var bookcaseTitle = page.GetByTestId("user-bookcase-title");
        var loginPrompt = page.GetByTestId("bookcase-login-cta");

        while (DateTimeOffset.UtcNow < deadline)
        {
            cancellationToken.ThrowIfCancellationRequested();

            if (await bookcaseTitle.IsVisibleAsync())
            {
                return;
            }

            if (await loginPrompt.IsVisibleAsync())
            {
                throw new PlaywrightException("Browser sampler opened /books but the login prompt was visible; authentication cookies were not accepted by the UI.");
            }

            await Task.Delay(250, cancellationToken);
        }

        throw new TimeoutException("Timed out waiting for the authenticated user bookcase.");
    }

    private static async Task WaitForInteractiveRendererAsync(IPage page, CancellationToken cancellationToken)
    {
        var deadline = DateTimeOffset.UtcNow + TimeSpan.FromSeconds(20);
        var marker = page.GetByTestId("is-interactive");
        while (DateTimeOffset.UtcNow < deadline)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                var text = await marker.TextContentAsync(new LocatorTextContentOptions { Timeout = 1_000 });
                if (string.Equals(text?.Trim(), "yes", StringComparison.OrdinalIgnoreCase))
                {
                    return;
                }
            }
            catch (PlaywrightException)
            {
                // The marker can be absent during navigation; retry until the deadline.
            }

            await Task.Delay(250, cancellationToken);
        }

        throw new TimeoutException("Timed out waiting for the Blazor renderer to become interactive.");
    }

    private string Absolute(string path) =>
        new Uri(_baseUrl, path).ToString();

    private static ScenarioRunResult SuccessResult() =>
        new(
            "browser_sampler_journey",
            ScenarioCategory.Browser,
            "/books",
            System.Net.HttpStatusCode.OK,
            true,
            false,
            false,
            TimeSpan.Zero,
            null,
            null);

    private static ScenarioRunResult FailedResult(string error) =>
        new(
            "browser_sampler_journey",
            ScenarioCategory.Browser,
            "/books",
            System.Net.HttpStatusCode.OK,
            false,
            false,
            false,
            TimeSpan.Zero,
            null,
            error);
}

internal sealed record BrowserSamplerExecutionResult(
    BrowserSamplerReport Report,
    int Created,
    int Updated,
    int Deleted,
    int VerifiedCreated,
    int VerifiedUpdated,
    int VerifiedDeleted);
