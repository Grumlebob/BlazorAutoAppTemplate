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
            await GoToAsync("/books?authorBookId=99999999&bookMode=view");
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

            TrackCreatedBook(title, url);
            TrackCreatedBook(updatedTitle, url);

            await LoginAsync("admin@admin.com", "Admin123");
            await GoHomeAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("author-bookcase-title")).ToHaveTextAsync("The Authors Bookcase");
            await Expect(Page.GetByTestId("user-bookcase-title")).ToHaveTextAsync("Your Bookcase");
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

            var bookLink = UserBookLink(title);
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);
            await Expect(Page.GetByText("Saved books")).ToHaveCountAsync(0);

            await ReloadAndWaitForInteractivityAsync();
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);

            await bookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GoBackAsync();
            await Expect(bookLink).ToBeVisibleAsync();

            await bookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(bookLink).ToBeVisibleAsync();

            await bookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-url-link")).ToContainTextAsync("Go to site");
            await Expect(Page.GetByTestId("book-edit-pencil")).ToBeVisibleAsync();
            await Expect(Page.GetByText("Author:")).ToHaveCountAsync(0);
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(bookLink).ToBeVisibleAsync();

            await bookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GetByTestId("book-edit-pencil").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(title);
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(bookLink).ToBeVisibleAsync();

            await bookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view").GetByRole(AriaRole.Heading, new LocatorGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(bookLink).ToBeVisibleAsync();

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await bookLink.ClickAsync();
            await Page.GetByTestId("book-edit-pencil").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(title);
            await Page.GetByTestId("book-title").FillAsync(updatedTitle);
            await Page.GetByTestId("book-save").ClickAsync();
            var updatedBookLink = UserBookLink(updatedTitle);
            await Expect(updatedBookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedBookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);
            await Expect(Page.GetByText("Saved books")).ToHaveCountAsync(0);

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(updatedBookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await updatedBookLink.ClickAsync();
            await Page.GetByTestId("book-edit-pencil").ClickAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(updatedTitle);
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(updatedBookLink).ToBeVisibleAsync();

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(updatedBookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await updatedBookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();

            await Page.GetByTestId("book-delete").ClickAsync();
            await Expect(Page.GetByTestId("book-delete-confirm")).ToBeVisibleAsync();
            await Page.GetByTestId("book-delete-confirm").ClickAsync();
            await Expect(updatedBookLink).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });
            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedBookLink).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });

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

            var bookLink = UserBookLink(title);
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByTestId("user-book-empty-state")).ToHaveCountAsync(0);
            await Expect(Page.GetByText("Saved books")).ToHaveCountAsync(0);

            await ReloadAndWaitForInteractivityAsync();
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await Page.GetByTestId("design-demo-link").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Book Design Demos" }))
                .ToBeVisibleAsync();
            await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Back to books" }).ClickAsync();
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(bookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await bookLink.ClickAsync();
            await Page.GetByTestId("book-edit-pencil").ClickAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Page.GetByTestId("book-title").FillAsync(updatedTitle);
            await Page.GetByTestId("book-save").ClickAsync();

            var updatedBookLink = UserBookLink(updatedTitle);
            await Expect(updatedBookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedBookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByText("Saved books")).ToHaveCountAsync(0);

            await GoHomeAndWaitForInteractivityAsync();
            await Expect(updatedBookLink).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await updatedBookLink.ClickAsync();
            await Expect(Page.GetByTestId("book-page-view")).ToBeVisibleAsync();

            await Page.GetByTestId("book-delete").ClickAsync();
            await Expect(Page.GetByTestId("book-delete-confirm")).ToBeVisibleAsync();
            await Page.GetByTestId("book-delete-confirm").ClickAsync();
            await Expect(updatedBookLink).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });
            await ReloadAndWaitForBooksDocumentAsync();
            await Expect(updatedBookLink).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });
        });
    }

    private ILocator UserBookLink(string title) =>
        Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = $"{title} details" }).First;

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
