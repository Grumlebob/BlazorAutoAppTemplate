using System;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Xunit;

namespace BlazorAutoApp.Test.E2E;

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

            await row.GetByTestId("movie-edit").ClickAsync();
            await Expect(Page.GetByTestId("movie-title")).ToHaveValueAsync(title);
            await Page.GetByTestId("movie-cancel").ClickAsync();
            await Expect(row).ToBeVisibleAsync();
        });
    }
}
