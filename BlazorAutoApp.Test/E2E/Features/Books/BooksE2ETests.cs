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
            await Page.GetByTestId("book-title").FillAsync(title);
            await Page.GetByTestId("book-author").FillAsync(author);
            await Page.GetByTestId("book-url").FillAsync(url);
            await Page.GetByTestId("book-save").ClickAsync();

            var row = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = title });
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await Expect(Page.GetByText("Saved books")).ToBeVisibleAsync();
            await TrackCreatedBookFromRowAsync(row, title, url);

            await row.GetByTestId("book-view").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GetByTestId("book-back").ClickAsync();
            await Expect(row).ToBeVisibleAsync();

            await row.GetByTestId("book-view").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GoBackAsync();
            await Expect(row).ToBeVisibleAsync();

            await row.GetByTestId("book-edit").ClickAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(title);
            await Page.GetByTestId("book-title").FillAsync(updatedTitle);
            await Page.GetByTestId("book-save").ClickAsync();
            var updatedRow = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = updatedTitle });
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await TrackCreatedBookFromRowAsync(updatedRow, updatedTitle, url);

            await updatedRow.GetByTestId("book-edit").ClickAsync();
            await Expect(Page.GetByTestId("book-title")).ToHaveValueAsync(updatedTitle);
            await Page.GetByTestId("book-cancel").ClickAsync();
            await Expect(updatedRow).ToBeVisibleAsync();

            Page.Dialog += async (_, dialog) => await dialog.AcceptAsync();
            await updatedRow.GetByTestId("book-delete").ClickAsync();
            await Expect(updatedRow).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });

            await GoToAsync("/books/99999999");
            await Expect(Page.GetByText("Book not found.")).ToBeVisibleAsync();
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
}
