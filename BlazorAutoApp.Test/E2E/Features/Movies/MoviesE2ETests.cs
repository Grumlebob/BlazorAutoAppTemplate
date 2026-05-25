using System;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Xunit;
using BlazorAutoApp.Test.E2E.Support;

namespace BlazorAutoApp.Test.E2E.Features.Movies;

public sealed class MoviesE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task Movies_CanCreateViewEditCancelAndNavigateBack()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            await GoHomeAndWaitForInteractivityAsync();

            var suffix = Guid.NewGuid().ToString("N")[..8];
            var title = $"E2E Movie {suffix}";
            var updatedTitle = $"E2E Movie Updated {suffix}";
            var director = $"E2E Director {suffix}";

            await Page.GetByTestId("add-movie").ClickAsync();
            await Page.GetByTestId("movie-title").FillAsync(title);
            await Page.GetByTestId("movie-director").FillAsync(director);
            await Page.GetByTestId("movie-rating").FillAsync("8");
            await Page.GetByTestId("movie-save").ClickAsync();

            var row = Page.Locator("tbody tr").Filter(new LocatorFilterOptions { HasTextString = title });
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await row.GetByTestId("movie-view").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GetByTestId("movie-back").ClickAsync();
            await Expect(row).ToBeVisibleAsync();

            await row.GetByTestId("movie-view").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title }))
                .ToBeVisibleAsync();
            await Page.GoBackAsync();
            await Expect(row).ToBeVisibleAsync();

            await row.GetByTestId("movie-edit").ClickAsync();
            await Expect(Page.GetByTestId("movie-title")).ToHaveValueAsync(title);
            await Page.GetByTestId("movie-title").FillAsync(updatedTitle);
            await Page.GetByTestId("movie-save").ClickAsync();
            var updatedRow = Page.Locator("tbody tr").Filter(new LocatorFilterOptions { HasTextString = updatedTitle });
            await Expect(updatedRow).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });

            await updatedRow.GetByTestId("movie-edit").ClickAsync();
            await Expect(Page.GetByTestId("movie-title")).ToHaveValueAsync(updatedTitle);
            await Page.GetByTestId("movie-cancel").ClickAsync();
            await Expect(updatedRow).ToBeVisibleAsync();

            Page.Dialog += async (_, dialog) => await dialog.AcceptAsync();
            await updatedRow.GetByTestId("movie-delete").ClickAsync();
            await Expect(updatedRow).ToBeHiddenAsync(new LocatorAssertionsToBeHiddenOptions { Timeout = 30_000 });

            await GoToAsync("/movies/99999999");
            await Expect(Page.GetByText("Movie not found.")).ToBeVisibleAsync();
        });
    }
}
