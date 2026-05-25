using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Playwright;
using Xunit;

namespace BlazorAutoApp.Test.E2E;

public sealed class VisualSnapshotE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task KeyScreens_CanBeCapturedForReview()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            var suffix = Guid.NewGuid().ToString("N")[..8];
            var title = $"Snapshot Movie {suffix}";
            var director = $"Snapshot Director {suffix}";

            await GoHomeAndWaitForInteractivityAsync();
            await CaptureAsync("home");

            await Page.GetByTestId("add-movie").ClickAsync();
            await CaptureAsync("movies-create");

            await Page.GetByTestId("movie-title").FillAsync(title);
            await Page.GetByTestId("movie-director").FillAsync(director);
            await Page.GetByTestId("movie-rating").FillAsync("9");
            await Page.GetByTestId("movie-save").ClickAsync();

            var row = Page.Locator("tbody tr").Filter(new LocatorFilterOptions { HasTextString = title });
            await Expect(row).ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await row.GetByTestId("movie-view").ClickAsync();
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = title })).ToBeVisibleAsync();
            await CaptureAsync("movies-details");

            await Page.GetByTestId("movie-back").ClickAsync();
            await row.GetByTestId("movie-edit").ClickAsync();
            await Expect(Page.GetByTestId("movie-title")).ToHaveValueAsync(title);
            await CaptureAsync("movies-edit");

            await GoToAsync("/Account/Login");
            await CaptureAsync("login");

            await GoToAsync("/Account/Register");
            await CaptureAsync("register");

            var email = $"snapshot-{suffix}@example.test";
            const string password = "Passw0rd!";
            await Page.Locator("#Input\\.Email").FillAsync(email);
            await Page.Locator("#Input\\.Password").FillAsync(password);
            await Page.Locator("#Input\\.ConfirmPassword").FillAsync(password);
            await Page.GetByRole(AriaRole.Button, new PageGetByRoleOptions { Name = "Register" }).ClickAsync();
            await GoToAsync("/Account/Manage");
            await Expect(Page.GetByRole(AriaRole.Heading, new PageGetByRoleOptions { Name = "Profile" }))
                .ToBeVisibleAsync(new LocatorAssertionsToBeVisibleOptions { Timeout = 30_000 });
            await CaptureAsync("account-manage");

            await GoToAsync("/movies/99999999");
            await Expect(Page.GetByText("Movie not found.")).ToBeVisibleAsync();
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
