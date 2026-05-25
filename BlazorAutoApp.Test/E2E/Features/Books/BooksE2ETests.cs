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
            await Expect(Page.GetByTestId("add-book")).ToHaveCountAsync(0);
            await Expect(Page.GetByText("Saved books")).ToHaveCountAsync(0);

            var suffix = Guid.NewGuid().ToString("N")[..8];
            var title = $"E2E Book {suffix}";
            var updatedTitle = $"E2E Book Updated {suffix}";
            var author = $"E2E Author {suffix}";
            var url = $"https://example.test/books/{suffix}";

            await RegisterAsync($"books-{suffix}@example.test");
            await GoHomeAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("add-book")).ToBeVisibleAsync();
            await Expect(Page.GetByText("Saved books")).ToBeVisibleAsync();

            await Page.GetByTestId("add-book").ClickAsync();
            await Page.GetByTestId("book-title").FillAsync(title);
            await Page.GetByTestId("book-author").FillAsync(author);
            await Page.GetByTestId("book-url").FillAsync(url);
            await Page.GetByTestId("book-save").ClickAsync();

            var row = Page.Locator("[data-testid^='book-row-']").Filter(new LocatorFilterOptions { HasTextString = title });
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

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
        const string password = "Passw0rd!";

        await GoToAsync("/Account/Register");
        await Page.Locator("#Input\\.Email").FillAsync(email);
        await Page.Locator("#Input\\.Password").FillAsync(password);
        await Page.Locator("#Input\\.ConfirmPassword").FillAsync(password);
        await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Register" }).ClickAsync();
    }
}
