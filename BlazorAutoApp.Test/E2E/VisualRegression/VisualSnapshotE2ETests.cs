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
            await Page.GetByTestId("author-bookcase-book").First.ClickAsync(new LocatorClickOptions { Force = true });
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await CaptureAsync("books-author-details");
            await Page.GetByTestId("book-back").ClickAsync();
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
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await CaptureAsync("books-create");

            await Page.GetByTestId("book-title").FillAsync(title);
            await Page.GetByTestId("book-author").FillAsync(author);
            await Page.GetByTestId("book-url").FillAsync(url);
            await Page.GetByTestId("book-save").ClickAsync();

            var bookLink = Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = $"{title} details" }).First;
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await bookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title })).ToBeVisibleAsync();
            await CaptureAsync("books-details");

            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await bookLink.ClickAsync();
            await Page.GetByTestId("book-edit-pencil").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
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
