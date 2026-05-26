using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Xunit;
using BlazorAutoApp.Test.E2E.Support;

namespace BlazorAutoApp.Test.E2E.VisualRegression;

public sealed class VisualSnapshotE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task KeyScreens_CanBeCapturedForReview()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            var suffix = Guid.NewGuid().ToString("N")[..8];
            var title = $"Snapshot Book {suffix}";
            var author = $"Snapshot Author {suffix}";
            var url = $"https://example.test/books/{suffix}";
            var email = $"snapshot-{suffix}@example.test";

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("author-bookcase-title")).ToHaveTextAsync("The Authors Bookcase");
            await Expect(Page.GetByTestId("bookcase-login-cta")).ToContainTextAsync("Create your own bookcase by logging in.");
            await CaptureAsync("home");

            TrackCreatedUser(email);
            TrackCreatedBook(title, url);

            await GoToAsync("/Account/Login");
            await CaptureAsync("login");

            await GoToAsync("/Account/Register");
            await CaptureAsync("register");
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.Locator("#Input\\.Password").FillAsync(E2EPassword);
            await Page.Locator("#Input\\.ConfirmPassword").FillAsync(E2EPassword);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Register" }).ClickAsync();
            await GoHomeAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("user-bookcase-title")).ToHaveTextAsync("Your Bookcase");

            await Page.GetByTestId("add-book").ClickAsync();
            await CaptureAsync("books-create");

            await Page.GetByTestId("book-title").FillAsync(title);
            await Page.GetByTestId("book-author").FillAsync(author);
            await Page.GetByTestId("book-url").FillAsync(url);
            await Page.GetByTestId("book-save").ClickAsync();

            var row = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = title });
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await TrackCreatedBookFromRowAsync(row, title, url);
            await row.GetByTestId("book-view").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title })).ToBeVisibleAsync();
            await CaptureAsync("books-details");

            await Page.GetByTestId("book-back").ClickAsync();
            await row.GetByTestId("book-edit").ClickAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(title);
            await CaptureAsync("books-edit");

            await GoToAsync("/Account/Manage");
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Profile" }))
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await CaptureAsync("account-manage");

            await GoToAsync("/books/99999999");
            await Expect(Page.GetByText("Book not found.")).ToBeVisibleAsync();
            await CaptureAsync("not-found");
        });
    }

    private async Task CaptureAsync(string name)
    {
        var snapshotDirectory = GetPlaywrightArtifactPath("Snapshots");
        Directory.CreateDirectory(snapshotDirectory);

        await Page.ScreenshotAsync(new PageScreenshotOptions
        {
            Path = Path.Combine(snapshotDirectory, $"{GetViewportLabel()}-{name}.png"),
            FullPage = true
        });
    }

    private static string GetViewportLabel()
    {
        var width = Environment.GetEnvironmentVariable("E2E_VIEWPORT_WIDTH");
        var height = Environment.GetEnvironmentVariable("E2E_VIEWPORT_HEIGHT");

        if (string.IsNullOrWhiteSpace(width) || string.IsNullOrWhiteSpace(height))
        {
            return "1280x900";
        }

        return $"{width}x{height}";
    }
}
