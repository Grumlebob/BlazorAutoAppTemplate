using System;
using System.IO;
using System.Threading.Tasks;
using BlazorAutoApp.Test.E2E.Support;
using Microsoft.Playwright;
using Xunit;

namespace BlazorAutoApp.Test.E2E.Observability;

public sealed class GrafanaObservabilityE2ETests : BlazorE2ETestBase
{
    [Fact(Skip = "Set RUN_E2E=1 and RUN_OBSERVABILITY_E2E=1 to run Grafana observability E2E tests.", SkipUnless = nameof(E2ETestGuard.IsObservabilityEnabled), SkipType = typeof(E2ETestGuard))]
    [Trait("Category", "E2E")]
    public async Task GrafanaHome_RendersCommandCenterAndDashboardLinks()
    {
        await RunWithFailureScreenshotAsync(async () =>
        {
            Page.SetDefaultTimeout(60_000);
            await Page.GotoAsync(GetGrafanaUrl(), new PageGotoOptions
            {
                WaitUntil = WaitUntilState.DOMContentLoaded
            });

            await Expect(Page.GetByText("Overall Health", new PageGetByTextOptions { Exact = true }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByText("Deployed Version", new PageGetByTextOptions { Exact = true }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByText("App Telemetry", new PageGetByTextOptions { Exact = true }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByText("Error Rate", new PageGetByTextOptions { Exact = true }))
                .ToBeVisibleAsync();
            await Expect(Page.GetByText("p95", new PageGetByTextOptions { Exact = true }))
                .ToBeVisibleAsync();
            await AssertPanelDoesNotContainAsync("Error Rate", "No data");
            await AssertPanelDoesNotContainAsync("Firing Alerts", "No data");

            await AssertDashboardLinkAsync("Application And Books", "Books Application And Books");
            await AssertDashboardLinkAsync("Infrastructure And Data", "Books Infrastructure And Data");
            await AssertDashboardLinkAsync("Telemetry And Alerts", "Books Telemetry And Alerts");
            await AssertDashboardLinkAsync("Logs And Traces", "Books Logs And Traces");

            await AssertNoObviousGrafanaErrorsAsync();
            await CaptureAsync("grafana-command-center");
        });
    }

    private async Task AssertDashboardLinkAsync(string linkText, string expectedTitle)
    {
        await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = linkText, Exact = true }).ClickAsync();
        await Expect(Page.GetByText(expectedTitle, new PageGetByTextOptions { Exact = true }))
            .ToBeVisibleAsync();
        await AssertNoObviousGrafanaErrorsAsync();
        await Page.GetByRole(AriaRole.Link, new PageGetByRoleOptions { Name = "Command Center", Exact = true }).ClickAsync();
        await Expect(Page.GetByText("Overall Health", new PageGetByTextOptions { Exact = true }))
            .ToBeVisibleAsync();
    }

    private async Task AssertPanelDoesNotContainAsync(string panelName, string unexpectedText)
    {
        var panelText = await Page.GetByRole(AriaRole.Region, new PageGetByRoleOptions { Name = panelName, Exact = true })
            .InnerTextAsync();
        Assert.DoesNotContain(unexpectedText, panelText, StringComparison.OrdinalIgnoreCase);
    }

    private async Task AssertNoObviousGrafanaErrorsAsync()
    {
        var bodyText = await Page.Locator("body").InnerTextAsync();
        var forbidden = new[]
        {
            "Dashboard not found",
            "Panel plugin not found",
            "Datasource not found",
            "Templating init failed",
            "An unexpected error happened"
        };

        foreach (var text in forbidden)
        {
            Assert.DoesNotContain(text, bodyText, StringComparison.OrdinalIgnoreCase);
        }
    }

    private async Task CaptureAsync(string name)
    {
        var directory = GetPlaywrightArtifactPath("Observability");
        Directory.CreateDirectory(directory);
        await Page.ScreenshotAsync(new PageScreenshotOptions
        {
            Path = Path.Combine(directory, $"{name}.png"),
            FullPage = true
        });
    }

    private static string GetGrafanaUrl()
    {
        var configured = Environment.GetEnvironmentVariable("GRAFANA_URL");
        return string.IsNullOrWhiteSpace(configured)
            ? "http://localhost:3000"
            : configured.TrimEnd('/');
    }
}
