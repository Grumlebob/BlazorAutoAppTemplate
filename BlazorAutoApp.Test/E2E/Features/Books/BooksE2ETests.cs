using System;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Xunit;
using BlazorAutoApp.Test.E2E.Support;

namespace BlazorAutoApp.Test.E2E.Features.Books;

public sealed class BooksE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task Books_CanCreateViewEditCancelAndNavigateBack()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            await GoHomeAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("design-demo-link")).ToBeVisibleAsync();
            await Page.GetByTestId("design-demo-link").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Book Design Demos" }))
                .ToBeVisibleAsync();
            await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Back to books" }).ClickAsync();
            await Expect(Page.GetByTestId("author-bookcase-title")).ToHaveTextAsync("The Authors Bookcase");
            await Page.GetByTestId("author-bookcase-book").First.ClickAsync(new LocatorClickOptions { Force = true });
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-edit-pencil")).ToHaveCountAsync(0);
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(Page.GetByTestId("author-bookcase-title")).ToHaveTextAsync("The Authors Bookcase");
            await GoToAsync("/books/author/not-a-real-book");
            await Expect(Page.GetByText("Book not found.")).ToBeVisibleAsync();
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(Page.GetByTestId("author-bookcase-title")).ToHaveTextAsync("The Authors Bookcase");
            await Expect(Page.GetByTestId("bookcase-login-cta")).ToContainTextAsync("Create your own bookcase by logging in.");
            await Expect(Page.GetByTestId("add-book")).ToHaveCountAsync(0);
            await Expect(Page.GetByText("Saved books")).ToHaveCountAsync(0);

            var suffix = Guid.NewGuid().ToString("N")[..8];
            var title = $"E2E Book {suffix}";
            var updatedTitle = $"E2E Book Updated {suffix}";
            var author = $"E2E Author {suffix}";
            var url = $"https://example.test/books/{suffix}";
            var email = $"books-{suffix}@example.test";

            TrackCreatedUser(email);
            TrackCreatedBook(title, url);
            TrackCreatedBook(updatedTitle, url);

            await RegisterAsync(email);
            await GoHomeAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("author-bookcase-title")).ToHaveTextAsync("The Authors Bookcase");
            await Expect(Page.GetByTestId("user-bookcase-title")).ToHaveTextAsync("Your Bookcase");
            await Expect(Page.GetByTestId("user-book-empty-state")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("add-book")).ToBeVisibleAsync();
            await Expect(Page.GetByText("Saved books")).ToHaveCountAsync(0);

            await Page.GetByTestId("add-book").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(string.Empty);
            await Expect(Page.GetByTestId("book-author")).ToHaveValueAsync(string.Empty);
            await Expect(Page.GetByTestId("book-url")).ToHaveValueAsync(string.Empty);
            await Page.GetByTestId("book-title").FillAsync(title);
            await Page.GetByTestId("book-author").FillAsync(author);
            await Page.GetByTestId("book-url").FillAsync(url);
            await Page.GetByTestId("book-save").ClickAsync();

            var row = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = title });
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);
            await Expect(Page.GetByText("Saved books")).ToBeVisibleAsync();
            await TrackCreatedBookFromRowAsync(row, title, url);

            await ReloadAndWaitForInteractivityAsync();
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);

            await Page.GetByTestId("user-bookcase-book").First.ClickAsync(new LocatorClickOptions { Force = true });
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GoBackAsync();
            await Expect(row).ToBeVisibleAsync();

            await Page.GetByTestId("user-bookcase-book").First.ClickAsync(new LocatorClickOptions { Force = true });
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(row).ToBeVisibleAsync();

            await row.GetByTestId("book-view").ClickAsync();
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-url-link")).ToContainTextAsync("Go to site");
            await Expect(Page.GetByTestId("book-edit-pencil")).ToBeVisibleAsync();
            await Expect(Page.GetByText("Author:")).ToHaveCountAsync(0);
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(row).ToBeVisibleAsync();

            await row.GetByTestId("book-view").ClickAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GetByTestId("book-edit-pencil").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(title);
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(row).ToBeVisibleAsync();

            await row.GetByTestId("book-view").ClickAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(row).ToBeVisibleAsync();

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await row.GetByTestId("book-edit").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(title);
            await Page.GetByTestId("book-title").FillAsync(updatedTitle);
            await Page.GetByTestId("book-save").ClickAsync();
            var updatedRow = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = updatedTitle });
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await TrackCreatedBookFromRowAsync(updatedRow, updatedTitle, url);

            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);

            await updatedRow.GetByTestId("book-edit").ClickAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(updatedTitle);
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(updatedRow).ToBeVisibleAsync();

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            Page.Dialog += async (_, dialog) => await dialog.AcceptAsync();
            await updatedRow.GetByTestId("book-delete").ClickAsync();
            await Expect(updatedRow).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });
            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedRow).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });

            await GoToAsync("/books/99999999");
            await Expect(Page.GetByText("Book not found.")).ToBeVisibleAsync();
        });
    }

    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task SeededUser_BookcaseCrudSurvivesRefreshAndNavigation()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            var suffix = Guid.NewGuid().ToString("N")[..8];
            var title = $"E2E Book Seeded {suffix}";
            var updatedTitle = $"E2E Book Updated Seeded {suffix}";
            var author = $"E2E Author Seeded {suffix}";
            var url = $"https://example.test/books/{suffix}";

            TrackCreatedBook(title, url);
            TrackCreatedBook(updatedTitle, url);

            await LoginAsync("user@user.com", "User123");
            await GoHomeAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("user-bookcase-title")).ToHaveTextAsync("Your Bookcase");
            await Expect(Page.GetByTestId("add-book")).ToBeVisibleAsync();

            await Page.GetByTestId("add-book").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Page.GetByTestId("book-title").FillAsync(title);
            await Page.GetByTestId("book-author").FillAsync(author);
            await Page.GetByTestId("book-url").FillAsync(url);
            await Page.GetByTestId("book-save").ClickAsync();

            var row = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = title });
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await TrackCreatedBookFromRowAsync(row, title, url);
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);

            await ReloadAndWaitForInteractivityAsync();
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await Page.GetByTestId("design-demo-link").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Book Design Demos" }))
                .ToBeVisibleAsync();
            await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Back to books" }).ClickAsync();
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await row.GetByTestId("book-edit").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Page.GetByTestId("book-title").FillAsync(updatedTitle);
            await Page.GetByTestId("book-save").ClickAsync();

            var updatedRow = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = updatedTitle });
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await TrackCreatedBookFromRowAsync(updatedRow, updatedTitle, url);
            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            Page.Dialog += async (_, dialog) => await dialog.AcceptAsync();
            await updatedRow.GetByTestId("book-delete").ClickAsync();
            await Expect(updatedRow).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });
            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedRow).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });
        });
    }

    private async Task RegisterAsync(string email)
    {
        await GoToAsync("/Account/Register");
        await Page.Locator("#Input\\.Email").FillAsync(email);
        await Page.Locator("#Input\\.Password").FillAsync(E2EPassword);
        await Page.Locator("#Input\\.ConfirmPassword").FillAsync(E2EPassword);
        await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Register" }).ClickAsync();
    }

    private async Task ReloadAndWaitForBooksDocumentAsync()
    {
        await Page.ReloadAsync(new PageReloadOptions { WaitUntil = WaitUntilState.DOMContentLoaded });
        await Expect(Page.GetByTestId("author-bookcase-title")).ToHaveTextAsync("The Authors Bookcase");
    }

    private async Task LoginAsync(string email, string password)
    {
        await GoToAsync("/Account/Login");
        await Page.Locator("#Input\\.Email").FillAsync(email);
        await Page.Locator("#Input\\.Password").FillAsync(password);
        await Page
            .GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Log in", Exact = true })
            .ClickAsync();
        await Page.WaitForLoadStateAsync(LoadState.DOMContentLoaded);
    }
}
