using System;
using System.Threading.Tasks;
using BlazorAutoApp.Test.E2E.Support;
using BlazorAutoApp.Test.TestSupport.Integration;
using Microsoft.Playwright;
using Xunit;

namespace BlazorAutoApp.Test.E2E.AppShell;

/// <summary>
/// Prerendered buttons do nothing until Blazor is interactive. They must render
/// disabled so a click is never silently lost, then enable after hydration.
/// </summary>
[Collection(TestCollectionNames.E2E)]
public sealed class PreHydrationControlsE2ETests : BlazorE2ETestBase
{
    private const string CreateBookPath = "/books?bookMode=create";

    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task BookEditorSave_IsDisabledBeforeHydrationAndEnabledAfterwards()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            await RegisterUniqueUserAsync("prehydration");

            const string frameworkScriptPattern = "**/_framework/blazor.web*.js";
            var frameworkScriptIntercepted = false;
            await Page.RouteAsync(frameworkScriptPattern, async route =>
            {
                frameworkScriptIntercepted = true;
                await route.AbortAsync();
            });

            try
            {
                await GoToAsync(CreateBookPath);
                Assert.True(frameworkScriptIntercepted, "Expected the Blazor framework script request to be intercepted.");
                await Expect(Page.GetByTestId("app-interactivity-probe"))
                    .ToHaveAttributeAsync("data-interactive", "false");

                var prerenderedSave = Page.GetByTestId("book-save");
                if (await prerenderedSave.CountAsync() > 0)
                {
                    await Expect(prerenderedSave).ToBeDisabledAsync();
                }
            }
            finally
            {
                await Page.UnrouteAsync(frameworkScriptPattern);
            }

            await ReloadAndWaitForInteractivityAsync();
            await Expect(Page.GetByTestId("book-page-editor")).ToBeVisibleAsync();
            await Expect(Page.GetByTestId("book-save")).ToBeEnabledAsync();
        });
    }
}
