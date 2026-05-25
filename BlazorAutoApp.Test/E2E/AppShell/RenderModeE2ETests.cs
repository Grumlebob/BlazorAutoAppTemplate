using System.Threading.Tasks;
using Xunit;
using BlazorAutoApp.Test.E2E.Support;

namespace BlazorAutoApp.Test.E2E.AppShell;

public sealed class RenderModeE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 to run Playwright E2E tests.", SkipUnless = nameof(E2ETestGuard.IsEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task HomePage_ReportsAssignedAutoAndHydratedRenderer()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            await GoHomeAndWaitForInteractivityAsync();

            var assignedMode = (await Page.GetByTestId("assigned-render-mode").InnerTextAsync()).Trim();
            Assert.True(
                assignedMode is "Interactive Server" or "Interactive WebAssembly" or "Interactive Auto",
                $"Expected assigned render mode to be interactive, but was '{assignedMode}'.");

            var currentRenderer = (await Page.GetByTestId("current-renderer").InnerTextAsync()).Trim();
            Assert.True(
                currentRenderer is "Server" or "WebAssembly",
                $"Expected hydrated renderer to be Server or WebAssembly, but was '{currentRenderer}'.");
        });
    }
}
